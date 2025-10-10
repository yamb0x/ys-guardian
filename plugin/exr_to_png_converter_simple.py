# -*- coding: utf-8 -*-
"""
Simplified EXR to PNG Converter for Cinema 4D Environment
Uses minimal dependencies that should work in C4D's Python environment
"""

import os

# Performance optimization: Cache discovered Python path across conversions
_CACHED_PYTHON_PATH = None

def convert_exr_to_png(exr_path, png_path, **kwargs):
    """
    Simplified converter that works with Cinema 4D's limited Python environment
    Uses external Python converter if available
    """
    try:
        log_file = r"C:\YS_Guardian_Output\snapshot_log.txt"

        # Get color mode from kwargs (default to 'aces' for Redshift accuracy)
        color_mode = kwargs.get('color_mode', 'aces')

        # Log the attempt
        try:
            with open(log_file, 'a') as f:
                from datetime import datetime
                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Simple converter: Attempting conversion\n")
                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Color mode: {color_mode}\n")
        except (IOError, OSError):
            pass  # Log file not accessible, continue anyway

        # First, try to use external Python converter if available
        import subprocess

        # Import our Python path finder
        try:
            from python_path_config import PYTHON_EXE
        except ImportError:
            PYTHON_EXE = None  # python_path_config module not available

        # Try to find the external converter in the same directory as this module
        current_dir = os.path.dirname(os.path.abspath(__file__))
        external_converter = os.path.join(current_dir, "exr_converter_external.py")

        # If not found in current dir, try the installed plugin location
        if not os.path.exists(external_converter):
            plugin_dir = r"C:\Program Files\Maxon Cinema 4D 2024\plugins\YS_Guardian"
            external_converter = os.path.join(plugin_dir, "exr_converter_external.py")

        if os.path.exists(external_converter):
            try:
                with open(log_file, 'a') as f:
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Found external converter, using system Python...\n")

                # Performance optimization: Use cached Python path if available
                global _CACHED_PYTHON_PATH
                if _CACHED_PYTHON_PATH and os.path.exists(_CACHED_PYTHON_PATH):
                    try:
                        with open(log_file, 'a') as f:
                            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Using cached Python path: {_CACHED_PYTHON_PATH}\n")

                        # Try cached Python directly - skip all tests
                        result = subprocess.run(
                            [_CACHED_PYTHON_PATH, external_converter, exr_path, png_path, color_mode],
                            capture_output=True,
                            text=True,
                            timeout=30
                        )

                        # Check if conversion was successful
                        if result.returncode == 0 and os.path.exists(png_path):
                            with open(log_file, 'a') as f:
                                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] SUCCESS: Cached Python worked! (Fast path)\n")
                            return True
                        else:
                            # Cached Python failed, clear cache and fallback to discovery
                            with open(log_file, 'a') as f:
                                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Cached Python failed, falling back to discovery...\n")
                            _CACHED_PYTHON_PATH = None
                    except Exception as e:
                        with open(log_file, 'a') as f:
                            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Cached Python error: {e}, falling back...\n")
                        _CACHED_PYTHON_PATH = None

                # Build list of Python commands to try
                python_commands = []

                # Priority 1: Use our cached/discovered Python path if available
                if PYTHON_EXE and os.path.exists(PYTHON_EXE):
                    python_commands.append(PYTHON_EXE)
                    with open(log_file, 'a') as f:
                        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Using cached Python: {PYTHON_EXE}\n")

                # Priority 2: Check for actual Python installations in common locations
                import glob

                # Check Program Files for official Python installations
                for pattern in [r"C:\Program Files\Python*\python.exe",
                              r"C:\Program Files (x86)\Python*\python.exe"]:
                    for python_exe in glob.glob(pattern):
                        # Normalize path to use backslashes
                        python_exe = os.path.normpath(python_exe)
                        if os.path.exists(python_exe) and python_exe not in python_commands:
                            python_commands.append(python_exe)

                # Check user local installations
                user_local = os.path.expanduser("~")
                pattern = os.path.join(user_local, r"AppData\Local\Programs\Python\Python*\python.exe")
                for python_exe in glob.glob(pattern):
                    # Normalize path to use backslashes
                    python_exe = os.path.normpath(python_exe)
                    if os.path.exists(python_exe) and python_exe not in python_commands:
                        python_commands.append(python_exe)

                # Priority 3: Try standard commands (but these might be Store redirects)
                python_commands.extend(["py", "python3", "python"])

                result = None
                working_python = None

                for python_cmd in python_commands:
                    try:
                        # Test if this Python command actually works (not Store redirect)
                        # Use a robust test that checks for version pattern (e.g., "3.13.7")
                        test_cmd = [python_cmd, "-c", "import sys; print(sys.version)"]
                        test_result = subprocess.run(
                            test_cmd,
                            capture_output=True,
                            text=True,
                            timeout=5
                        )

                        # Check for success: return code 0 AND output contains version pattern
                        # Version pattern: digit.digit (e.g., "3.13", "2.7", "3.11")
                        import re
                        has_version = bool(re.search(r'\d+\.\d+', test_result.stdout))

                        if test_result.returncode == 0 and has_version and test_result.stdout.strip():
                            # Python executable works! Now verify it can handle EXR conversion
                            # Check if Pillow is available (needed for image processing)
                            lib_test = subprocess.run(
                                [python_cmd, "-c", "import PIL; print('OK')"],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )

                            if lib_test.returncode == 0 and "OK" in lib_test.stdout:
                                with open(log_file, 'a') as f:
                                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] Found working Python: {python_cmd}\n")
                                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Version: {test_result.stdout.strip()}\n")
                                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] PIL available: Yes\n")

                                working_python = python_cmd

                                # Call external Python with the converter script and color mode
                                result = subprocess.run(
                                    [python_cmd, external_converter, exr_path, png_path, color_mode],
                                    capture_output=True,
                                    text=True,
                                    timeout=30
                                )

                                # Performance optimization: Cache successful Python path for next conversion
                                if result.returncode == 0:
                                    _CACHED_PYTHON_PATH = python_cmd
                                    with open(log_file, 'a') as f:
                                        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Cached Python path for future conversions\n")
                            else:
                                # Python works but Pillow not installed - log and continue
                                with open(log_file, 'a') as f:
                                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] [WARNING] Python works but PIL/Pillow not installed: {python_cmd}\n")
                                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}]   Install with: {python_cmd} -m pip install Pillow\n")
                                continue  # Try next Python

                            # Log the result
                            with open(log_file, 'a') as f:
                                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Converter returned: {result.returncode}\n")
                                if result.stdout:
                                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] STDOUT: {result.stdout}\n")
                                if result.stderr:
                                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] STDERR: {result.stderr}\n")

                            break  # Found working Python, exit loop
                        else:
                            # Test failed, log why with detailed diagnostics
                            with open(log_file, 'a') as f:
                                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] [FAIL] Test failed for: {python_cmd}\n")
                                f.write(f"[{datetime.now().strftime('%H:%M:%S')}]   Return code: {test_result.returncode}\n")
                                f.write(f"[{datetime.now().strftime('%H:%M:%S')}]   Has version pattern: {has_version}\n")
                                f.write(f"[{datetime.now().strftime('%H:%M:%S')}]   Output: {test_result.stdout[:100]}\n")
                                if test_result.stderr:
                                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}]   Stderr: {test_result.stderr[:200]}\n")
                    except Exception as e:
                        # Catch ALL exceptions and log them
                        with open(log_file, 'a') as f:
                            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Exception testing {python_cmd}: {str(e)}\n")
                        continue  # Try next Python command

                if result is None:
                    with open(log_file, 'a') as f:
                        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] ========================================\n")
                        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: No usable Python installation found\n")
                        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] ========================================\n")
                        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Tested {len(python_commands)} Python locations\n")
                        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] \n")
                        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] SOLUTION OPTIONS:\n")
                        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] 1. Install Pillow in existing Python:\n")
                        if working_python:
                            f.write(f"[{datetime.now().strftime('%H:%M:%S')}]    {working_python} -m pip install Pillow numpy OpenImageIO\n")
                        else:
                            f.write(f"[{datetime.now().strftime('%H:%M:%S')}]    py -m pip install Pillow numpy OpenImageIO\n")
                        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] 2. Or run: INSTALL_YS_GUARDIAN.bat as Administrator\n")
                        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] ========================================\n")
                    # Continue to fallback methods
                else:
                    # We have a result from subprocess.run
                    # Log the output
                    with open(log_file, 'a') as f:
                        if result.stdout:
                            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] External converter output: {result.stdout}\n")
                        if result.stderr:
                            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] External converter errors: {result.stderr}\n")

                    # Check if conversion was successful
                    if result.returncode == 0 and os.path.exists(png_path):
                        with open(log_file, 'a') as f:
                            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] SUCCESS: External conversion worked!\n")
                            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Output file: {png_path}\n")
                        return True
                    else:
                        with open(log_file, 'a') as f:
                            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] External converter failed with code {result.returncode}\n")

            except subprocess.TimeoutExpired:
                with open(log_file, 'a') as f:
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] External converter timed out\n")
            except Exception as e:
                with open(log_file, 'a') as f:
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] External converter error: {e}\n")
        else:
            with open(log_file, 'a') as f:
                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] External converter not found at: {external_converter}\n")

        # Fallback: Check if we can import PIL (often available in C4D)
        try:
            from PIL import Image

            # Try to read the EXR directly with PIL (might work for some EXR files)
            try:
                with open(log_file, 'a') as f:
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Fallback: Trying PIL direct read...\n")

                img = Image.open(exr_path)
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Ensure output directory exists
                os.makedirs(os.path.dirname(png_path), exist_ok=True)

                # Save as PNG with maximum quality
                img.save(png_path, 'PNG', compress_level=0, optimize=False)

                with open(log_file, 'a') as f:
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] SUCCESS: PIL conversion worked!\n")

                return True

            except Exception as e:
                with open(log_file, 'a') as f:
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] PIL failed: {e}\n")

        except ImportError:
            with open(log_file, 'a') as f:
                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] PIL not available in C4D\n")

        # If we get here, we couldn't convert the file
        # As a last resort, create a placeholder text file explaining the issue
        try:
            os.makedirs(os.path.dirname(png_path), exist_ok=True)

            placeholder_path = png_path.replace('.png', '_NEEDS_CONVERSION.txt')
            with open(placeholder_path, 'w') as f:
                f.write(f"EXR to PNG Conversion Required\n")
                f.write(f"=" * 40 + "\n")
                f.write(f"Source EXR: {exr_path}\n")
                f.write(f"Target PNG: {png_path}\n")
                f.write(f"\n")
                f.write(f"PROBLEM: No working Python installation found!\n")
                f.write(f"The plugin tried: py, python3, python\n")
                f.write(f"\n")
                f.write(f"QUICK FIX - Install Python:\n")
                f.write(f"1. Go to: https://www.python.org/downloads/\n")
                f.write(f"2. Download Python 3.11 or later\n")
                f.write(f"3. During installation, CHECK 'Add Python to PATH'\n")
                f.write(f"4. Open Command Prompt and run:\n")
                f.write(f"   py -m pip install Pillow numpy\n")
                f.write(f"5. Rerun the YS Guardian installer\n")
                f.write(f"\n")
                f.write(f"Alternative Solutions:\n")
                f.write(f"- Convert manually using external tool\n")
                f.write(f"- Use Redshift's built-in export to PNG instead of EXR\n")

            with open(log_file, 'a') as f:
                from datetime import datetime
                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Created placeholder file: {placeholder_path}\n")

            # Return False but with helpful information logged
            return False

        except Exception as e:
            with open(log_file, 'a') as f:
                from datetime import datetime
                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Failed to create placeholder: {e}\n")
            return False

    except Exception as e:
        try:
            with open(log_file, 'a') as f:
                from datetime import datetime
                import traceback
                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Simple converter error: {e}\n")
                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Traceback: {traceback.format_exc()}\n")
        except (IOError, OSError):
            pass  # Failed to write error log, but continue
        return False

def get_converter_info():
    """Get information about converter status"""
    return {
        'available': True,
        'method': 'simple/PIL fallback',
        'libraries': 'Minimal dependencies'
    }