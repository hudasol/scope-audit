import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_claims_lint_passes():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_claims.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def test_lint_detects_violations(tmp_path, monkeypatch):
    sys.path.insert(0, str(ROOT / "scripts"))
    import check_claims as cc
    bad = tmp_path / "docs"
    bad.mkdir()
    (bad / "x.md").write_text("The population of foxes is 12% higher — clearly.\nAlso Claude wrote this.\n", encoding="utf8")
    monkeypatch.setattr(cc, "ROOT", tmp_path)
    errs = cc.run()
    joined = "\n".join(errs)
    assert "dash character" in joined and "banned name" in joined and "claim word" in joined and "percent figure typed by hand" in joined
