# -*- coding: utf-8 -*-
"""
Redshift Snapshot Manager - Fixed Version
Directly grabs EXR files from cache folder and converts them
"""

import os
from datetime import datetime

# Import our EXR converter
CONVERTER_AVAILABLE = False
converter_module = None

try:
    # Use the simple converter directly (it's the only one we have)
    from exr_to_png_converter_simple import convert_exr_to_png, get_converter_info
    CONVERTER_AVAILABLE = True
    converter_module = "simple"
    print("Using simple EXR converter with external Python support")
except ImportError as e:
    print(f"Warning: No EXR to PNG converter available - {e}")
    CONVERTER_AVAILABLE = False
    converter_module = None


class RedshiftSnapshotConfig:
    """Configuration for Redshift snapshot management"""

    # The folder where Redshift saves EXR snapshots
    RS_SNAPSHOT_DIR = r"C:\cache\rs snapshots"

    @staticmethod
    def get_scene_snapshot_dir(doc, artist_name):
        """
        Get the organized snapshot directory for the current scene
        Creates a structure like: project_path/Output/artist_name/YYMMDD/
        """
        try:
            # Get project path from document
            project_path = doc.GetDocumentPath()
            print(f"Document path from C4D: {project_path}")

            if not project_path or project_path == "":
                # Fall back to default location
                project_path = r"C:\YS_Guardian_Output"
                print(f"Using fallback path: {project_path}")

            # Build the organized output path
            date_folder = datetime.now().strftime("%y%m%d")
            output_dir = os.path.join(
                project_path,
                "Output",
                artist_name if artist_name else "Unknown",
                date_folder
            )

            print(f"Creating output directory: {output_dir}")

            # Create directory structure if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)

            return output_dir
        except Exception as e:
            import traceback
            print(f"Error creating snapshot directory: {e}")
            traceback.print_exc()
            # Try a simpler fallback
            try:
                fallback_dir = os.path.join(r"C:\YS_Guardian_Output", artist_name or "Unknown", datetime.now().strftime("%y%m%d"))
                os.makedirs(fallback_dir, exist_ok=True)
                print(f"Using fallback directory: {fallback_dir}")
                return fallback_dir
            except:
                return None


class RedshiftSnapshotManager:
    """Manages EXR snapshot conversion and organization"""

    def __init__(self):
        self.rs_dir = RedshiftSnapshotConfig.RS_SNAPSHOT_DIR
        self.processed_files = set()  # Track processed files to avoid duplicates
        self.log_file = r"C:\YS_Guardian_Output\snapshot_log.txt"
        self._init_logging()

    def _init_logging(self):
        """Initialize file logging for debugging"""
        try:
            # Create log directory if it doesn't exist
            log_dir = os.path.dirname(self.log_file)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # Write initial log entry
            with open(self.log_file, 'a') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"YS Guardian Snapshot Manager - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*60}\n")
                f.write(f"Initialized with RS_SNAPSHOT_DIR: {self.rs_dir}\n")
        except Exception as e:
            print(f"Warning: Could not initialize logging: {e}")

    def _log(self, message):
        """Write a message to both console and log file"""
        print(message)
        try:
            with open(self.log_file, 'a') as f:
                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        except:
            pass  # Fail silently if logging fails

    def find_latest_exr(self):
        """Find the most recent EXR file in the Redshift snapshot directory"""
        if not os.path.exists(self.rs_dir):
            self._log(f"Snapshot directory not found: {self.rs_dir}")
            return None

        try:
            # Find all EXR files
            exr_files = []
            self._log(f"Searching for EXR files in {self.rs_dir}")
            for file in os.listdir(self.rs_dir):
                if file.lower().endswith('.exr'):
                    full_path = os.path.join(self.rs_dir, file)
                    # Get modification time
                    mtime = os.path.getmtime(full_path)
                    exr_files.append((full_path, mtime))
                    self._log(f"  Found: {file} (modified: {datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')})")

            if not exr_files:
                self._log(f"No EXR files found in {self.rs_dir}")
                return None

            # Sort by modification time (newest first)
            exr_files.sort(key=lambda x: x[1], reverse=True)

            # Return the newest file
            latest_file = exr_files[0][0]
            self._log(f"Selected latest EXR: {os.path.basename(latest_file)}")
            return latest_file

        except Exception as e:
            self._log(f"Error finding EXR files: {e}")
            import traceback
            self._log(f"Traceback: {traceback.format_exc()}")
            return None

    def process_snapshot(self, doc, artist_name):
        """
        Main function to process a snapshot:
        1. Find latest EXR in cache folder
        2. Convert to PNG
        3. Save to artist's daily folder
        """
        self._log("=" * 40)
        self._log("Starting snapshot process")
        self._log(f"Artist: {artist_name}")
        self._log(f"Converter module: {converter_module if converter_module else 'None available'}")

        if not CONVERTER_AVAILABLE:
            error_msg = "EXR converter not available. Please install OpenEXR."
            self._log(f"Error: {error_msg}")
            return None, error_msg

        # Find the latest EXR file
        exr_path = self.find_latest_exr()
        if not exr_path:
            error_msg = "No EXR snapshots found in cache folder.\nPlease take a snapshot in Redshift RenderView first."
            self._log(f"Error: {error_msg}")
            return None, error_msg

        # Check if we've already processed this file recently (within last 2 seconds)
        file_key = f"{exr_path}_{os.path.getmtime(exr_path)}"
        if file_key in self.processed_files:
            msg = f"File already processed: {os.path.basename(exr_path)}"
            self._log(msg)
            return None, "This snapshot was already converted."

        # Get output directory
        self._log("Getting output directory...")
        output_dir = RedshiftSnapshotConfig.get_scene_snapshot_dir(doc, artist_name)
        if not output_dir:
            error_msg = "Failed to create output directory"
            self._log(f"Error: {error_msg}")
            return None, error_msg
        self._log(f"Output directory: {output_dir}")

        try:
            # Get scene name from document
            doc_name = doc.GetDocumentName()
            if doc_name:
                # Remove .c4d extension
                scene_name = os.path.splitext(doc_name)[0]
            else:
                scene_name = "untitled"
            self._log(f"Scene name: {scene_name}")

            # Create output filename (without timestamp)
            output_filename = f"{scene_name}.png"
            output_path = os.path.join(output_dir, output_filename)

            # Convert EXR to PNG
            self._log(f"Converting {os.path.basename(exr_path)} to PNG...")
            self._log(f"  From: {exr_path}")
            self._log(f"  To: {output_path}")

            # Import traceback for better error reporting
            import traceback

            try:
                self._log("Calling convert_exr_to_png...")
                success = convert_exr_to_png(exr_path, output_path)
                self._log(f"Conversion result: {success}")
            except Exception as conv_error:
                self._log(f"Conversion exception: {conv_error}")
                self._log(f"Traceback: {traceback.format_exc()}")
                return None, f"Conversion error: {str(conv_error)}"

            if success:
                # Mark as processed
                self.processed_files.add(file_key)

                # Clean old entries from processed files (keep only last 10)
                if len(self.processed_files) > 10:
                    self.processed_files = set(list(self.processed_files)[-10:])

                self._log(f"SUCCESS: Snapshot saved: {output_path}")
                return output_path, None
            else:
                # Check if output file was created despite failure
                if os.path.exists(output_path):
                    self._log(f"Warning: Output file exists but conversion reported failure")
                    self._log(f"File size: {os.path.getsize(output_path)} bytes")
                    return output_path, None
                else:
                    self._log(f"Conversion failed - no output file created")
                    return None, "Failed to convert EXR to PNG - check log file at C:\\YS_Guardian_Output\\snapshot_log.txt"

        except Exception as e:
            import traceback
            self._log(f"Error processing snapshot: {e}")
            self._log(f"Traceback: {traceback.format_exc()}")
            return None, f"Error: {str(e)}"

    def cleanup_old_exr_files(self, keep_last=5):
        """Optional: Clean up old EXR files to save disk space"""
        if not os.path.exists(self.rs_dir):
            return

        try:
            # Find all EXR files
            exr_files = []
            for file in os.listdir(self.rs_dir):
                if file.lower().endswith('.exr'):
                    full_path = os.path.join(self.rs_dir, file)
                    mtime = os.path.getmtime(full_path)
                    exr_files.append((full_path, mtime))

            # Sort by modification time (newest first)
            exr_files.sort(key=lambda x: x[1], reverse=True)

            # Delete old files (keep only the specified number)
            for file_path, _ in exr_files[keep_last:]:
                try:
                    os.remove(file_path)
                    self._log(f"Deleted old EXR: {os.path.basename(file_path)}")
                except:
                    pass

        except Exception as e:
            self._log(f"Error cleaning up old files: {e}")


# Global instance
_snapshot_manager = None

def get_snapshot_manager():
    """Get or create the global snapshot manager"""
    global _snapshot_manager
    if _snapshot_manager is None:
        _snapshot_manager = RedshiftSnapshotManager()
    return _snapshot_manager