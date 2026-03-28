"""
Unit tests for jarvis_leaderboard_uploader.
Run with: pytest tests/ -v
"""

import csv
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from jarvis_leaderboard_uploader.validator import Validator, BenchmarkName
from jarvis_leaderboard_uploader.packager import Packager, _sanitize_name
from jarvis_leaderboard_uploader.logger import JarvisLogger
from jarvis_leaderboard_uploader.runner import ScriptRunner


def _make_logger():
    return JarvisLogger(verbose=False)

def _write_csv(path: Path, rows: list) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "prediction"])
        writer.writeheader()
        writer.writerows(rows)

def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "jarvis_leaderboard"
    (repo / "jarvis_leaderboard" / "contributions").mkdir(parents=True)
    return repo


class TestBenchmarkNameParsing:
    def setup_method(self):
        self.v = Validator(logger=_make_logger())

    def test_valid_name(self):
        b = self.v.parse_benchmark_name(
            "AI-SinglePropertyPrediction-formation_energy_peratom-dft_3d-test-mae"
        )
        assert b.method == "AI"
        assert b.subcategory == "SinglePropertyPrediction"
        assert b.property_name == "formation_energy_peratom"
        assert b.dataset == "dft_3d"
        assert b.split == "test"
        assert b.metric == "mae"

    def test_strips_csv_zip_extension(self):
        b = self.v.parse_benchmark_name(
            "AI-SinglePropertyPrediction-bandgap-dft_3d-test-mae.csv.zip"
        )
        assert b.metric == "mae"

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="does not match"):
            self.v.parse_benchmark_name("not-a-valid-name")

    def test_invalid_split_raises(self):
        with pytest.raises(ValueError):
            self.v.parse_benchmark_name(
                "AI-SinglePropertyPrediction-bandgap-dft_3d-INVALID-mae"
            )

    def test_zip_filename_property(self):
        b = self.v.parse_benchmark_name(
            "ES-SinglePropertyPrediction-bandgap_JVASP_1002_Si-dft_3d-test-mae"
        )
        assert b.zip_filename.endswith(".csv.zip")
        assert b.csv_filename.endswith(".csv")


class TestCSVValidation:
    def setup_method(self):
        self.v = Validator(logger=_make_logger())

    def test_valid_csv(self, tmp_path):
        p = tmp_path / "preds.csv"
        _write_csv(p, [{"id": "JVASP-1", "prediction": 1.5},
                       {"id": "JVASP-2", "prediction": -0.3}])
        ids, preds = self.v.validate_csv(p)
        assert ids == ["JVASP-1", "JVASP-2"]
        assert preds == [1.5, -0.3]

    def test_missing_prediction_column(self, tmp_path):
        p = tmp_path / "bad.csv"
        with open(p, "w") as f:
            f.write("id,value\nJVASP-1,1.0\n")
        with pytest.raises(ValueError, match="Missing required column"):
            self.v.validate_csv(p)

    def test_non_numeric_prediction(self, tmp_path):
        p = tmp_path / "bad.csv"
        _write_csv(p, [{"id": "JVASP-1", "prediction": "abc"}])
        with pytest.raises(ValueError, match="Non-numeric"):
            self.v.validate_csv(p)

    def test_duplicate_ids(self, tmp_path):
        p = tmp_path / "dup.csv"
        _write_csv(p, [{"id": "JVASP-1", "prediction": 1.0},
                       {"id": "JVASP-1", "prediction": 2.0}])
        with pytest.raises(ValueError, match="Duplicate"):
            self.v.validate_csv(p)

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            self.v.validate_csv("/nonexistent/path.csv")

    def test_empty_id_raises(self, tmp_path):
        p = tmp_path / "empty_id.csv"
        _write_csv(p, [{"id": "", "prediction": 1.0}])
        with pytest.raises(ValueError, match="Empty 'id'"):
            self.v.validate_csv(p)


class TestMetadataValidation:
    def setup_method(self):
        self.v = Validator(logger=_make_logger())

    def test_valid_metadata(self):
        m = {"model_name": "MyModel", "project_url": "https://example.com"}
        result = self.v.validate_metadata(m)
        assert result["model_name"] == "MyModel"

    def test_missing_model_name(self):
        with pytest.raises(ValueError, match="model_name"):
            self.v.validate_metadata({"project_url": "https://example.com"})

    def test_missing_project_url(self):
        with pytest.raises(ValueError, match="project_url"):
            self.v.validate_metadata({"model_name": "MyModel"})

    def test_load_from_file(self, tmp_path):
        p = tmp_path / "metadata.json"
        p.write_text(json.dumps({"model_name": "M", "project_url": "https://x.com"}))
        result = self.v.load_and_validate_metadata(p)
        assert result["model_name"] == "M"

    def test_bad_json_raises(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{not valid json}")
        with pytest.raises(ValueError, match="parse"):
            self.v.load_and_validate_metadata(p)


class TestZipValidation:
    def setup_method(self):
        self.v = Validator(logger=_make_logger())

    def test_valid_zip(self, tmp_path):
        csv_file = tmp_path / "preds.csv"
        _write_csv(csv_file, [{"id": "A", "prediction": 1.0}])
        zip_path = tmp_path / "preds.csv.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(csv_file, arcname="preds.csv")
        ids, preds = self.v.validate_existing_zip(zip_path)
        assert ids == ["A"]

    def test_not_a_zip(self, tmp_path):
        p = tmp_path / "fake.zip"
        p.write_bytes(b"not a zip")
        with pytest.raises(ValueError, match="valid zip"):
            self.v.validate_existing_zip(p)

    def test_zip_without_csv(self, tmp_path):
        zip_path = tmp_path / "empty.csv.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("readme.txt", "hello")
        with pytest.raises(ValueError, match="No .csv"):
            self.v.validate_existing_zip(zip_path)


class TestPackager:
    def test_create_contribution(self, tmp_path):
        repo = _make_repo(tmp_path)
        packager = Packager(repo_path=repo, logger=_make_logger())
        v = Validator(logger=_make_logger())
        bench = v.parse_benchmark_name("AI-SinglePropertyPrediction-bandgap-dft_3d-test-mae")
        csv_file = tmp_path / "preds.csv"
        _write_csv(csv_file, [{"id": "JVASP-1", "prediction": 1.2}])
        metadata = {"model_name": "M", "project_url": "https://x.com"}
        result = packager.create_contribution(
            contribution_name="test_model", benchmark=bench,
            csv_path=csv_file, metadata=metadata,
        )
        assert result.exists()
        assert (result / "AI-SinglePropertyPrediction-bandgap-dft_3d-test-mae.csv.zip").exists()
        assert (result / "metadata.json").exists()
        assert (result / "run.sh").exists()

    def test_overwrite_false_raises(self, tmp_path):
        repo = _make_repo(tmp_path)
        packager = Packager(repo_path=repo, logger=_make_logger())
        v = Validator(logger=_make_logger())
        bench = v.parse_benchmark_name("AI-SinglePropertyPrediction-bandgap-dft_3d-test-mae")
        csv_file = tmp_path / "p.csv"
        _write_csv(csv_file, [{"id": "A", "prediction": 1.0}])
        metadata = {"model_name": "M", "project_url": "https://x.com"}
        packager.create_contribution(
            contribution_name="dup_model", benchmark=bench, csv_path=csv_file, metadata=metadata
        )
        with pytest.raises(FileExistsError):
            packager.create_contribution(
                contribution_name="dup_model", benchmark=bench,
                csv_path=csv_file, metadata=metadata, overwrite=False,
            )

    def test_overwrite_true_replaces(self, tmp_path):
        repo = _make_repo(tmp_path)
        packager = Packager(repo_path=repo, logger=_make_logger())
        v = Validator(logger=_make_logger())
        bench = v.parse_benchmark_name("AI-SinglePropertyPrediction-bandgap-dft_3d-test-mae")
        csv_file = tmp_path / "p.csv"
        _write_csv(csv_file, [{"id": "A", "prediction": 1.0}])
        metadata = {"model_name": "M", "project_url": "https://x.com"}
        packager.create_contribution(
            contribution_name="dup2", benchmark=bench, csv_path=csv_file, metadata=metadata
        )
        packager.create_contribution(
            contribution_name="dup2", benchmark=bench,
            csv_path=csv_file, metadata=metadata, overwrite=True,
        )


class TestSanitizeName:
    def test_safe_name(self):
        assert _sanitize_name("my_model-v1.0") == "my_model-v1.0"
    def test_spaces_replaced(self):
        assert " " not in _sanitize_name("my model v1")
    def test_slashes_replaced(self):
        assert "/" not in _sanitize_name("path/to/model")


class TestScriptRunner:
    def test_run_with_output_csv(self, tmp_path):
        csv_out = tmp_path / "out.csv"
        _write_csv(csv_out, [{"id": "A", "prediction": 0.5}])
        runner = ScriptRunner(logger=_make_logger())
        result = runner.run(f"{sys.executable} -c 'pass'", output_csv=str(csv_out))
        assert result == csv_out

    def test_run_script_failure_raises(self):
        runner = ScriptRunner(logger=_make_logger())
        with pytest.raises(RuntimeError, match="non-zero return code"):
            runner.run(f"{sys.executable} -c 'import sys; sys.exit(1)'")

    def test_capture_stdout(self, tmp_path):
        runner = ScriptRunner(logger=_make_logger())
        script = f'{sys.executable} -c "print(\'id,prediction\'); print(\'A,1.0\')"'
        result = runner.run(script, capture_stdout_as_csv=True)
        assert result.exists()
        content = result.read_text()
        assert "id,prediction" in content
        result.unlink()