"""DIE-KV-64/RF-E 11-03 RE-FORM RF-KV1 of ot_nhb_zh (AHUB hard child; two strikes: native151 TT -22.83 / FF -13.47 /
slew 1202, then ECO A1 on the same placement-buffer nets).

Failure cause ([CHECKED] zh_native151_model signoff/tt/sta.log + RCX probe of DIE-KV-63/ahub): each of the 16 read
ports g_z[gz].g_b[gb].g_f[gf] takes a registered 6-bit node address (ot_nhb_dup_a6 u_a) and reads 16 b out of 64
entries of zm (64:1 mux, zv-masked).  Every address bit therefore drives the full mux tree (up to 512 loads), which
the tool buffers into fanout-64 placement-buffer chains (place*/fanout*, slew 330-404 ps vs 320; 3 x ~100 ps on the
worst TT path g_z[0].g_b[0].g_f[1].u_a/q[1] -> za_r[17]).

Form (0 cycles, exact): the read address is captured PRE-DECODED.  Each port's kept register module ot_nhb_rf1_pd
holds onehot(d[5:3]) and onehot(d[2:0]) (2 x 8 FF) from the same D the old u_a captured; entry a of the port is
selected by hi[a/8] & lo[a%8] (one AND2 per entry, each pre-decode bit drives 8 AND2), and the 16-b read is an
AND-OR over the 64 entries, so no select net fans out > 16.  hi/lo == onehot(old a) on every edge (no reset, like
u_a), so rd and the za_r / zb_r captures are unchanged.
Added flops: 16 ports x (16 - 6) = +160 FF (PG XCHECK-1: 160 / 0.0229 mm2 = 7.0k bits/mm2 in the ZH outline,
0.6k bits/mm2 over the AHUB slot 604.8 x 440.64 that carries it).
"""
import hashlib
import json
import re
from pathlib import Path

MOD = "ot_nhb_zh"
OLD = """                (* keep_hierarchy *) ot_nhb_dup_a6 u_a (.clk(clk), .d({zg_p, pzz[4:0]}), .q(a));
                wire [6:0]  ix = {a[5], a[4:0], gb[0]};
                wire [15:0] rd = zv[ix] ? zm[32*ix + 16*gf +: 16] : 16'd0;
"""
NEW = """                // RF-KV1 (DIE-KV-64/RF-E 11-03, zh_rf1.py): pre-decoded registered read address, <= 16 loads per bit
                wire [7:0] ahi, alo;
                (* keep_hierarchy *) ot_nhb_rf1_pd u_a (.clk(clk), .d({zg_p, pzz[4:0]}), .hi(ahi), .lo(alo));
                wire [15:0] rd = rf1_rd(ahi, alo, zv, zm, gb, gf);
"""
FUNC = """    // RF-KV1: 16-b read of port (gb, gf): OR over the 64 entries {a, gb} of (hi[a/8] & lo[a%8] & zv) & zm
    function automatic [15:0] rf1_rd(input [7:0] hi, input [7:0] lo, input [127:0] v, input [32*128-1:0] m,
                                     input integer b, input integer f);
        integer e;
        begin
            rf1_rd = 16'd0;
            for (e = 0; e < 64; e = e + 1)
                rf1_rd = rf1_rd | ({16{hi[e / 8] & lo[e % 8] & v[2*e + b]}} & m[32*(2*e + b) + 16*f +: 16]);
        end
    endfunction
"""
MODS = """
(* keep_hierarchy *) module ot_nhb_rf1_pd (input wire clk, input wire [5:0] d, output reg [7:0] hi, output reg [7:0] lo);
    always @(posedge clk) begin hi <= 8'd1 << d[5:3]; lo <= 8'd1 << d[2:0]; end
endmodule
"""


def transform(text):
    """-> rewritten ot_nhb_tiles.sv text; fail-closed on any unexpected shape"""
    if len(re.findall(rf"^module {MOD}\b", text, re.M)) != 1:
        raise ValueError(f"zh_rf1: expected one module {MOD}")
    if "rf1_" in text:
        raise ValueError("zh_rf1: already applied")
    if text.count(OLD) != 1:
        raise ValueError("zh_rf1: ZH read port (u_a / ix / rd) not in the expected form")
    anchor = "    localparam integer ZW = 4, ADD_LAT = 7;\n"
    start = text.index(f"module {MOD}")
    if text.count(anchor) != 1 or text.index(anchor) < start:
        raise ValueError("zh_rf1: ZH localparam anchor missing")
    for decl in ("reg [32*128-1:0] zm;", "reg [127:0]      zv;"):
        if decl not in text:
            raise ValueError(f"zh_rf1: {decl} not found")
    text = text.replace(anchor, anchor + FUNC, 1).replace(OLD, NEW, 1)
    return text + MODS


def apply_kit(kd, mod):
    kd = Path(kd)
    if mod != MOD:
        raise SystemExit(f"--zh-rf1 only applies to {MOD}")
    srcs = [p for p in sorted((kd / "rtl").glob("*.sv")) if re.search(rf"^module {MOD}\b", p.read_text(), re.M)]
    if len(srcs) != 1:
        raise SystemExit(f"--zh-rf1: expected one {MOD} source in the kit rtl, found {len(srcs)}")
    p = srcs[0]
    before = hashlib.sha256(p.read_bytes()).hexdigest()
    try:
        p.write_text(transform(p.read_text()))
    except ValueError as e:
        raise SystemExit(str(e))
    delta = dict(transform="physical/die_plan/qwen_kvsys/cores/harden/zh_rf1.py", file=p.name,
                 sha256_before=before, sha256_after=hashlib.sha256(p.read_bytes()).hexdigest(),
                 command_cycles=0, nominal_token_cycles=0, added_ff=16 * (16 - 6), max_select_loads=16,
                 form="pre-decoded registered ZH read address (RF-KV1)")
    (kd / "zh_rf1_delta.json").write_text(json.dumps(delta, indent=1) + "\n")
    return delta
