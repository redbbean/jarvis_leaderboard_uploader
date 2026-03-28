"""
runner.py
=========
Run a user-supplied evaluation script and capture its output CSV.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from jarvis_leaderboard_uploader.logger import JarvisLogger


class ScriptRunner:
    def __init__(self, logger: Optional[JarvisLogger] = None):
        self.logger = logger or JarvisLogger()

    def run(
        self,
        script: str,
        *,
        output_csv: Optional[str] = None,
        capture_stdout_as_csv: bool = False,
        timeout: Optional[int] = None,
        env: Optional[dict] = None,
        cwd: Optional[str] = None,
    ) -> Path:
        self.logger.step(f"Running evaluation script: {script}")

        run_env = {**os.environ, **(env or {})}
        run_cwd = str(cwd) if cwd else os.getcwd()

        if os.path.isfile(script) and not script.startswith("python"):
            cmd = [sys.executable, script]
        else:
            cmd = shlex.split(script)

        self.logger.info(f"Command : {' '.join(cmd)}")
        self.logger.info(f"CWD     : {run_cwd}")
        if timeout:
            self.logger.info(f"Timeout : {timeout}s")

        stdout_pipe = subprocess.PIPE if capture_stdout_as_csv else None

        try:
            result = subprocess.run(
                cmd,
                cwd=run_cwd,
                env=run_env,
                stdout=stdout_pipe,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Script timed out after {timeout}s.\n"
                "Increase the timeout with --timeout <seconds> or fix the script."
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"Could not find the executable for script '{script}'.\n"
                f"  Details: {exc}\n"
                "  Make sure the script path is correct and the interpreter is in your PATH."
            ) from exc

        if result.stderr:
            stderr_text = result.stderr.decode("utf-8", errors="replace")
            lines = stderr_text.strip().splitlines()
            if len(lines) > 40:
                self.logger.info(f"(Script stderr — showing last 40 of {len(lines)} lines)")
                lines = lines[-40:]
            for line in lines:
                self.logger.info(f"  [stderr] {line}")

        if result.returncode != 0:
            raise RuntimeError(
                f"Script exited with non-zero return code: {result.returncode}\n"
                "Review the stderr output above for details.\n"
                f"Script: {script}"
            )

        self.logger.success("Script finished successfully.")

        if capture_stdout_as_csv:
            stdout_text = result.stdout.decode("utf-8", errors="replace")
            if not stdout_text.strip():
                raise RuntimeError(
                    "Script wrote nothing to stdout, but capture_stdout_as_csv=True was set."
                )
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix=".csv", delete=False, encoding="utf-8"
            )
            tmp.write(stdout_text)
            tmp.close()
            csv_path = Path(tmp.name)
            self.logger.info(f"Captured stdout → temporary CSV: {csv_path}")
            return csv_path

        if output_csv:
            csv_path = Path(output_csv)
            if not csv_path.exists():
                raise RuntimeError(
                    f"Script ran successfully, but the expected output CSV "
                    f"was not found at: {csv_path}\n"
                    "Check that your script writes to this exact path, or update --output_csv."
                )
            self.logger.success(f"Output CSV found: {csv_path}")
            return csv_path

        self.logger.warning(
            "No output_csv path was specified. Scanning the working directory for CSV files…"
        )
        candidates = sorted(
            Path(run_cwd).glob("*.csv"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            self.logger.warning(
                f"Found {len(candidates)} CSV file(s). "
                f"Using most-recently modified: {candidates[0]}"
            )
            return candidates[0]

        raise RuntimeError(
            "Could not find a CSV output file.\n"
            "Please specify --output_csv <path> so the uploader knows "
            "where your script writes its predictions."
        )