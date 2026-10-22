#!/usr/bin/env python3
"""KV-GRP6 2026-10-20: s6 KV landing-group tiles qkd_kvs_grp_s6 / qkd_kvs_grp_h_s6 (default off).

Why (Codex s5 storage audit, results/rtl/qwen_kv_die/kvs_grp_s5_1020/io_storage/logical_storage.json, c1e5bec49): the
1024-b response payload passed FOUR unchanged flop captures, SRAM mem_q -> PC out_data (e0) -> branch hop (e1) ->
row-control idata (e2) -> rsp_data (e3).  The middle three are a flop->flop delay line >= 3 deep (SAFE item 5).

s6 (SAFE 5, +0 cycles): per PC branch the 256-b payload no longer rides the hop / idata flops.  It goes through a
genuine SRAM delay ring qkd_kvs_rsp_ring_s6: eight 4x32 1R1W macros (ot_sram_1r1w_4x32_m1_p192_grp_rsp), written
every core edge at slot wp (e1) and read every edge at slot rp = previous wp (e2); the row-control exit copies take
the macro read word at e3 exactly as they took idata.  Ages:
  e0 PC out_data FF (unchanged) | e1 SRAM write slot wp | e2 SRAM read slot rp (= the slot written at e1) | e3 exit FF
The pointers wp (+1 every edge) and rp (<= wp) are unreset and self-phasing: after ONE edge from ANY power-up value
rp == wp - 1, so read and write never address the same slot (no same-address collision) and every read returns the
word written one edge earlier.  The macro contents are never initialised and never need to be.
The old hop cleared its whole 295-b word while its landed reset rn was low; the ring keeps that exactly: the written
word is d & {z}, z = rn & rst_n (rn = the hop's own reset flop, rebuilt in the ring, one kept copy per macro), i.e.
zero iff the old hop output would have been zero after that edge.  Metadata (valid / t / v / epoch / layer / fault,
39 b per branch) keeps its hop flop (it is compared across the four PCs at the row control, not a passive delay).
The row-control output stage is two KEPT exit copies (as kv_grp_safe4 s4) on BOTH tiles: rsp and krsp face groups.

Derived MECHANICALLY from sha-pinned sources (refuses on drift); no shared file is modified:
  qkd_kvs_grp_s2.sv (KV-GRP3 s3 generation of kv_grp_safe2.py): qkd_kvs_grp_s2, qkd_kvs_grp_h_s2, landing_seg_s2
  kv_grp_safe4.rowctl() (qkd_static_kv_landing.sv rowctl with the s4 exit copies)
The s6 file holds only new modules; a kit reads it together with qkd_kvs_grp_s2.sv (leaves pc_s2 / lcal_s2 / rst).
Mutants (bench negative controls, each must FAIL; m1..m8 of kv_grp_safe2 still apply):
  9  krsp exit copy: data bit 0 inverted
  10 rsp exit copy: t bit 0 inverted
  11 ring read slot = wp (collides with the write slot: returns the word written 4 edges earlier)
  12 ring read one slot later (payload one edge late)
  13 ring reset-zero removed (z = 1: payload not cleared while the hop reset is low)
  14 ring branch 3 macro 7 write data bit 0 inverted

    python3 tools/qwen_kv_die/kv_grp_safe6.py            # writes rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_grp_s6.sv
    python3 tools/qwen_kv_die/kv_grp_safe6.py --check    # regenerate in memory, fail on any difference
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_grp_safe4 as S4  # noqa: E402

ROOT = S4.ROOT
S2F = S4.S2F
OUT = 'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_grp_s6.sv'
RMACRO = 'ot_sram_1r1w_4x32_m1_p192_grp_rsp'
RMACRO_DIR = 'physical/asap7_memory_macros/' + RMACRO
TOPS = ('qkd_kvs_grp_s6', 'qkd_kvs_grp_h_s6')
KEEP = ('qkd_kvs_rsp_exit_s6', 'qkd_kvs_rsp_ring_s6')
MUTANTS = {
    9: 'krsp exit copy: data bit 0 inverted',
    10: 'rsp exit copy: t bit 0 inverted',
    11: 'ring read slot = write slot wp (same-address collision)',
    12: 'ring read one slot later (payload one edge late)',
    13: 'ring reset-zero removed (z = 1)',
    14: 'ring branch 3 macro 7 write data bit 0 inverted',
}
one, module = S4.one, S4.module


def ring_body(mut):
    rd = {0: 'rp', 11: 'wp', 12: 'rp - 2\'d1'}
    z = "1'b1" if mut == 13 else 'rn & rst_n'
    flip = "^ ((MUT == 14 && b == 7) ? 32'd1 : 32'd0)" if mut == 'P' else ''
    return f"""    (* keep *) reg [1:0] wp;     // write slot, +1 every edge, unreset (any power-up value works)
    (* keep *) reg [1:0] rp;     // read slot = the slot written on the previous edge (rp == wp - 1 after one edge)
    always @(posedge ck) begin wp <= wp + 2'd1; rp <= wp; end
    for (genvar b = 0; b < 8; b = b + 1) begin : g_m
      (* keep *) reg rn;         // the old hop's landed reset flop, one kept copy per macro (32 gates each)
      always @(posedge ck or negedge hrn) if (!hrn) rn <= 1'b0; else rn <= 1'b1;
      wire z = {z};          // 0 iff the old hop word was cleared after this edge
      {RMACRO} u_m (.clk(ck), .r_ce_in(1'b1), .r_addr_in({rd.get(mut, 'rp')}), .rd_out(q[32*b+:32]),
        .w_ce_in(1'b1), .w_addr_in(wp), .wd_in((d[32*b+:32] & {{32{{z}}}}){flip}), .w_mask_in({{32{{1'b1}}}}));
    end
"""


RING = f"""// KV-GRP6: one PC branch's 256-b response payload delay as a genuine SRAM ring (8 x {RMACRO}).
// Write slot wp at edge e1, read slot rp (= previous wp) at e2: q after e2 == the word presented at e1 (d & z).  Ports:
// rst_n = the seg reset (D of the branch hrn flop), hrn = the branch landed reset (async clear of the hop rn).
(* keep_hierarchy *)
module {KEEP[1]} (input wire ck, input wire rst_n, input wire hrn, input wire [255:0] d, output wire [255:0] q);
{ring_body(0)}endmodule

// KV-GRP6 bench-only mutant ring (never instantiated at MUT 0).
module {KEEP[1]}_mut #(parameter integer MUT = 0) (input wire ck, input wire rst_n, input wire hrn, input wire [255:0] d,
    output wire [255:0] q);
    generate if (MUT == 11 || MUT == 12 || MUT == 13) begin : g_mm
      if (MUT == 11) begin : g11
{ring_body(11)}      end else if (MUT == 12) begin : g12
{ring_body(12)}      end else begin : g13
{ring_body(13)}      end
    end else begin : g_mp
{ring_body('P')}    end endgenerate
endmodule
"""

EXIT = S4.EXIT.replace(S4.KEEP, KEEP[0]).replace('KV-GRP5', 'KV-GRP6 (= kv_grp_safe4 s4 exit)')


def rowctl():
    r = S4.rowctl()
    r = r.replace('qkd_static_kv_rowctl_s4', 'qkd_static_kv_rowctl_s6').replace(S4.KEEP, KEEP[0])
    r = one(r, '      (* keep *) reg [1023:0] idata;\n      always @(posedge ck)idata<=pc_data;\n      assign xdata=idata;',
            '      // KV-GRP6 s6: pc_data is the branch SRAM rings\' read word (e2); the exit copies capture it at e3 as\n'
            '      // they captured idata (no idata flop: the payload delay is SRAM, not a flop chain).\n'
            '      assign xdata=pc_data;', 'rowctl idata')
    return r.replace('// KV-GRP5: qkd_static_kv_rowctl with', '// KV-GRP6: qkd_static_kv_rowctl (s4 exit copies, idata in SRAM) with')


def seg(s2):
    t = module(s2, 'qkd_static_kv_landing_seg_s2')
    t = one(t, 'module qkd_static_kv_landing_seg_s2 #(\n    parameter integer MUT=0,HOP_MUT=0\n)(',
            'module qkd_static_kv_landing_seg_s6 #(\n    parameter integer MUT=0,HOP_MUT=0,KMUT=0,RMUT=0\n)(', 'seg header')
    t = one(t, 'output wire [5:0] rsp_layer,output wire fault\n);',
            'output wire [5:0] rsp_layer,output wire fault,\n    output wire [1061:0] krsp_w\n);', 'seg ports')
    t = one(t, """      qkd_static_kv_hop295 #(.MUT(HOP_MUT==1 && branch==0))u_rsp(
        .ck(ck),.rst_n(hrn),
        .a({pf[branch],ol[6*branch+:6],oe[16*branch+:16],vv[branch],ot[14*branch+:14],od[256*branch+:256],ov[branch]}),
        .b({pf_d[branch],ol_d[6*branch+:6],oe_d[16*branch+:16],vv_d[branch],ot_d[14*branch+:14],od_d[256*branch+:256],ov_d[branch]}));""",
            """      // KV-GRP6 s6: the hop keeps the 39-b metadata word only; the 256-b payload takes the branch SRAM ring
      // (write e1 / read e2, same ages as hop e1 + idata e2), cleared exactly as the hop cleared it.
      qkd_static_kv_hop #(.W(39),.MUT(0))u_rsp(
        .ck(ck),.rst_n(hrn),
        .a({pf[branch],ol[6*branch+:6],oe[16*branch+:16],vv[branch],ot[14*branch+:14],ov[branch]}),
        .b({pf_d[branch],ol_d[6*branch+:6],oe_d[16*branch+:16],vv_d[branch],ot_d[14*branch+:14],ov_d[branch]}));
      if (RMUT == 0 || (RMUT == 14 && branch != 3)) begin : g_ring
        RING u_ring(.ck(ck),.rst_n(rst_n),.hrn(hrn),.d(od[256*branch+:256]),.q(od_d[256*branch+:256]));
      end else begin : g_ring_m
        RING_mut #(.MUT(RMUT)) u_ring(.ck(ck),.rst_n(rst_n),.hrn(hrn),.d(od[256*branch+:256]),.q(od_d[256*branch+:256]));
      end""".replace('RING', KEEP[1]), 'seg hop')
    t = one(t, '    qkd_static_kv_rowctl #(.VREQ(1)) u_rowctl(', '    qkd_static_kv_rowctl_s6 #(.VREQ(1),.MUT(KMUT)) u_rowctl(',
            'seg rowctl')
    t = one(t, '.rsp_layer(rsp_layer),.fault(fault));', '.rsp_layer(rsp_layer),.fault(fault),.krsp_w(krsp_w));', 'seg conn')
    return ('// KV-GRP6: qkd_static_kv_landing_seg_s2 with the payload in branch SRAM rings, rowctl_s6 exit copies.\n'
            '// Derived by tools/qwen_kv_die/kv_grp_safe6.py.\n' + t)


def tile(s2, base, top):
    t = module(s2, base)
    t = one(t, f'module {base} #(parameter integer MUT = 0) (', f'module {top} #(parameter integer MUT = 0) (', 'tile')
    t = one(t, '    qkd_static_kv_landing_seg_s2 #(.MUT((MUT == 6) ? 2 : 0), .HOP_MUT(0)) u_slg (',
            '    wire [1061:0] w_slg__krsp_w;\n'
            '    qkd_static_kv_landing_seg_s6 #(.MUT((MUT == 6) ? 2 : 0), .HOP_MUT(0), .KMUT((MUT == 9 || MUT == 10) ? MUT : 0),\n'
            '        .RMUT((MUT >= 11 && MUT <= 14) ? MUT : 0)) u_slg (', 'tile seg')
    t = one(t, '.rsp_layer(w_slg__rsp_layer), .fault(w_slg__fault));',
            '.rsp_layer(w_slg__rsp_layer), .fault(w_slg__fault), .krsp_w(w_slg__krsp_w));', 'tile seg conn')
    t = one(t, '    assign krsp = {w_slg__rsp_layer, w_slg__rsp_epoch, w_slg__rsp_v, w_slg__rsp_t, w_slg__rsp_data, w_slg__rsp_valid};',
            '    assign krsp = w_slg__krsp_w;   // KV-GRP6 s6: the krsp face leaves its own kept exit copy', 'tile krsp')
    return f'// KV-GRP6 s6 tile: {base} (s3 generation) with the response payload delay in SRAM rings.\n' + t


def build():
    s2 = S4.read(S2F)
    text = ('`timescale 1ns/1ps\n// KV-GRP6 2026-10-20 s6 KV landing-group tiles qkd_kvs_grp_s6 / qkd_kvs_grp_h_s6 (default off).  GENERATED\n'
            '// by tools/qwen_kv_die/kv_grp_safe6.py from sha-pinned sources; do not edit.  Read together with qkd_kvs_grp_s2.sv.\n\n'
            + tile(s2, 'qkd_kvs_grp_s2', TOPS[0]) + '\n' + tile(s2, 'qkd_kvs_grp_h_s2', TOPS[1]) + '\n' + seg(s2) + '\n'
            + rowctl() + '\n' + EXIT + '\n' + RING)
    return text, dict(tops=TOPS, keep=KEEP, ring_macro=RMACRO_DIR, sources=S4.SHA, mutants=MUTANTS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    text, rec = build()
    if a.check:
        if (ROOT / OUT).read_text() != text:
            raise SystemExit(f'kv_grp_safe6 --check: stale {OUT}')
        print('kv_grp_safe6 --check PASS')
        return
    (ROOT / OUT).write_text(text)
    print(json.dumps(rec, indent=1))


if __name__ == '__main__':
    main()
