import logging
from typing import Any

import pandas as pd

from src.loaders.base_loader import BaseLoader

logger = logging.getLogger(__name__)


class DataPipeline:
    """Unified manager for registering, loading, and retrieving datasets."""

    def __init__(self) -> None:
        self._loaders: dict[str, BaseLoader] = {}
        self._datasets: dict[str, pd.DataFrame] = {}

    def add_dataset(self, loader: BaseLoader) -> "DataPipeline":
        self._loaders[loader.name] = loader
        logger.info("Registered loader: %s", loader.name)
        return self

    def load_all(self) -> "DataPipeline":
        for name, loader in self._loaders.items():
            logger.info("Running loader: %s", name)
            loader.run()
            self._datasets[name] = loader.get_data()
            logger.info("Dataset '%s' loaded: %s", name, self._datasets[name].shape)
        return self

    def get_dataset(self, name: str) -> pd.DataFrame:
        if name not in self._datasets:
            raise KeyError(f"Dataset '{name}' not found. Available: {list(self._datasets.keys())}")
        return self._datasets[name]

    def get_metadata(self) -> dict[str, Any]:
        meta: dict[str, Any] = {}
        for name, loader in self._loaders.items():
            meta[name] = loader.get_metadata()
        return meta

    @property
    def datasets(self) -> dict[str, pd.DataFrame]:
        return self._datasets
