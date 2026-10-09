"""Launch a MoveIt Setup Assistant robot in Gazebo with ros2_control.

Usage:
    ros2 launch gz_sim.launch.py moveit_config:=<your_moveit_config_package> [world:=<path.sdf>]

Reads the Setup Assistant's URDF and ros2_controllers.yaml, replaces mock
hardware with Gazebo hardware, starts Gazebo, spawns the robot, and starts
every controller listed in ros2_controllers.yaml. Start MoveIt with
moveit_sim.launch.py.
"""
import os
import re

import xacro
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            OpaqueFunction, RegisterEventHandler, SetEnvironmentVariable)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

GZ_PLUGIN = """
  <gazebo>
    <plugin filename="gz_ros2_control-system" name="gz_ros2_control::GazeboSimROS2ControlPlugin">
      <parameters>{controllers}</parameters>
    </plugin>
  </gazebo>
</robot>"""


def _setup(context):
    pkg = LaunchConfiguration("moveit_config").perform(context)
    world = LaunchConfiguration("world").perform(context)
    share = get_package_share_directory(pkg)
    config = os.path.join(share, "config")
    xacros = [f for f in os.listdir(config) if f.endswith(".urdf.xacro")]
    if len(xacros) != 1:
        raise RuntimeError(f"Expected one .urdf.xacro in {config}, found {xacros}")
    controllers = os.path.join(config, "ros2_controllers.yaml")

    urdf = xacro.process_file(os.path.join(config, xacros[0]),
                              mappings={"initial_positions_file": os.path.join(config, "initial_positions.yaml")}).toxml()
    urdf = urdf.replace("mock_components/GenericSystem", "gz_ros2_control/GazeboSimSystem")
    urdf = urdf.replace("</robot>", GZ_PLUGIN.format(controllers=controllers), 1)

    # Add package share roots to Gazebo's resource path for package://<name>/... meshes.
    roots = {os.path.dirname(get_package_share_directory(p))
             for p in set(re.findall(r"package://([^/]+)/", urdf))}
    resource_path = os.pathsep.join(sorted(roots) + [os.environ.get("GZ_SIM_RESOURCE_PATH", "")])

    with open(controllers) as f:
        cm = yaml.safe_load(f)["controller_manager"]["ros__parameters"]
    names = [n for n, v in cm.items() if isinstance(v, dict) and "type" in v]
    names.sort(key=lambda n: n != "joint_state_broadcaster")

    gz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory("ros_gz_sim"), "launch", "gz_sim.launch.py")),
        launch_arguments={"gz_args": f"-r {world}", "on_exit_shutdown": "true"}.items())
    rsp = Node(package="robot_state_publisher", executable="robot_state_publisher",
               parameters=[{"robot_description": urdf, "use_sim_time": True}])
    robot = re.search(r'<robot[^>]*name="([^"]+)"', urdf).group(1)
    spawn = Node(package="ros_gz_sim", executable="create",
                 arguments=["-topic", "robot_description", "-name", robot])
    clock = Node(package="ros_gz_bridge", executable="parameter_bridge",
                 arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"])
    spawner = Node(package="controller_manager", executable="spawner",
                   arguments=names + ["--controller-manager-timeout", "60"])
    return [SetEnvironmentVariable("GZ_SIM_RESOURCE_PATH", resource_path),
            gz, rsp, clock, spawn,
            RegisterEventHandler(OnProcessExit(target_action=spawn, on_exit=[spawner]))]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("moveit_config", description="Your MoveIt config package name"),
        DeclareLaunchArgument("world", default_value="empty.sdf",
                              description="Gazebo world: empty.sdf or a path to your .sdf"),
        OpaqueFunction(function=_setup),
    ])
