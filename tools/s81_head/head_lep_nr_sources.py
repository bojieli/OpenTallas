#!/usr/bin/env python3
"""Derive the head's real no-repair LEP core from current selected S81 source.

Existing S81 masters stay byte-identical. New head-only module names retain
all arithmetic, queues, credits and timing; the SRAM helper uses real r0c0
macros with no repair pins. Physical hardening remains a fresh head build.
"""
import argparse,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_lep.sv','rtl/lib/ot_sram_oldread_wreg.sv','rtl/dsrom_sys/s81_dv/slice/dsdv_mu_land.sv','rtl/lib/ot_sram_showahead_1r1w.sv']

def module(text,name):
 m=re.search(r'^module\s+'+re.escape(name)+r'\b.*?^endmodule\b',text,re.M|re.S)
 if not m:raise ValueError('missing exact source module '+name)
 return m.group()

def derive(root):
 src=[(root/p).read_text() for p in SOURCES]
 core=module(src[0],'ot_s81sl_lep_core').replace('module ot_s81sl_lep_core','module ot_s81hd_lep_core_nr',1)
 # Slang requires a declared generate index even in the inactive SAFE_FIFO branch.
 core=core.replace('for(c=0;c<NA;c=c+1)', 'for(genvar c=0;c<NA;c=c+1)')
 core=core.replace('ot_sram_oldread_wreg #(', 'ot_sram_oldread_wreg_nr #(')
 core=core.replace('ot_sram_showahead_1r1w #(', 'ot_sram_showahead_1r1w_head_nr #(')
 idx=module(src[0],'ot_s81sl_lep_mu_ab_idx').replace('module ot_s81sl_lep_mu_ab_idx','module ot_s81hd_lep_idx_nr',1).replace('ot_s81sl_lep_core #(', 'ot_s81hd_lep_core_nr #(')
 # Expose the wrapper's existing mode as an explicit opt-in. Default1 keeps
 # every prior caller identical; the current head no-index leaf selects0.
 idx=idx.replace('IN_PIPE = 0, parameter integer NATIVE32 = 0',
                 'IN_PIPE = 0, parameter integer NATIVE32 = 0, parameter integer IDX_EN = 1')
 idx=idx.replace('.IDX_EN(1)) u', '.IDX_EN(IDX_EN)) u')
 mem=module(src[1],'ot_sram_oldread_wreg').replace('module ot_sram_oldread_wreg','module ot_sram_oldread_wreg_nr',1)
 mem=mem.replace('ot_sram_1r1w_512x128_m4_r2c2 u_m','ot_sram_1r1w_512x128_m4_r0c0 u_m')
 old=".w_mask_in({128{1'b1}}),\n     .rr_en(2'b00),.rr_addr(14'd0),.cr_en(2'b00),.cr_sel(14'd0));"
 if old not in mem:raise ValueError('repair-port source pattern changed')
 mem=mem.replace(old,".w_mask_in({128{1'b1}}));")
 # DIE-HEAD-71 (hd_lep0N l48ub a6 LEC NOT EQ, 11-05): the MU TX window tag bit 0 is the constant 1 of
 # {pos, user, land, 1}.  The source keeps it as a no-reset flop that only ever loads 1'b1, so synthesis
 # removes it and the register-mapped LEC finds a gold-only free register (w_t[0], X until the first load).
 # Head-only safe form: w_t holds bits 32:1 and wtag bit 0 is the constant wire.  wtag is read only while a
 # window is open (wn != 0, set by the same mcv load), so every observed value is unchanged: 0 added cycles.
 for old,new in [('reg w_ab, te; reg [32:0] w_t;','reg w_ab, te; reg [32:1] w_t;'),
                  ("w_t <= {mcq[33:13], mcq[12:3], mcq[2], 1'b1};","w_t <= {mcq[33:13], mcq[12:3], mcq[2]};"),
                  ('localparam integer LO=wt*9,W=(33-LO<9)?33-LO:9;',
                   'localparam integer LO0=wt*9,W0=(33-LO0<9)?33-LO0:9,LO=(LO0==0)?1:LO0,W=(LO0==0)?W0-1:W0;'),
                  ('assign wtag = w_t;',"assign wtag = {w_t, 1'b1};")]:
  if core.count(old)!=1:raise ValueError('MU TX tag source pattern changed: '+old)
  core=core.replace(old,new)
 # DIE-HEAD-84 11-07 (opt-in TXI, default 0 = every line above unchanged in function): TXI[4t+:4] registered stages
 # on TX lane t's ingress {push, address-group pushes, write word} so the lane FIFO (its SRAM column, pointers,
 # credits, read pipeline) can sit beside its own pair while the frame stays at the hub.  The TX path is feed-forward
 # (no lane state reaches the frame), so the stages only delay every write of lane t by TXI cycles: same words, same
 # order, same overflow fault.  Each stage is one instance g_tx[t].g_txi.g_s[j] (FIRM-placeable along the leg).
 for old,new in [('    parameter integer IN_PIPE = 0      // 1 (LEPCAP 10-19)','    parameter integer IN_PIPE = 0,     // 1 (LEPCAP 10-19)'),
                 ('\n) (\n    input  wire            clk,',"\n    parameter [15:0]  TXI = 16'h0000   // DIE-HEAD-84: per-lane TX ingress stages (see g_tx); 0 = none\n) (\n    input  wire            clk,"),
                 ('        wire psh = (SAFE_FIFO)?push_lane[2*t+t/2]:pp[t / 2];\n',
                  '        wire psh_s = (SAFE_FIFO)?push_lane[2*t+t/2]:pp[t / 2];\n'
                  '        wire psh; wire [TX_NA-1:0] pg_s, pgx; wire [H:0] wdx;\n'
                  '        for(genvar gi=0;gi<TX_NA;gi=gi+1)begin:g_pgs assign pg_s[gi]=push_group[2*gi+t/2]; end\n'
                  '        ot_s81hd_lep_txi #(.W(H+1),.NG(TX_NA),.N(TXI[4*t+:4])) g_txi(.clk(clk),.rn(rt),.psh_i(psh_s),.pg_i(pg_s),\n'
                  '            .wd_i({sq[t/2],(t%2==0)?hf0:hf1}),.psh_o(psh),.pg_o(pgx),.wd_o(wdx));\n'),
                 ('.wd({sq[t/2],(t%2==0)?hf0:hf1})','.wd(wdx)'),
                 ('.wd({sq[t / 2], (t % 2 == 0) ? hf0 : hf1})','.wd(wdx)')]:
  if core.count(old)!=1:raise ValueError('TXI source pattern changed: '+old[:50])
  core=core.replace(old,new)
 if core.count('push_group[2*c+t/2]')!=4:raise ValueError('TXI push-group pattern changed')
 core=core.replace('push_group[2*c+t/2]','pgx[c]')
 idx=idx.replace('parameter integer IDX_EN = 1\n',"parameter integer IDX_EN = 1, parameter [15:0] TXI = 16'h0000\n",1)
 if '.IDX_EN(IDX_EN)) u' not in idx:raise ValueError('idx pattern changed')
 idx=idx.replace('.IDX_EN(IDX_EN)) u','.IDX_EN(IDX_EN), .TXI(TXI)) u',1)
 txi=r"""module ot_s81hd_lep_txi #(parameter integer W = 553, parameter integer NG = 18, parameter integer N = 0) (
    input  wire          clk, rn,
    input  wire          psh_i, input wire [NG-1:0] pg_i, input wire [W-1:0] wd_i,
    output wire          psh_o, output wire [NG-1:0] pg_o, output wire [W-1:0] wd_o
);
    // DIE-HEAD-84: N registered stages on a TX lane's ingress; the pushes clear on the lane reset, the word is reset-free
    wire [NG:0] v [0:N]; wire [W-1:0] d [0:N];
    assign v[0] = {pg_i, psh_i}; assign d[0] = wd_i;
    // DIE-HEAD-85: each stage is a kept leaf (ot_s81hd_lep_txi_st, keep_hierarchy): lanes 0 / 1 share the push-group D
    // and lanes 0 / 2 (1 / 3) the word D, so flattened (* keep *) regs were folded across lanes by opt_merge (vD kit LEC
    // NOT EQUIVALENT 485 on lane 0's FIFO state: gate lane 0 read lane 1's g_txi.g_s[0].vq); a kept leaf cannot fold.
    for (genvar j = 0; j < N; j = j + 1) begin : g_s
        ot_s81hd_lep_txi_st #(.W(W), .NV(NG + 1)) u_st(.clk(clk), .rn(rn), .v_i(v[j]), .d_i(d[j]), .v_o(v[j + 1]), .d_o(d[j + 1]));
    end
    assign {pg_o, psh_o} = v[N];
`ifdef OT_S81HD_LEPK_MUT_TXISKEW
    assign wd_o = d[(N > 0) ? N - 1 : 0];             // MUTANT: the word one stage ahead of its pushes
`else
    assign wd_o = d[N];
`endif
endmodule

(* keep_hierarchy, keep *)
module ot_s81hd_lep_txi_st #(parameter integer W = 553, parameter integer NV = 19) (
    input  wire          clk, rn,
    input  wire [NV-1:0] v_i, input wire [W-1:0] d_i,
    output reg  [NV-1:0] v_o, output reg  [W-1:0] d_o
);
    // one TXI stage: the pushes clear on the lane reset, the word is reset-free
    always @(posedge clk or negedge rn) if (!rn) v_o <= '0; else v_o <= v_i;
    always @(posedge clk) d_o <= d_i;
endmodule"""
 land=module(src[2],'dsdv_mu_land').replace('module dsdv_mu_land','module dsdv_mu_land_head_nr',1)
 land=land.replace('ot_sram_1r1w_128x256_m1_r2c2 u_m','ot_sram_1r1w_128x256_m1_r0c0 u_m')
 old_land=".w_mask_in({256{1'b1}}),\n                    .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));"
 # Only the D<=128 branch is active for the head's NS1/NB80. Preserve the
 # inactive D>128 branch as source history; reject selecting it in this master.
 if old_land not in land:raise ValueError('MU landing repair-port pattern changed')
 land=land.replace(old_land,".w_mask_in({256{1'b1}}));",1)
 land=land.replace('    localparam integer TG = 1045;', '    initial if(NS*NB>128)$fatal(1,"head NR landing supports <=128 words");\n    localparam integer TG = 1045;')
 show=module(src[3],'ot_sram_showahead_1r1w').replace('module ot_sram_showahead_1r1w','module ot_sram_showahead_1r1w_head_nr',1)
 show=show.replace('ot_sram_1r1w_32x128_m1 u_m','ot_sram_1r1w_32x128_m1_r0c0 u_m')
 record=dict(schema='opentallas.s81.head-lep-nr-source.v1',sources={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in SOURCES},
             changes=['head-only module names','real512x128_m4_r0c0 instead of tied-repair r2c2','no data/control/credit/latency change',
                      'MU TX tag bit 0 = constant wire (no constant-load flop; LEC safe form, 11-05)',
                      'opt-in TXI per-lane TX ingress stages (DIE-HEAD-84 11-07; default 0 = no added cycle)'],added_cycles=0,
             physical='new head provider; no inherited physical view or signoff')
 header='`timescale 1ns/1ps\n// Generated by tools/s81_head/head_lep_nr_sources.py; do not edit.\n'
 return header+core+'\n\n'+idx+'\n\n'+mem+'\n\n'+land+'\n\n'+show+'\n\n'+txi+'\n',record

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--build-macro',action='store_true');ap.add_argument('--out',type=Path,default=ROOT/'rtl/dsrom_sys/s81_head/generated/ot_s81hd_lep_nr.sv');ap.add_argument('--record',type=Path,required=True);ap.add_argument('--check',action='store_true');a=ap.parse_args()
 if a.build_macro:
  import sys
  sys.path.insert(0,str(ROOT/'tools/mem_compiler'))
  import sram_gen,build_aligned_v2 as A
  out=ROOT/'physical/asap7_memory_macros_v2'
  for words,bits in [(128,256),(32,128)]:
   spec=sram_gen.SramSpec(name=f'ot_sram_1r1w_{words}x{bits}_m1_r0c0',words=words,bits=bits,mux=1,banks=1,ports='1r1w',spare_rows=0,spare_cols=0)
   with A.patched(sram_gen,macro_outline=A.aligned_outline,write_lef=A.aligned_write_lef,GENERATOR_VERSION=f"{sram_gen.GENERATOR_VERSION}+{A.ALIGN_VERSION}"):
    sheet=sram_gen.compile_macro(spec,out)
   area=sheet['area'];A.finish(out,spec.name,None,(area['macro_width_um'],area['macro_height_um']),{'kind':'sram','head_new_shape':True})
 text,record=derive(ROOT)
 if a.check:
  if a.out.read_text()!=text:raise SystemExit('STALE head LEP derived source')
 else:a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(text)
 a.record.parent.mkdir(parents=True,exist_ok=True);a.record.write_text(json.dumps(record,indent=2)+'\n')
 print('HEAD_LEP_NR_SOURCES PASS; original masters unchanged; added cycles0')
