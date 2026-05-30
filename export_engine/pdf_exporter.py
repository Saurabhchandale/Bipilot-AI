from __future__ import annotations

from datetime import datetime
from pathlib import Path
from textwrap import wrap
from typing import Any

import pandas as pd


class PDFReportExporter:
    """Create a clean PDF analysis report without heavy system dependencies."""

    def export(
        self,
        output_path: str | Path,
        original_filename: str,
        cleaned_dataframe: pd.DataFrame,
        cleaning_summary: dict[str, Any],
        analysis: dict[str, Any],
        profile: dict[str, Any],
        detection: dict[str, Any],
        ai_insights: dict[str, Any],
        chart_specs: list[dict[str, Any]],
    ) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines = self._build_report_lines(
            original_filename=original_filename,
            cleaned_dataframe=cleaned_dataframe,
            cleaning_summary=cleaning_summary,
            analysis=analysis,
            profile=profile,
            detection=detection,
            ai_insights=ai_insights,
            chart_specs=chart_specs,
        )

        pages = self._paginate(lines)
        output_path.write_bytes(self._build_pdf_bytes(pages))
        return output_path

    def _build_report_lines(
        self,
        original_filename: str,
        cleaned_dataframe: pd.DataFrame,
        cleaning_summary: dict[str, Any],
        analysis: dict[str, Any],
        profile: dict[str, Any],
        detection: dict[str, Any],
        ai_insights: dict[str, Any],
        chart_specs: list[dict[str, Any]],
    ) -> list[tuple[str, str]]:
        metadata = analysis.get("metadata", {})
        columns = analysis.get("columns", {})

        lines: list[tuple[str, str]] = [
            ("title", "Bipilot AI - Dataset Analysis Report"),
            ("body", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"),
            ("body", f"Source file: {original_filename}"),
            ("space", ""),
            ("section", "Executive Overview"),
            ("body", f"Dataset type: {detection.get('detected_type', 'Unknown')}"),
            ("body", f"Confidence: {detection.get('confidence', 0)}%"),
            ("body", f"Rows after cleaning: {metadata.get('row_count', 0)}"),
            ("body", f"Columns: {metadata.get('column_count', 0)}"),
            ("body", f"Duplicates removed: {cleaning_summary.get('duplicate_rows_removed', 0)}"),
            ("body", f"Missing values remaining: {metadata.get('total_missing_values', 0)}"),
            ("space", ""),
            ("section", "AI Business Summary"),
            ("body", ai_insights.get("summary", "No AI summary generated.")),
        ]

        lines.extend(self._bullet_section("Key Findings", ai_insights.get("key_findings", [])))
        lines.extend(self._bullet_section("Risks", ai_insights.get("risks", [])))
        lines.extend(self._bullet_section("Recommendations", ai_insights.get("recommendations", [])))

        lines.extend(
            [
                ("section", "Detected Dataset Structure"),
                ("body", f"Numeric columns: {self._join_or_none(columns.get('numeric', []))}"),
                ("body", f"Categorical columns: {self._join_or_none(columns.get('categorical', []))}"),
                ("body", f"Date columns: {self._join_or_none(columns.get('datetime', []))}"),
                ("body", f"Currency columns: {self._join_or_none(columns.get('currency', []))}"),
                ("body", f"Percentage columns: {self._join_or_none(columns.get('percentage', []))}"),
                ("space", ""),
            ]
        )

        lines.extend(
            self._bullet_section("Recommended KPIs", detection.get("recommended_kpis", []))
        )

        chart_lines = [
            f"{spec.get('title', 'Chart')} ({spec.get('chart_type', 'chart')})"
            for spec in chart_specs
        ]
        lines.extend(self._bullet_section("Recommended Dashboard Visuals", chart_lines))

        lines.extend(self._quality_lines(profile))
        lines.extend(self._outlier_lines(profile))
        lines.extend(self._cleaned_preview_lines(cleaned_dataframe))
        return lines

    def _bullet_section(self, title: str, items: list[Any]) -> list[tuple[str, str]]:
        lines: list[tuple[str, str]] = [("section", title)]
        if not items:
            lines.append(("body", "No items detected."))
        for item in items:
            lines.append(("bullet", str(item)))
        lines.append(("space", ""))
        return lines

    def _quality_lines(self, profile: dict[str, Any]) -> list[tuple[str, str]]:
        lines: list[tuple[str, str]] = [("section", "Data Quality Summary")]
        null_analysis = profile.get("null_analysis", {})
        unique_values = profile.get("unique_values", {})

        for column, details in list(null_analysis.items())[:20]:
            unique_count = unique_values.get(column, {}).get("unique_count", 0)
            lines.append(
                (
                    "body",
                    f"{column}: missing {details.get('missing_count', 0)} "
                    f"({details.get('missing_percent', 0)}%), unique {unique_count}",
                )
            )

        if len(null_analysis) > 20:
            lines.append(("body", f"...and {len(null_analysis) - 20} more columns."))
        lines.append(("space", ""))
        return lines

    def _outlier_lines(self, profile: dict[str, Any]) -> list[tuple[str, str]]:
        lines: list[tuple[str, str]] = [("section", "Outlier Summary")]
        outliers = profile.get("outliers", {})

        if not outliers:
            lines.append(("body", "No numeric outlier profile available."))
        for column, details in list(outliers.items())[:15]:
            lines.append(
                (
                    "body",
                    f"{column}: {details.get('outlier_count', 0)} outliers "
                    f"({details.get('outlier_percent', 0)}%)",
                )
            )

        lines.append(("space", ""))
        return lines

    def _cleaned_preview_lines(self, dataframe: pd.DataFrame) -> list[tuple[str, str]]:
        lines: list[tuple[str, str]] = [("section", "Cleaned Data Preview")]
        preview = dataframe.head(12).copy()
        if preview.empty:
            lines.append(("body", "No rows available after cleaning."))
            return lines

        columns = [str(column)[:16] for column in preview.columns[:6]]
        lines.append(("body", " | ".join(columns)))
        lines.append(("body", "-" * min(92, max(10, len(" | ".join(columns))))))

        for _, row in preview.iloc[:, :6].iterrows():
            values = [str(value)[:16] for value in row.tolist()]
            lines.append(("body", " | ".join(values)))

        if dataframe.shape[1] > 6:
            lines.append(("body", f"Preview shows first 6 of {dataframe.shape[1]} columns."))
        if dataframe.shape[0] > 12:
            lines.append(("body", f"Preview shows first 12 of {dataframe.shape[0]} cleaned rows."))

        return lines

    def _paginate(self, lines: list[tuple[str, str]]) -> list[list[tuple[str, str]]]:
        pages: list[list[tuple[str, str]]] = [[]]
        line_count = 0

        for style, text in lines:
            wrapped_text = self._wrap_text(style, text)
            for chunk in wrapped_text:
                if line_count >= 44:
                    pages.append([])
                    line_count = 0
                pages[-1].append((style, chunk))
                line_count += 2 if style in {"title", "section", "space"} else 1

        return pages

    def _wrap_text(self, style: str, text: str) -> list[str]:
        if style == "space":
            return [""]
        prefix = "- " if style == "bullet" else ""
        width = 84 if style == "body" else 72
        wrapped = wrap(str(text), width=width) or [""]
        if prefix:
            return [prefix + wrapped[0]] + ["  " + line for line in wrapped[1:]]
        return wrapped

    def _build_pdf_bytes(self, pages: list[list[tuple[str, str]]]) -> bytes:
        objects: list[bytes] = []
        pages_object_id = 2
        font_object_id = 3
        page_object_ids = []

        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        objects.append(b"")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

        for page_lines in pages:
            content = self._page_content(page_lines)
            content_object_id = len(objects) + 2
            page_object_id = len(objects) + 1
            page_object_ids.append(page_object_id)
            objects.append(
                (
                    f"<< /Type /Page /Parent {pages_object_id} 0 R /MediaBox [0 0 612 792] "
                    f"/Resources << /Font << /F1 {font_object_id} 0 R >> >> "
                    f"/Contents {content_object_id} 0 R >>"
                ).encode("latin-1")
            )
            objects.append(
                f"<< /Length {len(content)} >>\nstream\n".encode("latin-1")
                + content
                + b"\nendstream"
            )

        kids = " ".join(f"{object_id} 0 R" for object_id in page_object_ids)
        objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_object_ids)} >>".encode(
            "latin-1"
        )

        return self._assemble_pdf(objects)

    def _page_content(self, lines: list[tuple[str, str]]) -> bytes:
        commands = ["BT", "/F1 11 Tf", "50 742 Td"]
        y_position = 742

        for style, text in lines:
            font_size = 18 if style == "title" else 14 if style == "section" else 10
            leading = 24 if style == "title" else 19 if style == "section" else 14
            if style == "space":
                y_position -= 10
                continue

            y_position -= leading
            commands.append(f"/F1 {font_size} Tf")
            commands.append(f"1 0 0 1 50 {y_position} Tm")
            commands.append(f"({self._escape_pdf_text(text)}) Tj")

        commands.append("ET")
        return "\n".join(commands).encode("latin-1", errors="replace")

    def _assemble_pdf(self, objects: list[bytes]) -> bytes:
        pdf = bytearray(b"%PDF-1.4\n")
        offsets = [0]

        for index, obj in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(f"{index} 0 obj\n".encode("latin-1"))
            pdf.extend(obj)
            pdf.extend(b"\nendobj\n")

        xref_offset = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
        pdf.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
        pdf.extend(
            (
                f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
                f"startxref\n{xref_offset}\n%%EOF"
            ).encode("latin-1")
        )
        return bytes(pdf)

    def _escape_pdf_text(self, text: str) -> str:
        return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def _join_or_none(self, values: list[Any]) -> str:
        return ", ".join(str(value) for value in values) if values else "None"
