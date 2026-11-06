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


def test_every_audit_setting_has_benchmark_evidence():
    """Each threshold, budget and method offered on the audit screen has a 1,000 repeat result to show."""
    import json
    bench = json.load(open(Path(APP).parents[1] / "results" / "experiment_b.json", encoding="utf8"))
    for threshold in [0.1, 0.2, 0.4, 0.6, 0.8]:
        for budget in [50, 100, 200, 400, 800]:
            res = bench["regimes"][str(threshold)]["results"][str(budget)]
            for code in ["M0", "M1", "M2", "M3"]:
                assert res[code]["yield_mean"] >= 0, (threshold, budget, code)
                assert 0 <= res[code]["mae"] < 1, (threshold, budget, code)


def test_audit_screen_runs_for_every_method_and_extreme_settings():
    at = AppTest.from_file(APP, default_timeout=180).run()
    at.sidebar.radio[0].set_value("2. Audit").run()
    for code in ["M0", "M1", "M2", "M3"]:
        at.selectbox(key="method").set_value(code).run()
        assert not at.exception, code
    at.select_slider(key="threshold").set_value(0.8).run()
    at.select_slider(key="budget").set_value(50).run()
    at.slider(key="unresolved").set_value(10).run()
    assert not at.exception
    assert any("1,000 repeated audits" in m.value for m in at.markdown)
