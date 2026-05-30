from dataclasses import dataclass, field
from typing import Any
import warnings

import numpy as np
import pandas as pd


@dataclass
class CleaningSummary:
    """Human-readable summary of changes made during cleaning."""

    original_shape: tuple[int, int]
    final_shape: tuple[int, int] = (0, 0)
    duplicate_rows_removed: int = 0
    columns_renamed: dict[str, str] = field(default_factory=dict)
    missing_values_before: dict[str, int] = field(default_factory=dict)
    missing_values_after: dict[str, int] = field(default_factory=dict)
    date_columns_converted: list[str] = field(default_factory=list)
    numeric_columns_converted: list[str] = field(default_factory=list)
    missing_value_strategy: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_shape": self.original_shape,
            "final_shape": self.final_shape,
            "duplicate_rows_removed": self.duplicate_rows_removed,
            "columns_renamed": self.columns_renamed,
            "missing_values_before": self.missing_values_before,
            "missing_values_after": self.missing_values_after,
            "date_columns_converted": self.date_columns_converted,
            "numeric_columns_converted": self.numeric_columns_converted,
            "missing_value_strategy": self.missing_value_strategy,
        }


class DatasetCleaner:
    """Clean common CSV/Excel data quality issues for BI analysis."""

    COMMON_NULL_VALUES = {"", " ", "na", "n/a", "none", "null", "nan", "-", "--"}

    def clean(self, dataframe: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
        """Return a cleaned DataFrame and a summary of cleaning actions."""

        if dataframe is None or not isinstance(dataframe, pd.DataFrame):
            raise TypeError("DatasetCleaner.clean expects a pandas DataFrame.")

        cleaned = dataframe.copy()
        summary = CleaningSummary(original_shape=cleaned.shape)

        cleaned, summary.columns_renamed = self.standardize_column_names(cleaned)
        cleaned = self.normalize_null_values(cleaned)
        summary.missing_values_before = cleaned.isna().sum().to_dict()

        before_rows = len(cleaned)
        cleaned = cleaned.drop_duplicates().reset_index(drop=True)
        summary.duplicate_rows_removed = before_rows - len(cleaned)

        cleaned, date_columns = self.convert_date_columns(cleaned)
        summary.date_columns_converted = date_columns

        cleaned, numeric_columns = self.fix_numeric_datatypes(cleaned)
        summary.numeric_columns_converted = numeric_columns

        cleaned, strategies = self.handle_missing_values(cleaned)
        summary.missing_value_strategy = strategies

        summary.final_shape = cleaned.shape
        summary.missing_values_after = cleaned.isna().sum().to_dict()

        return cleaned, summary.to_dict()

    def standardize_column_names(self, dataframe: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
        """Make column names consistent for downstream engines."""

        renamed_columns: dict[str, str] = {}
        used_names: set[str] = set()

        for column in dataframe.columns:
            original = str(column)
            clean_name = original.strip().lower()
            clean_name = clean_name.replace("%", "percent")
            clean_name = clean_name.replace("$", "amount")
            clean_name = "_".join(clean_name.replace("-", " ").split())
            clean_name = "".join(char for char in clean_name if char.isalnum() or char == "_")
            clean_name = clean_name.strip("_") or "column"

            unique_name = clean_name
            counter = 2
            while unique_name in used_names:
                unique_name = f"{clean_name}_{counter}"
                counter += 1

            used_names.add(unique_name)
            renamed_columns[original] = unique_name

        return dataframe.rename(columns=renamed_columns), renamed_columns

    def normalize_null_values(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Convert common text placeholders into real pandas missing values."""

        cleaned = dataframe.copy()
        for column in cleaned.select_dtypes(include=["object", "string"]).columns:
            cleaned[column] = cleaned[column].apply(
                lambda value: np.nan
                if isinstance(value, str) and value.strip().lower() in self.COMMON_NULL_VALUES
                else value
            )
        return cleaned

    def convert_date_columns(self, dataframe: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        """Detect and convert likely date columns without forcing unrelated text fields."""

        cleaned = dataframe.copy()
        converted_columns: list[str] = []

        for column in cleaned.columns:
            if pd.api.types.is_datetime64_any_dtype(cleaned[column]):
                converted_columns.append(column)
                continue

            if not pd.api.types.is_object_dtype(cleaned[column]):
                continue

            column_name_hint = any(token in column for token in ["date", "time", "month", "year"])
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                parsed = pd.to_datetime(cleaned[column], errors="coerce", format="mixed")
            parse_ratio = parsed.notna().mean()

            if column_name_hint and parse_ratio >= 0.6:
                cleaned[column] = parsed
                converted_columns.append(column)
            elif parse_ratio >= 0.85 and cleaned[column].nunique(dropna=True) > 2:
                cleaned[column] = parsed
                converted_columns.append(column)

        return cleaned, converted_columns

    def fix_numeric_datatypes(self, dataframe: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        """Convert currency, percentage, and numeric-looking text columns."""

        cleaned = dataframe.copy()
        converted_columns: list[str] = []

        for column in cleaned.select_dtypes(include=["object", "string"]).columns:
            normalized = (
                cleaned[column]
                .astype("string")
                .str.replace(",", "", regex=False)
                .str.replace("$", "", regex=False)
                .str.replace("%", "", regex=False)
                .str.strip()
            )
            numeric = pd.to_numeric(normalized, errors="coerce")
            conversion_ratio = numeric.notna().mean()

            if conversion_ratio >= 0.6:
                cleaned[column] = numeric
                converted_columns.append(column)

        return cleaned, converted_columns

    def handle_missing_values(self, dataframe: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
        """Fill missing values using simple, explainable defaults."""

        cleaned = dataframe.copy()
        strategies: dict[str, str] = {}

        for column in cleaned.columns:
            missing_count = int(cleaned[column].isna().sum())
            if missing_count == 0:
                continue

            if pd.api.types.is_numeric_dtype(cleaned[column]):
                median_value = cleaned[column].median()
                if pd.isna(median_value):
                    median_value = 0
                if (
                    pd.api.types.is_integer_dtype(cleaned[column])
                    and float(median_value) % 1 != 0
                ):
                    cleaned[column] = cleaned[column].astype("Float64")
                cleaned[column] = cleaned[column].fillna(median_value)
                strategies[column] = f"filled {missing_count} numeric values with median"
            elif pd.api.types.is_datetime64_any_dtype(cleaned[column]):
                cleaned[column] = cleaned[column].ffill().bfill()
                strategies[column] = f"filled {missing_count} date values using nearby dates"
            else:
                mode = cleaned[column].mode(dropna=True)
                fill_value = mode.iloc[0] if not mode.empty else "Unknown"
                cleaned[column] = cleaned[column].fillna(fill_value)
                strategies[column] = f"filled {missing_count} categorical values with mode"

        return cleaned, strategies
