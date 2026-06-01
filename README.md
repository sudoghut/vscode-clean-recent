# VS Code Recent Cleaner

A Python script that removes stale entries from VS Code's **Open Recent** list — entries pointing to folders or files that no longer exist on disk.

## Background

VS Code 1.122+ stores "Open Recent" data in three separate locations:

| Type | Storage Location | Key |
|------|-----------------|-----|
| All recently opened (folders + files) | `~/.vscode-shared/sharedStorage/state.vscdb` | `history.recentlyOpenedPathsList` |
| Folder/workspace profile associations | `%APPDATA%\Code\User\globalStorage\storage.json` | `profileAssociations.workspaces` |
| Per-workspace editor tab history | `%APPDATA%\Code\User\workspaceStorage\*/state.vscdb` | `history.entries` |

The global recently opened list (`~/.vscode-shared/`) is what populates the **File → Open Recent** menu. Older tutorials that look for `history.recentlyOpenedPathsList` in `%APPDATA%\Code\User\globalStorage\state.vscdb` no longer work — that key moved to the shared storage location.

## Requirements

- Python 3.8+
- Windows (VS Code stores data under `%APPDATA%\Code\`)

## Usage

**Close VS Code first**, then run:

```bash
python clean_vscode_recent.py
```

Or on Windows to avoid encoding issues with non-ASCII paths:

```cmd
cmd.exe /c "chcp 65001 >nul && set PYTHONIOENCODING=utf-8 && python clean_vscode_recent.py"
```

The script will:

1. Scan `storage.json` and remove workspace/folder entries whose paths no longer exist
2. Scan all per-workspace SQLite databases and remove file editor history entries whose paths no longer exist
3. Print a summary of what was removed
4. Create a `storage.json.bak` backup before modifying workspace history

Restart VS Code after running to see the updated list.

## What the script does NOT touch

- Remote SSH, WSL, or Dev Container URIs — these are always preserved
- Any data outside of the two storage locations listed above

## Storage location history

| VS Code version | Storage | Key |
|----------------|---------|-----|
| ≤ ~1.74 | `storage.json` (JSON) | `history.recentlyOpenedPathsList` |
| ~1.75 – 1.121 | `state.vscdb` (SQLite) | `history.recentlyOpenedPathsList` |
| 1.122+ | `storage.json` | `profileAssociations.workspaces` |

Version boundaries are approximate — actual behavior is what matters.

## License

MIT
