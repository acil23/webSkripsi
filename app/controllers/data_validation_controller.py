"""Control layer untuk UC-01 Mengunggah Data Masukan."""

from __future__ import annotations

from app.entities.dataset_bundle import DatasetBundle
from app.services.data_loader_service import DataLoaderService, UploadedCsvPayload


class DataValidationController:
    def __init__(self, data_loader: DataLoaderService | None = None):
        self.data_loader = data_loader or DataLoaderService()

    def validate_uploaded_data(self, payloads: dict[str, list[UploadedCsvPayload]]) -> DatasetBundle:
        dataset = self.data_loader.validate_and_store_payloads(payloads)
        self._check_completeness(dataset)
        self._check_structure(dataset)
        return dataset

    def get_empty_dataset_bundle(self) -> DatasetBundle:
        return self.data_loader.create_empty_bundle()

    def _check_completeness(self, dataset: DatasetBundle) -> bool:
        return dataset.is_complete()

    def _check_structure(self, dataset: DatasetBundle) -> bool:
        return all(result.status != "Error" for result in dataset.datasets.values())
