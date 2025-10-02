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
- `ys_guardian_panel_v21_snapshot_fix.pyp` - Main plugin file
- `redshift_snapshot_manager_simple.py` - Snapshot management logic
- `redshift_command_listener.py` - Minimal command discovery
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
- **Redshift Snapshot Detection**: Automatically finds .rssnap2 files in temp folder
- **Snapshot Conversion**: Converts .rssnap2 format to viewable PNG images
- **Snapshot Organization**: Moves and renames snapshots to project structure

### What Doesn't Work ❌
- **Forcing Redshift Snapshot Directory**: Can't override Redshift's save location at runtime
- **Programmatic Snapshot Triggering**: No API access to trigger snapshots from code

### Redshift Snapshot Problem ⚠️
**Discovery**: Redshift saves snapshots as .rssnap2 files in `C:\Users\[username]\AppData\Local\Temp\snapshots`
**Format Issue**: .rssnap2 is a proprietary format that appears to be encrypted or specially encoded
**Analysis Results**:
- Files contain real image data (entropy ~5.6/8.0)
- Not standard image formats (not DDS, KTX, PVR)
- Not compressed with standard algorithms (zlib, gzip, lzma)
- Contains float32-like patterns but values are corrupted/encrypted
**Current Status**: Can detect .rssnap2 files but cannot convert them to viewable images
**Workaround**: Users must use Redshift's own tools to export snapshots as standard image formats

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
│ Quick Actions (4x4 grid)             │
│ [Select Lights] [Select Visibility] │
│ [Select Keys]   [Select Cameras]    │
│ [Vibrate Null]  [Basic Cam Rig]     │
│ [Drop to Floor] [Plugin Info]       │
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