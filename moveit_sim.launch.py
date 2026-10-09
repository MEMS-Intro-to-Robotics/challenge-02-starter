"""Launch MoveIt and RViz for a robot running in Gazebo (simulation time).

Usage:
    ros2 launch moveit_sim.launch.py moveit_config:=<your_moveit_config_package>

Run gz_sim.launch.py first in a separate terminal.
"""
import glob
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder


def _setup(context):
    pkg = LaunchConfiguration("moveit_config").perform(context)
    share = get_package_share_directory(pkg)
    srdfs = glob.glob(os.path.join(share, "config", "*.srdf"))
    if len(srdfs) != 1:
        raise RuntimeError(f"Expected one .srdf in {share}/config, found {srdfs}")
    robot = os.path.basename(srdfs[0])[:-len(".srdf")]

    mc = MoveItConfigsBuilder(robot, package_name=pkg).to_moveit_configs()
    sim = {"use_sim_time": True}
    move_group = Node(package="moveit_ros_move_group", executable="move_group", output="screen",
                      parameters=[mc.to_dict(), sim])
    rviz = Node(package="rviz2", executable="rviz2", output="log",
                arguments=["-d", os.path.join(share, "config", "moveit.rviz")],
                parameters=[mc.robot_description, mc.robot_description_semantic,
                            mc.robot_description_kinematics, mc.planning_pipelines,
                            mc.joint_limits, sim])
    return [move_group, rviz]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("moveit_config", description="Your MoveIt config package name"),
        OpaqueFunction(function=_setup),
    ])
