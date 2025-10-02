# -*- coding: utf-8 -*-
"""
Simplified EXR to PNG Converter for Cinema 4D Environment
Uses minimal dependencies that should work in C4D's Python environment
"""

import os

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
        except:
            pass

        # First, try to use external Python converter if available
        import subprocess
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

                # Call external Python with the converter script and color mode
                result = subprocess.run(
                    ["python", external_converter, exr_path, png_path, color_mode],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

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
                f.write(f"The EXR file exists but couldn't be converted to PNG\n")
                f.write(f"because Cinema 4D's Python environment lacks the\n")
                f.write(f"required image processing libraries.\n")
                f.write(f"\n")
                f.write(f"Solutions:\n")
                f.write(f"1. Install libraries in C4D's Python:\n")
                f.write(f"   cd 'C:\\Program Files\\Maxon Cinema 4D 2024\\resource\\modules\\python\\libs\\win64'\n")
                f.write(f"   python.exe -m pip install Pillow\n")
                f.write(f"\n")
                f.write(f"2. Convert manually using external tool\n")
                f.write(f"\n")
                f.write(f"3. Use Redshift's built-in export to PNG instead of EXR\n")

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
        except:
            pass
        return False

def get_converter_info():
    """Get information about converter status"""
    return {
        'available': True,
        'method': 'simple/PIL fallback',
        'libraries': 'Minimal dependencies'
    }