# jarvis-leaderboard-uploader

Automate submitting results to the JARVIS Leaderboard — from CSV validation to pull request.

---

## Resources

- JARVIS Leaderboard Guide: https://pages.nist.gov/jarvis_leaderboard/
- JARVIS Repository: https://github.com/atomgptlab/jarvis_leaderboard
- Uploader GitHub Repository: https://github.com/redbbean/jarvis_leaderboard_uploader

---

## What This Does

Submitting to JARVIS manually requires:

- Formatting CSVs exactly
- Naming benchmarks correctly
- Creating the right folder structure
- Zipping files properly
- Running validation scripts
- Using git correctly

This package automates all of that.

---

## Installation

```bash
pip install jarvis_leaderboard_uploader
```

---

## Quick Start

### Colab Notebook with more in detail examples coming soon!

### 1. Clone your fork of the JARVIS repo

```bash
git clone https://github.com/YOUR_USERNAME/jarvis_leaderboard
cd jarvis_leaderboard
```

---

### 2. Prepare your predictions CSV

Must look like:

```text
id,prediction
sample1,0.5
sample2,1.2
```

---

### 3. Submit

```bash
jarvis-upload submit   --repo_path ./jarvis_leaderboard   --benchmark "AI-TextClass-mmlu_test_quiz-mmlu-test-acc"   --results_file predictions.csv   --contribution_name "my_model_v1"   --model_name "My Model"   --project_url "https://github.com/me/model"
```

---

## What Happens Automatically

- Validates benchmark format
- Validates CSV structure
- Validates metadata
- Packages files into `.csv.zip`
- Creates contribution folder
- Runs `rebuild.py`
- Commits and pushes to your fork
- Prints PR link

---

## Validate Without Submitting

```bash
jarvis-upload validate   --benchmark "AI-TextClass-mmlu_test_quiz-mmlu-test-acc"   --results_file predictions.csv
```

---

## Using an Evaluation Script

Instead of passing a CSV, you can run a script:

```bash
jarvis-upload submit   --repo_path ./jarvis_leaderboard   --benchmark "..."   --eval_script "python eval.py"   --script_output_csv results.csv   --contribution_name "my_model"   --model_name "My Model"   --project_url "https://github.com/me/model"
```

---

## CLI Commands

| Command | Description |
|--------|-------------|
| `submit` | Full pipeline |
| `validate` | Check inputs only |
| `list` | Show existing contributions |
| `help-benchmark` | Show naming format |

---

## Requirements

- Python 3.8+
- Git installed and configured
- Fork of the JARVIS repository (main branch)

---

## Common Errors

- Wrong benchmark format
- Missing `id` / `prediction` columns
- Non-numeric predictions
- Not working inside a forked repo

The CLI will explain what went wrong and in which file. 

### Feel free to checkout the [GitHub repo]()

---

## Goal

Make JARVIS submissions:

- Faster
- Less error-prone
- Easier to reproduce

---

## License

MIT License
