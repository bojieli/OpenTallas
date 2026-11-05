#!/usr/bin/env python3
"""HBM-REFORM-A3 d44v part 19 inputs: tkm tile idpin + terminal_idpin -> 2 x ot_hgi_coll_tkm_tp192_htile_core (one master).
    gen_p19.py REPO KIT_IDPIN_RTL KIT_TERM_RTL OUT     writes composition into REPO, glue + conn + split_p19.json into OUT
The chain runs in Y on the die: S face = ins, up_out, clr; N face = ovf, up_in, conv. So hA south, hB north, each 319.68 x 172.8: the seam is
hA.N to hB.S, in chain order, and one table serves all 64 elements. Terminal: same composition; the kit wrapper ties up_in to 0 and leaves ovf open."""
import json, subprocess, sys
from pathlib import Path
repo, ki, kt, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]); out.mkdir(parents=True, exist_ok=True)
A = repo / "rtl/hbm_accel/cores_split/reform_1103/tkm_tile"; R = repo / "results/die_hbm_1103/reform/split_p6"
B = repo / "rtl/hbm_accel/cores_split/reform_1104a/tkm_tile"; B.mkdir(parents=True, exist_ok=True)
H, BASE, COMP = "ot_hgi_coll_tkm_tp192_htile_core", "ot_hgi_coll_tkm_tp192_tile_core", "ot_hgi_coll_tkm_tp192_tile_core__splitc"
sv = B / f"{COMP}.sv"
sv.write_text(f"""`default_nettype none
// HBM-REFORM-A3 11-05 d44v part 19: plan composition of the TKM tile, same ports as {BASE}. Sub-blocks are the hard cores, each with its kit face shell.
// Same wiring as ot_hgi_coll_tkm_tp192_tile_core__idpin__strap__split (reform_1103, reduced-chain EQ receipt).
module {COMP} (
    input wire tile_clk, input wire tile_clr, output wire tile_clr_o, input wire tile_conv, output wire tile_conv_o,
    input wire [343:0] tile_ins_b, input wire tile_ins_v, input wire [343:0] tile_up_in,
    output wire [343:0] tile_ovf_b, output wire tile_ovf_v, output wire [343:0] tile_up_out);
    wire clr_ab, conv_ba, v_ab; wire [343:0] b_ab, up_ba;
    {H} u_ha (.tile_clk(tile_clk), .tile_clr(tile_clr), .tile_clr_o(clr_ab), .tile_conv(conv_ba), .tile_conv_o(tile_conv_o),
        .tile_ins_v(tile_ins_v), .tile_ins_b(tile_ins_b), .tile_ovf_v(v_ab), .tile_ovf_b(b_ab), .tile_up_in(up_ba), .tile_up_out(tile_up_out));
    {H} u_hb (.tile_clk(tile_clk), .tile_clr(clr_ab), .tile_clr_o(tile_clr_o), .tile_conv(tile_conv), .tile_conv_o(conv_ba),
        .tile_ins_v(v_ab), .tile_ins_b(b_ab), .tile_ovf_v(tile_ovf_v), .tile_ovf_b(tile_ovf_b), .tile_up_in(tile_up_in), .tile_up_out(up_ba));
endmodule
`default_nettype wire
""")
PRE = "u_fcore.u_core."; W, HH = 319.68, 172.8
ROWS = dict(id=("ot_hgi_coll_tkm_tp192_tile_core__idpin__strap", ki), term=("ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__strap", kt))
spec = []
for k, (core, kit) in ROWS.items():
    g = out / f"{core}__p19glue.sv"
    subprocess.run([sys.executable, "-I", str(R / "split_glue.py"), str(kit / f"{core}__wrap.sv"), BASE, COMP, str(sv), str(g)], check=True)
    nj = out / f"{k}.netlist.json"
    subprocess.run(["bash", str(R / "netlist2.sh"), str(nj), core, str(g), str(sv), str(A / f"{H}.sv")], check=True)
    subprocess.run([sys.executable, "-I", str(R / "split_conn.py"), str(nj), core, str(out / f"{k}.conn.json")], check=True)
    nj.unlink()
    spec.append(dict(core=core, sha="p19", part="p19", glue=g.name, conn=f"{k}.conn.json", subs=[dict(module=H, cells=137216)],
                     added_cycles="down +5, clr_o +3, conv_o +2, up_out +2 on conv; TKM op +448 edges (latency/ tsv of reform_1103)",
                     layout={PRE + "u_ha": dict(xy=[0.0, 0.0], wh=[W, HH]), PRE + "u_hb": dict(xy=[0.0, HH], wh=[W, HH])},
                     clock_entry={H: [159.84 - 0.0, 86.4]}))
(out / "split_p19.json").write_text(json.dumps(spec, indent=1) + "\n")
print("wrote", out)
