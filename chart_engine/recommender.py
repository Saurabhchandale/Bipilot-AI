from typing import Any

import pandas as pd


class ChartRecommender:
    """Recommend dashboard charts from dataset analysis and detected business type."""

    def recommend(
        self,
        dataframe: pd.DataFrame,
        analysis: dict[str, Any],
        detection: dict[str, Any],
        max_charts: int = 6,
    ) -> list[dict[str, Any]]:
        if dataframe is None or not isinstance(dataframe, pd.DataFrame):
            raise TypeError("ChartRecommender.recommend expects a pandas DataFrame.")

        columns = analysis.get("columns", {})
        numeric_columns = columns.get("numeric", [])
        categorical_columns = columns.get("categorical", [])
        datetime_columns = columns.get("datetime", [])
        currency_columns = columns.get("currency", [])
        dataset_type = detection.get("detected_type", "Unknown")

        chart_specs: list[dict[str, Any]] = []

        primary_metric = self._pick_primary_metric(numeric_columns, currency_columns)
        primary_category = self._pick_primary_category(dataframe, categorical_columns)
        primary_date = datetime_columns[0] if datetime_columns else None

        if primary_date and primary_metric:
            chart_specs.append(
                {
                    "chart_type": "line",
                    "title": f"{self._label(primary_metric)} Trend",
                    "x": primary_date,
                    "y": primary_metric,
                    "description": "Shows how the main metric changes over time.",
                }
            )

        if primary_category and primary_metric:
            chart_specs.append(
                {
                    "chart_type": "bar",
                    "title": f"{self._label(primary_metric)} by {self._label(primary_category)}",
                    "x": primary_category,
                    "y": primary_metric,
                    "description": "Compares the main metric across business categories.",
                }
            )

        if primary_category:
            chart_specs.append(
                {
                    "chart_type": "pie",
                    "title": f"{self._label(primary_category)} Distribution",
                    "names": primary_category,
                    "description": "Shows the share of records by category.",
                }
            )

        if len(numeric_columns) >= 2:
            chart_specs.append(
                {
                    "chart_type": "scatter",
                    "title": f"{self._label(numeric_columns[0])} vs {self._label(numeric_columns[1])}",
                    "x": numeric_columns[0],
                    "y": numeric_columns[1],
                    "color": primary_category,
                    "description": "Highlights relationships between two numeric fields.",
                }
            )

        if len(numeric_columns) >= 2:
            chart_specs.append(
                {
                    "chart_type": "heatmap",
                    "title": "Correlation Heatmap",
                    "columns": numeric_columns[:8],
                    "description": "Shows correlation strength between numeric fields.",
                }
            )

        chart_specs.extend(
            self._domain_specific_charts(
                dataframe=dataframe,
                dataset_type=dataset_type,
                numeric_columns=numeric_columns,
                categorical_columns=categorical_columns,
                datetime_columns=datetime_columns,
                currency_columns=currency_columns,
            )
        )

        return self._deduplicate(chart_specs)[:max_charts]

    def _domain_specific_charts(
        self,
        dataframe: pd.DataFrame,
        dataset_type: str,
        numeric_columns: list[str],
        categorical_columns: list[str],
        datetime_columns: list[str],
        currency_columns: list[str],
    ) -> list[dict[str, Any]]:
        specs: list[dict[str, Any]] = []
        metric = self._pick_primary_metric(numeric_columns, currency_columns)
        date_column = datetime_columns[0] if datetime_columns else None

        domain_category_keywords = {
            "Sales": ["product", "region", "customer", "category"],
            "Finance": ["department", "category", "account", "type"],
            "HR": ["department", "job", "role", "manager"],
            "Marketing": ["campaign", "channel", "source", "medium"],
            "Inventory": ["product", "sku", "warehouse", "supplier"],
            "Insurance": ["policy", "claim", "risk", "agent"],
        }

        category = self._find_column_by_keywords(
            dataframe,
            categorical_columns,
            domain_category_keywords.get(dataset_type, []),
        )

        if category and metric:
            specs.append(
                {
                    "chart_type": "bar",
                    "title": f"{dataset_type}: {self._label(metric)} by {self._label(category)}",
                    "x": category,
                    "y": metric,
                    "description": f"Domain-focused comparison for {dataset_type.lower()} analysis.",
                }
            )

        if date_column and metric and dataset_type in {"Sales", "Finance", "Marketing", "Insurance"}:
            specs.append(
                {
                    "chart_type": "area",
                    "title": f"{dataset_type}: Cumulative {self._label(metric)}",
                    "x": date_column,
                    "y": metric,
                    "description": "Shows cumulative movement of the key metric over time.",
                }
            )

        return specs

    def _pick_primary_metric(self, numeric_columns: list[str], currency_columns: list[str]) -> str | None:
        if currency_columns:
            return currency_columns[0]
        preferred_tokens = ["revenue", "sales", "amount", "profit", "cost", "salary", "premium", "claim"]
        for token in preferred_tokens:
            for column in numeric_columns:
                if token in column.lower():
                    return column
        return numeric_columns[0] if numeric_columns else None

    def _pick_primary_category(self, dataframe: pd.DataFrame, categorical_columns: list[str]) -> str | None:
        good_categories = []
        for column in categorical_columns:
            unique_count = dataframe[column].nunique(dropna=True)
            if 2 <= unique_count <= 20:
                good_categories.append((column, unique_count))
        if not good_categories:
            return categorical_columns[0] if categorical_columns else None
        return sorted(good_categories, key=lambda item: item[1])[0][0]

    def _find_column_by_keywords(
        self, dataframe: pd.DataFrame, columns: list[str], keywords: list[str]
    ) -> str | None:
        for keyword in keywords:
            for column in columns:
                if keyword in column.lower() and dataframe[column].nunique(dropna=True) >= 2:
                    return column
        return self._pick_primary_category(dataframe, columns)

    def _deduplicate(self, specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen = set()
        unique_specs = []
        for spec in specs:
            key = (
                spec.get("chart_type"),
                spec.get("x"),
                spec.get("y"),
                spec.get("names"),
                tuple(spec.get("columns", [])),
            )
            if key in seen:
                continue
            seen.add(key)
            unique_specs.append(spec)
        return unique_specs

    def _label(self, column: str) -> str:
        return column.replace("_", " ").title()

