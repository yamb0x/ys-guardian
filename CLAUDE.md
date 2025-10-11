# YS Guardian Plugin - Development Rules

## Project Overview
YS Guardian Panel is a Cinema 4D quality control plugin designed for professional 3D production workflows. It acts as a real-time watchdog that continuously monitors scenes for common production issues that could cause problems during rendering or client delivery.

The plugin performs **5 critical quality checks** in real-time:
1. **Lights Organization** - Ensures all lights are properly organized in a "lights" group
2. **Visibility Consistency** - Detects objects with mismatched viewport/render visibility
3. **Keyframe Sanity** - Warns about multi-axis keyframes that can cause animation issues
4. **Camera Shift Detection** - Alerts when cameras have non-zero shift values
5. **Render Preset Management** - Ensures only approved render presets exist

Additional features include Shot ID management, Render Preset selection, Artist name tracking, and (in development) Redshift RenderView snapshot capture.

## Core Files (DO NOT DELETE)
- `ys_guardian_panel.pyp` - Main plugin file
- `redshift_snapshot_manager_fixed.py` - Snapshot management logic
- `exr_to_png_converter_simple.py` - EXR conversion
- `abc_retime/` - Bundled ABC Retime plugin (by axisfx2)
- `YS_Guardian_Documentation.md` - User documentation

## Development Rules

### 1. FOCUS
- **ONE PROBLEM AT A TIME**: Don't try to solve everything at once
- **CORE FUNCTIONALITY FIRST**: Get the basic feature working before adding complexity
- **NO FEATURE CREEP**: Don't add features that weren't requested

### 2. FILE MANAGEMENT
- **EDIT, DON'T CREATE**: Modify existing files instead of creating new versions
- **NO HELPER SCRIPTS**: Don't create installation scripts, test scripts, or diagnostic tools unless specifically requested
- **KEEP IT SIMPLE**: The fewer files, the better

### 3. PROBLEM SOLVING
- **IDENTIFY ROOT CAUSE**: Understand WHY something isn't working before trying to fix it
- **TEST INCREMENTALLY**: Make small changes and test each one
- **DOCUMENT FINDINGS**: Keep notes about what works and what doesn't in this file

### 4. CODE PRINCIPLES
- **MINIMAL DEPENDENCIES**: Use only Cinema 4D's built-in Python libraries when possible
- **FALLBACK GRACEFULLY**: If a feature can't work, fail silently with a simple message
- **NO OVER-ENGINEERING**: Simple solutions are better than complex ones

## Data Persistence

### Saved Per Computer/User (Persistent)
- **Artist Name**: Stored in Cinema 4D preferences folder (`GeGetC4DPath(c4d.C4D_PATH_PREFS)/ys_guardian_settings.json`)
- **Panel Layout**: Window position and docking state preserved by Cinema 4D

### Fetched From Scene (Per Document)
- **Shot ID**: Read from Main Take name, synchronized with scene
- **Render Preset**: Read from active render data, matches scene settings

### Runtime Only (Per Session)
- **Live Monitoring State**: Resets to enabled on startup
- **Check Interval**: Resets to default (800ms) on startup
- **Show/Hide Filters**: Resets to all visible on startup
- **Snapshot Directory**: Must be set each session (environment variable limitation)

## Current Issues & Status

### What Works ✅
- **All 5 Quality Checks**: Lights, visibility, keyframes, camera shift, render presets
- **Shot ID Management**: Syncs with Cinema 4D Take system
- **Render Preset Selection**: Quick switching between standard presets
- **Live Monitoring**: Real-time updates with performance optimization
- **Selection Tools**: One-click selection of problematic objects
- **Artist Name Persistence**: Saved per computer/user
- **Folder Structure Creation**: Organized output directory hierarchy
- **File Organization Logic**: Proper naming and placement of files
- **Redshift Snapshot Support**: Works with EXR snapshots (requires manual Redshift config)
- **Snapshot Conversion**: Converts EXR to PNG with filmic tone mapping
- **Snapshot Organization**: Moves and renames snapshots to project structure
- **Hierarchy→Layers**: Syncs object manager nulls with layer manager (creates/links layers)
- **Unique Layer Colors**: Each layer gets a distinct random color for easy identification
- **Drop to Floor**: Accurately positions objects at Y=0, handles rotation and hierarchy
- **Plugin Icon**: Custom YS Guardian icon displays in Extensions menu
- **Flexible Preset Names**: Accepts "pre_render", "pre-render", "Pre-Render" (case-insensitive)
- **Camera Setups**: Three pre-configured camera rigs (Simple, Shakel, Path) - one-click merge into scene
- **ABC Retime Integration**: Bundled plugin with one-click tag application for alembic retiming

### What Doesn't Work ❌
- **Forcing Redshift Snapshot Directory**: Can't override Redshift's save location at runtime
- **Programmatic Snapshot Triggering**: No API access to trigger snapshots from code

### Redshift Snapshot Setup Required ⚙️
**Solution**: Redshift RenderView must be configured to save snapshots as EXR format
**Setup Steps**:
1. Open Redshift RenderView
2. Click Preferences (gear icon) → Snapshots → Configuration
3. Set path: `C:/cache/rs snapshots`
4. Enable "Save snapshots as EXR" (not .rssnap2)
5. Click OK

**Current Status**: Works perfectly when configured correctly
**Note**: The installer creates the cache directory and shows these instructions automatically

## Active Tasks
Check the `tasks/` folder for current development tasks and priorities.
**IMPORTANT**: Always check the tasks folder at the start of each session to stay updated on pending work.

## Do NOT:
- Create multiple versions of the same file
- Add complex dependency management
- Create installation/setup scripts (unless updating the existing one)
- Promise automatic features that require Redshift API access we don't have
- Over-complicate the solution

## Keep It Simple
The plugin should do what it can do well, and clearly communicate its limitations.

## Recent Improvements (v1.0 - October 2024)

### Drop to Floor Enhancement
- Fixed rotation handling: now calculates global bounding box correctly
- Fixed hierarchy handling: works with nested objects
- Uses object cache for accurate geometry bounds
- Supports rotated, scaled, and grouped objects

### Layer Colors
- Each layer gets a unique random color based on name hash
- Colors are visually distinct using golden ratio distribution
- Same layer name = same color (consistent across sessions)
- Pleasant, bright colors (60% saturation, 95% brightness)

### Plugin Icon Integration
- Custom YS Guardian icon (32x32 PNG with alpha)
- Displays in Extensions menu and Plugin Manager
- Automatically installed by batch installer
- Path: `icons/ys-logo-alpha-32.png`

### Preset Name Flexibility
- Case-insensitive preset matching
- Accepts hyphens, underscores, or spaces: "pre-render", "pre_render", "Pre Render"
- UI displays readable names, internal system normalizes them
- No more preset naming errors!

### Redshift Snapshot Workflow
- Installer creates `C:\cache\rs snapshots` directory automatically
- Installer displays setup instructions for Redshift configuration
- Plugin Info dialog includes step-by-step Redshift setup
- README updated with clear configuration requirements

### ABC Retime Integration
- **Bundled Plugin**: abc_retime by axisfx2 included in installation
- **One-Click Application**: Button in Quick Actions applies tag to selected objects
- **Plugin ID**: 1058910 (Alembic Retime tag)
- **Supported Objects**: Alembic Object, Alembic Tag, Point Cache, Mograph Cache, X-Particles Cache
- **Manual Access**: Right-click Tags → Extensions → Alembic Retime
- **Features**: Percentage-based retiming, frame number control, timeline manager support
- **Installation**: Automatically installed to Cinema 4D plugins folder
- **Error Handling**: Clear messages for missing plugin, existing tags, or invalid objects

## Installation Batch File Maintenance ⚠️

### ALWAYS Update the Installation Batch
**IMPORTANT**: Whenever you make changes to the plugin, you MUST update the installation batch file at `installers\INSTALL_YS_GUARDIAN.bat` to ensure end users can test the latest features.

### What to Update in the Batch File:

1. **Feature List (Lines 9-21)**: Update the features description to match current capabilities
   - Add new UI features
   - Update button counts/descriptions
   - Mention visual improvements
   - List new tools or functions

2. **File Verification (Lines 233-246)**: Update icon verification if icon names change
   - Check all icon filenames match actual files in `icons/` folder
   - Update icon count if new icons are added

3. **Version Number**: Update if significant changes are made (currently v1.0)

### Testing Checklist for Each Update:
- [ ] Main plugin file loads without errors
- [ ] All 5 quality checks function correctly
- [ ] Icons display properly in Quality Check Status
- [ ] All Quick Action buttons work (8 buttons total in 4x4 grid)
- [ ] Select buttons work for each quality check (Lights, Visibility, Keyframes, Cameras)
- [ ] Drop to Floor functionality works with selected objects
- [ ] Rounded corners render on status bars
- [ ] Info dialog shows clean formatting (no ====)
- [ ] Artist name persistence works
- [ ] Shot ID syncs with Take system
- [ ] Render Preset selection works

### Current UI Layout (v1.0):
```
┌─────────────────────────────────────┐
│ Shot ID: [____] Preset: [dropdown]  │
│ Artist: [_______________________]   │
├─────────────────────────────────────┤
│ Monitoring Controls                  │
│ ☑ Live Monitoring  Update: [8]x100ms│
│ Active Watchers:                     │
│ ☑ Lights ☑ Visibility ☑ Keyframes   │
│ ☑ Cameras ☑ Presets                 │
├─────────────────────────────────────┤
│ Quality Check Status                 │
│ ╭─[🔦] Lights: 0 [OK]──────────────╮│
│ ╭─[👁] Visibility: 0 [OK]──────────╮│
│ ╭─[🔑] Keyframes: 0 [OK]───────────╮│
│ ╭─[📷] Cameras: 0 [OK]─────────────╮│
│ ╭─[📋] Presets: 0 [OK]─────────────╮│
├─────────────────────────────────────┤
│ Quick Actions                        │
│ [Hierarchy→Layers (2x)] [Solo (2x)] │
│ [Search 3D Model]  [Ask ChatGPT]    │
│ [Vibrate Null] [Drop] [ABC Retime]  │
│ [Cam: Simple] [Cam: Shakel] [Path]  │
├─────────────────────────────────────┤
│ Stills Management                    │
│ [Open Folder]   [Save Still]        │
└─────────────────────────────────────┘
```

### End User Experience Goals:
- Plugin should feel professional and polished
- Icons should enhance visual feedback, not clutter
- All functions should be discoverable and intuitive
- Error messages should be helpful, not cryptic
- Installation should be one-click simple