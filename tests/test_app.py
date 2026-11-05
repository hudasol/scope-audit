from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")


def test_three_screens_render_without_exception():
    at = AppTest.from_file(APP, default_timeout=120).run()
    assert not at.exception
    for name in ["2. Audit", "3. Review, approve and export", "1. Ingest and integrity"]:
        at.sidebar.radio[0].set_value(name).run()
        assert not at.exception, name


def test_export_blocked_before_approval():
    at = AppTest.from_file(APP, default_timeout=120).run()
    at.sidebar.radio[0].set_value("3. Review, approve and export").run()
    at.button[2].click().run()
    assert any("No approved observations" in e.value for e in at.error)
