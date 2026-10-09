#!/usr/bin/env python3
"""Update a MoveIt Setup Assistant package's configuration (ROS 2 Jazzy).

1. Enable acceleration limits in config/joint_limits.yaml and replace zero
   max_acceleration values with --accel rad/s^2. This addresses planning
   failures caused by missing acceleration limits.
2. Write whole-number limits in config/joint_limits.yaml as decimals (100 becomes
   100.0). MoveIt stops at startup with "expected [double] got [integer]" when a
   limit such as max_velocity is a whole number, which happens when the URDF
   gives one (the Fusion exporter writes velocity="100").
3. Add missing action_ns and default entries in config/moveit_controllers.yaml
   so MoveIt can find FollowJointTrajectory controllers for execution.

Usage (from the folder that holds your MoveIt config package):
    python3 fix_moveit_config.py <your_moveit_config_folder> [--accel 2.0]

After regenerating the package in the Setup Assistant, run this script again
and rebuild with colcon.
"""
import argparse
import pathlib
import re
import sys


def fix_joint_limits(path: pathlib.Path, accel: float) -> int:
    text = path.read_text()
    text, n = re.subn(r"has_acceleration_limits: false", "has_acceleration_limits: true", text)
    text = re.sub(r"max_acceleration: 0(\.0*)?\s*$", f"max_acceleration: {accel}", text, flags=re.M)
    path.write_text(text)
    return n


def fix_integer_limits(path: pathlib.Path) -> int:
    text = path.read_text()
    text, n = re.subn(r"^(\s*(?:max|min)_(?:velocity|acceleration|position):\s*)(-?\d+)\s*$",
                      r"\g<1>\g<2>.0", text, flags=re.M)
    path.write_text(text)
    return n


def fix_controllers(path: pathlib.Path) -> int:
    lines = path.read_text().splitlines()
    out, fixed = [], 0
    for i, line in enumerate(lines):
        out.append(line)
        m = re.match(r"^(\s+)type: FollowJointTrajectory\s*$", line)
        if not m:
            continue
        block = []
        for nxt in lines[i + 1:]:
            if nxt.strip() and len(nxt) - len(nxt.lstrip()) < len(m.group(1)):
                break
            block.append(nxt)
        indent = m.group(1)
        if not any("action_ns:" in b for b in block):
            out.append(f"{indent}action_ns: follow_joint_trajectory")
            fixed += 1
        if not any(re.match(r"\s+default:", b) for b in block):
            out.append(f"{indent}default: true")
    path.write_text("\n".join(out) + "\n")
    return fixed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("package", type=pathlib.Path, help="your MoveIt config package folder")
    parser.add_argument("--accel", type=float, default=2.0, help="max joint acceleration, rad/s^2 (default 2.0)")
    args = parser.parse_args()

    config = args.package / "config"
    limits, controllers = config / "joint_limits.yaml", config / "moveit_controllers.yaml"
    for f in (limits, controllers):
        if not f.is_file():
            sys.exit(f"Not found: {f}\nPass the folder the Setup Assistant generated (it contains config/).")

    n = fix_joint_limits(limits, args.accel)
    print(f"{limits}: acceleration limits turned on for {n} joint(s)")
    n = fix_integer_limits(limits)
    print(f"{limits}: {n} whole-number limit(s) written as decimals")
    n = fix_controllers(controllers)
    print(f"{controllers}: action_ns added to {n} controller(s)")
    print("Now rebuild: colcon build --symlink-install && source install/setup.bash")


if __name__ == "__main__":
    main()
