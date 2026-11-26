"""Local, cell-grounded workbook questions. Excel calculates formula results."""
from dataclasses import dataclass, field
from datetime import date
from html import escape
from io import BytesIO
import re
from statistics import mean

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter, range_boundaries
from finsight.ai_config import dataset_ai_available
from finsight.grounded_chat import Interpretation


@dataclass
class LookupDetails:
    source_value: str
    period_note: str
    label_cell: str
    period_cell: str
    comparison_year: int | None = None
    comparison_question: str = ""


@dataclass
class Reply:
    text: str
    sheet: str
    reference: str = ""
    label: str = ""
    filters: dict = field(default_factory=dict)
    sources: tuple[tuple[str, str], ...] = ()
    lookup: LookupDetails | None = None
    interpretation: Interpretation | None = None
    outlook: bool = False


CELL = r"\$?[A-Z]{1,3}\$?[1-9]\d{0,6}"
CELL_REFERENCE = re.compile(r"(?<![\w$])(" + CELL + r"(?:\s*:\s*" + CELL + r")?)(?!\w)", re.I)
PERIOD_TOKEN = re.compile(r"FY(?:19|20)\d{2}|Q[1-4]", re.I)
FOLLOWUP = re.compile(r"\b(?:what about|how about|that|those|them|same|instead|and in)\b", re.I)
OPERATIONS = (
    (r"\b(sum|total|add)\b", "Sum", sum),
    (r"\b(average|mean)\b", "Average", mean),
    (r"\b(min|minimum|lowest|smallest)\b", "Minimum", min),
    (r"\b(max|maximum|highest|largest)\b", "Maximum", max),
    (r"\bcount\b|how many", "Numeric count", len),
)


def cell_references(question):
    explicit = re.search(r"\b(?:cell|formula|range|read)\b", question, re.I)
    direct_quarter_cell = re.fullmatch(r"\s*(?:(?:sum|average|count|min|max|show)\s+)?Q[1-4][?.!]?\s*", question, re.I)
    return [
        match.group() for match in CELL_REFERENCE.finditer(question)
        if explicit or direct_quarter_cell or question[:match.start()].rstrip().endswith("!")
        or not PERIOD_TOKEN.fullmatch(match.group())
    ]


def mentioned_sheets(names, question):
    """Require a sheet qualifier when a name could also be a row or column label."""
    matches = []
    for name in sorted(names, key=len, reverse=True):
        bare = re.escape(name).replace("_", r"(?:_|\s+)")
        quoted = re.escape(name.replace("'", "''"))
        identifier = rf"(?:'{quoted}'|\"{bare}\"|{bare})"
        qualifier = r"\b(?:sheet|worksheet|tab|on|in|from)\s+"
        pattern = rf"(?<!\w)(?:{identifier}\s*(?=!)|{qualifier}{identifier}(?!\w))"
        match = re.search(pattern, question, re.I)
        if match and not any(match.start() < end and start < match.end() for _, start, end in matches):
            matches.append((name, match.start(), match.end()))
    return matches


def answer(workbook_bytes, question, selected, prior=None):
    q = question.strip()
    wb = load_workbook(BytesIO(workbook_bytes), read_only=True, data_only=True)
    try:
        from finsight.period_comparison import compare_periods, monthly_reply
        if not cell_references(q):
            comparison = compare_periods(wb, q, selected, prior)
            if comparison:
                return comparison
        if re.search(r"\b(sheets|worksheets|tabs)\b", q, re.I) and not cell_references(q):
            return Reply("Worksheets: " + ", ".join(wb.sheetnames), selected)
        matches = mentioned_sheets(wb.sheetnames, q)
        if len(matches) > 1:
            return Reply("This lookup covers one worksheet at a time. Choose " + " or ".join(name for name, _, _ in matches) + ".", selected)
        if not matches and re.search(r"!\s*" + CELL + r"(?!\w)", q, re.I):
            return Reply("I couldn't find that worksheet. Available worksheets: " + ", ".join(wb.sheetnames), selected)
        sheet = prior.sheet if prior and FOLLOWUP.search(q) else selected
        prompt = q
        if matches:
            sheet, start, end = matches[0]
            prompt = q[:start] + " " + q[end:]
        ws = wb[sheet]
        refs = cell_references(prompt)
        operation = next(((label, fn) for pattern, label, fn in OPERATIONS if re.search(pattern, prompt, re.I)), None)
        if not refs and operation and prior and prior.sheet == sheet and re.search(r"\b(that|those|them|same|it|instead|range)\b", prompt, re.I):
            refs = [prior.reference] if prior.reference else []
        if len(refs) > 1:
            return Reply("Give me one rectangular range, such as B2:D8, so I can identify the cells to use.", sheet)
        if refs:
            ref = re.sub(r"[\s$]", "", refs[0]).upper()
            x1, y1, x2, y2 = range_boundaries(ref)
            if x2 > 16384 or y2 > 1048576 or x1 > x2 or y1 > y2:
                return Reply("That address is outside Excel's worksheet bounds or has its endpoints reversed.", sheet)
            if (x2-x1+1)*(y2-y1+1) > 100000:
                return Reply("Select a range of up to 100,000 cells per question.", sheet)
            formulas = bool(re.search(r"\bformula\b", prompt, re.I))
            formula_book = load_workbook(BytesIO(workbook_bytes), read_only=True, data_only=False) if formulas else None
            try:
                rows = (formula_book[sheet] if formulas else ws).iter_rows(min_col=x1, max_col=x2, min_row=y1, max_row=y2, values_only=True)
                values = [(f"{get_column_letter(c)}{r}", value) for r, row in enumerate(rows, y1)
                          for c, value in enumerate(row, x1) if value is not None]
            finally:
                if formula_book:
                    formula_book.close()
            source = f"{sheet}!{ref}"
            if formulas and values and not any(isinstance(value,str) and value.startswith("=") for _,value in values):
                return Reply(f"{source} contains stored values. No formula text is available for those cells.", sheet, ref)
            if operation and not formulas:
                numbers = [v for _, v in values if type(v) in (float, int)]
                label, fn = operation
                if numbers or fn == len:
                    return Reply(f"{label} for {source}: {fn(numbers):,.12g} ({len(numbers):,} numeric cells).", sheet, ref)
                return Reply(f"{source} has no saved numeric values.", sheet, ref)
            detail = "\n".join(f"{cell}: {v}" for cell, v in values[:30])
            if len(values) > 30:
                detail += f"\nShowing 30 of {len(values):,} populated cells."
            return Reply(source + "\n" + (detail or "No saved value. If this is a formula, ask for its formula or recalculate and save in Excel."), sheet, ref)

        monthly = monthly_reply(ws, prompt, prior)
        if monthly:
            return monthly
        from finsight.table_chat import table_answer
        table = table_answer(ws, prompt, prior if prior and prior.sheet == sheet else None)
        if table:
            result, metric, *context = table
            return Reply(result, sheet, label=metric, filters=context[0] if context else {},
                         sources=context[1] if len(context) > 1 else ())
        quoted = re.search(r'["“](.+?)["”]', prompt)
        tokens = set(re.findall(r"[\w]+", prompt.casefold()))
        years = {int(y) for y in re.findall(r"\b(?:fy\s*)?((?:19|20)\d{2})\b", prompt, re.I)}
        followup = prior and prior.sheet == sheet and prior.label and re.search(r"\b(what about|how about|same|instead|and in)\b", prompt, re.I)
        aliases = {"revenue": ("net revenue", "sales", "net sales"), "cogs": ("cost of goods sold", "cost of sales")}
        labels = []
        year_columns = {}
        for row_number, row in enumerate(ws.values, 1):
            for col, value in enumerate(row, 1):
                year = value.year if isinstance(value, date) else value
                if year in years or (isinstance(year,str) and year.strip().isdigit() and int(year.strip()) in years):
                    year_columns.setdefault(int(year), []).append((row_number, col))
                elif isinstance(value, str):
                    words = set(re.findall(r"[\w]+", value.casefold()))
                    match = (quoted.group(1).casefold() == value.strip().casefold() if quoted
                             else bool(words) and words <= tokens and any(len(w)>2 for w in words))
                    if not quoted:
                        match |= any(key in tokens and value.strip().casefold() in alternatives for key, alternatives in aliases.items())
                        match |= bool(followup and value == prior.label)
                    if match and len(labels) < 12:
                        labels.append((row_number, col, value, row))
        if labels:
            lines = []
            sources = []
            for r, c, label, row in labels:
                positions = sorted({col for hits in year_columns.values() for yr, col in hits if yr < r}) if years else range(c+1, len(row)+1)
                cells = [f"{get_column_letter(col)}{r} = {row[col-1]}" for col in positions if col <= len(row) and row[col-1] is not None]
                sources.extend((sheet, cell.split(" = ", 1)[0]) for cell in cells[:12])
                if operation and c == 1:
                    nums = [row[col-1] for col in positions if col <= len(row) and type(row[col-1]) in (float,int)]
                    if nums:
                        title, fn = operation
                        cells.insert(0, f"{title} = {fn(nums):,.12g} across {len(nums)} numeric cells")
                lines.append(f"{get_column_letter(c)}{r} ({label}): " + (", ".join(cells[:12]) or "No matching values to the right or under the requested year."))
            return Reply(sheet + "\n" + "\n".join(lines), sheet,
                         label=labels[0][2] if len(labels)==1 else "", sources=tuple(sources))
        return Reply(f"{sheet} has {ws.max_row or 0:,} worksheet rows and {ws.max_column or 0:,} columns in its saved dimensions. Ask for a cell, a range calculation, a formula, or an exact row label in quotes.", sheet)
    finally:
        wb.close()


def preview_cells(workbook_bytes, sheet, ref):
    x1, y1, x2, y2 = range_boundaries(ref)
    last_col, last_row = min(x2, x1 + 7), min(y2, y1 + 11)
    workbook = load_workbook(BytesIO(workbook_bytes), read_only=True, data_only=True)
    try:
        rows = list(workbook[sheet].iter_rows(min_col=x1, max_col=last_col, min_row=y1,
                                             max_row=last_row, values_only=True))
    finally:
        workbook.close()
    displayed = f"{get_column_letter(x1)}{y1}:{get_column_letter(last_col)}{last_row}"
    return rows, [get_column_letter(col) for col in range(x1, last_col + 1)], y1, displayed, (last_col, last_row) != (x2, y2)


def preview_lookup(workbook_bytes, sheet, ref, lookup):
    workbook = load_workbook(BytesIO(workbook_bytes), read_only=True, data_only=True)
    try:
        worksheet = workbook[sheet]
        cells = (("Row label", lookup.label_cell), ("Fiscal year", lookup.period_cell), ("Source value", ref))
        return {f"{label} ({address})": worksheet[address].value for label, address in cells if address}
    finally:
        workbook.close()


def render_workbook_reply(st, source, reply, key):
    import pandas as pd

    with st.chat_message("assistant", avatar=":material/auto_awesome:"):
        lookup = getattr(reply, "lookup", None)
        if lookup:
            st.html(f'<p><strong>{escape(reply.text)}</strong></p>')
            st.text(lookup.source_value)
            if lookup.period_note:
                st.caption(lookup.period_note)
        elif getattr(reply, "outlook", False):
            st.markdown(reply.text)
        else:
            st.text(reply.text)
        interpretation = getattr(reply, "interpretation", None)
        if interpretation and interpretation.text:
            st.markdown("**AI interpretation**")
            st.text(interpretation.text)
        if interpretation and interpretation.status:
            st.caption(interpretation.status)
        sources = tuple(dict.fromkeys(getattr(reply, "sources", ())))
        if not sources and reply.reference:
            sources = ((reply.sheet, reply.reference),)
        if not sources:
            return
        panel = st.expander("View source cells" if lookup else "Source cells", key=f"source_cells_{key}", on_change="rerun")
        if panel.open:
            sheet, ref = sources[0]
            if len(sources) > 1:
                sheet, ref = panel.selectbox("Worksheet range", sources, format_func=lambda item: "!".join(item),
                                             key=f"source_range_{key}")
            if lookup:
                values = preview_lookup(source["bytes"], sheet, ref, lookup)
                panel.dataframe(pd.DataFrame([values]), hide_index=True, width="stretch")
                return
            rows, columns, first_row, displayed, cropped = preview_cells(source["bytes"], sheet, ref)
            value_label = "CSV values" if source["name"].lower().endswith(".csv") else "Saved Excel values"
            panel.caption(f"{sheet}!{ref} · {value_label}" + (f" · Preview {displayed}" if cropped else ""))
            if rows:
                cells = [[str(value) if value is not None else "" for value in row] for row in rows]
                panel.dataframe(pd.DataFrame(cells, columns=columns, index=range(first_row, first_row + len(rows))),
                                width="stretch")


def annual_comparison_button(prompt_slot, reply, key):
    lookup = getattr(reply, "lookup", None)
    if lookup and lookup.comparison_question:
        prompts = prompt_slot.container(horizontal=True, gap="small")
        if prompts.button(f"Compare with FY{lookup.comparison_year}", key=f"annual_compare_{key}"):
            prompt_slot.empty()
            return lookup.comparison_question
    return None


def enrich_annual_metadata(source, sheet, frame):
    """Recover source labels for sessions opened before the import stored them."""
    if {"Fiscal year row", "Revenue label", "COGS label"} <= set(frame.columns):
        return frame
    from finsight.annual_chat import sheet_coordinates

    workbook = load_workbook(BytesIO(source["bytes"]), read_only=True, data_only=True)
    try:
        worksheet = workbook[sheet]
        candidate = source.get("candidates", {}).get(sheet)
        if candidate is not None:
            frame["Fiscal year row"] = candidate.header_row
        for metric in ("Revenue", "COGS"):
            coordinates = sheet_coordinates(frame.iloc[0].get(f"{metric} cell"))
            if coordinates:
                frame[f"{metric} label"] = str(worksheet[f"A{coordinates[1]}"].value or metric).strip()
    finally:
        workbook.close()
    return frame


def render_chat(st, source, question, prompt_slot, *, annual=None, annual_sheet=None, monthly=None, dataset_key=""):
    from finsight.copilot_ui import copilot_context, copilot_toolbar
    context, settings, reset = copilot_toolbar(st, "workbook_new_chat")
    sheet = settings.selectbox("Worksheet", source["sheets"], index=source["sheets"].index(source["selected"]),
                         key=f"chat_sheet_{source['id']}_{source['selected']}")
    histories = st.session_state.setdefault("workbook_conversations", {})
    history = histories.setdefault((source["id"], sheet, dataset_key), [])
    prefix = f"{source['id']}_{sheet}_{dataset_key}"
    if reset:
        history.clear()
        st.rerun()
    can_use_ai = dataset_ai_available()
    live = can_use_ai and settings.checkbox(
        "Use AI interpretation for this workbook",
        help="Sends your question, recent questions, the local result and selected worksheet excerpts to OpenAI.",
        key="workbook_ai_" + source["id"],
    )
    if source["name"].lower().endswith((".xls", ".xlsb")):
        settings.caption("This format uses saved values. Formula text is available for modern Excel files.")
    elif source["name"].lower().endswith(".csv"):
        settings.caption("CSV row 1 contains the column headers.")
    processing = "OpenAI interpretation enabled" if live else "AI available in Settings" if can_use_ai else "Local analysis"
    context.html(copilot_context(source["name"], sheet, processing))
    for index, (earlier_question, reply) in enumerate(history):
        st.chat_message("user", avatar=":material/person:").text(earlier_question)
        render_workbook_reply(st, source, reply, f"{prefix}_{index}")
    if not question and history:
        question = annual_comparison_button(prompt_slot, history[-1][1], f"{prefix}_{len(history)}")
    if not history and not question:
        from finsight.period_comparison import workbook_suggestions
        suggestions = workbook_suggestions(source["bytes"], sheet, annual if sheet == annual_sheet else None)
        if suggestions:
            prompts = prompt_slot.container(horizontal=True, gap="small")
            for index, prompt in enumerate(suggestions):
                if prompts.button(prompt, key=f"workbook_suggestion_{index}"):
                    question = prompt
            if question:
                prompt_slot.empty()
    if question:
        from finsight.financial_outlook import annual_outlook, is_outlook, monthly_outlook
        from finsight.grounded_chat import interpret_evidence
        prior = history[-1][1] if history else None
        reply = None
        follows_other_sheet = prior and prior.sheet != sheet and FOLLOWUP.search(question)
        explicit_other_sheet = any(name != sheet for name, _, _ in mentioned_sheets(source["sheets"], question))
        use_annual = annual is not None and sheet == annual_sheet and not follows_other_sheet and not explicit_other_sheet
        if is_outlook(question, workbook=True):
            try:
                if use_annual:
                    text = annual_outlook(annual, question)
                elif monthly is not None and sheet == source["selected"] and not explicit_other_sheet:
                    text = monthly_outlook(monthly, question)
                else:
                    raise ValueError("A new financial outlook requires an annual statement with actuals or a mapped date, revenue and cost table for this worksheet.")
            except ValueError as error:
                text = str(error)
            interpretation = interpret_evidence(question, {"E0": text}, [q for q, _ in history[-3:]], enabled=live)
            reply = Reply(text, sheet, interpretation=interpretation, outlook=True)
        elif use_annual:
            from finsight.annual_chat import annual_reply
            reply = annual_reply(enrich_annual_metadata(source, sheet, annual), sheet, question, prior)
        if reply is None:
            reply = answer(source["bytes"], question, sheet, prior)
        if live and not reply.outlook:
            from finsight.workbook_interpretation import interpret
            reply = interpret(source, reply.sheet, question, history, reply)
        history.append((question, reply))
        st.chat_message("user", avatar=":material/person:").text(question)
        render_workbook_reply(st, source, reply, f"{prefix}_{len(history)-1}")
        annual_comparison_button(prompt_slot, reply, f"{prefix}_{len(history)}")
