#!/usr/bin/env python3
"""HBMb/SMH7-VMG 2026-10-21 (PD-AUDIT must-do 2, finding C2): REGIONAL-CLOCK successors of the VM hub-glue core modules.

The g7s tiles (hfd_hgi_vms_glue_{nw,sw}_t) run ONE clock spine over 648 x 1555.2 um (81k / 107k sinks, TT insertion
977-988 ps).  g8r gives the tile three GEOMETRIC clock regions, horizontal bands aligned to the ring-face lane bands:
  s    y <  580.1 um  (three lane bands: NW 5 4 3, SW 6 7 0; the S-face banks; the far-face bank at that end)
  core 580.1 .. 976 (two lane bands + the ring header / tx controls / clk / rst_n, the hub island, replay, status)
  n    y >= 976 um    (three lane bands: NW 0 7 6, SW 3 4 5; the N-face banks; the far-face bank at that end)
Every register is clocked by the root of the band it is PLACED in.  The band of each register group is the measured
majority band of that group in the g7s gate placement (3_place.odb, tools/hbm_die_v16/vms_glue_seam_census.tcl ->
results/rtl/vm_glue_1018/g8r/region_map_<q>.json): the lane-aligned seams put 97-100 % of every lane-band / bank / hub
group on one side, so each root's sinks form one compact band (no register moves; the floorplan and relay lattice of g7
are unchanged).  Region code: 0 = s, 1 = core, 2 = n; clock vector ckr = {clk_n, clk, clk_s}.

This script writes rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_glue_lr.sv from hfd_hgi_vms_glue_lt.sv by asserted textual
edits (each edit must match exactly once), so the _lr modules are the _lt modules with ONLY the clock of chosen
registers changed:
  ot_vms_rstop_lr   band b registers (+ the lane / egress slices of stage A) on ckr[RB[b]]; rce pair p on ckr[RP[p]];
                    rce half h on ckr[RHL[h]]; injection half relay pi_m h on ckr[RPI[h]]; replay relay ri_m on band 0's
                    root; everything else (header band, control, commit ring, rce output, cco) on the core root.
  ot_vms_hub_lr     bank request stage b (sel_h, slice selects, pp / pv) on ckr[RQ[b]]; face-group request copies g
                    (qr_g1 / qr_g / sq_g1 / sq_g) on ckr[RQG[g]]; everything else on the core root.
  ot_vms_rst_forest_lr  every reset leaf q on the root of the registers it clears (RLR); the per-group landing /
                    synchroniser (l1 / s0 / s1) on the core root (rst_l0 lands at the E-face centre).
  hfd_vms_glue_core_lr  the _lt core wiring with ckr; hub <-> stop relays, replay and status on the core root.
Function, reset behaviour and every edge are IDENTICAL to _lt (same registers, same D logic): with clk_s = clk = clk_n the
_lr core is cycle-exact with the _lt core (tile lockstep bench drives all three from one clock).  Region crossings are plain
registered hops between neighbour-matched band roots (static schedule, 0 added edges; see lanes/HBMb-SMH7.md SAFE review).
    gen_vms_glue_lr.py [--check]
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / 'rtl/hbm_accel/generic/vm/static'
SRC, OUT = D / 'hfd_hgi_vms_glue_lt.sv', D / 'hfd_hgi_vms_glue_lr.sv'


def cut(text, start, end):
    i = text.index(start)
    j = text.index(end, i) + len(end)
    return text[i:j]


def sub(text, old, new, count=1):
    n = text.count(old)
    if n != count:
        raise SystemExit(f'gen_vms_glue_lr: expected {count} x {old!r}, found {n}')
    return text.replace(old, new)


def rstop(t):
    t = sub(t, 'module ot_vms_rstop_lt #(', 'module ot_vms_rstop_lr #(')
    t = sub(t, '    parameter integer NLS=36             // g6 reset leaves', '    parameter integer NLS=36,            // g6 reset leaves')
    t = sub(t, '                                         // 3+4b+r band b slices 3r..3r+2 (+ eg_v on r 0), 35 outstanding\n) (',
            '                                         // 3+4b+r band b slices 3r..3r+2 (+ eg_v on r 0), 35 outstanding\n'
            '    parameter [15:0] RB=16\'h5555,          // g8r: clock region of lane band b (2 b each: 0 s / 1 core / 2 n)\n'
            '    parameter [7:0] RP=8\'h55,              // g8r: region of rce pair register p\n'
            '    parameter [3:0] RHL=4\'h5,              // g8r: region of rce half register h\n'
            '    parameter [3:0] RPI=4\'h5               // g8r: region of the injection half relay pi_m h\n) (')
    t = sub(t, '    input wire clk,\n    input wire [NLS-1:0] rl,',
            '    input wire [2:0] ckr,                // g8r: band roots {n, core, s}\n    input wire [NLS-1:0] rl,')
    t = sub(t, '    output reg fault\n);\n', '    output reg fault\n);\n    wire clk=ckr[1];                     // g8r: the core (header band) root\n')
    # stage A: header bits stay on the core root; lane / egress slices land in their band (band loop below)
    t = sub(t, '        a_l<=l_in; a_pi<=pi; a_eg<=eg; a_ri<=ri;', '        a_l[2223:2208]<=l_in[2223:2208]; a_pi<=pi; a_ri<=ri;')
    t = sub(t, '        always @(posedge clk) pi_m<=a_pi[277:0];', '        always @(posedge ckr[RPI[2*h+:2]]) pi_m<=a_pi[277:0];')
    t = sub(t, '            always @(posedge clk) begin ri_m<=a_ri[255:0]; h7_m<=a_l[2214:2208]; end',
            '            always @(posedge ckr[RB[1:0]]) ri_m<=a_ri[255:0];   // g8r: beside band 0\n'
            '            always @(posedge clk) h7_m<=a_l[2214:2208];')
    t = sub(t, '        localparam integer H=UPPER[b] ? 1 : 0;\n',
            '        localparam integer H=UPPER[b] ? 1 : 0;\n'
            '        wire ckb=ckr[RB[2*b+:2]];          // g8r: this band\'s regional root\n'
            '        always @(posedge ckb) begin a_l[b*276+:276]<=l_in[b*276+:276]; a_eg[b*276+:276]<=eg[b*276+:276]; end\n')
    for old in ('        always @(posedge clk) begin oh_m<=oh_a; own_m<=own_a; kind_m<=a_l[2222:2221]; end',
                '        always @(posedge clk) begin ln_m<=a_l[b*276+:276]; eg_m<=a_eg[b*276+:276]; lv_r<=a_l[b*276+275]; ev_r<=a_eg[b*276+275]; end',
                '        always @(posedge clk) begin ln<=ln_m; eg_d<=eg_m[274:0]; pi_b<=hm_pi[H]; end',
                '        always @(posedge clk or negedge rl[3+4*b]) if(!rl[3+4*b]) eg_v<=0; else eg_v<=eg_m[275];',
                '            always @(posedge clk or negedge rl[RL])',
                '            always @(posedge clk) lv_q<=ln_m[275];',
                '            always @(posedge clk) begin ri_b<=hm_ri[H]; h7_b<=hm_h7[H]; end'):
        t = sub(t, old, old.replace('posedge clk', 'posedge ckb'))
    t = sub(t, '        always @(posedge clk) begin\n            lo<=fl;', '        always @(posedge ckb) begin\n            lo<=fl;')
    old_tree = cut(t, '    reg [274:0] pl [0:3]; reg [1:0] pv [0:3]; reg [9:0] ph, ph2;', '        ph2<=ph;\n    end\n')
    t = sub(t, old_tree,
            '    // g8r: pair registers on their regional roots (RP), packed per pair\n'
            '    wire [4*275-1:0] plw; wire [7:0] pvw; reg [9:0] ph, ph2;\n'
            '    for(genvar p=0;p<4;p=p+1) begin : pair\n'
            '        reg [274:0] pl; reg [1:0] pv;\n'
            '        always @(posedge ckr[RP[2*p+:2]]) begin\n'
            '            pl<=lane_q[2*p][274:0] | lane_q[2*p+1][274:0];   // both bands of a pair sit in one half: same decode\n'
            '            pv<=own_kind0[2*p] ? {lv[2*p+1],lv[2*p]} : 2\'d0;\n'
            '        end\n'
            '        assign plw[p*275+:275]=pl; assign pvw[2*p+:2]=pv;\n'
            '    end\n'
            '    always @(posedge clk) begin\n'
            '        ph<=(own && kind==2\'d0) ? {1\'b1,h_d[8:0]} : 10\'d0;\n'
            '        ph2<=ph;\n'
            '    end\n')
    t = sub(t, '                hl_n[h]=hl_n[h]|pl[p];\n                if(pv[p]!=0) hb_n[h]={1\'b1,2\'(p),pv[p][1]};',
            '                hl_n[h]=hl_n[h]|plw[p*275+:275];\n                if(pvw[2*p+:2]!=0) hb_n[h]={1\'b1,2\'(p),pvw[2*p+1]};')
    t = sub(t, '    reg [274:0] hl [0:1]; reg [3:0] hb [0:1];\n'
               '    always @(posedge clk) begin hl[0]<=hl_n[0]; hl[1]<=hl_n[1]; hb[0]<=hb_n[0]; hb[1]<=hb_n[1]; end\n'
               '    wire pick1=hb[1][3] && (!hb[0][3] || hb[1][2:1]>hb[0][2:1]);\n'
               '    wire [2:0] bnk=pick1 ? hb[1][2:0] : (hb[0][3] ? hb[0][2:0] : 3\'d0);\n'
               '    wire [274:0] lor=hl[0]|hl[1];\n',
            '    // g8r: half registers on their regional roots (RHL), packed per half\n'
            '    wire [2*275-1:0] hlw; wire [7:0] hbw;\n'
            '    for(genvar h=0;h<2;h=h+1) begin : hreg\n'
            '        reg [274:0] hl; reg [3:0] hb;\n'
            '        always @(posedge ckr[RHL[2*h+:2]]) begin hl<=hl_n[h]; hb<=hb_n[h]; end\n'
            '        assign hlw[h*275+:275]=hl; assign hbw[4*h+:4]=hb;\n'
            '    end\n'
            '    wire pick1=hbw[7] && (!hbw[3] || hbw[6:5]>hbw[2:1]);\n'
            '    wire [2:0] bnk=pick1 ? hbw[6:4] : (hbw[3] ? hbw[2:0] : 3\'d0);\n'
            '    wire [274:0] lor=hlw[274:0]|hlw[549:275];\n')
    return t


def hub(t):
    t = sub(t, 'module ot_vms_hub_lt #(', 'module ot_vms_hub_lr #(')
    t = sub(t, '    parameter integer NLH=3+14*(NC+1)   // reset leaves (layout: see L_* below)\n)(',
            '    parameter integer NLH=3+14*(NC+1),  // reset leaves (layout: see L_* below)\n'
            '    parameter [15:0] RQ=16\'h5555,       // g8r: clock region of bank request stage b (0 s / 1 core / 2 n)\n'
            '    parameter [5:0] RQG=6\'h15           // g8r: region of the face-group request copies g\n)(')
    t = sub(t, '    input wire clk,\n    input wire [NLH-1:0] rl,', '    input wire [2:0] ckr,               // g8r: band roots {n, core, s}\n    input wire [NLH-1:0] rl,')
    t = sub(t, '    output reg [2:0] status\n);\n', '    output reg [2:0] status\n);\n    wire clk=ckr[1];                    // g8r: the hub island is on the core root\n')
    t = sub(t, '        always @(posedge clk) begin qr_g1<=qr; sq_g1<=sq; qr_g<=qr_g1; sq_g<=sq_g1; end',
            '        always @(posedge ckr[RQG[2*g+:2]]) begin qr_g1<=qr; sq_g1<=sq; qr_g<=qr_g1; sq_g<=sq_g1; end')
    t = sub(t, '        for(genvar b=GL;b<=GH;b=b+1) begin : bank\n',
            '        for(genvar b=GL;b<=GH;b=b+1) begin : bank\n            wire ckq=ckr[RQ[2*b+:2]];      // g8r: this bank\'s request stage root\n')
    for old in ('            always @(posedge clk) sel_h<=sel_n;',
                '                always @(posedge clk) sel<=(MUT==6) ? sel_n : sel_h;   // MUT 6 (bench only): g5 select stage missing',
                '            always @(posedge clk) pp<=nq[283:0];',
                '            always @(posedge clk or negedge rl[L_PV]) if(!rl[L_PV]) pv<=1\'b0; else pv<=nq[284];'):
        t = sub(t, old, old.replace('posedge clk', 'posedge ckq'))
    return t


FOREST = '''// g8r reset forest: as ot_vms_rst_forest (same leaves, same 2 / 5-edge timing); every leaf q is clocked by the regional
// root of the registers it clears (RLR, 2 b per leaf: 0 s / 1 core / 2 n), the per-group landing / synchroniser stays on
// the core root beside rst_l0
module ot_vms_rst_forest_lr #(parameter integer NL=24, parameter integer GL=24, parameter [255:0] RLR={128{2'b01}}) (
    input wire [2:0] ckr,
    input wire rst_l0,
    output wire [NL-1:0] rl
);
    wire clk=ckr[1];
    localparam integer NG=(NL+GL-1)/GL;
    for(genvar g=0;g<NG;g=g+1) begin : grp
        (* keep = "true", dont_touch = "true" *) reg l1;
        (* keep = "true", dont_touch = "true" *) reg s0, s1;
        always @(posedge clk) l1<=rst_l0;
        always @(posedge clk or negedge l1) if(!l1) begin s0<=1'b0; s1<=1'b0; end else begin s0<=1'b1; s1<=s0; end
        for(genvar i=g*GL;i<(g+1)*GL && i<NL;i=i+1) begin : lf
            (* keep = "true", dont_touch = "true" *) reg q;
            always @(posedge ckr[RLR[2*i+:2]] or negedge l1) if(!l1) q<=1'b0; else q<=s1;
            assign rl[i]=q;
        end
    end
endmodule
'''


def core(t):
    t = sub(t, 'module hfd_vms_glue_core_lt #(', 'module hfd_vms_glue_core_lr #(')
    t = sub(t, '    parameter [7:0] UPPER=8\'b00111100     // g4: lane bands in the upper half of the ring face\n)(',
            '    parameter [7:0] UPPER=8\'b00111100,    // g4: lane bands in the upper half of the ring face\n'
            '    parameter [15:0] RB=16\'h5555,         // g8r regions (0 s / 1 core / 2 n): ring-stop lane bands,\n'
            '    parameter [7:0] RP=8\'h55,             //   rce pairs,\n'
            '    parameter [3:0] RHL=4\'h5,             //   rce halves,\n'
            '    parameter [3:0] RPI=4\'h5,             //   injection half relays,\n'
            '    parameter [15:0] RQ=16\'h5555,         //   hub bank request stages,\n'
            '    parameter [5:0] RQG=6\'h15,            //   hub face-group request copies,\n'
            '    parameter [255:0] RLR={128{2\'b01}}    //   reset leaves\n)(')
    t = sub(t, '    input wire clk,\n    input wire rst_l0,', '    input wire [2:0] ckr,                 // g8r: band roots {n, core, s}\n    input wire rst_l0,')
    t = sub(t, '    output wire [2:0] ring_fault\n);\n', '    output wire [2:0] ring_fault\n);\n    wire clk=ckr[1];                      // g8r: relays, replay and status on the core root\n')
    t = sub(t, '    ot_vms_rst_forest #(.NL(NL)) u_rst(.clk(clk),.rst_l0(rst_l0),.rl(rl));',
            '    ot_vms_rst_forest_lr #(.NL(NL),.RLR(RLR)) u_rst(.ckr(ckr),.rst_l0(rst_l0),.rl(rl));')
    t = sub(t, '    ot_vms_hub_lt #(.NC(NC),.CW(CW),.MUT(RMUT),.NLH(NLH)) u_hub(\n        .clk(clk),',
            '    ot_vms_hub_lr #(.NC(NC),.CW(CW),.MUT(RMUT),.NLH(NLH),.RQ(RQ),.RQG(RQG)) u_hub(\n        .ckr(ckr),')
    t = sub(t, '    ot_vms_rstop_lt #(.COMMIT_DELAY(COMMIT_DELAY),.MUT(RMUT),.UPPER(UPPER),.NLS(NLS)) u_cw(\n        .clk(clk),',
            '    ot_vms_rstop_lr #(.COMMIT_DELAY(COMMIT_DELAY),.MUT(RMUT),.UPPER(UPPER),.NLS(NLS),.RB(RB),.RP(RP),.RHL(RHL),.RPI(RPI)) u_cw(\n        .ckr(ckr),')
    t = sub(t, '    ot_vms_rstop_lt #(.COMMIT_DELAY(COMMIT_DELAY),.MUT(RMUT),.UPPER(UPPER),.NLS(NLS)) u_ccw(\n        .clk(clk),',
            '    ot_vms_rstop_lr #(.COMMIT_DELAY(COMMIT_DELAY),.MUT(RMUT),.UPPER(UPPER),.NLS(NLS),.RB(RB),.RP(RP),.RHL(RHL),.RPI(RPI)) u_ccw(\n        .ckr(ckr),')
    return t


def main():
    lt = SRC.read_text()
    parts = [rstop(cut(lt, 'module ot_vms_rstop_lt #(', 'endmodule\n')),
             hub(cut(lt, 'module ot_vms_hub_lt #(', 'endmodule\n')),
             FOREST,
             core(cut(lt, 'module hfd_vms_glue_core_lt #(', 'endmodule\n'))]
    doc = '\n'.join('// ' + x if x else '//' for x in __doc__.strip().split('\n')[:-1])
    out = ('`timescale 1ns/1ps\n`default_nettype none\n// GENERATED by tools/hbm_die_v16/gen_vms_glue_lr.py from hfd_hgi_vms_glue_lt.sv '
           '(do not edit).\n' + doc + '\n// ot_vms_rcl_lt and ot_vms_status_static are used unchanged (core root).\n\n'
           + '\n'.join(parts) + '`default_nettype wire\n')
    if '--check' in sys.argv:
        ok = OUT.exists() and OUT.read_text() == out
        print('VMS_GLUE_LR', 'CHECK_PASS' if ok else 'CHECK_FAIL'); sys.exit(0 if ok else 1)
    OUT.write_text(out); print('WROTE', OUT.relative_to(ROOT), len(out.splitlines()), 'lines')


if __name__ == '__main__':
    main()
