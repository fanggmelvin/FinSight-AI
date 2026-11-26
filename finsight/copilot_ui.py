"""Presentation-only helpers; preserve original financial text and evidence."""
import re
from datetime import datetime
from html import escape


def compact_period(period):
    months = period.split(', ')
    if not all(re.fullmatch(r'\d{4}-(?:0[1-9]|1[0-2])', m) for m in months):
        return period
    labels = [datetime.strptime(m, '%Y-%m').strftime('%b %Y') for m in months]
    if len(labels) == 1:
        return labels[0] + ' · 1 month'
    return f'{labels[0]} – {labels[-1]} · {len(labels)} selected months'


def ranking_lead(text):
    lines = text.splitlines()
    if not lines or not re.fullmatch(r'\*\*.+ ranking by .+ \((?:ascending|descending)\)\*\*', lines[0]):
        return None
    return next((line[2:] for line in lines[1:] if line.startswith('- **')), None)


def action_cards(text):
    cards = []
    for line in text.split('\n\n'):
        match = re.fullmatch(r'(?:- )?\*\*(.+?):\*\* (.+?) \*\*Proposed action:\*\* (.+)', line, re.S)
        if not match:
            return []
        cards.append(match.groups())
    return cards


def ranking_card(text):
    lead = ranking_lead(text)
    if not lead:
        return None
    header = re.fullmatch(r'\*\*(.+) ranking by (.+) \((ascending|descending)\)\*\*', text.splitlines()[0])
    row = re.fullmatch(r'\*\*(.+?):\*\* (.+) (\[E\d+\])', lead)
    if not header or not row:
        return None
    dimension, metric, direction = header.groups()
    name, details, evidence = row.groups()
    fields = details.split('; ')
    prefix = metric + ' '
    if not fields[0].startswith(prefix):
        return None
    value = fields[0][len(prefix):]
    if not re.fullmatch(r'-?[\d,]+(?:\.\d+)?%?', value):
        return None
    return (f"{'Lowest' if direction == 'ascending' else 'Highest'} {dimension.lower()} {metric}", name, value, '; '.join(fields[1:]), evidence)


def plan_status(diagnostic, plan_diagnostic, offline):
    if offline and plan_diagnostic == 'AI count incomplete; local plan used.':
        return diagnostic
    return '; '.join(x for x in (diagnostic, plan_diagnostic) if x) or None


def suggestion_label(prompt):
    labels = {
        'Summarize financial performance.': 'Financial performance',
        'Which products should we prioritize to improve profitability?': 'Growth opportunities',
        'If you were our CFO, what are the three most important actions you would recommend?': 'CFO recommendations',
        'What are our biggest financial risks?': 'Financial risks',
        'Identify profitability risks supported by the evidence.': 'Profitability risks',
        'Which business categories contribute most to revenue?': 'Revenue contributors',
        'Which contributors offset the decline?': 'Offsets to decline',
        'What should management investigate next?': 'Management priorities',
    }
    return labels.get(prompt, 'Explain revenue change' if prompt.startswith('Explain the revenue change from ') else prompt)


def copilot_toolbar(st, reset_key):
    with st.container(key="copilot_toolbar"):
        source, actions = st.columns([3, 2], vertical_alignment="center")
        context = source.empty()
        controls = actions.container(horizontal=True, horizontal_alignment="right", gap="small")
        settings = controls.popover("Settings", icon=":material/settings:", width="content")
        reset = controls.button("New chat", icon=":material/add:", key=reset_key)
    return context, settings, reset


def copilot_context(source, detail, processing):
    return (
        '<div class="copilot-source">'
        f'<div class="copilot-source-name">{escape(source)}</div>'
        f'<div class="copilot-source-detail">{escape(detail)} · {escape(processing)}</div>'
        '</div>'
    )


def copilot_css():
    return """
    [data-testid="stAppViewContainer"]:has(.st-key-fs_workspace_ai_copilot) [data-testid="stBottomBlockContainer"] {
      max-width: 1440px;
    }
    [data-testid="stAppViewContainer"]:has(.st-key-fs_workspace_ai_copilot) [data-testid="stBottom"] > div {
      background: rgba(234, 241, 249, .36); backdrop-filter: blur(12px);
    }
    .st-key-fs_workspace_ai_copilot {
      container-type: inline-size;
    }
    .st-key-copilot_toolbar {
      padding: .85rem clamp(.85rem, 2.2vw, 1.35rem);
      box-sizing: border-box; border: 1px solid transparent; border-radius: 18px;
      background:
        radial-gradient(ellipse at 85% 0%, #274a70, transparent 68%) padding-box,
        linear-gradient(115deg, #101d35, #142e4b 60%, #173742) padding-box,
        linear-gradient(100deg, #729df1, #9abcf8 40%, #80dac7) border-box;
      box-shadow: 0 12px 28px #142e4b32, inset 0 1px #d1edff29;
    }
    .copilot-source {position: relative; min-width: 0; padding-inline-start: 1rem; overflow-wrap: anywhere;}
    .copilot-source::before {
      content: ""; position: absolute; inset-inline-start: 0; top: .47rem;
      width: .45rem; height: .45rem; border-radius: 50%;
      background: #9ff0d9; box-shadow: 0 0 12px #66e0d5ad;
    }
    .copilot-source-name {color: #f4f9ff; font-size: 1.03rem; font-weight: 650; line-height: 1.4;}
    .copilot-source-detail {color: #c2d8ee; font-size: .81rem; margin-top: .16rem; line-height: 1.45;}
    .st-key-copilot_toolbar [data-testid="stPopoverButton"],
    .st-key-copilot_toolbar :is(.st-key-copilot_new_chat, .st-key-workbook_new_chat) button {
      background: #d1e6ff14; border-color: #9cbbeb72; color: #f4f9ff; border-radius: 10px;
    }
    .st-key-copilot_toolbar :is(.st-key-copilot_new_chat, .st-key-workbook_new_chat) button {
      background: #8ee3d3; border-color: #bbf6e7; color: #102e3a;
    }
    .st-key-copilot_toolbar [data-testid="stPopoverButton"]:hover,
    .st-key-copilot_toolbar :is(.st-key-copilot_new_chat, .st-key-workbook_new_chat) button:hover {
      border-color: #c5faef; box-shadow: 0 0 10px #9ef5e44d;
    }
    .st-key-copilot_toolbar button:focus-visible {outline: 2px solid #c5faef; outline-offset: 2px;}
    [data-testid="stAppViewContainer"]:has(.st-key-fs_workspace_ai_copilot) [data-testid="stChatInput"] {
      border: 1px solid #8cabdc; border-radius: 16px;
      background: linear-gradient(105deg, #f9fcff, #edf9f9);
      box-shadow: 0 5px 18px #32629a24;
    }
    [data-testid="stAppViewContainer"]:has(.st-key-fs_workspace_ai_copilot) [data-testid="stChatInput"]:focus-within {
      border-color: #477abb; box-shadow: 0 0 0 3px #87b7ef66;
    }
    [data-testid="stAppViewContainer"]:has(.st-key-fs_workspace_ai_copilot) [data-testid="stChatInput"] [data-baseweb="textarea"],
    [data-testid="stAppViewContainer"]:has(.st-key-fs_workspace_ai_copilot) [data-testid="stChatInput"] textarea {
      background: transparent;
    }
    [data-testid="stAppViewContainer"]:has(.st-key-fs_workspace_ai_copilot) [data-testid="stBottom"] .stButton button {
      background: #f6fbffdb; border-color: #a5c3e4; border-radius: 999px;
    }
    .st-key-fs_workspace_ai_copilot [data-testid="stChatMessage"] {
      box-sizing: border-box; min-width: 0; padding: .75rem;
    }
    .st-key-fs_workspace_ai_copilot [data-testid="stChatMessage"]:has(> [aria-label="Chat message from user"]) {
      width: fit-content; max-width: 74%; margin-inline-start: auto;
      flex-direction: row-reverse; background: linear-gradient(120deg, #eef3ff, #e7f6f9); border-color: #a5bfdf;
    }
    .st-key-fs_workspace_ai_copilot [data-testid="stChatMessage"]:has(> [aria-label="Chat message from assistant"]) {
      width: 90%; margin-inline-end: auto; background: #f8fcffed;
      border-color: #c1d6eb; border-inline-start: 3px solid #70bbae;
    }
    .st-key-fs_workspace_ai_copilot [data-testid="stChatMessageAvatarCustom"] {
      background: #deebfc; border-color: #b6cdea;
    }
    .st-key-fs_workspace_ai_copilot [data-testid="stChatMessage"]:has(> [aria-label="Chat message from assistant"])
    [data-testid="stChatMessageAvatarCustom"] {
      background: #d4f3eb; border-color: #b0e3d8;
    }
    .st-key-fs_workspace_ai_copilot [data-testid="stChatMessageContent"] {
      min-width: 0; overflow-wrap: anywhere;
    }
    .st-key-fs_workspace_ai_copilot [data-testid="stChatMessageContent"] [data-testid="stText"],
    .st-key-fs_workspace_ai_copilot [data-testid="stChatMessageContent"] pre {
      white-space: pre-wrap; overflow-wrap: anywhere;
    }
    @media (max-width: 720px) {
      .st-key-fs_workspace_ai_copilot [data-testid="stChatMessage"]:has(> [aria-label="Chat message from user"]) {
        max-width: 90%;
      }
      .st-key-fs_workspace_ai_copilot [data-testid="stChatMessage"]:has(> [aria-label="Chat message from assistant"]) {
        width: 96%;
      }
    }
    @container (max-width: 600px) {
      .st-key-copilot_toolbar [data-testid="stHorizontalBlock"] {flex-wrap: wrap;}
      .st-key-copilot_toolbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        flex: 1 1 100% !important; min-width: 0;
      }
    }
    """


def financial_suggestions(frame):
    months = sorted(frame["date"].dt.to_period("M").dropna().astype(str).unique())
    suggestions = []
    dimension = next((name for name in ("product", "country", "segment")
                      if name in frame and frame[name].nunique() > 1), None)
    if len(months) >= 2 and dimension:
        suggestions.append(f"Explain the revenue change from {months[-2]} to {months[-1]} by {dimension}.")
    if "budget_revenue" in frame and len(frame) and frame["budget_revenue"].notna().all():
        suggestions.append("What was the revenue budget variance?")
    if not frame.empty:
        suggestions.append("Summarize financial performance.")
    return suggestions
