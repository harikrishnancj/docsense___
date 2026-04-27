import os
import tempfile
from pathlib import Path

# Define a temporary directory on the D: drive where there is plenty of space
PROJECT_TEMP_DIR = Path("d:/Docsense/DocSense/tmp_files")

def setup_temp_dir():
    """
    Ensures a custom temporary directory exists on the D: drive and
    configures environment variables to redirect libraries (like Camelot/Ghostscript) 
    to use this directory instead of the full C: drive.
    """
    # Create the directory if it doesn't exist
    PROJECT_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    
    # Absolute path for the temp dir
    abs_temp_path = str(PROJECT_TEMP_DIR.absolute())
    
    # 1. Update Python's internal tempfile directory
    tempfile.tempdir = abs_temp_path
    
    # 2. Update environment variables for subprocesses and other libraries
    # This covers most libraries that use tempfile or system temp paths
    os.environ["TEMP"] = abs_temp_path
    os.environ["TMP"] = abs_temp_path
    os.environ["TMPDIR"] = abs_temp_path
    
    print(f"✅ Temporary file directory redirected to: {abs_temp_path}")

# Run setup on import to ensure early redirection
setup_temp_dir()
