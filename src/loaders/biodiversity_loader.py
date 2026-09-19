"""Loader for the three biodiversity datasets.

Consumes the competition-provided community-science files:
  - iNaturalist observations          (birds / plants / insects)
  - OpenBioMaps Debrecen bird records (rare / uncommon / common)
  - PADAPT habitat conservation map   (44 patches)

All datasets share a ``debrecen_station`` column aligned to the Green
Sentinel station codes, so they can be merged by station code.
"""

import logging
from pathlib import Path

import pandas as pd

from src.config import BIODIVERSITY_DIR, BIODIVERSITY_FILES
from src.loaders.base_loader import BaseLoader

logger = logging.getLogger(__name__)

SPECIES_TYPE_MAP = {
    "bird": "Bird",
    "plant": "Plant",
    "insect": "Insect",
}


class BiodiversityLoader(BaseLoader):
    """Load and clean the three biodiversity CSV datasets."""

    def __init__(self, base_dir: Path | None = None) -> None:
        super().__init__("biodiversity")
        self._dir = base_dir or BIODIVERSITY_DIR
        self._inat: pd.DataFrame | None = None
        self._birds: pd.DataFrame | None = None
        self._habitats: pd.DataFrame | None = None

    def load(self) -> "BiodiversityLoader":
        def _read(name: str) -> pd.DataFrame:
            path = self._dir / BIODIVERSITY_FILES[name]
            return pd.read_csv(path)

        self._inat = _read("inaturalist")
        self._birds = _read("birds")
        self._habitats = _read("habitats")
        self._metadata = {
            "inaturalist_rows": len(self._inat),
            "bird_rows": len(self._birds),
            "habitat_patches": len(self._habitats),
            "source_dir": str(self._dir),
        }
        return self

    def clean(self) -> "BiodiversityLoader":
        for tbl in (self._inat, self._birds, self._habitats):
            if "debrecen_station" in tbl.columns:
                tbl["debrecen_station"] = (
                    tbl["debrecen_station"].astype(str).str.strip().str.upper()
                )
        if "date_observed" in self._inat.columns:
            self._inat["date_observed"] = pd.to_datetime(
                self._inat["date_observed"], errors="coerce"
            )
        if "date_observed" in self._birds.columns:
            self._birds["date_observed"] = pd.to_datetime(
                self._birds["date_observed"], errors="coerce"
            )
        if "last_survey_date" in self._habitats.columns:
            self._habitats["last_survey_date"] = pd.to_datetime(
                self._habitats["last_survey_date"], errors="coerce"
            )
        return self

    def standardize_format(self) -> "BiodiversityLoader":
        inat = self._inat.copy()
        birds = self._birds.copy()
        habitats = self._habitats.copy()

        inat_std = pd.DataFrame(
            {
                "dataset": "iNaturalist",
                "station": inat["debrecen_station"],
                "date": inat["date_observed"],
                "species": inat["species_name"],
                "species_type": inat["species_type"].str.capitalize(),
                "count": pd.to_numeric(inat["count"], errors="coerce"),
                "latitude": inat["latitude"],
                "longitude": inat["longitude"],
            }
        )
        bird_std = pd.DataFrame(
            {
                "dataset": "OpenBioMaps",
                "station": birds["debrecen_station"],
                "date": birds["date_observed"],
                "species": birds["species_english"],
                "species_type": "Bird",
                "count": pd.to_numeric(birds["abundance"], errors="coerce"),
                "latitude": birds["latitude"],
                "longitude": birds["longitude"],
            }
        )
        bird_std["rarity_status"] = birds.get("rarity_status", "common").fillna("common")

        habitat_std = pd.DataFrame(
            {
                "station": habitats["debrecen_station"],
                "habitat_type": habitats["habitat_type"],
                "conservation_status": habitats["conservation_status"],
                "species_richness_index": habitats["species_richness_index"],
                "habitat_area_hectares": habitats["habitat_area_hectares"],
                "restoration_potential": habitats["restoration_potential"],
                "latitude": habitats["latitude"],
                "longitude": habitats["longitude"],
            }
        )

        self._inat = inat
        self._birds = birds
        self._habitats = habitat_std

        obs = pd.concat([inat_std, bird_std], ignore_index=True)
        obs["count"] = obs["count"].fillna(1)
        self._data = obs
        self._metadata["observations"] = len(obs)
        self._metadata["unique_species"] = int(obs["species"].nunique())
        self._metadata["stations_monitored"] = sorted(obs["station"].unique().tolist())
        return self

    def get_inaturalist(self) -> pd.DataFrame:
        if self._inat is None:
            raise RuntimeError("BiodiversityLoader has not been run.")
        return self._inat

    def get_birds(self) -> pd.DataFrame:
        if self._birds is None:
            raise RuntimeError("BiodiversityLoader has not been run.")
        return self._birds

    def get_habitats(self) -> pd.DataFrame:
        if self._habitats is None:
            raise RuntimeError("BiodiversityLoader has not been run.")
        return self._habitats