"""
clean_vscode_recent.py
Removes stale entries from VS Code's "Open Recent" list.

Covers two storage locations used by VS Code 1.122+:
  1. Workspace/folder history  -> storage.json (profileAssociations.workspaces)
  2. File editor history        -> workspaceStorage/*/state.vscdb (history.entries)

Remote and WSL URIs are never touched.
VS Code must be closed before running this script.
"""

import json
import os
import shutil
import sqlite3
import glob
import sys
import tempfile
from urllib.parse import unquote

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def uri_to_local_path(uri: str):
    """
    Convert a VS Code file URI to a local filesystem path.
    Returns None for remote/WSL URIs so they are always preserved.
    """
    if not uri:
        return None
    if uri.startswith("file:///"):
        path = unquote(uri[8:])
    elif uri.startswith("file://"):
        path = unquote(uri[7:])
    else:
        return None  # vscode-remote://, wsl+//, etc. — skip

    # /C:/foo  ->  C:/foo  (Windows drive letter)
    if len(path) > 3 and path[0] == "/" and path[2] == ":":
        path = path[1:]
    return path


# ---------------------------------------------------------------------------
# Part 1: workspace/folder history  (storage.json)
# ---------------------------------------------------------------------------

def clean_workspace_history():
    storage_path = os.path.expandvars(
        r"%APPDATA%\Code\User\globalStorage\storage.json"
    )
    if not os.path.exists(storage_path):
        print("[workspace] storage.json not found, skipping.")
        return

    try:
        with open(storage_path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[workspace] Failed to read storage.json: {e}")
        return

    workspaces = data.get("profileAssociations", {}).get("workspaces", {})
    print(f"[workspace] Found {len(workspaces)} entries.")

    kept = {}
    removed = []
    for uri, profile in workspaces.items():
        path = uri_to_local_path(uri)
        if path is None or os.path.exists(path):
            kept[uri] = profile
        else:
            removed.append(uri)

    if not removed:
        print("[workspace] Nothing to remove.")
        return

    print(f"[workspace] Removing {len(removed)} stale entries:")
    for uri in removed:
        print(f"  - {unquote(uri)}")

    # Back up before modifying
    backup = storage_path + ".bak"
    shutil.copy2(storage_path, backup)
    print(f"[workspace] Backup saved to {backup}")

    # Atomic write: write to a temp file in the same directory, then replace
    data["profileAssociations"]["workspaces"] = kept
    storage_dir = os.path.dirname(storage_path)
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=storage_dir,
            delete=False, suffix=".tmp"
        ) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp_path = tmp.name
        os.replace(tmp_path, storage_path)
    except OSError as e:
        print(f"[workspace] Failed to write storage.json: {e}")
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return

    print(f"[workspace] Done. Kept {len(kept)}, removed {len(removed)}.")


# ---------------------------------------------------------------------------
# Part 2: per-workspace file editor history  (workspaceStorage/*/state.vscdb)
# ---------------------------------------------------------------------------

def clean_file_history():
    ws_base = os.path.expandvars(r"%APPDATA%\Code\User\workspaceStorage")
    db_paths = glob.glob(os.path.join(ws_base, "*", "state.vscdb"))
    print(f"\n[file history] Scanning {len(db_paths)} workspace databases...")

    total_removed = 0
    total_kept = 0
    dbs_updated = 0

    for db_path in db_paths:
        conn = None
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(
                "SELECT value FROM ItemTable WHERE key = 'history.entries'"
            )
            row = cur.fetchone()
            if not row:
                continue

            entries = json.loads(row[0])
            kept = []
            removed_uris = []

            for entry in entries:
                resource = entry.get("editor", {}).get("resource", "")
                path = uri_to_local_path(resource)
                if path is None or os.path.exists(path):
                    kept.append(entry)
                else:
                    removed_uris.append(resource)

            if removed_uris:
                print(f"\n  DB: {db_path}")
                for uri in removed_uris:
                    print(f"    - {unquote(uri)}")
                cur.execute(
                    "UPDATE ItemTable SET value = ? WHERE key = 'history.entries'",
                    (json.dumps(kept),),
                )
                conn.commit()
                total_removed += len(removed_uris)
                dbs_updated += 1

            total_kept += len(kept)

        except sqlite3.Error as e:
            print(f"  [warning] SQLite error in {db_path}: {e}")
        except (json.JSONDecodeError, OSError) as e:
            print(f"  [warning] Error processing {db_path}: {e}")
        finally:
            if conn:
                conn.close()

    print(
        f"\n[file history] Done. Updated {dbs_updated} databases, "
        f"removed {total_removed} stale entries, kept {total_kept}."
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("VS Code Recent Cleaner")
    print("Make sure VS Code is closed before proceeding.\n")
    clean_workspace_history()
    clean_file_history()
    print("\nAll done. Restart VS Code to see the changes.")
