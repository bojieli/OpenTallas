#!/usr/bin/env python3
"""KV-KT-E0 2026-11-18 (FABLE-FIX-KV-HG fix #2, KV event D25): the kt input stations of the lanes INSIDE kv3_head_eighth_e0.

A head's K-tree u_kt sits in the eighth core e0 together with lanes 0 and 1.  The other 14 lanes reach it across the
hg / hgi parent, where the stations are parent cells (head_<..>__g_t_<t>__u_kst0 / u_kst1, bind/kv45/
kv_head_kst_netlist.py).  The K-tree adds the 16 lanes edge for edge, so the two in-core lanes need the SAME depth inside
the core, or their scores (and lane 0's valid) arrive `depth` edges early.  This edits the core RTL of the kit
(gen_core_kit_kv.py --head-kst N; results/kv_cores_r5/rtl/kv3_head_eighth_e0/kv3_head_eighth_e0.sv form):

  every member ot_qkh_head_stk_native u_g_t_<t>_u_stk whose kp_o / kpv_o / gf_o nets feed u_u_kt inside the core gets
  ot_qkh_head_kst_native u_g_t_<t>_u_kst0 / u_g_t_<t>_u_kst1 (D = 1 for the first N, else 0 = wires) between the stk
  and the nets the K-tree reads.  Same clock net as the stk.  No port, pin or reset changes: the core LEF / pins file
  and the parent bind are untouched (+34 flops a stage a lane: +136 at depth 2).

Fail closed: not exactly lanes 0 and 1, a station already present, a stk output net with any other reader (a core
output pin would leave early), or a net list this script cannot read bit for bit.
"""
import re

LEAF = "rtl/qwen_sys/split_20261014/ot_qkh_head_kst.sv"
STK = re.compile(r"    ot_qkh_head_stk_native #\(\.MUT\(0\)\) u_g_t_(\d+)_u_stk \(\n(.*?)\n    \);\n", re.S)
KT = re.compile(r"    ot_qkh_ktree_lk(?:_nc32c)? #\([^\n]*\) u_u_kt \(\n(.*?)\n    \);\n", re.S)


def _port(body, name, what):
    m = re.findall(rf"^        \.{name}\((.*)\),?$", body, re.M)
    if len(m) != 1:
        raise ValueError(f"{what}: port {name} found {len(m)} times")
    return m[0]


def _bits(expr, what):
    """'{n1[0], n2[0]}' or 'n1[0]' -> ['n1[0]', ...] (msb first)"""
    e = expr.strip()
    b = [x.strip() for x in e[1:-1].split(",")] if e.startswith("{") else [e]
    if not all(re.fullmatch(r"n\d+\[0\]", x) for x in b):
        raise ValueError(f"{what}: unexpected net expression {expr[:80]!r}")
    return b


def transform(text, depth):
    """(new core RTL, delta record) with `depth` kt stations on the in-core lanes"""
    if depth not in (0, 1, 2):
        raise ValueError(f"--head-kst {depth}: the stations are 0, 1 or 2 stages")
    if "ot_qkh_head_kst_native" in text:
        raise ValueError("the core RTL already carries kt stations")
    if depth == 0:
        return text, dict(depth=0, lanes=[], flops=0)
    kt = KT.findall(text)
    stk = list(STK.finditer(text))
    if len(kt) != 1:
        raise ValueError(f"K-tree instances u_u_kt: {len(kt)} (the stations belong to the eighth that holds the K-tree)")
    lanes = sorted(int(m.group(1)) for m in stk)
    if lanes != [0, 1]:
        raise ValueError(f"in-core stk lanes {lanes}: this edit is for kv3_head_eighth_e0 (lanes 0 and 1)")
    kt_in = {p: _port(kt[0], p, "u_u_kt") for p in ("kp_in", "kpv_in", "gf_in")}
    add, recs = [], []
    for m in stk:
        t, body = m.group(1), m.group(2)
        what = f"u_g_t_{t}_u_stk"
        clk = _port(body, "clk", what)
        outs = {p: _bits(_port(body, p, what), what) for p in ("kp_o", "kpv_o", "gf_o")}
        if [len(outs[p]) for p in ("kp_o", "kpv_o", "gf_o")] != [32, 1, 1]:
            raise ValueError(f"{what}: output widths {[len(v) for v in outs.values()]}")
        new_body = body
        for p, kin in (("kp_o", "kp_in"), ("kpv_o", "kpv_in"), ("gf_o", "gf_in")):
            for net in outs[p]:
                base = net[:-3]
                uses = len(re.findall(rf"\b{base}\b", text))
                # the wire declaration, the stk output, the K-tree input: nothing else may read the early value
                if uses != 3 or net not in kt_in[kin]:
                    raise ValueError(f"{what}.{p} net {base}: {uses} uses (want declaration + stk + u_u_kt.{kin})")
            old = f"        .{p}({_port(body, p, what)})"
            w = "[31:0]" if p == "kp_o" else ""
            new_body = new_body.replace(old, f"        .{p}(kst_t{t}_s_{p[:-2]}{w})")
        text = text.replace(m.group(0), m.group(0).replace(body, new_body))
        add.append(f"    // KV-KT-E0 kt input stations of in-core lane {t} (depth {depth}: uniform with the 14 parent lanes)")
        add.append(f"    wire [31:0] kst_t{t}_s_kp, kst_t{t}_m_kp;")
        add.append(f"    wire kst_t{t}_s_kpv, kst_t{t}_s_gf, kst_t{t}_m_kpv, kst_t{t}_m_gf;")
        add.append(f"    ot_qkh_head_kst_native #(.D(1)) u_g_t_{t}_u_kst0 (.clk({clk}), .kp_i(kst_t{t}_s_kp), .kpv_i(kst_t{t}_s_kpv), "
                   f".gf_i(kst_t{t}_s_gf), .kp_o(kst_t{t}_m_kp), .kpv_o(kst_t{t}_m_kpv), .gf_o(kst_t{t}_m_gf));")
        add.append(f"    ot_qkh_head_kst_native #(.D({1 if depth >= 2 else 0})) u_g_t_{t}_u_kst1 (.clk({clk}), .kp_i(kst_t{t}_m_kp), "
                   f".kpv_i(kst_t{t}_m_kpv), .gf_i(kst_t{t}_m_gf), .kp_o({{{', '.join(outs['kp_o'])}}}), "
                   f".kpv_o({outs['kpv_o'][0]}), .gf_o({outs['gf_o'][0]}));")
        recs.append(dict(lane=int(t), leaves=[f"u_g_t_{t}_u_kst0", f"u_g_t_{t}_u_kst1"], clock=clk))
    k = text.rindex("\nendmodule")
    text = text[:k] + "\n" + "\n".join(add) + text[k:]
    return text, dict(depth=depth, lanes=recs, flops=34 * depth * len(recs), ports_changed=0, pins_changed=0,
                      leaf=LEAF, note="in-core lanes only; the 14 parent lanes take the same depth as hg / hgi parent cells "
                                      "(bind/kv45/kv_head_kst_netlist.py); the score leaves the head `depth` edges later "
                                      "(ECTL HXK + depth, attention calendar D_QK + depth: tools/qwen_kv_die/kv_head_kst.py)")
