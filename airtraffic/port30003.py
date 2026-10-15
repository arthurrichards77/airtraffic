import rclpy
from rclpy.node import Node
from foxglove_msgs.msg import GeoJSON
import socket
from shapely.geometry import Point
from geopandas import GeoDataFrame
import pandas as pd
import time

class Port30003Publisher(Node):

    def __init__(self):
        super().__init__('port30003_publisher')
        self.tracker = GeoDataFrame(columns=['name','metadata','alt_ft',
                                             #'last_seen',
                                             'last_update','callsign',
                                             'geometry'],
                                    crs=4326)
        self.publisher2_ = self.create_publisher(GeoJSON, 'adsb2', 10)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect(('localhost',30003))
        self.socket.setblocking(False)
        timer_period = 0.5  # seconds
        self.update_count = 0
        self.track_timeout = 60 # 60 steps or 30s
        self.timer = self.create_timer(timer_period, self.timer_callback)

    def timer_callback(self):
        self.update_count = self.update_count + 1
        try:
            data_str = self.socket.recv(4096).decode('utf-8')
            msg_list = data_str.split('\r\n')
            msg_list = [m for m in msg_list if len(m)>0]
            self.get_logger().info(f'Got {len(msg_list)} messages from receiver')
            for msg in msg_list:
                msg_data = msg.split(',')
                if len(msg_data)>=16:
                    icao_id = msg_data[4]
                    find_ac = (self.tracker['name']==icao_id)
                    # see if it has lat/lon
                    lat_str = msg_data[14]
                    lon_str = msg_data[15]
                    #print(lat_str,lon_str)
                    if len(lat_str)>0 and len(lon_str)>0:
                        # update tracker
                        cur_point = Point(float(lon_str),float(lat_str))
                        cur_alt_ft = float(msg_data[11])
                        cur_time = time.strptime(msg_data[7][0:8],'%H:%M:%S')
                        if any(find_ac):
                            self.tracker.loc[find_ac,'geometry'] = cur_point
                            self.tracker.loc[find_ac,'alt_ft'] = cur_alt_ft
                            #self.tracker.loc[find_ac,'last_seen'] = cur_time
                            self.tracker.loc[find_ac,'last_update'] = self.update_count
                            self.tracker.loc[find_ac,'metadata'] = None
                            self.get_logger().info(f'Update track {icao_id}')
                        else:
                            new_gpd = GeoDataFrame({'name': [icao_id],
                                                    'geometry': [cur_point],
                                                    'alt_ft': [cur_alt_ft],
                                                    #'last_seen': cur_time,
                                                    'last_update': [self.update_count],
                                                    'callsign': [None],
                                                    'metadata': [None],
                                                    },
                                                    crs=4326)
                            print(self.tracker)
                            print(new_gpd)
                            self.tracker = pd.concat((self.tracker, new_gpd))
                            print(self.tracker)
                            self.get_logger().info(f'New track {icao_id}')
                    callsign = msg_data[10].strip()
                    if len(callsign)>0:
                        self.tracker.loc[find_ac,'callsign'] = callsign
        except BlockingIOError:
            pass
        faded_tracks = self.tracker['last_update']<(self.update_count - self.track_timeout)
        if any(faded_tracks):
            for _,r in self.tracker[faded_tracks].iterrows():
                self.get_logger().info(f'Removing lost track {r['name']}')
            #self.get_logger().info(self.tracker.loc[faded_tracks,'name'])
            #print(self.tracker.loc[faded_tracks,'name'])
            self.tracker.drop(faded_tracks.index, inplace=True)
        self.tracker['metadata'] = [{'alt_ft': str(r['alt_ft']), 'callsign':r['callsign']} for _,r in self.tracker.iterrows()]
        ros_msg2 = GeoJSON(geojson=self.tracker.to_json())
        self.publisher2_.publish(ros_msg2)
        #print(self.tracker)

def main(args=None):
    rclpy.init(args=args)
    port30003_publisher = Port30003Publisher()
    rclpy.spin(port30003_publisher)
    # Destroy the node explicitly
    port30003_publisher.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
