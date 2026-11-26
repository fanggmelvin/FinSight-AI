"""Prepare supported uploads and expose source options when a sheet needs them."""
import hashlib
from io import BytesIO

import pandas as pd

from finsight.annual_analytics import annual_state
from finsight.data_validator import COLUMN_ALIASES, detect_columns, validate_financial_data
from finsight.demo_dataset import load_demo_state
from finsight.statement_normalization import SCALES, SOURCE_UNITS, normalize_annual
from finsight.workbook_ingestion import csv_value_snapshot, discover_workbook, workbook_values


def read_upload(name, data, identity):
    if name.lower().endswith(".csv"):
        return {"id": identity, "name": name, "frame": pd.read_csv(BytesIO(data)), "selected": "CSV"}
    data = workbook_values(data, name)
    with pd.ExcelFile(BytesIO(data), engine="openpyxl") as workbook:
        sheets = list(workbook.sheet_names)
        if not sheets:
            raise ValueError("The workbook contains no worksheets.")
        candidates = {candidate.sheet: candidate for candidate in discover_workbook(workbook)}
    return {"id": identity, "name": name, "bytes": data, "sheets": sheets,
            "candidates": candidates, "selected": next(iter(candidates), sheets[0])}


def render_upload(st, clear_validation, open_workbook_in_copilot):
    state = st.session_state
    st.title("Financial Data Upload")
    if st.button("Restore demo dataset", key="restore_demo_dataset"):
        for key in ("pending_upload", "chat_workbook", "workbook_conversations", "copilot_mode"):
            state.pop(key, None)
        clear_validation()
        state.update(load_demo_state())
        state["scenario_demo_source"] = True
        state["upload_widget_generation"] = state.get("upload_widget_generation", 0) + 1
        st.rerun()

    incoming = st.file_uploader("Choose a financial data file",
                                type=["xlsx", "xlsm", "xltx", "xltm", "xls", "xlsb", "csv"],
                                key=f"financial_upload_{state.get('upload_widget_generation', 0)}")
    upload = state.get("pending_upload")
    new = False
    if incoming is not None:
        contents = incoming.getvalue()
        identity = hashlib.sha256(contents).hexdigest()
        new = upload is None or (upload["id"], upload["name"]) != (identity, incoming.name)
        if new:
            try:
                upload = read_upload(incoming.name, contents, identity)
            except Exception as error:
                st.error(f"Unable to read file: {error}")
                return
            state["pending_upload"] = upload

    if upload is None:
        st.info("Upload an Excel workbook or CSV to get started.")
        return

    is_workbook = "sheets" in upload
    sheet = upload["selected"]
    candidate = None
    if is_workbook:
        sheets = upload["sheets"]
        if len(sheets) > 1:
            sheet = st.selectbox("Worksheet", sheets, index=sheets.index(sheet), key=f"upload_sheet_{upload['id']}")
        upload["selected"] = sheet
        candidate = upload["candidates"].get(sheet)
        state["chat_workbook"] = upload
        st.button("Ask in AI Copilot", on_click=open_workbook_in_copilot, args=(upload["id"],), key="open_workbook_chat")

    source_id = f"{upload['id']}:{sheet}"
    if candidate and candidate.kind == "annual":
        ready = render_annual_options(st, upload, candidate, source_id, clear_validation)
    else:
        ready = render_table_options(st, upload, candidate, source_id, clear_validation, new)

    if new and ready:
        state["copilot_mode"] = "Financial analysis"
        state["workspace_page"] = "Overview"
        st.rerun()
    if new:
        if not is_workbook:
            try:
                snapshot = csv_value_snapshot(upload["frame"])
            except Exception as error:
                st.warning(f"Unable to open the CSV in Copilot: {error}")
                return
            upload.update(bytes=snapshot, sheets=["CSV"], candidates={})
            state["chat_workbook"] = upload
        clear_validation()
        for key in ("validated_data", "financial_data", "dataset_id"):
            state.pop(key, None)
        state.update(file_name=upload["name"], sheet_name=sheet, scenario_demo_source=False)
        open_workbook_in_copilot(upload["id"])
        st.rerun()


def render_annual_options(st, upload, candidate, source_id, clear_validation):
    years = sorted(candidate.frame["Fiscal year"].tolist())
    unit_options = [SOURCE_UNITS, *SCALES]
    saved = upload.setdefault("annual_options", {})
    default_units, default_cutoff = saved.get(candidate.sheet, (candidate.units, candidate.last_actual))
    details = st.expander("Annual source details")
    with details:
        units = st.selectbox("Monetary units", unit_options, index=unit_options.index(default_units),
                             key=f"{source_id}_units")
        cutoff = st.selectbox("Last actual fiscal year", [None, *years],
                              index=[None, *years].index(default_cutoff),
                              format_func=lambda year: "Unmarked in workbook" if year is None else str(year),
                              key=f"{source_id}_cutoff")
        if candidate.excluded:
            st.warning("Fiscal years with missing or invalid amounts: " + ", ".join(map(str, candidate.excluded)))
    saved[candidate.sheet] = (units, cutoff)
    dataset_id = f"{source_id}:{units}:{cutoff}"
    state = st.session_state
    if (state.get("dataset_id"), state.get("file_name")) != (dataset_id, upload["name"]):
        try:
            frame = normalize_annual(candidate, units, cutoff)
            prepared = annual_state(frame, upload["name"], candidate.sheet, dataset_id)
        except ValueError as error:
            st.warning(str(error))
            return False
        clear_validation()
        state.update(prepared)
    state["annual_workbook"] = {**upload, "selected": candidate.sheet}
    st.success("Ready to use")
    details.download_button("Download prepared annual data", state["annual_data"].to_csv(index=False),
                            file_name="prepared_annual_data.csv", mime="text/csv")
    return True


def render_table_options(st, upload, candidate, source_id, clear_validation, new):
    if candidate is not None:
        frame = candidate.frame
    elif "frame" in upload:
        frame = upload["frame"]
    elif new:
        return False
    else:
        with pd.ExcelFile(BytesIO(upload["bytes"]), engine="openpyxl") as workbook:
            frame = workbook.parse(upload["selected"]).dropna(how="all")
            frame.attrs["excel_rows"] = tuple(int(index) + 2 for index in frame.index)
            frame.attrs["excel_epoch"] = workbook.book.epoch
    frame = frame.rename(columns=lambda name: str(name).strip())
    detected = detect_columns(frame)
    saved = upload.setdefault("column_options", {})
    defaults = saved.get(upload["selected"], detected)
    with st.expander("Column assignments", expanded=not {"date", "revenue", "cogs"} <= detected.keys()):
        options = [None, *frame.columns.unique()]
        mapping = {}
        for field in COLUMN_ALIASES:
            default = defaults.get(field)
            selected = st.selectbox(field.replace("_", " ").title(), options, index=options.index(default),
                                    format_func=lambda name: "Choose column" if name is None else name,
                                    key=f"{source_id}_{field}")
            if selected is not None:
                mapping[field] = selected
    saved[upload["selected"]] = mapping
    if not new:
        with st.expander("Source preview"):
            preview = frame.head(100)
            preview.attrs.clear()
            st.dataframe(preview, width="stretch")
    try:
        result = validate_financial_data(frame, mapping=mapping, source_rows=frame.attrs.get("excel_rows"),
                                         excel_epoch=frame.attrs.get("excel_epoch"))
    except ValueError as error:
        st.warning(str(error))
        return False
    if not result["valid"]:
        if not (new and "sheets" in upload):
            st.warning("Some analytics need a date, revenue, and cost column with usable values.")
            active = st.session_state.get("file_name")
            if "validated_data" in st.session_state and active:
                st.caption(f"Dashboards are still using {active}.")
            with st.expander("Import details"):
                for error in result["errors"]:
                    st.write(error)
        return False
    state = st.session_state
    previous = state.get("validation_result", {})
    if (state.get("dataset_id"), state.get("file_name"), previous.get("mapping")) != (source_id, upload["name"], mapping):
        clear_validation()
        state.update(dataset_id=source_id, file_name=upload["name"], sheet_name=upload["selected"],
                     financial_data=frame, validated_data=result["data"], validation_result=result,
                     scenario_demo_source=False)
        if "sheets" not in upload:
            state.pop("chat_workbook", None)
    st.success("Ready to use")
    if result["warnings"]:
        with st.expander("Import notes"):
            for warning in result["warnings"]:
                st.write(warning)
    st.download_button("Download prepared data", result["data"].to_csv(index=False),
                       file_name="prepared_financial_data.csv", mime="text/csv")
    return True
