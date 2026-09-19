import logging
from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class BaseLoader(ABC):
    """Abstract base class for all data loaders."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._data: pd.DataFrame | None = None
        self._metadata: dict[str, Any] = {}

    @abstractmethod
    def load(self) -> "BaseLoader":
        """Load raw data from source. Returns self for chaining."""

    @abstractmethod
    def clean(self) -> "BaseLoader":
        """Apply cleaning rules (anomalies, missing values). Returns self."""

    @abstractmethod
    def standardize_format(self) -> "BaseLoader":
        """Convert to standardised column schema. Returns self."""

    def get_data(self) -> pd.DataFrame:
        if self._data is None:
            raise RuntimeError(f"Loader '{self.name}' has not been run. Call load().")
        return self._data

    def get_metadata(self) -> dict[str, Any]:
        return {**self._metadata, "loader": self.name, "rows": len(self._data) if self._data is not None else 0}

    def run(self) -> "BaseLoader":
        self.load().clean().standardize_format()
        logger.info("Loader '%s' complete: %s rows, %s cols", self.name, len(self._data), self._data.columns.tolist())
        return self
