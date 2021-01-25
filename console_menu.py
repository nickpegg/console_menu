#!/usr/bin/env python3

import logging
import os
import re
import shutil
import subprocess
import sys
import yaml

from argparse import ArgumentParser, Namespace
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Optional, Tuple

from serial import Serial
from serial.tools.list_ports import comports
from serial.tools.miniterm import main as miniterm

TTY_PATTERN = "/dev/ttyUSB"
LOGIN_RE = r"(.+)\s+login"

# Gotta go fast
BAUD_RATE = 115200


logger = logging.getLogger("console_menu")


def main() -> None:
    args = parse_args()

    picocom_path = shutil.which("picocom")
    if not picocom_path:
        print("Unable to find picocom installed")
        sys.exit(1)

    if args.discover:
        host_ports = discover()
        if len(host_ports) == 0:
            print("Did not discover any hosts")
            sys.exit(1)

        with open(args.file, "w") as f:
            f.write(yaml.dump(host_ports))
        sys.exit(0)

    if os.path.exists(args.file):
        host_ports = yaml.safe_load(open(args.file))
    else:
        host_ports = {}
    if len(host_ports) == 0:
        print(
            f"Did not load any host ports from {args.file}. Make sure to run "
            "console_menu --discover to discover which hosts are on which ports"
        )
        sys.exit(1)

    if args.hostname:
        # Hostname given via CLI, connect to it and exit
        if args.hostname not in host_ports:
            print(f"Requested host {args.hostname} was not found via discovery")
            sys.exit(1)
        connect(host_ports[args.hostname], args.timeout)
    else:
        # Launch into menu mode
        while True:
            print("\nSelect a host to connect to:")
            for host in sorted(host_ports.keys()):
                print(f"- {host}")
            print("")

            try:
                selection = input(f"Your selection (Press Enter to exit): ")
            except KeyboardInterrupt:
                sys.exit(0)

            if selection == "":
                sys.exit(0)
            elif selection not in host_ports:
                print("Invalid selection!")
                continue

            connect(host_ports[selection], args.timeout)


def parse_args() -> Namespace:
    arg_parser = ArgumentParser()

    arg_parser.add_argument("hostname", nargs="?")
    arg_parser.add_argument("--logging", default="warning")
    arg_parser.add_argument("--discover", action="store_true", help="Run discovery")
    arg_parser.add_argument(
        "-f",
        "--file",
        default="ports.yml",
        help="Path to the file to store port mapping in",
    )
    arg_parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=60,
        help="Close console connection after this many seconds of inactivity",
    )

    arg_parser.add_argument(
        "-c", help="Unused, for shell compatibility", action="store_true"
    )

    args = arg_parser.parse_args()

    # Set up logging
    try:
        logging_level = getattr(logging, args.logging.upper())
    except AttributeError:
        logging.error(f"Invalid --logging value: {args.logging}")
        logging_level = logging.WARNING
    logging.basicConfig(level=logging_level)
    logger.debug(f"log level: {args.logging}")

    return args


def discover() -> Dict[str, str]:
    """
    Discover hosts on all serial ports which match TTY_PATTERN, and return a mapping of
    hostname to serial port name
    """
    discovered_hosts = {}

    pool = ThreadPoolExecutor()
    futures = []

    logger.info("Discovering hosts on ports")
    for port_info in comports():
        if TTY_PATTERN in port_info.device:
            logger.debug(
                f"Found interesting port {port_info.device}, discovering host on there"
            )
            futures.append(pool.submit(discover_port, port_info.device))

    if len(futures) == 0:
        logger.info(f"Found no ports that match: {TTY_PATTERN}")
        return {}

    for future in as_completed(futures):
        (hostname, port) = future.result()
        if hostname:
            logger.info(f"Found {hostname} on {port}")
            discovered_hosts[hostname] = port
        else:
            logger.warning(f"Unable to detect hostname on port {port}")

    return discovered_hosts


def discover_port(port: str) -> Tuple[Optional[str], str]:
    """
    Discover the hostname of a Linux server on a single port. Does this by expecting a
    login prompt after sending a couple of CRs.
    """
    serial_port = Serial(port=port, baudrate=BAUD_RATE, timeout=0.5)

    i = 0
    hostname = None
    while not hostname and i < 3:
        serial_port.write(b"\n")
        line = serial_port.readline().decode()

        match = re.search(LOGIN_RE, line)
        if match:
            hostname = match.group(1)
        else:
            hostname = None

    serial_port.close()
    return (hostname, port)


def connect(port: str, timeout_s: float) -> None:
    """
    Get a console session open to ``port``.
    """
    timeout_ms = int(timeout_s * 1000)
    subprocess.run(["picocom", f"-b {BAUD_RATE}", f"-x {timeout_ms}", port])


if __name__ == "__main__":
    main()
