from typing import Any

import numpy as np
import pandas as pd


class DatasetAnalyzer:
    """Generate metadata and BI-friendly analysis from a cleaned dataset."""

    CURRENCY_KEYWORDS = {
        "amount",
        "revenue",
        "sales",
        "price",
        "cost",
        "profit",
        "income",
        "salary",
        "premium",
        "claim",
        "balance",
        "expense",
    }
    PERCENTAGE_KEYWORDS = {"percent", "percentage", "rate", "ratio", "margin", "growth"}
    BUSINESS_COLUMN_KEYWORDS = {
        "date": ["date", "time", "month", "year", "quarter"],
        "customer": ["customer", "client", "account", "buyer"],
        "employee": ["employee", "staff", "agent", "manager"],
        "product": ["product", "sku", "item", "category"],
        "location": ["country", "city", "state", "region", "branch"],
        "financial": list(CURRENCY_KEYWORDS),
        "performance": ["score", "rating", "target", "conversion", "retention"],
    }

    def analyze(self, dataframe: pd.DataFrame) -> dict[str, Any]:
        """Return a complete analysis payload for dashboard and AI engines."""

        if dataframe is None or not isinstance(dataframe, pd.DataFrame):
            raise TypeError("DatasetAnalyzer.analyze expects a pandas DataFrame.")

        numeric_columns = self.detect_numeric_columns(dataframe)
        categorical_columns = self.detect_categorical_columns(dataframe)
        datetime_columns = self.detect_datetime_columns(dataframe)
        currency_columns = self.detect_currency_columns(dataframe)
        percentage_columns = self.detect_percentage_columns(dataframe)

        return {
            "metadata": self.generate_metadata(dataframe),
            "columns": {
                "numeric": numeric_columns,
                "categorical": categorical_columns,
                "datetime": datetime_columns,
                "currency": currency_columns,
                "percentage": percentage_columns,
            },
            "business_columns": self.detect_business_relevant_columns(dataframe),
            "statistical_summary": self.generate_statistical_summary(dataframe),
        }

    def generate_metadata(self, dataframe: pd.DataFrame) -> dict[str, Any]:
        memory_usage_mb = dataframe.memory_usage(deep=True).sum() / (1024 * 1024)
        return {
            "row_count": int(dataframe.shape[0]),
            "column_count": int(dataframe.shape[1]),
            "columns": dataframe.columns.tolist(),
            "memory_usage_mb": round(float(memory_usage_mb), 4),
            "duplicate_rows": int(dataframe.duplicated().sum()),
            "total_missing_values": int(dataframe.isna().sum().sum()),
        }

    def detect_numeric_columns(self, dataframe: pd.DataFrame) -> list[str]:
        return dataframe.select_dtypes(include=[np.number]).columns.tolist()

    def detect_categorical_columns(self, dataframe: pd.DataFrame) -> list[str]:
        categorical_columns: list[str] = []

        for column in dataframe.columns:
            if pd.api.types.is_datetime64_any_dtype(dataframe[column]):
                continue
            if pd.api.types.is_object_dtype(dataframe[column]) or pd.api.types.is_string_dtype(dataframe[column]):
                categorical_columns.append(column)
                continue

            unique_ratio = dataframe[column].nunique(dropna=True) / max(len(dataframe), 1)
            if unique_ratio <= 0.05 and dataframe[column].nunique(dropna=True) <= 25:
                categorical_columns.append(column)

        return categorical_columns

    def detect_datetime_columns(self, dataframe: pd.DataFrame) -> list[str]:
        datetime_columns = dataframe.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns.tolist()

        for column in dataframe.columns:
            if column in datetime_columns:
                continue
            column_lower = column.lower()
            if any(token in column_lower for token in ["date", "time", "month", "year"]):
                sample = dataframe[column].dropna().head(100)
                if not sample.empty:
                    parsed = pd.to_datetime(sample, errors="coerce")
                    if parsed.notna().mean() >= 0.6:
                        datetime_columns.append(column)

        return datetime_columns

    def detect_currency_columns(self, dataframe: pd.DataFrame) -> list[str]:
        currency_columns: list[str] = []

        for column in dataframe.columns:
            name_match = any(keyword in column.lower() for keyword in self.CURRENCY_KEYWORDS)
            if name_match and pd.api.types.is_numeric_dtype(dataframe[column]):
                currency_columns.append(column)
                continue

            if pd.api.types.is_object_dtype(dataframe[column]):
                sample = dataframe[column].dropna().astype(str).head(100)
                symbol_ratio = sample.str.contains(r"[$€£₹]", regex=True).mean() if not sample.empty else 0
                if symbol_ratio >= 0.3:
                    currency_columns.append(column)

        return currency_columns

    def detect_percentage_columns(self, dataframe: pd.DataFrame) -> list[str]:
        percentage_columns: list[str] = []

        for column in dataframe.columns:
            name_match = any(keyword in column.lower() for keyword in self.PERCENTAGE_KEYWORDS)
            if name_match and pd.api.types.is_numeric_dtype(dataframe[column]):
                percentage_columns.append(column)
                continue

            if pd.api.types.is_object_dtype(dataframe[column]):
                sample = dataframe[column].dropna().astype(str).head(100)
                percent_ratio = sample.str.contains("%", regex=False).mean() if not sample.empty else 0
                if percent_ratio >= 0.3:
                    percentage_columns.append(column)

        return percentage_columns

    def detect_business_relevant_columns(self, dataframe: pd.DataFrame) -> dict[str, list[str]]:
        business_columns: dict[str, list[str]] = {}

        for business_area, keywords in self.BUSINESS_COLUMN_KEYWORDS.items():
            matches = [
                column
                for column in dataframe.columns
                if any(keyword in column.lower() for keyword in keywords)
            ]
            if matches:
                business_columns[business_area] = matches

        return business_columns

    def generate_statistical_summary(self, dataframe: pd.DataFrame) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "numeric": {},
            "categorical": {},
            "datetime": {},
        }

        numeric_columns = self.detect_numeric_columns(dataframe)
        if numeric_columns:
            numeric_summary = dataframe[numeric_columns].describe().replace({np.nan: None})
            summary["numeric"] = numeric_summary.to_dict()

        for column in self.detect_categorical_columns(dataframe):
            top_values = dataframe[column].value_counts(dropna=False).head(10)
            summary["categorical"][column] = {
                "unique_count": int(dataframe[column].nunique(dropna=True)),
                "top_values": {str(index): int(value) for index, value in top_values.items()},
            }

        for column in self.detect_datetime_columns(dataframe):
            parsed = pd.to_datetime(dataframe[column], errors="coerce")
            summary["datetime"][column] = {
                "min": parsed.min().isoformat() if parsed.notna().any() else None,
                "max": parsed.max().isoformat() if parsed.notna().any() else None,
                "valid_dates": int(parsed.notna().sum()),
            }

        return summary

