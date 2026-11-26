"""Optional qualitative synthesis over a bounded set of cited worksheet excerpts."""
import heapq
from dataclasses import replace
from io import BytesIO
import re

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from finsight.grounded_chat import interpret_evidence

def collect_evidence(source, sheet, question, local):
    terms = set(re.findall(r"[\w]+", question.casefold())) - {
        "what", "were", "was", "how", "does", "the", "for", "and", "with", "from", "this", "that",
    }
    wb = load_workbook(BytesIO(source["bytes"]), read_only=True, data_only=True)
    records = {"E0": local.text[:2200]}
    try:
        sheets = [sheet] + [s for s in wb.sheetnames if s != sheet and s.casefold().replace("_"," ") in question.casefold().replace("_"," ")]
        for s in sheets[:3]:
            ws = wb[s]
            def rows():
                for row_num, row in enumerate(ws.values, 1):
                    present = [(get_column_letter(col)+str(row_num),str(value)[:80]) for col,value in enumerate(row,1) if value is not None]
                    if not present:
                        continue
                    words = set(re.findall(r"[\w]+"," ".join(v for _,v in present).casefold()))
                    relevance = len(terms & words)
                    # Retain early labels and headers when lexical matches are sparse.
                    yield (relevance, -row_num, s + ": " + ", ".join(f"{addr}={val}" for addr,val in present[:15])[:700])
            for _, _, row in heapq.nlargest(8,rows()):
                records[f"E{len(records)}"] = row
    finally:
        wb.close()
    return records


def interpret(source, sheet, question, history, local):
    evidence = collect_evidence(source, sheet, question, local)
    interpretation = interpret_evidence(
        question, evidence, [q for q, _ in history], enabled=True,
        guidance="If E0 already answers a cell lookup, only add context if the excerpts support it. Keep workbook totals and projections as supplied in E0.",
    )
    if interpretation.text:
        cited = dict.fromkeys(re.findall(r"\[(E\d+)\]", interpretation.text))
        excerpts = [f"[{ref}] {evidence[ref]}" for ref in cited if ref != "E0"]
        text = interpretation.text.replace(" [E0]", "")
        interpretation = replace(interpretation, text="\n\n".join([text, *excerpts]))
    return replace(local, interpretation=interpretation)
