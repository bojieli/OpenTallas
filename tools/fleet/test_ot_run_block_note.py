"""DISK-EXPLICIT-1123 + BLOCK-NOTE-1123 (COORD 11-23: LEAF-ROUTE-CBC J9 gates --crit --disk 2 sat ~1 h on epyc9 behind the 60 GB die default, no reason shown)."""
import importlib.machinery, importlib.util, json, pathlib, time
H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_run_blocknote", str(H / "ot-run"))
RUN = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_blocknote", l)); l.exec_module(RUN)


def row(free):
    return {"disk_gb": free}


def test_explicit_disk_is_judged_on_itself(monkeypatch):
    monkeypatch.setattr(RUN, "die_disk_reserved", lambda h, dev=None: 0)
    ok = {"epyc9": row(50)}
    assert RUN.drop_low_disk(ok, True, 60) == {}                          # die default: 50 - 60 < floor
    assert RUN.drop_low_disk(ok, True, 2) == {}                           # die, implicit: 50 - 2 < 60 real-free floor (unchanged)
    assert list(RUN.drop_low_disk(ok, True, 2, explicit=True)) == ["epyc9"]   # --disk 2 named: judged on it
    assert RUN.drop_low_disk({"epyc9": row(1)}, True, 2, explicit=True) == {}  # still needs the disk it asks for


def test_block_why_names_the_rail():
    w = RUN.block_why(["ot-run: epyc9 skipped for this die job: DISK 50 GB free - 2 GB this job < 60 GB real-free floor"], ["epyc9"], {}, 2, True)
    assert w.startswith("--disk 2 GB; ") and "real-free floor" in w
    w2 = RUN.block_why([], ["epyc9"], {"epyc9": "disk 12 GB < 20"}, 20, False)
    assert "(default)" in w2 and "epyc9: disk 12 GB < 20" in w2
    assert "ot-heavy" in RUN.block_why([], ["epyc9"], {}, 20, False)


def test_ticket_carries_the_reason_and_status_lists_it(tmp_path):
    p = str(tmp_path / "t.json")
    now = time.time()
    RUN.ticket_open("/srv/x/job", now=now - 1200, path=p, lane="LEAF-ROUTE-CBC")
    RUN.ticket_touch("/srv/x/job", state="waiting", why="08:30 --disk 2 GB; epyc9: ...", now=now, path=p)
    b = RUN.blocked_tickets(path=p, now=now)
    assert len(b) == 1 and b[0][0] == "/srv/x/job" and b[0][2] == "LEAF-ROUTE-CBC" and "--disk 2" in b[0][3]
    RUN.ticket_touch("/srv/x/job", state="running", now=now, path=p)
    assert "why" not in json.load(open(p))["/srv/x/job"] and RUN.blocked_tickets(path=p, now=now) == []


def test_ot_heavy_repeats_the_wait_reason():
    src = (H / "ot-heavy").read_text()
    assert 'ot-heavy: BLOCKED $(( (_wnow - T0) / 60 )) min on $(hostname) by $_wf: $WHY' in src
    assert "OT_HEAVY_BLOCK_NOTE_S:-600" in src


def test_main_wiring():
    src = (H / "ot-run").read_text()
    assert "explicit=disk_explicit" in src and 'say(f"ot-run: BLOCKED {int(_el_b / 60)} min: {_why}")' in src
