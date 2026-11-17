#!/usr/bin/env python3
from pathlib import Path
import hashlib,json
import argparse
ap=argparse.ArgumentParser(description='Emit explicit opt-in selected head/tile round96 source; originals retained')
ap.add_argument('--head-source',type=Path,required=True);ap.add_argument('--tile-source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
a=ap.parse_args();P=a.out;P.mkdir(parents=True,exist_ok=True);hp=a.head_source;tp=a.tile_source
h=hp.read_text();t=tp.read_text()
if hashlib.sha256(h.encode()).hexdigest()!='d423a75beb72d8e473ece60fbfb29ad03f74161ece9dead2bddfb57ea439ac24' or hashlib.sha256(t.encode()).hexdigest()!='6ebb478e5c5d4748b9456698411f1ea4f223a7cb9e54a94c85d54aecd6898e80': raise ValueError('selected-source identity differs; source review and profile required')
def sub(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
h=sub(h,'    integer hb;','''`ifdef OT_QC_AR_ROUND96
    reg [6:0] ar_wait;
    wire ar_role = ib_q[378:361]==18'd4096 && b_tiles==3 &&
        (b_kk==2 || b_kk==6) && !b_wsrc && b_split==8 &&
        !ib_q[27] && ib_q[26] && !ib_q[25];
    wire ar_boundary = busy && te_c[0] && keq_c[0] && !rz_c[0] && ar_role;
    wire [6:0] ar_wait_next = g_q ? 7'd0 : ar_boundary ?
        (b_kk==2 ? 7'd80 : 7'd48) : ar_wait!=0 ? ar_wait-1'b1 : 7'd0;
    always @(posedge ck or negedge rr[0])
        if(!rr[0]) ar_wait<=0; else ar_wait<=ar_wait_next;
`endif
    integer hb;''')
h=sub(h,"        end else if (busy) begin\n            ph_n = ph + 1'b1;", """        end else if (busy) begin
`ifdef OT_QC_AR_ROUND96
            ph_n = (ar_wait!=0) ? 3'd0 : ph + 1'b1;
`else
            ph_n = ph + 1'b1;
`endif""")
h=sub(h,'    wire          RD_x   = gl4[1] | busy_n;', '''`ifdef OT_QC_AR_ROUND96
    wire          RD_x   = gl4[1] | (busy_n && ar_wait_next==0);
`else
    wire          RD_x   = gl4[1] | busy_n;
`endif''')
a='    if (REGROOT < 6) begin : g_ctl_all'
b='''`ifdef OT_QC_AR_ROUND96
    reg [6:0] ar_wait;
    reg ar_role;
    wire ar_input_role = i_nout==4096 && i_tiles==3 && (i_k==2 || i_k==6) &&
        !i_wsrc && i_split==8 && !i_mmode && i_oen && !i_amax;
    wire ar_boundary = active && !pend && ar_wait==0 && j_last && k_last && !t_last && ar_role;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin ar_wait<=0;ar_role<=0;end
        else begin
            if(go && !active && !pend) begin ar_wait<=0;ar_role<=ar_input_role;end
            else if(ar_boundary) ar_wait<=(ktot_r==2 ? 7'd80 : 7'd48);
            else if(ar_wait!=0) ar_wait<=ar_wait-1'b1;
        end
    end
    initial if(REGROOT!=3) $fatal(1,"AR_ROUND96 qualified selected REGROOT3 only");
`endif
'''+a
t=sub(t,a,b)
a='''            end else if (!active) begin'''
# unique inside selected g_ctl_all region
start=t.index('    if (REGROOT < 6) begin : g_ctl_all');end=t.index('    end else if (REGROOT < 8)',start)
x=t[start:end];x=sub(x,a,'''`ifdef OT_QC_AR_ROUND96
            end else if(ar_wait!=0) begin
                wrom_re<=0; kv_re<=0;
`endif
            end else if (!active) begin''')
x=sub(x,'        assign acc = {5{active}};', '''`ifdef OT_QC_AR_ROUND96
        assign acc = {5{active && ar_wait==0}};
`else
        assign acc = {5{active}};
`endif''')
t=t[:start]+x+t[end:]
(P/'head_round96.sv').write_text(h);(P/'matvec_round96.sv').write_text(t)
(P/'source_contract.json').write_text(json.dumps({'schema':'opentallas.qwen.ar-round96-source.v1','default_off':True,'define':'OT_QC_AR_ROUND96','head_source':str(hp),'head_sha256':hashlib.sha256(hp.read_bytes()).hexdigest(),'tile_source':str(tp),'tile_sha256':hashlib.sha256(tp.read_bytes()).hexdigest(),'head_output_sha256':hashlib.sha256(h.encode()).hexdigest(),'tile_output_sha256':hashlib.sha256(t.encode()).hexdigest(),'profile':'model_before_build.json'},indent=2)+'\n')
