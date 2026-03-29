# JARVIS Leaderboard Uploader

`jarvis-leaderboard-uploader` is a Python package and CLI for preparing JARVIS Leaderboard submissions from either an existing results CSV or an evaluation script.

## Install

```bash
pip install jarvis_leaderboard_uploader
```

## What it does

The package helps you:

- validate benchmark names
- check that your results CSV has the required `id` and `prediction` columns
- validate metadata
- package your submission into the expected contribution folder
- optionally run an evaluation script before packaging
- print the next pull request step after the contribution is created

## Quick start

Show benchmark name examples:

```bash
jarvis-upload help-benchmark
```

Validate a CSV before submitting:

```bash
jarvis-upload validate   --benchmark "AI-SinglePropertyPrediction-formation_energy_peratom-dft_3d-test-mae"   --results_file predictions.csv
```

Submit from a CSV:

```bash
jarvis-upload submit   --repo_path ./jarvis_leaderboard   --benchmark "AI-SinglePropertyPrediction-formation_energy_peratom-dft_3d-test-mae"   --contribution_name my_model_v1   --results_file predictions.csv   --model_name "MyModel"   --project_url "https://github.com/you/your-project"
```

Submit by running a script:

```bash
jarvis-upload submit   --repo_path ./jarvis_leaderboard   --benchmark "AI-SinglePropertyPrediction-formation_energy_peratom-dft_3d-test-mae"   --contribution_name my_model_v1   --eval_script "python run_eval.py"   --script_output_csv predictions.csv   --model_name "MyModel"   --project_url "https://github.com/you/your-project"
```

## Required inputs

You need:

- a cloned fork of the `jarvis_leaderboard` repository
- a benchmark name in the expected format
- a results CSV with `id` and `prediction`
- metadata supplied by either `--metadata_file` or `--model_name` plus `--project_url`

## CLI commands

- `submit` — validate, package, commit, and push the contribution
- `validate` — check a CSV and benchmark without writing files
- `list` — list existing contribution folders in a local repo
- `help-benchmark` — print benchmark format examples

## Example workflow

1. Run your evaluation or prepare your CSV.
2. Validate the file.
3. Submit the contribution.
4. Open the pull request that the CLI prints at the end.

## Project homepage

For source code, development notes, and issue tracking, see the GitHub repository.

## License

MIT
