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


if __name__ == "__main__":
    test_fail_pad_pass_mutant()
    test_v_after_command_fails_closed()
    print("2 passed")
