"""
cli.py
======
`jarvis-upload` CLI — submit / validate / list / help-benchmark
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from jarvis_leaderboard_uploader.uploader import JarvisUploader
from jarvis_leaderboard_uploader.logger import JarvisLogger, Colour


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jarvis-upload",
        description="Automate submitting results to the JARVIS Leaderboard.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # submit
    submit = sub.add_parser("submit", help="Full workflow: validate → package → commit → push")
    _add_common_args(submit)
    _add_submission_args(submit)

    # validate
    validate = sub.add_parser("validate", help="Dry-run validation only — no files written")
    validate.add_argument("--benchmark", required=True)
    validate.add_argument("--results_file", required=True)
    validate.add_argument("--metadata_file")
    validate.add_argument("--verbose", action="store_true", default=True)

    # list
    ls = sub.add_parser("list", help="List all existing contribution folders in the repo")
    ls.add_argument("--repo_path", required=True)

    # help-benchmark
    sub.add_parser("help-benchmark", help="Print benchmark name format + examples")

    return parser


def _add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--repo_path", required=True)
    p.add_argument("--benchmark", required=True)
    p.add_argument("--contribution_name", required=True)
    meta = p.add_mutually_exclusive_group(required=True)
    meta.add_argument("--metadata_file")
    meta.add_argument("--model_name")
    p.add_argument("--project_url")
    p.add_argument("--verbose", action="store_true", default=True)
    p.add_argument("--team_name", help="Your team or personal name")
    p.add_argument("--date_submitted", help="Submission date in YYYY-MM-DD format")


def _add_submission_args(p: argparse.ArgumentParser) -> None:
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--results_file")
    src.add_argument("--eval_script")
    p.add_argument("--script_output_csv")
    p.add_argument("--script_capture_stdout", action="store_true")
    p.add_argument("--script_timeout", type=int, default=None)
    p.add_argument("--script_cwd")
    p.add_argument("--run_script")
    p.add_argument("--run_py")
    p.add_argument("--dockerfile")
    p.add_argument("--no_rebuild", action="store_true")
    p.add_argument("--no_git", action="store_true")
    p.add_argument("--no_push", action="store_true")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--commit_message")
    p.add_argument("--github_username")


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    logger = JarvisLogger(verbose=getattr(args, "verbose", True))

    try:
        if args.command == "help-benchmark":
            _make_dummy_uploader().benchmark_help()
            return 0

        if args.command == "list":
            uploader = JarvisUploader(repo_path=args.repo_path)
            contribs = uploader.list_contributions()
            if contribs:
                print(f"\n{len(contribs)} existing contribution(s):\n")
                for c in contribs:
                    print(f"  • {c}")
            else:
                print("No existing contributions found.")
            return 0

        if args.command == "validate":
            uploader = JarvisUploader(repo_path=".", verbose=args.verbose)
            uploader.validate_only(
                benchmark=args.benchmark,
                results_file=args.results_file,
                metadata=args.metadata_file,
            )
            return 0

        if args.command == "submit":
            if args.metadata_file:
                metadata = Path(args.metadata_file)
            else:
                if not args.project_url:
                    parser.error("--project_url is required when --model_name is used.")
                metadata = {
                    "model_name": args.model_name,
                    "project_url": args.project_url,
                }
                if args.team_name:
                    metadata["team_name"] = args.team_name
                if args.date_submitted:
                    metadata["date_submitted"] = args.date_submitted
                else:
                    # Default to today's date if not provided
                    import datetime
                    metadata["date_submitted"] = datetime.date.today().isoformat()

            uploader = JarvisUploader(repo_path=args.repo_path, verbose=args.verbose)
            uploader.submit(
                benchmark=args.benchmark,
                contribution_name=args.contribution_name,
                metadata=metadata,
                results_file=args.results_file,
                eval_script=args.eval_script,
                script_output_csv=args.script_output_csv,
                script_capture_stdout=args.script_capture_stdout,
                script_timeout=args.script_timeout,
                script_cwd=args.script_cwd,
                run_script=args.run_script,
                run_py=args.run_py,
                dockerfile=args.dockerfile,
                overwrite=args.overwrite,
                run_rebuild=not args.no_rebuild,
                auto_git=not args.no_git,
                push=not args.no_push,
                commit_message=args.commit_message,
                github_username=args.github_username,
            )
            return 0

    except (ValueError, FileNotFoundError, FileExistsError, RuntimeError) as exc:
        logger.error(
            f"Submission failed: {type(exc).__name__}",
            hint="Review the error output above and fix the reported issues.",
        )
        return 1
    except KeyboardInterrupt:
        print(f"\n{Colour.YELLOW}Interrupted.{Colour.RESET}")
        return 130
    except Exception as exc:
        logger.error(
            f"Unexpected error: {exc}",
            exc=exc,
            hint="This may be a bug. Please open an issue with the traceback above.",
        )
        return 1

    return 0


def _make_dummy_uploader() -> JarvisUploader:
    import tempfile, os
    tmp = tempfile.mkdtemp()
    os.makedirs(os.path.join(tmp, "jarvis_leaderboard", "contributions"))
    return JarvisUploader(repo_path=tmp, verbose=True)


if __name__ == "__main__":
    sys.exit(main())