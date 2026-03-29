# jarvis_leaderboard_uploader

A Python package and CLI tool to automate submitting results to the JARVIS Leaderboard.

This tool handles the full workflow:
validate → package → commit → push → PR instructions

---

## Related Resources

- JARVIS Leaderboard Guide: https://pages.nist.gov/jarvis_leaderboard/
- JARVIS Leaderboard Repository: https://github.com/atomgptlab/jarvis_leaderboard

These are the official references this project is built around.

---

## Features

- ✅ Benchmark name validation (strict format enforcement)
- ✅ CSV validation (`id`, `prediction`)
- ✅ Metadata validation
- ✅ Script execution support (auto-generate CSVs)
- ✅ Automatic packaging into `.csv.zip`
- ✅ Git automation (add, commit, push)
- ✅ Pull request instructions
- ✅ Clean CLI (`jarvis-upload`)

---

## Installation (Development)

```bash
git clone https://github.com/YOUR_USERNAME/jarvis_leaderboard_uploader
cd jarvis_leaderboard_uploader

pip install -e .
```

With dev tools:

```bash
pip install -e ".[dev]"
```

---

## How It Works

This package mirrors the manual JARVIS submission workflow:

1. Validate benchmark name
2. Validate predictions CSV
3. Validate metadata
4. Package files into correct structure
5. Run `rebuild.py`
6. Commit + push to your fork
7. Guide you to open a PR

---

## CLI Usage

### Colab Notebook with more in detail examples coming soon!

### Submit (full pipeline)

```bash
jarvis-upload submit   --repo_path ./jarvis_leaderboard   --benchmark "AI-TextClass-mmlu_test_quiz-mmlu-test-acc"   --results_file predictions.csv   --contribution_name "my_model"   --model_name "My Model"   --project_url "https://github.com/me/model"
```

---

### Validate only

```bash
jarvis-upload validate   --benchmark "AI-TextClass-mmlu_test_quiz-mmlu-test-acc"   --results_file predictions.csv
```

---

### List contributions

```bash
jarvis-upload list --repo_path ./jarvis_leaderboard
```

---

### Benchmark help

```bash
jarvis-upload help-benchmark
```

---

## Project Structure

```text
jarvis_leaderboard_uploader/
├── cli.py
├── uploader.py
├── validator.py
├── runner.py
├── packager.py
├── git_helper.py
├── logger.py
```

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Notes on JARVIS Workflow

While building this tool, I noticed a few inconsistencies between:

- The official JARVIS guide
- The actual repository structure / expectations

This tool is designed to bridge that gap and make submissions more reliable.

---

## What I Learned

This project ended up being much more involved than expected, especially around:

- Building a proper Python package
  - `pyproject.toml`, `MANIFEST.in`, packaging structure
- Structuring a multi-file system cleanly
- Designing a CLI with `argparse`
- Working with CSVs in general

One big takeaway: Stay disciplined with version control!

---

## Contributing

PRs and suggestions are welcome.

If you find bugs or edge cases (especially with new benchmarks), feel free to open an issue.

---

## License

MIT License
