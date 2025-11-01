#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MultiChain Explorer - Main Entry Point

This is the main entry point for the MultiChain Explorer application.
It handles command-line arguments, daemon mode, and process management.
"""

import logging
import os
import signal
import sys
from typing import List, Optional

import app_state
import http_server
import readconf
import utils

# Application metadata
APP_NAME = "MultiChain Explorer"
APP_VERSION = app_state.VERSION

# Configure module logger
logger = logging.getLogger(__name__)


def show_usage() -> None:
    """Display usage information."""
    usage_text = f"""
Usage: python main.py config-file.ini [action]

{APP_NAME}, version {APP_VERSION}

Arguments:
  config-file               Configuration file (see example.ini for examples)
  
Optional Actions:
  daemon                    Start explorer as background daemon
  stop                      Stop running explorer instance
  status                    Check explorer status

Examples:
  python main.py multichain.ini
  python main.py multichain.ini daemon
  python main.py multichain.ini stop
"""
    print(usage_text)


def check_running_instance() -> Optional[int]:
    """
    Check if an explorer instance is already running.

    Returns:
        PID of running instance, or None if not running
    """
    state = app_state.get_state()
    current_pid = utils.file_read(state.pid_file)

    if current_pid is not None:
        try:
            # Check if process is actually running using utils function
            if utils.is_process_running(int(current_pid)):
                return int(current_pid)
            else:
                # Process not running, clean up stale PID file
                utils.remove_file(state.pid_file)
                return None
        except (OSError, ValueError):
            # Error checking process or invalid PID, clean up
            utils.remove_file(state.pid_file)
            return None

    return None


def handle_stop_action(pid: Optional[int]) -> int:
    """
    Handle the 'stop' action.

    Args:
        pid: PID of running instance, or None

    Returns:
        Exit code (0 for success)
    """
    if pid is None:
        print("Explorer is not running\n")
        return 0

    print(f"Explorer found, PID {pid}")
    utils.log_write(f"Stopping Explorer, PID: {pid}")
    print("Sending stop signal...")

    try:
        os.kill(pid, signal.SIGTERM)
        state = app_state.get_state()
        utils.remove_file(state.pid_file)
        print("Explorer stopped successfully")
    except OSError as e:
        logger.warning(f"Error stopping explorer: {e}")
        utils.log_write("Explorer already stopped")
        state = app_state.get_state()
        utils.remove_file(state.pid_file)

    return 0


def handle_status_action(pid: Optional[int]) -> int:
    """
    Handle the 'status' action.

    Args:
        pid: PID of running instance, or None

    Returns:
        Exit code (0 for success)
    """
    if pid is None:
        print("Explorer is not running\n")
    else:
        print(f"Explorer is running, PID {pid}\n")

    return 0


def start_explorer() -> bool:
    """
    Start the explorer server.

    Returns:
        True if server started and stopped gracefully, False on error
    """
    # Write PID file
    state = app_state.get_state()
    pid = utils.get_pid()
    utils.file_write(state.pid_file, pid)

    current_pid = utils.file_read(state.pid_file)
    utils.log_write(f"Explorer started, PID: {current_pid}")
    logger.info(f"Explorer started with PID: {current_pid}")

    # Start HTTP server
    try:
        success = http_server.start_server()
    except Exception as e:
        logger.error(f"Server error: {e}")
        success = False
    finally:
        # Clean up PID file
        utils.remove_file(state.pid_file)
        utils.log_write("Explorer stopped")

    return success


def main(argv: List[str]) -> int:
    """
    Main entry point for the application.

    Args:
        argv: Command-line arguments (excluding program name)

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Check for arguments
    if len(argv) == 0:
        show_usage()
        return 0

    # Display app banner
    print(f"\n{APP_NAME}, version {app_state.VERSION}\n")

    # Parse command-line arguments
    args = readconf.parse_argv(argv)

    # Handle daemon mode
    state = app_state.get_state()
    if state.action == "daemon":
        logger.info("Starting in daemon mode...")
        utils.become_daemon()

    # Read configuration
    if not readconf.read_conf(args):
        logger.error("Failed to read configuration")
        return 1

    # Check for running instance
    running_pid = check_running_instance()

    # Handle actions
    if state.action is not None:
        if state.action == "stop":
            return handle_stop_action(running_pid)
        elif state.action == "status":
            return handle_status_action(running_pid)

    # Check if already running (for start action)
    if running_pid is not None:
        utils.print_error(
            f"Explorer is already running with PID {running_pid}\n"
            f"Use 'python main.py {argv[0]} stop' to stop it first."
        )
        return 1

    # Start the explorer
    try:
        success = start_explorer()
        return 0 if success else 1
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        return 0
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
