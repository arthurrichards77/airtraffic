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
        self.declare_parameter('ring_list', [(i+1.0) for i in range(10)])
        self.declare_parameter('ring_unit', 'NM')
        ring_list = self.get_parameter('ring_list').get_parameter_value().double_array_value
        num_rings = len(ring_list)
        ring_unit = self.get_parameter('ring_unit').get_parameter_value().string_value
        if ring_unit=='m':
            ring_scale = 1.0
        elif ring_unit=='NM':
            ring_scale = NM_IN_METRES
        else:
            self.get_logger().warn(f'Unrecognized unit {ring_unit}: assuming metres')
            ring_scale = 1.0
        ctr_lat = self.get_parameter('ctr_lat').get_parameter_value().double_value
        ctr_lon = self.get_parameter('ctr_lon').get_parameter_value().double_value
        gdf_ctrs = gpd.points_from_xy([ctr_lon]*num_rings,[ctr_lat]*num_rings,crs=4326)
        ring_list_m = [r*ring_scale for r in ring_list]
        gdf_rings = gpd.GeoDataFrame(geometry=gdf_ctrs.to_crs(LOCAL_CRS).buffer(ring_list_m).boundary.to_crs(4326))
        self.msg = GeoJSON()
        self.msg.geojson = gdf_rings.to_json()
        self.publisher_ = self.create_publisher(GeoJSON, 'range_rings', 10)
        timer_period = 1.0  # seconds
        self.timer = self.create_timer(timer_period, self.timer_callback)

    def timer_callback(self):
        self.publisher_.publish(self.msg)
        self.get_logger().debug('Publishing: "%s"' % self.msg.geojson)

def main(args=None):
    rclpy.init(args=args)
    range_ring_publisher = RangeRingPublisher()
    rclpy.spin(range_ring_publisher)
    # Destroy the node explicitly
    range_ring_publisher.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
