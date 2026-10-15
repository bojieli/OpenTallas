#!/usr/bin/env python3
"""Extract production controller/tree at existing two-edge station chains.
The source's own module remains the flat reference; each direction moves one
of its existing two enabled registers into each hardened leaf (zero new edges).
"""
import re,json
from pathlib import Path
src=Path('rtl/qwen_sys/redesign_qwen/ot_qfd_tt_ctlm_i.sv').read_text()
s=src[src.index('module ot_qfd_tt_ctlm_i #('):]
param,tail=s.split(') (',1);ph,body=tail.split(');',1);body=body.rsplit('endmodule',1)[0]
ph=re.sub(r'//[^\n]*','',ph)
ports={};direction=width=None
for item in ph.split(','):
 item=item.strip()
 m=re.fullmatch(r'(input|output)\s+wire\s*(\[[^\]]+\])?\s*(\w+)',item)
 if m:direction,width,name=m.groups();width=width or '';ports[name]=(direction,width)
 else:ports[item]=(direction,width)
cmdnames=['go','i_nout','i_tiles','i_k','i_wsrc','i_wbase','i_ts','i_ks','i_js','i_xbase','i_xks','i_xjs','i_xcs','i_jsh','i_split','i_wcs','i_round','i_obase','i_ots','i_ojs','i_mmode','i_oen','i_amax','i_rmax','i_mbase']
cmdwidth=[1,18,18,18,1,24,24,24,24,24,24,24,24,3,4,24,1,24,24,24,1,1,1,1,24]
retnames=['ready','idle','wrom_re','wrom_addr','am_idx','am_val','am_any','progress','fault'];retwidth=[1,1,1,24,18,32,1,16,1]
CW,RW=sum(cmdwidth),sum(retwidth)
headnames=['clk','rst_n','h_start','token','pos','prog_base','pw_v','pw_addr','pw_data','x_oacc','x_oidle','x_oprog','x_orows','kv_ok','kv_write_drained','me_mem_ok','m_fin_o','m_fidx_o','m_fval_o','me_clk_en','c_fault']+[n for n in ports if n.startswith('kvd_')]
treenames=['clk','rst_n','me_mem_ok']+[n for n in ports if n not in headnames]+[n for n in headnames if n not in ('clk','rst_n','me_mem_ok') and ports[n][0]=='input']
head=body[:body.index('    ot_qfd_issue_shell')]
# The tree-facing pin capture belongs to the tree leaf, not the head.
a=head.index('    wire up_fault_c');b=head.index('    (* keep',a)
dpin=head[a:b];head=head[:a]+head[b:]
# Controller never sees/produces the clock of another hardened leaf.
# Preserve original native idle/supply gating; tree has its own pruned shadow predictor.
shell=body[body.index('    ot_qfd_issue_shell'):body.index('    ot_hdc_delay #(.W(1), .D(DCU_M)')]
head+=shell
for line in body.splitlines():
 if 'ot_hdc_delay' in line and 'u_sd_me_' in line:
  head+=line.replace('.D(DCU_M)','.D(1)')+'\n'
 if 'ot_hdc_delay' in line and 'u_su_me_' in line:
  head+=line.replace('.D(DUC_M)','.D(1)')+'\n'
head+='    assign cmd = {'+', '.join('u_me_'+n for n in reversed(cmdnames))+'};\n'
head+='    assign {'+', '.join('u_me_'+n for n in reversed(retnames))+'} = ret;\n'
head+='    ot_hdc_delay #(.W(1),.D(OS),.RESET(1)) u_os_fin (.clk(clk),.rst_n(rsv[4]),.d(m_fin),.q(m_fin_o));\n'
a=body.index('    ot_hdc_delay #(.W(18 + 32)');b=body.index('    ot_qfd_tt_ctl #',a)
head+=body[a:b]
# Native clock-gated station updates become equivalent synchronous enables
# on the head's one root. The controller state already runs on this root.
# The pre-edge registered enable is exactly the ICG's sampled enable.
head=re.sub(r'ot_hdc_delay([^;]+?)\.clk\(c_me_clk\)',lambda m:'ot_tt_ce_delay'+m[1]+'.clk(clk), .en(me_clk_en)',head)
# Preserve native enable phase with a local controller shadow, not an enable
# arriving over a cross-tile combinational path. Only me_clk_en is live on
# the shadow: synthesis prunes unused data/argmax/descriptor state. Its two
# program macros are deliberately retained; complete production word kept
# by the actual issuing head, not re-encoded or truncated.
shadow_inputs=[n for n in headnames if ports[n][0]=='input']
tree='    wire rs;\n    ot_qfd_rst_stn #(.D(IS)) u_rs (.clk(clk),.rst_n(rst_n),.rst_q(rs));\n    wire local_en, ec;\n'
# qfd_tt_ctlm_head has no clock output port: its internal gate stays internal.
tree+='    qfd_tt_ctlm_head #('+', '.join('.'+p+'('+p+')' for p in ['DCU_M','DUC_M','XW','IS','OS','PSRAM','PMUT','HQ2','MEREG','RRG','PCUT','G','TPMUT','AUD'])+') u_shadow (\n'
tree+=',\n'.join('        .'+n+'('+n+')' for n in shadow_inputs)+',\n        .cmd(),.ret(ret),.me_clk_en(local_en));\n'
tree+='    ot_hdc_cg u_cg (.clk(clk),.en(local_en),.gclk(ec));\n'+dpin
for n,w in zip(cmdnames,cmdwidth):tree+=f'    wire [{w-1}:0] u_me_{n};\n'
for n,w in zip(retnames,retwidth):tree+=f'    wire [{w-1}:0] u_me_{n};\n'
tree+=f'''    reg [{CW-1}:1] cmd_data;
    reg cmd_go;
    always @(posedge ec) cmd_data<=cmd[{CW-1}:1];
    always @(posedge ec or negedge rs) if(!rs) cmd_go<=0; else cmd_go<=cmd[0];
    wire [{CW-1}:0] cq_raw={{cmd_data,cmd_go}};
`ifdef OT_TT_SPLIT_MUT
    wire [{CW-1}:0] cq=cq_raw ^ (cmd_go ? ({{{CW}{{1'b0}}}} | ({CW}'d1 << 19)) : {CW}'d0);
`else
    wire [{CW-1}:0] cq=cq_raw;
`endif
    assign {{'''+', '.join('u_me_'+n for n in reversed(cmdnames))+'} = cq;\n'
tree+=f'    reg [{RW-1}:0] ret_q;\n    always @(posedge ec or negedge rs) if(!rs) ret_q<=0; else ret_q<={{'+', '.join('u_me_'+n for n in reversed(retnames))+'};\n    assign ret=ret_q;\n'
a=body.index('    ot_qfd_tt_ctl #');b=body.index('    assign u_me_mx_we',a)
tree+=body[a:b].replace('.clk(c_me_clk)', '.clk(ec)').replace('.rst_n(rsv[0])','.rst_n(rs)')
tree+='''    reg [XW-1:0] me_acc;
    always @(posedge ec or negedge rs) if(!rs) me_acc<=0; else if(u_me_go) me_acc<=me_acc+1'b1;
    ot_hdc_delay #(.W(XW+17),.D(OS),.RESET(1)) u_snap(.clk(clk),.rst_n(rs),.d({me_acc,u_me_idle,u_me_progress}),.q({me_acc_o,me_idle_o,me_prog_o}));
'''
# No tree-source macro or controller is replaced with a behavioral stand-in.
params=['DCU_M','DUC_M','XW','IS','OS','PSRAM','PMUT','HQ2','MEREG','RRG','PCUT','G','TPMUT','AUD']
param=param.replace('parameter integer PSRAM = 0','parameter integer PSRAM = 1').replace('parameter integer HQ2 = 0','parameter integer HQ2 = 1').replace('parameter integer MEREG = 0','parameter integer MEREG = 3').replace('parameter integer RRG = 0','parameter integer RRG = 1').replace('parameter integer PCUT = 0','parameter integer PCUT = 1').replace('parameter integer G = 6144','parameter integer G = 3072').replace('parameter integer AUD = 0','parameter integer AUD = 33975')
def emit(name,names,extra,b):
 h=param.replace('ot_qfd_tt_ctlm_i',name,1)
 pp=[f'    {ports[n][0]} wire {ports[n][1]} {n}' for n in names]+extra
 return h+') (\n'+',\n'.join(pp)+'\n);\n'+b+'endmodule\n'
text='''`timescale 1ns/1ps
// Generated by tools/qwen_tt_split/gen_split.py from production ctlm_i.
// Split across the EXISTING DCU2/DUC2 stations: one launch and one capture
// stage per direction. No clock is forwarded. Head/tree have independent
// roots and native MEREG3 gates; tree-local shadow predicts the exact enable.
// Only shadow gate output is live: unused data fields prune, issuing head stays full.
// Full G3072 tree control, tag SRAMs, all operation fields/18-bit rows retained.
'''
text+=emit('qfd_tt_ctlm_head',headnames,[f'    output wire [{CW-1}:0] cmd',f'    input wire [{RW-1}:0] ret'],head)
text+=emit('qfd_tt_ctlm_tree',treenames,[f'    input wire [{CW-1}:0] cmd',f'    output wire [{RW-1}:0] ret'],tree)
pp=[]
for n in ports:
 if n=='clk':pp+=['    input wire ck_head','    input wire ck_tree']
 else:pp.append(f'    {ports[n][0]} wire {ports[n][1]} {n}')
text+=param.replace('ot_qfd_tt_ctlm_i','ot_qfd_tt_ctlm_split',1)+') (\n'+',\n'.join(pp)+f'\n);\n    wire [{CW-1}:0] cmd; wire [{RW-1}:0] ret;\n'
for module,names,clock in [('qfd_tt_ctlm_head',headnames,'ck_head'),('qfd_tt_ctlm_tree',treenames,'ck_tree')]:
 text+='    '+module+' #('+', '.join(f'.{p}({p})' for p in params)+') u_'+('head' if 'head' in module else 'tree')+' (\n'+',\n'.join(f'        .{n}({clock if n=="clk" else n})' for n in names)+',\n        .cmd(cmd),.ret(ret));\n'
text+='endmodule\n'
text+='''
// Edge-equivalent form of an enabled-clock delay line. Only head station
// registers use it; the complete engine retains native local clock gating.
module ot_tt_ce_delay #(parameter integer W=1,D=1,RESET=0)(
 input wire clk,rst_n,en,input wire [W-1:0] d,output wire [W-1:0] q);
 generate if(D==0) begin:g_wire
  assign q=d;
 end else begin:g_pipe
  reg [W-1:0] r[0:D-1];integer k;
  if(RESET!=0) begin:g_reset
   always @(posedge clk or negedge rst_n)
    if(!rst_n) begin for(k=0;k<D;k=k+1) r[k]<=0;end
    else if(en) begin r[0]<=d;for(k=1;k<D;k=k+1) r[k]<=r[k-1];end
  end else begin:g_data
   always @(posedge clk) if(en) begin r[0]<=d;for(k=1;k<D;k=k+1) r[k]<=r[k-1];end
  end
  assign q=r[D-1];
 end endgenerate
endmodule
'''
Path('rtl/physical/ot_qfd_tt_ctlm_split.sv').write_text(text)

# Fixed hard parent: no parameter overrides on hard-child names.
fixed=[]
for n in ports:
 if n=='clk': fixed+=['    input wire ck_head','    input wire ck_tree'];continue
 w=ports[n][1].replace('$clog2(G)','12').replace('XW','24').replace('G','3072')
 fixed.append(f'    {ports[n][0]} wire {w} {n}')
fp='// Fixed wires-only parent, one entry per independently rooted child.\nmodule ot_qfd_tt_ctlm_split_hard (\n'+',\n'.join(fixed)+f'\n);\n    wire [{CW-1}:0] cmd; wire [{RW-1}:0] ret;\n'
for module,names,clock in [('qfd_tt_ctlm_head',headnames,'ck_head'),('qfd_tt_ctlm_tree',treenames,'ck_tree')]:
 fp+='    '+module+' u_'+('head' if 'head' in module else 'tree')+' (\n'+',\n'.join('        .'+n+'('+ (clock if n=='clk' else n) +')' for n in names)+',\n        .cmd(cmd),.ret(ret));\n'
fp+='endmodule\n'
Path('rtl/physical/ot_qfd_tt_ctlm_split_parent.sv').write_text(fp)
Path('physical/qfd_tt_ctlm_split/seam.json').write_text(json.dumps({'command_bits':CW,'return_bits':RW,'command_lsb_first':dict(zip(cmdnames,cmdwidth)),'return_lsb_first':dict(zip(retnames,retwidth)),'station_cycles':{'head_launch':1,'tree_capture':1,'tree_launch':1,'head_capture':1},'original_DCU':2,'original_DUC':2,'added_station_cycles':0,'clock':'independent roots/native MEREG3 ICGs with tree-local pruned controller shadow; no clock or enable forwarding'},indent=1)+'\n')
print(CW,RW,headnames,treenames)
