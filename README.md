# YS Guardian v1.0

Professional quality control and workflow automation plugin for Cinema 4D production environments.

![YS Guardian Interface](https://github.com/user-attachments/assets/847c6930-f54c-4f7f-86e2-5308f9e0e7bd)

## Overview

YS Guardian monitors your Cinema 4D scenes in real-time, catching common production issues before they cause problems during rendering or client delivery. Built for professional 3D studios, it combines quality monitoring with workflow automation tools designed to streamline production pipelines.

## Core Features

### Quality Monitoring
Five continuous checks protect your production pipeline:

- **Lights Organization** – Validates proper light group structure
- **Visibility Consistency** – Detects viewport/render visibility mismatches
- **Keyframe Validation** – Flags problematic multi-axis animations
- **Camera Shift Detection** – Ensures proper camera framing
- **Render Preset Compliance** – Enforces standardized output settings

Terminal-style status display with color coding provides instant visual feedback. One-click selection of problematic objects accelerates corrections.

### Render Management
Standardized presets with automatic output path organization:

- **Previz** – 1280×720 @ 25fps
- **Pre-Render** – 1920×1080 @ 25fps
- **Render** – 1920×1080 @ 25fps
- **Stills** – 3840×2160 @ 25fps

Force Settings button applies standard resolutions across all presets. Force Vertical converts to 9:16 aspect ratio for social media delivery.

### Workflow Automation

**Layer Management**
- Hierarchy→Layers: Converts scene hierarchy to layer structure
- Solo Layers: Isolates selected layers with one click
- Automatic color coding for lights, cameras, and environment groups

**Scene Tools**
- Vibrate Null: Merges pre-configured null with vibration expression
- Camera Rigs: Three production-ready camera setups (Simple, Shakel, Path)
- Drop to Floor: Accurate Y=0 positioning for rotated/grouped objects

**Stills Management**
Advanced snapshot workflow with automatic color-accurate conversion:
- Captures Redshift RenderView snapshots as EXR
- Converts to PNG with filmic tone mapping
- Organizes output: `Output/[Artist]/YYMMDD/scene_HHMMSS.png`
- Displays in Picture Viewer with metadata

This system maintains professional color accuracy while providing convenient PNG output for client review and archival.

## Installation

### Requirements
- Cinema 4D 2024 or later
- Redshift 3D (for snapshot features)
- Python 3.x with Pillow and NumPy (for EXR conversion)

### Quick Install
```bash
# Run as Administrator
INSTALL_YS_GUARDIAN.bat
```

The installer handles plugin files, Python dependencies, and directory structure automatically. Restart Cinema 4D after installation.

### Redshift Configuration
For snapshot features to function:

1. Open Redshift RenderView → Preferences → Snapshots
2. Set path: `C:/cache/rs snapshots`
3. Enable "Save snapshots as EXR"
4. Click OK

The installer creates the cache directory. This configuration is required for the Save Still feature.

## Usage

### Setup
1. Extensions → YS Guardian
2. Enter artist name (saved per computer)
3. Configure monitoring update rate
4. Set Redshift snapshot format to EXR

### Quality Workflow
Status display shows real-time results:
```
[FAIL] LIGHTS        : 3 lights outside lights group
[WARN] VISIBILITY    : Visibility mismatch on 'RS Spot Light.1'
[ OK ] KEYFRAMES     : Keyframes properly configured
[ OK ] CAMERAS       : Camera shifts at 0%
[ OK ] RENDER_PRESETS: Render presets compliant
```

Click Select buttons to isolate problematic objects for correction.

### Stills Workflow
1. Render preview in Redshift RenderView
2. Take snapshot (Redshift saves to cache as EXR)
3. Click Save Still in YS Guardian
4. PNG appears in organized artist/date folder structure

## Technical Details

### Performance
- Smart caching reduces scene traversal overhead
- Chunked processing for large scenes (1000 objects/cycle)
- Automatic pause during active renders
- Configurable update intervals (100-5000ms)

### Data Persistence
- **Artist Name**: Saved per computer in Cinema 4D preferences
- **Shot ID**: Synced with Take system (Main Take name)
- **Window Layout**: Preserved by Cinema 4D workspace
- **Monitor Settings**: Reset each session

### EXR Conversion
The snapshot system uses external Python with Pillow for color-accurate conversion. This approach maintains professional color fidelity through filmic tone mapping while providing convenient PNG output for review workflows.

## Troubleshooting

**Quality checks not updating**
- Enable Live Monitoring
- Verify update rate ≥100ms
- Check watcher toggles

**Snapshot conversion fails**
- Verify Redshift saves EXR format (not .rssnap2)
- Check Python dependencies: `pip install Pillow numpy`
- Confirm cache directory: `C:\cache\rs snapshots\`

**Layer sync errors**
- Organize objects in top-level null groups
- Ensure unique null names
- Remove orphan objects

**Preset switching issues**
- Confirm lowercase preset names
- Check for duplicate presets
- Use Force Settings to create missing presets

## License

Proprietary software developed by Yambo Studio for professional production use.

## Support

Found a bug or have a feature request? Use the **Report Bug** button in the plugin or visit the [Issues page](https://github.com/yamb0x/ys-guardian/issues/new).

## Links

[GitHub Repository](https://github.com/yamb0x/ys-guardian) · [Report Bug](https://github.com/yamb0x/ys-guardian/issues/new) · [Development Guide](CLAUDE.md)
