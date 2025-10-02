# YS Guardian

YS Guardian is a production quality control plugin for Cinema 4D that monitors scenes in real-time for common pipeline issues and provides workflow automation tools for professional 3D production environments.

**Key features:** Real-time quality monitoring · Render preset management · Artist tracking · Workflow automation tools

![YS Guardian Interface](https://github.com/user-attachments/assets/847c6930-f54c-4f7f-86e2-5308f9e0e7bd)

## Quality Monitoring

YS Guardian performs continuous scene validation across five critical production areas:

| Check | Purpose | Detection |
|-------|---------|-----------|
| **Lights Organization** | Ensures proper scene hierarchy | Identifies lights outside designated groups |
| **Visibility Consistency** | Prevents render surprises | Detects viewport/render visibility mismatches |
| **Keyframe Validation** | Maintains animation integrity | Flags multi-axis position/rotation keyframes |
| **Camera Shift Detection** | Ensures proper framing | Alerts on non-zero camera shift values |
| **Render Preset Compliance** | Standardizes output settings | Validates against approved preset names |

Each check provides:
- Terminal-style status display with color coding
- Issue count and detailed messages
- One-click selection of problematic objects
- Real-time updates with configurable intervals

## Render Management

### Preset System
Fast switching between standardized render configurations with automatic output path management:

- **Previz**: 1280×720 @ 25fps → `output/previz/_Shots/$take/`
- **Pre-Render**: 1920×1080 @ 25fps → `output/pre_render/_Shots/$take/v01/`
- **Render**: 1920×1080 @ 25fps → `output/render/_Shots/$take/v01/`
- **Stills**: 3840×2160 @ 25fps → `output/stills/_Shots/$take/v01/`

**Force Settings**: Apply standard resolutions and framerates to all presets
**Force Vertical**: Convert all presets to 9:16 aspect ratio (720×1280, 1080×1920, 2160×3840) for social media delivery

### Shot Tracking
- Syncs with Cinema 4D's Take system
- Shot ID automatically updates from Main Take name
- Output paths use Take-based naming for organized rendering

## Workflow Automation

### Layer Management
**Hierarchy→Layers**: Automatically creates layer structure from scene hierarchy
- Scans top-level null objects in Object Manager
- Creates or updates matching layers in Layer Manager
- Assigns nulls and all children to corresponding layers
- Validates scene organization (rejects objects outside null groups)
- Applies color coding for common group types (lights, cameras, environment)

**Solo Layers**: Layer isolation workflow
- Solo selected layers (hide all others)
- Click again to restore all layers
- Disables unassigned objects during solo mode
- Full undo support for all layer operations

### Scene Tools
**Vibrate Null**: Merges pre-configured null with vibration expression
**Basic Cam Rig**: Creates camera with null parent for animation control
**Drop to Floor**: Positions selected objects at Y=0 using accurate bounding box calculation
- Handles rotated, scaled, and grouped objects correctly
- Batch processing for multiple selections
- Silent operation with console feedback only

### External Integration
**Search 3D Model**: Quick access to 3dsky.org library search
**Ask ChatGPT**: Opens ChatGPT with pre-formatted prompt for Cinema 4D Python Tag scripts
- Includes technical director role definition
- Cinema 4D 2024 API specifications
- Production-safe code requirements

## Stills Management

**Save Still**: Captures and converts Redshift RenderView snapshots
- Locates latest EXR in Redshift cache directory
- Converts to PNG with filmic tone mapping
- Saves to organized artist/date folder structure: `Output/[Artist]/YYMMDD/scene_HHMMSS.png`
- Displays image in Picture Viewer with resolution and aspect ratio info

**Open Folder**: Direct access to artist's dated output directory

**Requirements**: Redshift must save snapshots as EXR format (not .rssnap2)

## Monitoring Controls

- **Update Rate**: Configurable check interval (100-5000ms)
- **Watcher Toggles**: Enable/disable individual quality checks
- **Mute All**: Temporarily suspend all checks
- **Live Status**: Terminal-style display with color-coded status messages

## Installation

### Requirements
- Cinema 4D 2024 or later
- Redshift 3D (for snapshot features)
- Python 3.x with `OpenEXR` and `Pillow` packages (for EXR conversion)

### Automated Installation
```bash
# Navigate to installers directory
cd installers

# Run installation script as Administrator
INSTALL_YS_GUARDIAN.bat
```

Restart Cinema 4D after installation completes.

### Manual Installation
Copy plugin files to Cinema 4D plugins directory:
```
C:\Program Files\Maxon Cinema 4D 2024\plugins\YS_Guardian\
├── plugin\
│   └── ys_guardian_panel.pyp
├── icons\
│   └── [status and toggle icons]
└── c4d\
    └── VibrateNull.c4d
```

### Python Dependencies
```bash
pip install OpenEXR-Python Pillow numpy
```

## Usage

### Setup
1. Open panel: **Extensions → YS Guardian**
2. Enter artist name (saved per computer)
3. Set monitoring update rate (default: 1000ms)
4. Configure Redshift to save snapshots as EXR format

### Quality Monitoring Workflow
The status display uses terminal-style formatting:
```
[FAIL] LIGHTS        : 3 lights outside lights group
[WARN] VISIBILITY    : Visibility mismatch on 'RS Spot Light.1'
[ OK ] KEYFRAMES     : Keyframes properly configured
[ OK ] CAMERAS       : Camera shifts at 0%
[ OK ] RENDER_PRESETS: Render presets compliant
```

Click **Select** buttons to select problematic objects for correction.

### Layer Workflow
1. Organize scene into top-level null groups
2. Click **Hierarchy→Layers** to create matching layer structure
3. Use **Solo Layers** to isolate specific layers during work
4. Click **Solo Layers** again to restore full scene visibility

### Stills Capture
```
1. Render preview in Redshift RenderView
2. Take snapshot (Redshift saves to cache as EXR)
3. Click "Save Still" in YS Guardian
4. PNG output: Output/[Artist]/YYMMDD/scene_HHMMSS.png
```

## Technical Details

### Performance Optimization
- **Smart Caching**: Results cached for 500ms to reduce scene traversal
- **Chunked Processing**: Maximum 1000 objects per check cycle
- **Early Exit**: Stops after 50 issues detected per check
- **Throttled Updates**: Minimum 50ms between UI redraws
- **Render Detection**: Automatically pauses monitoring during active renders

### Data Persistence

| Data | Storage Location | Scope |
|------|-----------------|-------|
| Artist Name | `%AppData%/MAXON/prefs/ys_guardian_settings.json` | Per computer |
| Window Layout | Cinema 4D layout system | Per workspace |
| Shot ID | Take system (Main Take name) | Per document |
| Active Preset | Render data settings | Per document |
| Monitor State | Runtime only | Per session |

## Troubleshooting

### Common Issues

**Quality checks not updating**
- Verify "Live Monitoring" is enabled
- Check update rate setting (minimum 100ms)
- Ensure watchers are not muted

**Snapshot conversion fails**
- Verify Redshift saves snapshots as EXR (not .rssnap2)
- Check Python dependencies: `pip install OpenEXR-Python Pillow`
- Verify cache directory exists: `C:\cache\rs snapshots\`

**Layer sync errors**
- Ensure all objects are organized in top-level null groups
- Check that nulls have unique names
- Verify no orphan objects exist outside nulls

**Preset switching not working**
- Confirm preset exists with exact lowercase name
- Check render data list for duplicate presets
- Use "Force Settings" to create missing presets

### Redshift Configuration
```
RenderView → Options → Snapshot Settings
├── Format: EXR (not .rssnap2)
├── Path: C:\cache\rs snapshots\
└── Auto-increment: Enabled
```

## License

Proprietary software developed by Yambo Studio for internal production use.

## Links

[GitHub Repository](https://github.com/yamb0x/ys-guardian) · [Report Issues](https://github.com/yamb0x/ys-guardian/issues) · [Development Guide](CLAUDE.md)