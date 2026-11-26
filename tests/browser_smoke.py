"""Exercise the actual Streamlit frontend with Chromium in an isolated session."""
from io import BytesIO
from pathlib import Path
import os
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

from openpyxl import Workbook
from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def sample_workbook():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Operations"
    sheet.append(["Project", "Owner", "Amount"])
    sheet.append(["Apollo", "Casey", 20])
    sheet.append(["Beacon", "Ari", 30])
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def exercise(url):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.set_default_timeout(30000)
        page.goto(url)
        expect(page.get_by_role("heading", name="Financial overview", exact=True)).to_be_visible()
        sidebar = page.get_by_test_id("stSidebar")
        panel = sidebar.locator(".st-key-active_dataset_manager")
        name = panel.get_by_text("Microsoft Financial Sample (demo)", exact=True)
        status = panel.get_by_text("Ready · 700 records", exact=True)
        change = panel.get_by_role("button", name="Change dataset", exact=True)
        expect(name).to_be_visible()
        expect(status).to_be_visible()
        expect(change).to_be_visible()
        bounds = panel.bounding_box()
        sidebar_bounds = sidebar.bounding_box()
        name_bounds = name.bounding_box()
        status_bounds = status.bounding_box()
        assert bounds["x"] + bounds["width"] <= sidebar_bounds["x"] + sidebar_bounds["width"]
        assert name_bounds["y"] + name_bounds["height"] <= status_bounds["y"]
        assert status_bounds["y"] + status_bounds["height"] <= change.bounding_box()["y"]
        change.click()
        page.locator('input[type="file"]').set_input_files({
            "name": "operations.xlsx",
            "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "buffer": sample_workbook(),
        })
        expect(page.get_by_role("heading", name="AI Copilot", exact=True)).to_be_visible()
        expect(sidebar.get_by_role("button", name="Workbook chat", exact=True)).to_have_count(0)
        toolbar = page.locator(".st-key-copilot_toolbar")
        expect(toolbar.get_by_text("operations.xlsx", exact=True)).to_be_visible()
        expect(toolbar.get_by_text("Operations · Local analysis", exact=True)).to_be_visible()
        expect(toolbar.get_by_role("button", name="Settings", exact=True)).to_be_visible()
        expect(toolbar.get_by_role("button", name="New chat", exact=True)).to_be_visible()
        assert "linear-gradient" in toolbar.evaluate("(element) => getComputedStyle(element).backgroundImage")
        chat = page.get_by_test_id("stChatInputTextArea")
        chat.fill("Who is the owner of Apollo?")
        chat.press("Enter")
        expect(page.get_by_text("Owner: Casey (Operations!B2)", exact=True)).to_be_visible()
        messages = page.get_by_test_id("stChatMessage")
        user = messages.filter(has=page.get_by_role("group", name="Chat message from user", exact=True)).first
        assistant = messages.filter(has=page.get_by_role("group", name="Chat message from assistant", exact=True)).first
        expect(user).to_have_css("flex-direction", "row-reverse")
        user_box, assistant_box = user.bounding_box(), assistant.bounding_box()
        assert user_box["x"] > assistant_box["x"]
        assert user_box["x"] + user_box["width"] > assistant_box["x"] + assistant_box["width"]
        assert "radial-gradient" in page.get_by_test_id("stAppViewContainer").evaluate(
            "(element) => getComputedStyle(element).backgroundImage"
        )
        chat.fill("Sum C2:C3")
        chat.press("Enter")
        expect(page.get_by_text("Sum for Operations!C2:C3: 50 (2 numeric cells).")).to_be_visible()
        page.get_by_text("Source cells", exact=True).last.click()
        expect(page.get_by_text("Operations!C2:C3 · Saved Excel values", exact=True)).to_be_visible()
        expect(page.get_by_test_id("stException")).to_have_count(0)
        mobile = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
        mobile.goto(url)
        expect(mobile.get_by_role("heading", name="Financial overview", exact=True)).to_be_visible()
        assert mobile.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        browser.close()


if __name__ == "__main__":
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    env = dict(os.environ, FINSIGHT_LIVE_AI="0", STREAMLIT_BROWSER_GATHER_USAGE_STATS="false")
    with subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py",
                           "--server.address", "127.0.0.1", "--server.port", str(port),
                           "--server.headless", "true"], cwd=ROOT, env=env) as server:
        try:
            for _ in range(100):
                if server.poll() is not None:
                    raise RuntimeError("Streamlit exited before startup")
                try:
                    with urlopen(url + "/_stcore/health", timeout=1) as check:
                        if check.read() == b"ok":
                            break
                except (URLError, TimeoutError):
                    time.sleep(0.25)
            else:
                raise RuntimeError("Streamlit startup timed out")
            exercise(url)
        finally:
            server.terminate()
