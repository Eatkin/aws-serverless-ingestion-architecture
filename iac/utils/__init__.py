import os
import shutil
import subprocess
import sys
import tempfile


def bundle_directory(source: str, bundle_name: str, common: str = "../common") -> None:
    """Bundles source directory into a zip of bundle name
    Bundle"""
    ignore_pattern = shutil.ignore_patterns(
        "__pycache__", "*.pyc", "venv", ".mppy_cache"
    )
    with tempfile.TemporaryDirectory() as build:

        shutil.copytree(source, build, dirs_exist_ok=True, ignore=ignore_pattern)
        shutil.copytree(
            common,
            os.path.join(build, "common"),
            dirs_exist_ok=True,
            ignore=ignore_pattern,
        )

        req_file = os.path.join(build, "requirements.txt")
        if os.path.exists(req_file):
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    req_file,
                    "-t",
                    build,
                    "--platform",
                    "manylinux2014_x86_64",
                    "--only-binary=:all:",
                    "--upgrade",
                    "--no-cache-dir",
                    "--python-version", "3.12"
                ],
                check=True,
            )
        else:
            raise Exception(f"No requirements.txt found in {source}")

        shutil.make_archive(bundle_name, "zip", build)
