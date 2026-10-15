#!/usr/bin/env python3
"""Deterministic opt-in source extraction; existing caller files never edited."""
from pathlib import Path
import hashlib,json,subprocess
R=Path(__file__).resolve().parents[3]; D=R/'rtl/physical'
def rep(s,a,b):
 assert s.count(a)==1,(a[:80],s.count(a));return s.replace(a,b)
anchors={
 'ot_hdc_vstream_static_relay_entries.sv':'b50dbbd1b1923b780ddeb3f931d2277bc8a5de0f2d074389641a4c119fb5ec79',
 'ot_qfd_sp_su64_static_glue_entries.sv':'e66864c38973478e8e7bbc5f44b92d93f1e94dda42276b41ec81ed6115c908b1',
 'qfd_sp_su64_sfu_glue_entries.sv':'770f3ab5f30e40657a3b4982d8f35b3a77febc78a054f81972003df72714d7f0'}
def original(name):
 return subprocess.check_output(['git','show','685dad9b5:rtl/physical/'+name],cwd=R).decode()
for name,sha in anchors.items():
 assert hashlib.sha256(original(name).encode()).hexdigest()==sha,('source anchor changed',name)
pins='input wire [7:0] ck_octet,input wire ck_red_input,\n    '
s=original('ot_hdc_vstream_static_relay_entries.sv')
s=rep(s,'module ot_hdc_vstream_static_relay_entries #(','module ot_hdc_vstream_station_candidate #(\n    parameter integer STATION_CUT=0,')
s=rep(s,'    input wire[SW-1:0]ck_head', '    '+pins+'output wire [499:0] station_b_d,output wire [2:0] station_b_v,\n    input wire [3999:0] station_b_q,input wire [23:0] station_b_vq,\n    input wire[SW-1:0]ck_head')
a=s.index('    generate for (g = 0; g < NG;');b=s.index('    genvar l;',a);old=s[a:b]
new=old.replace('if (LT != 0) begin : g_on','if (STATION_CUT != 0) begin:g_cut\n            wire [499:0] gb=station_b_q[500*g+:500];\n            wire [2:0] gv=station_b_vq[3*g+:3];\n        end else if (LT != 0) begin : g_on')
# Actual lane references keep the original g_on hierarchy, so use an outer
# original-named g_on scope and conditional state implementation inside it.
new=old.replace('(* keep *) reg [GBW-1:0] gb;','wire [GBW-1:0] gb;').replace('(* keep *) reg [2:0]     gv;','wire [2:0] gv;')
x=new.index('            reg rg;');y=new.index('\n        end\n',x)
body=new[x:y].replace(' gv <=',' gv_r <=').replace(' gb <=',' gb_r <=')
new=new[:x]+'''            if(STATION_CUT!=0)begin:g_cut
                assign gb=station_b_q[500*g+:500];assign gv=station_b_vq[3*g+:3];
            end else begin:g_inline
                reg [GBW-1:0] gb_r;reg [2:0]gv_r;
                assign gb=gb_r;assign gv=gv_r;
'''+body+'\n            end'+new[y:]
s=s[:a]+'''    assign station_b_d={v,fin_th,rrow,asi,bsi,csi,dsi,asrc,bsrc,csrc,mc,md,redsq,ma,mb,dst,red,ad,cls,i_sfu,imm1,imm2,wrom_q};
    assign station_b_v={emit,accept,v_last_r};
'''+new+s[b:]
a=s.index('    reg              rd_v,');b=s.index('    wire f_red;',a);old=s[a:b]
decl=old[:old.index('    integer li;')].replace('reg ','wire ')
body=old[old.index('    integer li;'):]
# Original variable names scoped in generate, expose via same-name wires.
body=body.replace('rd_v','rv').replace('rd_mx','rm').replace('rd_sq','rsq').replace('rd_last','rl').replace('rd_addr','ra').replace('rd_x','rx')
s=s[:a]+decl+'''    generate if(STATION_CUT!=0)begin:g_rd_cut
      ot_qfd_su_reducer_station_candidate u_rd(.clk(ck_red_input),.rst_n(rst_c),
       .l_ov(l_ov),.l_red(l_red),.l_redsq(l_redsq),.l_last(l_last),.l_raddr(l_raddr),.l_out(l_out),
       .rd_v(rd_v),.rd_mx(rd_mx),.rd_sq(rd_sq),.rd_last(rd_last),.rd_addr(rd_addr),.rd_x(rd_x));
    end else begin:g_rd_inline
      reg rv,rm,rsq,rl;reg[AW-1:0]ra;reg[SW*32-1:0]rx;
      assign {rd_v,rd_mx,rd_sq,rd_last,rd_addr,rd_x}={rv,rm,rsq,rl,ra,rx};
'''+body+'    end endgenerate\n'+s[b:]
s=rep(s,'    localparam integer LS = $clog2(SW);','    initial if(STATION_CUT!=0 && (SW!=64||NW!=18||AW!=24||WR!=16))$fatal(1,"station native shape");\n    localparam integer LS = $clog2(SW);')
(D/'ot_hdc_vstream_station_candidate.sv').write_text(s)
s=original('ot_qfd_sp_su64_static_glue_entries.sv');s=rep(s,'module ot_qfd_sp_su64_static_glue_entries #(','module ot_qfd_sp_su64_station_candidate #(\n    parameter integer STATION_CUT=0,')
s=rep(s,'    input wire[63:0]ck_head','    '+pins+'input wire[63:0]ck_head')
a=s.index('    ot_hdc_delay #(.W(FI + NW + SW*64)');b=s.index('    ot_hdc_delay #(.W(2)',a);old=s[a:b]
s=s[:a]+'''    wire[499:0] station_b_d;wire[2:0]station_b_v;wire[3999:0]station_b_q;wire[23:0]station_b_vq;
    generate if(STATION_CUT==0)begin:g_if_inline
'''+old+'''    end else begin:g_if_cut
      ot_hdc_delay #(.W(FI+NW),.D(IS)) u_fields(.clk(clk),.rst_n(rst_n),.d({f_d,tok}),.q({f_q,tok_q}));
    end endgenerate
'''+s[b:]
s=rep(s,'ot_hdc_vstream_static_relay_entries #(.RELAY_CUT(1),','ot_hdc_vstream_station_candidate #(.STATION_CUT(STATION_CUT),.RELAY_CUT(1),')
s=rep(s,' u_su (',' u_su (.ck_octet(ck_octet),.ck_red_input(ck_red_input),.station_b_d(station_b_d),.station_b_v(station_b_v),.station_b_q(station_b_q),.station_b_vq(station_b_vq),')
a=s.index('    ot_hdc_delay #(.W(FS)');b=s.index('\nendmodule',a);old=s[a:b]
s=s[:a]+'''    generate if(STATION_CUT==0)begin:g_os_inline
'''+old+'''    end else begin:g_os_cut
      ot_hdc_delay #(.W(FS-2*SW),.D(OS),.RESET(1))u_status(.clk(clk),.rst_n(rst_n),
       .d({accepted_count,s_ready,s_idle,s_active,s_inflight,s_fault||e_fault,s_wrom_re,s_progress,s_rows}),
       .q({accepted_ops,ready,idle,obs_active,obs_inflight,fault,wrom_fault,progress,progress_rows}));
      for(genvar g=0;g<8;g=g+1)begin:g_octet
       ot_qfd_su_octet_station_candidate u_station(.clk(ck_octet[g]),.rst_n(rst_n),.b_rst_n(rs),
        .crom_d(crom_m[512*g+:512]),.crom_q(crq_q0[512*g+:512]),
        .os_d({s_crom_addr[192*g+:192],s_kv_waddr[192*g+:192],s_kv_wdata[256*g+:256]}),
        .os_q({crom_addr[192*g+:192],kv_waddr[192*g+:192],kv_wdata[256*g+:256]}),
        .os_v({s_crom_re[8*g+:8],s_kv_we[8*g+:8]}),.os_vq({crom_re[8*g+:8],kv_we[8*g+:8]}),
        .b_d(station_b_d),.b_v(station_b_v),.b_q(station_b_q[500*g+:500]),.b_vq(station_b_vq[3*g+:3]));
      end
    end endgenerate
    initial if(STATION_CUT!=0 && (SW!=64||NW!=18||AW!=24||W!=16||IS!=1||OS!=1))$fatal(1,"station native shape/edges");
'''+s[b:]
(D/'ot_qfd_sp_su64_station_candidate.sv').write_text(s)
s=original('qfd_sp_su64_sfu_glue_entries.sv');s=rep(s,'module qfd_sp_su64_sfu_glue_entries #(','module qfd_sp_su64_sfu_station_candidate #(parameter integer STATION_CUT=0,')
s=rep(s,'    input wire ck,rst_n,','    input wire ck,rst_n,\n    input wire ck_octet0,ck_octet1,ck_octet2,ck_octet3,ck_octet4,ck_octet5,ck_octet6,ck_octet7,ck_red_input,')
s=rep(s,'ot_qfd_sp_su64_static_glue_entries #(','ot_qfd_sp_su64_station_candidate #(.STATION_CUT(STATION_CUT),')
s=rep(s,' .clk(ck),.rst_n(rst_n),.go(si[0])',' .ck_octet({ck_octet7,ck_octet6,ck_octet5,ck_octet4,ck_octet3,ck_octet2,ck_octet1,ck_octet0}),.ck_red_input(ck_red_input),\n .clk(ck),.rst_n(rst_n),.go(si[0])')
(D/'qfd_sp_su64_sfu_station_candidate.sv').write_text(s)
print(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.glob('*station_candidate.sv')},indent=2))
