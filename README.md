# YS Guardian v1.0.3

Quality control and workflow automation plugin for Cinema 4D production environments — built for Yambo Studio & Friends.

![YS Guardian Interface](https://github.com/user-attachments/assets/847c6930-f54c-4f7f-86e2-5308f9e0e7bd)

## Overview

YS Guardian is a small C4D plugin I built to automate tasks, create shortcuts, and guard our team's workflow inside productions. While parts are specific to our internal setup, a lot of it should be useful for anyone working in C4D.

The plugin monitors your Cinema 4D scenes in real-time, catching common production issues and flags them. Additionally, it has some custom built-in tools for automating your workflow, such as camera rigs (by keyframe wizard Riccardo Bottoni), abc_retime integration (incredible little plugin by Austin Marola & Axis), and other handy C4D tools I built, like Hierarchy→Layers, Solo Layers (like cv-layer-comps but simpler and plays nice with it), Drop to Floor (revived old plugin I liked), and more.

The tool is built for 3D professionals and studios. It combines monitoring with workflow automation tools designed to streamline production pipelines. The tool has some internal parts, but if there's demand, I'm happy to add settings to make it more generalized.

**IMPORTANT**: The plugin installs Python 3.x with Pillow and NumPy on your Windows environment in order to convert EXR to PNG and apply ACES tone mapping.

**Tested on**: Cinema 4D 2024 and Redshift 2025, but should work with newer versions as well (not tested).

## Core Features

### Pipeline Checks

Six continuous checks to keep your C4D files clean (you can choose which warnings to enable):

- **Lights Organization** – Validates proper light group structure
- **Visibility Consistency** – Detects viewport/render visibility mismatches
- **Keyframe Validation** – Flags problematic multi-axis animations
- **Camera Shift Detection** – Ensures proper camera framing
- **Render Preset Compliance** – Enforces standardized output settings (Yambo Studio folder structure only currently)
- **Asset Path Validation** – Detects absolute texture and asset paths that break portability (essential for team collaboration and render farm compatibility)

Status display with color coding provides instant visual feedback. One-click selection of problematic objects helps save clicks on corrections.

### Render Preset Manager

Standardized presets with automatic output path organization:

- **Previz** – 1280×720 @ 25fps
- **Pre-Render** – 1920×1080 @ 25fps
- **Render** – 1920×1080 @ 25fps
- **Stills** – 3840×2160 @ 25fps

**Force Settings** button applies standard resolutions across all presets.
**Force Vertical** converts to 9:16 aspect ratio for social media delivery with one-click AR switch.

### Workflow Automation

**Hierarchy → Layers**
Converts scene hierarchy into a clean layer structure with automatic color coding for lights, cameras, and environment groups.

**Solo Layers**
Isolate selected layers with a single click — a lightweight take on cv-layer-comps that plays nice with it.

**Vibrate Null**
A replacement for the classic Vibrate Tag — consistent results and perfect loops. Merges pre-configured null with vibration expression.

**Camera Rigs**
Three production-ready camera setups (Simple, Shakel, Path) by keyframe wizard **Riccardo Bottoni** (@riccardobottoni). One-click merge into scene.

**Drop to Floor**
Mini-remake of the old favorite plugin for snapping objects onto surfaces. Accurate Y=0 positioning for rotated/grouped objects.

**ABC Retime Shortcut**
Quick access to the excellent Alembic retime tool by **Austin Marola** (@zonedog) and **@axisfx**. One-click tag application for alembic retiming. [GitHub: abc_retime](https://github.com/axisfx2/abc_retime)

### Quick Tools

**Create Hierarchy**
Merges a pre-configured null hierarchy template into the scene. Sets up a clean organizational structure for production scenes in one click.

### Grab Stills

Automatic snapshot workflow with color-accurate conversion using bundled global Python install — capture your work as you go:

- Captures Redshift RenderView snapshots as EXR
- Converts to PNG with ACES RRT/ODT tone mapping
- Organizes output: `Output/[Artist]/YYMMDD/scene_HHMMSS.png` (Yambo Studio folder structure)
- Displays in Picture Viewer with metadata

This system maintains color accuracy by matching your scene's ACES tone mapping, providing convenient PNG output for client review and archival. **Please report if color seems off!**

## Installation

### Requirements

- Cinema 4D 2024 or later
- Redshift 3D (for snapshot features)
- Windows OS (installer handles Python setup automatically)

### Quick Install

```bash
# Run as Administrator
INSTALL_YS_GUARDIAN.bat
```

The installer handles:
- Plugin files → Cinema 4D plugins folder
- Python 3.x + Pillow + NumPy (global install)
- Directory structure creation (`C:\cache\rs snapshots\`)
- ABC Retime plugin integration

**Restart Cinema 4D after installation.**

### Redshift Configuration

For snapshot features to function properly:

1. Open Redshift RenderView → Preferences (gear icon) → Snapshots → Configuration
2. Set path: `C:/cache/rs snapshots`
3. Enable **"Save snapshots as EXR"** (not .rssnap2)
4. Click OK

The installer creates the cache directory automatically. This configuration is required for the Save Still feature.

## Usage

### Initial Setup

1. Extensions → YS Guardian
2. Enter artist name (saved per computer)
3. Configure monitoring update rate (default: 800ms)
4. Verify Redshift snapshot format is set to EXR

### Quality Workflow

Status display shows real-time results:

```
[FAIL] LIGHTS        : 3 lights outside lights group
[WARN] VISIBILITY    : Visibility mismatch on 'RS Spot Light.1'
[ OK ] KEYFRAMES     : Keyframes properly configured
[ OK ] CAMERAS       : Camera shifts at 0%
[ OK ] RENDER_PRESETS: Render presets compliant
```

Click **Select** buttons to isolate problematic objects for quick correction.

### Stills Workflow

1. Render preview in Redshift RenderView
2. Take snapshot in RenderView (Redshift saves to cache as EXR)
3. Click **Save Still** in YS Guardian panel
4. PNG appears in organized artist/date folder structure
5. Opens automatically in Picture Viewer

### Layer Management

**Hierarchy → Layers**:
1. Organize objects into top-level null groups
2. Click **Hierarchy→Layers (2x)** button
3. Plugin creates/syncs layers with automatic color coding

**Solo Layers**:
1. Select layers in Layer Manager
2. Click **Solo (2x)** button
3. Plugin isolates selected layers, hides all others
4. Click again to restore visibility

### Quick Actions

- **Create Hierarchy**: Merges null hierarchy template into scene
- **Vibrate Null**: Merges vibration null into scene
- **Drop to Floor**: Snaps selected objects to Y=0
- **ABC Retime**: Applies Alembic Retime tag to selected cache objects
- **Cam Rigs**: Merge Simple/Shakel/Path camera setups

## Technical Details

### Performance

- Smart caching reduces scene traversal overhead
- Chunked processing for large scenes (1000+ objects/cycle)
- Automatic pause during active renders
- Configurable update intervals (100-5000ms)
- Low memory footprint (~50MB)

### Data Persistence

- **Artist Name**: Saved per computer in Cinema 4D preferences
- **Shot ID**: Synced with Take system (Main Take name)
- **Window Layout**: Preserved by Cinema 4D workspace
- **Monitor Settings**: Reset each session

### EXR Conversion

The snapshot system uses external Python with Pillow for color-accurate conversion. Applies **ACES RRT/ODT display transform** to match Redshift RenderView output, maintaining professional color fidelity while providing convenient PNG output for review workflows.

**Technical Implementation**:
- Reads EXR linear data
- Converts ACEScg → linear sRGB
- Applies ACES RRT/ODT tone mapping
- Encodes to sRGB with proper OETF
- Saves as PNG with maximum quality (no compression)

### Supported Cache Types (ABC Retime)

- Alembic Object
- Alembic Tag
- Point Cache
- Mograph Cache
- X-Particles Cache

## Troubleshooting

**Quality checks not updating**
- Enable **Live Monitoring** checkbox
- Verify update rate ≥100ms
- Check individual watcher toggles (lights, visibility, etc.)

**Snapshot conversion fails**
- Verify Redshift saves EXR format (not .rssnap2)
- Check Python dependencies: `pip install Pillow numpy OpenEXR`
- Confirm cache directory exists: `C:\cache\rs snapshots\`
- Check logs: `C:\YS_Guardian_Output\snapshot_log.txt`

**Layer sync errors**
- Organize objects in top-level null groups (no orphan objects)
- Ensure unique null names
- Remove duplicate layers manually

**Preset switching issues**
- Confirm preset names match: previz, pre_render, render, stills
- Check for duplicate presets in Render Settings
- Use **Force Settings** to create missing presets

**ABC Retime not working**
- Verify selected object is a supported cache type
- Check if tag already exists on object
- Ensure abc_retime plugin is installed in Cinema 4D plugins folder

## Changelog

### v1.0.3 | 16.02.2026

**Changes**:
- **Added Create Hierarchy button** - One-click merge of pre-configured null hierarchy template into scene for quick project setup
- **Removed absolute path popup warning** - The periodic warning dialog that interrupted workflow has been removed. Absolute path status is still shown passively in the panel's ASSET_PATHS row
- **Removed Cam3 (Path) button** - Replaced by Create Hierarchy

### v1.0.2 | 09.11.2025

**Major Fix**:
- **Fixed absolute path detection for node materials** - Previously only detected absolute paths in Redshift materials (type 1036224). Now detects absolute paths in ALL material types including standard Cinema 4D node materials, which use the Maxon node system (`net.maxon`). This was causing the plugin to miss texture paths stored in standard materials.

**Technical Details**:
- Replaced complex node graph traversal (which required Cinema 4D API methods that don't exist) with direct BaseContainer parameter scanning
- Now scans all material parameters for file paths, catching textures regardless of material type or node space configuration
- Detects both forward slash (`D:/path`) and backslash (`D:\path`) absolute path formats
- Added new asset types: `material_texture` and `material_param` for better tracking

**Impact**: The 6th quality check (ASSET_PATHS) now properly detects absolute texture paths in standard Cinema 4D materials, not just Alembic files and Redshift materials. This prevents production issues caused by non-portable asset references.

### v1.0.1 | 11.10.2025

**Bug Fixes**:
- Fixed null print spam in console (removed unnecessary return values from Timer method)
- Corrected stills tone mapping to proper ACES RRT/ODT (was incorrectly labeled as "Filmic")

**Additions**:
- Added abc_retime plugin integration by @zonedog + @axisfx (one-click tag application)
- Updated documentation to reflect accurate ACES tone mapping

**Credits**: Thanks @thodos for the tips ❤️

### v1.0.0 | 10.10.2025

Initial release with:
- Five pipeline quality checks
- Render preset management
- Hierarchy→Layers and Solo Layers
- Vibrate Null, Camera Rigs, Drop to Floor
- Redshift snapshot conversion with ACES tone mapping
- Quick tools (GPT, 3Dsky search)

## License

Proprietary software developed by Yambo Studio for professional production use.
Free for personal and commercial use. Redistribution not permitted without permission.

## Support

**Found a bug or have a feature request?**
Use the **Report Bug** button in the plugin or visit the [Issues page](https://github.com/yamb0x/ys-guardian/issues/new).

**When reporting bugs**, please include:
- Cinema 4D version and Redshift version
- Error description and steps to reproduce
- Logs from: `C:\YS_Guardian_Output\snapshot_log.txt`

## Special Thanks

- **Riccardo Bottoni** (@riccardobottoni) – Camera rigs (Simple, Shakel, Path). The keyframe wizard himself.
- **Austin Marola** (@zonedog) and **@axisfx** – [ABC Retime plugin](https://github.com/axisfx2/abc_retime). Incredible little tool for alembic retiming.
- **Drop to Floor** original creators – Took the concept and rewrote it for modern C4D.
- **@thodos** – For tips that led to v1.0.1 improvements.

## Links

[GitHub Repository](https://github.com/yamb0x/ys-guardian) · [Report Bug](https://github.com/yamb0x/ys-guardian/issues/new) · [Development Guide](CLAUDE.md)

---

**Made with ❤️ at Yambo Studio**
