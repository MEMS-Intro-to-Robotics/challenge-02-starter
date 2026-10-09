"""Launch RViz and joint sliders for a URDF or xacro file.

Usage:
    ros2 launch display.launch.py model:=<path to .urdf or .urdf.xacro> [fixed_frame:=<root link>]

Launches robot_state_publisher, joint_state_publisher_gui, and RViz with
RobotModel and TF displays. fixed_frame defaults to "world"; use your robot's
root link if the URDF has no link named world.
"""
import os
import tempfile

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

RVIZ_CONFIG = """Panels:
  - Class: rviz_common/Displays
    Name: Displays
Visualization Manager:
  Class: ""
  Displays:
    - Class: rviz_default_plugins/Grid
      Name: Grid
      Enabled: true
    - Class: rviz_default_plugins/RobotModel
      Name: RobotModel
      Enabled: true
      Description Source: Topic
      Description Topic:
        Value: /robot_description
    - Class: rviz_default_plugins/TF
      Name: TF
      Enabled: true
      Show Names: true
      Marker Scale: 0.3
  Enabled: true
  Name: root
  Views:
    Current:
      Class: rviz_default_plugins/Orbit
      Distance: 2.0
      Pitch: 0.4
      Yaw: 0.8
      Focal Point:
        X: 0
        Y: 0
        Z: 0.3
Window Geometry:
  Width: 1200
  Height: 850
"""


def generate_launch_description():
    rviz_file = os.path.join(tempfile.gettempdir(), "display_launch.rviz")
    with open(rviz_file, "w") as f:
        f.write(RVIZ_CONFIG)
    description = ParameterValue(Command(["xacro ", LaunchConfiguration("model")]), value_type=str)
    return LaunchDescription([
        DeclareLaunchArgument("model", description="Path to your .urdf or .urdf.xacro file"),
        DeclareLaunchArgument("fixed_frame", default_value="world",
                              description="RViz fixed frame: your robot's root link"),
        Node(package="robot_state_publisher", executable="robot_state_publisher",
             parameters=[{"robot_description": description}]),
        Node(package="joint_state_publisher_gui", executable="joint_state_publisher_gui"),
        Node(package="rviz2", executable="rviz2",
             arguments=["-d", rviz_file, "-f", LaunchConfiguration("fixed_frame")]),
    ])
