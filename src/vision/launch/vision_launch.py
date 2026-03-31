from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    zed_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory('zed_wrapper'), 'launch', 'zed_camera.launch.py'
        )]),
        launch_arguments={'camera_model': 'zed2'}.items(),
    )

    detector_node = Node(
        package='vision',
        executable='lane_detector',
        name='lane_detector'
    )

    return LaunchDescription([zed_launch, detector_node])