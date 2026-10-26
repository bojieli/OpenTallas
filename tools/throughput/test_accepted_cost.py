"""Tests of the accepted-cost ledger (owner 2026-10-13).   python3 -m pytest tools/throughput/test_accepted_cost.py"""
import copy
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import accepted_cost as AC  # noqa: E402


def path():
    """a -> b -> d on the critical path (10 + 20 + 5), c overlapped beside b with 12 cycles of slack"""
    nodes = [dict(id="a", cycles=10, base_cycles=10, start=0, critical=True),
             dict(id="L0.b", cycles=20, base_cycles=20, critical=True),
             dict(id="L0.c", cycles=8, base_cycles=8, critical=False),
             dict(id="L1.b", cycles=20, base_cycles=20, critical=True),
             dict(id="d", cycles=5, base_cycles=5, critical=True)]
    edges = [dict(src="a", dst="L0.b", cycles=0), dict(src="a", dst="L0.c", cycles=0),
             dict(src="L0.b", dst="L1.b", cycles=0), dict(src="L0.c", dst="L1.b", cycles=0),
             dict(src="L1.b", dst="d", cycles=0)]
    return dict(nodes=nodes, edges=edges)


def row(design="s81", unit="u", loss=1.0, ratio=2.0, grade="committed_bench", evidence="AGENTS.md", group=None):
    r = AC.make_row(design, unit, 100.0, 100.0 * ratio, {"ar": dict(e2e_loss_pct=loss)}, evidence, grade, group=group)
    return r


def test_solve_reproduces_the_chain():
    assert AC.solve(**path())[0] == 55


def test_critical_unit_costs_every_run():
    r = AC.rom_loss(path(), r"\.b$", 20, 30)
    assert r["runs_per_token"] == 2 and r["critical_runs"] == 2
    assert r["added_cycles"] == 20
    assert r["e2e_loss_pct"] == round(100 * (1 - 55 / 75), 3)


def test_loss_is_not_the_unit_ratio():
    r = AC.rom_loss(path(), r"\.b$", 20, 30)          # unit 1.5x, token 55 -> 75
    assert r["e2e_loss_pct"] < 50


def test_overlapped_unit_costs_only_past_its_slack():
    assert AC.rom_loss(path(), r"\.c$", 8, 20)["added_cycles"] == 0          # exactly absorbs the 12 of slack
    r = AC.rom_loss(path(), r"\.c$", 8, 25)
    assert r["added_cycles"] == 5 and r["naive_added_cycles"] == 17 and r["overlapped_runs"] == 1


def test_price_filter_and_no_match():
    p = path()
    p["nodes"][3]["base_cycles"] = p["nodes"][3]["cycles"] = 90              # another vehicle under the same name
    r = AC.rom_loss(p, r"\.b$", 20, 30)
    assert r["runs_per_token"] == 1 and r["other_price_nodes_skipped"] == 1
    with pytest.raises(AC.LedgerError):
        AC.rom_loss(path(), r"nothing", 20, 30)


def test_wave_positions_pay_the_slowest_stage_again():
    p = path()
    p["nodes"].append(dict(id="w", cycles=40, base_cycles=40, critical=True, op="wave.busy"))
    p["edges"].append(dict(src="d", dst="w", cycles=0))
    for n in p["nodes"]:
        n["group"] = "S1" if n["id"].startswith("L1") else "S0"
    p["groups"] = [dict(id="S0", kind="stage", cycles=38), dict(id="S1", kind="stage", cycles=40)]
    r = AC.rom_loss(p, r"\.b$", 20, 30)
    assert r["added_cycles"] == 30 and r["wave_added_cycles_per_position"] == 10 and r["runs_per_token"] == 2


def test_rate_class():
    r = AC.rate_loss(path(), 44, 0.44, 0.40)
    assert r["added_cycles"] == 10.0
    assert AC.rate_loss(path(), 0, 0.44, 0.40)["e2e_loss_pct"] == 0
    assert AC.rate_loss(path(), 44, 0.44, 0.40, critical=False)["added_cycles"] == 0
    assert AC.unit_ratio(0.44, 0.40, rate=True) == 1.1


def test_hbm_loss_uses_the_schedule_not_the_ratio():
    def run(op=None, f=1.0):                       # A is on the path, B is overlapped behind a 100-cycle peer
        a = 50 * (f if op == "X.A" else 1)
        b = 60 * (f if op == "X.B" else 1)
        return a + max(100, b)
    cnt = {"X.A": 3, "X.B": 3}
    assert AC.hbm_loss(run, cnt, "X.A", 2.0)["added_cycles"] == 50
    assert AC.hbm_loss(run, cnt, "X.B", 1.5)["e2e_loss_pct"] == 0
    assert AC.hbm_loss(run, cnt, "X.C", 2.0) is None


def test_accept_within_limits(tmp_path):
    led = AC.empty_ledger()
    AC.propose(led, row(loss=4.9))
    assert AC.accept(led, "s81", "u", root=AC.ROOT)["status"] == "accepted"
    AC.save_ledger(led, tmp_path / "l.json")
    back = json.loads((tmp_path / "l.json").read_text())
    assert back["totals"]["s81"]["accepted_pct"] == 4.9 and AC.check(back) == []


def test_accept_records_the_decision_note():
    led = AC.empty_ledger()
    AC.propose(led, row(loss=1.0))
    r = AC.accept(led, "s81", "u", root=AC.ROOT, note="owner-accepted")
    assert r["status"] == "accepted" and r["acceptance_note"] == "owner-accepted"
    d = r["accepted_date"]
    r = AC.accept(led, "s81", "u", root=AC.ROOT, note="owner re-confirmed")
    assert r["acceptance_note"] == "owner re-confirmed" and r["accepted_date"] == d


def test_owner_exception_waives_only_the_limits():
    led = AC.empty_ledger()
    AC.propose(led, row(unit="a", loss=4.0))
    AC.propose(led, row(unit="a2", loss=4.5))
    AC.accept(led, "s81", "a2", root=AC.ROOT)
    AC.accept(led, "s81", "a", root=AC.ROOT)
    AC.propose(led, row(unit="b", loss=9.0))
    with pytest.raises(AC.LedgerError):
        AC.accept(led, "s81", "b", root=AC.ROOT)
    r = AC.accept(led, "s81", "b", root=AC.ROOT, owner_exception="owner 2026-10-14")
    assert r["status"] == "accepted" and r["owner_exception"]
    assert AC.check(led) == [] and AC.totals(led)["s81"]["over_limit_by_owner_exception"]
    AC.find(led, "s81", "b").pop("owner_exception")
    assert len(AC.check(led)) == 2          # mutant: without the exception both limits are violations
    AC.propose(led, row(unit="c", loss=9.0, grade="interim_log"))
    with pytest.raises(AC.LedgerError):     # the exception never waives the committed-bench requirement
        AC.accept(led, "s81", "c", root=AC.ROOT, owner_exception="owner")


def test_supersede_accepted_keeps_the_old_decision():
    led = AC.empty_ledger()
    AC.propose(led, row(loss=2.0))
    AC.accept(led, "s81", "u", root=AC.ROOT, note="first")
    with pytest.raises(AC.LedgerError):
        AC.propose(led, row(loss=9.0))
    new = AC.propose(led, row(loss=9.0), supersede_accepted="owner 2026-10-14")
    assert new["status"] == "proposed" and new["supersedes"]["e2e_loss_pct"] == 2.0
    assert new["supersedes"]["acceptance_note"] == "first"


def test_refuses_over_five_percent():
    led = AC.empty_ledger()
    AC.propose(led, row(loss=5.01))
    with pytest.raises(AC.LedgerError, match="unit limit"):
        AC.accept(led, "s81", "u")
    assert led["rows"][0]["status"] == "proposed"


def test_refuses_design_total_over_fifteen_percent():
    led = AC.empty_ledger()
    for i in range(3):
        AC.propose(led, row(unit=f"u{i}", loss=4.5))
        AC.accept(led, "s81", f"u{i}")
    AC.propose(led, row(unit="u3", loss=2.0))
    with pytest.raises(AC.LedgerError, match="design total"):
        AC.accept(led, "s81", "u3")
    AC.propose(led, row(unit="u4", loss=1.5))                 # exactly 15.0 is allowed
    AC.accept(led, "s81", "u4")
    AC.propose(led, row(design="qwen_rom", unit="q", loss=4.0))     # another design has its own total
    AC.accept(led, "qwen_rom", "q")
    assert AC.totals(led)["s81"]["accepted_pct"] == 15.0 and AC.totals(led)["s81"]["headroom_pct"] == 0.0


def test_refuses_without_committed_evidence_or_need():
    led = AC.empty_ledger()
    AC.propose(led, row(unit="log", grade="interim_log"))
    AC.propose(led, row(unit="nofile", evidence="results/does/not/exist.json"))
    AC.propose(led, row(unit="fine", ratio=1.05))
    for u, why in (("log", "committed bench"), ("nofile", "not in the repository"), ("fine", "qualifies")):
        with pytest.raises(AC.LedgerError, match=why):
            AC.accept(led, "s81", u)
    with pytest.raises(AC.LedgerError, match="no row"):
        AC.accept(led, "s81", "absent")


def test_accepted_row_is_not_silently_replaced():
    led = AC.empty_ledger()
    AC.propose(led, row(loss=1.0))
    AC.propose(led, row(loss=2.0))                            # a proposal may be re-measured
    assert len(led["rows"]) == 1 and led["rows"][0]["e2e_loss_pct"] == 2.0
    AC.accept(led, "s81", "u")
    with pytest.raises(AC.LedgerError, match="already accepted"):
        AC.propose(led, row(loss=0.1))


def test_check_catches_hand_edits():
    led = AC.empty_ledger()
    AC.propose(led, row(loss=9.0))
    bad = copy.deepcopy(led)
    bad["rows"][0]["status"] = "accepted"
    assert any("over 5.0" in b for b in AC.check(bad))
    many = AC.empty_ledger()
    for i in range(4):
        r = row(unit=f"u{i}", loss=4.0)
        r["status"] = "accepted"
        many["rows"].append(r)
    assert any("accepted total" in b for b in AC.check(many))


def test_group_counts_alternative_measurements_once():
    led = AC.empty_ledger()
    AC.propose(led, row(unit="SM a", loss=3.0, group="SM"))
    AC.propose(led, row(unit="SM b", loss=7.0, group="SM"))
    AC.propose(led, row(unit="other", loss=1.0))
    assert AC.totals(led)["s81"]["proposed_pct"] == 8.0


def test_worst_workload_binds():
    r = AC.make_row("s81", "u", 100, 200, {"ar": dict(e2e_loss_pct=1.6), "mtp": dict(e2e_loss_pct=1.3)}, "x",
                    "committed_bench")
    assert r["e2e_loss_pct"] == 1.6 and r["binding_workload"] == "ar" and r["unit_ratio"] == 2.0


def test_committed_token_paths_and_s81_hc_post():
    for name in ("qwen_rom", "ds_rom", "ds_rom_mtp"):
        AC.load_path(name)                                     # the committed DAGs re-solve to their published totals
    per = AC.compute("s81", match=r"hc_post$", price=112.9, measured=287.0)
    assert per["ar"]["runs_per_token"] == 80 and per["ar"]["critical_runs"] == 80
    assert per["ar"]["added_cycles"] == pytest.approx(80 * (287 - 112.9), abs=0.2)
    assert 1.5 < per["ar"]["e2e_loss_pct"] < 1.8               # a 2.54x unit costs under 2 % of the token
    assert per["mtp"]["wave_positions"] == 5 and per["mtp"]["other_price_nodes_skipped"] == 6


def test_committed_ledger_is_valid():
    if AC.LEDGER.exists():
        led = AC.load_ledger()
        assert led["schema"] == AC.SCHEMA and AC.check(led) == []
        assert led["totals"] == AC.totals(led)


def test_unpriced_serial_job_has_no_ratio_and_is_judged_by_its_loss():
    """a job the token path does not hold (price 0): node_delta on the nodes it delays, ratio None, loss counted"""
    r = AC.rom_loss(path(), r"\.b$", 0, 0, node_delta=5)
    assert r["added_cycles"] == 10 and r["runs_per_token"] == 2
    assert AC.unit_ratio(0, 5) is None
    led = AC.empty_ledger()
    ok = AC.make_row("s81", "unpriced", 0, 5.0, {"ar": dict(e2e_loss_pct=3.0)}, "AGENTS.md", "committed_bench")
    assert ok["unit_ratio"] is None and AC.refusal(led, ok) is None
    over = AC.make_row("s81", "unpriced big", 0, 50.0, {"ar": dict(e2e_loss_pct=6.0)}, "AGENTS.md", "committed_bench")
    assert "unit limit" in AC.refusal(led, over)
    led["rows"] += [ok, over]
    assert AC.check(led) == [] and "unpriced" in AC.table(led)


def test_annotate_states_the_share_basis_without_touching_numbers(tmp_path):
    led = AC.empty_ledger()
    per = {"ar": dict(e2e_loss_pct=0.4)}
    row = AC.make_row("s81", "SU.X unit", 80.0, 167.0, per, "ev", "committed_bench", "n", group="SU.X")
    AC.propose(led, row)
    before = (row["e2e_loss_pct"], row["unit_ratio"], row["status"])
    assert "| - |" in AC.table(led)                                  # not stated yet
    r = AC.annotate(led, "s81", "SU.X", "modelled", "QUALIFIER q")   # by group
    assert r is row and r["share_basis"] == "modelled" and r["note"].endswith("QUALIFIER q")
    AC.annotate(led, "s81", "SU.X unit", None, "QUALIFIER q")        # appended once
    assert r["note"].count("QUALIFIER q") == 1 and (r["e2e_loss_pct"], r["unit_ratio"], r["status"]) == before
    assert "| MODELLED |" in AC.table(led) and AC.check(led) == []
    r["share_basis"] = "guessed"
    assert any("share basis" in b for b in AC.check(led))
    with pytest.raises(AC.LedgerError):
        AC.annotate(led, "s81", "SU.NONE", "measured")


def test_superseded_rows_leave_every_total_and_the_table():
    led = AC.empty_ledger()
    AC.propose(led, row(unit="VM.READ", loss=4.0))
    AC.accept(led, "s81", "VM.READ", root=AC.ROOT)
    AC.propose(led, row(unit="FIELD.X", loss=1.0))
    with pytest.raises(AC.LedgerError):
        AC.supersede(led, "s81", r"^VM\.", by="", reason="r")            # the superseding die rev is required
    hit = AC.supersede(led, "s81", r"^VM\.", by="DV die p4l", reason="retired hub")
    assert [r["unit"] for r in hit] == ["VM.READ"] and len(led["rows"]) == 2   # kept, never deleted
    r = AC.find(led, "s81", "VM.READ")
    assert r["status"] == "superseded" and r["superseded"]["from_status"] == "accepted" and r["e2e_loss_pct"] == 4.0
    t = AC.totals(led)["s81"]
    assert (t["accepted_pct"], t["proposed_pct"], t["superseded_rows"], t["superseded_pct_not_counted"]) == (0.0, 1.0, 1, 4.0)
    assert AC.check(led) == []
    tab = AC.table(led)
    assert "VM.READ" not in tab and "FIELD.X" in tab and "1 superseded rows" in tab
    with pytest.raises(AC.LedgerError, match="superseded"):
        AC.propose(led, row(unit="VM.READ", loss=1.0))                  # a retired row is not silently replaced
    del r["superseded"]["by"]
    assert any("superseded without" in b for b in AC.check(led))


def test_committed_s81_total_is_the_dv_die_only():
    led = AC.load_ledger()
    s81 = [r for r in led["rows"] if r["design"] == "s81"]
    live = [r for r in s81 if r["status"] != "superseded"]
    assert not [r["unit"] for r in live if re.match(r"(VM|SU|HC|MIX4)\.|CAPT\.CD_PINREG$", r["group"])]
    assert all(r["superseded"]["by"] and r["superseded"]["reason"] for r in s81 if r["status"] == "superseded")
    ar = sum((r["per_workload"].get("ar") or {}).get("e2e_loss_pct", 0.0) for r in live)
    landing = sum(r["per_workload"]["ar"]["e2e_loss_pct"] for r in live if r["group"].startswith("S81.DV_LANDING"))
    assert abs(ar - landing - 0.871) < 1e-6 and abs(ar - 2.775) < 1e-6


def test_op_alternation_and_scoped_fmt():
    """TOK-SCHED 10-25: 'A|B' op alternation and the --op-fmt [OP:]OPERAND=FMT[/FMT] filter scoped to one op"""
    import types
    D = lambda f: types.SimpleNamespace(fmt=f)
    sm_bf = types.SimpleNamespace(unit="SM", op="MATVEC", desc={"B": D("BF16")})
    sm_i8 = types.SimpleNamespace(unit="SM", op="MATVEC", desc={"B": D("INT8")})
    sm_f8 = types.SimpleNamespace(unit="SM", op="MATVEC", desc={"B": D("FP8E4M3")})
    att = types.SimpleNamespace(unit="ATT", op="QK", desc={"B": D("FP8E4M3")})
    assert AC.op_match("ATT.QK", "SM.MATVEC|ATT.QK|ATT.PV") and not AC.op_match("ATT.SPAN", "SM.MATVEC|ATT.QK")
    f = AC.parse_fmt(["SM.MATVEC:B=BF16/INT8"])
    assert [AC.fmt_match(r, f) for r in (sm_bf, sm_i8, sm_f8, att)] == [True, True, False, True]
    g = AC.parse_fmt(["B=BF16"])
    assert [AC.fmt_match(r, g) for r in (sm_bf, sm_i8, att)] == [True, False, False]
    assert AC.parse_fmt([]) is None and AC.fmt_match(att, None)
