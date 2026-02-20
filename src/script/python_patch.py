#!/usr/bin/env python3
"""
Ceph Manager Live-Patcher
=========================

A lightweight, Git-aware tool to inject local Ceph Manager Python changes 
directly into a pre-existing container image, bypassing the need for long 
C++ compile times or full container rebuilds.

Why use this?
-------------
When working on `ceph-mgr` Python modules, building a new Ceph image from 
scratch can take a very long time. This script allows you to surgically copy 
your modified Python files into a base image, validate them, and save the 
result as a new image in seconds.

Core Features:
--------------
* Git Integration: Automatically detects modified/added/deleted files using 
  `git status` (for uncommitted changes) or `git diff` (when comparing against a branch).
* Path Mapping: Automatically maps local `src/pybind/mgr/` paths to remote 
  `/usr/share/ceph/mgr/` paths inside the container.
* Syntax Validation: Runs `python3 -m py_compile` on modified Python files 
  *inside* the container. If a syntax error is found, the build aborts immediately.
* Permission Handling: Ensures all injected files have `root:root` ownership 
  and `644` permissions.
* Architecture Safe: Forces `--platform linux/amd64` to prevent manifest 
  errors when running Docker via Colima or Docker Desktop on ARM Macs.

Usage Examples:
---------------
1. Patch using only uncommitted local changes:
   $ python3 python_patch.py --base quay.ceph.io/base:tag --out quay.ceph.io/my_user/ceph:test

2. Patch using commits from a specific branch (and push the result):
   $ python3 python_patch.py --base <base> --out <out> --branch origin/my-feature --push

3. See the exact code diffs before patching:
   $ python3 python_patch.py --base <base> --out <out> --branch <branch> --show-diffs

Notes:
------
- By default, local uncommitted changes will OVERRIDE changes from the target 
  branch if there is a conflict. 
- The script restricts patching exclusively to the `src/pybind/mgr/` directory 
  to prevent accidentally copying C++ source files or compiled binaries.
"""

import argparse
import subprocess
import sys
import os
import shutil
import logging

# --- Configuration ---
LOCAL_PREFIX = "src/pybind/mgr/"
REMOTE_PREFIX = "/usr/share/ceph/mgr/"
ALLOWED_DIR = "src/pybind/mgr/"

log = logging.getLogger("patcher")

def setup_logging(level):
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

def get_engine(use_sudo, override_engine=None):
    engine = None
    if override_engine:
        if not shutil.which(override_engine):
            log.error(f"❌ Requested engine '{override_engine}' not found on PATH.")
            sys.exit(1)
        engine = override_engine
    else:
        engine = shutil.which("docker") or shutil.which("podman")
        if not engine:
            log.error("❌ Neither Docker nor Podman found on this system!")
            sys.exit(1)
    
    cmd = f"sudo {engine}" if use_sudo else engine
    
    try:
        log.debug(f"🩺 Checking if {cmd} daemon is running...")
        subprocess.check_output(f"{cmd} info", shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        log.error(f"❌ {cmd} is installed, but the daemon is not running or unreachable.")
        sys.exit(1)

    log.debug(f"⚙️  Using container engine: {cmd}")
    return cmd

def run_cmd(cmd, check=True):
    log.debug(f"Running: {cmd}")
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode().strip()
    except subprocess.CalledProcessError as e:
        if check:
            log.error(f"❌ Error executing: {cmd}\n{e.output.decode().strip()}")
            sys.exit(1)
        return ""

def get_git_root():
    """Finds the absolute path to the root of the Git repository."""
    return run_cmd("git rev-parse --show-toplevel")

def display_changes_summary(target_branch, include_untracked):
    """Prints a clean, human-readable summary of commits and local changes."""
    if target_branch:
        log.info(f"\n📋 Commits to apply (HEAD vs {target_branch}):")
        log.info("-" * 60)
        
        log_cmd = f"git log --name-status --no-renames --pretty=format:\"%h %s\" {target_branch}..HEAD"
        log_output = run_cmd(log_cmd, check=False)
        
        if not log_output:
            log.info("   (No new commits found)")
        else:
            for line in log_output.split('\n'):
                if not line.strip():
                    log.info("") 
                elif '\t' in line and line[0] in ['M', 'A', 'D']:
                    parts = line.split('\t', 1)
                    if len(parts) == 2:
                        log.info(f"    {parts[0]:<2} {parts[1]}")
                else:
                    log.info(f"📦 {line}")
        log.info("-" * 60)

    log.info("\n📂 Uncommitted Local Changes:")
    log.info("-" * 60)
    status_output = run_cmd("git status --porcelain")
    has_local = False
    
    for line in status_output.split('\n'):
        if not line: continue
        status = line[:2]
        path = line[3:]
        if status.strip() == '??' and not include_untracked:
            continue
        log.info(f"    {status.strip():<2} {path.strip()}")
        has_local = True
    
    if not has_local:
        log.info("    (No local changes)")
    log.info("-" * 60 + "\n")

def display_diffs(target_branch, git_root):
    """Prints the actual line-by-line code diffs filtered to the allowed directory."""
    log.info("🔍 DETAILED CODE DIFFS:")
    log.info("=" * 60)
    
    abs_allowed_dir = os.path.join(git_root, ALLOWED_DIR)
    
    # 1. Diff for commits
    if target_branch:
        log.info(f"\n--- Committed Changes ({target_branch}..HEAD) ---")
        diff_cmd = f"git diff {target_branch}..HEAD -- {abs_allowed_dir}"
        output = run_cmd(diff_cmd, check=False)
        if output:
            log.info(output)
        else:
            log.info("  (No content changes in allowed directory)")
            
    # 2. Diff for uncommitted local changes
    log.info("\n--- Uncommitted Local Changes ---")
    local_diff_cmd = f"git diff HEAD -- {abs_allowed_dir}"
    local_output = run_cmd(local_diff_cmd, check=False)
    if local_output:
        log.info(local_output)
    else:
        log.info("  (No uncommitted content changes in allowed directory)")
    log.info("=" * 60 + "\n")

def get_changed_files(target_branch, include_untracked):
    changes = {}

    if target_branch:
        diff_output = run_cmd(f"git diff --name-status --no-renames {target_branch}")
        for line in diff_output.split('\n'):
            if not line.strip(): continue
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                changes[parts[1].strip()] = parts[0].strip()

    status_output = run_cmd("git status --porcelain")
    for line in status_output.split('\n'):
        if not line: continue
        status = line[:2].strip()
        path = line[3:].strip()
        
        if status == '??' and not include_untracked:
            continue
        changes[path] = status

    return changes

def patch_image(args):
    git_root = get_git_root()

    # Print the UI summary
    display_changes_summary(args.branch, args.include_untracked)
    
    # Show actual code diffs if requested
    if args.show_diffs:
        display_diffs(args.branch, git_root)
        
    engine = get_engine(args.sudo, args.engine)
    files_to_patch = get_changed_files(args.branch, args.include_untracked)
    
    if not files_to_patch:
        log.info("✅ No changes detected. Exiting.")
        return

    log.info(f"🏗️  Starting base image '{args.base}' in the background...")
    container_id = run_cmd(f"{engine} run -d --platform linux/amd64 --entrypoint /bin/sh {args.base} -c 'sleep 300'")

    try:
        made_changes = False

        for local_path, status in files_to_patch.items():
            
            if not local_path.startswith(ALLOWED_DIR):
                log.warning(f"⚠️  Skipping: '{local_path}' (Outside of {ALLOWED_DIR})")
                continue

            is_python = local_path.endswith('.py')
            if not is_python:
                log.warning(f"⚠️  Warning: '{local_path}' is not a Python file. Proceeding anyway.")

            relative_part = local_path.replace(LOCAL_PREFIX, "", 1)
            remote_path = os.path.join(REMOTE_PREFIX, relative_part)
            abs_local_path = os.path.join(git_root, local_path)

            if status.startswith('D'):
                log.info(f"🗑️  Deleting: {remote_path}")
                run_cmd(f"{engine} exec {container_id} rm -f {remote_path}", check=False)
                made_changes = True
            
            else:
                log.info(f"🚀 Patching: {remote_path}")
                remote_dir = os.path.dirname(remote_path)
                run_cmd(f"{engine} exec {container_id} mkdir -p {remote_dir}")
                
                subprocess.run(f"{engine} cp {abs_local_path} {container_id}:{remote_path}", shell=True, check=True)
                run_cmd(f"{engine} exec {container_id} chown root:root {remote_path}")
                run_cmd(f"{engine} exec {container_id} chmod 644 {remote_path}")
                made_changes = True

                if is_python:
                    log.debug(f"   🔍 Validating syntax for {local_path}...")
                    compile_check = subprocess.run(
                        f"{engine} exec {container_id} python3 -m py_compile {remote_path}",
                        shell=True, capture_output=True, text=True
                    )
                    
                    if compile_check.returncode != 0:
                        log.error(f"\n❌ SYNTAX ERROR IN: {local_path}")
                        log.error(compile_check.stderr.strip() or compile_check.stdout.strip())
                        log.error("🛑 Aborting build to prevent broken image. Cleaning up...")
                        sys.exit(1)

        if made_changes:
            log.info(f"\n💾 Saving new image as: {args.out}...")
            run_cmd(f"{engine} commit {container_id} {args.out}")
            log.info("✨ Image committed successfully!")

            if args.push:
                log.info(f"☁️  Pushing {args.out} to remote registry...")
                run_cmd(f"{engine} push {args.out}")
                log.info("✅ Push complete!")
        else:
            log.info("✅ No valid files to patch inside the allowed directory.")

    finally:
        log.debug(f"🧹 Cleaning up container {container_id[:12]}...")
        run_cmd(f"{engine} rm -f {container_id}", check=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live-patch a Docker/Podman image with Git changes.")
    parser.add_argument("--base", required=True, help="Base container image to pull and modify")
    parser.add_argument("--out", required=True, help="Name of the output container image")
    parser.add_argument("--branch", "-b", help="Target branch to compare against (e.g., origin/main)")
    parser.add_argument("--include-untracked", action="store_true", help="Include untracked local files")
    parser.add_argument("--push", action="store_true", help="Push the resulting image to the registry")
    parser.add_argument("--sudo", action="store_true", help="Run container commands with sudo")
    parser.add_argument("--engine", help="Force a specific container engine (e.g., docker or podman)")
    parser.add_argument("--show-diffs", action="store_true", help="Show the actual content diffs of the patched files")
    
    parser.add_argument("--debug", action="store_const", dest="log_level", const=logging.DEBUG, default=logging.INFO, help="Enable verbose debug logging")
    parser.add_argument("--quiet", "-q", action="store_const", dest="log_level", const=logging.WARNING, help="Only print errors and warnings")

    args = parser.parse_args()
    setup_logging(args.log_level)
    
    patch_image(args)