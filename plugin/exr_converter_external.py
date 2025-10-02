#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
External EXR to PNG Converter for YS Guardian
Uses system Python with OpenEXR and Pillow
"""

import sys
import os
import numpy as np
from PIL import Image

# Try to import OpenEXR
try:
    import OpenEXR
    import Imath
    HAS_OPENEXR = True
except ImportError:
    HAS_OPENEXR = False
    print("Warning: OpenEXR not available, will try Pillow only")


def apply_aces_tone_mapping(linear_rgb):
    """Apply ACES RRT/ODT tone mapping approximation
    This approximates the ACES 1.0 SDR Video (REC709/sRGB) view transform
    """
    # ACES RRT/ODT approximation
    # Based on the ACES filmic tone mapping curve
    x = linear_rgb

    # Exposure adjustment (ACES uses 0.6 exposure by default)
    x = x * 0.6

    # ACES tone mapping matrix coefficients
    a = 2.51
    b = 0.03
    c = 2.43
    d = 0.59
    e = 0.14

    # Apply the ACES curve
    result = ((x*(a*x+b))/(x*(c*x+d)+e))

    return np.clip(result, 0, 1)


def acescg_to_linear_srgb(acescg):
    """Convert from ACEScg color space to linear sRGB
    Uses the proper ACEScg to sRGB primaries transformation
    """
    # ACEScg to linear sRGB matrix
    # This matrix accounts for the different primaries between ACEScg and sRGB
    matrix = np.array([
        [ 1.70505, -0.62179, -0.08326],
        [-0.13026,  1.14080, -0.01055],
        [-0.02400, -0.12897,  1.15297]
    ])

    # Reshape for matrix multiplication
    shape = acescg.shape
    pixels = acescg.reshape(-1, 3)

    # Apply the color space transformation
    linear_srgb = np.dot(pixels, matrix.T)

    # Reshape back
    return linear_srgb.reshape(shape)


def apply_redshift_display_transform(linear_rgb):
    """Apply a display transform that mimics Redshift's RenderView
    Combines ACES tone mapping with proper sRGB encoding
    """
    # Step 1: Convert from ACEScg to linear sRGB if needed
    # (Assuming input is in ACEScg space as that's Redshift's default)
    linear_srgb = acescg_to_linear_srgb(linear_rgb)

    # Step 2: Apply ACES tone mapping
    tone_mapped = apply_aces_tone_mapping(linear_srgb)

    # Step 3: Apply sRGB OETF (not simple gamma!)
    # This is the proper sRGB transfer function
    srgb = np.where(
        tone_mapped <= 0.0031308,
        tone_mapped * 12.92,
        1.055 * np.power(tone_mapped, 1.0/2.4) - 0.055
    )

    return np.clip(srgb, 0, 1)


def read_exr_openexr(filepath):
    """Read EXR using OpenEXR library"""
    exr_file = OpenEXR.InputFile(filepath)
    header = exr_file.header()

    # Get image dimensions
    dw = header['dataWindow']
    width = dw.max.x - dw.min.x + 1
    height = dw.max.y - dw.min.y + 1

    # Define channel types
    pt = Imath.PixelType(Imath.PixelType.FLOAT)

    # Read RGB channels (handle different channel names)
    channels = header['channels'].keys()

    # Try to find RGB channels
    if 'R' in channels and 'G' in channels and 'B' in channels:
        r_str = exr_file.channel('R', pt)
        g_str = exr_file.channel('G', pt)
        b_str = exr_file.channel('B', pt)
    elif 'r' in channels and 'g' in channels and 'b' in channels:
        r_str = exr_file.channel('r', pt)
        g_str = exr_file.channel('g', pt)
        b_str = exr_file.channel('b', pt)
    else:
        # Try to get any three channels
        chan_list = list(channels)
        if len(chan_list) >= 3:
            r_str = exr_file.channel(chan_list[0], pt)
            g_str = exr_file.channel(chan_list[1], pt)
            b_str = exr_file.channel(chan_list[2], pt)
        else:
            raise Exception(f"Not enough channels in EXR: {chan_list}")

    # Convert to numpy arrays
    r = np.frombuffer(r_str, dtype=np.float32).reshape((height, width))
    g = np.frombuffer(g_str, dtype=np.float32).reshape((height, width))
    b = np.frombuffer(b_str, dtype=np.float32).reshape((height, width))

    # Stack into RGB image
    rgb = np.stack([r, g, b], axis=-1)

    return rgb


def convert_exr_to_png(exr_path, png_path, color_mode='auto'):
    """Convert EXR to PNG with Redshift-accurate color management

    Args:
        exr_path: Path to input EXR file
        png_path: Path to output PNG file
        color_mode: Color conversion mode
                   'auto' - Detect best mode based on values
                   'aces' - Use ACES display transform (default Redshift)
                   'simple' - Simple gamma 2.2 (legacy)
                   'linear' - No tone mapping, just sRGB encoding
    """
    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(png_path) or '.', exist_ok=True)

        # Try OpenEXR first if available
        if HAS_OPENEXR:
            try:
                print(f"Reading EXR with OpenEXR: {exr_path}")

                # Read the EXR file
                exr_file = OpenEXR.InputFile(exr_path)
                header = exr_file.header()

                # Check for color space metadata in header
                print(f"EXR Header channels: {list(header['channels'].keys())}")

                # Check for any color space attributes
                if 'chromaticities' in header:
                    print(f"Chromaticities found: {header['chromaticities']}")
                if 'whiteLuminance' in header:
                    print(f"White luminance: {header['whiteLuminance']}")

                # Read the image data
                linear_rgb = read_exr_openexr(exr_path)

                # Check value range to understand the data
                min_value = np.min(linear_rgb)
                max_value = np.max(linear_rgb)
                avg_value = np.mean(linear_rgb)
                print(f"EXR value range: min={min_value:.3f}, max={max_value:.3f}, avg={avg_value:.3f}")

                # Determine which color mode to use
                if color_mode == 'auto':
                    # Auto-detect based on value range
                    if max_value > 1.5:
                        actual_mode = 'aces'
                        print(f"Auto-detected HDR content (max={max_value:.2f}), using ACES mode")
                    else:
                        actual_mode = 'linear'
                        print(f"Auto-detected SDR content (max={max_value:.2f}), using linear mode")
                else:
                    actual_mode = color_mode
                    print(f"Using {actual_mode} color mode")

                # Apply the appropriate color transform
                if actual_mode == 'aces':
                    # Full ACES display transform (Redshift default)
                    print("Applying Redshift/ACES display transform...")
                    display_rgb = apply_redshift_display_transform(linear_rgb)

                elif actual_mode == 'simple':
                    # Legacy simple gamma 2.2
                    print("Applying simple gamma 2.2 correction...")
                    display_rgb = np.power(np.clip(linear_rgb, 0, 1), 1.0/2.2)

                elif actual_mode == 'linear':
                    # Just apply sRGB encoding, no tone mapping
                    print("Applying sRGB encoding (no tone mapping)...")
                    display_rgb = np.where(
                        linear_rgb <= 0.0031308,
                        linear_rgb * 12.92,
                        1.055 * np.power(np.clip(linear_rgb, 0, 1), 1.0/2.4) - 0.055
                    )
                    display_rgb = np.clip(display_rgb, 0, 1)

                else:
                    # Default to ACES
                    print(f"Unknown mode '{actual_mode}', defaulting to ACES")
                    display_rgb = apply_redshift_display_transform(linear_rgb)

                # Convert to 8-bit
                rgb_8bit = np.clip(display_rgb * 255, 0, 255).astype(np.uint8)

                # Save with PIL using maximum quality settings
                img = Image.fromarray(rgb_8bit)

                # Save with maximum PNG quality (no compression)
                img.save(png_path, 'PNG',
                        compress_level=0,  # No compression (0-9, 0 is none)
                        optimize=False)    # Don't optimize file size

                print(f"SUCCESS: Converted with ACES display transform to {png_path}")
                return True

            except Exception as e:
                print(f"OpenEXR failed: {e}")
                print("Falling back to PIL...")

        # Fallback to PIL (basic conversion)
        print(f"Reading EXR with PIL: {exr_path}")
        img = Image.open(exr_path)

        print(f"PIL Image mode: {img.mode}, size: {img.size}")

        # Convert to RGB if needed
        if img.mode != 'RGB':
            print(f"Converting from {img.mode} to RGB")
            img = img.convert('RGB')

        # Get image as numpy array for processing
        img_array = np.array(img, dtype=np.float32) / 255.0

        # Check value range for PIL data
        min_val = np.min(img_array)
        max_val = np.max(img_array)
        print(f"PIL data range: min={min_val:.3f}, max={max_val:.3f}")

        # Apply appropriate transform for PIL fallback
        if color_mode == 'aces' or (color_mode == 'auto' and max_val > 0.9):
            print("Applying ACES display transform to PIL data...")
            display_rgb = apply_redshift_display_transform(img_array)
        elif color_mode == 'simple':
            print("Applying simple gamma 2.2 to PIL data...")
            display_rgb = np.power(np.clip(img_array, 0, 1), 1.0/2.2)
        else:
            print("Applying sRGB encoding to PIL data...")
            display_rgb = np.where(
                img_array <= 0.0031308,
                img_array * 12.92,
                1.055 * np.power(np.clip(img_array, 0, 1), 1.0/2.4) - 0.055
            )
            display_rgb = np.clip(display_rgb, 0, 1)

        # Convert back to 8-bit
        rgb_8bit = np.clip(display_rgb * 255, 0, 255).astype(np.uint8)
        img = Image.fromarray(rgb_8bit)

        # Save with maximum quality
        img.save(png_path, 'PNG',
                compress_level=0,
                optimize=False)

        print(f"SUCCESS: Converted with PIL (display transform applied) to {png_path}")
        return True

    except Exception as e:
        print(f"ERROR: Failed to convert: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point for command line usage"""
    if len(sys.argv) < 3:
        print("Usage: python exr_converter_external.py input.exr output.png [color_mode]")
        print("Color modes: auto (default), aces, simple, linear")
        sys.exit(1)

    exr_path = sys.argv[1]
    png_path = sys.argv[2]
    color_mode = sys.argv[3] if len(sys.argv) > 3 else 'auto'

    if not os.path.exists(exr_path):
        print(f"ERROR: Input file not found: {exr_path}")
        sys.exit(1)

    print(f"Converting with color mode: {color_mode}")
    success = convert_exr_to_png(exr_path, png_path, color_mode)

    # Return exit code (0 for success, 1 for failure)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()