# -*- coding: utf-8 -*-
import c4d
from c4d import plugins, gui, documents
import os
import json
import time
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import threading
from collections import defaultdict

# Import snapshot management modules
sys.path.insert(0, os.path.dirname(__file__))
try:
    from redshift_snapshot_manager_fixed import RedshiftSnapshotManager, RedshiftSnapshotConfig, get_snapshot_manager
    from exr_to_png_converter_simple import convert_exr_to_png, get_converter_info
    SNAPSHOT_AVAILABLE = True
    converter_info = get_converter_info()
    EXR_CONVERTER_AVAILABLE = converter_info["available"]
    EXR_CONVERTER_METHOD = converter_info["method"] if converter_info["available"] else None
except ImportError as e:
    safe_print(f"Warning: Snapshot modules import error: {e}")
    SNAPSHOT_AVAILABLE = False
    EXR_CONVERTER_AVAILABLE = False
    EXR_CONVERTER_METHOD = None

# Plugin ID - change if ID collision
PLUGIN_ID = 2099069
PLUGIN_NAME = "YS Guardian v1.0"
PRESETS = ["previz", "pre_render", "render", "stills"]

# Icon paths - check both development and installed locations
plugin_dir = os.path.dirname(__file__)
# First try parent directory (current structure)
parent_icons = os.path.join(plugin_dir, "..", "icons")
# Then try plugin directory
plugin_icons = os.path.join(plugin_dir, "icons")

if os.path.exists(parent_icons):
    ICONS_DIR = parent_icons
elif os.path.exists(plugin_icons):
    ICONS_DIR = plugin_icons
else:
    # Fallback to parent directory
    ICONS_DIR = parent_icons

ICONS = {
    # Status icons
    "lights_bad": os.path.join(ICONS_DIR, "lights outside icon.tif"),
    "visibility_bad": os.path.join(ICONS_DIR, "visability trap icon.tif"),
    "keyframe_bad": os.path.join(ICONS_DIR, "keyframe sanity icon.tif"),
    "camera_bad": os.path.join(ICONS_DIR, "camera with non zero shift icon.tif"),
    "preset_bad": os.path.join(ICONS_DIR, "render preset conlfict icon.tif"),
    # Toggle icons
    "lights_toggle": os.path.join(ICONS_DIR, "lights toggle.tif"),
    "visibility_toggle": os.path.join(ICONS_DIR, "visability toggle.tif"),
    "keyframe_toggle": os.path.join(ICONS_DIR, "keyframe toggle.png"),
    "camera_toggle": os.path.join(ICONS_DIR, "camera toggle.tif"),
    # Info icon
    "info": os.path.join(ICONS_DIR, "info.svg")
}

# Performance settings for watcher
MAX_OBJECTS_PER_CHECK = 1000  # Process in chunks
CACHE_DURATION = 0.5  # Cache results for 500ms
CHECK_COOLDOWN = 0.1  # Minimum time between checks

# Global settings file for artist name
SETTINGS_FILE = "ys_guardian_settings.json"

# ---------------- Safe Print Function ----------------
def safe_print(msg):
    """Print to console with null safety"""
    try:
        if msg is not None:
            print(f"[YS Guardian] {msg}")
    except:
        pass

# ---------------- Artist Name Persistence ----------------
class GlobalSettings:
    """Manages computer-level settings (not scene-specific)"""

    @staticmethod
    def get_settings_path() -> str:
        """Get path to global settings file in user's preferences"""
        prefs_path = c4d.storage.GeGetC4DPath(c4d.C4D_PATH_PREFS)
        return os.path.join(prefs_path, SETTINGS_FILE)

    @staticmethod
    def load_artist_name() -> str:
        """Load artist name from computer-level settings"""
        settings_path = GlobalSettings.get_settings_path()

        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    return settings.get('artist_name', '')
            except:
                pass

        return ''

    @staticmethod
    def save_artist_name(artist_name: str) -> bool:
        """Save artist name to computer-level settings"""
        settings_path = GlobalSettings.get_settings_path()

        settings = {}
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
            except:
                pass

        settings['artist_name'] = artist_name

        try:
            with open(settings_path, 'w') as f:
                json.dump(settings, f, indent=2)
            verified_name = GlobalSettings.load_artist_name()
            return verified_name == artist_name
        except:
            return False

# ---------------- Performance Cache ----------------
class CheckCache:
    def __init__(self):
        self.cache = {}
        self.last_update = 0
        self.doc_id = None

    def get(self, doc, key):
        doc_id = id(doc)
        now = time.time()

        if (self.doc_id == doc_id and
            key in self.cache and
            now - self.last_update < CACHE_DURATION):
            return self.cache[key]
        return None

    def set(self, doc, key, value):
        self.doc_id = id(doc)
        self.cache[key] = value
        self.last_update = time.time()

    def clear(self):
        self.cache.clear()
        self.doc_id = None

# Global cache instance
check_cache = CheckCache()

# ---------------- utils ----------------
def _iter_objs(op, max_count=None):
    """Optimized object iterator with limit"""
    count = 0
    stack = [op]

    while stack and (max_count is None or count < max_count):
        current = stack.pop()
        if current is None:
            continue

        yield current
        count += 1

        child = current.GetDown()
        if child:
            stack.append(child)

        sibling = current.GetNext()
        if sibling:
            stack.append(sibling)

def _any_ancestor_named(o, names_lower):
    """Check if any ancestor has one of the specified names"""
    if not o:
        return False

    p = o.GetUp()
    depth = 0
    max_depth = 100

    while p and depth < max_depth:
        try:
            nm = (p.GetName() or "").strip().lower()
            if nm in names_lower:
                return True
        except:
            pass
        p = p.GetUp()
        depth += 1
    return False

# ---------------- lights (optimized) ----------------
RS_LIGHT_ID = 1036751  # Redshift Light
C4D_LIGHT_ID = c4d.Olight
LIGHT_TYPE_CACHE = {}  # Cache light type checks

def _is_light_obj(op):
    """Optimized light detection with caching"""
    if not op:
        return False

    op_id = op.GetType()

    # Check cache first
    if op_id in LIGHT_TYPE_CACHE:
        return LIGHT_TYPE_CACHE[op_id]

    is_light = False

    try:
        # Fast checks first
        if op_id == C4D_LIGHT_ID or op_id == RS_LIGHT_ID:
            is_light = True
        elif op.CheckType(C4D_LIGHT_ID):
            is_light = True
        else:
            # Additional Redshift light types
            if op_id in (1036754, 1038653, 1036950, 1034355, 1036753):  # RS lights
                is_light = True
            else:
                # Slow check last
                tn = (op.GetTypeName() or "").lower()
                if "light" in tn:
                    is_light = True
    except:
        pass

    # Cache result
    LIGHT_TYPE_CACHE[op_id] = is_light
    return is_light

def check_lights(doc):
    """Check for lights outside proper containers"""
    cached = check_cache.get(doc, "lights")
    if cached is not None:
        return cached

    offenders = []
    names = {"lights", "lighting"}
    first = doc.GetFirstObject()

    if not first:
        check_cache.set(doc, "lights", offenders)
        return offenders

    try:
        for o in _iter_objs(first, MAX_OBJECTS_PER_CHECK):
            if not o:
                continue

            if not _is_light_obj(o):
                continue

            if _any_ancestor_named(o, names):
                continue

            offenders.append(o)

            # Early exit if too many issues
            if len(offenders) > 50:
                safe_print(f"Too many light issues found ({len(offenders)}+), stopping check")
                break

    except Exception as e:
        safe_print(f"Error checking lights: {e}")

    check_cache.set(doc, "lights", offenders)
    return offenders

# ---------------- visibility traps (optimized) ----------------
def check_visibility_traps(doc):
    """Check for visibility inconsistencies between viewport and render"""
    cached = check_cache.get(doc, "vis")
    if cached is not None:
        return cached

    traps = []
    first = doc.GetFirstObject()

    if not first:
        check_cache.set(doc, "vis", traps)
        return traps

    def ed(o):
        try:
            return o[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR]
        except:
            return c4d.OBJECT_ON

    def rd(o):
        try:
            return o[c4d.ID_BASEOBJECT_VISIBILITY_RENDER]
        except:
            return c4d.OBJECT_ON

    try:
        # Build parent visibility map for optimization
        parent_vis = {}

        for o in _iter_objs(first, MAX_OBJECTS_PER_CHECK):
            if not o:
                continue

            try:
                obj_id = id(o)
                ed_vis = ed(o)
                rd_vis = rd(o)

                # Check direct visibility trap
                if ed_vis == c4d.OBJECT_OFF and rd_vis != c4d.OBJECT_OFF:
                    traps.append(o)
                    continue

                # Check ancestor visibility
                p = o.GetUp()
                if p:
                    parent_id = id(p)

                    # Use cached parent visibility if available
                    if parent_id in parent_vis:
                        ancE, ancR = parent_vis[parent_id]
                    else:
                        ancE = False
                        ancR = False
                        temp_p = p
                        depth = 0

                        while temp_p and depth < 50:
                            if ed(temp_p) == c4d.OBJECT_OFF:
                                ancE = True
                            if rd(temp_p) == c4d.OBJECT_OFF:
                                ancR = True
                            temp_p = temp_p.GetUp()
                            depth += 1

                        parent_vis[parent_id] = (ancE, ancR)

                    if (ancE and ed_vis == c4d.OBJECT_ON) or (ancR and rd_vis == c4d.OBJECT_ON):
                        traps.append(o)

                # Early exit
                if len(traps) > 50:
                    safe_print(f"Too many visibility issues ({len(traps)}+), stopping check")
                    break

            except Exception:
                continue

    except Exception as e:
        safe_print(f"Error checking visibility: {e}")

    check_cache.set(doc, "vis", traps)
    return traps

# ---------------- keyframe sanity (optimized) ----------------
def check_keys(doc):
    """Check for multi-axis position/rotation keyframes"""
    cached = check_cache.get(doc, "keys")
    if cached is not None:
        return cached

    offenders = []
    first = doc.GetFirstObject()

    if not first:
        check_cache.set(doc, "keys", offenders)
        return offenders

    try:
        for o in _iter_objs(first, MAX_OBJECTS_PER_CHECK):
            if not o:
                continue

            try:
                tracks = o.GetCTracks()
                if not tracks:
                    continue

                pos_axes = set()
                rot_axes = set()

                for tr in tracks:
                    try:
                        did = tr.GetDescriptionID()
                        if not did or did.GetDepth() < 1:
                            continue

                        first_id = did[0].id

                        if first_id == c4d.ID_BASEOBJECT_POSITION:
                            if did.GetDepth() >= 2:
                                pos_axes.add(did[1].id)
                        elif first_id == c4d.ID_BASEOBJECT_ROTATION:
                            if did.GetDepth() >= 2:
                                rot_axes.add(did[1].id)
                    except:
                        continue

                if len(pos_axes) > 1 or len(rot_axes) > 1:
                    offenders.append(o)

                # Early exit
                if len(offenders) > 50:
                    safe_print(f"Too many keyframe issues ({len(offenders)}+), stopping check")
                    break

            except:
                continue

    except Exception as e:
        safe_print(f"Error checking keyframes: {e}")

    check_cache.set(doc, "keys", offenders)
    return offenders

# ---------------- camera shift (optimized) ----------------
RS_CAMERA_ID = 1057516

def _camera_shift_values(o):
    """Get camera shift values efficiently"""
    if not o:
        return 0.0, 0.0

    # Try standard attributes first (fastest)
    attrs = [
        (c4d.CAMERAOBJECT_FILM_OFFSET_X, c4d.CAMERAOBJECT_FILM_OFFSET_Y),
    ]

    for xid, yid in attrs:
        try:
            x = float(o[xid] or 0.0)
            y = float(o[yid] or 0.0)
            if abs(x) > 1e-6 or abs(y) > 1e-6:
                return x, y
        except:
            pass

    # Skip slow description iteration for performance
    return 0.0, 0.0

def check_camera_shift(doc):
    """Check for cameras with non-zero shift"""
    cached = check_cache.get(doc, "cam")
    if cached is not None:
        return cached

    bad = []
    first = doc.GetFirstObject()

    if not first:
        check_cache.set(doc, "cam", bad)
        return bad

    try:
        for o in _iter_objs(first, MAX_OBJECTS_PER_CHECK):
            if not o:
                continue

            try:
                # Quick type check
                obj_type = o.GetType()
                if obj_type != c4d.Ocamera and obj_type != RS_CAMERA_ID:
                    continue

                x, y = _camera_shift_values(o)
                if abs(x) > 1e-6 or abs(y) > 1e-6:
                    bad.append(o)

                # Early exit
                if len(bad) > 20:
                    safe_print(f"Too many camera shift issues ({len(bad)}+), stopping check")
                    break

            except:
                continue

    except Exception as e:
        safe_print(f"Error checking camera shift: {e}")

    check_cache.set(doc, "cam", bad)
    return bad

# ---------------- render preset conflicts (optimized) ----------------
def check_render_conflicts(doc):
    """Check for render setting conflicts"""
    cached = check_cache.get(doc, "rdc")
    if cached is not None:
        return cached

    allowed = set(PRESETS)
    name_counts = defaultdict(int)
    extras = 0

    try:
        rd = doc.GetFirstRenderData()
        count = 0
        max_check = 100  # Limit iterations

        while rd and count < max_check:
            try:
                name = (rd.GetName() or "").strip().lower()
                if name in allowed:
                    name_counts[name] += 1
                else:
                    extras += 1
            except:
                pass

            rd = rd.GetNext()
            count += 1

        dups = sum(max(0, c - 1) for c in name_counts.values())
        result = extras + dups

    except Exception as e:
        safe_print(f"Error checking render conflicts: {e}")
        result = 0

    check_cache.set(doc, "rdc", result)
    return result

# ---------------- UI StatusArea ----------------
class StatusArea(gui.GeUserArea):
    def __init__(self):
        super().__init__()
        self.data = {}
        self.show = {"lights": True, "vis": True, "keys": True, "cam": True, "rdc": True}
        self.pad = 10  # Improved spacing
        self.rowh = 30  # Height for icon display
        self.font = c4d.FONT_BOLD
        self.last_draw_time = 0
        self.min_draw_interval = 0.05  # Minimum 50ms between redraws
        self.icons = {}
        self._load_icons()

    def _load_icons(self):
        """Load all status icons"""
        try:
            icon_map = {
                "lights": ICONS.get("lights_bad"),
                "visibility": ICONS.get("visibility_bad"),
                "keyframe": ICONS.get("keyframe_bad"),
                "camera": ICONS.get("camera_bad"),
                "preset": ICONS.get("preset_bad")
            }

            safe_print(f"Loading icons from: {ICONS_DIR}")
            icons_loaded = 0

            for name, path in icon_map.items():
                if path and os.path.exists(path):
                    bmp = c4d.bitmaps.BaseBitmap()
                    if bmp.InitWith(path)[0] == c4d.IMAGERESULT_OK:
                        # Don't resize, just use original
                        self.icons[name] = bmp
                        icons_loaded += 1
                        safe_print(f"Loaded icon: {name} from {os.path.basename(path)}")
                    else:
                        safe_print(f"Failed to init bitmap for: {path}")
                else:
                    safe_print(f"Icon path not found: {path}")

            safe_print(f"Total icons loaded: {icons_loaded}/{len(icon_map)}")

        except Exception as e:
            safe_print(f"Error loading icons: {e}")

    def GetMinSize(self):
        rows = sum(1 for _, v in self.show.items() if v)
        return 620, max(1, rows) * (self.rowh + self.pad) + self.pad + 28

    def set_state(self, data, show):
        self.data = data or {}
        self.show = show or self.show

        # Throttle redraws
        now = time.time()
        if now - self.last_draw_time > self.min_draw_interval:
            self.Redraw()
            self.last_draw_time = now

    def _sev(self, n):
        if n <= 0:  return ("OK",   c4d.Vector(0.18, 0.65, 0.28))
        if n < 5:   return ("WARN", c4d.Vector(0.95, 0.72, 0.16))
        return ("BAD", c4d.Vector(0.85, 0.25, 0.25))

    def _fg(self, bg):
        lum = 0.2126*bg.x + 0.7152*bg.y + 0.0722*bg.z
        return c4d.Vector(0,0,0) if lum > 0.55 else c4d.Vector(1,1,1)

    def DrawMsg(self, x1, y1, x2, y2, msg):
        try:
            self.OffScreenOn()
            w = self.GetWidth(); h = self.GetHeight()

            # Background
            self.DrawSetPen(c4d.Vector(0.12,0.12,0.12))
            self.DrawRectangle(0,0,w,h)

            try:
                self.DrawSetFont(self.font)
            except:
                pass

            x=self.pad; y=self.pad

            def draw_rounded_rect(x1, y1, x2, y2, radius, color):
                """Draw a rounded rectangle"""
                self.DrawSetPen(color)
                # Convert all coordinates to integers
                x1, y1, x2, y2, radius = int(x1), int(y1), int(x2), int(y2), int(radius)

                # Draw main rectangle
                self.DrawRectangle(x1 + radius, y1, x2 - radius, y2)
                self.DrawRectangle(x1, y1 + radius, x2, y2 - radius)

                # Draw corners (approximate with small rectangles)
                corner_steps = 4
                for i in range(corner_steps):
                    offset = int(radius * (1 - (i / float(corner_steps))))
                    width = int(radius * (i / float(corner_steps)))
                    # Top-left
                    self.DrawRectangle(x1 + offset, y1 + width, x1 + radius, y1 + width + 1)
                    # Top-right
                    self.DrawRectangle(x2 - radius, y1 + width, x2 - offset, y1 + width + 1)
                    # Bottom-left
                    self.DrawRectangle(x1 + offset, y2 - width - 1, x1 + radius, y2 - width)
                    # Bottom-right
                    self.DrawRectangle(x2 - radius, y2 - width - 1, x2 - offset, y2 - width)

            def row(label, key, mode="default"):
                nonlocal y
                val = int(self.data.get(key, 0))

                # Choose tag + color based on mode
                if mode == "lights":
                    if val > 0:
                        tag_text = f"{val} lights outside lights group"
                        _, col = self._sev(val)
                    else:
                        tag_text, col = ("OK", c4d.Vector(0.18,0.65,0.28))
                elif mode == "keys":
                    if val > 0:
                        names = self.data.get("keys_names", [])
                        first = names[0] if names else "object"
                        extra = f" (+{val-1} more)" if val > 1 else ""
                        tag_text = f"MULTIPLE KEYFRAMES ON `{first}`{extra}"
                        _, col = self._sev(val)
                    else:
                        tag_text, col = ("OK", c4d.Vector(0.18,0.65,0.28))
                elif mode == "vis":
                    if val > 0:
                        names = self.data.get("vis_names", [])
                        first = names[0] if names else "object"
                        extra = f" (+{val-1} more)" if val > 1 else ""
                        tag_text = f"MISMATCHED VIEWPORT/RENDER VISIBILITY on `{first}`{extra}"
                        _, col = self._sev(val)
                    else:
                        tag_text, col = ("OK", c4d.Vector(0.18,0.65,0.28))
                elif mode == "cam":
                    if val > 0:
                        tag_text = "ADJUST SHIFT BACK TO 0%! Or update on Discord"
                        col = c4d.Vector(0.85,0.25,0.25)
                    else:
                        tag_text, col = ("OK", c4d.Vector(0.18,0.65,0.28))
                elif mode == "rdc":
                    if val > 0:
                        tag_text = "REMOVE ADDITIONAL RENDER PRESET"
                        col = c4d.Vector(0.85,0.25,0.25)
                    else:
                        tag_text, col = ("OK", c4d.Vector(0.18,0.65,0.28))
                else:
                    tag_text, col = self._sev(val)

                # Draw row background with rounded corners
                draw_rounded_rect(x, y, w-self.pad, y+self.rowh, 5, col)

                # Prepare text and icon
                icon_key = None
                show_icon = (val > 0)  # Only show icon for issues

                if show_icon:
                    # Determine which icon to use (must match keys in _load_icons)
                    if mode == "lights":
                        icon_key = "lights"
                    elif mode == "vis":
                        icon_key = "visibility"
                    elif mode == "keys":
                        icon_key = "keyframe"
                    elif mode == "cam":
                        icon_key = "camera"
                    elif mode == "rdc":
                        icon_key = "preset"

                # Calculate positions
                text_x = x + 10
                icon_space = 0

                # Draw icon if available
                if show_icon and icon_key and icon_key in self.icons:
                    icon = self.icons[icon_key]
                    if icon:
                        icon_w = min(20, icon.GetBw())  # Limit icon size
                        icon_h = min(20, icon.GetBh())
                        icon_x = int(x + 8)
                        icon_y = int(y + (self.rowh - icon_h) // 2)
                        # Convert all parameters to int
                        self.DrawBitmap(icon, int(icon_x), int(icon_y), int(icon_w), int(icon_h),
                                      0, 0, int(icon.GetBw()), int(icon.GetBh()), c4d.BMP_ALLOWALPHA)
                        icon_space = icon_w + 5
                        text_x = int(icon_x + icon_space)

                # Draw text (format depends on if there's an issue)
                self.DrawSetTextCol(self._fg(col), col)
                if val > 0:
                    # Issue found - show detailed message
                    self.DrawText(f"{label}: {val}  [{tag_text}]", int(text_x), int(y+8))
                else:
                    # No issue - just show OK
                    self.DrawText(f"{label}: {val}  [OK]", int(text_x), int(y+8))

                y += self.rowh + self.pad

            mapping = [
                ("Lights outside lights group", "lights", "lights"),
                ("Visibility traps", "vis", "vis"),
                ("Keyframe sanity hits", "keys", "keys"),
                ("Cameras with non-zero Shift", "cam", "cam"),
                ("Render preset conflicts", "rdc", "rdc"),
            ]

            for label, key, mode in mapping:
                if self.show.get(key, False):
                    row(label, key, mode)

            y += 6
            self.DrawSetTextCol(c4d.Vector(0.8,0.8,0.8), c4d.Vector(0,0,0))
            self.DrawText("YAMBO STUDIO © 2025  STUDIO TOOLS  V.2.2", int(x+6), int(h-18))

        except Exception as e:
            safe_print(f"Error in DrawMsg: {e}")

# ---------------- Snapshot Handler ----------------
class SnapshotHandler:
    """Handles all snapshot operations"""

    def __init__(self):
        self.snapshot_manager = get_snapshot_manager() if SNAPSHOT_AVAILABLE else None

    def take_snapshot(self, doc, artist_name):
        """Process snapshot - grab EXR from cache and convert to PNG"""
        if not SNAPSHOT_AVAILABLE or not self.snapshot_manager:
            c4d.gui.MessageDialog("Still save system not available.\nPlease install OpenEXR: pip install OpenEXR-Python")
            return

        if not artist_name:
            c4d.gui.MessageDialog("Please set your artist name first!")
            return

        # Process the snapshot (find EXR, convert, and save)
        output_path, error = self.snapshot_manager.process_snapshot(doc, artist_name)

        if output_path:
            self._show_success(output_path)
        else:
            c4d.gui.MessageDialog(error or "Failed to process snapshot")

    def open_artist_folder(self, doc, artist_name):
        """Open the artist's output folder"""
        if not artist_name:
            c4d.gui.MessageDialog("Please set your artist name first!")
            return

        # Get the output directory
        output_dir = RedshiftSnapshotConfig.get_scene_snapshot_dir(doc, artist_name)

        if output_dir and os.path.exists(output_dir):
            # Open folder in Explorer
            os.startfile(output_dir)
        else:
            c4d.gui.MessageDialog(f"Artist folder not found:\n{output_dir}")

    def _show_success(self, path):
        """Show success message and open in Picture Viewer"""
        try:
            # Load and show in Picture Viewer
            bmp = c4d.bitmaps.BaseBitmap()
            if bmp.InitWith(path)[0] == c4d.IMAGERESULT_OK:
                # Get image dimensions for aspect ratio
                width = bmp.GetBw()
                height = bmp.GetBh()

                # Calculate aspect ratio
                if height > 0:
                    aspect_ratio = width / height
                    # Format as common ratio
                    if abs(aspect_ratio - 1.778) < 0.01:
                        aspect_str = "16:9"
                    elif abs(aspect_ratio - 1.333) < 0.01:
                        aspect_str = "4:3"
                    elif abs(aspect_ratio - 2.35) < 0.05:
                        aspect_str = "2.35:1"
                    elif abs(aspect_ratio - 1.0) < 0.01:
                        aspect_str = "1:1"
                    else:
                        aspect_str = f"{aspect_ratio:.2f}:1"
                else:
                    aspect_str = "Unknown"

                c4d.bitmaps.ShowBitmap(bmp)

                filename = os.path.basename(path)
                folder = os.path.dirname(path)
                c4d.gui.MessageDialog(f"Still saved!\n\nFile: {filename}\nResolution: {width}x{height} ({aspect_str})\nFolder: {folder}")
            else:
                # If we can't load the bitmap, still show basic success
                filename = os.path.basename(path)
                folder = os.path.dirname(path)
                c4d.gui.MessageDialog(f"Still saved!\n\nFile: {filename}\nFolder: {folder}")

        except:
            pass

# Global snapshot handler
_snapshot_handler = SnapshotHandler()

# ---------------- UI ----------------
class G:
    SHOT = 1001
    PRESET = 1002  # Not used anymore - replaced by tabs
    ARTIST = 1003
    LIVE = 1004
    STEP = 1005
    CANVAS = 1008
    BTN_SNAPSHOT = 1009
    BTN_OPEN_FOLDER = 1010
    BTN_INFO = 1020

    SHOW_L = 1011
    SHOW_V = 1014
    SHOW_K = 1015
    SHOW_C = 1016
    SHOW_P = 1017  # Show Preset conflicts

    SEL_LIGHTS = 1101
    SEL_VIS = 1103
    SEL_KEYS = 1104
    SEL_CAMS = 1105

    # New Quick Action buttons
    BTN_VIBRATE_NULL = 1106
    BTN_CAM_RIG = 1107
    BTN_ASSET_BROWSER = 1108
    BTN_PLACEHOLDER = 1109  # Fourth button placeholder

    # Render preset tab buttons
    BTN_PRESET_PREVIZ = 1200
    BTN_PRESET_PRERENDER = 1201
    BTN_PRESET_RENDER = 1202
    BTN_PRESET_STILLS = 1203
    BTN_FORCE_RENDER = 1204
    BTN_FORCE_VERTICAL = 1205

    # Active Watchers as tabs (replacing checkboxes)
    BTN_WATCH_LIGHTS = 1300
    BTN_WATCH_VIS = 1301
    BTN_WATCH_KEYS = 1302
    BTN_WATCH_CAM = 1303
    BTN_WATCH_PRESET = 1304

    # Monitoring control buttons
    BTN_MUTE_ALL = 1305

class YSPanel(gui.GeDialog):
    def __init__(self):
        super().__init__()
        self._last_doc = None
        self._last_check_time = 0
        self._check_thread = None
        self._thread_lock = threading.Lock()
        self._pending_results = None
        self._artist_name = ""

        # Store selection results
        self._lights_bad = []
        self._vis_bad = []
        self._keys_bad = []
        self._cam_bad = []

    # ---- read scene -> UI
    def _sync_from_doc(self, doc):
        """Sync UI with document state"""
        if not doc:
            return

        try:
            td = None
            try:
                td = doc.GetTakeData()
            except:
                try:
                    td = documents.GetTakeData(doc)
                except:
                    pass

            shot = ""
            if td:
                main_take = td.GetMainTake()
                if main_take:
                    shot = main_take.GetName() or ""
            self.SetString(G.SHOT, shot)
        except Exception as e:
            safe_print(f"Error syncing shot name: {e}")

        try:
            ard = doc.GetActiveRenderData()
            if ard:
                name = (ard.GetName() or "").strip().lower()
                # Update the active preset based on current render data
                if name in PRESETS:
                    self._active_preset = name
                    self._update_preset_buttons()
        except Exception as e:
            safe_print(f"Error syncing render preset: {e}")

    # ---- write UI -> scene
    def _apply_shot(self, doc):
        if not doc:
            return

        try:
            name = self.GetString(G.SHOT)
            td = None

            try:
                td = doc.GetTakeData()
            except:
                try:
                    td = documents.GetTakeData(doc)
                except:
                    pass

            if td:
                main_take = td.GetMainTake()
                if main_take:
                    main_take.SetName(name)
                    c4d.EventAdd()
        except Exception as e:
            safe_print(f"Error applying shot name: {e}")

    def _apply_preset(self, doc, preset_name):
        if not doc:
            return

        try:
            rd = doc.GetFirstRenderData()

            while rd:
                if (rd.GetName() or "").strip().lower() == preset_name:
                    doc.SetActiveRenderData(rd)
                    c4d.EventAdd()
                    self._active_preset = preset_name
                    self._update_preset_buttons()
                    safe_print(f"Switched to render preset: {preset_name}")
                    break
                rd = rd.GetNext()
        except Exception as e:
            safe_print(f"Error applying render preset: {e}")

    def _update_preset_buttons(self):
        """Update preset button visual state to show active preset"""
        # This could be enhanced with visual feedback in future
        pass

    def _flags(self):
        # Return watcher states (now controlled by tab buttons)
        if self._all_muted:
            # If muted, all watchers are off
            return {
                "lights": False,
                "vis": False,
                "keys": False,
                "cam": False,
                "rdc": False
            }
        return self._watcher_states

    def _refresh(self):
        """Throttled refresh with performance optimization"""
        doc = c4d.documents.GetActiveDocument()
        if not doc:
            return

        # Check cooldown
        now = time.time()
        if now - self._last_check_time < CHECK_COOLDOWN:
            return
        self._last_check_time = now

        try:
            # Run checks
            lights_bad = check_lights(doc)
            vis_bad = check_visibility_traps(doc)
            keys_bad = check_keys(doc)
            cam_bad = check_camera_shift(doc)
            rdc_bad = check_render_conflicts(doc)

            # Update UI
            self.ua.set_state(
                dict(
                    lights=len(lights_bad) if lights_bad else 0,
                    vis=len(vis_bad) if vis_bad else 0,
                    vis_names=[(o.GetName() or "object") for o in (vis_bad[:10] if vis_bad else [])],
                    keys=len(keys_bad) if keys_bad else 0,
                    keys_names=[(o.GetName() or "object") for o in (keys_bad[:10] if keys_bad else [])],
                    cam=len(cam_bad) if cam_bad else 0,
                    rdc=int(rdc_bad) if rdc_bad else 0,
                ),
                self._flags(),
            )

            # Store results for selection
            self._lights_bad = lights_bad
            self._vis_bad = vis_bad
            self._keys_bad = keys_bad
            self._cam_bad = cam_bad

        except Exception as e:
            safe_print(f"Error during refresh: {e}")

    # ---- layout
    def CreateLayout(self):
        self.SetTitle(PLUGIN_NAME)

        # Main container with better spacing
        self.GroupBegin(1, c4d.BFH_SCALEFIT|c4d.BFV_SCALEFIT, 1, 0)
        self.GroupBorderSpace(10, 10, 10, 10)

        # Top section - Job & Artist info
        self.GroupBegin(10, c4d.BFH_SCALEFIT, 1, 0)

        # Job info row with Shot ID
        self.GroupBegin(11, c4d.BFH_SCALEFIT, 2, 0)
        self.AddStaticText(0,0,80,0,"Shot ID:",0)
        self.AddEditText(G.SHOT, c4d.BFH_SCALEFIT, 200,0)
        self.GroupEnd()

        # Render Preset tabs and Force buttons
        self.AddSeparatorH(5)
        self.GroupBegin(13, c4d.BFH_SCALEFIT, 1, 0)
        self.AddStaticText(0,0,0,0,"Render Preset:",0)
        self.GroupBegin(14, c4d.BFH_SCALEFIT, 6, 0)
        # Add preset buttons as tabs
        self.AddButton(G.BTN_PRESET_PREVIZ, c4d.BFH_SCALEFIT, 0, 0, "Previz")
        self.AddButton(G.BTN_PRESET_PRERENDER, c4d.BFH_SCALEFIT, 0, 0, "Pre-Render")
        self.AddButton(G.BTN_PRESET_RENDER, c4d.BFH_SCALEFIT, 0, 0, "Render")
        self.AddButton(G.BTN_PRESET_STILLS, c4d.BFH_SCALEFIT, 0, 0, "Stills")
        self.AddButton(G.BTN_FORCE_RENDER, c4d.BFH_SCALEFIT, 0, 0, "Force Settings")
        self.AddButton(G.BTN_FORCE_VERTICAL, c4d.BFH_SCALEFIT, 0, 0, "Force Vertical")
        self.GroupEnd()
        self.GroupEnd()

        # Artist row
        self.AddSeparatorH(8)
        self.GroupBegin(12, c4d.BFH_SCALEFIT, 2, 0)
        self.AddStaticText(0,0,80,0,"Artist:",0)
        self.AddEditText(G.ARTIST, c4d.BFH_SCALEFIT, 0,0)
        self.GroupEnd()

        self.GroupEnd()

        # Monitoring controls section - modernized
        self.AddSeparatorH(12)
        self.GroupBegin(20, c4d.BFH_SCALEFIT, 1, 0)
        self.AddStaticText(0,0,0,0,"Monitoring Controls",0)

        # Update rate and mute controls
        self.GroupBegin(21, c4d.BFH_SCALEFIT, 4, 0)
        self.AddStaticText(0,0,80,0,"Update Rate:",0)
        self.AddEditNumberArrows(G.STEP,0,60,0)
        self.AddStaticText(0,0,50,0,"x 100ms",0)
        self.AddButton(G.BTN_MUTE_ALL, c4d.BFH_SCALEFIT, 0, 0, "Mute All")
        self.GroupEnd()

        # Active watchers as tabs
        self.AddSeparatorH(5)
        self.AddStaticText(0,0,0,0,"Active Watchers:",0)
        self.GroupBegin(35, c4d.BFH_SCALEFIT, 5, 0)
        self.AddButton(G.BTN_WATCH_LIGHTS, c4d.BFH_SCALEFIT, 0, 0, "Lights")
        self.AddButton(G.BTN_WATCH_VIS, c4d.BFH_SCALEFIT, 0, 0, "Visibility")
        self.AddButton(G.BTN_WATCH_KEYS, c4d.BFH_SCALEFIT, 0, 0, "Keyframes")
        self.AddButton(G.BTN_WATCH_CAM, c4d.BFH_SCALEFIT, 0, 0, "Cameras")
        self.AddButton(G.BTN_WATCH_PRESET, c4d.BFH_SCALEFIT, 0, 0, "Presets")
        self.GroupEnd()

        self.GroupEnd()

        # Status area (visual watcher)
        self.AddSeparatorH(12)
        self.GroupBegin(40, c4d.BFH_SCALEFIT|c4d.BFV_SCALEFIT, 1, 0)
        self.AddStaticText(0,0,0,0,"Quality Check Status",0)
        self.AddSeparatorH(5)
        self.AddUserArea(G.CANVAS, c4d.BFH_SCALEFIT|c4d.BFV_SCALEFIT, 0, 200)
        self.ua = StatusArea()
        self.AttachUserArea(self.ua, G.CANVAS)
        self.GroupEnd()

        # Quick Actions - 4x4 grid
        self.AddSeparatorH(12)
        self.GroupBegin(50, c4d.BFH_SCALEFIT, 1, 0)
        self.AddStaticText(0,0,0,0,"Quick Actions",0)
        self.AddSeparatorH(5)

        # First row - Selection buttons
        self.GroupBegin(51, c4d.BFH_SCALEFIT, 4, 0)
        self.AddButton(G.SEL_LIGHTS,c4d.BFH_SCALEFIT,0,0,"Select Bad Lights")
        self.AddButton(G.SEL_VIS,c4d.BFH_SCALEFIT,0,0,"Select Bad Visibility")
        self.AddButton(G.SEL_KEYS,c4d.BFH_SCALEFIT,0,0,"Select Keyframe Issues")
        self.AddButton(G.SEL_CAMS,c4d.BFH_SCALEFIT,0,0,"Select Bad Cameras")
        self.GroupEnd()

        # Second row - Additional tools
        self.GroupBegin(52, c4d.BFH_SCALEFIT, 4, 0)
        self.AddButton(G.BTN_VIBRATE_NULL,c4d.BFH_SCALEFIT,0,0,"Vibrate Null")
        self.AddButton(G.BTN_CAM_RIG,c4d.BFH_SCALEFIT,0,0,"Basic Cam Rig")
        self.AddButton(G.BTN_ASSET_BROWSER,c4d.BFH_SCALEFIT,0,0,"YS-Alembic Browser")
        self.AddButton(G.BTN_INFO, c4d.BFH_SCALEFIT, 0, 0, "Plugin Info & Checks")
        self.GroupEnd()

        self.GroupEnd()

        # Snapshot section - improved layout
        self.AddSeparatorH(12)
        self.GroupBegin(60, c4d.BFH_SCALEFIT, 1, 0)
        self.AddStaticText(0,0,0,0,"Stills Management",0)
        self.AddSeparatorH(5)

        self.GroupBegin(61, c4d.BFH_SCALEFIT, 2, 0)
        self.GroupBorderSpace(5, 5, 5, 5)
        self.AddButton(G.BTN_OPEN_FOLDER, c4d.BFH_SCALEFIT, 0, 0, "Open Your Stills Folder")
        self.AddButton(G.BTN_SNAPSHOT, c4d.BFH_SCALEFIT, 0, 0, "Save Still")
        self.GroupEnd()

        self.GroupEnd()

        self.GroupEnd()  # Main container end

        self.SetTimer(500)
        return True

    def InitValues(self):
        # Initialize watcher states (all active by default)
        self._watcher_states = {
            'lights': True,
            'vis': True,
            'keys': True,
            'cam': True,
            'rdc': True
        }
        self._all_muted = False

        self.SetInt32(G.STEP, 10)

        # Load artist name from computer-level settings
        self._artist_name = GlobalSettings.load_artist_name()
        if self._artist_name:
            self.SetString(G.ARTIST, self._artist_name)

        # Initialize active preset
        self._active_preset = "previz"  # Default preset

        doc = c4d.documents.GetActiveDocument()
        self._sync_from_doc(doc)
        self._refresh()
        self._last_doc = doc
        return True

    def Timer(self, msg):
        doc = c4d.documents.GetActiveDocument()

        # Document change detection
        if doc is not self._last_doc:
            check_cache.clear()  # Clear cache on document change
            self._sync_from_doc(doc)
            self._refresh()
            self._last_doc = doc

        # Live updates
        if self.GetBool(G.LIVE):
            self._refresh()

        return True

    def Command(self, cid, msg):
        doc = c4d.documents.GetActiveDocument()
        if not doc:
            return True

        if cid == G.SHOT:
            self._apply_shot(doc)

        # Handle preset tab buttons
        elif cid == G.BTN_PRESET_PREVIZ:
            self._apply_preset(doc, "previz")
        elif cid == G.BTN_PRESET_PRERENDER:
            self._apply_preset(doc, "pre_render")
        elif cid == G.BTN_PRESET_RENDER:
            self._apply_preset(doc, "render")
        elif cid == G.BTN_PRESET_STILLS:
            self._apply_preset(doc, "stills")

        elif cid == G.BTN_FORCE_RENDER:
            self._force_render_settings(doc)

        elif cid == G.BTN_FORCE_VERTICAL:
            self._force_vertical_aspect(doc)

        # Handle watcher tab buttons
        elif cid == G.BTN_WATCH_LIGHTS:
            self._watcher_states['lights'] = not self._watcher_states['lights']
            self._refresh()
        elif cid == G.BTN_WATCH_VIS:
            self._watcher_states['vis'] = not self._watcher_states['vis']
            self._refresh()
        elif cid == G.BTN_WATCH_KEYS:
            self._watcher_states['keys'] = not self._watcher_states['keys']
            self._refresh()
        elif cid == G.BTN_WATCH_CAM:
            self._watcher_states['cam'] = not self._watcher_states['cam']
            self._refresh()
        elif cid == G.BTN_WATCH_PRESET:
            self._watcher_states['rdc'] = not self._watcher_states['rdc']
            self._refresh()

        elif cid == G.BTN_MUTE_ALL:
            self._all_muted = not self._all_muted
            self._refresh()
            if self._all_muted:
                safe_print("All quality checks muted")
            else:
                safe_print("Quality checks unmuted")

        elif cid == G.ARTIST:
            # Artist name changed - save to global settings
            new_artist_name = self.GetString(G.ARTIST).strip()
            if new_artist_name != self._artist_name:
                self._artist_name = new_artist_name
                GlobalSettings.save_artist_name(self._artist_name)

        elif cid == G.BTN_SNAPSHOT:
            self._take_renderview_snapshot()

        elif cid == G.BTN_OPEN_FOLDER:
            self._open_artist_folder()

        elif cid == G.BTN_INFO:
            self._show_info_dialog()

        elif cid == G.BTN_VIBRATE_NULL:
            self._create_vibrate_null(doc)

        elif cid == G.BTN_CAM_RIG:
            self._create_basic_cam_rig(doc)

        elif cid == G.BTN_ASSET_BROWSER:
            # Open the Asset Browser
            c4d.CallCommand(200000193)  # Open Asset Browser

        elif cid == G.SEL_LIGHTS:
            if hasattr(self, '_lights_bad'):
                _select_objects(doc, self._lights_bad)
                safe_print(f"Selected {len(self._lights_bad)} problematic lights")
            else:
                safe_print("No light issues found")

        elif cid == G.SEL_VIS:
            if hasattr(self, '_vis_bad'):
                _select_objects(doc, self._vis_bad)
                safe_print(f"Selected {len(self._vis_bad)} visibility issues")
            else:
                safe_print("No visibility issues found")

        elif cid == G.SEL_KEYS:
            if hasattr(self, '_keys_bad'):
                _select_objects(doc, self._keys_bad)
                safe_print(f"Selected {len(self._keys_bad)} keyframe issues")
            else:
                safe_print("No keyframe issues found")

        elif cid == G.SEL_CAMS:
            if hasattr(self, '_cam_bad'):
                _select_objects(doc, self._cam_bad)
                safe_print(f"Selected {len(self._cam_bad)} camera shift issues")
            else:
                safe_print("No camera shift issues found")

        elif cid == G.STEP:
            # Update timer interval
            interval = max(100, self.GetInt32(G.STEP) * 100)
            self.SetTimer(interval)
            safe_print(f"Update interval: {interval}ms")

        return True

    def _open_artist_folder(self):
        """Open the artist's output folder"""
        doc = c4d.documents.GetActiveDocument()
        if not doc:
            c4d.gui.MessageDialog("No active document!")
            return

        _snapshot_handler.open_artist_folder(doc, self._artist_name)

    def _create_vibrate_null(self, doc):
        """Merge vibrate null from C4D file"""
        if not doc:
            return

        try:
            # Get path to the C4D file
            plugin_dir = os.path.dirname(os.path.dirname(__file__))
            c4d_file = os.path.join(plugin_dir, "c4d", "VibrateNull.c4d")

            # Check if file exists
            if not os.path.exists(c4d_file):
                safe_print(f"VibrateNull.c4d not found at: {c4d_file}")
                c4d.gui.MessageDialog("VibrateNull.c4d file not found in c4d folder")
                return

            # Merge the C4D file into the current document
            merge_doc = c4d.documents.MergeDocument(doc, c4d_file, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS)

            if merge_doc:
                c4d.EventAdd()
                safe_print("Merged vibrate null from VibrateNull.c4d")
            else:
                safe_print("Failed to merge VibrateNull.c4d")
                c4d.gui.MessageDialog("Failed to merge VibrateNull.c4d")

        except Exception as e:
            safe_print(f"Error merging vibrate null: {e}")
            c4d.gui.MessageDialog(f"Error loading vibrate null: {e}")

    def _force_render_settings(self, doc):
        """Force apply render settings based on active preset"""
        if not doc:
            return

        try:
            # Get the active preset name
            preset_name = self._active_preset

            # Find or create render data with this name
            rd = doc.GetFirstRenderData()
            target_rd = None

            # Search for existing preset
            while rd:
                if (rd.GetName() or "").strip().lower() == preset_name:
                    target_rd = rd
                    break
                rd = rd.GetNext()

            if not target_rd:
                # Create new render data if not found
                target_rd = c4d.documents.RenderData()
                target_rd.SetName(preset_name)
                doc.InsertRenderData(target_rd)
                safe_print(f"Created new render preset: {preset_name}")

            # Apply standard settings and output paths based on preset
            if preset_name == "previz":
                # Low quality for fast preview
                target_rd[c4d.RDATA_XRES] = 1280
                target_rd[c4d.RDATA_YRES] = 720
                target_rd[c4d.RDATA_FRAMERATE] = 25
                # Set output path
                target_rd[c4d.RDATA_PATH] = "../../output/previz/_Shots/$take/$prj"
            elif preset_name == "pre_render":
                # Medium quality
                target_rd[c4d.RDATA_XRES] = 1920
                target_rd[c4d.RDATA_YRES] = 1080
                target_rd[c4d.RDATA_FRAMERATE] = 25
                # Set output path
                target_rd[c4d.RDATA_PATH] = "../../output/pre_render/_Shots/$take/v01/$prj"
            elif preset_name == "render":
                # High quality
                target_rd[c4d.RDATA_XRES] = 1920
                target_rd[c4d.RDATA_YRES] = 1080
                target_rd[c4d.RDATA_FRAMERATE] = 25
                # Set output path
                target_rd[c4d.RDATA_PATH] = "../../output/render/_Shots/$take/v01/$prj"
            elif preset_name == "stills":
                # Still image settings
                target_rd[c4d.RDATA_XRES] = 3840
                target_rd[c4d.RDATA_YRES] = 2160
                target_rd[c4d.RDATA_FRAMERATE] = 25
                # Set output path
                target_rd[c4d.RDATA_PATH] = "../../output/stills/_Shots/$take/v01/$prj"

            # Set as active
            doc.SetActiveRenderData(target_rd)
            c4d.EventAdd()

            c4d.gui.MessageDialog(f"Applied standard settings for '{preset_name}' preset\n\n"
                                 f"Resolution: {target_rd[c4d.RDATA_XRES]}x{target_rd[c4d.RDATA_YRES]}\n"
                                 f"Frame Rate: {target_rd[c4d.RDATA_FRAMERATE]} fps\n"
                                 f"Output Path: {target_rd[c4d.RDATA_PATH]}")

        except Exception as e:
            safe_print(f"Error forcing render settings: {e}")

    def _force_vertical_aspect(self, doc):
        """Force all render presets to 9:16 vertical aspect ratio for social media"""
        if not doc:
            return

        try:
            # Common vertical resolutions (9:16 aspect ratio) and output paths
            vertical_presets = {
                "previz": {
                    "resolution": (720, 1280),
                    "path": "../../output/previz/_Shots/$take/$prj"
                },
                "pre_render": {
                    "resolution": (1080, 1920),
                    "path": "../../output/pre_render/_Shots/$take/v01/$prj"
                },
                "render": {
                    "resolution": (1080, 1920),
                    "path": "../../output/render/_Shots/$take/v01/$prj"
                },
                "stills": {
                    "resolution": (2160, 3840),
                    "path": "../../output/stills/_Shots/$take/v01/$prj"
                }
            }

            changed_count = 0
            rd = doc.GetFirstRenderData()

            while rd:
                preset_name = (rd.GetName() or "").strip().lower()

                if preset_name in vertical_presets:
                    preset_data = vertical_presets[preset_name]
                    width, height = preset_data["resolution"]
                    # Set vertical resolution
                    rd[c4d.RDATA_XRES] = width
                    rd[c4d.RDATA_YRES] = height
                    rd[c4d.RDATA_FRAMERATE] = 25
                    # Set output path
                    rd[c4d.RDATA_PATH] = preset_data["path"]
                    changed_count += 1
                    safe_print(f"Changed '{preset_name}' to {width}x{height} (9:16) with path: {preset_data['path']}")

                rd = rd.GetNext()

            c4d.EventAdd()

            if changed_count > 0:
                c4d.gui.MessageDialog(f"Forced Vertical Aspect (9:16) for Reels/Stories\n\n"
                                     f"Updated {changed_count} render presets:\n"
                                     f"• Previz: 720×1280\n"
                                     f"• Pre-Render: 1080×1920\n"
                                     f"• Render: 1080×1920\n"
                                     f"• Stills: 2160×3840\n\n"
                                     f"All at 25 fps for social media")
            else:
                c4d.gui.MessageDialog("No standard render presets found to update.\n"
                                     "Create presets named: previz, pre_render, render, or stills")

        except Exception as e:
            safe_print(f"Error forcing vertical aspect: {e}")

    def _create_basic_cam_rig(self, doc):
        """Create a basic camera rig with null parent"""
        if not doc:
            return

        # Create camera
        camera = c4d.BaseObject(c4d.Ocamera)
        camera.SetName("Camera")

        # Create null parent
        camera_null = c4d.BaseObject(c4d.Onull)
        camera_null.SetName("Camera_Rig")

        # Set camera as child of null
        camera.InsertUnder(camera_null)

        # Set camera position (offset from null)
        camera[c4d.ID_BASEOBJECT_REL_POSITION] = c4d.Vector(0, 0, -400)

        # Insert into document
        doc.InsertObject(camera_null)
        doc.SetActiveObject(camera_null, c4d.SELECTION_NEW)

        # Set as active camera
        bd = doc.GetRenderBaseDraw()
        if bd:
            bd.SetSceneCamera(camera)

        c4d.EventAdd()

        safe_print("Created basic camera rig")

    def _take_renderview_snapshot(self):
        """Take a snapshot from RenderView"""
        doc = c4d.documents.GetActiveDocument()
        if not doc:
            c4d.gui.MessageDialog("No active document!")
            return

        if not self._artist_name:
            c4d.gui.MessageDialog("Please set your artist name first!")
            return

        _snapshot_handler.take_snapshot(doc, self._artist_name)

    def _show_info_dialog(self):
        """Show comprehensive plugin info and system checks"""
        info = []
        info.append("YS GUARDIAN v1.0 - PLUGIN INFO")
        info.append("-" * 40)
        info.append("")

        # System checks section
        info.append("SYSTEM CHECKS:")
        info.append("-" * 30)

        # Check snapshot system availability
        if SNAPSHOT_AVAILABLE:
            info.append("[OK] Snapshot system modules loaded")
        else:
            info.append("[FAIL] Snapshot modules not available")
            info.append("       Fix: Check plugin installation")

        # Check EXR converter
        if EXR_CONVERTER_AVAILABLE:
            info.append(f"[OK] EXR converter available ({EXR_CONVERTER_METHOD})")
        else:
            info.append("[WARN] EXR converter not configured")

        # Check Python dependencies
        info.append("")
        info.append("PYTHON DEPENDENCIES:")
        info.append("-" * 30)

        # Check OpenEXR
        try:
            import subprocess
            result = subprocess.run(["python", "-c", "import OpenEXR"],
                                 capture_output=True, timeout=2)
            if result.returncode == 0:
                info.append("[OK] OpenEXR-Python installed")
            else:
                info.append("[FAIL] OpenEXR-Python not installed")
                info.append("       Fix: pip install OpenEXR-Python")
        except:
            info.append("[WARN] Could not check OpenEXR")

        # Check Pillow
        try:
            result = subprocess.run(["python", "-c", "from PIL import Image"],
                                 capture_output=True, timeout=2)
            if result.returncode == 0:
                info.append("[OK] Pillow installed")
            else:
                info.append("[WARN] Pillow not installed (optional)")
                info.append("       Fix: pip install Pillow")
        except:
            info.append("[WARN] Could not check Pillow")

        # Check directories
        info.append("")
        info.append("DIRECTORIES:")
        info.append("-" * 30)

        rs_dir = r"C:\cache\rs snapshots"
        if os.path.exists(rs_dir):
            try:
                exr_count = len([f for f in os.listdir(rs_dir) if f.endswith('.exr')])
                info.append(f"[OK] Redshift cache: {exr_count} EXR files")
            except:
                info.append("[OK] Redshift cache exists")
        else:
            info.append("[WARN] Redshift cache folder not found")
            info.append(f"       Expected: {rs_dir}")

        log_dir = r"C:\YS_Guardian_Output"
        if os.path.exists(log_dir):
            info.append("[OK] Log directory exists")
        else:
            info.append("[WARN] Log directory not found")
            info.append(f"       Will create at: {log_dir}")

        # Important notes section
        info.append("")
        info.append("IMPORTANT NOTES:")
        info.append("-" * 30)
        info.append("1. BEFORE SAVING STILL:")
        info.append("   - Take a snapshot in Redshift RenderView first")
        info.append("   - The plugin saves the LATEST snapshot as PNG")
        info.append("")
        info.append("2. SNAPSHOT WORKFLOW:")
        info.append("   - Press Snapshot in Redshift RenderView")
        info.append("   - Click 'Save Still' in YS Guardian")
        info.append("   - Still will be saved to your artist folder")
        info.append("")
        info.append("3. OUTPUT LOCATION:")
        info.append("   Project/Output/[Artist Name]/[Date]/")
        info.append("")
        info.append("4. QUALITY CHECKS:")
        info.append("   - Lights: Must be in 'lights' group")
        info.append("   - Visibility: No viewport/render mismatch")
        info.append("   - Keyframes: Warns about multi-axis keys")
        info.append("   - Cameras: No shift values allowed")
        info.append("   - Presets: Only approved render presets")
        info.append("")
        info.append("-" * 40)
        info.append("Plugin by Yambo (C) 2025")

        # Show the info dialog
        c4d.gui.MessageDialog("\n".join(info))

    def DestroyWindow(self):
        """Clean up when panel closes"""
        pass  # No cleanup needed anymore

def _select_objects(doc, objs):
    """Select objects in the scene"""
    if not doc or not objs:
        return

    def clear(op):
        stack = [op]
        while stack:
            current = stack.pop()
            if current:
                try:
                    current.DelBit(c4d.BIT_ACTIVE)
                except:
                    pass

                child = current.GetDown()
                if child:
                    stack.append(child)

                sibling = current.GetNext()
                if sibling:
                    stack.append(sibling)

    first = doc.GetFirstObject()
    if first:
        clear(first)

    for o in objs:
        try:
            if o:
                o.SetBit(c4d.BIT_ACTIVE)
        except:
            pass

    c4d.EventAdd()

# -------------- registration --------------
class YSPanelCmd(plugins.CommandData):
    dlg = None

    def Execute(self, doc):
        if self.dlg is None:
            self.dlg = YSPanel()
            safe_print("YS Guardian Panel v1.0 initialized")
        # Pass plugin ID as second argument for layout persistence
        return self.dlg.Open(dlgtype=c4d.DLG_TYPE_ASYNC, pluginid=PLUGIN_ID,
                            defaultw=720, defaulth=440)

    def RestoreLayout(self, sec_ref):
        """Required for layout persistence - called when C4D restores layouts"""
        if self.dlg is None:
            self.dlg = YSPanel()
        # Restore the dialog with the plugin ID
        return self.dlg.Restore(pluginid=PLUGIN_ID, secret=sec_ref)

def Register():
    ok = plugins.RegisterCommandPlugin(
        id=PLUGIN_ID,
        str=PLUGIN_NAME,
        info=0,
        icon=c4d.bitmaps.BaseBitmap(),
        help="Open YS Guardian Panel",
        dat=YSPanelCmd()
    )
    if ok:
        safe_print("Guardian panel v1.0 registered successfully")
    else:
        safe_print("Failed to register Guardian panel")
    return ok

if __name__ == "__main__":
    # Print setup info
    print(f"\n{'='*50}")
    print(f"YS Guardian Panel v1.0 - Complete Edition")
    print(f"{'='*50}")

    if SNAPSHOT_AVAILABLE and EXR_CONVERTER_AVAILABLE:
        print(f"Snapshot Support: ENABLED")
        print(f"  Converter: {EXR_CONVERTER_METHOD}")
        print(f"  Tone Mapping: Filmic (cinematic quality)")
    else:
        print(f"Snapshot Support: DISABLED")
        if not SNAPSHOT_AVAILABLE:
            print(f"  Missing dependencies for snapshot support")

    print(f"Watcher Status: ACTIVE")
    print(f"  5 Quality Checks: Lights, Visibility, Keys, Camera, Render")
    print(f"  Real-time Monitoring: Enabled")
    print(f"{'='*50}\n")

    Register()