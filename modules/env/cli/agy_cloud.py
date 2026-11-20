#!/usr/bin/env python3
"""
agy_cloud.py - Antigravity Cloud Bridge CLI
Communicates with the cloud runner hosted on Hugging Face Spaces (Jishnupg/Hermes)
backed by 16 vCPUs and persistent Google Drive storage.
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

DEFAULT_URL = os.environ.get("AGY_CLOUD_URL", "https://<YOUR_CLOUD_RUNNER_URL>/antigravity")
AUTH_TOKEN = os.environ.get("AGY_CLOUD_TOKEN", os.environ.get("AUTH_TOKEN", ""))

CLOUD_KEYWORDS = [
    "pip ", "pip3 ", "npm ", "npx ", "pnpm ", "yarn ",
    "pytest", "python -m venv", "python3 -m venv",
    "cargo ", "rustc ", "go build", "go run", "go test",
    "make ", "cmake ", "ninja ", "gcc ", "g++ ", "clang ",
    "git clone", "docker ", "uvicorn ", "fastapi "
]

def make_request(path: str, data: dict = None, method: str = "GET") -> dict:
    url = f"{DEFAULT_URL.rstrip('/')}/{path.lstrip('/')}"
    headers = {
        "User-Agent": "Antigravity-Android-Client/2.4"
    }
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = "POST"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return {"ok": False, "status_code": e.code, "error": f"HTTP {e.code}: {err_body}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def should_route_to_cloud(command: str) -> bool:
    """Returns True if the command is a heavy development task that should execute in the cloud."""
    cmd_lower = command.lower().strip()
    return any(kw in cmd_lower for kw in CLOUD_KEYWORDS)

def cmd_status():
    print(f"Connecting to Antigravity Cloud ({DEFAULT_URL})...")
    res = make_request("healthz")
    if "status" in res and res.get("status") == "online":
        print("✅ Antigravity Cloud is ONLINE!")
        print(f"   Hardware  : Intel Xeon Platinum (16 vCPUs)")
        print(f"   Workspace : {res.get('workspace')}")
        print(f"   Mounted   : {'Yes (Persistent Cloud/GDrive)' if res.get('is_mounted') else 'Local Volume (/data) with GDrive Auto-Sync'}")
        disk = res.get("disk", {})
        print(f"   Storage   : {disk.get('used_gb', 0)} GB used / {disk.get('free_gb', 0)} GB free (Total: {disk.get('total_gb', 0)} GB)")
    else:
        print(f"❌ Could not connect or space is sleeping: {res.get('error', res)}")

def cmd_exec(command: str, cwd: str = None, timeout: int = 600, json_output: bool = False):
    payload = {"cmd": command, "timeout": timeout}
    if cwd:
        payload["cwd"] = cwd
    
    res = make_request("exec", payload)
    if json_output:
        print(json.dumps(res, indent=2))
        return
    
    if res.get("ok"):
        if res.get("stdout"):
            sys.stdout.write(res["stdout"])
        if res.get("stderr"):
            sys.stderr.write(res["stderr"])
        sys.exit(res.get("exit_code", 0))
    else:
        if res.get("stderr"):
            sys.stderr.write(res["stderr"])
        else:
            print(f"Cloud execution error: {res.get('error')}", file=sys.stderr)
        sys.exit(res.get("exit_code", 1))

def cmd_ls(path: str = ""):
    res = make_request(f"files/list?path={path}")
    if res.get("ok"):
        print(f"Contents of {path or '/data/antigravity'} (Google Drive):")
        for item in res.get("items", []):
            kind = "[DIR] " if item["is_dir"] else "[FILE]"
            size = f"({item['size']} B)" if not item["is_dir"] else ""
            print(f"  {kind} {item['name']} {size}")
    else:
        print(f"Error listing files: {res.get('error')}")

def cmd_push(local_path: str, remote_path: str = None):
    if not os.path.isfile(local_path):
        print(f"Local file not found: {local_path}", file=sys.stderr)
        sys.exit(1)
    
    if not remote_path:
        remote_path = os.path.basename(local_path)
    
    with open(local_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    
    res = make_request("files/write", {"path": remote_path, "content": content})
    if res.get("ok"):
        print(f"✅ Uploaded {local_path} ➔ cloud:/data/antigravity/{remote_path} ({res.get('bytes_written')} bytes)")
    else:
        print(f"❌ Upload failed: {res.get('error')}", file=sys.stderr)
        sys.exit(1)

def cmd_pull(remote_path: str, local_path: str = None):
    if not local_path:
        local_path = os.path.basename(remote_path)
    
    res = make_request("files/read", {"path": remote_path})
    if res.get("ok"):
        content = res.get("content", "")
        os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Downloaded cloud:/data/antigravity/{remote_path} ➔ {local_path} ({len(content.encode('utf-8'))} bytes)")
    else:
        print(f"❌ Download failed: {res.get('error')}", file=sys.stderr)
        sys.exit(1)

def cmd_clone(repo_url: str, folder_name: str = ""):
    print(f"Cloning {repo_url} directly into cloud Google Drive...")
    cmd = f"git clone {repo_url} {folder_name}".strip()
    cmd_exec(f"{cmd} && rclone copy /data/antigravity gdrive:Antigravity --transfers 4 --fast-list")

def cmd_sync():
    print("Triggering immediate Google Drive sync in cloud...")
    cmd_exec("rclone sync /data/antigravity gdrive:Antigravity --transfers 4 --fast-list && echo 'Sync complete!'")

def main():
    parser = argparse.ArgumentParser(description="Antigravity Cloud Bridge (16 vCPU & Google Drive)")
    sub = parser.add_subparsers(dest="subcommand")

    sub.add_parser("status", help="Check cloud status and Google Drive health")
    
    exec_p = sub.add_parser("exec", help="Run command on 16 vCPU cloud")
    exec_p.add_argument("command", help="Command to execute")
    exec_p.add_argument("--cwd", help="Remote working directory", default=None)
    exec_p.add_argument("--timeout", type=int, default=600, help="Timeout in seconds")
    exec_p.add_argument("--json", action="store_true", help="Output JSON response")

    ls_p = sub.add_parser("ls", help="List cloud workspace / Google Drive files")
    ls_p.add_argument("path", nargs="?", default="", help="Subdirectory path")

    push_p = sub.add_parser("push", help="Push local file to cloud workspace")
    push_p.add_argument("local_file", help="Local file path")
    push_p.add_argument("remote_path", nargs="?", default=None, help="Remote path in workspace")

    pull_p = sub.add_parser("pull", help="Pull cloud file to local device")
    pull_p.add_argument("remote_path", help="Remote path in workspace")
    pull_p.add_argument("local_file", nargs="?", default=None, help="Local file destination")

    clone_p = sub.add_parser("clone", help="Clone git repo directly into cloud Google Drive")
    clone_p.add_argument("repo_url", help="Git repository URL")
    clone_p.add_argument("folder_name", nargs="?", default="", help="Optional destination folder")

    sub.add_parser("sync", help="Force immediate bidirectional Google Drive sync")

    args = parser.parse_args()

    if args.subcommand == "status":
        cmd_status()
    elif args.subcommand == "exec":
        cmd_exec(args.command, args.cwd, args.timeout, args.json)
    elif args.subcommand == "ls":
        cmd_ls(args.path)
    elif args.subcommand == "push":
        cmd_push(args.local_file, args.remote_path)
    elif args.subcommand == "pull":
        cmd_pull(args.remote_path, args.local_file)
    elif args.subcommand == "clone":
        cmd_clone(args.repo_url, args.folder_name)
    elif args.subcommand == "sync":
        cmd_sync()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
