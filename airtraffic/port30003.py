import rclpy
from rclpy.node import Node
from foxglove_msgs.msg import LocationFix, KeyValuePair
import socket

class Port30003Publisher(Node):

    def __init__(self):
        super().__init__('port30003_publisher')
        self.publisher_ = self.create_publisher(LocationFix, 'adsb', 10)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect(('localhost',30003))
        self.socket.setblocking(False)
        timer_period = 0.5  # seconds
        self.timer = self.create_timer(timer_period, self.timer_callback)

    def timer_callback(self):
        try:
            data_str = self.socket.recv(4096).decode('utf-8')
            msg_list = data_str.split('\r\n')
            msg_list = [m for m in msg_list if len(m)>0]
            print(f'Got {len(msg_list)} messages')
            print(msg_list)
            for msg in msg_list:
                msg_data = msg.split(',')
                print(msg_data)
                if len(msg_data)>=16:
                    lat_str = msg_data[14]
                    lon_str = msg_data[15]
                    print(lat_str,lon_str)
                    if len(lat_str)>0 and len(lon_str)>0:
                        ros_msg = LocationFix()
                        ros_msg.frame_id = msg_data[4] # ICAO as primary ID
                        ros_msg.latitude = float(lat_str)
                        ros_msg.longitude = float(lon_str)
                        ros_msg.metadata = [KeyValuePair(key='ICAO',value=msg_data[4])]
                        self.publisher_.publish(ros_msg)
        except BlockingIOError:
            pass

def main(args=None):
    rclpy.init(args=args)
    port30003_publisher = Port30003Publisher()
    rclpy.spin(port30003_publisher)
    # Destroy the node explicitly
    port30003_publisher.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
