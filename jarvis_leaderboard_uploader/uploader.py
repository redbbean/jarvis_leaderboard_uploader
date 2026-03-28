"""
uploader.py
===========
The high-level JarvisUploader class — orchestrates the entire workflow.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Union

from jarvis_leaderboard_uploader.git_helper import GitHelper
from jarvis_leaderboard_uploader.logger import JarvisLogger
from jarvis_leaderboard_uploader.packager import Packager
from jarvis_leaderboard_uploader.runner import ScriptRunner
from jarvis_leaderboard_uploader.validator import Validator


class JarvisUploader:
    """
    One-stop orchestrator for submitting results to the JARVIS Leaderboard.

    Parameters
    ----------
    repo_path : Path to your cloned fork of jarvis_leaderboard.
    verbose   : Whether to print step-by-step progress (default: True).
    """

    def __init__(self, repo_path: Union[str, Path], *, verbose: bool = True):
        self.repo_path = Path(repo_path)
        self.logger = JarvisLogger(verbose=verbose)
        self._validator = Validator(logger=self.logger)
        self._packager = Packager(repo_path=self.repo_path, logger=self.logger)
        self._git = GitHelper(repo_path=self.repo_path, logger=self.logger)
        self._runner = ScriptRunner(logger=self.logger)

    def submit(
        self,
        *,
        benchmark: str,
        contribution_name: str,
        metadata: Union[Dict, str, Path],
        results_file: Optional[Union[str, Path]] = None,
        eval_script: Optional[str] = None,
        script_output_csv: Optional[Union[str, Path]] = None,
        script_capture_stdout: bool = False,
        script_timeout: Optional[int] = None,
        script_cwd: Optional[Union[str, Path]] = None,
        script_env: Optional[Dict] = None,
        run_script: Optional[Union[str, Path]] = None,
        run_py: Optional[Union[str, Path]] = None,
        dockerfile: Optional[Union[str, Path]] = None,
        overwrite: bool = False,
        run_rebuild: bool = True,
        auto_git: bool = True,
        push: bool = True,
        commit_message: Optional[str] = None,
        github_username: Optional[str] = None,
    ) -> Path:
        self.logger.section(f"JARVIS Leaderboard Uploader — '{contribution_name}'")
        self.logger.reset_steps()

        if results_file is None and eval_script is None:
            raise ValueError(
                "You must provide either 'results_file' or 'eval_script'."
            )
        if results_file is not None and eval_script is not None:
            raise ValueError("Provide either 'results_file' or 'eval_script', not both.")

        # Step 1: Parse benchmark name
        self.logger.step(f"Parsing benchmark name: {benchmark}")
        try:
            bench = self._validator.parse_benchmark_name(benchmark)
        except ValueError as exc:
            self.logger.error(str(exc), hint="Check the JARVIS guide for valid names.")
            raise

        self.logger.success(
            f"Benchmark parsed:\n"
            f"    Method      : {bench.method}\n"
            f"    Subcategory : {bench.subcategory}\n"
            f"    Property    : {bench.property_name}\n"
            f"    Dataset     : {bench.dataset}\n"
            f"    Split       : {bench.split}\n"
            f"    Metric      : {bench.metric}"
        )

        # Step 2: Obtain the CSV
        if results_file:
            csv_path = Path(results_file)
            self.logger.step(f"Using provided results file: {csv_path}")
        else:
            self.logger.step("Running evaluation script to produce predictions")
            try:
                csv_path = self._runner.run(
                    eval_script,
                    output_csv=script_output_csv,
                    capture_stdout_as_csv=script_capture_stdout,
                    timeout=script_timeout,
                    env=script_env,
                    cwd=script_cwd,
                )
            except RuntimeError as exc:
                self.logger.error(
                    str(exc),
                    hint="Make sure your script exits with code 0 and writes a CSV.",
                )
                raise

        # Step 3: Validate CSV
        self.logger.step(f"Validating CSV: {csv_path}")
        try:
            ids, predictions = self._validator.validate_csv(csv_path)
        except (ValueError, FileNotFoundError) as exc:
            self.logger.error(
                str(exc),
                filepath=str(csv_path),
                hint=(
                    "The CSV must have exactly two columns: 'id' and 'prediction'.\n"
                    "    'id' must match the benchmark test-set IDs.\n"
                    "    'prediction' must be a numeric value."
                ),
            )
            raise
        self.logger.success(f"CSV valid — {len(ids)} predictions found.")

        # Step 4: Validate metadata
        self.logger.step("Validating metadata")
        try:
            if isinstance(metadata, (str, Path)):
                meta_dict = self._validator.load_and_validate_metadata(metadata)
            else:
                meta_dict = self._validator.validate_metadata(dict(metadata))
        except (ValueError, FileNotFoundError) as exc:
            self.logger.error(
                str(exc),
                hint="Required keys: model_name, project_url.",
            )
            raise
        self.logger.success("Metadata valid.")

        # Step 5: Check git fork
        if auto_git or push:
            self._git.check_fork()

        # Step 6: Build contribution folder
        try:
            contribution_path = self._packager.create_contribution(
                contribution_name=contribution_name,
                benchmark=bench,
                csv_path=csv_path,
                metadata=meta_dict,
                run_script=run_script,
                run_py=run_py,
                dockerfile=dockerfile,
                overwrite=overwrite,
            )
        except (FileExistsError, FileNotFoundError, ValueError) as exc:
            self.logger.error(str(exc))
            raise

        # Step 7: Run rebuild.py
        if run_rebuild:
            try:
                self._git.run_rebuild()
            except RuntimeError as exc:
                self.logger.error(
                    str(exc),
                    hint="Fix the errors above before pushing.",
                )
                raise

        # Step 8: Git add + commit + push
        if auto_git:
            try:
                self._git.add_and_commit(
                    contribution_path,
                    commit_message=commit_message,
                    contribution_name=contribution_name,
                )
                if push:
                    self._git.push()
            except RuntimeError as exc:
                self.logger.error(
                    str(exc),
                    hint=(
                        "Check that your git credentials are set up correctly.\n"
                        "For HTTPS: git config --global credential.helper store\n"
                        "For SSH  : make sure your SSH key is added to GitHub."
                    ),
                )
                raise

        # Step 9: PR instructions
        self._git.pr_instructions(
            contribution_name=contribution_name,
            github_username=github_username,
        )

        return contribution_path

    def validate_only(
        self,
        *,
        benchmark: str,
        results_file: Union[str, Path],
        metadata: Optional[Union[Dict, str, Path]] = None,
    ) -> None:
        self.logger.section("Dry-run validation (no files will be written)")
        self.logger.reset_steps()

        self.logger.step("Parsing benchmark name")
        bench = self._validator.parse_benchmark_name(benchmark)
        self.logger.success(f"Benchmark '{bench.raw}' parsed successfully.")

        self.logger.step("Validating CSV")
        ids, preds = self._validator.validate_csv(results_file)
        self.logger.success(f"CSV valid — {len(ids)} rows found.")

        if metadata is not None:
            self.logger.step("Validating metadata")
            if isinstance(metadata, (str, Path)):
                self._validator.load_and_validate_metadata(metadata)
            else:
                self._validator.validate_metadata(dict(metadata))
            self.logger.success("Metadata valid.")

        self.logger.section("All checks passed ✓")

    def list_contributions(self) -> list:
        return self._packager.list_existing_contributions()

    def benchmark_help(self) -> None:
        print(
            "\nBenchmark name format:\n"
            "  METHOD-SUBCATEGORY-property-dataset-split-metric\n"
            "\nExamples:\n"
            "  AI-SinglePropertyPrediction-formation_energy_peratom-dft_3d-test-mae\n"
            "  ES-SinglePropertyPrediction-bandgap_JVASP_1002_Si-dft_3d-test-mae\n"
            "  FF-SinglePropertyPrediction-bulk_modulus_JVASP_1002_Si-dft_3d-test-mae\n"
            "\nValid methods  : AI, ES, FF, QC, EXP\n"
            "Valid splits    : train, val, test\n"
            "Common metrics  : mae, acc, multimae\n"
            "Full list       : https://pages.nist.gov/jarvis_leaderboard/\n"
        )