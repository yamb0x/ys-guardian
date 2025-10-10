# YS Guardian Installation Guide

## Quick Start

1. **Right-click** `INSTALL_YS_GUARDIAN.bat`
2. Select **"Run as Administrator"**
3. Follow the prompts
4. Restart Cinema 4D 2024

That's it! The installer handles everything automatically and keeps the window open to show results.

## Diagnostic Tool

If you have issues with Python or EXR conversion:
- Run `TEST_PYTHON_SETUP.bat` to diagnose Python installation problems

## What the Installer Does

1. **Checks Prerequisites**
   - Verifies Administrator privileges
   - Confirms Cinema 4D 2024 is installed
   - Validates all source files are present

2. **Installs Plugin Files**
   - Main plugin: `ys_guardian_panel.pyp`
   - Snapshot manager
   - EXR to PNG converters
   - Python configuration helper

3. **Sets Up Directories**
   - Plugin directory: `C:\Program Files\Maxon Cinema 4D 2024\plugins\YS_Guardian\`
   - Output directory: `C:\YS_Guardian_Output\`
   - Cache directory: `C:\cache\rs snapshots\`

4. **Handles Python Setup**
   - Automatically detects Python installation
   - Offers to install Python if not found
   - Installs required packages (Pillow, NumPy)

## Python Detection Methods

The installer uses multiple methods to find Python:

1. **py launcher** (most reliable on Windows)
2. **python/python3 commands** (if in PATH)
3. **Common installation directories**:
   - `C:\Program Files\Python*`
   - `%LocalAppData%\Programs\Python\Python*`
4. **Registry check** (fallback)

## Required Redshift Configuration

For the snapshot feature to work:

1. Open **Redshift RenderView**
2. Click **Preferences** (gear icon)
3. Go to **Snapshots → Configuration**
4. Set path to: `C:/cache/rs snapshots`
5. Enable **"Save snapshots as EXR"**
6. Click **OK**

## Troubleshooting

### "Administrator privileges required"
- You must right-click and select "Run as Administrator"

### "Python not found"
- The installer will offer to download and install Python automatically
- Or install manually from https://www.python.org (check "Add to PATH")

### "Cinema 4D 2024 not found"
- The installer expects C4D at: `C:\Program Files\Maxon Cinema 4D 2024\`
- If installed elsewhere, edit the `INSTALL_YS_GUARDIAN.bat` file

### Window closes immediately
- Use `RUN_INSTALLER.bat` instead - it keeps the window open

### EXR conversion not working
- Run `TEST_PYTHON_SETUP.bat` to diagnose Python issues
- Ensure Pillow and NumPy are installed
- Check Windows Store app aliases aren't interfering

## File Structure After Installation

```
C:\Program Files\Maxon Cinema 4D 2024\plugins\YS_Guardian\
├── ys_guardian_panel.pyp          (main plugin)
├── redshift_snapshot_manager_fixed.py
├── exr_to_png_converter_simple.py
├── exr_converter_external.py
├── python_path_config.py
├── c4d\
│   └── VibrateNull.c4d
└── icons\
    └── ys-logo-alpha-32.png

C:\YS_Guardian_Output\              (output directory)
└── snapshot_log.txt

C:\cache\rs snapshots\              (Redshift snapshots)
```

## Uninstalling

To uninstall the plugin:

1. Delete the folder: `C:\Program Files\Maxon Cinema 4D 2024\plugins\YS_Guardian\`
2. Optionally delete: `C:\YS_Guardian_Output\`
3. Optionally delete: `C:\cache\rs snapshots\`

## Support

For issues or questions:
- Check the log file: `%TEMP%\ys_guardian_install.log`
- Contact the YS Guardian development team