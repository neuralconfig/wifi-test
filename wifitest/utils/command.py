"""
Command utility module for executing shell commands.
"""

import subprocess
import logging
from typing import List, Dict, Any

def run_command(command: List[str], timeout: int = 30, logger=None) -> Dict[str, Any]:
    """
    Run a shell command and return the result.

    Args:
        command: List of command and arguments
        timeout: Timeout in seconds
        logger: Logger instance to use (optional)

    Returns:
        Dictionary containing success status, stdout, stderr, and return code
    """
    cmd_str = ' '.join(command)
    
    if logger:
        logger.debug(f"Running command: {cmd_str}")

    result = {
        "success": False,
        "stdout": "",
        "stderr": "",
        "returncode": -1,
        "command": cmd_str
    }

    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        result["stdout"] = process.stdout
        result["stderr"] = process.stderr
        result["returncode"] = process.returncode
        result["success"] = process.returncode == 0

        # Log stdout for debugging (but truncate if very long)
        if logger and process.stdout:
            stdout_log = process.stdout if len(process.stdout) < 500 else process.stdout[:500] + "... [truncated]"
            logger.debug(f"Command stdout: {stdout_log}")

        if not result["success"] and logger:
            logger.warning(f"Command failed with return code {process.returncode}")
            logger.warning(f"Command: {cmd_str}")
            logger.warning(f"stderr: {process.stderr}")

    except subprocess.TimeoutExpired:
        if logger:
            logger.error(f"Command timed out after {timeout} seconds: {cmd_str}")
        result["stderr"] = f"Command timed out after {timeout} seconds"

    except Exception as e:
        if logger:
            logger.error(f"Error executing command: {cmd_str}")
            logger.error(f"Error details: {str(e)}")
        result["stderr"] = str(e)

    return result