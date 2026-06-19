# Icons Repository And Updates Design

## Context

The repository now contains an `Icon` folder with the application icon at
`Icon/icon.png`. The GUI currently shows only text in the header, PyInstaller
does not receive an application icon, and release builds do not bundle GUI icon
assets.

The project also needs repository information in the GUI and a way to discover
new public GitHub releases. The repository is currently private, so the
application must handle GitHub returning a not-found response without treating
that as a runtime failure. When the repository becomes public, the same code
should start opening the repository link and checking releases without requiring
an application update.

## Goals

- Use `Icon/icon.png` as the application icon in the GUI.
- Use the same application icon for the Windows EXE build when possible.
- Add a local GitHub icon asset and show it in the GUI next to the application
  icon.
- Make the GitHub icon clickable.
- When the repository is private or not publicly reachable, show a clear GUI
  message instead of opening a broken link.
- When the repository is public, open the repository URL from the GitHub icon.
- Show project and repository information in the GUI.
- Check GitHub releases for a newer public version.
- Show a pulsating `Update` button only when a newer public release exists.
- Download the release EXE after the user clicks `Update`, with progress and log
  messages.

## Non-Goals

- No GitHub authentication token support.
- No automatic replacement of the currently running EXE.
- No installer.
- No background service.
- No update checks when the repository is private or public GitHub API access is
  unavailable.
- No change to release publishing rules other than bundling icon resources and
  applying the EXE icon.

## User Experience

The top of the GUI becomes a compact header containing:

- the application icon from `Icon/icon.png`;
- the application name and current version;
- a GitHub icon button;
- an `Update` button that is hidden by default.

The GitHub icon button first uses repository status discovered by the updater.
If the repository is public, the button opens
`https://github.com/NefilimPL/intrastat-generator`. If the repository is private
or unreachable through the public API, it shows a message saying that the
repository is currently private or unavailable.

The GUI also gains a project/repository information action. It presents:

- project name;
- version;
- description;
- authors;
- license;
- repository URL;
- repository visibility state;
- latest release version when known;
- update asset name and size when known;
- local download location when an update has been downloaded.

When a newer release is found, a visible pulsating `Update` button appears near
the header. Clicking it starts an EXE download. Download progress is reflected
in the existing progress bar, status text, and log. The downloaded file is saved
to an update download directory next to the program. The application tells the
user where the file was saved and that they should close the current program
before running the downloaded EXE.

## Architecture

`src/intrastat_generator/project.py`
: Owns stable project metadata such as repository owner/name, URL, description,
  authors, and license.

`src/intrastat_generator/assets.py`
: Resolves application assets from the external application directory, source
  checkout, or PyInstaller bundle. It finds `Icon/icon.png`, `Icon/github.png`,
  and an optional generated `Icon/icon.ico`.

`src/intrastat_generator/updater.py`
: Owns GitHub public API calls, version comparison, release asset selection, and
  EXE download. It uses only the Python standard library.

`src/intrastat_generator/gui.py`
: Owns Tkinter widgets, icon loading, repository click behavior, update-check
  threading, update progress messages, and project information dialogs.

`.github/workflows/release.yml`
: Stages `Icon` resources for PyInstaller and passes `--icon` when an icon file
  is available.

## Data Flow

1. GUI starts.
2. GUI loads `Icon/icon.png` and `Icon/github.png` through `assets.py`.
3. GUI sets the Tk window icon from the application icon.
4. GUI starts a background update check.
5. The updater requests the public GitHub repository endpoint.
6. A `404` or `403` response marks the repository as private or unavailable.
7. A `200` response marks the repository as public and enables repository link
   opening.
8. For a public repository, the updater requests the latest release endpoint.
9. The updater compares the latest release tag with the current application
   version after stripping build branch suffixes such as `-dev` or `-Main`.
10. If the latest release is newer and contains a Windows `.exe` asset, the GUI
    shows the pulsating `Update` button.
11. Clicking `Update` downloads the selected asset and posts progress to the GUI
    queue.
12. The GUI logs completion and shows the downloaded EXE path.

## Version Comparison

The updater compares semantic release numbers from tags like `v0.0.6` and build
versions like `v0.0.5-dev`. Non-numeric suffixes are ignored for update
ordering. If either side cannot be parsed as a dotted numeric version, the
updater does not offer an update.

Examples:

- current `v0.0.5-dev`, latest `v0.0.6` means update available;
- current `v0.0.6-Main`, latest `v0.0.6` means no update;
- current `0.0.0-dev`, latest `v0.0.1` means update available;
- current `feature-build`, latest `v0.0.1` means no update because current
  version is not comparable.

## Error Handling

Network errors, timeouts, GitHub rate limits, private repository responses, and
missing release assets are non-fatal. They update repository status and log a
short GUI message where useful, but they do not block generation.

Downloads write to a temporary `.part` file first. On success, the `.part` file
is renamed to the final EXE name. Existing files use the existing unique-path
helper so a previous download is not overwritten.

If a download fails, the partial file is removed when possible and the GUI shows
an error message.

## Testing

Add focused tests for:

- project metadata values;
- asset path resolution for source and PyInstaller bundle layouts;
- parsing semantic versions from current and release strings;
- detecting whether a release is newer;
- selecting a Windows EXE release asset;
- repository API status handling for public, private, rate-limited, and network
  failure cases through injectable opener functions;
- release workflow text checks for staging `Icon` resources and passing the EXE
  icon to PyInstaller.

GUI image rendering remains covered lightly through helper functions because
Tkinter widget rendering is environment-dependent in CI.

## Acceptance Criteria

- `Icon/icon.png` is used as the GUI window icon when present.
- A GitHub icon appears next to the application icon in the GUI.
- Clicking the GitHub icon opens the repository when it is public.
- Clicking the GitHub icon shows a private/unavailable message while the
  repository is not public.
- The GUI exposes project and repository information.
- A newer public GitHub release makes a pulsating `Update` button visible.
- Clicking `Update` downloads the release EXE with progress feedback.
- Private repository status does not produce an application error.
- Release builds include icon resources and apply the application icon to the
  Windows EXE when an icon file is available.
