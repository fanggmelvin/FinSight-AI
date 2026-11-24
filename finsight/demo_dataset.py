"""Load the bundled sample through the standard financial validator."""
from pathlib import Path
import pandas as pd
from finsight.data_validator import validate_financial_data


def load_demo_state():
    path = Path(__file__).resolve().parent.parent / "demo_data" / "financial_sample.csv"
    raw = pd.read_csv(path)
    result = validate_financial_data(raw)
    if not result["valid"]:
        raise ValueError("Bundled sample failed validation")
    return {"dataset_id": "bundled-financial-sample-v1", "financial_data": raw,
            "validated_data": result["data"], "validation_result": result,
            "file_name": "Microsoft Financial Sample (demo)", "sheet_name": "Raw_Data"}
