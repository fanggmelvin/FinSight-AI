import re

from finsight.copilot_ui import compact_period, ranking_lead, action_cards, ranking_card

import hashlib
from finsight.demo_dataset import load_demo_state

import pandas as pd
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError
import plotly.express as px
from finsight.ai_config import dataset_ai_available, live_ai_available, load_local_config

from finsight.finance_engine import (
    calculate_metrics,
    calculate_monthly_performance,
    calculate_breakdown,
    detect_anomalies,
    calculate_revenue_drivers
)


# ==========================================
# APPLICATION CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="FinSight AI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Resolve root-level Streamlit secrets before loading local defaults.
try:
    st.secrets.get("FINSIGHT_LIVE_AI")
except StreamlitSecretNotFoundError:
    pass
load_local_config()


# ==========================================
# HELPER FUNCTIONS
# ==========================================

from finsight.ui_theme import apply_theme
apply_theme(st.session_state.get("aurora_motion", True))

def show_numerical_verification(result, compact=False):
    st.subheader("Numerical claim checks")
    check = result.get("numerical_verification", {})
    if check.get("mode") == "deterministic":
        st.metric("Financial fields rendered from evidence", check.get("rendered_fields", 0))
        st.caption("Additional verification API tokens: 0. Values are rendered locally, not independently audited. AI commentary is not verified for factual entailment.")
        if check.get("controlled_actions"):
            st.caption("AI-generated synthesis accepted." if check.get("generated_synthesis") else "Local rule-based recommendations used.")
            if check.get("commentary_diagnostic"):
                st.info(check["commentary_diagnostic"])
            return
        if not check.get("commentary_accepted"):
            st.warning("AI commentary withheld: " + str(check.get("commentary_diagnostic") or "Output constraints not met"))
        elif check.get("commentary_diagnostic"):
            st.warning("Some commentary rejected: " + str(check["commentary_diagnostic"]))
        return
    if check.get("extraction_status") != "completed":
        st.warning("Numerical claim extraction incomplete or unavailable. Manual review required.")
    if check.get("errors"):
        with (st.container() if compact else st.expander("Extraction diagnostics", expanded=True)):
            st.json(check["errors"])
    st.caption(f"Extraction batches: {check.get('batches', 'N/A')} | Surface coverage warnings (separate from claim counts): {check.get('coverage_warnings', 'N/A')}")
    cols = st.columns(3)
    for col, status in zip(cols, ["passed", "failed", "unverified"]):
        col.metric(status.title(), check.get(status, 0))
    if check.get("failed") or check.get("unverified") or check.get("coverage_warnings"):
        st.warning("Some extracted claims failed or require review.")
    st.caption("AI proposes claim mappings; Python checks mapped values and rankings. Extraction may miss claims or map them incorrectly. Passing checks do not establish full report accuracy.")
    st.caption(f"Additional verification request tokens: {check.get('tokens')}")
    with (st.container() if compact else st.expander("Numerical verification details")):
        if check.get("coverage_details"):
            st.json(check["coverage_details"])
        for item in check.get("results", []):
            st.write(item["claim"].get("text", "Claim"), item["status"])
            st.json(item)


def show_action_cards(text):
    cards = action_cards(text)
    if not cards:
        st.markdown(text)
        return
    for index, (heading, observation, action) in enumerate(cards, 1):
        heading = heading.removesuffix(" (local)")
        with st.container():
            st.markdown(f"**{index}. {heading}**\n\n{observation}  \n**Proposed action:** {action}")


def show_executive_analysis(result, *, compact=False, source_view=None, supporting_only=False):
    if result.get('numerical_verification', {}).get('mode') != 'deterministic' or 'commentary' not in result:
        if not supporting_only: st.markdown(result['answer'])
        if source_view: source_view()
        return
    from finsight.deterministic_report import report_groups, build_facts, key_tables, deterministic_insights
    from types import SimpleNamespace
    records = [r for r in result.get('cited_evidence', []) if r]
    total = next((r for r in records if r['title'] == 'Total financial change'), None)
    executive = 'executive-reporting' in result.get('active_skills', [])
    local_primary = compact and not executive and not result.get('direct_answer') and not result.get('local_plan') and not result.get('numerical_verification', {}).get('generated_synthesis')
    if not supporting_only:
        if result.get('direct_answer'):
            if not compact: st.subheader('Direct financial answer')
            lead = ranking_lead(result['direct_answer']) if compact else None
            if lead:
                with st.container():
                    card = ranking_card(result['direct_answer'])
                    if card:
                        label, name, value, details, evidence = card
                        st.metric(label + ' · ' + name, value)
                        st.caption((details + ' · ' if details else '') + evidence)
                    else:
                        st.markdown(lead)
                with st.expander('View rankings and context'):
                    st.markdown(result['direct_answer'])
            else:
                st.markdown(result['direct_answer'])
        if result.get('local_plan'):
            st.markdown('**Recommended actions**' if compact else '**Recommended actions (local)**')
            (show_action_cards if compact else st.markdown)(result['commentary'])
        if result.get('numerical_verification', {}).get('generated_synthesis'):
            st.markdown('**AI interpretation**')
            (show_action_cards if compact else st.markdown)(result['commentary'].split('\n\n**Calculated supporting findings**', 1)[0])
            st.caption('AI interpretation and proposed actions; not independently verified for factual entailment.')
        if local_primary:

            st.markdown(result['commentary'])
        if source_view: source_view()
        if compact:
            if executive and not (result.get("direct_answer") or result.get("local_plan") or result.get("numerical_verification", {}).get("generated_synthesis")):
                st.markdown(result["commentary"])
            return
    st.subheader('Executive summary' if executive else 'Calculated financial evidence')
    st.caption('Monetary values are in source currency units. Contributions across dimensions must not be added.')
    if total:
        v = total['values']
        cols = st.columns(3)
        for col, label, field, change in zip(cols, ['Revenue', 'Gross profit', 'Gross margin'], ['current_revenue', 'current_gross_profit', 'current_gross_margin'], ['revenue_change', 'gross_profit_change', None]):
            value = v.get(field)
            delta = v.get(change) if change else None
            if field == 'current_gross_margin' and value is not None and v.get('previous_gross_margin') is not None:
                delta_text = f"{(value-v['previous_gross_margin'])*100:+.2f} pp"
            else:
                delta_text = f"{delta:+,.2f}" if delta is not None else None
            col.metric(label, format_percent(value) if 'margin' in field else (f'{value:,.2f}' if value is not None else 'N/A'), delta_text)
        st.caption(f"Source: [{total['evidence_id']}] | Change versus previous period")
    if not total:
        summary = {r['title']:r for r in records}
        specs = [('Total Revenue','revenue'),('Total Cost of Goods Sold','cogs'),('Gross Profit','gross_profit'),('Gross Margin','gross_margin')]
        if all(t in summary for t,f in specs):
            for col,(t,f) in zip(st.columns(4),specs):
                v=summary[t]['values'].get(f)
                col.metric(t, format_percent(v) if f=='gross_margin' else (f'{v:,.2f}' if v is not None else 'N/A'))
    if 'anomaly-detection' in result.get('active_skills', []):
        from finsight.skill_workflow import anomaly_rows
        st.subheader('Rule-based financial anomalies')
        flags = anomaly_rows(records)
        if flags:
            st.dataframe(pd.DataFrame(flags), hide_index=True, width='stretch')
        else:
            st.info('No rule-based anomalies detected in the selected evidence.')
        st.caption('High severity flags precede review flags. Flags are investigation leads, not established causes.')
    if executive:
        from finsight.skill_workflow import executive_risks
        st.subheader('Material financial risks and management action plan')
        risks = executive_risks(records)
        if risks:
            st.dataframe(pd.DataFrame(risks), hide_index=True, width='stretch')
        else:
            st.info('No highlights available under the current report rules.')
        st.caption('Priorities are illustrative review rules, not audited materiality thresholds. Segment exposure at or above 75% is flagged high. Lowest margin is a relative ranking, not proof of underperformance.')
        st.subheader('Calculated findings and management recommendations')
        st.markdown(result['commentary'].split('\n\n**Calculated supporting findings**\n\n', 1)[-1] or 'Commentary unavailable; review the calculated evidence.')
        st.caption('Financial findings are calculated locally. Supporting findings and fallback actions are rule-based. Actions are not established causes or guaranteed outcomes.')
        st.subheader('Supporting financial performance')
    from contextlib import nullcontext
    with (st.expander("Supporting analysis and financial breakdowns", expanded=False) if compact else nullcontext()):
        for group, data in key_tables(records).items():
            frame = pd.DataFrame(data)
            route = result.get('route',{})
            metric = route.get('metric') or ('revenue_change' if 'revenue_change' in frame else 'revenue')
            if group == 'Financial Performance':
                frame = frame.sort_values('Name')
            elif metric in frame:
                frame = frame.sort_values(metric, ascending=route.get('ascending', metric == 'gross_margin' or (metric == 'revenue_change' and route.get('direction') != 'growth')), na_position='last')
            for field in ('gross_margin','revenue_share'):
                if field in frame:
                    frame[field] = frame[field].map(lambda x: f'{x:.2%}' if pd.notna(x) else 'N/A')
            for field in ('revenue_change','gross_profit_change','previous_revenue','current_revenue','previous_gross_profit','current_gross_profit','revenue','gross_profit'):
                if field in frame:
                    frame[field] = frame[field].map(lambda x: f'{x:,.2f}' if pd.notna(x) else 'N/A')
            frame = frame.rename(columns=lambda c: c.replace('_',' ').title())
            st.markdown('**' + ('Monthly Financial Performance' if group == 'Financial Performance' else group + ' financial breakdown') + '**')
            st.dataframe(frame, hide_index=True, width='stretch')
        for group, rows in report_groups(records).items():
            if group not in ('Product', 'Country', 'Segment', 'Intersection'):
                continue
            data = [{'Contributor': r['title'].split(':',1)[1].strip() + ' [' + r['evidence_id'] + ']', 'Revenue change': r['values'].get('revenue_change')} for r in rows if r['values'].get('revenue_change') is not None]
            if data:
                frame = pd.DataFrame(data).sort_values('Revenue change')
                frame['Direction'] = frame['Revenue change'].map(lambda x: 'Increase' if x > 0 else 'Decrease' if x < 0 else 'Unchanged')
                fig = px.bar(frame, x='Revenue change', y='Contributor', color='Direction', orientation='h', title=group + ' revenue contributions', color_discrete_map={'Increase':'#16967A','Decrease':'#B91C1C','Unchanged':'#94A3B8'})
                fig.update_layout(height=max(300, 45*len(frame)+100), showlegend=False)
                st.plotly_chart(fig, width='stretch')
        findings = deterministic_insights(records, result.get("route", {}).get("direction"))
        if findings and not result.get("numerical_verification", {}).get("controlled_actions"):
            st.subheader('Calculated management insights')
            st.markdown(findings)
            st.caption('Rankings are calculated from available evidence; suggested reviews are not established causes.')
        if not executive and not local_primary:
            supporting = (result.get("supporting_findings") if result.get("local_plan")
                          else result["commentary"].split('\n\n**Calculated supporting findings**\n\n', 1)[-1])
        else:
            supporting = None
        if supporting:
            st.subheader('Calculated findings and management recommendations')
            st.markdown(supporting)
            st.caption('Financial findings are calculated locally. Supporting findings and fallback actions are rule-based. Actions are not established causes or guaranteed outcomes.')
    with st.expander('Complete calculated financial evidence'):
        facts = build_facts(SimpleNamespace(records=records))
        for group, rows in report_groups(records).items():
            st.markdown('**' + group + '**')
            from finsight.workspace_ui import evidence_label, registry_display
            table = [{'Evidence': r['evidence_id'], 'Title': r['title'], **{evidence_label(k.split('.',1)[1]): registry_display(k.split('.',1)[1], val) for k,val in facts.items() if k.startswith(r['evidence_id']+'.')}} for r in rows]
            st.dataframe(pd.DataFrame(table), hide_index=True, width='stretch')


def format_money(value):

    if pd.isna(value):
        return "N/A"

    sign = "-" if value < 0 else ""
    value = abs(value)

    if value >= 1_000_000_000:
        return f"{sign}${value / 1e9:,.2f}B"

    if value >= 1_000_000:
        return f"{sign}${value / 1e6:,.2f}M"

    if value >= 1_000:
        return f"{sign}${value / 1e3:,.2f}K"

    return f"{sign}${value:,.2f}"


def format_percent(value):

    if pd.isna(value):
        return "N/A"

    return f"{value:.2%}"


def clear_validation():

    for key in [
        "validation_result",
        "annual_data",
        "annual_workbook",
        "validated_data",
        "ai_scope",
        "ai_history",
        "executive_report",
        "validated_ai_cache",
    ]:
        st.session_state.pop(key, None)


def show_metrics(df):

    metrics = calculate_metrics(df)

    cols = st.columns(4)

    cols[0].metric(
        "Total Revenue",
        format_money(metrics["revenue"])
    )

    cols[1].metric(
        "Total COGS",
        format_money(metrics["cogs"])
    )

    cols[2].metric(
        "Gross Profit",
        format_money(metrics["gross_profit"])
    )

    cols[3].metric(
        "Gross Margin",
        format_percent(metrics["gross_margin"])
    )

    if "budget_variance" in metrics:

        cols = st.columns(3)

        cols[0].metric(
            "Budget Revenue",
            format_money(metrics["budget_revenue"])
        )

        cols[1].metric(
            "Budget Variance",
            format_money(metrics["budget_variance"])
        )

        cols[2].metric(
            "Budget Variance %",
            format_percent(metrics["budget_variance_pct"])
        )

    return metrics


def require_data(show_source=True):

    if "validated_data" not in st.session_state:

        st.warning(
            "Upload a financial dataset with dates, revenue, and costs to use this feature."
        )

        st.stop()

    if show_source:
        st.caption(
            f"Source: {st.session_state['file_name']} | "
            f"{st.session_state['sheet_name']}"
        )

    return st.session_state["validated_data"].copy()


def apply_filters(df, prefix, embedded=False, show_count=True):

    with (st.container() if embedded else st.expander("Analysis filters", expanded=False)):
        years = sorted(
            df["date"].dt.year.unique().tolist()
        )

        selected_year = st.selectbox(
            "Financial Year",
            ["All Years"] + years,
            key=f"{prefix}_year"
        )

        if selected_year != "All Years":

            df = df[
                df["date"].dt.year == selected_year
            ]

        cols = st.columns(3)

        for i, field in enumerate(
            ["segment", "country", "product"]
        ):

            if field in df.columns:

                options = sorted(
                    df[field].dropna().unique().tolist()
                )

                with cols[i]:

                    selected = st.multiselect(
                        field.title(),
                        options,
                        key=f"{prefix}_{field}"
                    )

                if selected:

                    df = df[df[field].isin(selected)]

    if df.empty:

        st.warning(
            "No records match the selected filters."
        )

        st.stop()

    if not embedded and show_count:
        st.caption(f"Analyzing {len(df):,} financial records.")

    return df.copy()


def style_chart(fig):

    fig.update_layout(
        template="plotly_white",
        font=dict(color="#334155", family="Arial"),
        colorway=["#426E9B", "#16967A", "#B45309", "#64748B"],
        hoverlabel=dict(bgcolor="white", font_color="#10243D"),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        margin=dict(l=20, r=20, t=48 if fig.layout.title.text else 15, b=20),
        height=330
    )

    fig.update_xaxes(gridcolor="#E5EAF0", automargin=True)
    fig.update_yaxes(gridcolor="#E5EAF0", automargin=True)
    labels = {"month": "Month", "revenue": "Revenue", "gross_profit": "Gross profit", "gross_margin": "Gross margin", "revenue_growth": "Revenue growth", "revenue_change": "Revenue change", "product": "Product", "country": "Country", "segment": "Segment", "direction": "Direction", "cogs": "Cost of goods sold"}
    for axis in (fig.layout.xaxis, fig.layout.yaxis):
        raw = axis.title.text
        if raw in labels:
            axis.title.text = labels[raw]
        if raw in ("revenue", "gross_profit", "revenue_change", "cogs"):
            axis.tickprefix = "$"
    if fig.layout.legend.title.text in labels:
        fig.layout.legend.title.text = labels[fig.layout.legend.title.text]
    return fig


def show_table(df, *, labels=None):

    config = {}

    money_columns = [
        "revenue",
        "cogs",
        "gross_profit",
        "current_revenue",
        "previous_revenue",
        "revenue_change",
        "absolute_change"
    ]

    percent_columns = [
        "gross_margin",
        "revenue_share",
        "revenue_growth"
    ]

    for column in money_columns:

        if column in df.columns:

            config[column] = (
                st.column_config.NumberColumn(
                    column.replace("_", " ").title(),
                    format="dollar"
                )
            )

    for column in percent_columns:

        if column in df.columns:

            config[column] = (
                st.column_config.NumberColumn(
                    column.replace("_", " ").title(),
                    format="percent"
                )
            )

    for column, label in (labels or {}).items():
        if column in df.columns:
            if column in config:
                config[column]["label"] = label
            else:
                config[column] = label

    st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        column_config=config
    )


# ==========================================
# SIDEBAR
# ==========================================

if not st.session_state.get("demo_initialized"):
    st.session_state["demo_initialized"] = True
    if "financial_data" not in st.session_state:
        try:
            st.session_state.update(load_demo_state())
            st.session_state["scenario_demo_source"] = True
        except Exception:
            st.warning("Sample data unavailable. Upload a financial file to continue.")

def select_workspace(name):
    st.session_state["workspace_page"] = name


def open_workbook_in_copilot(workbook_id):
    st.session_state["copilot_mode"] = "Workbook"
    st.session_state["copilot_workbook_id"] = workbook_id
    select_workspace("AI Copilot")


with st.sidebar:

    from finsight.workspace_ui import dataset_summary, dataset_card_markup, compact_sidebar_css
    st.markdown("<style>" + compact_sidebar_css() + "</style>", unsafe_allow_html=True)
    with st.container(key="sidebar_brand"):
        st.title("FinSight AI")
        st.caption("Evidence-Driven Financial Intelligence")
    summary = dataset_summary(st.session_state)
    with st.container(key="active_dataset_manager"):
        st.html(dataset_card_markup(summary, annual="annual_data" in st.session_state,
                                    workbook_only="validated_data" not in st.session_state and bool(st.session_state.get("chat_workbook"))))
        has_dataset = summary["records"] is not None
        st.button("Change dataset" if has_dataset else "Upload dataset",
                  icon=":material/upload_file:", key="nav_upload_dataset",
                  width="stretch", type="primary", on_click=select_workspace, args=("Data Upload",))
    st.divider()

    pages = {
        "Overview": ":material/dashboard:",
        "Data Upload": ":material/upload_file:",
        "Financial Analysis": ":material/monitoring:",
        "Performance Drivers": ":material/insights:",
        "Anomaly Detection": ":material/warning:",
        "AI Copilot": ":material/auto_awesome:",
        "Scenario Modeling": ":material/tune:",
        "Financial Reports": ":material/description:",
    }
    if st.session_state.get("workspace_page") not in pages:
        st.session_state["workspace_page"] = "Overview"
    from finsight.workspace_ui import NAV_GROUPS
    for group, names in NAV_GROUPS:
        if group == "DATA MANAGEMENT":
            continue  # Accessible through the global dataset manager.
        with st.container(key="sidebar_section_label_" + group.lower().replace(" ", "_")):
            st.caption(group)
        for name in names:
            icon = pages[name]
            st.button(name, icon=icon, key=f"nav_{name}", width="stretch",
                      type="primary" if st.session_state["workspace_page"] == name else "secondary",
                      on_click=select_workspace, args=(name,))
    page = st.session_state["workspace_page"]

    st.divider()

    with st.expander("Settings", icon=":material/settings:", expanded=False):
        st.toggle("Ambient animation", value=True, key="aurora_motion", help="Pause decorative background, navigation and Copilot motion.")
    st.caption("Live AI available · v0.17.0" if live_ai_available() else "Local analysis · v0.17.0")


# Keep animation rules stable across reruns; mount a new keyed workspace on navigation.
from finsight.navigation_motion import navigation_css, workspace_key
st.markdown("<style>" + navigation_css(st.session_state.get("aurora_motion", True)) + "</style>", unsafe_allow_html=True)
copilot_workbook = None
typed = None
prompt_slot = None
active_annual = st.session_state.get("annual_workbook")
if page == "AI Copilot":
    from finsight.copilot_ui import copilot_css
    st.html("<style>" + copilot_css() + "</style>")
    st.title("AI Copilot")
    workbooks = {
        source["id"]: source
        for source in (active_annual, st.session_state.get("chat_workbook"))
        if source
    }
    can_analyze = "validated_data" in st.session_state and "annual_data" not in st.session_state
    mode = "Workbook" if workbooks else "Financial analysis"
    if workbooks and can_analyze:
        modes = ["Financial analysis", "Workbook"]
        mode = st.radio("Question source", modes, horizontal=True, key="copilot_mode_selector",
                        index=modes.index(st.session_state.get("copilot_mode", modes[0])))
        st.session_state["copilot_mode"] = mode
    if mode == "Workbook":
        workbook_ids = list(workbooks)
        workbook_id = st.session_state.get("copilot_workbook_id")
        if workbook_id not in workbooks:
            workbook_id = workbook_ids[0]
        if len(workbooks) > 1:
            workbook_id = st.selectbox("Workbook", workbook_ids, index=workbook_ids.index(workbook_id),
                                       format_func=lambda key: workbooks[key]["name"])
        st.session_state["copilot_workbook_id"] = workbook_id
        copilot_workbook = workbooks[workbook_id]
        prompt_slot = st.bottom.empty()
        typed = st.chat_input("Ask about a worksheet, cell, or range.", key="copilot_workbook_question")
    elif can_analyze:
        prompt_slot = st.bottom.empty()
        typed = st.chat_input("Ask about your financial data.", key="copilot_financial_question")

# ==========================================
# OVERVIEW
# ==========================================

with st.container(key=workspace_key(page)):
    if copilot_workbook:
        from finsight.workbook_chat import render_chat
        same_annual = active_annual and active_annual["id"] == copilot_workbook["id"]
        render_chat(st, copilot_workbook, typed, prompt_slot, annual=st.session_state.get("annual_data") if same_annual else None,
                    annual_sheet=active_annual["selected"] if same_annual else None,
                    dataset_key=st.session_state.get("dataset_id", "") if same_annual else "")
    elif "annual_data" in st.session_state and page != "Data Upload":
        from finsight.annual_analytics import render_annual
        render_annual(st, page, st.session_state)
    elif page == "Overview":

        st.title("Financial overview")

        if "validated_data" in st.session_state:
            df = st.session_state["validated_data"]
            monthly = calculate_monthly_performance(df)
            from finsight.overview_layout import reporting_label, overview_css
            st.markdown("<style>" + overview_css() + "</style>", unsafe_allow_html=True)
            st.caption(f"{reporting_label(monthly['month'])} · {len(df):,} validated records · {st.session_state.get('file_name', 'Active dataset')}")
            with st.container(key="overview_metrics"):
                show_metrics(df)
            with st.container(key="overview_charts"):
                left, right = st.columns([2, 1])
                with left:
                    with st.container(key="overview_revenue_card"):
                        st.subheader("Monthly revenue")
                        fig = px.bar(monthly, x="month", y="revenue", labels={"month": "Month", "revenue": "Revenue"})
                        fig.update_traces(marker_color="#426E9B")
                        fig.update_yaxes(tickprefix="$")
                        fig = style_chart(fig)
                        fig.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                        fig.update_xaxes(title_text=None)
                        st.plotly_chart(fig, width="stretch")
                with right:
                    with st.container(key="overview_margin_card"):
                        st.subheader("Gross margin")
                        fig = px.line(monthly, x="month", y="gross_margin", markers=True, labels={"month": "Month", "gross_margin": "Margin"})
                        fig.update_traces(line_color="#16967A")
                        fig.update_yaxes(tickformat=".0%")
                        fig = style_chart(fig)
                        fig.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                        fig.update_xaxes(title_text=None)
                        st.plotly_chart(fig, width="stretch")
        else:
            st.info("Upload a financial dataset to view your dashboard.")

        with st.expander("Calculation methodology"):
            st.write("Financial calculations are performed by a deterministic Python engine, independently of the AI model.")


    # ==========================================
    # DATA UPLOAD
    # ==========================================

    elif page == "Data Upload":
        from finsight.upload_ui import render_upload
        render_upload(st, clear_validation, open_workbook_in_copilot)

    # ==========================================
    # FINANCIAL ANALYSIS
    # ==========================================

    elif page == "Financial Analysis":

        st.title("Financial Analysis")

        from finsight.analysis_layout import analysis_css, monthly_display, compact_chart
        from finsight.overview_layout import reporting_label
        st.markdown("<style>" + analysis_css() + "</style>", unsafe_allow_html=True)
        df = require_data(show_source=False)

        df = apply_filters(df, "analysis", show_count=False)
        monthly = calculate_monthly_performance(df)
        st.caption(f"{reporting_label(monthly['month'])} · {len(monthly)} reporting months · {len(df):,} records · {st.session_state.get('file_name', 'Active dataset')}")

        metrics = show_metrics(df)

        with st.container(key="analysis_charts"):
            left, right = st.columns(2)

            with left:

                fig = px.line(
                    monthly,
                    x="month",
                    y="revenue",
                    markers=True,
                    title="Monthly Revenue"
                )

                fig.update_traces(
                    line_color="#426E9B"
                )

                st.plotly_chart(
                    compact_chart(style_chart(fig)),
                    width="stretch"
                )

            with right:

                fig = px.line(
                    monthly,
                    x="month",
                    y="gross_profit",
                    markers=True,
                    title="Monthly Gross Profit"
                )

                fig.update_traces(
                    line_color="#16967A"
                )

                st.plotly_chart(
                    compact_chart(style_chart(fig)),
                    width="stretch"
                )

            left, right = st.columns(2)

            with left:

                fig = px.bar(
                    monthly,
                    x="month",
                    y="revenue_growth",
                    title="Monthly revenue growth"
                )

                fig.update_traces(marker_color=["#94A3B8" if pd.isna(v) else "#16967A" if v >= 0 else "#B91C1C" for v in monthly["revenue_growth"]])

                fig.update_yaxes(tickformat=".0%")

                st.plotly_chart(
                    compact_chart(style_chart(fig)),
                    width="stretch"
                )

            with right:

                fig = px.line(
                    monthly,
                    x="month",
                    y="gross_margin",
                    markers=True,
                    title="Monthly gross margin"
                )

                fig.update_traces(line_color="#16967A")
                fig.update_yaxes(tickformat=".0%")

                st.plotly_chart(
                    compact_chart(style_chart(fig)),
                    width="stretch"
                )

        with st.expander("Monthly financial summary"):
            st.dataframe(monthly_display(monthly), width="stretch", hide_index=True, column_config={
                "month": "Month", "records": "Records",
                "revenue": st.column_config.NumberColumn("Revenue", format="dollar"),
                "cogs": st.column_config.NumberColumn("COGS", format="dollar"),
                "gross_profit": st.column_config.NumberColumn("Gross profit", format="dollar"),
                "gross_margin": st.column_config.NumberColumn("Gross margin", format="percent"),
                "revenue_growth": st.column_config.NumberColumn("Revenue growth", format="percent"),
                "margin_change_pp": st.column_config.NumberColumn("Margin change (pp)", format="%.2f"),
            })

        with st.expander("Calculation methodology and source records"):

            st.write(
                f"Revenue = "
                f"${metrics['revenue']:,.2f}"
            )

            st.write(
                f"Gross Profit = "
                f"${metrics['revenue']:,.2f} - "
                f"${metrics['cogs']:,.2f} = "
                f"${metrics['gross_profit']:,.2f}"
            )

            st.write(
                "Gross Margin = "
                "Gross Profit / Revenue = "
                f"{format_percent(metrics['gross_margin'])}"
            )

            st.markdown("**Supporting Source Records**")

            show_table(df)


    # ==========================================
    # PERFORMANCE DRIVERS
    # ==========================================

    elif page == "Performance Drivers":

        from finsight.drivers_layout import drivers_css, driver_chart
        from finsight.overview_layout import reporting_label
        st.title("Performance Drivers")
        st.markdown("<style>" + drivers_css() + "</style>", unsafe_allow_html=True)
        df = require_data(show_source=False)
        df = apply_filters(df, "drivers", show_count=False)
        st.caption(f"{reporting_label(df['date'])} · {len(df):,} records · {st.session_state.get('file_name', 'Active dataset')}")

        dimensions = [
            field for field in
            ["product", "country", "segment"]
            if field in df.columns
        ]

        if not dimensions:

            st.warning(
                "Map a product, country, or segment "
                "column to enable this analysis."
            )

            st.stop()

        dimension_col, view_col = st.columns([1, 2])
        dimension = dimension_col.selectbox(
            "Analyze Performance By", dimensions, format_func=str.title
        )
        view = view_col.segmented_control(
            "Analysis view", ["Performance rankings", "Revenue change"],
            default="Performance rankings", key="drivers_view_segmented",
            selection_mode="single"
        ) or "Performance rankings"
        if view == "Performance rankings":
            breakdown = calculate_breakdown(
                df,
                dimension
            )

            leaders = st.columns(2)
            if not breakdown.empty:
                revenue_leader = breakdown.sort_values("revenue", ascending=False).iloc[0]
                leaders[0].metric("Revenue leader · " + str(revenue_leader[dimension]), format_money(revenue_leader["revenue"]))
                valid = breakdown.dropna(subset=["gross_margin"])
                if not valid.empty:
                    margin_leader = valid.sort_values("gross_margin", ascending=False).iloc[0]
                    leaders[1].metric("Highest gross margin · " + str(margin_leader[dimension]), format_percent(margin_leader["gross_margin"]))

            left, right = st.columns(2)

            with left:

                fig = px.bar(
                    breakdown,
                    x="revenue",
                    y=dimension,
                    orientation="h",
                    title="Revenue Ranking",
                    color_discrete_sequence=["#426E9B"]
                )

                fig.update_yaxes(
                    categoryorder="total ascending"
                )

                st.plotly_chart(
                    driver_chart(style_chart(fig), len(breakdown), horizontal=True),
                    width="stretch"
                )

            with right:

                fig = px.bar(
                    breakdown,
                    x="gross_profit",
                    y=dimension,
                    orientation="h",
                    title="Gross Profit Ranking",
                    color_discrete_sequence=["#16967A"]
                )

                fig.update_yaxes(
                    categoryorder="total ascending"
                )

                st.plotly_chart(
                    driver_chart(style_chart(fig), len(breakdown), horizontal=True),
                    width="stretch"
                )

            with st.expander("Detailed performance breakdown"):
                show_table(breakdown, labels={dimension: dimension.title(), "cogs": "COGS", "records": "Records"})

        else:
            months = sorted(
                df["date"]
                .dt.to_period("M")
                .astype(str)
                .unique()
                .tolist()
            )

            if len(months) < 2:

                st.warning(
                    "At least two months of data are required."
                )

                st.stop()

            left, right = st.columns(2)

            with left:

                previous_month = st.selectbox(
                    "Previous Period",
                    months,
                    index=len(months) - 2
                )

            with right:

                current_month = st.selectbox(
                    "Current Period",
                    months,
                    index=len(months) - 1
                )

            if current_month <= previous_month:

                st.warning(
                    "Current period must be later "
                    "than the previous period."
                )

                st.stop()

            drivers = calculate_revenue_drivers(
                df,
                dimension,
                current_month,
                previous_month
            )

            if drivers.empty:

                st.warning(
                    "Insufficient data for this comparison."
                )

                st.stop()

            previous_revenue = float(
                drivers["previous_revenue"].sum()
            )

            current_revenue = float(
                drivers["current_revenue"].sum()
            )

            total_change = float(
                drivers["revenue_change"].sum()
            )

            growth = (
                total_change / previous_revenue
                if previous_revenue > 0
                else None
            )

            cols = st.columns(4)

            cols[0].metric(
                "Previous Revenue",
                format_money(previous_revenue)
            )

            cols[1].metric(
                "Current Revenue",
                format_money(current_revenue)
            )

            cols[2].metric(
                "Revenue Change",
                format_money(total_change)
            )

            cols[3].metric(
                "Growth",
                format_percent(growth)
            )

            drivers["direction"] = (
                drivers["revenue_change"].apply(
                    lambda x: (
                        "Increase" if x > 0
                        else "Decrease" if x < 0
                        else "Unchanged"
                    )
                )
            )

            fig = px.bar(
                drivers,
                x=dimension,
                y="revenue_change",
                color="direction",
                color_discrete_map={
                    "Increase": "#16967A",
                    "Decrease": "#B91C1C",
                    "Unchanged": "#94A3B8"
                },
                title="Revenue Change Attribution"
            )

            fig.add_hline(
                y=0,
                line_color="gray"
            )

            st.plotly_chart(
                driver_chart(style_chart(fig)),
                width="stretch"
            )

            with st.expander("Detailed revenue attribution"):
                show_table(drivers, labels={dimension: dimension.title(), "direction": "Direction"})

            negative = drivers[
                drivers["revenue_change"] < 0
            ].sort_values("revenue_change")

            positive = drivers[
                drivers["revenue_change"] > 0
            ].sort_values(
                "revenue_change",
                ascending=False
            )

            findings = st.columns(2)
            if not positive.empty:
                largest = positive.iloc[0]
                findings[0].markdown(
                    f"**Largest positive contributor:** {largest[dimension]} — "
                    f":green[+{format_money(largest['revenue_change'])}]"
                )
            if not negative.empty:
                largest = negative.iloc[0]
                findings[1].markdown(
                    f"**Largest negative contributor:** {largest[dimension]} — "
                    f":red[{format_money(largest['revenue_change'])}]"
                )

            st.caption(
                "These findings identify arithmetic "
                "contributors, not proven business causes."
            )

            with st.expander("Supporting Source Evidence"):

                selected_value = st.selectbox(
                    "Select Contributor",
                    drivers[dimension].tolist()
                )

                evidence = df.copy()

                evidence["comparison_month"] = (
                    evidence["date"]
                    .dt.to_period("M")
                    .astype(str)
                )

                category = (
                    evidence[dimension]
                    .astype("string")
                    .fillna("Unknown")
                )

                evidence = evidence[
                    (category == selected_value)
                    & (
                        evidence["comparison_month"].isin(
                            [previous_month, current_month]
                        )
                    )
                ]

                show_table(evidence)

                st.download_button(
                    "Download Supporting Evidence",
                    evidence.to_csv(
                        index=False
                    ).encode("utf-8"),
                    "revenue_driver_evidence.csv",
                    "text/csv"
                )

    # ==========================================
    # ANOMALY DETECTION
    # ==========================================

    elif page == "Anomaly Detection":

        from finsight.anomaly_layout import anomaly_css, anomaly_chart, anomaly_findings, anomaly_display
        from finsight.overview_layout import reporting_label
        st.markdown("<style>" + anomaly_css() + "</style>", unsafe_allow_html=True)
        st.title("Anomaly Detection")
        df = apply_filters(require_data(show_source=False), "anomalies", show_count=False)
        monthly = calculate_monthly_performance(df)
        st.caption(f"{reporting_label(monthly['month'])} · {len(monthly)} reporting months · {len(df):,} records · {st.session_state.get('file_name', 'Active dataset')}")
        anomalies = detect_anomalies(df)
        cols = st.columns(3)
        cols[0].metric("Total flags", len(anomalies))
        cols[1].metric("High priority", sum(f['severity'] == 'High' for f in anomalies))
        cols[2].metric("Review required", sum(f['severity'] == 'Review' for f in anomalies))

        fig = px.bar(monthly, x="month", y="revenue_growth", title="Monthly revenue growth and thresholds")
        fig.update_traces(marker_color=["#94A3B8" if pd.isna(v) else "#16967A" if v >= 0 else "#B91C1C" for v in monthly["revenue_growth"]])
        fig.update_yaxes(tickformat=".0%")
        for threshold, color in [(0.20, "#16967A"), (-0.20, "#B91C1C")]:
            fig.add_hline(y=threshold, line_dash="dash", line_color=color)
        st.plotly_chart(anomaly_chart(style_chart(fig)), width="stretch")
        st.caption("Dashed lines: +20% / −20% revenue growth thresholds. Rule-based flags, not statistical or AI predictions.")

        if anomalies:
            left, right = st.columns(2)
            decline, compression = anomaly_findings(anomalies)
            for col, finding, label, fmt in [(left, decline, "Largest flagged revenue decline", "+.2%"), (right, compression, "Largest flagged margin compression", "+.2f")]:
                with col:
                    if finding is None:
                        st.markdown(f"**{label}:** None flagged")
                    else:
                        value = format(finding['value'], fmt) + (" pp" if fmt == "+.2f" else "")
                        st.markdown(f"**{label}:** :red[{value}] · {finding['period']}")
        else:
            st.success("No anomalies detected under the current business rules.")

        with st.expander(f"Anomaly register ({len(anomalies)})"):
            severity = st.selectbox("Severity", ["All flags", "High", "Review"], format_func=lambda v: {"High": "High priority", "Review": "Review required"}.get(v, v), key="anomaly_register_severity")
            display = anomaly_display(anomalies, severity)
            if display.empty:
                st.caption("No flags match this selection.")
            else:
                show_table(display, labels={"period":"Period", "category":"Category", "severity":"Severity", "value":"Change", "description":"Description"})
            if anomalies:
                st.download_button("Download full anomaly register", pd.DataFrame(anomalies).to_csv(index=False).encode("utf-8"), "financial_anomalies.csv", "text/csv")

        with st.expander("Detection methodology"):
            st.write("Revenue decline: 20% or more month over month.")
            st.write("Revenue increase: 20% or more month over month.")
            st.write("Margin compression: decline of 3 percentage points or more.")
            st.write("Missing months are not treated as zero.")


    # ==========================================
    # AI COPILOT
    # ==========================================

    elif page == "Scenario Modeling":
        from finsight.scenario_layout import METRICS, compact_value, scenario_rows, scenario_chart, scenario_css
        from finsight.workspace_ui import SIM_DEFAULTS, visible_delta, scenario_delta_color
        from finsight.scenario_controls import simulate_controls, target_controls
        from finsight.scenario_presentation import executive_summary
        st.markdown("<style>" + scenario_css() + "</style>", unsafe_allow_html=True)
        st.title("Scenario Modeling")
        df = apply_filters(require_data(show_source=False), "simulator", show_count=False)
        st.caption(f"{compact_period(', '.join(sorted(df['date'].dt.to_period('M').astype(str).unique())))} · {len(df):,} records · {st.session_state.get('file_name', 'Active dataset')} · Hypothetical, not a forecast · No AI requests")
        def reset_simulator():
            for key, value in SIM_DEFAULTS.items():
                st.session_state[key] = value
        for key, value in SIM_DEFAULTS.items():
            st.session_state.setdefault(key, value)
        mode_col, reset_col = st.columns([4, 1], vertical_alignment="bottom")
        sim_mode = mode_col.segmented_control("Scenario type", ["Revenue and COGS", "Target gross margin"], default="Revenue and COGS", key="sim_type_segmented", selection_mode="single") or "Revenue and COGS"
        reset_col.button("Reset assumptions", key="sim_reset", on_click=reset_simulator, width="stretch")
        try:
            if sim_mode == "Revenue and COGS":
                left, right = st.columns(2)
                rev = left.slider("Revenue adjustment (%)", -100, 50, key="sim_rev")
                cost = right.slider("COGS adjustment (%)", -100, 50, key="sim_cost")
                behavior = st.radio("Cost behavior", ["Independent", "Proportional to revenue"], key="sim_behavior", horizontal=True)
                simulation = simulate_controls(df, rev, cost, behavior == "Proportional to revenue")
            else:
                target = st.slider("Target gross margin (%)", 0, 99, key="sim_target")
                simulation = target_controls(df, target)
            base = simulation["baseline"]
            cases = simulation["cases"]
            if len(cases) > 1:
                selected = st.radio("Target margin approach", list(range(len(cases))), format_func=lambda i: cases[i]["label"], horizontal=True, key="sim_target_approach")
            else:
                selected = 0
            projected = cases[selected]["metrics"]
            for col, metric in zip(st.columns(4), METRICS):
                margin = metric.endswith("(%)")
                value = projected[metric]
                delta = value - base[metric] if value is not None and base[metric] is not None else None
                col.metric(metric, compact_value(value, margin), compact_value(delta, margin, True) if visible_delta(delta, margin) is not None else None, delta_color=scenario_delta_color(metric, delta))
            chart = pd.DataFrame({"Metric": list(METRICS[:3]), "Baseline": [base[k] for k in METRICS[:3]], "Projected": [projected[k] for k in METRICS[:3]]})
            st.plotly_chart(scenario_chart(style_chart(px.bar(chart, x="Metric", y=["Baseline", "Projected"], barmode="group", color_discrete_sequence=["#426E9B", "#16967A"], labels={"value": "Source currency units", "variable": "Case"}))), width="stretch", key="sim_chart_compact")
            with st.expander("Detailed scenario calculations"):
                st.caption("Source currency units · " + executive_summary(base, projected))
                for case in cases:
                    if len(cases) > 1:
                        st.markdown("**" + case["label"] + "**")
                    st.dataframe(pd.DataFrame(scenario_rows(base, case["metrics"])), hide_index=True, width="stretch")
            with st.expander("Assumptions and methodology"):
                st.write("Independent: COGS adjustment applies to baseline costs. Proportional: costs first scale with revenue, then the COGS adjustment applies.")
                st.write("Gross profit = revenue minus COGS. Gross margin = gross profit divided by revenue; undefined when revenue is zero. Target margin cases hold either revenue or COGS constant.")
                st.caption("Uses currently filtered records. Hypothetical, not a forecast. No AI requests.")
        except ValueError as exc:
            st.warning(str(exc))


    elif page == "AI Copilot":

        if "validated_data" not in st.session_state:
            st.info("Upload an Excel workbook or a financial CSV to start asking questions.")
            st.stop()

        from finsight.copilot_ui import copilot_context, copilot_toolbar
        context, settings, reset = copilot_toolbar(st, "copilot_new_chat")
        if reset:
            st.session_state["ai_history"] = []
            st.session_state.pop("validated_ai_cache", None)
            st.rerun()
        with settings:
            df = apply_filters(require_data(show_source=False), "copilot", embedded=True)
            source = st.session_state["file_name"]
            sheet = st.session_state["sheet_name"]
            st.caption(f"Dataset: {source} · {sheet}")

            st.markdown("**Analysis mode**")
            with st.container():
                mode = st.radio("Analysis mode", ["Automatic", "Financial summary", "Revenue change investigation", "Multi-dimensional investigation"], horizontal=True)
                st.caption("Automatic mode selects evidence using your question and the filtered dataset. Explicit monthly comparisons require both months to be present.")
                dimension = current = previous = None
                if mode in ("Revenue change investigation", "Multi-dimensional investigation"):
                    dimensions = [x for x in ["product", "country", "segment"] if x in df.columns]
                    months = sorted(df["date"].dt.to_period("M").astype(str).unique())
                    if not dimensions or len(months) < 2:
                        st.warning("This mode requires a mapped business dimension and at least two months.")
                        st.stop()
                    dimension = st.selectbox("Analyze by", dimensions, format_func=str.title) if mode == "Revenue change investigation" else "all"
                    left, right = st.columns(2)
                    previous = left.selectbox("Previous period", months, index=len(months)-2, key="ai_previous")
                    current = right.selectbox("Current period", months, index=len(months)-1, key="ai_current")
                    if current <= previous:
                        st.warning("Choose a current period later than the previous period.")
                        st.stop()
                    suggestions = [f"Explain the revenue change from {previous} to {current}" +
                                   (f" by {dimension}." if dimension != "all" else ".")]
                else:
                    from finsight.copilot_ui import financial_suggestions
                    suggestions = (financial_suggestions(df) if mode == "Automatic"
                                   else ["Summarize financial performance."])

            scenario_demo = st.session_state.get("scenario_demo_source", False)
            live_scenario_ai = dataset_ai_available(demo=scenario_demo)
            data_ai = live_scenario_ai and (scenario_demo or st.checkbox("Allow AI to receive aggregated evidence from this uploaded dataset", value=False, key=f"copilot_consent_{st.session_state.get('dataset_id')}"))
            if live_scenario_ai:
                from finsight.api_guard import quota_status
                with st.container():
                    st.caption("Live AI quota")
                    try:
                        for quota in quota_status():
                            st.caption(f"{quota['window'].title()}: {quota['remaining']} / {quota['limit']} remaining" + (f"; next request in about {int(quota['retry_seconds'])+1} seconds" if quota['retry_seconds'] is not None else ""))
                    except Exception:
                        st.caption("Quota status unavailable; request guard remains active.")
            from finsight.request_policy import allow_ai, cached_analysis
            st.markdown("**AI interpretation**")
            with st.container():
                deeper_ai = st.checkbox("Include AI interpretation for basic financial questions", value=False, disabled=not data_ai) and data_ai
                scenario_ai = st.checkbox(
                    "Include AI strategic interpretation for scenarios",
                    value=bool(scenario_demo and live_scenario_ai),
                    key=f"scenario_ai_{scenario_demo}_{st.session_state.get('dataset_id')}_{live_scenario_ai}",
                    disabled=not data_ai,
                ) and data_ai
            st.caption("Follow-up questions reuse context. Changing filters or starting a new chat resets context.")
        period = compact_period(', '.join(sorted(df['date'].dt.to_period('M').astype(str).unique())))
        processing = "OpenAI available for analysis" if data_ai else "Local analysis"
        context.html(copilot_context(source, period, processing))
        scope = (st.session_state.get("dataset_id"), source, sheet, mode, dimension, previous, current, hashlib.sha256(df.to_csv(index=False).encode()).hexdigest())
        if st.session_state.get("ai_scope") != scope:
            st.session_state["ai_scope"] = scope
            st.session_state["ai_history"] = []
        history = st.session_state["ai_history"]
        suggestion = None
        if not history and not typed and suggestions and prompt_slot is not None:
            prompts = prompt_slot.container(horizontal=True, gap="small")
            for i, prompt in enumerate(suggestions):
                if prompts.button(prompt, key=f"suggestion_{i}"):
                    suggestion = prompt
            if suggestion:
                prompt_slot.empty()

        def render_answer(result, answer_index):
            if result.get("cache_hit"):
                st.caption("Reused validated session response; no new AI request.")
            if result.get("session_limited"):
                st.caption("Session AI limit reached; local analysis used.")
            if "scenario" in result:
                scenario = result["scenario"]
                st.subheader("Financial scenario — illustrative, not a forecast")
                st.caption(compact_period(scenario["period"]))
                st.caption(f"Baseline: {scenario['records']} selected records. Monetary values in source currency units.")
                from finsight.scenario_presentation import format_value, executive_summary
                if result.get("effective_question") != result.get("question") and result.get("effective_question"):
                    st.caption("Interpreted follow-up: " + result["effective_question"])
                for case_index, case in enumerate(scenario["cases"]):
                    st.markdown("**" + case["label"] + "**")
                    base, projected = scenario["baseline"], case["metrics"]
                    st.write(executive_summary(base, projected))
                    if case["label"].startswith("Target via"):
                        metric = "Revenue" if "via revenue" in case["label"] else "COGS"
                        st.metric("Required " + metric, format_value(projected[metric]), format_value(projected[metric]-base[metric], delta=True))
                    cols = st.columns(2)
                    for col, metric in zip(cols, ("Gross profit", "Gross margin (%)")):
                        margin = metric.endswith("(%)")
                        delta = projected[metric]-base[metric] if projected[metric] is not None and base[metric] is not None else None
                        col.metric("Gross margin" if margin else metric, format_value(projected[metric], margin), format_value(delta, margin, True) if delta is not None else None)
                    table = []
                    for metric, value in base.items():
                        p = projected[metric]
                        margin = metric.endswith("(%)")
                        table.append({"Metric": metric, "Baseline": format_value(value, margin), "Projected": format_value(p, margin), "Change": format_value(p-value if p is not None and value is not None else None, margin, True)})
                    with st.expander("Baseline and projected calculations"):
                        st.dataframe(pd.DataFrame(table), hide_index=True)
                        chart = pd.DataFrame({"Metric": ["Revenue", "COGS", "Gross profit"], "Baseline": [base[k] for k in ("Revenue", "COGS", "Gross profit")], "Projected": [projected[k] for k in ("Revenue", "COGS", "Gross profit")]})
                        st.plotly_chart(px.bar(chart, x="Metric", y=["Baseline", "Projected"], barmode="group", color_discrete_sequence=["#426E9B", "#16967A"], labels={"value":"Source currency units", "variable":"Case"}), key=f"scenario_chart_{answer_index}_{case_index}")
                if result.get("sensitivity"):
                    with st.expander("Sensitivity analysis"):
                        st.caption("Percentage magnitude varies; original direction and reporting scope are preserved.")
                        st.plotly_chart(px.line(pd.DataFrame(result["sensitivity"]), x="Assumption magnitude (%)", y="Gross profit", color="Cost assumption", markers=True), key=f"scenario_sensitivity_{answer_index}")
                commentary = result.get("scenario_commentary")
                if commentary:
                    st.markdown("**" + commentary["source"] + "**")
                    st.text(commentary["text"])
                    st.caption(commentary["status"])
                    if commentary.get("diagnostic"):
                        with st.expander("Validation details"):
                            st.caption(commentary["diagnostic"])
                    if commentary["tokens"] is not None:
                        st.caption(f"Reported API tokens: {commentary['tokens']}")
                else:
                    st.caption("No AI request sent.")
                with st.expander("Model assumptions and reporting scope"):
                    st.caption("Exact reporting months: " + scenario["period"])
                    st.caption("No demand, capacity, stranded costs, taxes or operating expenses are modeled.")
                    if any(case["label"].startswith("Remove segment") for case in scenario["cases"]):
                        st.caption("Segment removal assumes all recorded segment COGS are avoidable.")
                return
            if result.get("effective_question") and result["effective_question"] != result["question"]:
                st.caption("Interpreted follow-up: " + result["effective_question"])
            if result.get("effective_period"):
                st.caption("Reporting period: " + compact_period(result["effective_period"]))
            if result.get("investigation"):
                with st.expander("Deterministic reconciliation", expanded=False):
                    inv = result["investigation"]
                    st.caption(inv["note"])
                    st.dataframe([{"Dimension": d, "Net revenue change": round(b["net_change"], 2), "Reconciliation difference": round(b["reconciliation_difference"], 2)} for d,b in inv["dimensions"].items()])
            from finsight.evidence_ui import evidence_sections
            featured, records = evidence_sections(result)
            def source_view():
                if featured:
                    st.caption("References are scoped to this answer. Registry membership is not independent verification of a claim.")
                    selected = st.selectbox("Choose a source", [r['evidence_id'] for r in featured],
                        format_func=lambda eid: next(f"[{eid}] {r['title']}" for r in featured if r['evidence_id'] == eid),
                        key=f"primary_evidence_{answer_index}")
                    record = next(r for r in featured if r['evidence_id'] == selected)
                    st.write(record.get('title', ''))
                    st.caption("Calculation methodology")
                    st.text(str(record.get('methodology', 'Not supplied')))
                    st.caption("Calculated values (original evidence units)")
                    from finsight.workspace_ui import evidence_rows
                    st.dataframe(pd.DataFrame(evidence_rows(record.get("values", {}), record.get("category"))), hide_index=True, width="stretch")
                    st.caption("Original evidence (raw values)")
                    st.json(record.get("values", {}), expanded=False)
                    st.caption("Source file, worksheet and row references where available")
                    st.json(record.get('source', {}), expanded=False)
            show_executive_analysis(result, compact=True)
            diagnostic = result.get("numerical_verification", {}).get("commentary_diagnostic")
            if diagnostic == "Local recommendations used; no live AI request for this analysis.":
                st.caption("Local rule-based recommendations · No AI request" if result.get("local_plan") else "Calculated locally · No AI request")
            elif diagnostic: st.caption(diagnostic)
            elif result.get("local_plan"): st.caption("Local rule-based recommendations.")
            verification = result["verification"]
            check = result.get("numerical_verification", {})
            if not verification["passed"]:
                st.warning("Citation ID verification did not pass. Review this answer before relying on it.")
            if check.get("mode") == "deterministic":
                if not check.get("controlled_actions") and (not check.get("commentary_accepted") or check.get("commentary_diagnostic")):
                    st.warning("Some AI commentary was withheld or rejected. Review the verification details.")
            elif check.get("extraction_status") != "completed" or any(check.get(k) for k in ("failed", "unverified", "coverage_warnings", "errors")):
                st.warning("Numerical verification is incomplete or requires review.")
            with st.expander(f"Sources and calculations ({len(records)} records)", expanded=False):
                st.caption("Citation ID checks do not establish factual accuracy; financial values are not independently audited.")
                source_view()
                show_executive_analysis(result, compact=True, supporting_only=True)
                if result.get("effective_period"):
                    st.caption("Exact reporting months: " + result["effective_period"])
                if result.get("route"):
                    route = result["route"]
                    st.caption(f"Selected analysis: {route['mode']}")
                    st.write(route.get("reason", ""))
                    if route.get("previous_month") and route.get("current_month"):
                        st.write(f"Dimension: {route['dimension']} | {route['previous_month']} to {route['current_month']}")
                if result.get("active_skills"):
                    st.caption("Active financial skills: " + ", ".join(result["active_skills"]))
                show_numerical_verification(result, compact=True)
                if verification["passed"]:
                    st.success("All cited evidence IDs exist in the registry.")
                cols = st.columns(3)
                cols[0].metric("Valid IDs", len(verification["valid_citations"]))
                cols[1].metric("Invalid IDs", len(verification["invalid_citations"]))
                cols[2].metric("Reported tokens", result["total_tokens"])
                st.caption(f"Model: {result['model']} | Token count for final request only")
                options = ["Citation verification details"] + [
                    f"[{record['evidence_id']}] {record['title']}" for record in records
                ]
                choice = st.selectbox(
                    "Select evidence or verification details",
                    range(len(options)),
                    format_func=lambda index: options[index],
                    key=f"copilot_evidence_{answer_index}",
                )
                if choice == 0:
                    st.json(verification)
                else:
                    record = records[choice - 1]
                    st.write("Methodology:", record.get("methodology"))
                    st.write("Calculated values:")
                    st.write(record.get("values"))
                    st.write("Source evidence:")
                    st.write(record.get("source", {}))
                    st.write("Full evidence record:")
                    st.write(record)

        for answer_index, item in enumerate(history):
            with st.chat_message("user", avatar=":material/person:"):
                st.write(item["question"])
            with st.chat_message("assistant", avatar=":material/auto_awesome:"):
                render_answer(item, answer_index)

        question = suggestion or typed
        if question and question.strip():
            with st.chat_message("user", avatar=":material/person:"):
                st.write(question)
            with st.chat_message("assistant", avatar=":material/auto_awesome:"):
                try:
                    from finsight.ai_engine import analyze_financial_data, investigate_revenue_change
                    from finsight.question_router import route_question
                    original_question = question
                    from finsight.question_safety import question_warning
                    warning = question_warning(question)
                    if warning:
                        st.warning(warning)
                        st.info("No AI request was sent.")
                        st.stop()
                    from finsight.scenario import is_scenario, run_scenario
                    from finsight.scenario_presentation import resolve_scenario_followup, sensitivity
                    if mode == "Automatic":
                        question, scenario_clarification = resolve_scenario_followup(question, history[-1] if history else None)
                        if scenario_clarification:
                            st.warning(scenario_clarification)
                            st.info("No AI request was sent.")
                            st.stop()
                    if mode == "Automatic" and re.search(r"\bshould\b.*\bdiscontinue\b", question, re.I):
                        from finsight.request_policy import closure_decision
                        st.markdown(closure_decision(question, df))
                        st.info("No AI request was sent.")
                        st.stop()
                    if mode == "Automatic" and is_scenario(question):
                        try:
                            scenario = run_scenario(question, df)
                        except ValueError as exc:
                            st.warning(str(exc))
                            st.info("No AI request was sent.")
                            st.stop()
                        result = {"question": original_question, "effective_question": question, "scenario": scenario, "sensitivity": sensitivity(question, df), "route": {"mode": "scenario"}}
                        from finsight.scenario_commentary import interpret_scenario
                        with st.spinner("Preparing scenario interpretation..."):
                            result = cached_analysis(st.session_state, (scope, question, "scenario"), scenario_ai, lambda enabled: dict(result, scenario_commentary=interpret_scenario(question, scenario, enabled=enabled)))
                        history.append(result)
                        st.rerun()
                    if mode == "Automatic":
                        from finsight.conversation import resolve_followup
                        question, clarification = resolve_followup(question, history[-1] if history else None)
                        if clarification:
                            st.warning(clarification)
                            st.info("No AI request was sent.")
                            st.stop()
                        months = sorted(df["date"].dt.to_period("M").dropna().astype(str).unique())
                        route = route_question(question, months)
                    elif mode == "Multi-dimensional investigation":
                        route = {"mode": "multi_investigation", "dimension": "all", "current_month": current, "previous_month": previous, "reason": "Multi-dimensional comparison."}
                    elif mode == "Revenue change investigation":
                        route = {"mode": "revenue_investigation", "dimension": dimension, "current_month": current, "previous_month": previous, "reason": "Manual selection."}
                    else:
                        route = {"mode": "summary", "reason": "Manual selection."}
                    if route["mode"] in ("summary", "ranking"):
                        from finsight.reliability import scope_data
                        try:
                            scope_data(question, df, route)
                        except ValueError as exc:
                            st.warning(str(exc))
                            st.info("No AI request was sent.")
                            st.stop()
                    if route["mode"] == "clarify":
                        st.warning(route["reason"])
                        st.info("Please rephrase your question or choose manual analysis. No AI request was sent.")
                        st.stop()
                    if mode == "Automatic" and route["mode"] in ("summary", "ranking"):
                        from finsight.request_policy import named_analysis
                        direct = named_analysis(question, df)
                        if direct is not None:
                            st.markdown(direct)
                            st.info("No AI request was sent.")
                            st.stop()
                    if route["mode"] == "revenue_investigation" and route["dimension"] not in df.columns:
                        st.warning("The requested business dimension is not mapped in this dataset. No AI request was sent.")
                        st.stop()
                    def run_analysis(enabled):
                        if route["mode"] == "multi_investigation":
                            from finsight.investigation_bridge import run_investigation
                            return run_investigation(question, df, route["previous_month"], route["current_month"], source, sheet, enabled=enabled)
                        elif route["mode"] == "revenue_investigation":
                            return investigate_revenue_change(question, df, route["dimension"], route["current_month"], route["previous_month"], source, sheet, enabled=enabled)
                        else:
                            return analyze_financial_data(question, df, source, sheet, route=route, enabled=enabled)
                    ai_requested = allow_ai(question, route, deeper_ai)
                    with st.spinner("Calculating evidence and generating analysis..."):
                        result = cached_analysis(st.session_state, (scope, question, str(route)), data_ai and ai_requested, run_analysis)
                    if ai_requested and not data_ai:
                        result["numerical_verification"]["commentary_diagnostic"] = (
                            "Local recommendation · Live AI is unavailable in this deployment." if not live_ai_available()
                            else "Local recommendation · AI access for this dataset is disabled." if not live_scenario_ai
                            else "Local recommendation · This dataset has not been shared with AI."
                        )
                    result["route"] = route
                    result["effective_question"] = question
                    result["question"] = original_question
                    history.append(result)
                    st.rerun()
                except Exception as error:
                    status = getattr(error, "status_code", None)
                    if status == 429:
                        st.error("API quota or rate limit reached. Check your API credits and try again later.")
                    elif status == 401:
                        st.error("API authentication failed. Check your local .env configuration.")
                    elif status == 404:
                        st.error("The configured AI model or endpoint is unavailable.")
                    else:
                        st.error(f"Analysis failed ({type(error).__name__}). Check your configuration and evidence engine.")


    # ==========================================
    # FINANCIAL REPORTS
    # ==========================================

    elif page == "Financial Reports":

        import json
        from datetime import datetime, timezone

        st.title("Financial Reports")
        df = apply_filters(require_data(show_source=False), "report", show_count=False)
        source = st.session_state["file_name"]
        sheet = st.session_state["sheet_name"]
        st.caption(f"{compact_period(', '.join(sorted(df['date'].dt.to_period('M').astype(str).unique())))} · {len(df):,} records · {source}")
        metrics = show_metrics(df)
        audience = st.selectbox("Report audience", ["Executive leadership", "Finance management", "Board of directors"])
        scope = (source, sheet, audience, hashlib.sha256(df.to_csv(index=False).encode()).hexdigest())
        if st.session_state.get("report_scope") != scope:
            st.session_state["report_scope"] = scope
            st.session_state.pop("executive_report", None)
        report_demo = st.session_state.get("scenario_demo_source", False)
        report_ai = dataset_ai_available(demo=report_demo) and (report_demo or st.checkbox(
            "Allow AI to receive aggregated evidence for this uploaded dataset report",
            value=False, key=f"report_consent_{st.session_state.get('dataset_id')}"))
        st.caption("OpenAI receives aggregated evidence and report instructions." if report_ai else "Reports use local calculations and recommendations.")
        if st.button("Generate Executive Report", type="primary"):
            st.session_state.pop("executive_report", None)
            try:
                from finsight.ai_engine import analyze_financial_data
                question = (
                    f"Prepare an executive financial performance report for {audience}. "
                    "Include executive summary, revenue and profitability performance, monthly trends, "
                    "business concentration, financial risks, prioritized management recommendations, and limitations. "
                    "Cite evidence IDs for factual claims. Distinguish observed facts from hypotheses. "
                    "Do not invent budget figures, causal explanations or forecasts. "
                    "If evidence is missing, state that explicitly. Recommendations are proposed actions, not proven outcomes."
                )
                with st.spinner("Preparing financial evidence and executive report..."):
                    result = analyze_financial_data(question, df, source, sheet, enabled=report_ai)
                st.session_state["executive_report"] = {"result": result, "generated": datetime.now(timezone.utc).isoformat()}
            except Exception as error:
                status = getattr(error, "status_code", None)
                if status == 429:
                    st.error("API quota or rate limit reached. Check your credits and retry later.")
                elif status == 401:
                    st.error("API authentication failed. Check your local configuration.")
                else:
                    st.error(f"Report generation failed ({type(error).__name__}).")
        saved = st.session_state.get("executive_report")
        if saved:
            result = saved["result"]
            verification = result["verification"]
            records = [r for r in result["cited_evidence"] if r]
            st.divider()
            st.subheader("Executive Report — Draft for Review")
            metadata = {"source": source, "sheet": sheet, "audience": audience, "generated_utc": saved["generated"], "records": len(df), "period_start": str(df['date'].min()), "period_end": str(df['date'].max()), "model": result["model"], "filters": {k: st.session_state.get(f'report_{k}') for k in ['year','segment','country','product']}, "metrics": metrics, "verification": verification, "numerical_verification": result.get("numerical_verification"), "cited_evidence": records}
            evidence_json = json.dumps(metadata, indent=2, default=str)
            from finsight.workspace_ui import report_kpi_lines
            report = (
                "# FinSight AI | Executive Financial Report\n\n"
                "**Draft — human review required.**\n\n"
                f"Source: {source} | {sheet}\n\nAudience: {audience}\n\nGenerated (UTC): {saved['generated']}\n\n"
                f"Records: {len(df)} | Period: {df['date'].min()} to {df['date'].max()}\n\n"
                "## Calculated financial KPIs\n\nMonetary values use source currency units.\n\n"
                + report_kpi_lines(metrics)
                + "\n\n" + result["answer"]
                + "\n\n## Evidence and verification\n\nCitation ID validity does not establish factual or numerical accuracy.\n\n```json\n"
                + evidence_json + "\n```\n"
            )
            a,b = st.columns(2)
            a.download_button("Download Executive Report", report.encode("utf-8"), "FinSight_Executive_Report.md", "text/markdown")
            b.download_button("Download Supporting Evidence", evidence_json.encode("utf-8"), "FinSight_Report_Evidence.json", "application/json")

            from finsight.skill_workflow import executive_risks
            from finsight.deterministic_report import key_tables
            risks = executive_risks(records)
            st.subheader("Priority findings")
            if risks:
                st.dataframe(pd.DataFrame(risks), hide_index=True, width="stretch")
            else:
                st.caption("No highlights available under the current report rules.")
            st.caption("Priorities are illustrative review rules, not audited materiality thresholds. Segment exposure at or above 75% is flagged high. Lowest margin is a relative ranking, not proof of underperformance.")
            with st.expander("Detailed management recommendations"):
                st.markdown(result.get("commentary") or result["answer"])
                st.caption("Financial findings are calculated locally. Actions are not established causes or guaranteed outcomes.")
            with st.expander("Supporting financial performance"):
                tables = key_tables(records)
                if tables:
                    group = st.selectbox("Financial breakdown", list(tables), key="report_breakdown")
                    frame = pd.DataFrame(tables[group])
                    for field in ("gross_margin", "revenue_share"):
                        if field in frame:
                            frame[field] = frame[field].map(lambda x: f"{x:.2%}" if pd.notna(x) else "N/A")
                    for field in ("revenue", "gross_profit", "revenue_change", "gross_profit_change", "previous_revenue", "current_revenue", "previous_gross_profit", "current_gross_profit"):
                        if field in frame:
                            frame[field] = frame[field].map(lambda x: f"{x:,.2f}" if pd.notna(x) else "N/A")
                    st.dataframe(frame.rename(columns=lambda c: c.replace("_", " ").title()), hide_index=True, width="stretch")
            with st.expander(f"Evidence explorer ({len(records)} records)"):
                categories = sorted({str(r.get("category", "Other")) for r in records})
                category = st.selectbox("Evidence category", ["All categories"] + categories, key="report_evidence_category")
                query = st.text_input("Search evidence ID or title", key="report_evidence_query").strip().casefold()
                matches = [r for r in records if (category == "All categories" or str(r.get("category", "Other")) == category) and query in (str(r["evidence_id"]) + " " + str(r["title"])).casefold()]
                if matches:
                    labels = {f"[{r['evidence_id']}] {r['title']}": r for r in matches}
                    selected = st.selectbox("Evidence record", list(labels), key="report_evidence_record")
                    record = labels[selected]
                    from finsight.workspace_ui import evidence_rows
                    st.markdown(f"**{record['title']}**")
                    st.caption(str(record.get('methodology', 'Not supplied')))
                    st.dataframe(pd.DataFrame(evidence_rows(record.get('values', {}), record.get('category'))), hide_index=True, width="stretch")
                    origin = record.get('source', {})
                    st.caption(f"Source: {origin.get('file', 'Not supplied')} | Worksheet: {origin.get('worksheet', 'Not supplied')}")
                    with st.expander("Raw evidence and source row references"):
                        st.json(record, expanded=False)
                else:
                    st.caption("No matching evidence records.")
            check = result.get("numerical_verification", {})
            st.caption(f"{len(verification['valid_citations'])} valid evidence IDs · {len(verification['invalid_citations'])} invalid IDs · {result['total_tokens']} reported tokens · Human review required")
            if not verification["passed"]:
                st.warning("Citation ID verification failed. Review before using this report.")
            with st.expander("Verification and methodology"):
                if result.get("active_skills"):
                    st.caption("Active financial skills: " + ", ".join(result["active_skills"]))
                show_numerical_verification(result)
                st.caption("Citation ID checks do not establish numerical accuracy or factual support. Human review is required.")
                st.caption(f"Model: {result['model']} | Final request token count only")
