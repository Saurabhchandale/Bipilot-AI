from typing import Any

import pandas as pd
import plotly.express as px
import plotly.io as pio


class PlotlyChartGenerator:
    """Generate interactive Plotly chart HTML from chart recommendation specs."""

    def generate_dashboard(
        self,
        dataframe: pd.DataFrame,
        chart_specs: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        charts = []

        for index, spec in enumerate(chart_specs):
            try:
                figure = self._build_figure(dataframe, spec)
                if figure is None:
                    continue

                figure.update_layout(
                    template="plotly_white",
                    margin=dict(l=32, r=24, t=64, b=42),
                    height=420,
                    title=dict(text=spec["title"], x=0.02, xanchor="left"),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )

                html = pio.to_html(
                    figure,
                    full_html=False,
                    include_plotlyjs=True if index == 0 else False,
                    config={"displayModeBar": False, "responsive": True},
                )
                charts.append(
                    {
                        "title": spec["title"],
                        "description": spec.get("description", ""),
                        "html": html,
                    }
                )
            except Exception as exc:
                charts.append(
                    {
                        "title": spec.get("title", "Chart"),
                        "description": f"Could not generate this chart: {exc}",
                        "html": "",
                    }
                )

        return charts

    def _build_figure(self, dataframe: pd.DataFrame, spec: dict[str, Any]):
        chart_type = spec.get("chart_type")

        if chart_type == "line":
            chart_data = self._aggregate_by_date(dataframe, spec["x"], spec["y"])
            return px.line(chart_data, x=spec["x"], y=spec["y"], markers=True)

        if chart_type == "area":
            chart_data = self._aggregate_by_date(dataframe, spec["x"], spec["y"])
            chart_data[spec["y"]] = chart_data[spec["y"]].cumsum()
            return px.area(chart_data, x=spec["x"], y=spec["y"])

        if chart_type == "bar":
            chart_data = self._aggregate_by_category(dataframe, spec["x"], spec["y"])
            return px.bar(chart_data, x=spec["x"], y=spec["y"], text_auto=".2s")

        if chart_type == "pie":
            chart_data = dataframe[spec["names"]].value_counts(dropna=False).head(10).reset_index()
            chart_data.columns = [spec["names"], "record_count"]
            return px.pie(chart_data, names=spec["names"], values="record_count", hole=0.35)

        if chart_type == "scatter":
            color = spec.get("color")
            color_column = color if color in dataframe.columns else None
            return px.scatter(
                dataframe,
                x=spec["x"],
                y=spec["y"],
                color=color_column,
                trendline=None,
            )

        if chart_type == "heatmap":
            numeric_data = dataframe[spec["columns"]].select_dtypes(include="number")
            if numeric_data.shape[1] < 2:
                return None
            correlation = numeric_data.corr(numeric_only=True).round(2)
            return px.imshow(
                correlation,
                text_auto=True,
                aspect="auto",
                color_continuous_scale="RdBu_r",
                zmin=-1,
                zmax=1,
            )

        return None

    def _aggregate_by_date(self, dataframe: pd.DataFrame, date_column: str, metric_column: str) -> pd.DataFrame:
        chart_data = dataframe[[date_column, metric_column]].dropna().copy()
        chart_data[date_column] = pd.to_datetime(chart_data[date_column], errors="coerce")
        chart_data = chart_data.dropna(subset=[date_column])

        if chart_data.empty:
            return chart_data

        chart_data["period"] = chart_data[date_column].dt.to_period("M").dt.to_timestamp()
        grouped = chart_data.groupby("period", as_index=False)[metric_column].sum()
        return grouped.rename(columns={"period": date_column})

    def _aggregate_by_category(
        self, dataframe: pd.DataFrame, category_column: str, metric_column: str
    ) -> pd.DataFrame:
        chart_data = dataframe[[category_column, metric_column]].dropna().copy()
        grouped = (
            chart_data.groupby(category_column, as_index=False)[metric_column]
            .sum()
            .sort_values(metric_column, ascending=False)
            .head(12)
        )
        return grouped

