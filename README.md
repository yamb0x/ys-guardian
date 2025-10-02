# YS Guardian v1.0 - Cinema 4D Production Quality Control Plugin

**Professional production quality control and automation toolkit for Cinema 4D 2024 with Redshift 3D**

## 🎯 Overview
YS Guardian is a comprehensive quality control plugin that acts as a real-time watchdog for Cinema 4D production workflows. It continuously monitors your scene for common production issues, automates repetitive tasks, and ensures consistency across team projects.

## ✨ Features

### 🔍 Real-Time Quality Monitoring
The plugin performs **5 critical quality checks** with visual status indicators:

- **🔦 Lights Organization** - Detects lights not properly organized in "lights" or "lighting" groups
- **👁 Visibility Consistency** - Catches viewport/render visibility mismatches that cause render surprises
- **🔑 Keyframe Sanity** - Warns about multi-axis keyframes that can cause animation issues
- **📷 Camera Shift Detection** - Alerts when cameras have non-zero shift values
- **📋 Render Preset Validation** - Ensures only approved presets exist (previz, pre_render, render, stills)

Each check displays:
- Visual icon indicator
- Count of issues found
- Color-coded status bars with rounded corners
- One-click selection of problematic objects

### 🎬 Production Management

#### Shot & Artist Tracking
- **Shot ID Management** - Syncs with Cinema 4D's Take system for consistent naming
- **Artist Name Persistence** - Saves per computer/user for automatic identification
- **Organized Output Structure** - Creates dated folders per artist

#### Render Preset System
- **Quick Preset Switching** - One-click tabs for previz, pre_render, render, and stills
- **Force Settings** - Apply standardized resolution/framerate per preset
- **Force Vertical** - Instantly convert all presets to 9:16 for social media (Reels/Stories)
- **Visual Active Preset** - Shows which preset is currently active

### 🛠 Quick Actions Toolbar
**8 powerful tools in a 4x2 grid layout:**

**Row 1 - Selection Tools:**
- **Select Bad Lights** - Select all lights outside proper groups
- **Select Bad Visibility** - Select objects with visibility issues
- **Select Keyframe Issues** - Select objects with multi-axis keyframes
- **Select Bad Cameras** - Select cameras with shift problems

**Row 2 - Creation Tools:**
- **Vibrate Null** - Creates null with randomized vibration expression
- **Basic Cam Rig** - Creates camera with null parent for easy animation
- **YS-Alembic Browser** - Quick access to asset browser
- **Plugin Info** - Displays detailed status and troubleshooting info

### 📸 Stills Management
- **Save Still** - Captures RenderView snapshots (EXR format)
- **Automatic Conversion** - Converts EXR to PNG with HDR tone mapping
- **Organized Storage** - `Output/ArtistName/YYMMDD/scenename_HHMMSS.png`
- **Open Folder** - Quick access to your stills folder

### 🎛 Monitoring Controls
- **Live Monitoring Toggle** - Enable/disable real-time quality checking
- **Update Rate Control** - Adjustable check interval (100-5000ms)
- **Active Watchers Tabs** - Individual toggle for each quality check
- **Mute All** - Temporarily disable all checks without losing settings

## 📦 Installation

### Prerequisites
- **Cinema 4D 2024** or later
- **Redshift 3D** renderer (for snapshot features)
- **Python 3.x** with packages: `Pillow`, `OpenEXR`, `numpy` (for EXR conversion)

### One-Click Installation
1. Navigate to `installers/` folder
2. Right-click `INSTALL_YS_GUARDIAN.bat` → **Run as Administrator**
3. Follow the prompts
4. Restart Cinema 4D

### Manual Installation
Copy the following to `C:\Program Files\Maxon Cinema 4D 2024\plugins\YS_Guardian\`:
```
plugin/
├── ys_guardian_panel.pyp          # Main plugin file
├── redshift_snapshot_manager_fixed.py
├── exr_to_png_converter_simple.py
└── exr_converter_external.py
icons/                              # All UI icons
```

## 🚀 Usage

### Opening the Panel
**Extensions → YS Guardian** or assign a keyboard shortcut for quick access

### Initial Setup
1. **Enter Artist Name** - Automatically saved per computer
2. **Configure Monitoring** - Enable/disable specific quality checks
3. **Set Update Rate** - Default 800ms (8 x 100ms)
4. **Configure Redshift** - Set snapshot format to EXR

### Daily Workflow

#### Quality Monitoring
- **Green Status** = All clear ✅
- **Orange/Red Status** = Issues detected with count
- **Click Status Bar** = Select problematic objects
- **Toggle Watchers** = Focus on specific checks

#### Preset Management
1. Click preset tabs to switch render settings
2. Use "Force Settings" to standardize resolutions
3. Use "Force Vertical" for social media format

#### Taking Stills
1. Render in Redshift RenderView
2. Click "Save Still" in YS Guardian
3. Find organized PNG in your dated folder

### Output Structure
```
Project_Folder/
└── Output/
    └── [Artist_Name]/
        └── [YYMMDD]/
            ├── scene1_143022.png  (14:30:22)
            ├── scene1_144511.png  (14:45:11)
            └── scene1_151203.png  (15:12:03)
```

## 🔧 Advanced Features

### Render Preset Standards

| Preset | Resolution | FPS | Purpose |
|--------|------------|-----|---------|
| **previz** | 1280×720 | 25 | Quick previews, animatics |
| **pre_render** | 1920×1080 | 25 | Client reviews, WIP |
| **render** | 1920×1080 | 25 | Final delivery |
| **stills** | 3840×2160 | 25 | High-res stills |

**Vertical Mode (9:16):**
| Preset | Resolution | Platform |
|--------|------------|----------|
| **previz** | 720×1280 | Stories/Reels test |
| **pre_render** | 1080×1920 | Instagram/TikTok |
| **render** | 1080×1920 | Final vertical |
| **stills** | 2160×3840 | 4K vertical |

### Performance Optimization
- **Smart Caching** - Results cached for 500ms
- **Chunked Processing** - Max 1000 objects per check
- **Early Exit** - Stops after 50 issues found
- **Render Pause** - Automatically pauses during renders

## ⚠️ Troubleshooting

### Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| **Quality checks not updating** | Enable "Live Monitoring", check update rate |
| **Can't select problematic objects** | Click the status bar, not the icon |
| **Snapshot conversion fails** | Run `installers/external_converter_setup.bat` |
| **Plugin not showing** | Restart C4D after installation |
| **Preset not switching** | Ensure preset exists with exact name |

### Redshift Snapshot Setup
1. **Redshift RenderView** → **Options** → **Snapshot Settings**
2. Set format to **EXR** (not .rssnap2)
3. Set path to `C:\cache\rs snapshots\`
4. Enable "Auto-increment filename"

### Python Dependencies
```bash
# Install required packages
pip install Pillow OpenEXR numpy

# Verify installation
python -c "import PIL, OpenEXR, numpy; print('All packages installed')"
```

## 👥 Team Deployment

### For IT/Pipeline
1. Clone repository to network location
2. Modify `INSTALL_YS_GUARDIAN.bat` for your paths
3. Deploy via Group Policy or login script
4. Set environment variable: `YS_GUARDIAN_OUTPUT`

### For Artists
1. Get the `ys_guardian` folder from Pipeline
2. Run `installers/INSTALL_YS_GUARDIAN.bat` as Admin
3. Restart Cinema 4D
4. Find under Extensions menu

## 📊 Technical Specifications

### System Requirements
- **OS**: Windows 10/11
- **Cinema 4D**: 2024.0.0 or later
- **Python**: 3.7+ (for EXR conversion)
- **RAM**: Minimal impact (~50MB)
- **CPU**: <1% usage during monitoring

### File Structure
```
ys_guardian/
├── plugin/
│   ├── ys_guardian_panel.pyp         # Main plugin (58KB)
│   ├── redshift_snapshot_manager.py  # Snapshot handler
│   └── exr_converter_external.py     # EXR→PNG converter
├── icons/
│   ├── lights_outside_icon.tif       # Status icons
│   ├── visibility_trap_icon.tif
│   └── [other status icons]
├── installers/
│   └── INSTALL_YS_GUARDIAN.bat       # One-click installer
└── README.md                          # This file
```

### Data Persistence

| Data Type | Storage Location | Persistence |
|-----------|-----------------|-------------|
| **Artist Name** | `%AppData%/MAXON/prefs/ys_guardian_settings.json` | Per computer |
| **Window Position** | Cinema 4D layout | Per workspace |
| **Shot ID** | Scene Take system | Per document |
| **Render Preset** | Active render data | Per document |
| **Monitor State** | Runtime only | Per session |

## 📝 Version History

- **v1.0** (Current) - Initial release with complete feature set:
  - 5 real-time quality checks with visual indicators
  - 8 quick action tools in grid layout
  - Render preset management with Force Vertical
  - Stills management with EXR conversion
  - Artist tracking and Shot ID synchronization
  - Performance optimization with smart caching

## 🤝 Contributing

This is an internal Yambo Studio tool. For feature requests or bug reports:
1. Contact the Pipeline team
2. Check `CLAUDE.md` for development guidelines
3. Test changes in sandbox environment first

## 📄 License

**Internal Use Only** - Yambo Studio Proprietary Tool
Not for distribution outside the organization

---
*YS Guardian - Keeping your Cinema 4D projects clean and professional*