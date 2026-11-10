"""Patch code.json with correct version info for programs fetched from releases.json.

make-code-json reads versions from pymake's internal program catalog, which may
be out of date relative to the versions actually fetched. This script overwrites
the version (and url) for each program listed in releases.json with the values
from the releases.json manifest, then regenerates code.md (also written by
make-code-json from the same stale data) from the patched code.json.

If --zip is given, the patched code.json is added to the archive. This script
is meant to be the only thing that puts code.json in the zip, so make-code-json
should be run *without* --zip; if the archive already contains a code.json the
script fails rather than writing a duplicate entry.

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


def write_code_md(code, code_md_path):
    """Write the code.md table in the same format as pymake's make-code-json."""
    lines = [
        "| Program | Version | UTC Date |",
        "| ------- | ------- | ---- |",
    ]
    for target in sorted(code):
        target_dict = code[target]
        date = target_dict.get("url_download_asset_date")
        line = f"| {target} | {target_dict['version']} |"
        line += f" {date} |" if date else " |"
        lines.append(line)
    Path(code_md_path).write_text("\n".join(lines) + "\n")
    print(f"wrote {code_md_path}")


def patch(
    manifest_path,
    code_json_path,
    ostag,
    zip_path=None,
    code_md_path=None,
):
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

    if changed:
        for line in changed:
            print(line)
        code_json_path.write_text(json.dumps(code, indent=4) + "\n")
        print(f"wrote {code_json_path}")
    else:
        print("code.json already up to date")

    if code_md_path:
        write_code_md(code, code_md_path)

    if zip_path:
        with zipfile.ZipFile(zip_path, "a", zipfile.ZIP_DEFLATED) as zf:
            if "code.json" in zf.namelist():
                print(
                    f"{zip_path} already contains code.json; run make-code-json "
                    "without --zip so this script is the only writer",
                    file=sys.stderr,
                )
                sys.exit(1)
            zf.write(code_json_path, "code.json")
        print(f"added code.json to {zip_path}")


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
        help="zip file to add the patched code.json to",
    )
    parser.add_argument(
        "--code-md",
        dest="code_md_path",
        default="code.md",
        help="path to code.md to regenerate from the patched code.json "
        "(default: code.md; pass an empty string to skip)",
    )
    args = parser.parse_args()
    patch(
        args.manifest,
        args.code_json,
        args.ostag,
        args.zip_path,
        args.code_md_path or None,
    )


if __name__ == "__main__":
    main()
