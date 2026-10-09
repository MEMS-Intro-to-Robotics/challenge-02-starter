# Challenge Homework 2: MoveIt, Gazebo, and a Task: [Your Name]

ECE 383 / ME 555: Introduction to Robotics and Automation (Fall 2026)

Update this README with your name, NetID, and a 1–3 line summary of your work.

## Contents

- `fix_moveit_config.py`: corrects known errors in the package the MoveIt Setup
  Assistant generates. Run it each time after you generate the package:
  `python3 fix_moveit_config.py ros2_ws/src/<your_moveit_config>`
- `gz_sim.launch.py`: starts Gazebo with your robot and its controllers
- `moveit_sim.launch.py`: starts MoveIt and RViz for the robot in Gazebo
- `task_world.sdf`: a starter Gazebo world; copy it and build your task's
  environment in the copy
- `display.launch.py`: shows a URDF in RViz with joint sliders, as in Homework 1
- `docs/`: your task screenshots
- `test_challenge_2.py`: automated repository checks
- `pytest.ini`: limits `pytest` to `test_challenge_2.py` so it skips the ROS 2
  workspace

Run the launch files from the repository root, for example
`ros2 launch gz_sim.launch.py moveit_config:=<your_moveit_config>`.

Start by copying your description package from your Homework 1 repository into
`ros2_ws/src/`. The help page for the challenge homeworks has setup notes and
troubleshooting guidance:
https://mems-intro-to-robotics.github.io/guides/challenge_hw_help/

## Run the grading checks

From the repository root on the VM:

```bash
pytest -v
```

The checks confirm that the repository contains your description package, a
MoveIt configuration package with the fixes applied, a world file of your own, a
Python task script that uses `pymoveit2`, three readable screenshots in `docs/`,
and an updated README. They also flag tracked ROS 2 build output.

The repository checks cover files and package setup. Course staff evaluate your
configuration, simulation, and task from your Gradescope PDF.

Before the final push, fix every failure and confirm that Classroom 50 reports a
passing result.
