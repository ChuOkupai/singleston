#!/usr/bin/env python3
"""
Multi-version Python build testing script for singleston.

This script tests the build process across Python 3.9, 3.10, 3.11, and 3.12.
"""

import subprocess
import sys
import os
import tempfile
import shutil
from pathlib import Path


# Python versions to test
PYTHON_VERSIONS = ['3.9', '3.10', '3.11', '3.12']
PYTHON_EXECUTABLES = [f'/opt/homebrew/bin/python{version}' for version in PYTHON_VERSIONS]


def run_command(cmd, cwd=None, capture_output=True):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def test_python_version(python_exe):
    """Test the build process for a specific Python version."""
    print(f"\n{'='*60}")
    print(f"Testing Python {python_exe}")
    print(f"{'='*60}")

    # Check if Python executable exists
    if not os.path.exists(python_exe):
        print(f"❌ Python executable {python_exe} not found")
        return False

    # Get Python version
    success, stdout, stderr = run_command(f"{python_exe} --version")
    if not success:
        print(f"❌ Failed to get Python version: {stderr}")
        return False

    python_version = stdout.strip()
    print(f"✅ Found {python_version}")

    # Create a temporary virtual environment
    with tempfile.TemporaryDirectory() as temp_dir:
        venv_path = os.path.join(temp_dir, "test_venv")

        print(f"📦 Creating virtual environment at {venv_path}")
        success, stdout, stderr = run_command(f"{python_exe} -m venv {venv_path}")
        if not success:
            print(f"❌ Failed to create virtual environment: {stderr}")
            return False

        # Determine the correct pip executable path
        if sys.platform == "win32":
            pip_exe = os.path.join(venv_path, "Scripts", "pip")
            python_venv_exe = os.path.join(venv_path, "Scripts", "python")
        else:
            pip_exe = os.path.join(venv_path, "bin", "pip")
            python_venv_exe = os.path.join(venv_path, "bin", "python")

        # Upgrade pip
        print("📦 Upgrading pip")
        success, stdout, stderr = run_command(f"{python_venv_exe} -m pip install --upgrade pip")
        if not success:
            print(f"❌ Failed to upgrade pip: {stderr}")
            return False

        # Install build dependencies
        print("📦 Installing build dependencies")
        success, stdout, stderr = run_command(f"{pip_exe} install build wheel setuptools")
        if not success:
            print(f"❌ Failed to install build dependencies: {stderr}")
            return False

        # Build the package
        project_root = os.getcwd()
        print(f"🔨 Building package from {project_root}")
        success, stdout, stderr = run_command(f"{python_venv_exe} -m build", cwd=project_root)
        if not success:
            print(f"❌ Failed to build package: {stderr}")
            return False
        print("✅ Package built successfully")

        # Install the built package
        print("📦 Installing built package")
        dist_dir = os.path.join(project_root, "dist")
        if os.path.exists(dist_dir):
            # Find the wheel file
            wheel_files = [f for f in os.listdir(dist_dir) if f.endswith('.whl')]
            if wheel_files:
                wheel_file = os.path.join(dist_dir, wheel_files[-1])  # Use the latest wheel
                success, stdout, stderr = run_command(f"{pip_exe} install {wheel_file}")
                if not success:
                    print(f"❌ Failed to install wheel: {stderr}")
                    return False
                print("✅ Wheel installed successfully")
            else:
                print("⚠️  No wheel file found, trying tarball")
                tarball_files = [f for f in os.listdir(dist_dir) if f.endswith('.tar.gz')]
                if tarball_files:
                    tarball_file = os.path.join(dist_dir, tarball_files[-1])
                    success, stdout, stderr = run_command(f"{pip_exe} install {tarball_file}")
                    if not success:
                        print(f"❌ Failed to install tarball: {stderr}")
                        return False
                    print("✅ Tarball installed successfully")
                else:
                    print("❌ No distributable files found")
                    return False

        # Test the installed package
        print("🧪 Testing installed package")
        success, stdout, stderr = run_command(f"{python_venv_exe} -c 'import scripts.singleston; print(\"Import successful\")'")
        if not success:
            print(f"❌ Failed to import package: {stderr}")
            return False
        print("✅ Package import successful")

        # Test the command line interface
        print("🧪 Testing command line interface")
        success, stdout, stderr = run_command(f"{python_venv_exe} -m scripts.singleston --version")
        if not success:
            print(f"❌ Failed to run CLI: {stderr}")
            return False
        print(f"✅ CLI working: {stdout.strip()}")

        # Run unit tests with this Python version
        print("🧪 Running unit tests")
        success, stdout, stderr = run_command(f"{python_venv_exe} -m unittest discover tests/ -v", cwd=project_root)
        if not success:
            print(f"❌ Unit tests failed: {stderr}")
            return False
        print("✅ Unit tests passed")

    return True


def main():
    """Main function to test all Python versions."""
    print("🐍 Multi-version Python Build Testing for Singleston")
    print(f"Testing Python versions: {', '.join(PYTHON_VERSIONS)}")

    # Clean up any previous builds
    print("\n🧹 Cleaning up previous builds")
    dist_dir = "dist"
    build_dir = "build"
    egg_info_dirs = [d for d in os.listdir(".") if d.endswith(".egg-info")]

    for cleanup_dir in [dist_dir, build_dir] + egg_info_dirs:
        if os.path.exists(cleanup_dir):
            shutil.rmtree(cleanup_dir)
            print(f"✅ Removed {cleanup_dir}")

    results = {}

    for python_exe in PYTHON_EXECUTABLES:
        version = python_exe.split('python')[-1]
        try:
            success = test_python_version(python_exe)
            results[version] = success
        except Exception as e:
            print(f"❌ Unexpected error testing Python {version}: {e}")
            results[version] = False

        # Clean up build artifacts between tests
        for cleanup_dir in [dist_dir, build_dir] + [d for d in os.listdir(".") if d.endswith(".egg-info")]:
            if os.path.exists(cleanup_dir):
                shutil.rmtree(cleanup_dir)

    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    for version, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"Python {version}: {status}")

    total_tests = len(results)
    passed_tests = sum(results.values())
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("🎉 All tests passed!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
