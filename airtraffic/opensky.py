from warnings import warn
import json
import requests
import pandas as pd
from shapely.geometry import Point
from geopandas import GeoDataFrame
import os
import rclpy
from rclpy.node import Node
from foxglove_msgs.msg import GeoJSON
    
class OpenskyLiveClient():

    def __init__(self, credentials):
        resp = requests.post('https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token',
                             data={"grant_type":"client_credentials",
                                   "client_id":credentials["client_id"],
                                   "client_secret":credentials["client_secret"]},
                             headers={"Content-Type":"application/x-www-form-urlencoded"},
                             timeout=60)
        if resp.status_code==200:
            self.token = resp.json()['access_token']
            print('Authenticated OK')
        else:
            warn(f'Authentication problem: status code {resp.status_code}')
            self.token = None
        self.calls_remaining = 1e9

    @staticmethod
    def convert_json_to_df(input_json: str):
        df = pd.DataFrame(input_json['states'], columns=['icao24',
                                                         'callsign',
                                                         'origin_country',
                                                         'lastposupdate',
                                                         'lastcontact',
                                                         'lon',
                                                         'lat',
                                                         'baroaltitude',
                                                         'onground',
                                                         'velocity',
                                                         'true_track',
                                                         'vertrate',
                                                         'sensors',
                                                         'geoaltitude',
                                                         'squawk',
                                                         'spi',
                                                         'category',
                                                         ])
        return df

    @staticmethod
    def add_geometry_to_df(df: pd.DataFrame):
        df['geometry'] = [Point(lon,lat) for lon,lat in zip(df['lon'].to_list(),
                                                            df['lat'].to_list())]
        gdf = GeoDataFrame(df,crs='4326')
        return gdf

    def api_get(self,path,params=None,timeout=60):
        url = 'https://opensky-network.org/api/' + path
        resp = requests.get(url,
                            headers={"Authorization": "Bearer "+self.token},
                            params = params,
                            timeout = timeout)
        if resp.status_code != 200:
            warn(f'Status code {resp.status_code}')
            return
        if 'X-Rate-Limit-Remaining' in resp.headers:
            print(resp.headers['X-Rate-Limit-Remaining'],'calls remaining', )
            self.calls_remaining = int(resp.headers['X-Rate-Limit-Remaining'])
        return resp.json()

    def fetch_states(self, west: float,south: float,east: float,north: float):
        assert north>south
        assert east>west
        resp_json = self.api_get('states/all',
                                 params = {'lomin': west,
                                           'lamin': south,
                                           'lomax': east,
                                           'lamax': north,
                                           })
        df_state_vectors = self.convert_json_to_df(resp_json)
        return self.add_geometry_to_df(df_state_vectors)

    def fetch_own_states(self):
        resp_json = self.api_get('states/own')
        df_state_vectors = self.convert_json_to_df(resp_json)
        return self.add_geometry_to_df(df_state_vectors)

CRED_ENV_VAR = 'CREDENTIALS_FILE'

class OpenskyPublisher(Node):

    def __init__(self):
        super().__init__('opensky_publisher')
        # get credentials
        self.declare_parameter('credentials_file', 'NULL')
        cred_param = self.get_parameter('credentials_file').get_parameter_value().string_value
        if CRED_ENV_VAR in os.environ:
            cred_file = os.environ[CRED_ENV_VAR]
            self.get_logger().info(f'Using credentials file {cred_file} from env {CRED_ENV_VAR}')
        elif cred_param != 'NULL':
            cred_file = cred_param
            self.get_logger().info(f'Using credentials file {cred_file} from ROS2 parameter')
        else:
            cred_file = '~/credentials.json'
            self.get_logger().info(f'Using default credentials file {cred_file}')
        full_path = os.path.expanduser(cred_file)
        self.get_logger().info(f'Looking for credentials in {full_path}')
        with open(full_path,'r',encoding='utf-8') as f:
            credentials = json.load(f)
        self.osky_client = OpenskyLiveClient(credentials['opensky_live'])
        # get desired range
        self.declare_parameter('lomin', -0.6)
        self.declare_parameter('lamin', 51.2)
        self.declare_parameter('lomax', -0.3)
        self.declare_parameter('lamax', 51.6)
        self.publisher_ = self.create_publisher(GeoJSON, 'opensky', 10)
        # publish every N seconds
        timer_period = 2.0  # seconds
        self.timer = self.create_timer(timer_period, self.timer_callback)

    def timer_callback(self):
        gdf_osky = self.osky_client.fetch_states(self.get_parameter('lomin').get_parameter_value().double_value,
                                                 self.get_parameter('lamin').get_parameter_value().double_value,
                                                 self.get_parameter('lomax').get_parameter_value().double_value,
                                                 self.get_parameter('lamax').get_parameter_value().double_value,)
        gdf_osky['metadata'] = [{'alt': str(r['geoaltitude'])} for _,r in gdf_osky.iterrows()]
        msg = GeoJSON()
        msg.geojson = gdf_osky.rename(columns={'callsign':'name'}).to_json()
        self.publisher_.publish(msg)
        self.get_logger().debug('Publishing: "%s"' % msg.geojson)

def main(args=None):
    rclpy.init(args=args)
    opensky_publisher = OpenskyPublisher()
    rclpy.spin(opensky_publisher)
    # Destroy the node explicitly
    opensky_publisher.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
