from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.models import DirectVideoRequest, TemplateVideoRequest


class LeadsService:
    @staticmethod
    def read_table(path: str | Path) -> pd.DataFrame:
        path = Path(path)
        if path.suffix.lower() == '.csv':
            return pd.read_csv(path)
        if path.suffix.lower() in {'.xlsx', '.xlsm', '.xls'}:
            return pd.read_excel(path)
        raise ValueError('Only CSV and XLSX/XLS files are supported')

    @staticmethod
    def direct_requests_from_dataframe(df: pd.DataFrame, **overrides) -> list[DirectVideoRequest]:
        records = df.to_dict(orient='records')
        return [DirectVideoRequest(**record, **overrides) for record in records]

    @staticmethod
    def template_requests_from_dataframe(df: pd.DataFrame, **overrides) -> list[TemplateVideoRequest]:
        records = df.to_dict(orient='records')
        return [TemplateVideoRequest(**record, **overrides) for record in records]
