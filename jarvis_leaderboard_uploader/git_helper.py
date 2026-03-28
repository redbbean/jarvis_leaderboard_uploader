"""
git_helper.py
=============
Automates git add/commit/push + fork safety check + PR instructions.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

from jarvis_leaderboard_uploader.logger import JarvisLogger

UPSTREAM_ORG = "atomgptlab"
TARGET_BRANCH = "main"
LEADERBOARD_REPO = "jarvis_leaderboard"


class GitHelper:
    def __init__(self, repo_path: str | Path, logger: Optional[JarvisLogger] = None):
        self.repo_path = Path(repo_path)
        self.logger = logger or JarvisLogger()
        self._ensure_git_available()

    def add_and_commit(
        self,
        contribution_path: str | Path,
        *,
        commit_message: Optional[str] = None,
        contribution_name: Optional[str] = None,
    ) -> None:
        self.logger.step("Staging and committing the contribution")
        rel_path = self._relative_path(contribution_path)
        self._run_git(["add", str(rel_path)], step="git add")
        msg = commit_message or f"Add contribution: {contribution_name or rel_path.name}"
        self._run_git(["commit", "-m", msg], step="git commit")
        self.logger.success(f'Committed with message: "{msg}"')

    def push(self, *, branch: Optional[str] = None) -> None:
        self.logger.step("Pushing to origin")
        current_branch = self._current_branch()
        target = branch or current_branch
        self._run_git(["push", "origin", target], step="git push")
        self.logger.success(f"Pushed branch '{target}' to origin.")

    def check_fork(self) -> bool:
        self.logger.step("Verifying that repo is a fork of the upstream")
        try:
            remotes = self._git_output(["remote", "-v"])
        except RuntimeError:
            self.logger.warning("Could not read git remotes — skipping fork check.")
            return True

        if f"{UPSTREAM_ORG}/{LEADERBOARD_REPO}" in remotes:
            origin_lines = [l for l in remotes.splitlines() if l.startswith("origin")]
            for line in origin_lines:
                if f"{UPSTREAM_ORG}/{LEADERBOARD_REPO}" in line:
                    self.logger.error(
                        f"Your 'origin' remote points directly to the upstream repo.",
                        hint=(
                            "You must work in a fork.\n"
                            "  1. Fork at https://github.com/atomgptlab/jarvis_leaderboard\n"
                            "  2. Clone YOUR fork: git clone https://github.com/YOUR_USERNAME/jarvis_leaderboard\n"
                            "  3. Re-run this command from the cloned fork."
                        ),
                    )
                    return False

        self.logger.success("Repo appears to be a personal fork — good.")
        return True

    def pr_instructions(self, *, contribution_name: str, github_username: Optional[str] = None) -> None:
        self.logger.section("Next Step: Open a Pull Request")
        username = github_username or self._infer_github_username()

        if username:
            fork_url = f"https://github.com/{username}/{LEADERBOARD_REPO}"
            pr_url = (
                f"https://github.com/{UPSTREAM_ORG}/{LEADERBOARD_REPO}/compare/"
                f"{TARGET_BRANCH}...{username}:{TARGET_BRANCH}"
            )
        else:
            fork_url = f"https://github.com/YOUR_USERNAME/{LEADERBOARD_REPO}"
            pr_url = f"https://github.com/{UPSTREAM_ORG}/{LEADERBOARD_REPO}/pulls"

        self.logger.info(
            f"\n"
            f"  Your contribution '{contribution_name}' has been committed and pushed.\n"
            f"\n"
            f"  To submit it to the official JARVIS Leaderboard:\n"
            f"\n"
            f"  1. Go to your fork:  {fork_url}\n"
            f"  2. Open a PR at:     {pr_url}\n"
            f"  3. Base branch:      {UPSTREAM_ORG}/{LEADERBOARD_REPO}  →  {TARGET_BRANCH}\n"
            f"\n"
            f"  ⚠ Pull requests to 'main' are for admins only — always target '{TARGET_BRANCH}'.\n"
        )

    def run_rebuild(self) -> None:
        self.logger.step("Running rebuild.py to validate the leaderboard")
        rebuild_script = self.repo_path / "jarvis_leaderboard" / "rebuild.py"
        if not rebuild_script.exists():
            self.logger.warning(f"rebuild.py not found at {rebuild_script} — skipping.")
            return
        result = subprocess.run(
            [sys.executable, str(rebuild_script)],
            cwd=str(self.repo_path),
            capture_output=True,
            text=True,
        )
        if result.stdout:
            for line in result.stdout.strip().splitlines()[-20:]:
                self.logger.info(f"  [rebuild] {line}")
        if result.returncode != 0:
            self.logger.error(
                "rebuild.py exited with errors.",
                hint=(
                    "Common causes:\n"
                    "  • CSV columns don't match expected benchmark IDs\n"
                    "  • Benchmark filename doesn't match an existing benchmark\n"
                    "  • metadata.json is malformed"
                ),
            )
            if result.stderr:
                for line in result.stderr.strip().splitlines():
                    self.logger.info(f"  [rebuild stderr] {line}")
            raise RuntimeError("rebuild.py failed — see errors above.")
        self.logger.success("rebuild.py completed without errors.")

    def _run_git(self, args: list, *, step: str = "git") -> str:
        cmd = ["git"] + args
        result = subprocess.run(cmd, cwd=str(self.repo_path), capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"'{step}' failed (exit code {result.returncode}).\n"
                f"  Command : {' '.join(cmd)}\n"
                f"  stdout  : {result.stdout.strip()}\n"
                f"  stderr  : {result.stderr.strip()}\n"
                f"  Repo    : {self.repo_path}\n\n"
                "Common causes:\n"
                "  • Nothing to commit\n"
                "  • Not in a git repository\n"
                "  • SSH key / HTTPS credentials not configured\n"
                "  • Remote branch doesn't exist yet (try: git push -u origin HEAD)"
            )
        return result.stdout

    def _git_output(self, args: list) -> str:
        result = subprocess.run(
            ["git"] + args, cwd=str(self.repo_path), capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())
        return result.stdout.strip()

    def _current_branch(self) -> str:
        try:
            return self._git_output(["rev-parse", "--abbrev-ref", "HEAD"])
        except RuntimeError:
            return "main"

    def _infer_github_username(self) -> Optional[str]:
        try:
            remotes = self._git_output(["remote", "-v"])
        except RuntimeError:
            return None
        for line in remotes.splitlines():
            if "origin" in line and "github.com" in line:
                parts = line.split()
                url = parts[1] if len(parts) > 1 else ""
                for sep in ("github.com/", "github.com:"):
                    if sep in url:
                        after = url.split(sep)[-1].split("/")[0]
                        if after and after != UPSTREAM_ORG:
                            return after
        return None

    def _relative_path(self, path: str | Path) -> Path:
        p = Path(path)
        try:
            return p.relative_to(self.repo_path)
        except ValueError:
            return p

    def _ensure_git_available(self) -> None:
        result = subprocess.run(["git", "--version"], capture_output=True)
        if result.returncode != 0:
            raise EnvironmentError(
                "git is not available on your PATH.\n"
                "Install git from https://git-scm.com/downloads and try again."
            )