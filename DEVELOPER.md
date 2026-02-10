# Developers

This document provides guidance for using this repository to release USGS executables.

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->


- [Overview](#overview)
- [Program sources](#program-sources)
  - [Fetched from pre-built GitHub releases](#fetched-from-pre-built-github-releases)
  - [Built from source by pymake](#built-from-source-by-pymake)
- [How it works](#how-it-works)
  - [Adding a program](#adding-a-program)
  - [Updating a program](#updating-a-program)
  - [Future `modflow-devtools` migration](#future-modflow-devtools-migration)
- [Triggering a release](#triggering-a-release)
  - [GitHub UI](#github-ui)
  - [GitHub CLI](#github-cli)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Overview

This repository only builds USGS programs and contains none of their source code. Its contents are concerned only with the build and release process. Repository contents have no direct relationship to release cadence or version/tag numbers.

This repo is configured to allow manually triggering releases, independent of changes to version-controlled files.

The `.github/workflows/release.yml` workflow is triggered on the following [events](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows):

- `push` to `master`
- `workflow_dispatch`

If the triggering event is `push`, metadata is updated, binaries are built and uploaded as artifacts, and the workflow ends. This tests whether programs can be built by pymake.

If the triggering event is `workflow_dispatch`:

- Metadata is updated. If changes are detected to any of the program versions or timestamps, a draft PR is opened against the `master` branch to update the table in `README.md`.
- Binaries are built and uploaded as artifacts
- A release is created, incrementing the version number.

**Note**: the release is currently published immediately, but could be changed to a draft by updating the `draft` input on `ncipollo/release-action` in `.github/workflows/release.yml`.

**Note**: version numbers don't currently follow semantic versioning conventions, but simply increment an integer for each release.

## Program sources

The distribution includes programs from across the MODFLOW ecosystem. Each program's source code and/or pre-built binaries come from one of three places: a MODFLOW-ORG GitHub repository with platform binaries, a MODFLOW-ORG repository with source-only releases, or a USGS server. This table tracks the current state as of January 2026.

### Fetched from pre-built GitHub releases

These programs are downloaded as pre-built binaries via `releases.json`. Their repositories publish platform-specific archives (linux.zip, mac.zip, macarm.zip, win64.zip) as release assets.

| Program(s) | Repository | Release tag |
|------------|-----------|-------------|
| mf6, zbud6, mf5to6, libmf6 | [MODFLOW-ORG/modflow6](https://github.com/MODFLOW-ORG/modflow6) | 6.7.0 |
| triangle | [MODFLOW-ORG/triangle](https://github.com/MODFLOW-ORG/triangle) | v1.6 |
| gridgen | [MODFLOW-ORG/gridgen](https://github.com/MODFLOW-ORG/gridgen) | v1.0.02 |
| zonbud | [MODFLOW-ORG/zonbud](https://github.com/MODFLOW-ORG/zonbud) | v3.01 |
| zonbudusg | [MODFLOW-ORG/zonbudusg](https://github.com/MODFLOW-ORG/zonbudusg) | v1.01 |
| mfnwt, mfnwtdbl | [MODFLOW-ORG/mfnwt](https://github.com/MODFLOW-ORG/mfnwt) | v1.3.0 |
| swtv4 | [MODFLOW-ORG/swtv4](https://github.com/MODFLOW-ORG/swtv4) | v4.00.05 |
| mp6 | [MODFLOW-ORG/modpath6](https://github.com/MODFLOW-ORG/modpath6) | v6.0.1 |
| vs2dt | [MODFLOW-ORG/vs2dt](https://github.com/MODFLOW-ORG/vs2dt) | v3.3 |
| mflgr, mflgrdbl | [MODFLOW-ORG/mflgr](https://github.com/MODFLOW-ORG/mflgr) | v2.0.0 |
| mf2000 | [MODFLOW-ORG/mf2000](https://github.com/MODFLOW-ORG/mf2000) | v1.19.01 |

### Built from source by pymake

These programs are compiled by pymake.

| Program(s) | Source |
|------------|--------|
| mf2005, mf2005dbl | [MODFLOW-ORG/mf2005](https://github.com/MODFLOW-ORG/mf2005) |
| mfusg, mfusgdbl | [MODFLOW-ORG/mfusg](https://github.com/MODFLOW-ORG/mfusg) |
| mfusg_gsi | [MODFLOW-ORG/mfusgt](https://github.com/MODFLOW-ORG/mfusgt) |
| mt3dms | [MODFLOW-ORG/mt3dms](https://github.com/MODFLOW-ORG/mt3dms) |
| mt3dusgs | [MODFLOW-ORG/mt3d-usgs](https://github.com/MODFLOW-ORG/mt3d-usgs) |
| mp7 | [USGS](https://water.usgs.gov/water-resources/software/MODPATH/) |
| crt | [USGS](https://water.usgs.gov/ogw/CRT/) |
| sutra | [USGS](https://water.usgs.gov/water-resources/software/sutra/) |

To move a program from "built by pymake" to "fetched from releases", its repository needs to start publishing platform-specific binary archives as GitHub release assets, then an entry can be added to `releases.json` (see [Adding a program](#adding-a-program)).

## How it works

The release workflow uses a hybrid approach: some programs are downloaded as pre-built binaries from their independently managed GitHub repositories, while others are still compiled from source by pymake. This is a stopgap until the [modflow-devtools programs API](https://github.com/MODFLOW-ORG/modflow-devtools/issues/263) is ready to manage all program installations.

The file `releases.json` in the repository root is a manifest listing programs to fetch from GitHub releases. Each entry specifies a source repository, release tag, platform-specific asset filenames, and a mapping of output program names to archive filenames.

During a release build, the workflow:

1. Runs `scripts/fetch_releases.py` to download pre-built binaries for the current platform from each repository listed in `releases.json`.
2. Runs pymake to compile the remaining programs, excluding those already fetched.
3. Combines everything into the platform zip alongside pymake-generated metadata.

The fetch script handles platform-specific file extensions (`.exe`, `.dll`, `.dylib`, `.so`) and supports renaming programs when the archive filename differs from the distribution name (e.g., `mfusgt` in the archive becomes `mfusg_gsi` in the distribution).

### Adding a program

When a program repository begins publishing pre-built platform binaries as release assets, add an entry to `releases.json`:

```json
{
  "repo": "MODFLOW-ORG/<repo>",
  "tag": "<release-tag>",
  "assets": {
    "linux": "linux.zip",
    "mac": "mac.zip",
    "macarm": "macarm.zip",
    "win64": "win64.zip"
  },
  "programs": {
    "<output-name>": "<archive-name>"
  }
}
```

- `repo`: GitHub owner/name
- `tag`: release tag to download from
- `assets`: platform-to-asset-filename mapping (must match the release asset names)
- `programs`: maps the desired output filename to the filename inside the archive. If they are the same, use the same value for both.

The program will automatically be excluded from the pymake build. No workflow changes are needed.

### Updating a program

To update a fetched program to a new release, change the `tag` field in its `releases.json` entry (and update asset filenames if they changed). The next release build will fetch the new version.

To update a program built by pymake, update the program database in the pymake repository.

### Future `modflow-devtools` migration

This hybrid system will be replaced by the [modflow-devtools programs API](https://github.com/MODFLOW-ORG/modflow-devtools/issues/263) once it is ready. At that point, `releases.json` and `scripts/fetch_releases.py` can be removed and replaced with a `programs install` command.

When installation of the full suite is possible with devtools it is possible a combined distribution like this repository becomes less of a necessity, but it becomes trivially maintainable.

## Triggering a release

The `workflow_dispatch` event is GitHub's mechanism for manually triggering workflows. This can be accomplished from the Actions tab in the GitHub UI, or via the [GitHub CLI](https://cli.github.com/manual/gh_workflow_run).

Trigger the `release.yml` workflow to start the release.

### GitHub UI

Navigate to the Actions tab of this repository. Select a workflow. A `Run workflow` button should be visible in an alert at the top of the list of workflow runs. Click the `Run workflow` button, selecting the `master` branch. 

### GitHub CLI

Install and configure the [GitHub CLI](https://cli.github.com/manual/) if needed. Then the following command can be run from the root of your local clone of the repository:

```shell
gh workflow run <workflow>.yml
```

On the first run, the CLI will prompt to choose whether the run should be triggered on your fork of the repository or on the upstream version. This decision is stored for subsequent runs &mdash; to override it later, use the `--repo` (short `-R`) option to specify the repository. For instance, if you initially selected your fork but would like to trigger on the main repository:

```shell
gh workflow run <workflow>.yml -R MODFLOW-ORG/executables
```

**Note:** by default, workflow runs are associated with the repository's default branch. If the repo's default branch is `develop` (as is currently the case for `MODFLOW-ORG/executables`, you will need to use the `--ref` (short `-r`) option to specify the `master` branch when triggering from the CLI. For instance:

```shell
gh workflow run <workflow>.yml -R MODFLOW-ORG/executables -r master
```
