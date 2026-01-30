"""Fetch pre-built executables from independent GitHub release repos.

This script reads releases.json and either downloads pre-built binaries
for a given platform or lists program names (for pymake --exclude).

Usage:
    # List programs managed by releases.json (for pymake --exclude)
    python fetch_releases.py --manifest releases.json --list

    # Download pre-built binaries for a platform
    python fetch_releases.py --manifest releases.json --ostag mac --outdir mac

    # Download and add to an existing zip
    python fetch_releases.py --manifest releases.json --ostag mac --outdir mac --zip mac.zip
"""

import argparse
import json
import os
import shutil
import stat
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

# platform extensions for executables and libraries
_EXE_EXT = {"win64": ".exe"}
_LIB_EXT = {"linux": ".so", "mac": ".dylib", "macarm": ".dylib", "win64": ".dll"}

GITHUB_URL = "https://github.com/{repo}/releases/download/{tag}/{asset}"


def _load_manifest(path):
    with open(path) as f:
        return json.load(f)


def _all_program_names(manifest):
    """Return sorted list of all output program names across all entries."""
    names = []
    for entry in manifest:
        names.extend(entry["programs"].keys())
    return sorted(names)


def _find_in_zip(zf, basename, ostag):
    """Find a file in a zip archive matching basename with platform extension.

    Searches for the basename with and without platform-specific extensions,
    matching against the filename component (ignoring directory paths within
    the archive).
    """
    exe_ext = _EXE_EXT.get(ostag, "")
    lib_ext = _LIB_EXT.get(ostag, "")
    candidates = [basename + exe_ext]
    if lib_ext:
        candidates.append(basename + lib_ext)
    # also try bare name (unix executables have no extension)
    if exe_ext:
        candidates.append(basename)

    for info in zf.infolist():
        if info.is_dir():
            continue
        member_name = Path(info.filename).name
        if member_name in candidates:
            return info
    return None


def fetch(manifest, ostag, outdir, zip_path=None):
    """Download and extract pre-built programs for the given platform."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    fetched = []
    for entry in manifest:
        repo = entry["repo"]
        tag = entry["tag"]
        asset = entry["assets"].get(ostag)
        if asset is None:
            print(f"  skip {repo}: no asset for {ostag}")
            continue

        url = GITHUB_URL.format(repo=repo, tag=tag, asset=asset)
        print(f"  downloading {repo} {tag} ({asset})")

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            urllib.request.urlretrieve(url, tmp_path)
            with zipfile.ZipFile(tmp_path) as zf:
                for output_name, archive_name in entry["programs"].items():
                    info = _find_in_zip(zf, archive_name, ostag)
                    if info is None:
                        print(f"  warning: {archive_name} not found in {asset}")
                        continue

                    # determine output filename with correct extension
                    _, ext = os.path.splitext(info.filename)
                    out_file = output_name + ext
                    out_path = outdir / out_file

                    # extract to temp then move (handles nested paths in archive)
                    with tempfile.TemporaryDirectory() as extract_dir:
                        zf.extract(info, extract_dir)
                        extracted = Path(extract_dir) / info.filename
                        shutil.copy2(extracted, out_path)

                    # ensure executable permission
                    out_path.chmod(
                        out_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                    )
                    print(f"  {out_file}")
                    fetched.append(out_file)
        finally:
            os.unlink(tmp_path)

    # add fetched programs to zip if requested
    if zip_path and fetched:
        mode = "a" if Path(zip_path).exists() else "w"
        with zipfile.ZipFile(zip_path, mode, zipfile.ZIP_DEFLATED) as zf:
            for fname in fetched:
                zf.write(outdir / fname, fname)
        print(f"  added {len(fetched)} programs to {zip_path}")

    return fetched


def main():
    parser = argparse.ArgumentParser(
        description="Fetch pre-built executables from GitHub releases"
    )
    parser.add_argument(
        "--manifest",
        default="releases.json",
        help="path to releases.json manifest",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list program names and exit (for pymake --exclude)",
    )
    parser.add_argument("--ostag", help="platform tag (linux, mac, macarm, win64)")
    parser.add_argument("--outdir", help="output directory for executables")
    parser.add_argument("--zip", dest="zip_path", help="zip file to add programs to")

    args = parser.parse_args()
    manifest = _load_manifest(args.manifest)

    if args.list:
        print(",".join(_all_program_names(manifest)))
        return

    if not args.ostag or not args.outdir:
        parser.error("--ostag and --outdir are required for fetch mode")

    fetched = fetch(manifest, args.ostag, args.outdir, args.zip_path)
    if not fetched:
        print("warning: no programs fetched", file=sys.stderr)
        sys.exit(1)

    print(f"fetched {len(fetched)} programs")


if __name__ == "__main__":
    main()
