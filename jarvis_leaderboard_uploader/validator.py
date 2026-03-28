"""
validator.py
============
Validates everything before anything is written to disk:
  • Benchmark filename format
  • CSV columns and content
  • metadata.json required fields
"""

from __future__ import annotations

import csv
import json
import os
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from jarvis_leaderboard_uploader.logger import JarvisLogger

VALID_METHODS = {"AI", "ES", "FF", "QC", "EXP"}

VALID_SUBCATEGORIES = {
    "SinglePropertyPrediction",
    "SinglePropertyClass",
    "ImageClass",
    "TextClass",
    "TokenClass",
    "TextGen",
    "TextSummary",
    "MLFF",
    "Spectra",
    "EigenSolver",
    "AtomGen",
}

VALID_SPLITS = {"train", "val", "test"}
VALID_METRICS = {"mae", "acc", "multimae", "f1", "rmse", "r2"}

BENCHMARK_RE = re.compile(
    r"^(?P<method>[A-Z]+)"
    r"-(?P<subcategory>[A-Za-z]+)"
    r"-(?P<property>[^-]+)"
    r"-(?P<dataset>[^-]+)"
    r"-(?P<split>train|val|test)"
    r"-(?P<metric>[^-]+)$"
)

REQUIRED_METADATA_KEYS = {"model_name", "project_url"}


@dataclass
class BenchmarkName:
    method: str
    subcategory: str
    property_name: str
    dataset: str
    split: str
    metric: str
    raw: str

    @property
    def csv_filename(self) -> str:
        return f"{self.raw}.csv"

    @property
    def zip_filename(self) -> str:
        return f"{self.raw}.csv.zip"


class Validator:
    def __init__(self, logger: Optional[JarvisLogger] = None):
        self.logger = logger or JarvisLogger()
        self._errors: List[str] = []

    def parse_benchmark_name(self, benchmark: str) -> BenchmarkName:
        stem = benchmark
        for ext in (".csv.zip", ".csv", ".zip"):
            if stem.endswith(ext):
                stem = stem[: -len(ext)]
                self.logger.warning(f"Extension '{ext}' stripped from benchmark name automatically.")

        match = BENCHMARK_RE.match(stem)
        if not match:
            raise ValueError(
                f"Benchmark name '{stem}' does not match the required format:\n"
                "  METHOD-SUBCATEGORY-property-dataset-split-metric\n"
                "  Example: AI-SinglePropertyPrediction-formation_energy_peratom-dft_3d-test-mae\n"
                f"  Valid methods: {sorted(VALID_METHODS)}\n"
                f"  Valid subcategories: {sorted(VALID_SUBCATEGORIES)}\n"
                f"  Valid splits: {sorted(VALID_SPLITS)}"
            )

        groups = match.groupdict()
        warnings: List[str] = []

        if groups["method"] not in VALID_METHODS:
            warnings.append(
                f"Method '{groups['method']}' is not in the known set "
                f"{sorted(VALID_METHODS)}. It may still be valid if newly added."
            )
        if groups["subcategory"] not in VALID_SUBCATEGORIES:
            warnings.append(
                f"Subcategory '{groups['subcategory']}' is not in the known set. "
                "It may still be valid for newer leaderboard entries."
            )
        if groups["split"] not in VALID_SPLITS:
            raise ValueError(
                f"Split must be one of {sorted(VALID_SPLITS)}, got '{groups['split']}'."
            )

        for w in warnings:
            self.logger.warning(w)

        return BenchmarkName(
            method=groups["method"],
            subcategory=groups["subcategory"],
            property_name=groups["property"],
            dataset=groups["dataset"],
            split=groups["split"],
            metric=groups["metric"],
            raw=stem,
        )

    def validate_csv(
        self,
        csv_path: str | Path,
        *,
        expected_ids: Optional[List[str]] = None,
    ) -> Tuple[List[str], List[float]]:
        path = Path(csv_path)
        errors: List[str] = []

        if not path.exists():
            raise FileNotFoundError(
                f"CSV file not found: {path}\nMake sure the path is correct and the file exists."
            )

        if path.suffix.lower() not in (".csv",):
            self.logger.warning(
                f"File extension is '{path.suffix}' — expected '.csv'. Attempting to parse anyway."
            )

        ids: List[str] = []
        predictions: List[float] = []

        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                if reader.fieldnames is None:
                    raise ValueError(f"CSV file appears to be empty: {path}")

                fieldnames = [n.strip() for n in reader.fieldnames]
                missing_cols = {"id", "prediction"} - set(fieldnames)
                extra_cols = set(fieldnames) - {"id", "prediction"}

                if missing_cols:
                    errors.append(
                        f"Missing required column(s): {sorted(missing_cols)}.\n"
                        f"  Found columns: {fieldnames}\n  File: {path}"
                    )
                if extra_cols:
                    self.logger.warning(
                        f"Extra column(s) found and will be ignored: {sorted(extra_cols)}"
                    )
                if errors:
                    raise ValueError("\n".join(errors))

                seen_ids: set = set()
                for row_num, row in enumerate(reader, start=2):
                    row_id = str(row.get("id", "")).strip()
                    raw_pred = str(row.get("prediction", "")).strip()

                    if not row_id:
                        errors.append(f"Empty 'id' at row {row_num} in {path}")
                        continue
                    if row_id in seen_ids:
                        errors.append(f"Duplicate id '{row_id}' at row {row_num} in {path}")
                    seen_ids.add(row_id)

                    try:
                        pred_val = float(raw_pred)
                    except ValueError:
                        errors.append(
                            f"Non-numeric prediction '{raw_pred}' "
                            f"for id '{row_id}' at row {row_num} in {path}"
                        )
                        continue

                    ids.append(row_id)
                    predictions.append(pred_val)

        except (OSError, UnicodeDecodeError) as exc:
            raise ValueError(f"Could not read CSV file '{path}': {exc}") from exc

        if errors:
            error_sample = errors[:10]
            suffix = f"\n  … and {len(errors) - 10} more" if len(errors) > 10 else ""
            raise ValueError(
                f"CSV validation failed with {len(errors)} error(s):\n"
                + "\n".join(f"  • {e}" for e in error_sample)
                + suffix
            )

        if expected_ids is not None:
            expected_set = set(expected_ids)
            found_set = set(ids)
            missing = expected_set - found_set
            extra = found_set - expected_set
            if missing:
                self.logger.warning(
                    f"{len(missing)} expected ID(s) missing. First few: {sorted(missing)[:5]}"
                )
            if extra:
                self.logger.warning(
                    f"{len(extra)} unexpected ID(s). First few: {sorted(extra)[:5]}"
                )

        return ids, predictions

    def validate_metadata(self, metadata: Dict) -> Dict:
        errors = []
        for key in REQUIRED_METADATA_KEYS:
            if key not in metadata or not metadata[key]:
                errors.append(f"Required metadata key '{key}' is missing or empty.")
        if errors:
            raise ValueError(
                "metadata.json validation failed:\n"
                + "\n".join(f"  • {e}" for e in errors)
                + f"\n\nRequired keys: {sorted(REQUIRED_METADATA_KEYS)}"
            )
        recommended = {"authors", "description", "doi", "license"}
        missing_rec = recommended - set(metadata.keys())
        if missing_rec:
            self.logger.warning(
                f"Optional but recommended metadata fields missing: {sorted(missing_rec)}."
            )
        return metadata

    def load_and_validate_metadata(self, metadata_path: str | Path) -> Dict:
        path = Path(metadata_path)
        if not path.exists():
            raise FileNotFoundError(f"metadata.json not found at: {path}")
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Could not parse metadata file '{path}' as JSON.\n"
                f"  Error: {exc}\n  Make sure the file is valid JSON."
            ) from exc
        return self.validate_metadata(data)

    def validate_existing_zip(self, zip_path: str | Path) -> Tuple[List[str], List[float]]:
        path = Path(zip_path)
        if not path.exists():
            raise FileNotFoundError(f"Zip file not found: {path}")
        if not zipfile.is_zipfile(path):
            raise ValueError(
                f"'{path}' is not a valid zip file.\n"
                "JARVIS contributions must be CSV files zipped as .csv.zip."
            )
        with zipfile.ZipFile(path, "r") as zf:
            csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
            if not csv_names:
                raise ValueError(
                    f"No .csv file found inside zip archive '{path}'.\n"
                    "The archive must contain exactly one CSV file."
                )
            if len(csv_names) > 1:
                self.logger.warning(
                    f"Multiple CSV files found in zip: {csv_names}. Using '{csv_names[0]}'."
                )
            csv_content = zf.read(csv_names[0]).decode("utf-8")

        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(csv_content)
            tmp_path = tmp.name

        try:
            return self.validate_csv(tmp_path)
        finally:
            os.unlink(tmp_path)