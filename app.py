
import hashlib
import os
from finsight.demo_dataset import load_demo_state

# Public-safe default; local live AI requires explicit opt-in.
os.environ.setdefault("FINSIGHT_LIVE_AI", "0")
import io

import pandas as pd
import streamlit as st
import plotly.express as px

from finsight.data_validator import (
    detect_columns,
    validate_financial_data,
    COLUMN_ALIASES
)

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


# ==========================================
# HELPER FUNCTIONS
# ==========================================

from finsight.ui_theme import apply_theme
apply_theme()

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


def show_executive_analysis(result):
    if result.get('numerical_verification', {}).get('mode') != 'deterministic' or 'commentary' not in result:
        st.markdown(result['answer'])
        return
    from finsight.deterministic_report import report_groups, build_facts, key_tables, deterministic_insights
    from types import SimpleNamespace
    records = [r for r in result.get('cited_evidence', []) if r]
    total = next((r for r in records if r['title'] == 'Total financial change'), None)
    executive = 'executive-reporting' in result.get('active_skills', [])
    if result.get('direct_answer'):
        st.subheader('Direct financial answer')
        st.markdown(result['direct_answer'])
    if result.get('local_plan'):
        st.subheader('Local strategic action plan')
        st.markdown(result['commentary'])
    if result.get('numerical_verification', {}).get('generated_synthesis'):
        st.subheader('AI financial answer')
        st.markdown(result['commentary'].split('\n\n**Calculated supporting findings**', 1)[0])
        st.caption('AI interpretation and proposed actions; not independently verified for factual entailment.')
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
    if not executive:
        st.subheader('Calculated findings and management recommendations')
        st.markdown(result['commentary'].split('\n\n**Calculated supporting findings**\n\n', 1)[-1] or 'Commentary unavailable; review the calculated evidence.')
        st.caption('Financial findings are calculated locally. Supporting findings and fallback actions are rule-based. Actions are not established causes or guaranteed outcomes.')
    with st.expander('Complete calculated financial evidence'):
        facts = build_facts(SimpleNamespace(records=records))
        for group, rows in report_groups(records).items():
            st.markdown('**' + group + '**')
            table = [{'Evidence': r['evidence_id'], 'Title': r['title'], **{k.split('.',1)[1].replace('_',' ').title(): val for k,val in facts.items() if k.startswith(r['evidence_id']+'.')}} for r in rows]
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
        "validated_data",
        "ai_scope",
        "ai_history"
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


def require_data():

    if "validated_data" not in st.session_state:

        st.warning(
            "Upload and validate a financial dataset first."
        )

        st.stop()

    st.caption(
        f"Source: {st.session_state['file_name']} | "
        f"{st.session_state['sheet_name']}"
    )

    return st.session_state["validated_data"].copy()


def apply_filters(df, prefix):

    with st.expander("Analysis filters", expanded=False):
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

    st.caption(
        f"Analyzing {len(df):,} financial records."
    )

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


def show_table(df):

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
        except Exception:
            st.warning("Sample data unavailable. Upload a financial file to continue.")

with st.sidebar:

    st.title("FinSight AI")

    st.caption(
        "Evidence-Driven Financial Intelligence"
    )

    st.divider()

    pages = {
        "Overview": ":material/dashboard:",
        "Data Upload": ":material/upload_file:",
        "Financial Analysis": ":material/monitoring:",
        "Performance Drivers": ":material/insights:",
        "Anomaly Detection": ":material/warning:",
        "AI Copilot": ":material/auto_awesome:",
        "Financial Reports": ":material/description:",
    }
    if st.session_state.get("workspace_page") not in pages:
        st.session_state["workspace_page"] = "Overview"
    st.caption("WORKSPACE")
    for name, icon in pages.items():
        if st.button(name, icon=icon, key=f"nav_{name}", width="stretch",
                     type="primary" if st.session_state["workspace_page"] == name else "secondary"):
            st.session_state["workspace_page"] = name
            st.rerun()
    page = st.session_state["workspace_page"]

    st.divider()

    if "validated_data" in st.session_state:

        st.success("Financial data validated")

        st.caption(
            st.session_state.get("file_name", "")
        )

    elif "financial_data" in st.session_state:

        st.warning("Data requires validation")

    else:

        st.caption("No active dataset")

    st.divider()

    if st.button("Load sample dataset"):
        clear_validation()
        st.session_state.update(load_demo_state())
        st.session_state.pop("executive_report", None)
        st.rerun()
    if os.getenv("FINSIGHT_LIVE_AI") != "1":
        st.caption("Public demo: local analysis only; no API calls.")
    st.caption("Version 0.17.0")
    st.caption("Independent Portfolio Project")


# ==========================================
# OVERVIEW
# ==========================================

if page == "Overview":

    st.caption("WORKSPACE / OVERVIEW")
    st.title("Financial overview")
    st.write("Monitor business performance and uncover financial insights.")

    if "validated_data" in st.session_state:
        df = st.session_state["validated_data"]
        st.caption(f"{len(df):,} validated records · {st.session_state.get('file_name', 'Active dataset')}")
        show_metrics(df)
        st.caption("Metrics reflect all validated records.")
        monthly = calculate_monthly_performance(df)
        left, right = st.columns([2, 1])
        with left:
            with st.container(border=True):
                st.subheader("Revenue performance")
                fig = px.bar(monthly, x="month", y="revenue", labels={"month": "Month", "revenue": "Revenue"})
                fig.update_traces(marker_color="#426E9B")
                fig.update_yaxes(tickprefix="$")
                st.plotly_chart(style_chart(fig), width="stretch")
        with right:
            with st.container(border=True):
                st.subheader("Gross margin")
                fig = px.line(monthly, x="month", y="gross_margin", markers=True, labels={"month": "Month", "gross_margin": "Margin"})
                fig.update_traces(line_color="#16967A")
                fig.update_yaxes(tickformat=".0%")
                st.plotly_chart(style_chart(fig), width="stretch")
    else:
        st.info("Upload and validate a dataset to view your financial dashboard.")

    st.subheader("Explore your workspace")
    cards = [
        ("Financial Analysis", "Explore revenue, costs and profitability."),
        ("Performance Drivers", "Understand contributors to financial changes."),
        ("Anomaly Detection", "Review unusual movements and margin compression."),
        ("AI Copilot", "Ask evidence-backed financial questions."),
    ]
    for offset in (0, 2):
        for col, (name, description) in zip(st.columns(2), cards[offset:offset+2]):
            with col:
                with st.container(border=True):
                    st.markdown(f"**{name}**")
                    st.write(description)
                    if st.button(f"Open {name}", key=f"overview_{name}", width="stretch"):
                        st.session_state["workspace_page"] = name
                        st.rerun()
    with st.expander("Calculation methodology"):
        st.write("Financial calculations are performed by a deterministic Python engine, independently of the AI model.")


# ==========================================
# DATA UPLOAD
# ==========================================

elif page == "Data Upload":

    st.title("Financial Data Upload")

    uploaded_file = st.file_uploader(
        "Choose a financial data file",
        type=["xlsx", "csv"]
    )

    if uploaded_file is not None:

        try:

            file_bytes = uploaded_file.getvalue()

            file_hash = hashlib.sha256(
                file_bytes
            ).hexdigest()

            if uploaded_file.name.lower().endswith(".csv"):

                selected_sheet = "CSV"

                df = pd.read_csv(
                    io.BytesIO(file_bytes)
                )

            else:

                workbook = pd.ExcelFile(
                    io.BytesIO(file_bytes)
                )

                selected_sheet = st.selectbox(
                    "Select worksheet",
                    workbook.sheet_names,
                    key=f"sheet_{file_hash}"
                )

                df = pd.read_excel(
                    workbook,
                    sheet_name=selected_sheet
                )

            df.columns = [
                str(column).strip()
                for column in df.columns
            ]

            dataset_id = (
                file_hash + ":" + selected_sheet
            )

            if (
                st.session_state.get("dataset_id")
                != dataset_id
            ):

                clear_validation()

            st.session_state["dataset_id"] = dataset_id
            st.session_state["financial_data"] = df
            st.session_state["file_name"] = uploaded_file.name
            st.session_state["sheet_name"] = selected_sheet

            st.success("File loaded successfully!")

        except Exception as error:

            clear_validation()

            st.session_state.pop(
                "financial_data", None
            )

            st.error(f"Unable to read file: {error}")

    if "financial_data" not in st.session_state:

        st.info("Upload a financial dataset to continue.")

        st.stop()

    df = st.session_state["financial_data"]

    dataset_id = st.session_state["dataset_id"]

    st.caption(
        f"Active source: "
        f"{st.session_state['file_name']} | "
        f"{st.session_state['sheet_name']}"
    )

    cols = st.columns(3)

    cols[0].metric("Rows", len(df))

    cols[1].metric("Columns", len(df.columns))

    cols[2].metric(
        "Missing Values",
        int(df.isna().sum().sum())
    )

    with st.expander("Raw Data Preview"):

        st.dataframe(
            df.head(100),
            width="stretch"
        )

    if df.columns.duplicated().any():

        clear_validation()

        st.error("Duplicate column names detected.")

        st.stop()

    st.divider()

    st.subheader("Financial Column Mapping")

    detected = detect_columns(df)

    options = [None] + list(df.columns)

    required = ["revenue", "cogs", "date"]

    labels = {
        "revenue": "Revenue",
        "cogs": "Cost of Goods Sold",
        "date": "Transaction Date",
        "reported_profit": "Reported Gross Profit",
        "segment": "Business Segment",
        "country": "Country / Geography",
        "product": "Product",
        "discounts": "Discounts",
        "gross_sales": "Gross Sales",
        "units_sold": "Units Sold",
        "budget_revenue": "Budget Revenue"
    }

    mapping = {}

    def render_mapping(field):

        default = detected.get(field)

        selected = st.selectbox(
            labels.get(field, field),
            options,
            index=(
                options.index(default)
                if default in options
                else 0
            ),
            format_func=lambda x: (
                "Not mapped" if x is None else str(x)
            ),
            key=f"{dataset_id}_{field}"
        )

        if selected is not None:

            mapping[field] = selected

    st.markdown("#### Required Fields")

    cols = st.columns(3)

    for i, field in enumerate(required):

        with cols[i]:

            render_mapping(field)

    with st.expander(
        "Optional Financial Fields",
        expanded=True
    ):

        cols = st.columns(3)

        optional = [
            field for field in COLUMN_ALIASES
            if field not in required
        ]

        for i, field in enumerate(optional):

            with cols[i % 3]:

                render_mapping(field)

    previous = st.session_state.get(
        "validation_result"
    )

    if (
        previous is not None
        and previous["mapping"] != mapping
    ):

        clear_validation()

    if st.button(
        "Validate Financial Data",
        type="primary",
        width="stretch"
    ):

        clear_validation()

        if len(set(mapping.values())) != len(mapping):

            st.error(
                "A source column cannot be mapped "
                "to multiple financial fields."
            )

        else:

            result = validate_financial_data(
                df,
                mapping=mapping
            )

            st.session_state["validation_result"] = result

            if result["valid"]:

                st.session_state["validated_data"] = (
                    result["data"]
                )

    if "validation_result" in st.session_state:

        result = st.session_state["validation_result"]

        st.divider()

        st.subheader("Validation Results")

        cols = st.columns(3)

        cols[0].metric(
            "Mapped Fields",
            len(result["mapping"])
        )

        cols[1].metric(
            "Errors",
            len(result["errors"])
        )

        cols[2].metric(
            "Warnings",
            len(result["warnings"])
        )

        for error in result["errors"]:

            st.error(error)

        for warning in result["warnings"]:

            st.warning(warning)

        if result["valid"]:

            st.success(
                "Financial data passed validation."
            )

            show_table(result["data"].head(100))

            st.download_button(
                "Download Validated Dataset",
                result["data"].to_csv(
                    index=False
                ).encode("utf-8"),
                "validated_financial_data.csv",
                "text/csv"
            )


# ==========================================
# FINANCIAL ANALYSIS
# ==========================================

elif page == "Financial Analysis":

    st.title("Financial Analysis")

    df = require_data()

    df = apply_filters(df, "analysis")

    st.divider()

    metrics = show_metrics(df)

    monthly = calculate_monthly_performance(df)

    st.divider()

    st.subheader("Monthly Financial Performance")

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
            style_chart(fig),
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
            style_chart(fig),
            width="stretch"
        )

    left, right = st.columns(2)

    with left:

        fig = px.bar(
            monthly,
            x="month",
            y="revenue_growth",
            title="Month-over-Month Revenue Growth"
        )

        fig.update_traces(marker_color=["#94A3B8" if pd.isna(v) else "#16967A" if v >= 0 else "#B91C1C" for v in monthly["revenue_growth"]])

        fig.update_yaxes(tickformat=".0%")

        st.plotly_chart(
            style_chart(fig),
            width="stretch"
        )

    with right:

        fig = px.line(
            monthly,
            x="month",
            y="gross_margin",
            markers=True,
            title="Monthly Gross Margin"
        )

        fig.update_yaxes(tickformat=".0%")

        st.plotly_chart(
            style_chart(fig),
            width="stretch"
        )

    st.subheader("Monthly Financial Summary")

    show_table(monthly)

    st.divider()

    st.subheader("Calculation Evidence")

    with st.expander("Show Financial Calculations"):

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

    st.title("Financial Performance Drivers")

    st.write(
        "Investigate profitability, revenue concentration, "
        "and contributors to financial changes."
    )

    df = require_data()

    df = apply_filters(df, "drivers")

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

    st.divider()

    dimension = st.selectbox(
        "Analyze Performance By",
        dimensions,
        format_func=str.title
    )

    breakdown = calculate_breakdown(
        df,
        dimension
    )

    st.subheader(
        f"{dimension.title()} Performance"
    )

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
            style_chart(fig),
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
            style_chart(fig),
            width="stretch"
        )

    show_table(breakdown)

    st.divider()

    st.subheader("Revenue Change Investigation")

    st.write(
        "Compare two months and identify "
        "which business categories contributed "
        "to the revenue change."
    )

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
        style_chart(fig),
        width="stretch"
    )

    show_table(drivers)

    st.subheader("Calculated Financial Findings")

    negative = drivers[
        drivers["revenue_change"] < 0
    ].sort_values("revenue_change")

    positive = drivers[
        drivers["revenue_change"] > 0
    ].sort_values(
        "revenue_change",
        ascending=False
    )

    if not negative.empty:

        largest = negative.iloc[0]

        st.warning(
            f"Largest negative contributor: "
            f"{largest[dimension]} — "
            f"{format_money(largest['revenue_change'])}"
        )

    if not positive.empty:

        largest = positive.iloc[0]

        st.success(
            f"Largest positive contributor: "
            f"{largest[dimension]} — "
            f"{format_money(largest['revenue_change'])}"
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

    st.title("Financial Anomaly Detection")

    df = require_data()

    df = apply_filters(df, "anomalies")

    anomalies = detect_anomalies(df)

    high = [
        item for item in anomalies
        if item["severity"] == "High"
    ]

    review = [
        item for item in anomalies
        if item["severity"] == "Review"
    ]

    st.divider()

    cols = st.columns(3)

    cols[0].metric(
        "Total Flags",
        len(anomalies)
    )

    cols[1].metric(
        "High Priority",
        len(high)
    )

    cols[2].metric(
        "Review Required",
        len(review)
    )

    st.caption(
        "Rule-based financial flags, "
        "not statistical or AI predictions."
    )

    with st.expander("Detection Methodology"):

        st.write(
            "Revenue decline: 20% or more "
            "month over month."
        )

        st.write(
            "Revenue increase: 20% or more "
            "month over month."
        )

        st.write(
            "Margin compression: decline of "
            "3 percentage points or more."
        )

        st.write(
            "Missing months are not treated as zero."
        )

    st.divider()

    if not anomalies:

        st.success(
            "No anomalies detected under "
            "the current business rules."
        )

    else:

        st.subheader("Detected Financial Flags")

        for item in anomalies:

            message = (
                f"{item['period']} | "
                f"{item['category']}: "
                f"{item['description']}"
            )

            if item["severity"] == "High":

                st.error(message)

            else:

                st.warning(message)

        st.subheader("Anomaly Register")

        anomaly_df = pd.DataFrame(anomalies)

        show_table(anomaly_df)

        st.download_button(
            "Download Anomaly Register",
            anomaly_df.to_csv(
                index=False
            ).encode("utf-8"),
            "financial_anomalies.csv",
            "text/csv"
        )

    st.divider()

    monthly = calculate_monthly_performance(df)

    fig = px.bar(
        monthly,
        x="month",
        y="revenue_growth",
        title="Monthly Revenue Growth and Thresholds"
    )

    fig.update_traces(marker_color=["#94A3B8" if pd.isna(v) else "#16967A" if v >= 0 else "#B91C1C" for v in monthly["revenue_growth"]])

    fig.update_yaxes(tickformat=".0%")

    fig.add_hline(
        y=0.20,
        line_dash="dash",
        line_color="#16967A",
        annotation_text="+20% threshold"
    )

    fig.add_hline(
        y=-0.20,
        line_dash="dash",
        line_color="#B91C1C",
        annotation_text="-20% threshold"
    )

    st.plotly_chart(
        style_chart(fig),
        width="stretch"
    )


# ==========================================
# AI COPILOT
# ==========================================

elif page == "AI Copilot":

    st.title("AI Financial Copilot")
    st.caption("Evidence-backed financial intelligence")
    df = apply_filters(require_data(), "copilot")
    source = st.session_state["file_name"]
    sheet = st.session_state["sheet_name"]
    st.info("Financial calculations are performed locally. Aggregated evidence, source labels and your question are sent to OpenAI when you submit a question. Financial figures are rendered locally; no additional AI verification request is made. Use only data you are authorized to share." if os.getenv("FINSIGHT_LIVE_AI") == "1" else "Public demo: financial calculations and rule-based recommendations run locally. No data is sent to OpenAI and no API key is required.")

    with st.expander("Analysis mode and comparison settings", expanded=False):
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
            suggestions = [f"Explain the revenue change from {previous} to {current} by {dimension}.", "Which contributors offset the decline?", "What should management investigate next?"]
        else:
            suggestions = ["Summarize financial performance.", "Identify profitability risks supported by the evidence.", "Which business categories contribute most to revenue?"]

    scope = (st.session_state.get("dataset_id"), source, sheet, mode, dimension, previous, current, hashlib.sha256(df.to_csv(index=False).encode()).hexdigest())
    if st.session_state.get("ai_scope") != scope:
        st.session_state["ai_scope"] = scope
        st.session_state["ai_history"] = []
    history = st.session_state["ai_history"]
    if st.button("Clear conversation"):
        history.clear()
        st.rerun()
    st.caption("Follow-up ranking questions can reuse the previous dimension, metric and reporting year. Changing filters or clearing the conversation resets context. Resolved questions and current aggregated evidence are sent to OpenAI in live mode.")
    suggestion = None
    if not history:
        st.subheader("What would you like to analyze?")
        st.caption("Start with a suggested question or enter your own below.")
        for i, (col, prompt) in enumerate(zip(st.columns(3), suggestions)):
            with col:
                with st.container(border=True):
                    if st.button(prompt, key=f"suggestion_{i}", width="stretch"):
                        suggestion = prompt
    else:
        with st.expander("Suggested questions"):
            for i, (col, prompt) in enumerate(zip(st.columns(3), suggestions)):
                if col.button(prompt, key=f"suggestion_{i}", width="stretch"):
                    suggestion = prompt
    suggested_submit = suggestion is not None

    def render_answer(result, answer_index):
        if "scenario" in result:
            scenario = result["scenario"]
            st.subheader("Financial scenario — illustrative, not a forecast")
            st.caption("Effective reporting months: " + scenario["period"])
            st.caption(f"Baseline: {scenario['records']} selected records. Monetary values in source currency units. No AI request sent.")
            for case in scenario["cases"]:
                st.markdown("**" + case["label"] + "**")
                table = []
                for metric, base in scenario["baseline"].items():
                    projected = case["metrics"][metric]
                    table.append({"Metric": metric, "Baseline": base, "Projected": projected, "Change (pp for margin)": projected-base if projected is not None and base is not None else None})
                st.dataframe(pd.DataFrame(table).round(2), hide_index=True)
            st.caption("Assumptions are illustrative. No demand, capacity, stranded costs, taxes or operating expenses are modeled. Segment removal assumes all recorded segment COGS are avoidable.")
            return
        if result.get("effective_question") and result["effective_question"] != result["question"]:
            st.caption("Interpreted follow-up: " + result["effective_question"])
        if result.get("effective_period"):
            st.caption("Effective reporting months: " + result["effective_period"])
        if result.get("route"):
            route = result["route"]
            st.caption(f"Selected analysis: {route['mode']}")
            st.write(route.get("reason", ""))
            if route.get("previous_month") and route.get("current_month"):
                st.write(f"Dimension: {route['dimension']} | {route['previous_month']} to {route['current_month']}")
        if result.get("investigation"):
            with st.expander("Deterministic reconciliation", expanded=False):
                inv = result["investigation"]
                st.caption(inv["note"])
                st.dataframe([{"Dimension": d, "Net revenue change": round(b["net_change"], 2), "Reconciliation difference": round(b["reconciliation_difference"], 2)} for d,b in inv["dimensions"].items()])
        show_executive_analysis(result)
        verification = result["verification"]
        check = result.get("numerical_verification", {})
        if not verification["passed"]:
            st.warning("Citation ID verification did not pass. Review this answer before relying on it.")
        if check.get("mode") == "deterministic":
            if not check.get("controlled_actions") and (not check.get("commentary_accepted") or check.get("commentary_diagnostic")):
                st.warning("Some AI commentary was withheld or rejected. Review the verification details.")
        elif check.get("extraction_status") != "completed" or any(check.get(k) for k in ("failed", "unverified", "coverage_warnings", "errors")):
            st.warning("Numerical verification is incomplete or requires review.")
        st.caption("Citation ID checks do not establish factual accuracy; financial values are not independently audited.")
        records = [record for record in result["cited_evidence"] if record]
        with st.expander(f"Evidence & verification details ({len(records)} records)", expanded=False):
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
        with st.chat_message("user"):
            st.write(item["question"])
        with st.chat_message("assistant"):
            render_answer(item, answer_index)

    typed = st.chat_input("Ask a question about your selected financial data")
    question = suggestion if suggested_submit else typed
    if question and question.strip():
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            try:
                from finsight.ai_engine import analyze_financial_data, investigate_revenue_change
                from finsight.question_router import route_question
                original_question = question
                from finsight.scenario import is_scenario, run_scenario
                if mode == "Automatic" and is_scenario(question):
                    try:
                        scenario = run_scenario(question, df)
                    except ValueError as exc:
                        st.warning(str(exc))
                        st.info("No AI request was sent.")
                        st.stop()
                    result = {"question": question, "scenario": scenario, "route": {"mode": "scenario"}}
                    history.append(result)
                    render_answer(result, len(history)-1)
                    st.stop()
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
                if route["mode"] == "revenue_investigation" and route["dimension"] not in df.columns:
                    st.warning("The requested business dimension is not mapped in this dataset. No AI request was sent.")
                    st.stop()
                with st.spinner("Calculating evidence and generating analysis..."):
                    if route["mode"] == "multi_investigation":
                        from finsight.investigation_bridge import run_investigation
                        result = run_investigation(question, df, route["previous_month"], route["current_month"], source, sheet)
                    elif route["mode"] == "revenue_investigation":
                        result = investigate_revenue_change(question, df, route["dimension"], route["current_month"], route["previous_month"], source, sheet)
                    else:
                        result = analyze_financial_data(question, df, source, sheet, route=route)
                result["route"] = route
                result["effective_question"] = question
                result["question"] = original_question
                history.append(result)
                render_answer(result, len(history) - 1)
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

    st.title("Executive Financial Reports")
    st.caption("Generate management-ready reports from validated financial evidence.")
    df = apply_filters(require_data(), "report")
    source = st.session_state["file_name"]
    sheet = st.session_state["sheet_name"]
    metrics = show_metrics(df)
    st.divider()
    audience = st.selectbox("Report audience", ["Executive leadership", "Finance management", "Board of directors"])
    st.info("Generating a report sends aggregated financial evidence, source labels and report instructions to OpenAI. Financial figures are rendered locally; no additional AI verification request is made. Use only data you are authorized to share." if os.getenv("FINSIGHT_LIVE_AI") == "1" else "Public demo: financial calculations and rule-based recommendations run locally. No data is sent to OpenAI and no API key is required.")
    scope = (source, sheet, audience, hashlib.sha256(df.to_csv(index=False).encode()).hexdigest())
    if st.session_state.get("report_scope") != scope:
        st.session_state["report_scope"] = scope
        st.session_state.pop("executive_report", None)
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
                result = analyze_financial_data(question, df, source, sheet)
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
        if result.get("active_skills"):
            st.caption("Active financial skills: " + ", ".join(result["active_skills"]))
        show_executive_analysis(result)
        show_numerical_verification(result)
        if verification["passed"]:
            st.success("Cited evidence IDs passed registry verification.")
        else:
            st.warning("Citation ID verification failed. Review before using this report.")
        st.caption("Citation ID checks do not establish numerical accuracy or factual support. Human review is required.")
        cols = st.columns(3)
        cols[0].metric("Valid IDs", len(verification["valid_citations"]))
        cols[1].metric("Invalid IDs", len(verification["invalid_citations"]))
        cols[2].metric("Reported tokens", result["total_tokens"])
        st.caption(f"Model: {result['model']} | Final request token count only")
        for record in records:
            with st.expander(f"[{record['evidence_id']}] {record['title']}"):
                st.write(record)
        metadata = {"source": source, "sheet": sheet, "audience": audience, "generated_utc": saved["generated"], "records": len(df), "period_start": str(df['date'].min()), "period_end": str(df['date'].max()), "model": result["model"], "filters": {k: st.session_state.get(f'report_{k}') for k in ['year','segment','country','product']}, "metrics": metrics, "verification": verification, "numerical_verification": result.get("numerical_verification"), "cited_evidence": records}
        evidence_json = json.dumps(metadata, indent=2, default=str)
        report = (
            "# FinSight AI | Executive Financial Report\n\n"
            "**AI-generated draft — human review required.**\n\n"
            f"Source: {source} | {sheet}\n\nAudience: {audience}\n\nGenerated (UTC): {saved['generated']}\n\n"
            f"Records: {len(df)} | Period: {df['date'].min()} to {df['date'].max()}\n\n"
            "## Calculated financial KPIs\n\n"
            + "\n".join(f"- {k}: {v}" for k,v in metrics.items())
            + "\n\n" + result["answer"]
            + "\n\n## Evidence and verification\n\nCitation ID validity does not establish factual or numerical accuracy.\n\n```json\n"
            + evidence_json + "\n```\n"
        )
        a,b = st.columns(2)
        a.download_button("Download Executive Report", report.encode("utf-8"), "FinSight_Executive_Report.md", "text/markdown")
        b.download_button("Download Supporting Evidence", evidence_json.encode("utf-8"), "FinSight_Report_Evidence.json", "application/json")
