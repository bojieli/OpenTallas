import importlib.util, os, sys
H = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location("fb", os.path.join(H, "failure_breakdown.py"))
fb = importlib.util.module_from_spec(sp); sp.loader.exec_module(fb)


def test_count_headline_reads_last_sign_rate_row(tmp_path, monkeypatch):
    (tmp_path / "tools").mkdir(); (tmp_path / "lanes").mkdir()
    (tmp_path / "lanes" / "SIGN-RATE.tsv").write_text(
        "# x\n2026-11-18 10:05 390 s81=1 any=440 auto\n2026-11-18 11:05 395 s81=37 head=4 qc=1 kv=2 hbm=3 any=450 defer=s81:1 retired=qc:5,s81:49 auto\n")
    monkeypatch.setattr(fb, "__file__", str(tmp_path / "tools" / "failure_breakdown.py"))
    assert fb.count_headline() == "signed any plan 450 | current plan 395 | deferred re-sign 1 (s81 1) | retired-plan 54 (qc 5, s81 49)"
