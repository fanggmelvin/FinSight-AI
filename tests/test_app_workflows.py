from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import asyncio
import sys

import pandas as pd
import pytest

from streamlit.testing.v1 import AppTest


@pytest.fixture(autouse=True)
def local_streamlit_runner(monkeypatch):
    # The synchronous AppTest runner does not need network I/O. Windows
    # constructs its wakeup socket via loopback, which can hang in a sandbox.
    if sys.platform == "win32":
        from streamlit.testing.v1 import local_script_runner

        class InProcessLoop(asyncio.SelectorEventLoop):
            def _make_self_pipe(self):
                pass

            def _close_self_pipe(self):
                pass

        monkeypatch.setattr(local_script_runner, "asyncio", SimpleNamespace(new_event_loop=InProcessLoop))


def test_demo_workspace_workflows(monkeypatch):
    monkeypatch.setenv("FINSIGHT_LIVE_AI", "0")
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=30).run()

    def check_page():
        assert not [item.message for item in app.exception]
        assert not [item.value for item in app.error]

    check_page()
    assert app.button(key="nav_upload_dataset").label == "Change dataset"
    app.button(key="nav_upload_dataset").click().run()
    check_page()
    assert app.session_state["workspace_page"] == "Data Upload"
    for page in ("Overview", "Financial Analysis", "Performance Drivers", "Anomaly Detection",
                 "AI Copilot", "Data Upload", "Scenario Modeling"):
        key = "nav_upload_dataset" if page == "Data Upload" else f"nav_{page}"
        app.button(key=key).click().run()
        check_page()
        assert app.session_state["workspace_page"] == page

    revenue = app.metric[0].value
    app.slider(key="sim_rev").set_value(20).run()
    check_page()
    assert app.metric[0].value != revenue
    app.button(key="sim_reset").click().run()
    check_page()
    assert app.metric[0].value == revenue

    app.button(key="nav_Financial Reports").click().run()
    next(button for button in app.button if button.label == "Generate Executive Report").click().run()
    check_page()
    assert {"Download Executive Report", "Download Supporting Evidence"} <= {
        button.label for button in app.get("download_button")
    }


def test_excel_upload_replacement_and_recovery(monkeypatch):
    monkeypatch.setenv("FINSIGHT_LIVE_AI", "0")
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=30).run()
    app.button(key="nav_upload_dataset").click().run()

    def upload(rows, filename):
        stream = BytesIO()
        pd.DataFrame(rows).to_excel(stream, index=False, header=False)
        app.file_uploader[0].set_value((filename, stream.getvalue(), "application/octet-stream")).run()
        assert not app.exception
        assert not app.error

    def click(label):
        next(button for button in app.button if button.label == label).click().run()
        assert not app.exception
        assert not app.error

    upload([["Transactions", None, None], ["Date", "Revenue", "COGS"],
            [None, None, None], ["2024-01-01", 120, 70]], "transactions.xlsx")
    assert app.session_state["workspace_page"] == "Overview"
    assert app.session_state["validated_data"]["revenue"].sum() == 120
    assert app.session_state["validated_data"]["source_row"].tolist() == [4]
    app.button(key="nav_AI Copilot").click().run()
    app.radio(key="copilot_mode_selector").set_value("Workbook").run()
    assert app.session_state["workspace_page"] == "AI Copilot"
    assert not any(button.label == "Workbook chat" for button in app.sidebar.button)
    assert len(app.chat_input) == 1
    app.chat_input[0].set_value("Read B4").run()
    assert app.chat_message[-1].text[0].value.endswith("B4: 120")
    assert any(panel.label == "Source cells" for panel in app.expander)
    assert len(app.chat_message) == 2
    app.chat_input[0].set_value("Read C4").run()
    assert app.chat_message[-1].text[0].value.endswith("C4: 70")
    assert len(app.chat_message) == 4
    source = app.session_state["chat_workbook"]
    app.session_state[f"source_cells_{source['id']}_{source['selected']}__1"] = True
    app.run()
    assert not app.exception
    assert app.chat_message[-1].dataframe[0].value.loc[4, "C"] == "70"
    assert len(app.chat_message) == 4

    app.radio(key="copilot_mode_selector").set_value("Financial analysis").run()
    assert not app.exception and not app.error
    assert len(app.chat_input) == 1
    assert app.chat_input[0].key == "copilot_financial_question"
    app.radio(key="copilot_mode_selector").set_value("Workbook").run()
    assert app.chat_message[-1].text[0].value.endswith("C4: 70")
    assert len(app.chat_message) == 4
    app.button(key="nav_upload_dataset").click().run()

    identity = app.session_state["dataset_id"]
    app.file_uploader[0].set_value(("broken.xlsx", b"invalid", "application/octet-stream")).run()
    assert app.error and not app.exception
    assert app.session_state["dataset_id"] == identity
    assert app.session_state["validated_data"]["revenue"].sum() == 120

    upload([["(in $ millions)", None, None], ["Fiscal Year", "2023A", "2024E"], ["Revenue", 100, 130],
            ["COGS", 70, 80]], "annual.xlsx")
    assert app.session_state["workspace_page"] == "Overview"
    assert app.session_state["validated_data"]["Revenue"].tolist() == [100_000_000]
    assert app.session_state["annual_data"]["Period type"].tolist() == ["Actual", "Forecast"]
    for page in ("Financial Analysis", "Performance Drivers", "Anomaly Detection",
                 "AI Copilot", "Scenario Modeling", "Financial Reports"):
        app.button(key=f"nav_{page}").click().run()
        assert not app.exception
        assert not app.error
    assert any(button.label == "Download annual report" for button in app.get("download_button"))
    app.button(key="nav_AI Copilot").click().run()
    assert len(app.chat_input) == 1
    app.chat_input[0].set_value("What was revenue in FY2024?").run()
    assert "Revenue for FY2024 (forecast) was $130 million." in app.chat_message[-1].get("html")[0].proto.body
    app.button(key="nav_upload_dataset").click().run()
    click("Restore demo dataset")
    assert app.session_state["dataset_id"] == "bundled-financial-sample-v1"


def test_uploads_reach_overview_or_copilot_without_confirmation(monkeypatch):
    monkeypatch.setenv("FINSIGHT_LIVE_AI", "0")
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=30).run()

    def upload(name, data):
        app.button(key="nav_upload_dataset").click().run()
        app.file_uploader[0].set_value((name, data, "application/octet-stream")).run()
        assert not app.error and not app.exception

    upload("transactions.csv", b"Date,Revenue,COGS\n2024-01-01,100,55")
    assert app.session_state["workspace_page"] == "Overview"
    assert app.session_state["validated_data"]["revenue"].tolist() == [100]

    upload("operations.csv", b"Project,Owner,Amount\nApollo,Casey,20")
    assert app.session_state["workspace_page"] == "AI Copilot"
    assert "validated_data" not in app.session_state
    app.chat_input[0].set_value("Who is the owner of Apollo?").run()
    assert app.chat_message[-1].text[0].value == "Owner: Casey (CSV!B2)"

    workbook = BytesIO()
    pd.DataFrame([["Fiscal Year", 2023, 2024], ["Net revenue", 100, 130], ["COGS", 70, 80]]).to_excel(
        workbook, index=False, header=False)
    upload("unmarked-annual.xlsx", workbook.getvalue())
    assert app.session_state["workspace_page"] == "Overview"
    assert app.session_state["annual_data"]["Period type"].tolist() == ["Unclassified", "Unclassified"]
    assert app.session_state["annual_data"]["Currency"].tolist() == ["Unspecified", "Unspecified"]
    app.button(key="nav_AI Copilot").click().run()
    app.chat_input[0].set_value("What was revenue in FY2023?").run()
    message = app.chat_message[-1]
    assert "Net revenue for FY2023 was 100 in source units." in message.get("html")[0].proto.body
    assert message.text[0].value == "Sheet1!B2 · Source value 100 (units unspecified)"
    assert "doesn’t identify FY2023" in message.caption[0].value
    source = app.session_state["chat_workbook"]
    dataset = app.session_state["dataset_id"]
    app.session_state[f"source_cells_{source['id']}_Sheet1_{dataset}_0"] = True
    app.run()
    values = app.chat_message[-1].dataframe[0].value.iloc[0]
    assert values.to_dict() == {"Row label (A2)": "Net revenue", "Fiscal year (B1)": 2023, "Source value (B2)": 100}
    next(button for button in app.button if button.label == "Compare with FY2024").click().run()
    assert "FY2023 to FY2024 net revenue change: 30.00 in source units (+30.00%)." in app.chat_message[-1].text[0].value
    app.button(key="nav_upload_dataset").click().run()
    next(box for box in app.selectbox if box.label == "Last actual fiscal year").select(2023).run()
    assert app.session_state["annual_data"]["Period type"].tolist() == ["Actual", "Forecast"]
    app.button(key="nav_Overview").click().run()
    app.button(key="nav_upload_dataset").click().run()
    assert app.session_state["annual_data"]["Period type"].tolist() == ["Actual", "Forecast"]


def test_workbook_ai_requires_deployment_opt_in_and_user_consent(monkeypatch):
    monkeypatch.setenv("FINSIGHT_LIVE_AI", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    monkeypatch.setenv("FINSIGHT_AI_UPLOADS", "0")
    calls = []

    def create(**request):
        calls.append(request)
        return SimpleNamespace(output_text='[{"text":"The worksheet identifies the project lead.","refs":["E0"]}]')

    monkeypatch.setattr("finsight.ai_engine.get_client", lambda: SimpleNamespace(responses=SimpleNamespace(create=create)))
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=30).run()
    app.button(key="nav_upload_dataset").click().run()
    app.file_uploader[0].set_value(("operations.csv", b"Project,Owner,Amount\nApollo,Casey,20", "text/csv")).run()
    consent = "Use AI interpretation for this workbook"
    assert not any(box.label == consent for box in app.checkbox)
    app.chat_input[0].set_value("Who is the owner of Apollo?").run()
    assert not calls
    monkeypatch.setenv("FINSIGHT_AI_UPLOADS", "1")
    app.run()
    app.chat_input[0].set_value("Who is the owner of Apollo?").run()
    assert not calls
    next(box for box in app.checkbox if box.label == consent).check().run()
    app.chat_input[0].set_value("Who is the owner of Apollo?").run()
    assert len(calls) == 1 and not app.exception
    answer = app.chat_message[-1].text[0].value
    assert answer.startswith("Owner: Casey (CSV!B2)")
    assert "The worksheet identifies the project lead." in answer

    def unavailable():
        raise RuntimeError("simulated provider outage")

    monkeypatch.setattr("finsight.ai_engine.get_client", unavailable)
    app.chat_input[0].set_value("Who is the owner of Apollo?").run()
    assert not app.exception
    assert app.chat_message[-1].text[0].value == "Owner: Casey (CSV!B2)"
