#!/usr/bin/env python3
"""Automated repository checks for Challenge Homework 2: MoveIt, Gazebo, and a Task.

Run with: pytest test_challenge_2.py -v

These checks look for required repository artifacts and basic file validity.
Course staff use the Gradescope PDF to grade the configuration, the simulation,
the task, and the evidence that it ran.
"""

from __future__ import annotations

import hashlib
import struct
import subprocess
import warnings
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent

WORKSPACE_SRC = Path("ros2_ws/src")
REQUIRED_SCREENSHOT_COUNT = 3
README_STARTER_FINGERPRINTS = ("Update this README", "[Your Name]")
URDF_SUFFIXES = (".urdf.xacro", ".xacro", ".urdf")
MESH_SUFFIXES = {".stl", ".dae", ".obj"}
IGNORED_PARTS = {"build", "install", "log", ".git", "__pycache__"}
# Exclude starter files when looking for a task script.
SUPPLIED_FILES = {
    "display.launch.py",
    "fix_moveit_config.py",
    "gz_sim.launch.py",
    "moveit_sim.launch.py",
    "test_challenge_2.py",
}
# sha256 of the starter's task_world.sdf, used to identify unchanged copies.
STARTER_WORLD_SHA256 = "438d8b6b032fa8b1939031e245afecc93fa4d986b42b038728e1e87ef38ba35a"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
IMAGE_SIGNATURES = (
    b"\xff\xd8\xff",
    b"GIF87a",
    b"GIF89a",
    b"BM",
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _png_dimensions(path: Path) -> tuple[int, int] | None:
    data = path.read_bytes()
    if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None

    position = 8
    dimensions: tuple[int, int] | None = None
    compressed = bytearray()
    saw_end = False
    while position + 12 <= len(data):
        length = struct.unpack(">I", data[position:position + 4])[0]
        chunk_end = position + 12 + length
        if chunk_end > len(data):
            return None
        kind = data[position + 4:position + 8]
        payload = data[position + 8:position + 8 + length]
        expected_crc = struct.unpack(">I", data[position + 8 + length:chunk_end])[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != expected_crc:
            return None
        if kind == b"IHDR":
            if dimensions is not None or length != 13:
                return None
            dimensions = struct.unpack(">II", payload[:8])
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            if length != 0 or chunk_end != len(data):
                return None
            saw_end = True
            break
        position = chunk_end

    if dimensions is None or not compressed or not saw_end:
        return None
    try:
        zlib.decompress(compressed)
    except zlib.error:
        return None
    return dimensions


def _is_image(path: Path) -> bool:
    head = path.read_bytes()[:12]
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return _png_dimensions(path) is not None
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return True
    return any(head.startswith(signature) for signature in IMAGE_SIGNATURES)


def _files_under(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return [
        path for path in root.rglob("*")
        if path.is_file() and not (set(path.relative_to(root).parts) & IGNORED_PARTS)
    ]


def _is_urdf_file(path: Path) -> bool:
    return path.name.casefold().endswith(URDF_SUFFIXES)


def _packages(repo: Path) -> list[Path]:
    src = repo / WORKSPACE_SRC
    if not src.is_dir():
        return []
    return sorted(
        manifest.parent for manifest in src.rglob("package.xml")
        if not (set(manifest.parent.relative_to(repo).parts) & IGNORED_PARTS)
    )


def find_moveit_packages(repo: Path) -> list[Path]:
    """Packages that hold a Setup Assistant .srdf in config/."""
    return [p for p in _packages(repo) if any((p / "config").glob("*.srdf"))]


def find_description_packages(repo: Path) -> list[Path]:
    """Packages, other than MoveIt configs, that hold a URDF or xacro file."""
    moveit = set(find_moveit_packages(repo))
    return [
        p for p in _packages(repo)
        if p not in moveit and any(_is_urdf_file(f) for f in _files_under(p))
    ]


def check_moveit_package(repo: Path) -> list[str]:
    packages = find_moveit_packages(repo)
    if not packages:
        return [
            "Add the MoveIt configuration package that the Setup Assistant generated "
            "under ros2_ws/src/. The grader looks for a package with a .srdf file in "
            "its config/ folder."
        ]
    errors: list[str] = []
    for package in packages:
        name = package.relative_to(repo).as_posix()
        controllers = package / "config" / "moveit_controllers.yaml"
        limits = package / "config" / "joint_limits.yaml"
        if not controllers.is_file():
            errors.append(f"{name}/config/moveit_controllers.yaml is missing. "
                          "Generate the package again in the Setup Assistant.")
        elif "action_ns" not in _read_text(controllers):
            errors.append(
                f"{name}/config/moveit_controllers.yaml has no action_ns, so MoveIt "
                "cannot execute plans. Run 'python3 fix_moveit_config.py "
                f"{name}' and rebuild."
            )
        if limits.is_file() and "has_acceleration_limits: false" in _read_text(limits):
            errors.append(
                f"{name}/config/joint_limits.yaml still has acceleration limits turned "
                "off, so planning fails. Run 'python3 fix_moveit_config.py "
                f"{name}' and rebuild."
            )
    return errors


def check_description_package(repo: Path) -> list[str]:
    packages = find_description_packages(repo)
    if not packages:
        return [
            "Copy your robot description package from Challenge Homework 1 into "
            "ros2_ws/src/. The grader looks for a package with a URDF or xacro file "
            "that is not the MoveIt configuration."
        ]
    errors: list[str] = []
    for package in packages:
        name = package.relative_to(repo).as_posix()
        files = _files_under(package)
        if not any(path.suffix.casefold() in MESH_SUFFIXES for path in files):
            errors.append(f"{name} contains no mesh files. Copy its meshes/ folder too.")
        for urdf in (path for path in files if _is_urdf_file(path)):
            try:
                ET.parse(urdf)
            except ET.ParseError as exc:
                errors.append(
                    f"{urdf.relative_to(repo).as_posix()} is not well-formed XML: {exc}."
                )
    return errors


def check_world(repo: Path) -> list[str]:
    worlds = []
    for path in _files_under(repo):
        if path.suffix.casefold() != ".sdf":
            continue
        data = path.read_bytes()
        if b"<world" in data and hashlib.sha256(data).hexdigest() != STARTER_WORLD_SHA256:
            worlds.append(path)
    if worlds:
        return []
    return [
        "Add your Gazebo world: an .sdf file with a <world> element. The unchanged "
        "task_world.sdf from the starter does not count; copy it and build your task's "
        "environment in the copy."
    ]


def check_task_script(repo: Path) -> list[str]:
    for path in _files_under(repo):
        if path.suffix != ".py" or path.name in SUPPLIED_FILES:
            continue
        if "pymoveit2" in _read_text(path):
            return []
    return [
        "Add your task script: a Python file that uses pymoveit2 to carry out your "
        "task. It can live in a ROS 2 package under ros2_ws/src/ or in the "
        "repository root."
    ]


def check_required_files(repo: Path) -> list[str]:
    errors: list[str] = []

    readme = repo / "README.md"
    if not readme.is_file():
        errors.append("Add the missing required file: README.md")
    else:
        leftovers = [m for m in README_STARTER_FINGERPRINTS if m in _read_text(readme)]
        if leftovers:
            errors.append(
                "README.md still contains starter text: "
                + ", ".join(f"'{marker}'" for marker in leftovers)
                + ". Replace it with your name, NetID, and a 1-3 line summary."
            )

    errors.extend(check_moveit_package(repo))
    errors.extend(check_description_package(repo))
    errors.extend(check_world(repo))
    errors.extend(check_task_script(repo))

    docs = repo / "docs"
    if not docs.is_dir():
        errors.append("Add a docs/ directory containing your task screenshots.")
    else:
        candidates = [
            path for path in docs.iterdir()
            if path.is_file() and path.suffix.casefold() in IMAGE_EXTENSIONS
        ]
        valid_images = [path for path in candidates if _is_image(path)]
        unreadable = sorted(path.name for path in candidates if path not in valid_images)
        if len(valid_images) < REQUIRED_SCREENSHOT_COUNT:
            message = (
                "Add at least three readable screenshots to docs/ showing your task in "
                f"Gazebo. The grader found {len(valid_images)}. PNG, JPEG, GIF, BMP, and "
                "WebP files are accepted; course staff judge their content from the PDF."
            )
            if unreadable:
                message += (
                    " These files in docs/ are not readable images, so they were not "
                    "counted: " + ", ".join(unreadable) + "."
                )
            errors.append(message)
        elif unreadable:
            warnings.warn(
                "These files in docs/ are not readable images: "
                + ", ".join(unreadable)
                + ". They are not counted; remove them or save them again."
            )

    return errors


def check_repository_hygiene(repo: Path) -> list[str]:
    if not (repo / ".git").exists():
        return [
            "Run pytest from the root of your cloned repository. "
            "The grader could not find its .git directory."
        ]

    result = _run_git(repo, "ls-files")
    if result.returncode != 0:
        return [
            "The grader could not inspect tracked files with 'git ls-files'. "
            "Run 'git status' and resolve the reported Git problem first."
        ]

    forbidden_directories = {"build", "install", "log"}
    tracked = [Path(line) for line in result.stdout.splitlines() if line]
    prohibited = [
        path.as_posix()
        for path in tracked
        if ({part.casefold() for part in path.parts[:-1]} & forbidden_directories)
    ]
    if prohibited:
        shown = prohibited[:8]
        remainder = len(prohibited) - len(shown)
        summary = ", ".join(shown)
        if remainder:
            summary += f", and {remainder} more"
        return [
            "Remove generated build/, install/, and log/ files from Git tracking, "
            "then commit and push again. The files may remain on your VM if .gitignore "
            f"excludes them. Tracked generated files: {summary}"
        ]
    return []


def _assert_no_errors(errors: list[str]) -> None:
    assert not errors, "\n- " + "\n- ".join(errors)


def test_repository_evidence() -> None:
    _assert_no_errors(check_required_files(REPO_ROOT))
    for notice in check_repository_hygiene(REPO_ROOT):
        warnings.warn("No points lost: " + notice)
