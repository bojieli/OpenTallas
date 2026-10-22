#!/usr/bin/env python3
"""Copy exact search arithmetic; localize only stage-equivalent mux consumers."""
from pathlib import Path
import hashlib
r=Path(__file__).resolve().parents[3]
src=r/'rtl/dsrom_sys/s81_ph/ot_s81ph_sel_pipeline.sv'
s=src.read_text().split('module ot_s81ph_sel_ctl_pipe')[0]
s=s.replace('ot_s81ph_sel_su_pipe','ot_s81pa_sel_su')
def rep(a,b):
 global s
 assert s.count(a)==1,(a,s.count(a));s=s.replace(a,b)
rep('    reg [15:0]      gea;','    wire [15:0] gea_next;\n    wire [QW-1:0] q3_local[0:15];\n    generate for(genvar n32q=0;n32q<16;n32q=n32q+1)begin:g_q3_local\n      ot_s81pa_copy #(.W(QW),.ID(n32q))u_q(.clk(clk),.d(qt),.q(q3_local[n32q]));\n      assign gea_next[n32q]=(s3_r[XW*n32q+:XW]>={{(XW-QW){1\'b0}},q3_local[n32q]});\n    end endgenerate')
rep('        for (i = 0; i < 16; i = i + 1) gea[i] <= (s3_r[XW*i +: XW] >= {{(XW-QW){1\'b0}}, q3});','')
a=s.index('    reg [3:0]    ga;');b=s.index('    reg [XW-1:0] acc_a;',a)
s=s[:a]+'''    wire[3:0]ga;wire[XW-1:0]acca;
    generate for(genvar n32c=0;n32c<(XW+1)/2;n32c=n32c+1)begin:g_acca_local
      localparam integer LO=2*n32c,SW=(XW-LO<2)?XW-LO:2;
      wire[16*SW-1:0]lanes;
      for(genvar n32b=0;n32b<16;n32b=n32b+1)begin:g_lane
        assign lanes[SW*n32b+:SW]=s4_r[XW*n32b+LO+:SW];
      end
      wire[3:0]bin;wire valid_unused;
      ot_s81pa_prio16 #(.W(SW),.ID(n32c))u_mux(.clk(clk),.compare_next(gea_next),.data(lanes),.fallback({SW{1'b0}}),.value(acca[LO+:SW]),.bin(bin),.valid(valid_unused));
      if(n32c==0)assign ga=bin;
    end endgenerate
''' +s[b:]
rep('    reg [15:0]      geb;','    wire[15:0]geb_next;\n    wire[QW-1:0]qb3_local[0:15];\n    generate for(genvar n32q=0;n32q<16;n32q=n32q+1)begin:g_qb3_local\n      ot_s81pa_copy #(.W(QW),.ID(n32q+16))u_q(.clk(clk),.d(bm3[4+:QW]),.q(qb3_local[n32q]));\n      assign geb_next[n32q]=(u3_r[XW*n32q+:XW]>={{(XW-QW){1\'b0}},qb3_local[n32q]});\n    end endgenerate')
rep('        for (i = 0; i < 16; i = i + 1) geb[i] <= (u3_r[XW*i +: XW] >= {{(XW-QW){1\'b0}}, q_b3});','')
a=s.index('    reg [3:0]    bb;');b=s.index('    always @(posedge clk) begin\n        res_b <=',a)
s=s[:a]+'''    wire[3:0]bb;wire okb;wire[XW-1:0]aboveb;
    generate for(genvar n32c=0;n32c<(XW+1)/2;n32c=n32c+1)begin:g_above_local
      localparam integer LO=2*n32c,SW=(XW-LO<2)?XW-LO:2;
      wire[16*SW-1:0]lanes;
      for(genvar n32b=0;n32b<16;n32b=n32b+1)begin:g_lane
        assign lanes[SW*n32b+:SW]=u4_r[XW*n32b+LO+:SW];
      end
      wire[3:0]bin;wire valid;
      ot_s81pa_prio16 #(.W(SW),.ID(n32c+32))u_mux(.clk(clk),.compare_next(geb_next),.data(lanes),.fallback(acc_b4[LO+:SW]),.value(aboveb[LO+:SW]),.bin(bin),.valid(valid));
      if(n32c==0)begin assign bb=bin;assign okb=valid;end
    end endgenerate
    wire[Q*CB-1:0]eq_selected;
    generate for(genvar n32c=0;n32c<(Q*CB+1)/2;n32c=n32c+1)begin:g_eq_local
      localparam integer LO=n32c*2,SW=(Q*CB-LO<2)?Q*CB-LO:2;
      wire[16*SW-1:0]lanes;
      for(genvar n32b=0;n32b<16;n32b=n32b+1)begin:g_lane
        for(genvar n32k=0;n32k<SW;n32k=n32k+1)begin:g_bit
          localparam integer QU=(LO+n32k)/CB,BIT=(LO+n32k)%CB;
          assign lanes[SW*n32b+n32k]=bs_r[CB*(16*QU+n32b)+BIT];
        end
      end
      ot_s81pa_bin16 #(.W(SW),.ID(n32c))u_mux(.clk(clk),.selector_next(bb),.data(lanes),.value(eq_selected[LO+:SW]));
    end endgenerate
''' +s[b:]
rep('        for (s = 0; s < Q; s = s + 1)                // one edge after res_b (static counts only)\n            res_eq[CB*s +: CB] <= bs_r[CB*(16*s + res_b[3:0]) +: CB];','        res_eq <= eq_selected; // same res_b/bs_r ages; consumer-local fixed-bin mux')
out=r/'rtl/dsrom_sys/s81_dv/unit/bk/plana/n32/ot_s81pa_search.sv'
out.write_text('// Opt-in same-stage search consumer localization. Baseline SHA256 '+hashlib.sha256(src.read_bytes()).hexdigest()+'\n'+'\n'.join(x.rstrip()for x in s.splitlines()).rstrip()+'\n')
