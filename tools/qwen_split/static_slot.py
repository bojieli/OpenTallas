#!/usr/bin/env python3
"""Generate separately named static slot around the new native parent."""
from pathlib import Path
import re
root=Path(__file__).resolve().parents[2];src=root/'rtl/physical/ot_qfd_tt_ctlm_split_slot.sv';s=src.read_text()
# Resolve just the opt-in monitor macro. Retain independent bench mutant branches.
s=re.sub(r'`ifdef OT_QFD_XPF_MONITOR\n(.*?)`else\n.*?`endif',r'\1',s,flags=re.S) if False else s
lines=[];inside=False;emit=True
for line in s.splitlines(True):
 if line.strip()=='`ifdef OT_QFD_XPF_MONITOR':inside=True;emit=True;continue
 if inside and line.strip()=='`else':emit=False;continue
 if inside and line.strip()=='`endif':inside=False;emit=True;continue
 if emit:lines.append(line)
s=''.join(lines);s=s[s.index('module qfd_tt_ctlm_s'):];s=s.replace('module qfd_tt_ctlm_s','module qfd_tt_ctlm_static_s',1).replace('XPF_TRANSPORT_EDGES=0','XPF_TRANSPORT_EDGES=-1')
s=s.replace('    input wire ck_xpf,','''    input wire ck_xpf,
    input wire ck_me_sched,
    input wire cp_active,output wire [55:0] cp,
    input wire su_image_ready,output wire control_stores_ready,output wire [75:0] program_obs,
    output wire layer_context_v,output wire [17:0] native_tok,native_pos,
    output wire [379:0] native_cmd,
    input wire [94:0] native_ret,
    output wire [5:0] command_stage,''',1)
s=re.sub(r'^\s*(?:input|output)\s+wire(?:\s*\[[^\n]+\])?\s+(?:xd|xr),\n','',s,flags=re.M)
for name in ['w_x_rdy','w_x_dv','w_x_dc','w_x_dcs','w_x_dsp']:
 s=re.sub(r'^\s*wire(?:\s*\[[^\n]+\])?\s+'+name+r';\n','',s,flags=re.M)
 s=re.sub(r'^\s*assign '+name+r' = [^\n]*\n','',s,flags=re.M)
a=s.index('    wire [52:0] m_xd =');b=s.index('    wire [91:0] m_xm =',a);s=s[:a]+s[b:]
a=s.index('    // PC identity comes from');b=s.index('    // Transport parameter',a)
s=s[:a]+'''    wire [15:0] actual_me_observe,monitor_me;
    ot_hdc_delay #(.W(16),.D(1),.RESET(1)) u_xpf_me_face
      (.clk(ck_xpf),.rst_n(monitor_rs),.d(actual_me_observe),.q(monitor_me));
    wire xpf_me_event=monitor_me[15];
    wire [11:0] xpf_me_pc=monitor_me[11:0];
'''+s[b:]
s=s.replace('|me_map_fault','')
s=s.replace('    wire monitor_rs;', '    wire me_image_ready,xpf_loader_ready,xpf_monitor_ready;\n    assign control_stores_ready=me_image_ready&&su_image_ready&&xpf_loader_ready&&xpf_monitor_ready;\n    wire monitor_rs;')
s=s.replace('ot_qfd_xpf_pw_loader u_xpf_loader','ot_qfd_xpf_dense_pw_loader u_xpf_loader')
s=s.replace('.stop_cycle(stop_cycle),.fault(xpf_loader_fault)', '.stop_cycle(stop_cycle),.image_ready(xpf_loader_ready),.fault(xpf_loader_fault)')
s=s.replace('.xpf(xpf),.fault(xpf_schedule_fault)', '.xpf(xpf),.image_ready(xpf_monitor_ready),.fault(xpf_schedule_fault)')
s=s.replace('ot_qfd_tt_ctlm_split_hard u_body (','ot_qfd_tt_ctlm_static_parent u_body (\n        .ck_me_sched(ck_me_sched),\n        .cp_active(cp_active),.cp(cp),\n        .me_image_ready(me_image_ready),.program_obs(program_obs),\n        .layer_context_v(layer_context_v),.native_tok(native_tok),.native_pos(native_pos),\n        .native_cmd(native_cmd),.native_ret(native_ret),.command_stage(command_stage),\n        .me_observe(actual_me_observe),')
s=s.replace('.dvm_cmd(ib)', '.rom_cmd(ib)')
s=s.replace(".cp_issue(1'b0),.cp_pc(12'd0),.me_issue(xpf_me_event)",".cp_issue(monitor_me[15]&&monitor_me[13:12]==3),.cp_pc(xpf_me_pc),.me_issue(xpf_me_event&&monitor_me[13:12]==1)")
for name in ['x_rdy','x_dv','x_dc','x_dcs','x_dsp']:s=re.sub(r'^\s*\.'+name+r'\([^\n]*\),\n','',s,flags=re.M)
s=s.replace('    input  wire uf,','    input  wire [3:0] uf,').replace('    assign w_up_fault = uf;','    assign w_up_fault = |uf; // Four real upper leaves; existing downstream fault capture is retained.')
s=s.replace('    wire w_rst_n;', '    generate if(XPF_TRANSPORT_EDGES<0)begin:g_unassigned_arm_route\n      initial $error("native XPF transport edges require assigned physical route");\n    end endgenerate\n    wire w_rst_n;',1)
# TP8 selected hardware has exactly three NB3 serializers; remove inherited six-band-only ports.
for k in (3,4,5):
    s=re.sub(r'^    output wire mer'+str(k)+r',\n','',s,flags=re.M)
    s=s.replace(',rf'+str(k),'').replace('assign mer'+str(k)+'=w_me_clk_en;','').replace('|rf'+str(k),'')
(root/'rtl/qwen_sys/static_schedule_20261014/qfd_tt_ctlm_static_s.sv').write_text('// New native static slot master; fresh physical qualification required.\n// Existing c341/f104/lc26 packing retained; obsolete VM xd/xr removed.\n'+s)
