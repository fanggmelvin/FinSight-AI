
import json
import pandas as pd

from evidence_engine import build_driver_evidence
from ai_engine import analyze_question


df = pd.DataFrame({

    "date": pd.to_datetime([
        "2014-10-01",
        "2014-10-01",
        "2014-11-01",
        "2014-11-01"
    ]),

    "revenue": [
        1000.0,
        2000.0,
        1500.0,
        500.0
    ],

    "cogs": [
        700.0,
        1400.0,
        1000.0,
        350.0
    ],

    "product": [
        "Paseo",
        "Velo",
        "Paseo",
        "Velo"
    ],

    "country": [
        "USA",
        "Canada",
        "USA",
        "Canada"
    ],

    "segment": [
        "Government",
        "Enterprise",
        "Government",
        "Enterprise"
    ],

    "source_row": [2, 3, 4, 5]

})


registry = build_driver_evidence(
    df,
    dimension="product",
    current_month="2014-11",
    previous_month="2014-10",
    source_name="Synthetic Test Dataset",
    sheet_name="Financial Records"
)


question = (
    "Why did revenue decline in November 2014? "
    "Identify the major product contributors "
    "and recommend management actions."
)


print("=" * 60)
print("FINSIGHT AI - FIRST INTELLIGENCE TEST")
print("=" * 60)

print("\nQUESTION:")
print(question)

result = analyze_question(
    question,
    registry
)

print("\nAI FINANCIAL ANALYSIS:")
print(result["answer"])

print("\nCITATION VERIFICATION:")

print(json.dumps(
    result["verification"],
    indent=2
))

print("\nMODEL:")
print(result["model"])

print("\nTOKEN USAGE:")
print(result["total_tokens"])

print("\nSUPPORTING EVIDENCE:")

for evidence in result["cited_evidence"]:

    print(
        evidence["evidence_id"],
        "-",
        evidence["title"]
    )

print("\nTEST COMPLETED.")
