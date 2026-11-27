"""phase_bind.py / adv_phase_bind.py (C-DIECLOCK-PHASE-BIND)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_phase_bind as ADV  # noqa: E402
import phase_bind as PB  # noqa: E402

T = 833.0


def _plan(parts):
    return {"partition_types": {"ty": {"reset": {"pin_entry_phase": True}}, "plain": {}},
            "partitions": [dict(name=n, type="ty", reset_entry_phase=h, id_straps={"strap_rst_ph": h % 2}) for n, h in parts]
            + [dict(name="q", type="plain")]}


def _rec(worst, end, launch="1000.0", capture="1400.0"):
    return dict(worst=worst, end=end, start="p/u_rrl/q/CLK", launch=launch, capture=capture)


def _sta(groups):
    """groups: {name: {corner: (setup_slack, hold_slack, end)}}"""
    c = {"TT": {"seams": {}}, "FF": {"seams": {}}}
    for g, per in groups.items():
        for corner, (s, h, end) in per.items():
            c[corner]["seams"][g] = {"max": _rec(s, end), "min": _rec(h, end)}
    return {"corners": c, "instances": {}, "spine_tree": {}}


def test_window_reproduces_run_slack_and_shifts_half_cycle():
    end = "a/u_rst_in/cap_r$_DFF_P_/D"
    sta = _sta({"p->a/arst_n": {"TT": (600.0, 20.0, end), "FF": (650.0, 10.0, end)}})
    bind, _ = PB.derive(_plan([("a", 0)]), sta, run_rows={"rows": [{"part": "a", "half_cycles": 0}]})
    r = bind["reset_entry"]["a"]
    assert r["scores"]["0"] == 10.0                     # the run's own edge: min of the measured slacks
    assert r["scores"]["1"] == 600.0 - T / 2            # half cycle earlier: setup loses T/2, hold gains T/2
    assert r["status"] == "MISBOUND" and r["best_h"] == 1 and r["strap"] == 1


def test_run_edge_from_rows_and_cap_f_default():
    endf = "a/u_rst_in/cap_f$_DFF_N_/D"
    sta = _sta({"p->a/arst_n": {"TT": (300.0, 300.0, endf), "FF": (300.0, 300.0, endf)}})
    b1, _ = PB.derive(_plan([("a", 1)]), sta)                                         # no row: cap_f default T/2 = h 1
    assert b1["reset_entry"]["a"]["scores"]["1"] == 300.0 and b1["reset_entry"]["a"]["status"] == "OK"
    b3, _ = PB.derive(_plan([("a", 1)]), sta, run_rows={"rows": [{"part": "a", "half_cycles": 3}]})
    assert b3["reset_entry"]["a"]["scores"]["3"] == 300.0


def test_proxy_first_flop_and_unmeasured():
    sta = _sta({"p->a/arst_n": {"TT": (700.0, 30.0, "a/u_rst_in/q$_DFF_P_/D"), "FF": (700.0, 30.0, "a/u_rst_in/q$_DFF_P_/D")}})
    bind, _ = PB.derive(_plan([("a", 2), ("b", 0)]), sta)
    a = bind["reset_entry"]["a"]
    assert a["measured_on"] == "proxy_first_flop" and a["scores"]["0"] == 30.0 and a["best_h"] == 1
    assert bind["reset_entry"]["b"]["status"] == "UNMEASURED" and "q" not in bind["reset_entry"]


def test_no_window_and_both_entries_share_h():
    e1, e2 = "a/u_rst_in/cap_r$_DFF_P_/D", "a/u_run_in/cap_r$_DFF_P_/D"
    sta = _sta({"p->a/arst_n": {"TT": (40.0, 40.0, e1), "FF": (40.0, 40.0, e1)},
                "p->a/start_i": {"TT": (500.0, 20.0, e2), "FF": (500.0, 20.0, e2)}})
    bind, _ = PB.derive(_plan([("a", 0)]), sta)
    r = bind["reset_entry"]["a"]
    assert r["status"] == "NO-WINDOW" and r["scores"]["0"] == 20.0


def test_rows_apply_form():
    end = "a/u_rst_in/cap_r$_DFF_P_/D"
    sta = _sta({"p->a/arst_n": {"TT": (600.0, 20.0, end), "FF": (650.0, 10.0, end)}})
    plan = _plan([("a", 0)])
    del plan["partitions"][0]["reset_entry_phase"]
    bind, _ = PB.derive(plan, sta)
    rows = PB.plan_rows(bind, "abc")["rows"]
    assert [r["op"] for r in rows] == ["set", "replace"]
    assert rows[0]["path"] == ["partitions", {"name": "a"}, "reset_entry_phase"] and rows[0]["value"] == 1
    assert rows[1]["old"] == 0 and rows[1]["value"] == 1


def test_start_edge_and_ambiguous():
    sc = {"count_aligned": {"regions": {"r1": {"edge_fall": True}, "r2": {"edge_fall": False}}}}
    endr = "r1/u_cland_origin/s0$_SDFF_PN0_/D"
    sta = _sta({"st_b1->r1/cland_tstart_in": {"TT": (700.0, 30.0, endr), "FF": (700.0, 30.0, endr)},
                "st_b2->r2/cland_tstart_in": {"TT": (900.0, -700.0, "r2/s0$_DFF_P_/D"), "FF": (500.0, -300.0, "r2/s0$_DFF_P_/D")}})
    bind, ca = PB.derive(_plan([]), sta, sidecar=sc)
    s1 = bind["start"]["st_b1->r1/cland_tstart_in"]
    assert s1["status"] == "OK" and s1["derived_edge_fall"] is True
    assert bind["start"]["st_b2->r2/cland_tstart_in"]["status"] == "AMBIGUOUS"
    assert {r["port"] for r in ca["TT"]} == {"start:st_b1->r1", "start:st_b2->r2"} and ca["TT"][0]["d_ps"] == 400.0


def test_check_lines_and_advisory(tmp_path, monkeypatch):
    end = "a/u_rst_in/cap_r$_DFF_P_/D"
    sta = _sta({"p->a/arst_n": {"TT": (600.0, 20.0, end), "FF": (650.0, 10.0, end)}})
    plan = _plan([("a", 0)])
    bind, _ = PB.derive(plan, sta)
    lines = PB.check_lines(plan, bind, {"count_aligned": {"regions": {}}})
    assert lines[0].startswith("RESET-ENTRY MISBOUND a reset_entry_phase 0")
    assert any(x.startswith("SUMMARY reset_entry ok 0 misbound 1") for x in lines)
    assert any(x.startswith("COUNT-ALIGN-UNBOUND") for x in lines)
    plan["partitions"][0]["reset_entry_phase"] = 1
    assert "misbound 0" in [x for x in PB.check_lines(plan, bind) if x.startswith("SUMMARY")][0]
    pp = tmp_path / "plan.json"
    pp.write_text(json.dumps(plan))
    monkeypatch.delenv("OT_PHASE_BIND", raising=False)
    monkeypatch.delenv("OT_PHASE_BIND_SIDECAR", raising=False)
    nob = ADV.findings(plan, str(pp))
    assert len(nob) == 1 and nob[0].startswith("WARN ADV-PHASE-BIND NO-BIND 1 ")
    assert ADV.findings({"partition_types": {}, "partitions": []}, str(pp)) == []
    (tmp_path / "phase_bind.json").write_text(json.dumps(bind))
    got = ADV.findings(plan, str(pp))
    assert got and all(x.startswith("WARN ADV-PHASE-BIND ") for x in got)


def test_cli_derive_check(tmp_path, capsys):
    end = "a/u_rst_in/cap_r$_DFF_P_/D"
    (tmp_path / "p.json").write_text(json.dumps(_plan([("a", 0)])))
    (tmp_path / "s.json").write_text(json.dumps(_sta({"p->a/arst_n": {"TT": (600.0, 20.0, end), "FF": (650.0, 10.0, end)}})))
    (tmp_path / "arr.txt").write_text("# OT_EDGES v1\nT t_a__clk 950.5 900.1 10\nT t_b__clk 7006.0 6900 10\n")
    o = tmp_path / "b.json"
    assert PB.main(["derive", "--plan", str(tmp_path / "p.json"), "--sta", str(tmp_path / "s.json"), "--arr",
                    f"TT={tmp_path / 'arr.txt'}", "--out", str(o), "--rows", str(tmp_path / "r.json")]) == 0
    b = json.loads(o.read_text())
    assert b["arrivals"]["TT"] == {"ports": 2, "min_ps": 950.5, "max_ps": 7006.0} and b["key"]["plan_sha12"]
    assert json.loads((tmp_path / "r.json").read_text())["base_plan_sha256_12"] == b["key"]["plan_sha12"]
    assert PB.main(["check", "--plan", str(tmp_path / "p.json"), "--bind", str(o)]) == 0
    assert "PHASE-BIND RESET-ENTRY MISBOUND a" in capsys.readouterr().out


def _bound(tmp_path, h):
    end = "a/u_rst_in/cap_r$_DFF_P_/D"
    sta = _sta({"p->a/arst_n": {"TT": (600.0, 20.0, end), "FF": (650.0, 10.0, end)}})
    plan = _plan([("a", h)])
    bind, _ = PB.derive(plan, sta)
    bind["key"]["ctree_spef_sha12"] = "aaaaaaaaaaaa"
    pp = tmp_path / "plan.json"
    pp.write_text(json.dumps(plan))
    return plan, bind, pp


def test_blocking_no_bind_misbound_stale(tmp_path, monkeypatch):
    for k in ("OT_PHASE_BIND", "OT_PHASE_BIND_SIDECAR", "OT_PHASE_BIND_CTREE_SHA12", "OT_PHASE_BIND_STRICT", "OT_PHASE_BIND_BLOCK"):
        monkeypatch.delenv(k, raising=False)
    plan, bind, pp = _bound(tmp_path, 0)
    nob = ADV.blocking(plan, str(pp))
    assert len(nob) == 1 and nob[0].startswith("FAIL ADV-PHASE-BIND NO-BIND 1 ")
    assert ADV.blocking({"partition_types": {}, "partitions": []}, str(pp)) == []
    sc = tmp_path / "source_sidecar.json"
    sc.write_text(json.dumps({"count_aligned": {"regions": {}}}))
    assert ADV.blocking({"partition_types": {}, "partitions": []}, str(pp)) == []        # count-align only stays a WARN
    (tmp_path / "phase_bind.json").write_text(json.dumps(bind))
    got = ADV.blocking(plan, str(pp))
    assert any(x.startswith("FAIL ADV-PHASE-BIND RESET-ENTRY MISBOUND a ") for x in got)
    assert not any("COUNT-ALIGN-UNBOUND" in x for x in got)                            # strict only
    monkeypatch.setenv("OT_PHASE_BIND_STRICT", "1")
    assert any("COUNT-ALIGN-UNBOUND" in x for x in ADV.blocking(plan, str(pp)))
    monkeypatch.delenv("OT_PHASE_BIND_STRICT")
    monkeypatch.setenv("OT_PHASE_BIND_CTREE_SHA12", "bbbbbbbbbbbb")
    assert any("STALE-CLOCK bind derived on ctree.spef aaaaaaaaaaaa" in x for x in ADV.blocking(plan, str(pp)))
    monkeypatch.setenv("OT_PHASE_BIND_CTREE_SHA12", "aaaaaaaaaaaa")
    assert not any("STALE-CLOCK" in x for x in ADV.blocking(plan, str(pp)))
    plan["partitions"][0]["reset_entry_phase"] = 1                                      # the derived choice: clean
    plan["partitions"].append(dict(name="b", type="ty", reset_entry_phase=0, id_straps={}))
    got = ADV.blocking(plan, str(pp))
    assert [x.split()[2] for x in got] == ["STALE-INSTANCE"]
    monkeypatch.setenv("OT_PHASE_BIND_BLOCK", "0")
    assert ADV.blocking(plan, str(pp)) == []


def test_pre_class_is_registered_and_blocks(tmp_path, monkeypatch):
    import plan_gate_pre as G
    assert "PHASE-BIND" in G.CLASSES
    plan, bind, pp = _bound(tmp_path, 0)
    monkeypatch.delenv("OT_PHASE_BIND", raising=False)
    monkeypatch.delenv("OT_PHASE_BIND_BLOCK", raising=False)
    got = G.phase_bind_findings(str(pp))
    assert got and all(x.startswith("FAIL ADV-PHASE-BIND ") for x in got)
