
import pandas as pd
import numpy as np
import re


# Recognized financial column names
COLUMN_ALIASES = {
    "revenue": [
        "sales",
        "net sales",
        "revenue",
        "total revenue",
        "net revenue"
    ],
    "cogs": [
        "cogs",
        "cost of goods sold",
        "cost of sales"
    ],
    "reported_profit": [
        "profit",
        "gross profit"
    ],
    "date": [
        "date",
        "transaction date",
        "period",
        "month date"
    ],
    "segment": [
        "segment",
        "business segment",
        "customer segment"
    ],
    "country": [
        "country",
        "geography",
        "region"
    ],
    "product": [
        "product",
        "product name"
    ],
    "discounts": [
        "discounts",
        "discount amount"
    ],
    "gross_sales": [
        "gross sales",
        "gross revenue"
    ],
    "units_sold": [
        "units sold",
        "quantity",
        "sales volume"
    ],
    "budget_revenue": [
        "budget revenue",
        "budgeted revenue",
        "revenue budget"
    ]
}


def normalize_name(name):
    """Standardize column names for matching."""

    name = str(name).strip().lower()
    name = re.sub(r"[_\-]+", " ", name)
    name = re.sub(r"\s+", " ", name)

    return name


def detect_columns(df):
    """Identify recognized financial columns."""

    detected = {}

    for field, aliases in COLUMN_ALIASES.items():

        matches = [
            column for column in df.columns
            if normalize_name(column) in aliases
        ]

        if len(matches) == 1:
            detected[field] = matches[0]

    return detected


def parse_numeric(series):
    """Convert financial values into numbers."""

    cleaned = series.astype("string").str.strip()

    cleaned = cleaned.str.replace(
        r"^\((.*)\)$",
        r"-\1",
        regex=True
    )

    cleaned = cleaned.str.replace(
        r"[$,]",
        "",
        regex=True
    )

    cleaned = cleaned.replace(
        ["", "-", "N/A", "nan"],
        pd.NA
    )

    result = pd.to_numeric(
        cleaned,
        errors="coerce"
    )

    return result.replace(
        [np.inf, -np.inf],
        np.nan
    )


def parse_dates(series, excel_epoch=None):
    # A bare number passed to pandas.to_datetime would otherwise be interpreted
    # as nanoseconds since 1970. Excel serial dates use the workbook's own epoch.
    text = series.astype("string").str.strip()
    numeric = text.str.fullmatch(r"\d+(?:\.\d+)?", na=False)
    packed = text.str.fullmatch(r"\d{8}", na=False)
    parsed = pd.to_datetime(text.mask(numeric), format="mixed", errors="coerce", utc=True).dt.tz_localize(None)
    if packed.any():
        parsed.loc[packed] = pd.to_datetime(text[packed], format="%Y%m%d", errors="coerce")
    if excel_epoch is not None:
        from openpyxl.utils.datetime import from_excel

        def convert(value):
            number = float(value)
            if 1900 <= number <= 2100 or not 1 <= number < 2958466:
                return pd.NaT
            try:
                return from_excel(number, epoch=excel_epoch)
            except (ValueError, OverflowError):
                return pd.NaT

        serial = numeric & ~packed
        if serial.any():
            parsed.loc[serial] = pd.to_datetime(text[serial].map(convert), errors="coerce")
    return parsed


def validate_financial_data(df, mapping=None, *, source_rows=None, excel_epoch=None):
    """Validate and standardize financial data."""

    errors = []
    warnings = []

    if df.empty:
        return {
            "valid": False,
            "errors": ["The dataset is empty."],
            "warnings": [],
            "mapping": {},
            "data": pd.DataFrame()
        }

    df = df.copy()

    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    if df.columns.duplicated().any():
        return {
            "valid": False,
            "errors": ["Duplicate column names detected."],
            "warnings": [],
            "mapping": {},
            "data": pd.DataFrame()
        }

    if mapping is None:
        mapping = detect_columns(df)

    if len(set(mapping.values())) != len(mapping):
        errors.append("A source column cannot be assigned to multiple financial fields.")

    required_fields = [
        "revenue",
        "cogs",
        "date"
    ]

    for field in required_fields:

        if field not in mapping:
            errors.append(
                f"Required field not detected: {field}"
            )

    clean_data = pd.DataFrame(index=df.index)

    clean_data["source_row"] = range(2, len(df) + 2) if source_rows is None else source_rows

    numeric_fields = [
        "revenue",
        "cogs",
        "reported_profit",
        "discounts",
        "gross_sales",
        "units_sold",
        "budget_revenue"
    ]

    for field, source_column in mapping.items():

        if source_column not in df.columns:
            errors.append(
                f"Source column missing: {source_column}"
            )
            continue

        if field in numeric_fields:

            clean_data[field] = parse_numeric(
                df[source_column]
            )

            missing = int(
                clean_data[field].isna().sum()
            )

            if missing > 0:

                message = (
                    f"{field}: {missing} missing "
                    "or invalid numeric values."
                )

                if field in required_fields:
                    errors.append(message)
                else:
                    warnings.append(message)

        elif field == "date":

            clean_data[field] = parse_dates(df[source_column], excel_epoch)

            invalid_dates = int(
                clean_data[field].isna().sum()
            )

            if invalid_dates > 0:
                errors.append(
                    f"{invalid_dates} invalid or missing dates."
                )

        else:

            clean_data[field] = (
                df[source_column]
                .astype("string")
                .str.strip()
            )

    # Detect possible duplicate records.
    duplicate_count = int(
        df.duplicated().sum()
    )

    if duplicate_count > 0:
        warnings.append(
            f"{duplicate_count} potential duplicate records. "
            "Review before removing them."
        )

    # Calculate gross profit independently.
    if {"revenue", "cogs"}.issubset(clean_data.columns):

        clean_data["gross_profit"] = (
            clean_data["revenue"]
            - clean_data["cogs"]
        )

        clean_data["gross_margin"] = (
            clean_data["gross_profit"]
            / clean_data["revenue"].replace(0, np.nan)
        )

        negative_revenue = int(
            (clean_data["revenue"] < 0).sum()
        )

        if negative_revenue > 0:
            warnings.append(
                f"{negative_revenue} negative revenue records. "
                "Check for returns or adjustments."
            )

        zero_revenue = int(
            (clean_data["revenue"] == 0).sum()
        )

        if zero_revenue > 0:
            warnings.append(
                f"{zero_revenue} zero-revenue records. "
                "Gross margin is undefined for these rows."
            )

    # Reconcile reported profit against calculated profit.
    if {
        "reported_profit",
        "gross_profit"
    }.issubset(clean_data.columns):

        difference = (
            clean_data["reported_profit"]
            - clean_data["gross_profit"]
        ).abs()

        mismatches = int(
            (difference > 0.01).sum()
        )

        if mismatches > 0:
            warnings.append(
                f"{mismatches} profit reconciliation "
                "differences detected."
            )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "mapping": mapping,
        "data": clean_data
    }
