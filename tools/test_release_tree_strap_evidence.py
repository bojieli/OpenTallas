"""STRAP-EVIDENCE-COUNT 11-24 (COORD after FABLE-FLOW 137fc4da1186): hd_lep0N / hd_lep0N_w records count only on VERIFIED count-strap evidence
with kit plan sha == bind plan sha; other types are untouched; the ingest sweep writes the verdict table the counter reads."""
import json, os, subprocess, sys, types
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import release_tree_plan as R  # noqa: E402

K = "/srv/opentallas-scratch2/claude/lane/kit_hd_lep0N"


def rec(host="epyc7", kit=K):
    return dict(scan_host=host, pins_path=kit + "/pins.json", name="kl_hd_lep0N")


def rows(tmp_path, *lines):
    p = tmp_path / "s.tsv"
    p.write_text("# head\n" + "".join(x + "\n" for x in lines))
    return R.strap_rows(p)


def test_verdict_fails_closed(tmp_path):
    assert "no count_strap_evidence" in R.strap_verdict(rec(), {})
    assert R.strap_verdict(rec(), rows(tmp_path, f"epyc7:{K}\tVERIFIED\taa\taa\t2026-11-24")) == ""
    assert "UNVERIFIED" in R.strap_verdict(rec(), rows(tmp_path, f"epyc7:{K}\tUNVERIFIED\taa\taa\td"))
    assert "!= bind plan sha" in R.strap_verdict(rec(), rows(tmp_path, f"epyc7:{K}\tVERIFIED\taa\tbb\td"))
    assert "!= bind plan sha" in R.strap_verdict(rec(), rows(tmp_path, f"epyc7:{K}\tVERIFIED\t\t\td"))
    assert "no count_strap" in R.strap_verdict(rec("epyc8"), rows(tmp_path, f"epyc7:{K}\tVERIFIED\taa\taa\td"))
    assert "no count_strap" in R.strap_verdict(dict(scan_host="origin/main", pins_path="x/pins.json"), {})


def test_filter_drops_credited_refs_of_strap_types_only():
    st = {"hd_lep0N": ["a", "credit"], "hd_lep0N_w": ["credit2"], "hd_x": ["credit3"]}
    assert R.strap_filter(st, {"a"}) == {"hd_lep0N": ["credit"], "hd_lep0N_w": ["credit2"]}
    assert st == {"hd_lep0N": ["a"], "hd_x": ["credit3"]}
    assert set(R.STRAP_EVIDENCE_TYPES) == {"hd_lep0N", "hd_lep0N_w"}


def test_ingest_sweep_writes_the_table(tmp_path, monkeypatch):
    import signed_store_ingest as I
    kit = tmp_path / "kit"; kit.mkdir()
    (kit / "count_strap_evidence.json").write_text(json.dumps(dict(verification="VERIFIED", tie_audit=dict(kit_plan_sha256="s1", bind_plan_sha256="s1"))))
    bad = tmp_path / "bad"; bad.mkdir(); (bad / "count_strap_evidence.json").write_text("{")
    none = tmp_path / "none"; none.mkdir()
    cache = tmp_path / "c.json"
    cache.write_text(json.dumps(dict(signed_records=[rec("epyc7", str(kit)), rec("epyc7", str(bad)), rec("epyc7", str(none)), rec("epyc4", str(kit))])))
    monkeypatch.setattr(R, "COUNT_STRAP", tmp_path / "COUNT-STRAP-EVIDENCE.tsv")
    calls = []

    def runner(cmd, inp=None, timeout=0):
        calls.append(cmd)
        if cmd[0].endswith("coord-commit.sh"):
            return types.SimpleNamespace(returncode=0, stdout="")
        return subprocess.run([sys.executable, "-I", "-c", I.STRAP_PY], input=inp, capture_output=True, text=True)
    fails = []
    out = I.strap_sweep(fails, cache=str(cache), runner=runner)
    assert fails == [] and len(out) == 2
    got = R.strap_rows()
    assert got[("epyc7", str(kit))]["verification"] == "VERIFIED" and got[("epyc7", str(bad))]["verification"] == "UNREADABLE"
    assert ("epyc7", str(none)) not in got and not any(h == "epyc4" for h, _ in got)     # terminated host never asked
    assert R.strap_verdict(rec("epyc7", str(kit)), got) == ""
    n = len(calls)
    I.strap_sweep(fails, cache=str(cache), runner=runner)
    assert not any(c[0].endswith("coord-commit.sh") for c in calls[n:])                  # unchanged table: no commit
