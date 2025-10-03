# -*- coding: utf-8 -*-
import c4d
from c4d import plugins, gui, documents
import os
import json
import time
import subprocess
import sys
import webbrowser
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

# Preset names - normalized to lowercase with underscores
# The system accepts both "pre_render" and "pre-render" (case-insensitive)
PRESETS = ["previz", "pre_render", "render", "stills"]

def normalize_preset_name(name):
    """Normalize preset name: lowercase, replace hyphens/spaces with underscores"""
    if not name:
        return ""
    return name.strip().lower().replace("-", "_").replace(" ", "_")

# Icons removed - using text-based status indicators only

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
    """Check for lights outside proper containers - accepts 'light', 'lights', or 'lighting'"""
    cached = check_cache.get(doc, "lights")
    if cached is not None:
        return cached

    offenders = []
    names = {"light", "lights", "lighting"}
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
    """Check for render setting conflicts - accepts pre_render, pre-render, Pre-Render etc."""
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
                # Normalize the name (lowercase, replace hyphens/spaces with underscores)
                name = normalize_preset_name(rd.GetName() or "")
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
        self.pad = 3  # Tighter padding for terminal look
        self.rowh = 24  # Match select button height
        self.font = c4d.FONT_MONOSPACED  # Terminal-style monospace font
        self.last_draw_time = 0
        self.min_draw_interval = 0.05  # Minimum 50ms between redraws

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
        # Terminal-style colors - like C4D script manager console
        # Using darker, more muted colors for terminal aesthetic
        if n <= 0:
            # Green for OK - muted terminal green
            return ("[ OK ]", c4d.Vector(0.15, 0.15, 0.15))  # Dark gray background
        if n < 5:
            # Yellow/amber for warnings - terminal amber
            return ("[WARN]", c4d.Vector(0.25, 0.20, 0.10))  # Dark amber background
        # Red for errors - terminal red
        return ("[FAIL]", c4d.Vector(0.25, 0.10, 0.10))  # Dark red background

    def _fg(self, bg):
        lum = 0.2126*bg.x + 0.7152*bg.y + 0.0722*bg.z
        return c4d.Vector(0,0,0) if lum > 0.55 else c4d.Vector(1,1,1)

    def DrawMsg(self, x1, y1, x2, y2, msg):
        try:
            self.OffScreenOn()
            w = self.GetWidth(); h = self.GetHeight()

            # Terminal-style dark background (like C4D script manager)
            self.DrawSetPen(c4d.Vector(0.08, 0.08, 0.08))
            self.DrawRectangle(0,0,w,h)

            try:
                self.DrawSetFont(self.font)
            except:
                pass

            x=self.pad; y=self.pad

            def row(label, key, mode="default"):
                nonlocal y
                val = int(self.data.get(key, 0))

                # Terminal-style status and message
                if mode == "lights":
                    if val > 0:
                        status = "[FAIL]"
                        message = f"{val} lights outside lights group"
                        text_col = c4d.Vector(1, 0.3, 0.3)  # Red text
                    else:
                        status = "[ OK ]"
                        message = "All lights properly organized"
                        text_col = c4d.Vector(0.3, 1, 0.3)  # Green text
                elif mode == "vis":
                    if val > 0:
                        status = "[WARN]"
                        names = self.data.get("vis_names", [])
                        first = names[0] if names else "object"
                        message = f"Visibility mismatch on '{first}'" + (f" (+{val-1} more)" if val > 1 else "")
                        text_col = c4d.Vector(1, 1, 0.3)  # Yellow text
                    else:
                        status = "[ OK ]"
                        message = "Visibility settings consistent"
                        text_col = c4d.Vector(0.3, 1, 0.3)  # Green text
                elif mode == "keys":
                    if val > 0:
                        status = "[WARN]"
                        names = self.data.get("keys_names", [])
                        first = names[0] if names else "object"
                        message = f"Multi-axis keys on '{first}'" + (f" (+{val-1} more)" if val > 1 else "")
                        text_col = c4d.Vector(1, 1, 0.3)  # Yellow text
                    else:
                        status = "[ OK ]"
                        message = "Keyframes properly configured"
                        text_col = c4d.Vector(0.3, 1, 0.3)  # Green text
                elif mode == "cam":
                    if val > 0:
                        status = "[FAIL]"
                        message = f"{val} camera(s) with non-zero shift"
                        text_col = c4d.Vector(1, 0.3, 0.3)  # Red text
                    else:
                        status = "[ OK ]"
                        message = "Camera shifts at 0%"
                        text_col = c4d.Vector(0.3, 1, 0.3)  # Green text
                elif mode == "rdc":
                    if val > 0:
                        status = "[FAIL]"
                        message = f"{val} non-standard render preset(s)"
                        text_col = c4d.Vector(1, 0.3, 0.3)  # Red text
                    else:
                        status = "[ OK ]"
                        message = "Render presets compliant"
                        text_col = c4d.Vector(0.3, 1, 0.3)  # Green text
                else:
                    status = "[ OK ]" if val <= 0 else "[FAIL]"
                    message = ""
                    text_col = c4d.Vector(0.3, 1, 0.3) if val <= 0 else c4d.Vector(1, 0.3, 0.3)

                # Draw terminal-style line with status indicator
                status_bg, _ = self._sev(val)

                # Draw subtle background stripe
                self.DrawSetPen(status_bg)
                self.DrawRectangle(int(x), int(y), int(w-self.pad), int(y+self.rowh))

                # Draw terminal-style text
                self.DrawSetTextCol(text_col, c4d.Vector(0,0,0))

                # Format: [STATUS] CHECK_NAME: Message
                check_name = label.ljust(15)

                # Draw status
                self.DrawText(status, int(x+5), int(y+6))

                # Draw check name
                self.DrawSetTextCol(c4d.Vector(0.5, 0.5, 0.5), c4d.Vector(0,0,0))  # Gray for label
                self.DrawText(f"{check_name}:", int(x+55), int(y+6))

                # Draw message
                self.DrawSetTextCol(text_col, c4d.Vector(0,0,0))
                self.DrawText(message, int(x+175), int(y+6))

                y += self.rowh + self.pad

            mapping = [
                ("LIGHTS", "lights", "lights"),
                ("VISIBILITY", "vis", "vis"),
                ("KEYFRAMES", "keys", "keys"),
                ("CAMERAS", "cam", "cam"),
                ("RENDER_PRESETS", "rdc", "rdc"),
            ]

            for label, key, mode in mapping:
                if self.show.get(key, False):
                    row(label, key, mode)

            y += 6
            # Footer text with simplified format (GitHub button will be separate)
            self.DrawSetTextCol(c4d.Vector(0.6, 0.6, 0.6), c4d.Vector(0,0,0))  # Gray color for footer
            footer_text = "YAMBO STUDIO © 2025  YS GUARDIAN  V1.0"
            self.DrawText(footer_text, int(x+6), int(h-18))

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

    # Placeholder buttons (future features)
    BTN_A = 1101
    BTN_B = 1103
    BTN_C = 1104
    BTN_D = 1105

    # Status text fields for quality checks
    STATUS_LIGHTS = 1105
    STATUS_VIS = 1106
    STATUS_KEYS = 1107
    STATUS_CAMS = 1108
    STATUS_PRESET = 1109

    # Select buttons for quality checks (in status area)
    SEL_LIGHTS = 1110
    SEL_VIS = 1111
    SEL_KEYS = 1112
    SEL_CAMS = 1113
    SEL_PRESET = 1114

    # New Quick Action buttons
    BTN_VIBRATE_NULL = 1120
    BTN_CAM_RIG = 1121
    BTN_DROP_TO_FLOOR = 1122  # Drop to Floor functionality
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

    # GitHub link button
    BTN_GITHUB = 1306

class YSPanel(gui.GeDialog):
    def __init__(self):
        super().__init__()
        self._last_doc = None
        self._last_check_time = 0
        self._check_thread = None
        self.ua = None  # StatusArea will be created in CreateLayout
        self._thread_lock = threading.Lock()
        self._pending_results = None
        self._artist_name = ""

        # Store selection results
        self._lights_bad = []
        self._vis_bad = []
        self._keys_bad = []
        self._cam_bad = []
        self._preset_bad = []

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
        """Apply preset - accepts pre_render, pre-render, Pre-Render, etc."""
        if not doc:
            return

        try:
            # Normalize the target preset name
            normalized_target = normalize_preset_name(preset_name)
            rd = doc.GetFirstRenderData()

            while rd:
                # Normalize the render data name for comparison
                normalized_rd = normalize_preset_name(rd.GetName() or "")
                if normalized_rd == normalized_target:
                    doc.SetActiveRenderData(rd)
                    c4d.EventAdd()
                    self._active_preset = normalized_target
                    self._update_preset_buttons()
                    safe_print(f"Switched to render preset: {rd.GetName()} (normalized: {normalized_target})")
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

            # Update visual status area
            lights_count = len(lights_bad) if lights_bad else 0
            vis_count = len(vis_bad) if vis_bad else 0
            keys_count = len(keys_bad) if keys_bad else 0
            cam_count = len(cam_bad) if cam_bad else 0
            rdc_count = int(rdc_bad) if rdc_bad else 0

            # Update StatusArea visual display
            self.ua.set_state(
                dict(
                    lights=lights_count,
                    vis=vis_count,
                    vis_names=[(o.GetName() or "object") for o in (vis_bad[:10] if vis_bad else [])],
                    keys=keys_count,
                    keys_names=[(o.GetName() or "object") for o in (keys_bad[:10] if keys_bad else [])],
                    cam=cam_count,
                    rdc=rdc_count,
                ),
                self._flags(),
            )

            # Enable/disable select buttons based on issues
            self.Enable(G.SEL_LIGHTS, lights_count > 0)
            self.Enable(G.SEL_VIS, vis_count > 0)
            self.Enable(G.SEL_KEYS, keys_count > 0)
            self.Enable(G.SEL_CAMS, cam_count > 0)
            self.Enable(G.SEL_PRESET, rdc_count > 0)

            # Store results for selection
            self._lights_bad = lights_bad
            self._vis_bad = vis_bad
            self._keys_bad = keys_bad
            self._cam_bad = cam_bad
            self._preset_bad = []  # For render presets, we don't track specific objects

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

        # Artist row (moved below Shot ID)
        self.AddSeparatorH(5)
        self.GroupBegin(12, c4d.BFH_SCALEFIT, 2, 0)
        self.AddStaticText(0,0,80,0,"Artist:",0)
        self.AddEditText(G.ARTIST, c4d.BFH_SCALEFIT, 0,0)
        self.GroupEnd()

        # Render Preset tabs and Force buttons
        self.AddSeparatorH(8)
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

        self.GroupEnd()

        # Add separator after Render Presets section
        self.AddSeparatorH(8)

        # Monitoring controls section - modernized
        self.AddSeparatorH(12)
        self.GroupBegin(20, c4d.BFH_SCALEFIT, 1, 0)
        self.AddStaticText(0,0,0,0,"Monitoring Controls",0)
        self.AddSeparatorH(5)  # Add separator after title

        # Update rate and mute controls - cleaner layout with more spacing
        self.GroupBegin(21, c4d.BFH_SCALEFIT, 2, 0)
        # Left side - Update rate controls with wider spacing
        self.GroupBegin(211, c4d.BFH_LEFT, 3, 0)
        self.AddStaticText(0,0,100,0,"Update Rate:",0)  # Increased width
        self.AddEditNumberArrows(G.STEP,0,50,0)
        self.AddStaticText(0,0,70,0,"x 100ms",0)  # Increased width
        self.GroupEnd()
        # Right side - Mute button
        self.GroupBegin(212, c4d.BFH_RIGHT, 1, 0)
        self.AddButton(G.BTN_MUTE_ALL, c4d.BFH_RIGHT, 60, 0, "Mute")
        self.GroupEnd()
        self.GroupEnd()

        # Active watchers as tabs
        self.AddSeparatorH(5)
        self.AddStaticText(0,0,0,0,"Enable/Disable Watchers:",0)  # Changed text
        self.AddSeparatorH(5)  # Add separator after title
        self.GroupBegin(35, c4d.BFH_SCALEFIT, 5, 0)
        self.AddButton(G.BTN_WATCH_LIGHTS, c4d.BFH_SCALEFIT, 0, 0, "Lights")
        self.AddButton(G.BTN_WATCH_VIS, c4d.BFH_SCALEFIT, 0, 0, "Visibility")
        self.AddButton(G.BTN_WATCH_KEYS, c4d.BFH_SCALEFIT, 0, 0, "Keyframes")
        self.AddButton(G.BTN_WATCH_CAM, c4d.BFH_SCALEFIT, 0, 0, "Cameras")
        self.AddButton(G.BTN_WATCH_PRESET, c4d.BFH_SCALEFIT, 0, 0, "Presets")
        self.GroupEnd()

        self.GroupEnd()

        # Status area (visual watcher with color-coded status)
        self.AddSeparatorH(12)
        self.GroupBegin(40, c4d.BFH_SCALEFIT, 1, 0)
        self.AddStaticText(0,0,0,0,"Quality Check Status",0)
        self.AddSeparatorH(5)

        # Visual status area with terminal-style display
        self.GroupBegin(406, c4d.BFH_SCALEFIT, 2, 0)
        self.AddUserArea(G.CANVAS, c4d.BFH_SCALEFIT|c4d.BFV_SCALEFIT, 0, 135)  # Adjusted height for 5 checks
        self.ua = StatusArea()
        self.AttachUserArea(self.ua, G.CANVAS)

        # Buttons column on the right
        self.GroupBegin(407, c4d.BFH_RIGHT|c4d.BFV_TOP, 1, 0)
        self.AddButton(G.SEL_LIGHTS, c4d.BFH_RIGHT, 60, 0, "Select")
        self.AddButton(G.SEL_VIS, c4d.BFH_RIGHT, 60, 0, "Select")
        self.AddButton(G.SEL_KEYS, c4d.BFH_RIGHT, 60, 0, "Select")
        self.AddButton(G.SEL_CAMS, c4d.BFH_RIGHT, 60, 0, "Select")
        self.AddButton(G.SEL_PRESET, c4d.BFH_RIGHT, 60, 0, "Info")
        self.GroupEnd()

        self.GroupEnd()

        self.GroupEnd()

        # Quick Actions - 4x4 grid
        self.AddSeparatorH(12)
        self.GroupBegin(50, c4d.BFH_SCALEFIT, 1, 0)
        self.AddStaticText(0,0,0,0,"Quick Actions",0)
        self.AddSeparatorH(5)

        # First row - Workflow automation buttons
        self.GroupBegin(51, c4d.BFH_SCALEFIT, 4, 0)
        self.AddButton(G.BTN_A,c4d.BFH_SCALEFIT,0,0,"Hierarchy→Layers")
        self.AddButton(G.BTN_B,c4d.BFH_SCALEFIT,0,0,"Solo Layers")
        self.AddButton(G.BTN_C,c4d.BFH_SCALEFIT,0,0,"Search 3D Model")
        self.AddButton(G.BTN_D,c4d.BFH_SCALEFIT,0,0,"Ask ChatGPT")
        self.GroupEnd()

        # Second row - Additional tools
        self.GroupBegin(52, c4d.BFH_SCALEFIT, 4, 0)
        self.AddButton(G.BTN_VIBRATE_NULL,c4d.BFH_SCALEFIT,0,0,"Vibrate Null")
        self.AddButton(G.BTN_CAM_RIG,c4d.BFH_SCALEFIT,0,0,"Basic Cam Rig")
        self.AddButton(G.BTN_DROP_TO_FLOOR,c4d.BFH_SCALEFIT,0,0,"Drop to Floor")
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

        # Add GitHub button with link arrow (↗)
        self.AddSeparatorH(8)
        self.GroupBegin(62, c4d.BFH_SCALEFIT, 1, 0)
        self.AddButton(G.BTN_GITHUB, c4d.BFH_SCALEFIT, 0, 0, "View on GitHub ↗")
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

        elif cid == G.BTN_DROP_TO_FLOOR:
            self._drop_to_floor(doc)

        elif cid == G.BTN_A:
            self._hierarchy_to_layers(doc)

        elif cid == G.BTN_B:
            self._solo_layers(doc)

        elif cid == G.BTN_C:
            self._search_3d_model()

        elif cid == G.BTN_D:
            self._ask_chatgpt()

        elif cid == G.BTN_GITHUB:
            # Open GitHub repository
            import webbrowser
            github_url = "https://github.com/yamb0x/ys-guardian"
            webbrowser.open(github_url)
            safe_print(f"Opening GitHub repository: {github_url}")

        elif cid == G.SEL_LIGHTS:
            if hasattr(self, '_lights_bad') and self._lights_bad:
                _select_objects(doc, self._lights_bad)
                safe_print(f"Selected {len(self._lights_bad)} problematic lights")
            else:
                c4d.gui.MessageDialog("No light issues found to select")

        elif cid == G.SEL_VIS:
            if hasattr(self, '_vis_bad') and self._vis_bad:
                _select_objects(doc, self._vis_bad)
                safe_print(f"Selected {len(self._vis_bad)} visibility issues")
            else:
                c4d.gui.MessageDialog("No visibility issues found to select")

        elif cid == G.SEL_KEYS:
            if hasattr(self, '_keys_bad') and self._keys_bad:
                _select_objects(doc, self._keys_bad)
                safe_print(f"Selected {len(self._keys_bad)} keyframe issues")
            else:
                c4d.gui.MessageDialog("No keyframe issues found to select")

        elif cid == G.SEL_CAMS:
            if hasattr(self, '_cam_bad') and self._cam_bad:
                _select_objects(doc, self._cam_bad)
                safe_print(f"Selected {len(self._cam_bad)} camera shift issues")
            else:
                c4d.gui.MessageDialog("No camera shift issues found to select")

        elif cid == G.SEL_PRESET:
            c4d.gui.MessageDialog("Please ensure only standard render presets exist:\n- previz\n- pre_render\n- render\n- stills")

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
            # Get path to the C4D file (in the same plugin directory)
            plugin_dir = os.path.dirname(__file__)
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

    def _hierarchy_to_layers(self, doc):
        """Link main project nulls and their children to layers with matching names"""
        if not doc:
            return

        safe_print("Starting Hierarchy to Layers sync...")

        # Check for objects outside nulls first
        root_objects = []
        orphan_objects = []

        obj = doc.GetFirstObject()
        while obj:
            # Only consider top-level objects
            if obj.GetUp() is None:
                if obj.GetType() == c4d.Onull:
                    root_objects.append(obj)
                else:
                    # Check if it's a camera or light (they might be allowed outside)
                    obj_type = obj.GetType()
                    if obj_type not in [c4d.Ocamera, c4d.Olight]:
                        orphan_objects.append(obj)
            obj = obj.GetNext()

        # If there are orphan objects, show error
        if orphan_objects:
            orphan_names = [obj.GetName() for obj in orphan_objects[:5]]  # Show first 5
            more = f" and {len(orphan_objects)-5} more" if len(orphan_objects) > 5 else ""

            msg = f"Found {len(orphan_objects)} object(s) outside of null groups:\n"
            msg += "\n".join(orphan_names) + more
            msg += "\n\nPlease organize all objects into null groups first."
            c4d.gui.MessageDialog(msg)
            safe_print(f"Aborted: {len(orphan_objects)} objects found outside null groups")
            return

        # No orphans, proceed with layer sync
        if not root_objects:
            c4d.gui.MessageDialog("No null groups found in the scene.")
            return

        # Start undo
        doc.StartUndo()

        # Get or create layer root
        layer_root = doc.GetLayerObjectRoot()
        if not layer_root:
            safe_print("Error: Could not get layer root")
            doc.EndUndo()
            return

        created_layers = 0
        updated_layers = 0

        for null in root_objects:
            null_name = null.GetName()

            # Find or create layer with matching name (returns layer and is_new flag)
            layer, is_new = self._find_or_create_layer(doc, layer_root, null_name)

            if layer:
                # Assign null and all children to this layer
                self._assign_to_layer_recursive(doc, null, layer)

                if is_new:
                    created_layers += 1
                    safe_print(f"Created new layer '{null_name}' and synced objects")
                else:
                    updated_layers += 1
                    safe_print(f"Updated existing layer '{null_name}' with objects")

        doc.EndUndo()
        c4d.EventAdd()

        # Just report to console, no popup
        safe_print(f"Hierarchy→Layers complete: {created_layers} new, {updated_layers} updated layers, {len(root_objects)} nulls synced")

    def _find_or_create_layer(self, doc, layer_root, name):
        """Find existing layer by name or create new one. Returns (layer, is_new)"""
        # First, search for existing layer
        layer = layer_root.GetDown()
        while layer:
            if layer.GetName() == name:
                return layer, False  # Found existing
            layer = layer.GetNext()

        # Create new layer
        new_layer = c4d.documents.LayerObject()
        new_layer.SetName(name)
        new_layer.InsertUnder(layer_root)

        # Generate unique random color based on layer name hash
        # This ensures same name always gets same color (consistent)
        import hashlib

        # Create hash from name
        name_hash = int(hashlib.md5(name.encode()).hexdigest()[:8], 16)

        # Generate pleasant, distinct colors using golden ratio
        # This creates visually distinct colors that are evenly distributed
        golden_ratio = 0.618033988749895
        hue = (name_hash * golden_ratio) % 1.0

        # Convert HSV to RGB (S=0.6, V=0.95 for pleasant, bright colors)
        saturation = 0.6
        value = 0.95

        def hsv_to_rgb(h, s, v):
            """Convert HSV to RGB"""
            h_i = int(h * 6)
            f = h * 6 - h_i
            p = v * (1 - s)
            q = v * (1 - f * s)
            t = v * (1 - (1 - f) * s)

            if h_i == 0:
                r, g, b = v, t, p
            elif h_i == 1:
                r, g, b = q, v, p
            elif h_i == 2:
                r, g, b = p, v, t
            elif h_i == 3:
                r, g, b = p, q, v
            elif h_i == 4:
                r, g, b = t, p, v
            else:
                r, g, b = v, p, q

            return c4d.Vector(r, g, b)

        unique_color = hsv_to_rgb(hue, saturation, value)
        new_layer[c4d.ID_LAYER_COLOR] = unique_color

        doc.AddUndo(c4d.UNDOTYPE_NEW, new_layer)
        return new_layer, True  # Return new layer and flag

    def _solo_layers(self, doc):
        """Solo selected layers - disable all other layers and their objects"""
        if not doc:
            return

        # Check if any layers are currently disabled (solo is active)
        # If so, restore all layers
        layer_root = doc.GetLayerObjectRoot()
        if not layer_root:
            safe_print("Error: Could not get layer root")
            return

        # Check if we're in solo mode
        def check_solo_mode(layer):
            """Check if any layer is disabled (indicating solo mode)"""
            while layer:
                if not layer[c4d.ID_LAYER_VIEW]:
                    return True
                child = layer.GetDown()
                if child and check_solo_mode(child):
                    return True
                layer = layer.GetNext()
            return False

        first_layer = layer_root.GetDown()
        if first_layer and check_solo_mode(first_layer):
            # We're in solo mode, restore all
            self._unsolo_layers(doc)
            return

        # Get all selected layers
        selected_layers = []

        def collect_selected_layers(layer):
            """Recursively collect selected layers"""
            while layer:
                if layer.GetBit(c4d.BIT_ACTIVE):
                    selected_layers.append(layer)
                # Check children
                child = layer.GetDown()
                if child:
                    collect_selected_layers(child)
                layer = layer.GetNext()

        # Start from first layer
        first_layer = layer_root.GetDown()
        if not first_layer:
            c4d.gui.MessageDialog("No layers found in the scene.\nCreate layers first using Hierarchy→Layers.")
            return

        collect_selected_layers(first_layer)

        if not selected_layers:
            c4d.gui.MessageDialog("Please select one or more layers to solo.")
            return

        safe_print(f"Solo mode: Isolating {len(selected_layers)} layer(s)")

        # Start undo
        doc.StartUndo()

        # Track what we're doing
        layers_disabled = 0
        layers_soloed = 0
        objects_affected = 0

        # First pass: Process all layers
        def process_layer(layer, is_soloed):
            """Process a layer and return count of affected objects"""
            nonlocal layers_disabled, layers_soloed

            doc.AddUndo(c4d.UNDOTYPE_CHANGE, layer)

            if is_soloed:
                # Enable this layer
                layer[c4d.ID_LAYER_VIEW] = True
                layer[c4d.ID_LAYER_RENDER] = True
                layer[c4d.ID_LAYER_MANAGER] = True
                layer[c4d.ID_LAYER_GENERATORS] = True
                layer[c4d.ID_LAYER_DEFORMERS] = True
                layer[c4d.ID_LAYER_EXPRESSIONS] = True  # This controls XPresso
                layer[c4d.ID_LAYER_ANIMATION] = True
                layer[c4d.ID_LAYER_LOCKED] = False
                # Try XPresso specific flag if it exists
                if hasattr(c4d, 'ID_LAYER_XPRESSO'):
                    layer[c4d.ID_LAYER_XPRESSO] = True
                layers_soloed += 1
                safe_print(f"  Enabled layer: {layer.GetName()}")
            else:
                # Disable this layer completely
                layer[c4d.ID_LAYER_VIEW] = False
                layer[c4d.ID_LAYER_RENDER] = False
                layer[c4d.ID_LAYER_MANAGER] = False
                layer[c4d.ID_LAYER_GENERATORS] = False
                layer[c4d.ID_LAYER_DEFORMERS] = False
                layer[c4d.ID_LAYER_EXPRESSIONS] = False  # This controls XPresso
                layer[c4d.ID_LAYER_ANIMATION] = False
                # Try XPresso specific flag if it exists
                if hasattr(c4d, 'ID_LAYER_XPRESSO'):
                    layer[c4d.ID_LAYER_XPRESSO] = False
                layers_disabled += 1

        # Process all layers
        def process_all_layers(layer):
            while layer:
                is_selected = layer in selected_layers
                process_layer(layer, is_selected)

                # Process children
                child = layer.GetDown()
                if child:
                    process_all_layers(child)

                layer = layer.GetNext()

        process_all_layers(first_layer)

        # Second pass: Handle objects without layers (disable them too)
        def disable_unassigned_objects(obj):
            """Disable objects not assigned to any layer"""
            nonlocal objects_affected

            while obj:
                # Check if object has no layer assignment
                if not obj.GetLayerObject(doc):
                    doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)

                    # Disable the object
                    obj[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] = 1  # Hide in editor
                    obj[c4d.ID_BASEOBJECT_VISIBILITY_RENDER] = 1  # Hide in render

                    # Disable generators and deformers
                    obj.SetDeformMode(False)

                    # If it's a generator, try to disable it
                    if obj.GetType() in [c4d.Oarray, c4d.Osymmetry, c4d.Oboole, c4d.Oinstance]:
                        obj[c4d.ID_BASEOBJECT_GENERATOR_FLAG] = False

                    objects_affected += 1

                # Process children
                child = obj.GetDown()
                if child:
                    disable_unassigned_objects(child)

                obj = obj.GetNext()

        # Disable unassigned objects
        first_object = doc.GetFirstObject()
        if first_object:
            disable_unassigned_objects(first_object)

        doc.EndUndo()
        c4d.EventAdd()

        # Report to console
        safe_print(f"Solo Layers complete: {layers_soloed} soloed, {layers_disabled} disabled, {objects_affected} unassigned objects hidden")

    def _unsolo_layers(self, doc):
        """Restore all layers to their default visible state"""
        if not doc:
            return

        safe_print("Restoring all layers...")

        # Get layer root
        layer_root = doc.GetLayerObjectRoot()
        if not layer_root:
            return

        doc.StartUndo()

        layers_restored = 0

        def restore_layer(layer):
            """Restore a layer to default visible state"""
            nonlocal layers_restored

            while layer:
                doc.AddUndo(c4d.UNDOTYPE_CHANGE, layer)

                # Enable everything
                layer[c4d.ID_LAYER_VIEW] = True
                layer[c4d.ID_LAYER_RENDER] = True
                layer[c4d.ID_LAYER_MANAGER] = True
                layer[c4d.ID_LAYER_GENERATORS] = True
                layer[c4d.ID_LAYER_DEFORMERS] = True
                layer[c4d.ID_LAYER_EXPRESSIONS] = True  # This controls XPresso
                layer[c4d.ID_LAYER_ANIMATION] = True
                layer[c4d.ID_LAYER_LOCKED] = False
                # Try XPresso specific flag if it exists
                if hasattr(c4d, 'ID_LAYER_XPRESSO'):
                    layer[c4d.ID_LAYER_XPRESSO] = True

                layers_restored += 1

                # Process children
                child = layer.GetDown()
                if child:
                    restore_layer(child)

                layer = layer.GetNext()

        # Restore all layers
        first_layer = layer_root.GetDown()
        if first_layer:
            restore_layer(first_layer)

        # Restore objects without layers
        def restore_unassigned_objects(obj):
            while obj:
                if not obj.GetLayerObject(doc):
                    doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
                    obj[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] = 2  # Show
                    obj[c4d.ID_BASEOBJECT_VISIBILITY_RENDER] = 2  # Show
                    obj.SetDeformMode(True)
                    if obj.GetType() in [c4d.Oarray, c4d.Osymmetry, c4d.Oboole, c4d.Oinstance]:
                        obj[c4d.ID_BASEOBJECT_GENERATOR_FLAG] = True

                child = obj.GetDown()
                if child:
                    restore_unassigned_objects(child)

                obj = obj.GetNext()

        first_object = doc.GetFirstObject()
        if first_object:
            restore_unassigned_objects(first_object)

        doc.EndUndo()
        c4d.EventAdd()

        safe_print(f"Restored {layers_restored} layers to visible state")

    def _search_3d_model(self):
        """Open 3dsky.org search with user's query"""
        # Ask user what they're looking for with a fun message
        search_term = c4d.gui.InputDialog("Which 3D model you need bro?", "")

        if search_term:
            # Clean up the search term for URL
            import urllib.parse
            encoded_term = urllib.parse.quote(search_term)

            # Construct 3dsky search URL
            search_url = f"https://3dsky.org/3dmodels?query={encoded_term}"

            # Open in browser
            import webbrowser
            webbrowser.open(search_url)

            safe_print(f"Opening 3dsky search for: {search_term}")
        else:
            safe_print("Search cancelled - no search term entered")

    def _ask_chatgpt(self):
        """Open ChatGPT with user's question copied to clipboard"""
        # Ask user for their prompt
        user_prompt = c4d.gui.InputDialog("What Python Tag script do you want to create?", "")

        if user_prompt:
            # Construct the full prompt with role and instructions
            full_prompt = """Role: You are a senior Technical Director and Python developer specializing in Cinema 4D Python Tags. You write production-safe code that creates and manages User Data in a single Python-Tag script. Your outputs must be robust, idempotent (no duplicate UD), and well-commented.

IMPORTANT: The plugin is designed for Cinema 4D 2024. Follow the correct documentation only and do not assume c4d commands and IDs. Use only verified Cinema 4D 2024 API calls.

Rules for Cinema4D scripting help:

Always clarify if the user wants a Python Tag vs a Python Generator vs a Command Script vs a Plugin.

Remember:
- Python Tags cannot permanently add objects, only return one object or change attributes.
- Python Generators are used when the goal is to create many children/geometry procedurally.
- For UI-driven tools (buttons, UD), a Script or Command Plugin is often more appropriate.
- Always explain which object type is correct before coding.

Workflow you must follow (two phases):

Plan first (no code): Outline the tag's behavior, schema (names, data types, default values, constraints), data flow, and how you'll avoid common C4D pitfalls. Confirm whether a Python Tag is the right choice or if a Python Generator would be better.

Then code: Output one complete Python-Tag script (no placeholders, no omissions) ready to paste into a Python Tag. The scripts should generate user data on the null on which the python tag is applied.

The user data controls should be sliders, buttons, dropdowns and anything needed for a clear and smart workflow to generate complex 3D scenes.

The script I am interested to build is: """ + user_prompt

            # Copy full prompt to clipboard
            c4d.CopyStringToClipboard(full_prompt)

            # Open ChatGPT
            import webbrowser
            webbrowser.open("https://chatgpt.com/")

            # Show reminder message
            c4d.gui.MessageDialog(
                "Your Python Tag prompt has been copied to clipboard!\n\n"
                "Just press Ctrl+V (or Cmd+V on Mac) in ChatGPT to paste it.\n\n"
                "ChatGPT will help you create a production-ready Python Tag script."
            )

            safe_print(f"Opened ChatGPT with Python Tag request: {user_prompt[:50]}...")
        else:
            safe_print("ChatGPT cancelled - no script description entered")

    def _assign_to_layer_recursive(self, doc, obj, layer):
        """Assign object and all its children to a layer"""
        if not obj or not layer:
            return

        # Add undo for the object
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)

        # Assign to layer
        obj.SetLayerObject(layer)

        # Process all children recursively
        child = obj.GetDown()
        while child:
            self._assign_to_layer_recursive(doc, child, layer)
            child = child.GetNext()

    def _drop_to_floor(self, doc):
        """Drop selected objects to floor (Y=0 plane) - handles rotation and hierarchy correctly"""
        if not doc:
            return

        # Get selected objects
        selected = doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_SELECTIONORDER)
        if not selected:
            safe_print("Please select one or more objects to drop to floor")
            return

        # Start undo
        doc.StartUndo()

        dropped_count = 0

        for obj in selected:
            # Get object's global matrix
            mg = obj.GetMg()

            # Get cache (the actual geometry for display/render)
            cache = obj.GetCache()
            if cache is None:
                cache = obj.GetDeformCache()

            # If we have a cache, use it to get the accurate global bounding box
            if cache:
                # Initialize with first point
                min_y = None

                # Recursively process cache and all children
                def process_cache(cache_obj, parent_mg):
                    """Recursively get all points from cache hierarchy"""
                    nonlocal min_y

                    if not cache_obj:
                        return

                    # Get cache's local matrix
                    cache_mg = cache_obj.GetMl()
                    # Combine with parent matrix to get global position
                    global_mg = parent_mg * cache_mg

                    # Get points if this is a PointObject
                    if cache_obj.CheckType(c4d.Opoint):
                        points = cache_obj.GetAllPoints()
                        if points:
                            for point in points:
                                # Transform point to global space
                                global_point = global_mg * point
                                if min_y is None or global_point.y < min_y:
                                    min_y = global_point.y

                    # Process children
                    child = cache_obj.GetDown()
                    if child:
                        process_cache(child, global_mg)

                    # Process siblings
                    next_obj = cache_obj.GetNext()
                    if next_obj:
                        process_cache(next_obj, parent_mg)

                # Process cache hierarchy
                process_cache(cache, mg)

                # If we didn't find any points, fall back to bounding box method
                if min_y is None:
                    # Use bounding box as fallback
                    mp = obj.GetMp()
                    rad = obj.GetRad()

                    if rad.GetLength() == 0:
                        rad = c4d.Vector(50, 50, 50)

                    # Calculate all 8 corners
                    corners = [
                        c4d.Vector(mp.x - rad.x, mp.y - rad.y, mp.z - rad.z),
                        c4d.Vector(mp.x + rad.x, mp.y - rad.y, mp.z - rad.z),
                        c4d.Vector(mp.x - rad.x, mp.y + rad.y, mp.z - rad.z),
                        c4d.Vector(mp.x + rad.x, mp.y + rad.y, mp.z - rad.z),
                        c4d.Vector(mp.x - rad.x, mp.y - rad.y, mp.z + rad.z),
                        c4d.Vector(mp.x + rad.x, mp.y - rad.y, mp.z + rad.z),
                        c4d.Vector(mp.x - rad.x, mp.y + rad.y, mp.z + rad.z),
                        c4d.Vector(mp.x + rad.x, mp.y + rad.y, mp.z + rad.z)
                    ]

                    min_y = float('inf')
                    for corner in corners:
                        world_corner = mg * corner
                        if world_corner.y < min_y:
                            min_y = world_corner.y
            else:
                # No cache - use bounding box method
                mp = obj.GetMp()
                rad = obj.GetRad()

                if rad.GetLength() == 0:
                    rad = c4d.Vector(50, 50, 50)

                # Calculate all 8 corners
                corners = [
                    c4d.Vector(mp.x - rad.x, mp.y - rad.y, mp.z - rad.z),
                    c4d.Vector(mp.x + rad.x, mp.y - rad.y, mp.z - rad.z),
                    c4d.Vector(mp.x - rad.x, mp.y + rad.y, mp.z - rad.z),
                    c4d.Vector(mp.x + rad.x, mp.y + rad.y, mp.z - rad.z),
                    c4d.Vector(mp.x - rad.x, mp.y - rad.y, mp.z + rad.z),
                    c4d.Vector(mp.x + rad.x, mp.y - rad.y, mp.z + rad.z),
                    c4d.Vector(mp.x - rad.x, mp.y + rad.y, mp.z + rad.z),
                    c4d.Vector(mp.x + rad.x, mp.y + rad.y, mp.z + rad.z)
                ]

                min_y = float('inf')
                for corner in corners:
                    world_corner = mg * corner
                    if world_corner.y < min_y:
                        min_y = world_corner.y

            # Calculate how much to move the object
            if min_y is not None and abs(min_y) > 0.001:  # Small threshold to avoid tiny movements
                move_distance = -min_y

                # Record undo for position change
                doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)

                # Move the object in global space
                current_pos = obj.GetAbsPos()
                new_pos = c4d.Vector(current_pos.x, current_pos.y + move_distance, current_pos.z)
                obj.SetAbsPos(new_pos)

                dropped_count += 1
                safe_print(f"Dropped '{obj.GetName()}' by {move_distance:.2f} units")

        # End undo
        doc.EndUndo()

        # Update the scene
        c4d.EventAdd()

        # Show result message in console only (no popup for smooth workflow)
        if dropped_count == 1:
            safe_print(f"Dropped 1 object to floor")
        elif dropped_count > 1:
            safe_print(f"Dropped {dropped_count} objects to floor")
        else:
            safe_print("No objects needed dropping - already on floor")

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
        """Show plugin info and debugging information for team support"""
        doc = c4d.documents.GetActiveDocument()
        info = []
        info.append("YS GUARDIAN v1.0 - PLUGIN INFO")
        info.append("")

        # System diagnostics for team debugging
        info.append("SYSTEM CHECKS:")
        info.append("")

        # Cinema 4D version
        try:
            c4d_version = c4d.GetC4DVersion()
            info.append(f"[OK] Cinema 4D version: {c4d_version}")
        except:
            info.append("[WARN] Could not detect C4D version")

        # Plugin installation path
        plugin_dir = os.path.dirname(__file__)
        info.append(f"[OK] Plugin location: {plugin_dir}")

        # Check snapshot system
        if SNAPSHOT_AVAILABLE:
            info.append("[OK] Snapshot system modules loaded")
        else:
            info.append("[FAIL] Snapshot modules not available")
            info.append("       Contact support with this error")

        # Check EXR converter
        if EXR_CONVERTER_AVAILABLE:
            info.append(f"[OK] EXR converter available ({EXR_CONVERTER_METHOD})")
        else:
            info.append("[WARN] EXR converter not configured")
            info.append("       System Python may not be available")

        # Current document info
        info.append("")
        info.append("CURRENT SCENE:")
        info.append("")
        if doc:
            doc_path = doc.GetDocumentPath()
            doc_name = doc.GetDocumentName()
            info.append(f"[OK] Document: {doc_name}")
            if doc_path:
                info.append(f"[OK] Path: {doc_path}")
            else:
                info.append("[WARN] Document not saved yet")

            # Count scene objects
            obj_count = 0
            op = doc.GetFirstObject()
            def count_objects(op):
                count = 0
                while op:
                    count += 1
                    count += count_objects(op.GetDown())
                    op = op.GetNext()
                return count
            obj_count = count_objects(op)
            info.append(f"[OK] Scene objects: {obj_count}")
        else:
            info.append("[WARN] No active document")

        # Check directories
        info.append("")
        info.append("DIRECTORIES:")
        info.append("")

        rs_dir = r"C:\cache\rs snapshots"
        if os.path.exists(rs_dir):
            try:
                exr_count = len([f for f in os.listdir(rs_dir) if f.endswith('.exr')])
                info.append(f"[OK] Redshift cache: {exr_count} EXR files")
            except:
                info.append("[OK] Redshift cache exists")
        else:
            info.append("[WARN] Redshift cache not found")
            info.append(f"       Expected: {rs_dir}")

        log_dir = r"C:\YS_Guardian_Output"
        if os.path.exists(log_dir):
            info.append("[OK] Log directory exists")
        else:
            info.append("[INFO] Log directory will be created on first use")

        # Snapshot workflow and Redshift setup
        info.append("")
        info.append("REDSHIFT SNAPSHOT SETUP (REQUIRED):")
        info.append("")
        info.append("Configure Redshift RenderView first:")
        info.append("1. Open Redshift RenderView")
        info.append("2. Click Preferences (gear icon) -> Snapshots")
        info.append("3. Configuration tab:")
        info.append("   - Set path: C:/cache/rs snapshots")
        info.append("   - Enable 'Save snapshots as EXR'")
        info.append("   - Click OK")
        info.append("")
        info.append("SNAPSHOT WORKFLOW:")
        info.append("")
        info.append("1. Take snapshot in Redshift RenderView")
        info.append("2. Click 'Save Still' in YS Guardian")
        info.append("3. Output: Project/Output/[Artist]/[Date]/")
        info.append("")

        # Quality checks reference
        info.append("QUALITY CHECKS:")
        info.append("")
        info.append("- Lights: Must be in 'lights' group")
        info.append("- Visibility: No viewport/render mismatch")
        info.append("- Keyframes: Warns about multi-axis keys")
        info.append("- Cameras: No shift values allowed")
        info.append("- Presets: Only approved render presets")
        info.append("")

        # Troubleshooting guide
        info.append("TROUBLESHOOTING:")
        info.append("")
        info.append("If experiencing issues, report to team with:")
        info.append("1. Screenshot of this dialog")
        info.append("2. Description of the problem")
        info.append("3. Steps to reproduce")
        info.append("4. Cinema 4D Console output (Shift+F10)")
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
    # Load plugin icon (PNG format for best Cinema 4D compatibility)
    icon = c4d.bitmaps.BaseBitmap()
    icon_path = os.path.join(os.path.dirname(__file__), "icons", "ys-logo-alpha-32.png")

    if os.path.exists(icon_path):
        result = icon.InitWith(icon_path)
        if result[0] == c4d.IMAGERESULT_OK:
            # Validate icon properties
            width = icon.GetBw()
            height = icon.GetBh()
            depth = icon.GetBt()

            if width == 32 and height == 32:
                safe_print(f"Plugin icon loaded: {icon_path} ({width}x{height}, {depth}-bit)")
            else:
                safe_print(f"Warning: Icon loaded but dimensions are {width}x{height}, expected 32x32")
        else:
            safe_print(f"Warning: Failed to load icon from {icon_path}")
            icon = None  # Use no icon instead of empty bitmap
    else:
        safe_print(f"Warning: Icon not found at {icon_path}")
        icon = None  # Use no icon instead of empty bitmap

    ok = plugins.RegisterCommandPlugin(
        id=PLUGIN_ID,
        str=PLUGIN_NAME,
        info=0,
        icon=icon,
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