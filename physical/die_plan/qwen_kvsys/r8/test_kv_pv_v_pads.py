"""DIE-KV-16: PV V-word landing pads (V-D-H = 0 per bank, astk pe2 one offset per source).  Synthetic pair side: 2 vports
x 4 banks, header / command / V / pe2 crossings; check FAILs on the unpadded bind, the table's targets PASS, a one-stage
mutant on one bank FAILs on exactly that member, and a V that lands after its command fails closed."""
import copy
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3] / "tools/die_plan"))
import kv_pv_v_pads as P  # noqa: E402
import regen_constants as RC  # noqa: E402
import r8  # noqa: E402

DV = {("vport_A", 0): -20, ("vport_A", 1): -35, ("vport_B", 2): -5, ("vport_B", 3): -50}   # landed - as-built of V


def mk(port, bits, src, a, b, lane="L1"):
    return dict(sink_port=port, sink_bits=[bits], source=src, source_bits=[bits], asbuilt_stages=a, bound_stages=b,
                landed_stages=b, lane=lane)


def landing(dcmd=3, dh=None):
    dh = dh or {"vport_A": 4, "vport_B": -6}
    g = [dict(sink="pvw_0__u_ctl", sink_part="hub_C", src_part="pv_S_0",
              members=[mk("in_t", [14 * i, 14 * i + 13], f"{vp}.out_t", 40, 40 + dh[vp]) for i, vp in enumerate(dh)]
              + [mk("in_valid", [i, i], f"{vp}.out_valid", 40, 40 + dh[vp]) for i, vp in enumerate(dh)])]
    for (vp, b), dv in DV.items():
        g.append(dict(sink=f"pvw_0__u_s0_b{b}", sink_part="pv_S_0", src_part="pv_S_1",
                      members=[mk("bc", [0, 22], "pvw_0__u_ctl.cmd", 50, 50 + dcmd),
                               mk("pv2", [0, 127], f"{vp}.out_v_lo", 90, 90 + dv, lane=f"L{b}"),
                               mk("pe2", [0, 15], "astk_ES__u_strip_g_owner_7__u_owner.response_data", 60, 60 - b,
                                  lane="LE")]))
    return g


def table(groups):
    ms = [dict(id=r8.mkey(g, m), sink=g["sink"], sink_part=g["sink_part"], src_part=g["src_part"], sink_port=m["sink_port"],
               sink_bits=m["sink_bits"], source=m["source"], asbuilt=m["asbuilt_stages"], bound=m["bound_stages"], pad=0,
               landed=m["landed_stages"], lane=m["lane"]) for g in groups for m in g["members"]]
    return dict(schema=r8.SCHEMA, die="qwen_kvsys", members=ms)


def write(d, groups):
    d.mkdir(parents=True, exist_ok=True)
    (d / "bus_groups.json").write_text(json.dumps(dict(die="qwen_kvsys", landing=groups, replica=[])))
    return d


def apply(groups, extra):
    g2 = copy.deepcopy(groups)
    by = {x["id"]: x["landed"] for x in extra["members"]}
    for g in g2:
        for m in g["members"]:
            k = r8.mkey(g, m)
            if k in by:
                m["landed_stages"] = by[k]
    return g2


def test_fail_pad_pass_mutant():
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        g = landing()
        s, _ = P.check(RC.Bound(str(write(t / "b0", g))))
        assert s["verdict"] == "FAIL" and s["bad"] > 0
        ex = P.pads(str(t / "b0"), table(g))
        # V-D-H targets: -(dv - dcmd - dh)
        pads = {x["sink"] + x["sink_port"]: x["pv_v_pad"] for x in ex["members"]}
        assert pads["pvw_0__u_s0_b0pv2"] == -(-20 - 3 - 4) and pads["pvw_0__u_s0_b3pv2"] == -(-50 - 3 + 6)
        assert pads["pvw_0__u_s0_b3pe2"] == 3 and "pvw_0__u_s0_b0pe2" not in pads   # pe2 lifted to the source max
        s, _ = P.check(RC.Bound(str(write(t / "b1", apply(g, ex)))))
        assert s["banks"] == 4 and s["bad"] == 0
        mut = copy.deepcopy(ex)
        mut["members"][0]["landed"] += 1
        s, h = P.check(RC.Bound(str(write(t / "b2", apply(g, mut)))))
        assert s["verdict"] == "FAIL" and s["bad"] == 1 and h == {"V:1": 1}


def test_v_after_command_fails_closed():
    with tempfile.TemporaryDirectory() as t:
        g = landing(dcmd=-60)          # command 60 stages short -> V would need a negative pad
        try:
            P.pads(str(write(Path(t) / "b", g)), table(g))
        except SystemExit as e:
            assert "needs" in str(e)
        else:
            raise AssertionError("negative pad not refused")


def test_e_min_pad_lifts_the_whole_source():
    """pads --e-min-pad M (class D 11-19): every pe2 member ends with a pad >= M, one e per source kept (check PASS)"""
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        g = landing()
        base = P.pads(str(write(t / "b0", g)), table(g))
        ex = P.pads(str(t / "b0"), table(g), 5)
        pe = {x["sink"]: x for x in ex["members"] if x["sink_port"] == "pe2"}
        assert len(pe) == 4 and min(x["landed"] - x["bound"] for x in pe.values()) == 5
        assert {k: x["pv_v_pad"] for k, x in pe.items()} == {f"pvw_0__u_s0_b{b}": 5 + b for b in range(4)}
        v = lambda tab: {x["id"]: x["landed"] for x in tab["members"] if x["sink_port"] == "pv2"}
        assert v(ex) == v(base)                                        # the V words do not move
        s, _ = P.check(RC.Bound(str(write(t / "b1", apply(g, ex)))))
        assert s["verdict"] == "FAIL" or s["bad"] == 0                 # 4 banks only: verdict needs 512, the rule has no bad row
        assert s["bad"] == 0


# FABLE-FIX-KV-PV class D 11-19

if __name__ == "__main__":
    test_fail_pad_pass_mutant()
    test_v_after_command_fails_closed()
    print("2 passed")


# ---- EMPTY-GUARD-1125 (KV-PV-ESTRIP: pads on a native_composite bind wrote a 0-member table and a vacuous clean rebind) ----------------
def _composite_bind(d):
    g = [dict(sink="native_composite_pv_N_0_pvg0_p0", sink_part="pv_N_0", src_part="pv_N_3",
              members=[mk("s0__pv2", [0, 127], "vport_WN_0.out_v_lo", 80, 43), mk("s0__bc", [0, 22], "pvw_1__u_ctl.cmd", 50, 53)])]
    return write(d, g)


def _met_bind(tmp_path):
    """a bind whose banks already meet the rule (the table's own pads applied): pads has nothing to add"""
    g = landing()
    pre = write(tmp_path / "pre", g)
    done = apply(g, P.pads(str(pre), table(g)))
    return write(tmp_path / "met", done), table(done)


def test_pads_refuses_a_bind_with_no_bank_members(tmp_path):
    import pytest
    d = _composite_bind(tmp_path / "b")
    r8t = tmp_path / "r8.json"; r8t.write_text(json.dumps(dict(members=[])))
    out = tmp_path / "out.json"
    with pytest.raises(SystemExit) as e:
        P.pads(str(d), json.loads(r8t.read_text()))
    assert "banks 0" in str(e.value)
    with pytest.raises(SystemExit):
        P.main(["pads", str(d), str(r8t), str(out)])
    assert not out.exists()                                     # nothing written
    assert P.check(RC.Bound(str(d)))[0]["verdict"] == "FAIL"


def test_pads_refuses_zero_member_table_unless_allowed(tmp_path):
    import pytest
    d, t = _met_bind(tmp_path)
    with pytest.raises(SystemExit) as e:
        P.pads(str(d), t)
    assert "0 members" in str(e.value)
    assert P.pads(str(d), t, allow_empty=True)["members"] == []


def test_empty_guard_mutants_are_killed(tmp_path):
    d_bad = _composite_bind(tmp_path / "bad")
    d_met, t_met = _met_bind(tmp_path)
    src = open(P.__file__).read()
    # (mutation, bind, table, message the real guard raises with)
    muts = [("    if not rows:     # EMPTY-GUARD-1125", "    if False:     # EMPTY-GUARD-1125", d_bad, dict(members=[]), "banks 0"),
            ("    if not out and not allow_empty:", "    if False:", d_met, t_met, "0 members")]
    for k, (a, b, d, tab, needle) in enumerate(muts):
        assert src.count(a) == 1, a
        ns = {"__name__": f"pvv_mut{k}", "__file__": P.__file__}
        exec(compile(src.replace(a, b), P.__file__, "exec"), ns)
        for fn, expect in ((P.pads, True), (ns["pads"], False)):       # real guard raises with the needle, the mutant does not
            try:
                fn(str(d), tab)
                msg = ""
            except SystemExit as e:
                msg = str(e)
            assert (needle in msg) == expect, f"mutant {k}: {fn.__module__} -> {msg[:80]!r}"
