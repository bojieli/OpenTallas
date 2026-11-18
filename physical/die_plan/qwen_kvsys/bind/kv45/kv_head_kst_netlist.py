#!/usr/bin/env python3
"""KV-KT-E0 2026-11-18 (FABLE-FIX-KV-HG fix #2, KV event D25): the KV as-built netlist with the head kt input stations.

The bound KV netlist is flat: a head is its leaves head_<st>_<e>_<h>__g_t_<t>__u_stk -> head_<..>__u_kt
(ot_qkh_ktree_lk reads kp_k / kpv_k / gf_k of all 16 lanes).  The eighth core e0 holds u_kt and lanes 0, 1; the other
14 lanes cross the hg / hgi parent unregistered, 1.1 - 1.8 mm (192+ setup ends at -251 ps).  This derivation is exactly
the netlist of the generated head ot_qkh_head_native_r4_s_lk_kst #(.KT_ST(D)) (tools/qwen_kv_die/head_st_rtl.py;
lock-step rtl/test/qwen_kv_die/tb_qkh_head_kst.sv), on every one of the 128 heads:

  ot_qkh_head_stk_native  head_X__g_t_<t>__u_stk    .kp_o / .kpv_o / .gf_o  -> new nets n_head_X__{kp,kpv,gf}_s
  ot_qkh_head_kst_native  head_X__g_t_<t>__u_kst0   _s -> _m     (D 1)                     new leaf, same clock net as the stk
  ot_qkh_head_kst_native  head_X__g_t_<t>__u_kst1   _m -> _k     (D 1 at depth 2, else 0)  new leaf; u_kt reads _k as before
  qkd_ectl3_kiss_st       ectl_<st>_<e>             .HXK(13) -> .HXK(13 + D)   (the score tag depth; ECTLK q0..q3 re-harden)

and nothing else (every other line is byte-identical).  The same depth on all 16 lanes; the two lanes whose stk sits in e0
(t = 0, 1) keep their stations INSIDE that core (composition members; core kit gen_core_kit_kv.py --head-kst D), lanes
2..15 are hg / hgi parent cells sited as relay chains (budgets.relay_mid_re_types, kv_head_kst.RELAY_MID_RE_ALT).

Derived inputs for the event (opt-in: nothing on main reads them until an as-built names them):
  bind/kv45/die_bound_native_mission_lc_kst<D>.v.gz                       asbuilt.netlist   (committed for depth 2)
  plan_of_record/inputs/asbuilt_map_binder2_kst<D>.json                   asbuilt.map_file  (+ the 4,096 station leaves, each in
                                                                          the partition of its lane's stk)     written by --event
  plan_of_record/inputs/composition_heads_astk_pv_1103_kst<D>.json.gz     asbuilt.compose   (kv3_head_eighth_e0 members + the
                                                                          four in-core station leaves; ports unchanged)  --event

  kv_head_kst_netlist.py [--depth 2]            write the netlist
  kv_head_kst_netlist.py [--depth 2] --event    write the netlist + the map + the composition (the event tree commits them)
  kv_head_kst_netlist.py [--depth 2] --check    fail if the committed netlist is stale
"""
import argparse
import gzip
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
POR = HERE.parents[1] / "plan_of_record" / "inputs"
SRC = HERE / "die_bound_native_mission_lc.v.gz"
MAP = POR / "asbuilt_map_binder2.json"
CMP = POR / "composition_heads_astk_pv_1103.json.gz"
N_HEADS, LANES, E0_LANES, N_ECTL, HXK0 = 128, 16, (0, 1), 32, 13
STK = re.compile(r"^(\s*)ot_qkh_head_stk_native #\(\.MUT\(0\)\) (head_\w+?)__g_t_(\d+)__u_stk \(\.clk\(([^)]+)\), (.*)\);$")
WIRE = re.compile(r"^(\s*wire \[(?:15|511):0\] n_(head_\w+?)__(kp|kpv|gf))_k;$")


def outs(d):
    return (HERE / f"die_bound_native_mission_lc_kst{d}.v.gz", POR / f"asbuilt_map_binder2_kst{d}.json",
            POR / f"composition_heads_astk_pv_1103_kst{d}.json.gz")


def leaves(head, t):
    return [f"{head}__g_t_{t}__u_kst0", f"{head}__g_t_{t}__u_kst1"]


def derive(text, depth):
    """the netlist with `depth` kt stations a lane on every head and HXK 13 + depth on every ECTL"""
    if depth not in (1, 2):
        raise ValueError(f"depth {depth}: 1 or 2 (0 is the netlist of record)")
    out, n = [], dict(stk=0, wire=0, ectl=0)
    heads = set()
    for line in text.split("\n"):
        w = WIRE.match(line)
        if w:
            out.append(line)
            out += [f"{w.group(1)}_s;", f"{w.group(1)}_m;"]
            n["wire"] += 1
            continue
        if "ot_qkh_head_stk_native" in line:
            m = STK.match(line)
            assert m, line[:200]
            ind, head, t, clk, rest = m.groups()
            t = int(t)
            net = f"n_{head}__"
            sl = f"[{32 * t + 31}:{32 * t}]"
            pins = {"gf_o": f"{net}gf_k[{t}]", "kp_o": f"{net}kp_k{sl}", "kpv_o": f"{net}kpv_k[{t}]"}
            new = line
            for p, e in pins.items():
                old = f".{p}({e})"
                assert new.count(old) == 1, (head, t, p)
                new = new.replace(old, f".{p}({e.replace('_k[', '_s[')})")
            out.append(new)
            for k, (a, b) in enumerate((("_s[", "_m["), ("_m[", "_k["))):
                c = {p: (e.replace("_k[", a), e.replace("_k[", b)) for p, e in pins.items()}
                out.append(f"{ind}ot_qkh_head_kst_native #(.D({1 if k < depth else 0})) {leaves(head, t)[k]} (.clk({clk}), "
                           f".gf_i({c['gf_o'][0]}), .gf_o({c['gf_o'][1]}), .kp_i({c['kp_o'][0]}), .kp_o({c['kp_o'][1]}), "
                           f".kpv_i({c['kpv_o'][0]}), .kpv_o({c['kpv_o'][1]}));")
            n["stk"] += 1
            heads.add(head)
            continue
        if "qkd_ectl3_kiss_st #(" in line:
            old = f".HXK({HXK0})"
            assert line.count(old) == 1, line[:160]
            line = line.replace(old, f".HXK({HXK0 + depth})")
            n["ectl"] += 1
        out.append(line)
    assert n == dict(stk=N_HEADS * LANES, wire=3 * N_HEADS, ectl=N_ECTL) and len(heads) == N_HEADS, (n, len(heads))
    return "\n".join(out)


def derive_map(m):
    """as-built instance map + the station leaves, each in the partition of its lane's stk"""
    parts = dict(m["parts"])
    add = 0
    for k, v in list(m["parts"].items()):
        x = re.fullmatch(r"(head_\w+?)__g_t_(\d+)__u_stk", k)
        if not x:
            continue
        assert len(v) == 2, (k, v)
        part, name = v
        y = re.fullmatch(r"(head\d+)__g_t_(\d+)__u_stk", name)
        assert y and y.group(2) == x.group(2), (k, name)
        for leaf, local in zip(leaves(x.group(1), int(x.group(2))), leaves(y.group(1), int(y.group(2)))):
            assert leaf not in parts
            parts[leaf] = [part, local]
            add += 1
    assert add == 2 * N_HEADS * LANES, add
    return dict(m, parts=dict(sorted(parts.items())) if list(m["parts"]) == sorted(m["parts"]) else parts)


def derive_compose(c):
    """composition + the in-core station leaves as members of every kv3_head_eighth_e0 (ports unchanged: both of a
    station's nets stay inside the core)"""
    cores, n = [], 0
    for core in c["cores"]:
        if core.get("module") == "kv3_head_eighth_e0":
            kt = [x for x in core["members"] if x.endswith("__u_kt")]
            assert len(kt) == 1, core["inst"]
            head = kt[0][:-len("__u_kt")]
            assert all(f"{head}__g_t_{t}__u_stk" in core["members"] for t in E0_LANES), core["inst"]
            core = dict(core, members=sorted(core["members"] + [x for t in E0_LANES for x in leaves(head, t)]))
            n += 1
        cores.append(core)
    assert n == N_HEADS, n
    return dict(c, cores=cores)


def build_event(depth):
    """(map text, composition text) in the form of their sources (json.dumps defaults)"""
    return (json.dumps(derive_map(json.loads(MAP.read_text()))),
            json.dumps(derive_compose(json.loads(gzip.decompress(CMP.read_bytes())))))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth", type=int, default=2)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--event", action="store_true")
    a = ap.parse_args()
    net = derive(gzip.decompress(SRC.read_bytes()).decode(), a.depth)
    f_net, f_map, f_cmp = outs(a.depth)
    if a.check:
        ok = f_net.is_file() and gzip.decompress(f_net.read_bytes()).decode() == net
        sys.exit(0 if ok else f"STALE {f_net}: rerun {Path(__file__).name}")
    f_net.write_bytes(gzip.compress(net.encode(), mtime=0))
    print("wrote", f_net)
    if a.event:
        mp, cm = build_event(a.depth)
        f_map.write_text(mp)
        f_cmp.write_bytes(gzip.compress(cm.encode(), mtime=0))
        print("wrote", f_map, f_cmp, sep="\n  ")
    print(f"depth {a.depth}: {N_HEADS * LANES * 2} station leaves ({N_HEADS * len(E0_LANES) * 2} in e0 cores, "
          f"{N_HEADS * (LANES - len(E0_LANES)) * 2} parent cells), {N_ECTL} ECTL HXK {HXK0} -> {HXK0 + a.depth}")
