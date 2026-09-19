import logging
from typing import Any

import numpy as np
import pandas as pd

from src.config import OUTLIER_SIGMA

logger = logging.getLogger(__name__)


class DataCleaner:
    """Anomaly handling, imputation, and outlier detection for long-format data.

    Operates on the standard 8-column schema produced by
    ``GreenSentinelLoader.standardize_format``.
    """

    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df.copy()
        self._report: dict[str, Any] = {}

    @property
    def report(self) -> dict[str, Any]:
        return self._report

    def clean(self) -> pd.DataFrame:
        df = self._df.copy()

        before_nans = int(df["value"].isna().sum())

        df["value"] = df.groupby(["station", "measurement_type"])["value"].transform(
            lambda s: s.ffill(limit=3).bfill(limit=3)
        )

        after_nans = int(df["value"].isna().sum())
        self._report["pre_imputation_nulls"] = before_nans
        self._report["post_imputation_nulls"] = after_nans

        outlier_mask = pd.Series(False, index=df.index)
        for _, grp in df.groupby("measurement_type"):
            std = grp["value"].std()
            mean = grp["value"].mean()
            if pd.notna(std) and std > 0:
                outlier_mask |= ((grp["value"] - mean).abs() > OUTLIER_SIGMA * std)

        self._report["outliers_flagged"] = int(outlier_mask.sum())
        self._report["outlier_measurements"] = (
            df.loc[outlier_mask, "measurement_type"]
            .value_counts()
            .to_dict()
        )

        self._df = df
        logger.info(
            "DataCleaner: %d -> %d nulls, %d outliers flagged",
            before_nans, after_nans, self._report["outliers_flagged"],
        )
        return df
