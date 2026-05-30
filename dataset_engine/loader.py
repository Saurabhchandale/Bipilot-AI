from pathlib import Path
from typing import BinaryIO, Optional, Union

import pandas as pd

try:
    from werkzeug.datastructures import FileStorage
    from werkzeug.utils import secure_filename
except ModuleNotFoundError:
    FileStorage = None

    def secure_filename(filename: str) -> str:
        return Path(filename).name.replace(" ", "_")


class DatasetLoadError(Exception):
    """Raised when a dataset cannot be validated or loaded."""


class DatasetLoader:
    """Load CSV and Excel datasets into pandas DataFrames."""

    DEFAULT_ALLOWED_EXTENSIONS = {"csv", "xls", "xlsx"}

    def __init__(self, allowed_extensions: Optional[set[str]] = None):
        self.allowed_extensions = allowed_extensions or self.DEFAULT_ALLOWED_EXTENSIONS

    def is_allowed_file(self, filename: str) -> bool:
        """Return True when a filename has a supported dataset extension."""

        if not filename or "." not in filename:
            return False
        extension = filename.rsplit(".", 1)[1].lower()
        return extension in self.allowed_extensions

    def validate_file(self, filename: str) -> str:
        """Validate a filename and return its lowercase extension."""

        if not filename:
            raise DatasetLoadError("No file name was provided.")

        safe_name = secure_filename(filename)
        if not safe_name:
            raise DatasetLoadError("The uploaded file name is not valid.")

        if not self.is_allowed_file(safe_name):
            allowed = ", ".join(sorted(self.allowed_extensions))
            raise DatasetLoadError(f"Unsupported file type. Allowed types: {allowed}.")

        return safe_name.rsplit(".", 1)[1].lower()

    def load(
        self,
        file: Union[str, Path, BinaryIO],
        filename: Optional[str] = None,
        **read_options,
    ) -> pd.DataFrame:
        """
        Load a CSV or Excel dataset from a path, Flask upload, or file-like object.

        Args:
            file: File path, Werkzeug FileStorage, or readable binary object.
            filename: Required only when a raw file-like object has no name.
            **read_options: Optional keyword arguments passed to pandas.
        """

        source, resolved_filename = self._resolve_source(file, filename)
        extension = self.validate_file(resolved_filename)

        try:
            if extension == "csv":
                dataframe = pd.read_csv(source, **read_options)
            else:
                dataframe = pd.read_excel(source, **read_options)
        except UnicodeDecodeError as exc:
            raise DatasetLoadError(
                "Could not read the file encoding. Try saving the file as UTF-8 CSV."
            ) from exc
        except ValueError as exc:
            raise DatasetLoadError(f"The dataset format appears invalid: {exc}") from exc
        except Exception as exc:
            raise DatasetLoadError(f"Failed to load dataset: {exc}") from exc

        self._validate_dataframe(dataframe)
        return dataframe

    def save_upload(self, uploaded_file, upload_folder: Union[str, Path]) -> Path:
        """Validate and save a Flask upload to the configured dataset folder."""

        extension = self.validate_file(uploaded_file.filename or "")
        filename = secure_filename(uploaded_file.filename or f"dataset.{extension}")
        destination = Path(upload_folder) / filename
        destination.parent.mkdir(parents=True, exist_ok=True)

        try:
            uploaded_file.save(destination)
        except Exception as exc:
            raise DatasetLoadError(f"Could not save uploaded file: {exc}") from exc

        return destination

    def _resolve_source(
        self, file: Union[str, Path, FileStorage, BinaryIO], filename: Optional[str]
    ):
        if FileStorage is not None and isinstance(file, FileStorage):
            if not file.filename:
                raise DatasetLoadError("No uploaded file was selected.")
            return file.stream, file.filename

        if isinstance(file, (str, Path)):
            path = Path(file)
            if not path.exists():
                raise DatasetLoadError(f"Dataset file does not exist: {path}")
            if not path.is_file():
                raise DatasetLoadError(f"Dataset path is not a file: {path}")
            return path, path.name

        resolved_filename = filename or getattr(file, "name", None)
        if not resolved_filename:
            raise DatasetLoadError("A filename is required for file-like dataset objects.")
        return file, Path(resolved_filename).name

    @staticmethod
    def _validate_dataframe(dataframe: pd.DataFrame) -> None:
        if dataframe.empty:
            raise DatasetLoadError("The dataset is empty.")
        if dataframe.columns.empty:
            raise DatasetLoadError("The dataset does not contain columns.")
