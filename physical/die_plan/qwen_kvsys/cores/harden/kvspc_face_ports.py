#!/usr/bin/env python3
"""KV-CORE-RTL/PC 10-25: kvs_pc / kvs_pc_h_head_p boundary recut (kit-copy RTL transform, gen_core_kit_kv.py
--kvspc-face-ports).  Fixes the kit preflight (face_guard) classes found on the A/B kits
(shared 1716 / 928, dropped 258 / 282, merged 48, unregistered 1 / 8):

  1. one clock (owner decision 14, 10-24: kvs_pc hck = the die clock): the core wrapper drops the hck pin and the
     forwarded HBM data clocks pc__front_hbm_data[3:0] / pc__return_hbm_data[3:0] (used only as clocks inside: 2112 /
     576 clock loads each); every hck / pll_hbm_data entry of the leaf is bound to ck.  The CDC FIFOs stay (same-clock
     FIFOs, latency unchanged: 0 cycles); replacing them by plain registers (decision 16a) is a separate step.
  2. dead pins (plan drop, NOT tied at a pin): pc__land_er[258:1] (landing read-return data: no landing reads exist on
     the static die; the chain station reads only land_er[0] / [259] / [260]) and, on the chain head h_head_p only
     (no ko pin), pc__ki[30:21] / pc__ki[14:1] (the kc word bits the tap does not decode).  The wrapper keeps the
     live bits as ports (`pc__land_er` [0:0] + `pc__land_er_259` [260:259]; head `pc__ki` [0:0] + `pc__ki_15` [20:15] +
     `pc__ki_31` [32:31]) and binds the leaf's dead bits to constants that have no load inside.
  3. kc chain station (ki / ko shared one tap flop): ki lands in its own pin flops (kq_v / kq_d), the controller
     command is decoded after them (exactly the old tap c_v / c_d registers: 0 cycles for this PC's command); ko is a
     separate output register of kq (+1 hclk per kc chain station, pre-ownership command path only).
  4. fi (combinational into the fo OR): lands in a pin flop fi_q first (+1 fault visibility edge for the upstream
     fault only; local faults unchanged).
  5. po (port flop also loaded by u_obs / u_cdc / the idle veto): private port flop `po` (keep, loaded only by the pin)
     + internal copy po_i with the identical next state (same edge, same reset) feeding every internal consumer
     (0 cycles; also keeps opt_merge from folding po[3] into po[2]).
  6. land_es (hold loop on the port flop): private port flop with next state from the internal copy les_i
     (port <= bh ? new : les_i), 0 cycles.
`mut` (tb only) injects one error per fix so the miter proves it observes each change:
  mut 1 = ko data bit 5 flipped, mut 2 = decoded layer +1, mut 3 = fi_q dropped from fo, mut 4 = po_i bit 28 stuck 0
  (internal consumers), mut 5 = land_es port copy bit 7 inverted.
"""
import re
import sys
from pathlib import Path

LAND_DEAD = list(range(1, 259))
HEAD_KI_DEAD = list(range(1, 15)) + list(range(21, 31))


def _module(text, name):
    i = text.index("module " + name + " ")
    j = text.index("endmodule", i) + len("endmodule")
    return i, j


def _sub1(s, old, new):
    assert s.count(old) == 1, (s.count(old), old[:120])
    return s.replace(old, new)


def sched_nc(text, mut=0):
    i, j = _module(text, "qkd_ctrl_pc_sched_nc")
    s = text[i:j]
    # (po) the column-delay line dv/dwe/dsr[0] has the same next state as po[28]/[29]: keep it so synthesis does not merge
    # it into the (kept) port flop and hang a second load on the pin net (preflight 10-25: pc__po[29:28] shared)
    s = _sub1(s, "    reg  [LW:0] dv, dwe, dsr;", "    (* keep *) reg  [LW:0] dv, dwe, dsr;")
    # (3) kc chain station: ki pin flops, decode after them, separate ko output register
    s = _sub1(s, """    ot_qkvd_kcmd_tap #(.ROW0(ROW0)) u_tap (.clk(hclk), .rst_n(h_rn), .i_v(ki[0]), .i_d(ki[32:1]),
        .o_v(ko[0]), .o_d(ko[32:1]), .c_v(tc_v), .c_d(tc_d));""",
              """    // KV-CORE-RTL/PC 10-25: ki lands in its own pin flops (kq); the command is decoded after them (= the tap's c_v /
    // c_d registers, 0 cycles); ko is a separate output register of kq (+1 hclk per kc chain station).
    (* keep *) reg kq_v; (* keep *) reg [31:0] kq_d;
    always @(posedge hclk or negedge h_rn) if (!h_rn) kq_v <= 1'b0; else kq_v <= ki[0];
    always @(posedge hclk) kq_d <= ki[32:1];
    wire [5:0] kq_layer = kq_d[19:14]""" + (" + 6'd1" if mut == 2 else "") + """;
    assign tc_v = kq_v && (kq_d[31:30] == 2'd0 || kq_d[31:30] == 2'd1);
    assign tc_d = (kq_d[31:30] == 2'd0) ? {2'd0, 11'd1024, 19'(ROW0 + kq_layer)} : {2'd1, 30'd0};
    (* keep *) reg ko_v; (* keep *) reg [31:0] ko_d;
    always @(posedge hclk or negedge h_rn) if (!h_rn) ko_v <= 1'b0; else ko_v <= kq_v;
    always @(posedge hclk) ko_d <= kq_d""" + (" ^ 32'd32" if mut == 1 else "") + """;
    assign ko = {ko_d, ko_v};""")
    # (4) fi pin flop
    s = _sub1(s, "else fo <= fo | fi | ctl_fault", "else fo <= fo | " + ("1'b0" if mut == 3 else "fi_q") + " | ctl_fault")
    s = _sub1(s, "    // ---- sticky fault chain, S -> N",
              "    (* keep *) reg fi_q;   // KV-CORE-RTL/PC 10-25: fi pin flop (+1 fault visibility edge for the upstream fault)\n"
              "    always @(posedge hclk) fi_q <= fi;\n    // ---- sticky fault chain, S -> N")
    # (5) po: private port flop + internal copy po_i
    s = _sub1(s, "    output reg [327:0] po,\n", "    (* keep *) output reg [327:0] po,\n    output reg [327:0] po_i,\n")
    old = ("      if(!h_rn)begin po<=0;physical_col_sr<=0;end\n"
           "      else begin po<={wd,col_col,col_bank,col_we,col_v,row_row,row_bank,row_op,row_v};physical_col_sr<=col_sr;end\n")
    new = ("      if(!h_rn)begin po<=0;po_i<=0;physical_col_sr<=0;end\n"
           "      else begin po<={wd,col_col,col_bank,col_we,col_v,row_row,row_bank,row_op,row_v};"
           "po_i<={wd,col_col,col_bank,col_we," + ("1'b0" if mut == 4 else "col_v") + ",row_row,row_bank,row_op,row_v};"
           "physical_col_sr<=col_sr;end\n")
    s = _sub1(s, old, new)
    # internal po readers -> po_i (the idle veto / drain activity)
    body_start = s.index("    // KV corrected returns include tag")
    tail = s[body_start:]
    tail = re.sub(r"(?<![\w.])po\[(0|28)\]", r"po_i[\1]", tail)
    s = s[:body_start] + tail
    assert "(* keep *) reg [327:0] po_i" not in s
    s = s.replace("    output reg [327:0] po_i,\n", "    (* keep *) output reg [327:0] po_i,\n")
    text = text[:i] + s + text[j:]
    # parent: u_cdc / u_obs read po_i
    i, j = _module(text, "qkd_ctrl_pc_host_static_nc")
    p = text[i:j]
    p = _sub1(p, "    wire [346:0] physical_context;\n", "    wire [346:0] physical_context;\n    wire [327:0] po_i;   // KV-CORE-RTL/PC: internal copy of po\n")
    p = _sub1(p, ".po(po), .pi_v(pi[0])", ".po(po), .po_i(po_i), .pi_v(pi[0])")
    p = _sub1(p, ".col_v(po[28]), .col_we(po[29])", ".col_v(po_i[28]), .col_we(po_i[29])")
    p = _sub1(p, ".hrst(hrst), .po(po), .static_column", ".hrst(hrst), .po(po_i), .static_column")
    return text[:i] + p + text[j:]


def chain_land(text, mod, mut=0):
    i, j = _module(text, mod)
    s = text[i:j]
    s = _sub1(s, "    always @(posedge ck) if (bh) land_es[287:1] <= {1'b1, 1'b1, c[F_AD +: 29], c[F_D0 +: 256]};\n",
              "    // KV-CORE-RTL/PC 10-25: land_es[287:1] private port flops (no hold loop on the pin flop): next state from the\n"
              "    // internal copy les_i (port <= bh ? new : les_i), equal on every edge (0 cycles)\n"
              "    (* keep *) reg [287:1] les_i;\n"
              "    wire [287:1] les_n = {1'b1, 1'b1, c[F_AD +: 29], c[F_D0 +: 256]};\n"
              "    always @(posedge ck) if (bh) les_i <= les_n;\n"
              "    always @(posedge ck) land_es[287:1] <= (bh ? les_n : les_i)" + (" ^ 287'd64" if mut == 5 else "") + ";\n")
    s = re.sub(r"output reg (\s*)\[287:0\](\s*)land_es,", r"(* keep *) output reg\1[287:0]\2land_es,", s, count=1)
    assert "(* keep *) output reg" in s
    return text[:i] + s + text[j:]


def _port_split(text, port, width, keep_ranges, dead):
    """wrapper port `port` [width-1:0] -> live pieces; returns (text, leaf binding expr, piece names)"""
    hi = width - 1
    decl = f"    input wire [{hi}:0] {port},\n"
    pieces = []
    for lo_, hi_ in keep_ranges:
        nm = port if lo_ == 0 else f"{port}_{lo_}"
        pieces.append((nm, hi_, lo_))
    newdecl = "".join(f"    input wire [{h}:{l}] {n},\n" for n, h, l in pieces)
    text = _sub1(text, decl, newdecl)
    # binding expression, MSB first
    items = []
    b = hi
    for n, h, l in sorted(pieces, key=lambda x: -x[1]):
        if b > h:
            items.append(f"{b - h}'d0")
        items.append(f"{n}[{h}:{l}]")
        b = l - 1
    if b >= 0:
        items.append(f"{b + 1}'d0")
    assert sum(1 for x in range(width) if not any(l <= x <= h for _, h, l in pieces)) == len(dead)
    return text, "{" + ", ".join(items) + "}", pieces


def wrapper(text, mod, head=False):
    i, j = _module(text, mod)
    s = text[i:j]
    # (1) one clock: drop hck + forwarded HBM data clocks, bind them to ck
    for d in ("    input wire [0:0] hck,\n", "    input wire [3:0] pc__front_hbm_data,\n", "    input wire [3:0] pc__return_hbm_data,\n"):
        s = _sub1(s, d, "")
    s = _sub1(s, ".hck(hck[0])", ".hck(ck[0])")
    s = _sub1(s, ".pc__front_hbm_data(pc__front_hbm_data[3:0])", ".pc__front_hbm_data({4{ck[0]}})")
    s = _sub1(s, ".pc__return_hbm_data(pc__return_hbm_data[3:0])", ".pc__return_hbm_data({4{ck[0]}})")
    # (2) dead pins
    s, expr, _ = _port_split(s, "pc__land_er", 261, [(0, 0), (259, 260)], LAND_DEAD)
    s = _sub1(s, ".pc__land_er(pc__land_er[260:0])", f".pc__land_er({expr})   /* [258:1] dead: plan drop, no load inside */")
    if head:
        s, expr, _ = _port_split(s, "pc__ki", 33, [(0, 0), (15, 20), (31, 32)], HEAD_KI_DEAD)
        s = _sub1(s, ".pc__ki(pc__ki[32:0])", f".pc__ki({expr})   /* chain head (no ko): [30:21] [14:1] dead, plan drop */")
    s = s.replace("module " + mod + " (", "// KV-CORE-RTL/PC 10-25 (kvspc_face_ports.py): one clock (hck / HBM data clocks := ck), dead pins dropped\nmodule " + mod + " (", 1)
    return text[:i] + s + text[j:]


def pins_update(pins, head=False):
    """the in-memory plan delta the preflight needs before KV-PLAN3 lands it: drop hck / HBM data clock / dead pins,
    rename the live pieces of split buses"""
    out = []
    drop_bus = {"hck", "pc__front_hbm_data", "pc__return_hbm_data"}
    for p in pins:
        b, k = p["bus"], p.get("bit")
        if b in drop_bus:
            continue
        if b == "pc__land_er":
            if k in LAND_DEAD:
                continue
            if k >= 259:
                p = dict(p, bus="pc__land_er_259")
        if head and b == "pc__ki":
            if k in HEAD_KI_DEAD:
                continue
            if 15 <= k <= 20:
                p = dict(p, bus="pc__ki_15")
            elif k >= 31:
                p = dict(p, bus="pc__ki_31")
        out.append(p)
    return out


def dropped_pins(head=False):
    d = ["hck[0]"] + [f"pc__front_hbm_data[{k}]" for k in range(4)] + [f"pc__return_hbm_data[{k}]" for k in range(4)]
    d += [f"pc__land_er[{k}]" for k in LAND_DEAD]
    if head:
        d += [f"pc__ki[{k}]" for k in HEAD_KI_DEAD]
    return d


def apply_kit(rtl_dir, mod, mut=0):
    d = Path(rtl_dir)
    head = mod.endswith("_h_head_p")
    p = d / "qkd_ctrl_pc_nc.sv"
    p.write_text(sched_nc(p.read_text(), mut))
    cs = "qkd_kv_pc_chain_station_b_p" if head else "qkd_kv_pc_chain_station_b"
    p = d / f"{cs}.sv"
    p.write_text(chain_land(p.read_text(), cs, mut))
    p = d / f"{mod}.sv"
    p.write_text(wrapper(p.read_text(), mod, head))


if __name__ == "__main__":
    apply_kit(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 0)


def core_json_update(cj):
    """gen_core_kit_kv.py --kvspc-face-ports: the same delta on the core json (pin classes / port declarations)"""
    head = cj["module"].endswith("_h_head_p")
    gone = {"hck", "pc__front_hbm_data", "pc__return_hbm_data"}
    pc, pd = {}, {}
    for n, c in cj["pin_class"].items():
        b, k = (n.split("[")[0], int(n.split("[")[1][:-1])) if "[" in n else (n, None)
        q = dict(bus=b, bit=k)
        r = pins_update([q], head)
        if r:
            nb = r[0]["bus"]
            pc[f"{nb}[{k}]" if k is not None else nb] = c
    for b, d in cj["port_decl"].items():
        if b in gone:
            continue
        if b == "pc__land_er":
            pd["pc__land_er"] = ["input", 0, 0]
            pd["pc__land_er_259"] = ["input", 260, 259]
        elif head and b == "pc__ki":
            pd["pc__ki"] = ["input", 0, 0]
            pd["pc__ki_15"] = ["input", 20, 15]
            pd["pc__ki_31"] = ["input", 32, 31]
        else:
            pd[b] = d
    cj["pin_class"], cj["port_decl"] = pc, pd
    cj["report"]["clock_nets"] = {"clk": "ck"}
    return cj


def plan_pins_update(pins, head=False):
    """plan pins (name = 'bus[bit]') -> the same delta as pins_update (gen_core_kit_kv.py, in memory)"""
    out = []
    for p in pins:
        n = p["name"]
        b, k = (n.split("[")[0], int(n.split("[")[1][:-1])) if "[" in n else (n, None)
        r = pins_update([dict(bus=b, bit=k)], head)
        if r:
            out.append(dict(p, name=f"{r[0]['bus']}[{k}]" if k is not None else r[0]["bus"]))
    return out
