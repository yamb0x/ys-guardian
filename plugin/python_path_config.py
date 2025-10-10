# -*- coding: utf-8 -*-
"""
Python Path Configuration for YS Guardian
This file stores the working Python path after it's been discovered
"""

import os
import glob
import subprocess

def find_working_python():
    """
    Find a working Python installation on Windows
    Returns the full path to python.exe or None if not found
    """
    python_commands = []

    # Check Program Files for official Python installations
    for pattern in [r"C:\Program Files\Python*\python.exe",
                    r"C:\Program Files (x86)\Python*\python.exe"]:
        python_commands.extend([os.path.normpath(p) for p in glob.glob(pattern)])

    # Check user local installations
    user_local = os.path.expanduser("~")
    patterns = [
        os.path.join(user_local, r"AppData\Local\Programs\Python\Python*\python.exe"),
        os.path.join(user_local, r"AppData\Local\Microsoft\Python*\python.exe")
    ]
    for pattern in patterns:
        python_commands.extend([os.path.normpath(p) for p in glob.glob(pattern)])

    # Also check common locations
    common_paths = [
        r"C:\Python311\python.exe",
        r"C:\Python310\python.exe",
        r"C:\Python39\python.exe",
        r"C:\Python38\python.exe",
        r"C:\Python\python.exe"
    ]
    python_commands.extend([os.path.normpath(p) for p in common_paths if os.path.exists(p)])

    # Test each Python to see if it actually works
    for python_exe in python_commands:
        if os.path.exists(python_exe):
            try:
                # Test if this Python actually works
                result = subprocess.run(
                    [python_exe, "-c", "import sys; print(sys.version)"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0 and "Python" in result.stdout:
                    # Test if required packages are installed
                    packages_ok = True
                    for package in ['PIL', 'numpy', 'OpenEXR']:
                        pkg_test = subprocess.run(
                            [python_exe, "-c", f"import {package}"],
                            capture_output=True,
                            timeout=5
                        )
                        if pkg_test.returncode != 0:
                            # Try to install the package
                            try:
                                install_result = subprocess.run(
                                    [python_exe, "-m", "pip", "install",
                                     "Pillow" if package == "PIL" else package],
                                    capture_output=True,
                                    timeout=60
                                )
                                if install_result.returncode != 0:
                                    packages_ok = False
                            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                                packages_ok = False  # Package installation failed

                    if packages_ok:
                        return python_exe
            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                continue  # Python test failed, try next candidate

    # Try PATH commands as last resort
    for cmd in ["py", "python3", "python"]:
        try:
            result = subprocess.run(
                [cmd, "-c", "import sys; print(sys.executable)"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.SubprocessError):
            continue  # Command not found, try next

    return None

def get_python_path():
    """
    Get the cached Python path or find a new one
    """
    # Check if we have a cached path
    cache_file = os.path.join(os.path.dirname(__file__), ".python_path_cache")

    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cached_path = f.read().strip()
                # Normalize the cached path to use backslashes
                cached_path = os.path.normpath(cached_path)
                # Verify the cached path still works
                if os.path.exists(cached_path):
                    result = subprocess.run(
                        [cached_path, "--version"],
                        capture_output=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        return cached_path
        except (IOError, OSError, subprocess.SubprocessError):
            # If cache is corrupt, delete it
            try:
                os.remove(cache_file)
            except (IOError, OSError):
                pass  # Cache file deletion failed, continue anyway

    # Find a working Python
    python_path = find_working_python()

    # Cache the result if found (already normalized from find_working_python)
    if python_path:
        try:
            # Ensure it's normalized before caching
            python_path = os.path.normpath(python_path)
            with open(cache_file, 'w') as f:
                f.write(python_path)
        except (IOError, OSError):
            pass  # Failed to cache path, continue anyway

    return python_path

# Export the working Python path
PYTHON_EXE = get_python_path()