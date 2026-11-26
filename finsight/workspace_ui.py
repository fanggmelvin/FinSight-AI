"""Presentation helpers for workspace navigation and neutral scenario deltas."""
from html import escape

from finsight.scenario_presentation import format_value

NAV_GROUPS = (
    ('FINANCIAL ANALYTICS', ('Overview', 'Financial Analysis', 'Performance Drivers', 'Anomaly Detection')),
    ('DECISION INTELLIGENCE', ('AI Copilot', 'Scenario Modeling', 'Financial Reports')),
    ('DATA MANAGEMENT', ('Data Upload',)),
)
SIM_DEFAULTS = {'sim_rev': 0, 'sim_cost': 0, 'sim_target': 20, 'sim_behavior': 'Independent'}


def visible_delta(value, margin=False):
    return format_value(value, margin, True) if value is not None and round(value, 2) != 0 else None


def evidence_rows(values, category=None):
    from types import SimpleNamespace
    from finsight.deterministic_report import build_facts
    facts = build_facts(SimpleNamespace(records=[{'evidence_id': 'E', 'category': category, 'values': values}]))
    return [{'Field': evidence_label(key), 'Value': facts.get('E.' + key, 'N/A' if value is None else str(value))} for key, value in values.items()]


def report_kpi_lines(metrics):
    rows = []
    for key, value in metrics.items():
        if value is None:
            shown = 'N/A'
        elif key == 'record_count':
            shown = f'{value:,}'
        elif key in ('gross_margin', 'budget_variance_pct'):
            shown = f'{value:.2%}'
        else:
            shown = f'{value:,.2f}'
        rows.append(f'- {evidence_label(key)}: {shown}')
    return '\n'.join(rows)


def evidence_label(field):
    return ' '.join(word.upper() if word.lower() == 'cogs' else word.capitalize() for word in field.split('_'))


def registry_display(field, formatted):
    if field == 'records' and formatted.endswith('.00'):
        return formatted[:-3]
    return formatted


def scenario_delta_color(metric, delta):
    if visible_delta(delta) is None:
        return 'off'
    return 'inverse' if metric == 'COGS' else 'normal'


def dataset_summary(state):
    validated = state.get("validated_data")
    raw = state.get("financial_data")
    data = validated if validated is not None else raw
    if data is None and (workbook := state.get("chat_workbook")):
        return {"name": workbook["name"], "validated": False, "records": len(workbook["sheets"])}
    return {"name": str(state.get("file_name") or "Financial dataset") if data is not None else "No dataset loaded",
            "validated": validated is not None,
            "records": len(data) if data is not None else None}


def dataset_card_markup(summary, *, annual=False, workbook_only=False):
    count = summary["records"]
    status = ""
    if count is not None:
        label = "Ready" if summary["validated"] else "Workbook chat" if workbook_only else "Column details needed"
        unit = "fiscal year" if annual else "worksheet" if workbook_only else "record"
        units = unit if count == 1 else unit + "s"
        style = " is-validated" if summary["validated"] else ""
        status = f'<div class="dataset-card-status{style}">{label} · {count:,} {units}</div>'
    return (
        '<div class="dataset-card-details">'
        '<div class="dataset-card-label">Active dataset</div>'
        f'<div class="dataset-card-name">{escape(summary["name"])}</div>'
        f"{status}</div>"
    )


def compact_sidebar_css():
    return '''
    [data-testid="stSidebar"], [data-testid="stSidebar"] [data-testid="stSidebarContent"] {background: #122C43;}
    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {padding-top: 0.5rem !important; padding-bottom: 1rem;}
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {gap: .65rem !important;}
    [data-testid="stSidebar"] [data-testid="stElementContainer"] {flex-shrink: 0; height: auto !important; min-height: min-content;}
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {line-height: 1.5;}
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {min-height: 1.5rem; padding: .2rem 0;}
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {margin: 0; font-size: .8rem; line-height: 1.5;}
    [data-testid="stSidebar"] .st-key-active_dataset_manager {
      box-sizing: border-box; min-width: 0; padding: .75rem; border-radius: 12px;
      background: #19354C; border: 1px solid #416079;
    }
    [data-testid="stSidebar"] .dataset-card-label {color: #BBD0E3; font-size: .75rem; line-height: 1.3;}
    [data-testid="stSidebar"] .dataset-card-name {
      color: #F8FAFC; font-size: .95rem; font-weight: 650; line-height: 1.4;
      margin-top: .25rem; overflow-wrap: anywhere;
    }
    [data-testid="stSidebar"] .dataset-card-status {
      color: #F0D8A6; font-size: .8rem; line-height: 1.4; margin-top: .3rem;
    }
    [data-testid="stSidebar"] .dataset-card-status.is-validated {color: #A6E4CC;}
    [data-testid="stSidebar"] h1 {font-size: 1.5rem; line-height: 1.35; padding: .2rem 0; margin: 0;}
    [data-testid="stSidebar"] hr {margin: .5rem 0;}
    [data-testid="stSidebar"] [class*="st-key-nav_"] button {min-height: 2.65rem; padding: .45rem .65rem;}
    [data-testid="stSidebar"] [class*="st-key-nav_"] button[kind="secondary"] {border-color: transparent !important;}
    [data-testid="stSidebar"] [class*="st-key-nav_"] button:focus-visible {outline: 2px solid #93C5FD;}
    [data-testid="stSidebar"] .st-key-sidebar_brand {padding-bottom: .4rem;}
    [data-testid="stSidebar"] [class*="st-key-sidebar_section_label_"] {padding: .45rem 0 .25rem;}
    [data-testid="stSidebar"] [data-testid="stSidebarHeader"] {padding-top: .25rem !important; padding-bottom: .25rem !important; min-height: 2.5rem !important; height: auto !important;}
    [data-testid="stSidebar"] [data-testid="stSidebarContent"] > div {padding-top: 0 !important;}
    [data-testid="stSidebar"] .st-key-nav_upload_dataset button[kind="primary"] {background: #176B70 !important; border: 1px solid #68B9B7 !important; box-shadow: none !important;}
    [data-testid="stSidebar"] .st-key-nav_upload_dataset button[kind="primary"]:hover {background: #217D82 !important;}
    [data-testid="stSidebar"] [class*="st-key-sidebar_section_label_"] {padding-bottom: .45rem;}
    [data-testid="stSidebar"] [data-testid="stExpander"] {background: #122C43 !important; border: 1px solid #38506A !important; box-shadow: none !important; color: #F1F5F9 !important;}
    [data-testid="stSidebar"] [data-testid="stExpander"] summary,
    [data-testid="stSidebar"] [data-testid="stExpander"] p,
    [data-testid="stSidebar"] [data-testid="stExpander"] label,
    [data-testid="stSidebar"] [data-testid="stExpander"] svg {color: #F1F5F9 !important;}
    [data-testid="stSidebar"] [data-testid="stExpander"] summary {min-height: 2.65rem;}
    [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stVerticalBlock"] {gap: .5rem !important;}
    [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stCaptionContainer"] {min-height: 1.5rem !important; height: auto !important; padding: .15rem 0 calc(.15rem + 10px) !important;}
    [data-testid="stSidebar"] [data-testid="stExpanderDetails"] {padding: .65rem .75rem !important; height: auto !important;}
    @media (max-height: 760px) {
      [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {gap: .4rem !important;}
      [data-testid="stSidebar"] [class*="st-key-nav_"] button {min-height: 2.35rem;}
    }
    '''
