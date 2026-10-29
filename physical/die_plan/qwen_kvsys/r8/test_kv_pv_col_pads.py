"""DIE-KV-14d: PV column equalisation pads -> the MAIN regen_constants kv_pv_trunk law is OK on the padded depths, and the
param hook's law agrees (fail closed before the pads).  Synthetic 2 x 32-column pair shaped like die-kv-13 bind5
(as-built staggered trunk 56..14 / 55..13, landed -10..+8, flag returns 5..78)."""
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3] / "tools/die_plan"))
import kv_pv_col_pads as P  # noqa: E402
import regen_constants as RC  # noqa: E402
import r8  # noqa: E402

TD, FD = 54, 58
DCMD = [7, 6, 3, 0, -1, -5, -8, -10]          # landed - as-built per trunk station (bind5 pvw_0 s0..s7)


def landing():
    groups = []
    for k, side_off in ((0, 0), (1, 1)):
        pvw = f"pvw_{k}"
        flags = []
        for c in range(32):
            st, grp = c % 8, c // 8
            ca = 56 - 6 * st - side_off - (grp % 2)          # as-built cmd (s8.. one stage shorter, like bind5)
            cl = ca + DCMD[st] + (grp % 2)
            fa = 58 + 6 * st
            fl = max(5, 78 - 9 * st - 2 * grp)
            mk = lambda port, bits, src, sb, a, b: dict(sink_port=port, sink_bits=[bits], source=src, source_bits=[sb],
                                                        asbuilt_stages=a, bound_stages=b, landed_stages=b, lane="L1")
            groups.append(dict(sink=f"{pvw}__u_s{c}_j", sink_part=f"pv_{k}_{st}", src_part="hub_C",
                               members=[mk("join_go", [0, 0], f"{pvw}__u_ctl.cmd", [31, 31], ca, cl)]))
            for b in range(2):
                groups.append(dict(sink=f"{pvw}__u_s{c}_b{b}", sink_part=f"pv_{k}_{st}", src_part="hub_C",
                                   members=[mk("bc", [0, 22], f"{pvw}__u_ctl.cmd", [8, 30], ca, cl)]))
            flags += [mk("col_valid", [c, c], f"{pvw}__u_s{c}_j.y_valid", [0, 0], fa, fl),
                      mk("col_fault", [c, c], f"{pvw}__u_s{c}_j.fault", [0, 0], fa, fl)]
        groups.append(dict(sink=f"{pvw}__u_ctl", sink_part="hub_C", src_part="pv", members=flags))
    return groups


def r8_table(groups):
    ms = []
    for g in groups:
        for m in g["members"]:
            ms.append(dict(id=r8.mkey(g, m), sink=g["sink"], sink_part=g["sink_part"], src_part=g["src_part"],
                           sink_port=m["sink_port"], sink_bits=m["sink_bits"], source=m["source"],
                           asbuilt=m["asbuilt_stages"], bound=m["bound_stages"], pad=0, landed=m["landed_stages"], lane="L1"))
    return dict(schema=r8.SCHEMA, die="qwen_kvsys", members=ms)


def write_bind(d, groups, applied=None):
    d.mkdir(parents=True, exist_ok=True)
    (d / "bus_groups.json").write_text(json.dumps(dict(die="qwen_kvsys", landing=groups, replica=[])))
    ch = [dict(inst=f"pvw_{k}__u_ctl", param=p, asbuilt=str(v), bound=(applied or {}).get(p, v))
          for k in (0, 1) for p, v in (("TRUNK_D", TD), ("FLAG_D", FD))]
    (d / "param_regen.json").write_text(json.dumps(dict(file="hook", changed=ch, record={})))


def law(d):
    o = RC.Out("qwen_kvsys", RC.Bound(d))
    RC.kv_pv_trunk(o)
    o.crosscheck()
    return o.c["TRUNK_D"], o.c["FLAG_D"]


def apply(groups, table):
    by = {m["id"]: m for m in table["members"]}
    for g in groups:
        for m in g["members"]:
            x = by.get(r8.mkey(g, m))
            if x:
                m["landed_stages"] = x["landed"]
    return groups


def test_unpadded_law_mismatch():
    with tempfile.TemporaryDirectory() as t:
        write_bind(Path(t), landing())
        tr, fl = law(t)
        assert tr["status"] == "MISMATCH" and fl["status"] == "MISMATCH"    # law != as-built 54/58 left in the RTL


def test_pads_make_law_exact_and_hook_agrees():
    with tempfile.TemporaryDirectory() as t:
        g = landing()
        write_bind(Path(t) / "b0", g)
        tab = P.pads(Path(t) / "b0", r8_table(g))
        s = tab["summary"]
        assert s["C"] == 8 and s["TRUNK_D"] == TD + 8
        assert all(m["pad"] >= 0 and m["landed"] == m["bound"] + m["pad"] for m in tab["members"])
        # padded bind with the hook-applied parameters: law OK (uniform) and equal to the RTL
        g2 = apply(landing(), tab)
        write_bind(Path(t) / "b1", g2, dict(TRUNK_D=s["TRUNK_D"], FLAG_D=s["FLAG_D"]))
        tr, fl = law(Path(t) / "b1")
        assert (tr["status"], fl["status"]) == ("OK", "OK"), (tr, fl)
        assert (tr["value"], fl["value"]) == (s["TRUNK_D"], s["FLAG_D"])
        # minimality: the column with the largest command delta gets no command pad
        assert min(r["cmd_pad"] for r in tab["law"]["columns"].values()) == 0
        # re-running the generator on the padded bind owes nothing
        again = P.pads(Path(t) / "b1", r8_table(g2))
        assert again["summary"]["pad_flops"] == 0 and again["summary"]["FLAG_D"] == s["FLAG_D"]


def _ctx(groups):
    cells, idx = [], {}

    def cell(path, module="leaf", params=None):
        if path not in idx:
            idx[path] = len(cells)
            cells.append(SimpleNamespace(path=path, module=module, ytype=module, params=params or {}))
        return idx[path]
    for k in (0, 1):
        cell(f"pvw_{k}__u_ctl", "ot_qwen_tp8_pv_wide_ctl_tbf_p", {"TRUNK_D": str(TD), "FLAG_D": str(FD)})
    sinks, bitcyc = {}, {}
    for g in groups:
        ci = cell(g["sink"])
        for m in g["members"]:
            sp, spn = m["source"].rsplit(".", 1)
            si = cell(sp)
            for i in range(m["sink_bits"][0][0], m["sink_bits"][0][1] + 1):
                key = (g["src_part"], g["sink_part"], si, spn, i)
                bitcyc[key] = m["bound_stages"]
                pad = m["landed_stages"] - m["bound_stages"]
                sinks[(ci, m["sink_port"], i)] = ("x", g["src_part"], si, spn, i, m["asbuilt_stages"], g["sink_part"]) + \
                    ((pad,) if pad else ())
    return SimpleNamespace(F=SimpleNamespace(cells=cells), sinks=sinks, bitcyc=bitcyc, param_defaults={})


def test_hook_law():
    import importlib.util
    spec = importlib.util.spec_from_file_location("hook", HERE / "kv_pv_col_regen.py")
    H = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(H)
    try:
        H.pv_trunk(_ctx(landing()))
        raise AssertionError("hook must fail closed on an unpadded bind")
    except ValueError as e:
        assert "not equalised" in str(e)
    with tempfile.TemporaryDirectory() as t:
        g = landing()
        write_bind(Path(t), g)
        tab = P.pads(Path(t), r8_table(g))
    params, rec = H.pv_trunk(_ctx(apply(landing(), tab)))
    assert params == {f"pvw_{k}__u_ctl": dict(TRUNK_D=tab["summary"]["TRUNK_D"], FLAG_D=tab["summary"]["FLAG_D"])
                      for k in (0, 1)}


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
            print("PASS", n)
