"""Discover financial worksheets while preserving original Excel row coordinates."""
import re
from dataclasses import dataclass
from io import BytesIO
from itertools import chain
from pathlib import Path
import pandas as pd
from finsight.data_validator import detect_columns, normalize_name, COLUMN_ALIASES, parse_numeric
from finsight.statement_normalization import SOURCE_UNITS


def workbook_values(data, filename):
    """Use an OOXML value snapshot for binary Excel files; keep modern files intact."""
    if Path(filename).suffix.lower() not in {".xls", ".xlsb"}:
        return data
    from openpyxl import Workbook
    snapshot = Workbook(write_only=True)
    with pd.ExcelFile(BytesIO(data), engine="calamine") as source:
        for name in source.sheet_names:
            target = snapshot.create_sheet(name)
            raw = source.parse(name, header=None, dtype=object, keep_default_na=False)
            write_saved_rows(target, raw.itertuples(index=False, name=None))
    output = BytesIO()
    snapshot.save(output)
    return output.getvalue()


def write_saved_rows(sheet, rows):
    from openpyxl.cell import WriteOnlyCell

    for row in rows:
        cells = []
        for value in row:
            cell = WriteOnlyCell(sheet, value=None if value == "" else value)
            if isinstance(value, str) and value:
                cell.data_type = "s"
            cells.append(cell)
        sheet.append(cells)


def csv_value_snapshot(frame):
    from openpyxl import Workbook

    workbook = Workbook(write_only=True)
    values = frame.astype(object).where(frame.notna(), None)
    rows = chain((frame.columns.tolist(),), values.itertuples(index=False, name=None))
    write_saved_rows(workbook.create_sheet("CSV"), rows)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()

@dataclass
class Candidate:
    sheet: str
    kind: str
    frame: pd.DataFrame
    header_row: int
    excluded: tuple = ()
    units: str = SOURCE_UNITS
    last_actual: int | None = None


PERIOD_LABELS = {
    "a": "actual", "actual": "actual", "actuals": "actual", "historical": "actual",
    "e": "forecast", "f": "forecast", "estimate": "forecast", "estimated": "forecast",
    "forecast": "forecast", "projected": "forecast", "budget": "forecast",
}


def fiscal_periods(raw, header):
    periods = []
    for column, value in enumerate(raw.iloc[header]):
        match = re.fullmatch(r"(?:FY\s*)?((?:19|20)\d{2})(?:\.0)?(?:\s*([A-Za-z]+))?", str(value).strip(), re.I)
        if not match or (match[2] and match[2].lower() not in PERIOD_LABELS):
            continue
        labels = {PERIOD_LABELS[token] for row in (header - 1, header + 1) if 0 <= row < len(raw)
                  if (token := str(raw.iat[row, column]).strip().lower()) in PERIOD_LABELS}
        if match[2]:
            labels.add(PERIOD_LABELS[match[2].lower()])
        periods.append((column, int(match[1]), next(iter(labels)) if len(labels) == 1 else None))
    return periods


def discover_sheet(sheet, raw):
    # A unique exact alias is required; no fuzzy guesses.
    for i in range(min(30, len(raw))):
        headers = [f"Unnamed column {j}" if pd.isna(x) or not str(x).strip() else str(x).strip()
                   for j,x in enumerate(raw.iloc[i],1)]
        if len(set(headers)) != len(headers):
            continue
        if not {'revenue','cogs','date'} <= detect_columns(pd.DataFrame(columns=headers)).keys():
            continue
        frame = raw.iloc[i+1:].dropna(how='all').copy()
        frame.columns = headers
        if not frame.empty:
            frame.attrs["excel_rows"] = tuple(int(index)+1 for index in frame.index)
            return Candidate(sheet, 'transaction', frame.reset_index(drop=True), i+1)
    # Avoid ratios, trends and assumptions even when labels match.
    if re.search(r'assumption|trend|common.size|\(cs\)', sheet, re.I):
        return None
    labels = [normalize_name(x) for x in raw.iloc[:,0]] if raw.shape[1] else []
    rows = {k:[i for i,x in enumerate(labels) if x in COLUMN_ALIASES[k]] for k in ('revenue','cogs')}
    if any(len(v)!=1 for v in rows.values()):
        return None
    for i in range(min(30,len(raw))):
        if labels[i] not in ('fiscal year','year','fiscal years'):
            continue
        years = fiscal_periods(raw, i)
        if not years or len({y for _, y, _ in years}) != len(years):
            continue
        records=[]; excluded=[]
        for j,y,_ in years:
            vals=parse_numeric(pd.Series([raw.iat[rows[k][0],j] for k in ('revenue','cogs')]))
            if vals.isna().any() or (vals<0).any():
                excluded.append(y); continue
            record = {"Fiscal year": y, "Fiscal year row": i + 1,
                      "Gross profit": float(vals.iloc[0] - vals.iloc[1])}
            for metric, label, value in zip(("Revenue", "COGS"), ("revenue", "cogs"), vals):
                row = rows[label][0]
                record[metric] = float(value)
                record[f"{metric} label"] = str(raw.iat[row, 0]).strip()
                record[f"{metric} cell"] = f"row {row + 1}, column {j + 1}"
            records.append(record)
        if records:
            title=' '.join(str(x) for x in raw.iloc[:i].values.ravel()).lower()
            scales = set(re.findall(r'(?:\bin\s*\$\s*|\busd\s+(?:in\s+)?)(dollars|thousands|millions|billions)\b', title))
            units = f"USD {next(iter(scales))}" if len(scales) == 1 else SOURCE_UNITS
            known_actuals = [year for _, year, kind in years if kind == "actual"]
            cutoff = max(known_actuals, default=None)
            accepted = {record["Fiscal year"] for record in records}
            if cutoff not in accepted or not all(
                kind == ("actual" if year <= cutoff else "forecast") for _, year, kind in years
            ):
                cutoff = None
            return Candidate(sheet, 'annual', pd.DataFrame(records), i+1, tuple(excluded), units, cutoff)
    return None


def discover_workbook(workbook):
    candidates=[]
    for sheet in workbook.sheet_names:
        raw=pd.read_excel(workbook,sheet_name=sheet,header=None)
        candidate=discover_sheet(sheet,raw)
        if candidate is not None:
            if candidate.kind == "transaction":
                candidate.frame.attrs["excel_epoch"] = workbook.book.epoch
            candidates.append(candidate)
    return candidates
