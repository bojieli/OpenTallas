import json
import signoff


def test_rejudge_write_keeps_backup_and_provenance(tmp_path, monkeypatch):
    rec = {"verdict": "NOT SIGNED", "reasons": ["old"]}
    p = tmp_path / "signoff.json"; p.write_text(json.dumps(rec))
    def fake_eval(r, it=None):
        r["verdict"] = "SIGNED"; r["reasons"] = []
    monkeypatch.setattr(signoff, "evaluate", fake_eval)
    monkeypatch.setattr(signoff, "summary_line", lambda r: "x")
    import argparse
    a = argparse.Namespace(record=str(p), insertion_target=None, rescore_unconstrained=False, kit=None, write=True, rejudge=True, rejudge_note="n")
    assert signoff.cmd_verdict(a) == 0
    new = json.loads(p.read_text())
    assert new["verdict"] == "SIGNED" and new["rejudged"]["note"] == "n"
    assert json.loads((tmp_path / "signoff.json.before-rejudge").read_text())["verdict"] == "NOT SIGNED"
    a.rejudge = False; p.write_text(json.dumps(rec)); (tmp_path / "signoff.json.before-rejudge").unlink()
    signoff.cmd_verdict(a)
    assert json.loads(p.read_text())["verdict"] == "NOT SIGNED"      # no flag, no write (unchanged behaviour)
