import re, sys
from pathlib import Path
src, out = Path(sys.argv[1]), Path(sys.argv[2])
NPAD = 8; DSREP = 8
SLOTS = ["ft0", "ft1", "ft7", "ft8", "ft9", "ft10", "ft11", "ft12"]
b = (src / "s81p_slice_station__t41_bound.sv").read_text()
n_sub = 0
for s in SLOTS:
    pat = re.compile(r"^(\s*)ot_dp_st #\(\.W\((\d+)\)\) u_ft_%s_o_0 \((.*?)\.d\(%s_i\[(\d+):0\]\), \.ea\(%s_i\[(\d+)\]\)" % (s, s, s), re.M)
    m = pat.search(b); assert m, s
    ind, W, hi, ea = m.group(1), int(m.group(2)), int(m.group(4)), int(m.group(5))
    assert hi == W - 1 and ea == W, (s, W, hi, ea)
    pad = (f"{ind}// T41FORM hold pad (DIE-S81-85 t41form 11-10): vclk ft slot input -> {NPAD} kept BUFx2 per bit -> station 0 (0 cycles)\n"
           f"{ind}wire [{W}:0] {s}_i_hp;\n"
           f"{ind}ot_t41_hpad #(.W({W + 1}), .N({NPAD})) u_hp_{s} (.a({s}_i), .y({s}_i_hp));\n")
    new = f"{m.group(1)}ot_dp_st #(.W({W})) u_ft_{s}_o_0 ({m.group(3)}.d({s}_i_hp[{hi}:0]), .ea({s}_i_hp[{ea}])"
    b = b[:m.start()] + pad + new.lstrip("\n") + b[m.end():]
    n_sub += 1
# other uses of the slot inputs must not exist (station 0 is the only load)
for s in SLOTS:
    uses = [l for l in b.splitlines() if re.search(r"\b%s_i\b" % s, l) and "input" not in l and "u_hp_" not in l]
    assert not uses, (s, uses)
n_land = len(re.findall(r"ot_dp_clk_landing #\(", b))
b = b.replace("ot_dp_clk_landing #(", f"ot_dp_clk_landing #(.DSREP({DSREP}), ")
b += f"""
// T41FORM (DIE-S81-85 t41form 11-10): structural hold pad for the vclk (non-forwarded) ft slot inputs.  Each bit goes
// through N kept platform buffers (BUFx2, not DONT_USE) before its station-0 face flop: logic identity, 0 cycles.
// Sized from attempt_4 FF sign-off (worst -66.78 ps, 4104 port starts): N=8 adds >= ~104 ps FF (BUFx2 FF ~13 ps) and
// costs ~145 ps TT on a port path with ~+360 ps TT setup slack.  dont_touch is set on the instances at PRE_FLOORPLAN.
module ot_t41_hpad #(parameter integer W = 1, parameter integer N = 1) (input wire [W-1:0] a, output wire [W-1:0] y);
    genvar i, k;
    generate for (i = 0; i < W; i = i + 1) begin : g_b
        wire [N:0] c;
        assign c[0] = a[i];
        for (k = 0; k < N; k = k + 1) begin : g_s
            (* keep, dont_touch *) BUFx2_ASAP7_75t_R u_b (.A(c[k]), .Y(c[k + 1]));
        end
        assign y[i] = c[N];
    end endgenerate
endmodule
"""
(out / "s81p_slice_station__t41_bound.sv").write_text(b)
# landing / ring: DSREP plumbing (default 1 = byte-identical behaviour), dsel SREP already exists (DSREP-1)
l = (src / "ot_dp_clk_landing.sv").read_text()
old = "    parameter bit     FREG = 0     // optional rising-fclk input capture: +1 data cycle\n"
assert old in l
l = l.replace(old, "    parameter bit     FREG = 0,    // optional rising-fclk input capture: +1 data cycle\n"
                   "    parameter integer DSREP = 1    // T41FORM: kept copies of each 64-bit chunk's one-hot read select (ot_meso_dsel SREP)\n")
old = ".GUARD_HI(4), .RDREG(1), .TNEG(WNEG)) u_ring ("
assert l.count(old) == 1
l = l.replace(old, ".GUARD_HI(4), .RDREG(1), .TNEG(WNEG), .DSREP(DSREP)) u_ring (")
(out / "ot_dp_clk_landing.sv").write_text(l)
f = (src / "ot_meso_fifo.sv").read_text()
old = "    parameter bit TNEG     = 0       // S81-RINGHOLD-3 variant (a)"
assert f.count(old) == 1
f = f.replace(old, "    parameter int DSREP    = 1,      // T41FORM: ot_meso_dsel SREP (kept select copies per chunk); 1 = unchanged\n"
                   "    parameter bit TNEG     = 0       // S81-RINGHOLD-3 variant (a)")
old = "ot_meso_dsel #(.W(WCH), .DEPTH(DEPTH), .REG(RDREG), .SPLIT(RSPLIT)) u_dsel"
assert f.count(old) == 1
f = f.replace(old, "ot_meso_dsel #(.W(WCH), .DEPTH(DEPTH), .REG(RDREG), .SPLIT(RSPLIT), .SREP(DSREP)) u_dsel")
(out / "ot_meso_fifo.sv").write_text(f)
print(f"pads on {n_sub} slots, DSREP={DSREP} on {n_land} landings")
