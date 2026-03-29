# JARVIS Leaderboard Uploader

A Python package and CLI for validating, packaging, and submitting JARVIS Leaderboard contributions from a local results CSV or an evaluation script. It helps automate the workflow from predictions to a contribution folder in a fork of the leaderboard repository.

## What this project does

`jarvis-upload` helps you:

- validate a benchmark name, results CSV, and metadata
- optionally run an evaluation script to generate predictions
- package the required contribution files
- commit and push the contribution to your fork
- print pull request instructions for the final submission step

## Why this exists

The JARVIS submission process involves several moving parts: benchmark naming, CSV formatting, metadata, repo structure, and git workflow. This tool brings those steps together so the process is easier to repeat and harder to get wrong.

## Installation

```bash
pip install jarvis_leaderboard_uploader
```

For local development:

```bash
pip install -e .
```

## Requirements

- Python 3.8+
- git
- a cloned fork of the `jarvis_leaderboard` repository

## Command-line usage

Check the benchmark format:

```bash
jarvis-upload help-benchmark
```

List existing contributions in a repo:

```bash
jarvis-upload list --repo_path ./jarvis_leaderboard
```

Validate a results file without writing anything:

```bash
jarvis-upload validate   --benchmark "AI-SinglePropertyPrediction-formation_energy_peratom-dft_3d-test-mae"   --results_file predictions.csv
```

Submit a contribution from an existing CSV:

```bash
jarvis-upload submit   --repo_path ./jarvis_leaderboard   --benchmark "AI-SinglePropertyPrediction-formation_energy_peratom-dft_3d-test-mae"   --contribution_name my_model_v1   --results_file predictions.csv   --model_name "MyModel"   --project_url "https://github.com/you/your-project"
```

Submit by running an evaluation script:

```bash
jarvis-upload submit   --repo_path ./jarvis_leaderboard   --benchmark "AI-SinglePropertyPrediction-formation_energy_peratom-dft_3d-test-mae"   --contribution_name my_model_v1   --eval_script "python run_eval.py"   --script_output_csv predictions.csv   --model_name "MyModel"   --project_url "https://github.com/you/your-project"
```

## Expected inputs

The uploader expects a CSV with two columns:

- `id`
- `prediction`

It also expects either:

- `--metadata_file path/to/metadata.json`, or
- `--model_name` and `--project_url`

Optional metadata fields include `team_name` and `date_submitted`.

## Project structure

The package is organized into small modules so the workflow is easier to understand and maintain:

- `validator.py` checks benchmark names, CSV files, and metadata
- `runner.py` handles evaluation scripts
- `packager.py` creates the contribution folder and archive
- `git_helper.py` manages git add / commit / push and PR guidance
- `uploader.py` coordinates the full workflow
- `cli.py` exposes the command-line interface

## Notes from the project

A few details in the upload guide and the repository did not line up exactly, so part of the work here was reconciling those differences and making the workflow more consistent.

This project also taught me a lot about Python packaging. Building something for PyPI turned out to involve more moving pieces than I expected, including `pyproject.toml`, `MANIFEST.in`, package layout, and making sure the right files are included in the distribution.

Other big takeaways were:

- splitting the workflow across separate files makes the code easier to reason about
- CLI design takes more thought than it first appears
- working with CSV files cleanly matters a lot for validation and reproducibility
- staying on top of version control is essential, especially on a project that evolves over time

## Running tests

```bash
pytest tests/ -v
```

## Building the package

```bash
python -m build
twine check dist/*
```

## Contributing

Issues and pull requests are welcome. If you are working on the leaderboard repo itself, keep the contribution folder structure and benchmark naming rules consistent with the upstream guide.

## License

MIT
