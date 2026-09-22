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

class OpenskyPublisher(Node):

    def __init__(self, osky_client):
        super().__init__('opensky_publisher')
        self.publisher_ = self.create_publisher(GeoJSON, 'opensky', 10)
        self.osky_client = osky_client
        timer_period = 2.0  # seconds
        self.timer = self.create_timer(timer_period, self.timer_callback)

    def timer_callback(self):
        gdf_osky = self.osky_client.fetch_states(-0.6,51.2,-0.3,51.6)
        gdf_osky['metadata'] = [{'alt': str(r['geoaltitude'])} for _,r in gdf_osky.iterrows()]
        msg = GeoJSON()
        msg.geojson = gdf_osky.rename(columns={'callsign':'name'}).to_json()
        self.publisher_.publish(msg)
        self.get_logger().info('Publishing: "%s"' % msg.geojson)

def main(args=None):
    rclpy.init(args=args)
    # load credentials and initialise client
    full_path = os.path.expanduser('~/credentials.json')
    print(f'Looking for credentials in {full_path}')
    with open(full_path,'r',encoding='utf-8') as f:
        credentials = json.load(f)
    osky_live = OpenskyLiveClient(credentials['opensky_live'])
    opensky_publisher = OpenskyPublisher(osky_client=osky_live)
    rclpy.spin(opensky_publisher)
    # Destroy the node explicitly
    opensky_publisher.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
