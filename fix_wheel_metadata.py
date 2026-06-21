#!/usr/bin/env python3
"""Remove problematic License-File field from wheel and sdist metadata for TestPyPI compatibility."""

import zipfile
import tarfile
import tempfile
import os

def fix_metadata_lines(lines):
    """Filter out problematic license metadata lines."""
    filtered = []
    for line in lines:
        if line.startswith(b'License-File:') or line.startswith(b'Dynamic:'):
            print(f"  Removing: {line.decode('utf-8').rstrip()}")
            continue
        filtered.append(line)
    return filtered

# Fix wheel
wheel_path = "dist/semantixrag-2.0.0-py3-none-any.whl"
print(f"\nFixing {wheel_path}...")
with tempfile.TemporaryDirectory() as tmpdir:
    with zipfile.ZipFile(wheel_path, 'r') as whl:
        whl.extractall(tmpdir)
    
    metadata_file = os.path.join(tmpdir, "semantixrag-2.0.0.dist-info/METADATA")
    with open(metadata_file, 'rb') as f:
        lines = f.read().split(b'\n')
    
    lines = [l + b'\n' for l in lines if l]
    filtered = fix_metadata_lines(lines)
    
    with open(metadata_file, 'wb') as f:
        f.write(b''.join(filtered))
    
    os.remove(wheel_path)
    with zipfile.ZipFile(wheel_path, 'w', zipfile.ZIP_DEFLATED) as whl:
        for root, dirs, files in os.walk(tmpdir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, tmpdir)
                whl.write(file_path, arcname)

print(f"✓ Fixed {wheel_path}")

# Fix sdist
sdist_path = "dist/semantixrag-2.0.0.tar.gz"
print(f"\nFixing {sdist_path}...")
with tempfile.TemporaryDirectory() as tmpdir:
    with tarfile.open(sdist_path, 'r:gz') as tar:
        tar.extractall(tmpdir)
    
    metadata_file = os.path.join(tmpdir, "semantixrag-2.0.0/PKG-INFO")
    with open(metadata_file, 'rb') as f:
        lines = f.read().split(b'\n')
    
    lines = [l + b'\n' for l in lines if l]
    filtered = fix_metadata_lines(lines)
    
    with open(metadata_file, 'wb') as f:
        f.write(b''.join(filtered))
    
    os.remove(sdist_path)
    with tarfile.open(sdist_path, 'w:gz') as tar:
        for root, dirs, files in os.walk(tmpdir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, tmpdir)
                tar.add(file_path, arcname=arcname)

print(f"✓ Fixed {sdist_path}")
print("\n✓ Both distributions ready for TestPyPI upload")

