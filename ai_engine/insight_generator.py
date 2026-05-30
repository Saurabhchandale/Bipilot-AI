from __future__ import annotations

import json
from typing import Any


class AIInsightGenerator:
    """Generate business insights from dataset analysis, profiling, and chart context."""

    def __init__(
        self,
        provider: str = "local",
        openai_api_key: str | None = None,
        gemini_api_key: str | None = None,
        openai_model: str = "gpt-4o-mini",
        gemini_model: str = "gemini-1.5-flash",
    ):
        self.provider = (provider or "local").lower()
        self.openai_api_key = openai_api_key
        self.gemini_api_key = gemini_api_key
        self.openai_model = openai_model
        self.gemini_model = gemini_model

    def generate(
        self,
        analysis: dict[str, Any],
        profile: dict[str, Any],
        detection: dict[str, Any],
        cleaning_summary: dict[str, Any],
        chart_specs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Return AI insights. Falls back to local rules when API access is unavailable."""

        context = self._build_context(
            analysis=analysis,
            profile=profile,
            detection=detection,
            cleaning_summary=cleaning_summary,
            chart_specs=chart_specs,
        )

        if self.provider == "openai" and self.openai_api_key:
            return self._generate_with_openai(context)

        if self.provider == "gemini" and self.gemini_api_key:
            return self._generate_with_gemini(context)

        return self._generate_local_insights(context)

    def _build_context(
        self,
        analysis: dict[str, Any],
        profile: dict[str, Any],
        detection: dict[str, Any],
        cleaning_summary: dict[str, Any],
        chart_specs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        columns = analysis.get("columns", {})
        metadata = analysis.get("metadata", {})
        null_analysis = profile.get("null_analysis", {})
        outliers = profile.get("outliers", {})
        correlations = profile.get("correlations", {})

        high_null_columns = [
            {
                "column": column,
                "missing_percent": details.get("missing_percent", 0),
            }
            for column, details in null_analysis.items()
            if details.get("missing_percent", 0) >= 10
        ]

        high_outlier_columns = [
            {
                "column": column,
                "outlier_percent": details.get("outlier_percent", 0),
            }
            for column, details in outliers.items()
            if details.get("outlier_percent", 0) >= 5
        ]

        return {
            "dataset_type": detection.get("detected_type", "Unknown"),
            "confidence": detection.get("confidence", 0),
            "rows": metadata.get("row_count", 0),
            "columns": metadata.get("column_count", 0),
            "numeric_columns": columns.get("numeric", []),
            "categorical_columns": columns.get("categorical", []),
            "datetime_columns": columns.get("datetime", []),
            "currency_columns": columns.get("currency", []),
            "percentage_columns": columns.get("percentage", []),
            "recommended_kpis": detection.get("recommended_kpis", []),
            "recommended_charts": [spec.get("title") for spec in chart_specs],
            "high_null_columns": high_null_columns,
            "high_outlier_columns": high_outlier_columns,
            "strong_correlations": correlations.get("strong_pairs", []),
            "duplicates_removed": cleaning_summary.get("duplicate_rows_removed", 0),
            "date_conversions": cleaning_summary.get("date_columns_converted", []),
            "numeric_conversions": cleaning_summary.get("numeric_columns_converted", []),
        }

    def _generate_with_openai(self, context: dict[str, Any]) -> dict[str, Any]:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.openai_api_key)
            response = client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a senior business intelligence analyst. "
                            "Return concise JSON with keys: summary, key_findings, risks, recommendations."
                        ),
                    },
                    {"role": "user", "content": self._prompt(context)},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)
            parsed["provider"] = "openai"
            return self._normalize_insight_payload(parsed)
        except Exception as exc:
            fallback = self._generate_local_insights(context)
            fallback["provider_note"] = f"OpenAI insight generation failed, local insights shown: {exc}"
            return fallback

    def _generate_with_gemini(self, context: dict[str, Any]) -> dict[str, Any]:
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel(self.gemini_model)
            response = model.generate_content(self._prompt(context))
            parsed = json.loads((response.text or "{}").strip().strip("`").replace("json\n", "", 1))
            parsed["provider"] = "gemini"
            return self._normalize_insight_payload(parsed)
        except Exception as exc:
            fallback = self._generate_local_insights(context)
            fallback["provider_note"] = f"Gemini insight generation failed, local insights shown: {exc}"
            return fallback

    def _generate_local_insights(self, context: dict[str, Any]) -> dict[str, Any]:
        dataset_type = context["dataset_type"]
        rows = context["rows"]
        columns = context["columns"]
        key_findings = [
            f"The uploaded dataset looks like a {dataset_type} dataset with {rows} rows and {columns} columns.",
            f"Detected {len(context['numeric_columns'])} numeric, {len(context['categorical_columns'])} categorical, and {len(context['datetime_columns'])} date columns.",
        ]

        if context["currency_columns"]:
            key_findings.append(
                "Currency-like metrics were found: " + ", ".join(context["currency_columns"][:4]) + "."
            )

        if context["strong_correlations"]:
            first_pair = context["strong_correlations"][0]
            key_findings.append(
                f"Strong correlation detected between {first_pair['columns'][0]} and {first_pair['columns'][1]}."
            )

        risks = []
        if context["high_null_columns"]:
            columns_with_nulls = ", ".join(item["column"] for item in context["high_null_columns"][:5])
            risks.append(f"Columns with high missing values may reduce insight quality: {columns_with_nulls}.")
        if context["high_outlier_columns"]:
            outlier_columns = ", ".join(item["column"] for item in context["high_outlier_columns"][:5])
            risks.append(f"Outliers are present in important numeric fields: {outlier_columns}.")
        if context["duplicates_removed"]:
            risks.append(f"{context['duplicates_removed']} duplicate rows were removed during cleaning.")
        if not risks:
            risks.append("No major quality risks were detected from the automated profile.")

        recommendations = []
        if context["recommended_kpis"]:
            recommendations.append("Track these KPIs first: " + ", ".join(context["recommended_kpis"][:4]) + ".")
        if context["recommended_charts"]:
            recommendations.append("Start dashboard review with: " + ", ".join(context["recommended_charts"][:3]) + ".")
        recommendations.append("Validate important business rules with a domain expert before final decisions.")

        return self._normalize_insight_payload(
            {
                "provider": "local",
                "summary": (
                    f"Bipilot AI detected this as a {dataset_type} dataset and prepared an initial BI analysis. "
                    "The insights below are generated from metadata, profiling, and chart recommendations."
                ),
                "key_findings": key_findings,
                "risks": risks,
                "recommendations": recommendations,
            }
        )

    def _prompt(self, context: dict[str, Any]) -> str:
        return (
            "Analyze this BI dataset context and return JSON only.\n"
            "JSON schema: {\n"
            '  "summary": "short executive summary",\n'
            '  "key_findings": ["finding 1", "finding 2"],\n'
            '  "risks": ["risk 1"],\n'
            '  "recommendations": ["recommendation 1"]\n'
            "}\n\n"
            f"Dataset context:\n{json.dumps(context, indent=2)}"
        )

    def _normalize_insight_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "provider": payload.get("provider", self.provider),
            "summary": str(payload.get("summary", "No summary generated.")),
            "key_findings": self._ensure_list(payload.get("key_findings")),
            "risks": self._ensure_list(payload.get("risks")),
            "recommendations": self._ensure_list(payload.get("recommendations")),
            "provider_note": payload.get("provider_note"),
        }

    def _ensure_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if value:
            return [str(value)]
        return []

