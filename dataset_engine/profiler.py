from typing import Any

import numpy as np
import pandas as pd


class DatasetProfiler:
    """Profile data quality, shape, distributions, outliers, and correlations."""

    def profile(self, dataframe: pd.DataFrame) -> dict[str, Any]:
        if dataframe is None or not isinstance(dataframe, pd.DataFrame):
            raise TypeError("DatasetProfiler.profile expects a pandas DataFrame.")

        return {
            "null_analysis": self.null_analysis(dataframe),
            "unique_values": self.unique_values(dataframe),
            "outliers": self.outlier_detection(dataframe),
            "correlations": self.correlation_analysis(dataframe),
            "distributions": self.distribution_analysis(dataframe),
        }

    def null_analysis(self, dataframe: pd.DataFrame) -> dict[str, dict[str, float | int]]:
        row_count = max(len(dataframe), 1)
        analysis: dict[str, dict[str, float | int]] = {}

        for column in dataframe.columns:
            missing_count = int(dataframe[column].isna().sum())
            analysis[column] = {
                "missing_count": missing_count,
                "missing_percent": round((missing_count / row_count) * 100, 2),
            }

        return analysis

    def unique_values(self, dataframe: pd.DataFrame) -> dict[str, dict[str, Any]]:
        row_count = max(len(dataframe), 1)
        profile: dict[str, dict[str, Any]] = {}

        for column in dataframe.columns:
            unique_count = int(dataframe[column].nunique(dropna=True))
            sample_values = dataframe[column].dropna().astype(str).unique()[:10].tolist()
            profile[column] = {
                "unique_count": unique_count,
                "unique_percent": round((unique_count / row_count) * 100, 2),
                "sample_values": sample_values,
            }

        return profile

    def outlier_detection(self, dataframe: pd.DataFrame) -> dict[str, dict[str, Any]]:
        outliers: dict[str, dict[str, Any]] = {}

        for column in dataframe.select_dtypes(include=[np.number]).columns:
            series = dataframe[column].dropna()
            if series.empty:
                continue

            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - (1.5 * iqr)
            upper_bound = q3 + (1.5 * iqr)
            outlier_mask = (series < lower_bound) | (series > upper_bound)
            outlier_count = int(outlier_mask.sum())

            outliers[column] = {
                "method": "IQR",
                "outlier_count": outlier_count,
                "outlier_percent": round((outlier_count / max(len(series), 1)) * 100, 2),
                "lower_bound": self._to_python_number(lower_bound),
                "upper_bound": self._to_python_number(upper_bound),
            }

        return outliers

    def correlation_analysis(self, dataframe: pd.DataFrame) -> dict[str, Any]:
        numeric_data = dataframe.select_dtypes(include=[np.number])
        if numeric_data.shape[1] < 2:
            return {"matrix": {}, "strong_pairs": []}

        correlation_matrix = numeric_data.corr(numeric_only=True).round(3)
        strong_pairs = []

        columns = correlation_matrix.columns.tolist()
        for index, left_column in enumerate(columns):
            for right_column in columns[index + 1 :]:
                value = correlation_matrix.loc[left_column, right_column]
                if pd.notna(value) and abs(value) >= 0.7:
                    strong_pairs.append(
                        {
                            "columns": [left_column, right_column],
                            "correlation": float(value),
                            "strength": "positive" if value > 0 else "negative",
                        }
                    )

        return {
            "matrix": self._dataframe_to_serializable_dict(correlation_matrix),
            "strong_pairs": strong_pairs,
        }

    def distribution_analysis(self, dataframe: pd.DataFrame) -> dict[str, Any]:
        distributions: dict[str, Any] = {
            "numeric": {},
            "categorical": {},
            "datetime": {},
        }

        for column in dataframe.select_dtypes(include=[np.number]).columns:
            series = dataframe[column].dropna()
            if series.empty:
                continue

            counts, edges = np.histogram(series, bins=min(10, max(1, series.nunique())))
            distributions["numeric"][column] = {
                "min": self._to_python_number(series.min()),
                "max": self._to_python_number(series.max()),
                "mean": self._to_python_number(series.mean()),
                "median": self._to_python_number(series.median()),
                "histogram": {
                    "counts": [int(value) for value in counts],
                    "bin_edges": [self._to_python_number(value) for value in edges],
                },
            }

        for column in dataframe.select_dtypes(include=["object", "string", "category"]).columns:
            top_values = dataframe[column].value_counts(dropna=False).head(10)
            distributions["categorical"][column] = {
                "top_values": {str(index): int(value) for index, value in top_values.items()}
            }

        for column in dataframe.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns:
            series = dataframe[column].dropna()
            if series.empty:
                continue
            distributions["datetime"][column] = {
                "min": series.min().isoformat(),
                "max": series.max().isoformat(),
                "records_by_month": {
                    str(index): int(value)
                    for index, value in series.dt.to_period("M").value_counts().sort_index().items()
                },
            }

        return distributions

    def _dataframe_to_serializable_dict(self, dataframe: pd.DataFrame) -> dict[str, dict[str, Any]]:
        serializable = dataframe.replace({np.nan: None}).to_dict()
        return {
            str(column): {
                str(index): self._to_python_number(value)
                for index, value in values.items()
            }
            for column, values in serializable.items()
        }

    def _to_python_number(self, value):
        if pd.isna(value):
            return None
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            return round(float(value), 4)
        return value

