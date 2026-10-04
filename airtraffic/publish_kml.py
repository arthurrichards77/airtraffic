from warnings import warn
import json
import requests
import geopandas as gpd
from shapely.geometry import Point
import os
import rclpy
from rclpy.node import Node
from foxglove_msgs.msg import GeoJSON
    

class KMLPublisher(Node):

    def __init__(self):
        super().__init__('kml_publisher')
        self.declare_parameter('kml_file', 'mymap.kml')
        self.publisher_ = self.create_publisher(GeoJSON, 'kml_layer', 10)
        filename = self.get_parameter('kml_file').get_parameter_value().string_value
        self.get_logger().info(f"Opening {filename}")
        gdf_kml = gpd.read_file(filename=filename)
        self.msg = GeoJSON()
        self.msg.geojson = gdf_kml.to_json()
        timer_period = 1.0  # seconds
        self.timer = self.create_timer(timer_period, self.timer_callback)

    def timer_callback(self):
        self.publisher_.publish(self.msg)
        self.get_logger().debug('Publishing: "%s"' % self.msg.geojson)

def main(args=None):
    rclpy.init(args=args)
    kml_publisher = KMLPublisher()
    rclpy.spin(kml_publisher)
    # Destroy the node explicitly
    kml_publisher.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
