from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from ai_engine import AIInsightGenerator
from chart_engine import ChartRecommender, PlotlyChartGenerator
from config import DevelopmentConfig
from dataset_engine import (
    DatasetAnalyzer,
    DatasetCleaner,
    DatasetLoader,
    DatasetProfiler,
    DatasetTypeDetector,
)
from dataset_engine.loader import DatasetLoadError
from export_engine import PDFReportExporter


def create_app(config_object=DevelopmentConfig):
    """Application factory used by Flask and future tests."""

    app = Flask(__name__)
    app.config.from_object(config_object)

    app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)
    app.config["EXPORT_FOLDER"].mkdir(parents=True, exist_ok=True)
    app.config["DATABASE_PATH"].parent.mkdir(parents=True, exist_ok=True)

    @app.get("/")
    def upload_page():
        return render_template("upload.html")

    @app.post("/analyze")
    def analyze_dataset():
        uploaded_file = request.files.get("dataset")
        if uploaded_file is None or not uploaded_file.filename:
            flash("Please choose a CSV or Excel file.")
            return redirect(url_for("upload_page"))

        loader = DatasetLoader(app.config["ALLOWED_EXTENSIONS"])

        try:
            saved_path = loader.save_upload(uploaded_file, app.config["UPLOAD_FOLDER"])
            raw_dataframe = loader.load(saved_path)

            cleaned_dataframe, cleaning_summary = DatasetCleaner().clean(raw_dataframe)
            analysis = DatasetAnalyzer().analyze(cleaned_dataframe)
            profile = DatasetProfiler().profile(cleaned_dataframe)
            detection = DatasetTypeDetector().detect(cleaned_dataframe, analysis)
            chart_specs = ChartRecommender().recommend(cleaned_dataframe, analysis, detection)
            charts = PlotlyChartGenerator().generate_dashboard(cleaned_dataframe, chart_specs)
            ai_insights = AIInsightGenerator(
                provider=app.config["AI_PROVIDER"],
                openai_api_key=app.config["OPENAI_API_KEY"],
                gemini_api_key=app.config["GEMINI_API_KEY"],
                openai_model=app.config["OPENAI_MODEL"],
                gemini_model=app.config["GEMINI_MODEL"],
            ).generate(
                analysis=analysis,
                profile=profile,
                detection=detection,
                cleaning_summary=cleaning_summary,
                chart_specs=chart_specs,
            )

            export_filename = self_contained_export_name(saved_path.name)
            export_path = app.config["EXPORT_FOLDER"] / export_filename
            PDFReportExporter().export(
                output_path=export_path,
                original_filename=saved_path.name,
                cleaned_dataframe=cleaned_dataframe,
                cleaning_summary=cleaning_summary,
                analysis=analysis,
                profile=profile,
                detection=detection,
                ai_insights=ai_insights,
                chart_specs=chart_specs,
            )
        except DatasetLoadError as exc:
            flash(str(exc))
            return redirect(url_for("upload_page"))
        except Exception as exc:
            flash(f"Analysis failed: {exc}")
            return redirect(url_for("upload_page"))

        preview_html = cleaned_dataframe.head(20).to_html(
            classes="data-table",
            index=False,
            border=0,
        )

        return render_template(
            "results.html",
            filename=saved_path.name,
            cleaning_summary=cleaning_summary,
            analysis=analysis,
            profile=profile,
            detection=detection,
            charts=charts,
            ai_insights=ai_insights,
            export_filename=export_filename,
            preview_html=preview_html,
        )

    @app.get("/download/<path:filename>")
    def download_report(filename):
        return send_from_directory(
            app.config["EXPORT_FOLDER"],
            filename,
            as_attachment=True,
            download_name=filename,
        )

    return app


app = create_app()


def self_contained_export_name(original_filename: str) -> str:
    safe_stem = secure_filename(original_filename).rsplit(".", 1)[0] or "dataset"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{safe_stem}_bipilot_report_{timestamp}.pdf"


if __name__ == "__main__":
    app.run()
