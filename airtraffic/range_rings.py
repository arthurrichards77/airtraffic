from warnings import warn
import json
import requests
import geopandas as gpd
from shapely.geometry import Point
import os
import rclpy
from rclpy.node import Node
from foxglove_msgs.msg import GeoJSON
    

NM_IN_METRES = 1852.0

LOCAL_CRS = 27700

class RangeRingPublisher(Node):

    def __init__(self):
        super().__init__('range_ring_publisher')
        self.declare_parameter('ctr_lon', -0.6)
        self.declare_parameter('ctr_lat', 51.2)
        self.declare_parameter('ring_list', [NM_IN_METRES*(i+1) for i in range(10)])
        self.publisher_ = self.create_publisher(GeoJSON, 'range_rings', 10)
        timer_period = 1.0  # seconds
        self.timer = self.create_timer(timer_period, self.timer_callback)

    def timer_callback(self):
        ring_list = self.get_parameter('ring_list').get_parameter_value().double_array_value
        num_rings = len(ring_list)
        ctr_lat = self.get_parameter('ctr_lat').get_parameter_value().double_value
        ctr_lon = self.get_parameter('ctr_lon').get_parameter_value().double_value
        gdf_ctrs = gpd.points_from_xy([ctr_lon]*num_rings,[ctr_lat]*num_rings,crs=4326)
        gdf_rings = gpd.GeoDataFrame(geometry=gdf_ctrs.to_crs(LOCAL_CRS).buffer(ring_list).boundary.to_crs(4326))
        msg = GeoJSON()
        msg.geojson = gdf_rings.to_json()
        self.publisher_.publish(msg)
        self.get_logger().debug('Publishing: "%s"' % msg.geojson)

def main(args=None):
    rclpy.init(args=args)
    range_ring_publisher = RangeRingPublisher()
    rclpy.spin(range_ring_publisher)
    # Destroy the node explicitly
    range_ring_publisher.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
