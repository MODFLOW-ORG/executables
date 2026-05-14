"""Patch code.json with correct version info for programs fetched from releases.json.

make-code-json reads versions from pymake's internal program catalog, which may
be out of date relative to the versions actually fetched. This script overwrites
the version (and url) for each program listed in releases.json with the values
from the releases.json manifest.

Usage:
    python patch_code_json.py --manifest releases.json --ostag linux --zip linux.zip
    python patch_code_json.py --manifest releases.json --ostag linux code.json
"""

import argparse
import datetime
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

GITHUB_URL = "https://github.com/{repo}/releases/download/{tag}/{asset}"


def _get_url_date(url):
    """Fetch Last-Modified date from a URL's response headers."""
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as resp:
            for key in ("Last-Modified", "Date"):
                val = resp.headers.get(key)
                if val:
                    dt = datetime.datetime.strptime(val, "%a, %d %b %Y %H:%M:%S %Z")
                    return dt.strftime("%m/%d/%Y")
    except Exception:
        pass
    return None


def patch(manifest_path, code_json_path, ostag, zip_path=None):
    with open(manifest_path) as f:
        manifest = json.load(f)

    code_json_path = Path(code_json_path)
    if not code_json_path.exists():
        print(f"code.json not found: {code_json_path}", file=sys.stderr)
        sys.exit(1)

    with open(code_json_path) as f:
        code = json.load(f)

    changed = []
    for entry in manifest:
        repo = entry["repo"]
        tag = entry["tag"]
        version = tag.lstrip("v")
        asset = entry["assets"].get(ostag)
        url = GITHUB_URL.format(repo=repo, tag=tag, asset=asset) if asset else None

        for prog_name in entry["programs"]:
            if prog_name not in code:
                continue
            prev_version = code[prog_name].get("version")
            if prev_version == version:
                continue
            code[prog_name]["version"] = version
            if url:
                code[prog_name]["url"] = url
                date = _get_url_date(url)
                if date:
                    code[prog_name]["url_download_asset_date"] = date
            changed.append(f"  {prog_name}: {prev_version!r} -> {version!r}")

    if not changed:
        print("code.json already up to date")
        return

    for line in changed:
        print(line)

    code_json_path.write_text(json.dumps(code, indent=4) + "\n")
    print(f"wrote {code_json_path}")

    if zip_path and Path(zip_path).exists():
        with zipfile.ZipFile(zip_path, "a", zipfile.ZIP_DEFLATED) as zf:
            zf.write(code_json_path, "code.json")
        print(f"updated code.json in {zip_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "code_json",
        nargs="?",
        default="code.json",
        help="path to code.json to patch (default: code.json)",
    )
    parser.add_argument(
        "--manifest",
        default="releases.json",
        help="path to releases.json manifest (default: releases.json)",
    )
    parser.add_argument(
        "--ostag",
        required=True,
        help="platform tag (linux, mac, macarm, win64)",
    )
    parser.add_argument(
        "--zip",
        dest="zip_path",
        help="zip file to update with the patched code.json",
    )
    args = parser.parse_args()
    patch(args.manifest, args.code_json, args.ostag, args.zip_path)


if __name__ == "__main__":
    main()
