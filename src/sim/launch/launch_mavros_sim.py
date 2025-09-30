#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node
import os

full_path = os.path.realpath(__file__)
path, filename = os.path.split(full_path)

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='mavros',
            executable='mavros_node',
            output='screen',
            parameters=[
                {'fcu_url': "udp://:14540@127.0.0.1:14557"},
                {'gcs_url': ''},
                {'system_id': 1},
                {'component_id': 1},
                {'target_system_id': 1},
                {'target_component_id': 1}
            ]
        ),
        ExecuteProcess(
            cmd=["/bin/bash", path + "/arm_vehicle.sh"],
            shell=True,
            output="screen"
        )
    ])
