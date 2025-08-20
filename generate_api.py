#!/usr/bin/env python3

import argparse
import os
from pathlib import Path
import re
import subprocess
import time
import yaml

EXCLUDE_PATTERNS = re.compile(
    r"(describe_parameters|get_parameter_types|get_parameters|list_parameters|set_parameters|rosout|parameter_events)"
)


def find_ros2_executables(workspace="install"):
    executables = []
    install_path = Path(workspace)
    if not install_path.exists():
        raise FileNotFoundError(f"No install directory found at {workspace}")

    for pkg_dir in install_path.iterdir():
        lib_path = pkg_dir / "lib" / pkg_dir.name
        if not lib_path.exists():
            continue
        for exe in lib_path.iterdir():
            if os.access(exe, os.X_OK) and exe.is_file():
                executables.append(
                    {"package": pkg_dir.name, "executable": exe.name, "path": str(exe)}
                )
    return executables


def run_cmd(cmd):
    """Run a shell command and return stdout lines."""
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip().splitlines()


def write_api_to_file(
    api: dict,
    machine_output_file: str = "public_api.yaml",
    human_output_file: str = "PUBLIC_API.md",
):
    """
    Writes the public api for a given ROS2 node to a file
    Inputs:
    api: Distionary containing the api for each node
    machine_output_file: String. Name of the to write the machine-readable api file to
    human_output_file: String. Name of the to write the human-readable api file to
    """
    # Machine readable version
    with open(machine_output_file, "w") as f:
        yaml.dump(api, f, sort_keys=False)

    # Human readable version
    md_lines = ["# Public API - ROS2 Interfaces"]
    for node in api.keys():
        md_lines += ["## " + node]
        for interface in api[node].keys():
            md_lines += ["### " + interface, "| Name | Type |", "| :--- | :--- |"]
            for api_element in api[node][interface]:
                md_lines += [f"| {api_element['name']} | {api_element['type']} |"]
            md_lines += [""]

    with open(human_output_file, "w") as f:
        f.write("\n".join(md_lines))


def parse_node_api(api: dict = {}):
    """
    Parse the api for the currently running nodes into a dictionary
    """
    node_list = run_cmd(["ros2", "node", "list"])

    for node in node_list:
        node_info = run_cmd(["ros2", "node", "info", node])

        # Add node name to the api dict (not necessarily the same as the exec name)
        node_name = node_info.pop(0)
        if node_name in api.keys():
            continue

        api[node_name] = {}

        # Iterate over the info
        curr_key = ""
        for line in node_info:
            if line.isspace() or not line:
                continue

            if (
                "subscribers:" in line.lower()
                or "publishers:" in line.lower()
                or "service servers:" in line.lower()
                or "service clients:" in line.lower()
                or "action servers:" in line.lower()
                or "action clients:" in line.lower()
            ):
                curr_key = line

                if curr_key not in api[node_name].keys():
                    api[node_name][curr_key] = []

                continue

            # Don't include it if the interface is one of the default interfaces
            if EXCLUDE_PATTERNS.search(line):
                continue

            try:
                api_element = line.split(": ")
                api_element = {"name": api_element[0].strip(), "type": api_element[1]}
            except IndexError as e:
                print(e.what())
                raise ValueError("Unable to parse API. Check parse script")

            api[node_name][curr_key].append(api_element)

    return api


def extract_api(human_readable_file: str, machine_readable_file: str):
    """
    Parses the ROS2 API for a given workspace, which is defined as
    the set of all ROS2 interfaces for the executables in the workspace.
    This includes parameters, publishers, subscribers, topic names,
    topic types, services, service types.
    """
    # Find the ROS2 executables
    execs = find_ros2_executables()

    # TODO: Figure out which executables need special running configuration

    # Run each executable and extract the API
    api = {}
    for exe in execs:
        p = subprocess.Popen(["ros2", "run", exe["package"], exe["executable"]])

        time.sleep(3)  # Wait for the node to spool up

        # Parse API
        api = parse_node_api(api)

        # Stop executables
        p.terminate()

    write_api_to_file(api, machine_readable_file, human_readable_file)
    print(f"Public API written to: {machine_readable_file} and {human_readable_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--human-readable-file",
        type=str,
        default="PUBLIC_API.md",
        help="Path to write the generated human-readable API to.",
    )
    parser.add_argument(
        "-m",
        "--machine-readable-file",
        type=str,
        default="public_api.yaml",
        help="Path to write the generated machine-readable API to.",
    )

    args = parser.parse_args()

    extract_api(args.human_readable_file, args.machine_readable_file)
