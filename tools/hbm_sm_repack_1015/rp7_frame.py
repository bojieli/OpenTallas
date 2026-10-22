#!/usr/bin/env python3
"""Emit the explicitly priced two-half composition and full-width r6 miter."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'rtl/hbm_accel/sm/repack/h2a7'
old=(ROOT/'rtl/hbm_accel/sm/repack/h2a6/ot_hbm_smh_rp6_frame.sv').read_text()
header=old[old.index('module ot_hbm_smh_rp6_2'):old.index('    wire [2068:0] x_b;')].replace('ot_hbm_smh_rp6_2','ot_hbm_smh_rp7_2')
a=['`timescale 1ns/1ps','// Priced frame: north xo_b +3 is padded by six to align xo_g* +9.', '// South external inputs and reset shift nine edges; all output ages are explicit.',header,
'wire [2068:0] x_b, x_bp; wire [49:0] x_g0; wire [99:0] x_gp;',
'ot_rp7_delay_ring #(.W(2069),.N(6)) u_xb_age (.clk(clk),.rst_n(rst_n),.d(x_b),.q(x_bp));',
'reg [8:0] sr; always @(posedge clk) sr<={sr[7:0],rst_n}; wire rst_s=sr[8];']
for n,w in [('xss_a1',9),('xss_g1',5),('xss_a2',7),('xss_g2',5),('rin_s',818),('attn',5)]:
 a += [f'wire [{w-1}:0] south_{n};',f'ot_rp7_delay_ring #(.W({w}),.N(9)) u_age_{n} (.clk(clk),.rst_n(rst_n),.d({n}),.q(south_{n}));']
for v,tag in [('m','main'),('f','fb')]:
 a += [f'generate if(VAR=={0 if v=="m" else 1}) begin:g_{tag}']
 for h in 'ns':
  s=json.loads((ROOT/f'results/arch/hbm_smh_r7_1021/lp_spec_{h}_{v}.json').read_text())
  cs=[f'.ck_{r["name"]}(clk)' for r in s['regions']]+[f'.rst_n({"rst_n" if h=="n" else "rst_s"})']
  if h=='n':cs += [f'.{n}({n})' for n in ['xs_a1','xs_g1','xs_a2','xs_g2','attn','rin_n','bin','gin','rout_n','bout']]+['.xo_b(x_b)','.xo_g0(x_g0)','.xo_gp(x_gp)']
  else:cs += [f'.{n}(south_{n})' for n in ['xss_a1','xss_g1','xss_a2','xss_g2','rin_s','attn']]+['.rout_s(rout_s)','.gout(gout)','.xi_b(x_bp)','.xi_g0(x_g0)','.xi_gp(x_gp)']
  a += [f'{s["top_lp"]} #(.HMUT(HMUT),.MUT(MUT)) u_{h} ('+', '.join(cs)+');']
 a += ['end endgenerate']
a += ['endmodule']
(OUT/'ot_hbm_smh_rp7_frame.sv').write_text('\n'.join(a)+'\n')
# Keep the predecessor production stimulus, including the zero reset interval.
b=(ROOT/'rtl/hbm_accel/sm/repack/h2a6/tb_ot_hbm_smh_rp6_2.sv').read_text()
b=b.replace('module tb_ot_hbm_smh_rp6_2;','module tb_ot_hbm_smh_rp7_frame;')
b=re.sub(r'    localparam integer DG = .*?\n','    localparam integer DN=VAR==0 ? 6:9, DS=VAR==0 ? 15:18, DB=6, DG=VAR==0 ? 21:36;\n',b)
b=b.replace('reg [3:0] rst_dl;','reg [0:0] rst_dl;').replace('wire rst_f = rst_dl[3];','wire rst_f = rst_dl[0];').replace('rst_dl <= {rst_dl[2:0], rst};','rst_dl <= rst;')
b=b.replace('ot_hbm_smh_rp4a_flat u_flat','ot_hbm_smh_rp6_2 #(.VAR(VAR)) u_flat').replace('ot_hbm_smh_rp6_2 #(.VAR(VAR), .HMUT(HMUT), .MUT(0)) u_lp','ot_hbm_smh_rp7_2 #(.VAR(VAR), .HMUT(HMUT), .MUT(MUT)) u_lp')
for n,d in [('rout_n','DN'),('rout_s','DS'),('bout','DB')]:
 b=b.replace(f'dlo_{n} [0:0]',f'dlo_{n} [0:{d}-1]').replace(f'j <= 0; j = j + 1) dlo_{n}',f'j < {d}; j = j + 1) dlo_{n}').replace(f'dlo_{n}[0]) begin bad',f'dlo_{n}[{d}-1]) begin bad').replace(f'cyc, dlo_{n}[0],',f'cyc, dlo_{n}[{d}-1],')
b=b.replace('dlo_gout[2 + GN + GS + LR + 2 * OS + DG]','dlo_gout[DG-1]')
b=b.replace('lo_bout !== fo_bout','lo_bout !== dlo_bout[DB-1]').replace('cyc, fo_bout, lo_bout','cyc, dlo_bout[DB-1], lo_bout')
start=b.index('    // activity census');end=b.index('    function [31:0] rnd;',start)
activity=['    integer c_bov=0,c_fov=0,c_ev=0,c_pub=0,c_pvin=0;']
for v,t in [(0,'main'),(1,'fb')]:
 activity += [f'generate if(VAR=={v}) begin:activity_{t}', 'always @(posedge clk) begin']
 for c,wire in [('c_bov','bov'),('c_fov','fov'),('c_ev','ev'),('c_pub','pv')]:activity += [f'{c}<={c}+u_flat.g_{t}.u_n.{wire}0+u_flat.g_{t}.u_s.{wire}1;']
 activity += ['end end endgenerate']
b=b[:start]+'\n'.join(activity)+'\n'+b[end:]
b=b.replace('R6_','R7_FRAME_').replace('warm=800 DG=%0d ATTN=%0d','warm=800 added_gout_edges=%0d ATTN=%0d')
b=b.replace('    integer cyc, nc, bad;', '    integer cyc, nc, bad; integer first_old[0:3],first_new[0:3];')
b=b.replace('        nc = 0; bad = 0;', '        nc = 0; bad = 0; for(integer k=0;k<4;k=k+1) begin first_old[k]=-1;first_new[k]=-1;end')
b=b.replace('            if (cyc > 800) begin', '''            for(integer k=0;k<4;k=k+1) begin
                if(first_old[k]<0 && fo_gout[k*50+49]) first_old[k]=cyc;
                if(first_new[k]<0 && lo_gout[k*50+49]) first_new[k]=cyc;
                if(cyc>16 && (lo_gout[k*50+49] || dlo_gout[DG-1][k*50+49]) && lo_gout[k*50+:50] !== dlo_gout[DG-1][k*50+:50]) begin
                    bad=bad+1; if(bad<6) $display("R7_FIRST_TOKEN_MISMATCH lane=%0d cycle=%0d old=%h new=%h",k,cyc,dlo_gout[DG-1][k*50+:50],lo_gout[k*50+:50]);
                end
            end
            if (cyc > 800) begin''')
b=b.replace('        $display("R7_FRAME_ACTIVITY', '''        for(integer k=0;k<4;k=k+1) begin
            $display("R7_FIRST_TOKEN lane=%0d old_cycle=%0d new_cycle=%0d required_added_edges=%0d",k,first_old[k],first_new[k],DG);
            if(first_old[k]<0 || first_new[k]!=first_old[k]+DG) bad=bad+1;
        end
        $display("R7_FRAME_ACTIVITY''')
b=b.replace('if (bad == 0 && nc > 0)', 'if (bad == 0 && nc > 0 && c_bov>0 && c_fov>0 && c_ev>0 && c_pub>0)')
(OUT/'tb_ot_hbm_smh_rp7_frame.sv').write_text(b)
sh=(ROOT/'rtl/hbm_accel/sm/repack/h2a6/run_rp6_2_one.sh').read_text()
src=re.search(r'^SRCS="(.*)"$',sh,re.M).group(1)
src=src.replace('rtl/hbm_accel/sm/repack/h2a6/tb_ot_hbm_smh_rp6_2.sv','')
src+=' '+' '.join(f'rtl/hbm_accel/sm/repack/h2a7/lp_{h}_{v}/ot_hbm_smh_rp7{h}_{v}.sv' for h in 'ns' for v in 'mf')
src+=' rtl/hbm_accel/sm/repack/h2a7/ot_rp7_delay_ring.sv rtl/hbm_accel/sm/repack/h2a7/ot_hbm_smh_rp7_frame.sv rtl/hbm_accel/sm/repack/h2a7/tb_ot_hbm_smh_rp7_frame.sv'
defs=re.search(r'-DOT_SMH_CG_ENREG (.*?) \$SRCS',sh).group(1)
(OUT/'run_rp7_frame.sh').write_text(f'''#!/bin/bash
set -euo pipefail
OUT=$1; VAR=${{2:-0}}; MUT=${{3:-0}}; mkdir -p "$OUT"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary -j 8 -Wno-fatal --top-module tb_ot_hbm_smh_rp7_frame -GVAR="$VAR" -GMUT="$MUT" -GGN=2 -GGS=2 -GXB=2 -GLR=2 -GOS=1 -DOT_SMH_CG_ENREG {defs} {src} -Mdir "$OUT/obj" > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_ot_hbm_smh_rp7_frame" > "$OUT/run.log" 2>&1
grep -q '^R7_FRAME_LOCKSTEP PASS' "$OUT/run.log"
''')
print('Generated priced full frame, exact r6 miter, and fleet runner; no simulation performed locally.')
