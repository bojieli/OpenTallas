#!/usr/bin/env python3
"""Build a private hybrid shell proposal; no shared source is modified.

The mapped engine is fixed at AW32/HDMAX128/KVHMAX2/QKV1/APIPE0/QPIPE2/
NATIVE_ROWS1/QMUT0. Define OT_ENG_N32 only for that exact production copy.
The unselected branch retains RTL engine elaboration for CDC inspection.
Whole-tile native admission and behavioral equivalence remain required.
"""
import argparse,hashlib,re
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--shell',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args(); s=a.shell.read_text()
assert hashlib.sha256(a.shell.read_bytes()).hexdigest()=='f21beeef47679e7364a35e21eb0ea4f0b5c042dcbe6089494a761490147035e1'
start=s.index('    qkd_host_native_engine #(')
end=s.index('.n_beats(e_nbeat));',start)+len('.n_beats(e_nbeat));')
original=s[start:end]
# New reset banks release on exactly the same second clk_i edge as u_rsi.
# 2 x 17 leaves keeps each first-stage fanout <=17 and each leaf <=32.
lines=['`ifdef OT_ENG_N32',
 '    generate if (AW!=32 || HDMAX!=128 || KVHMAX!=2 || QKV_EN!=1 || APIPE!=0 || QPIPE!=2 || NATIVE_ROWS!=1 || MUT!=0) begin : g_wrong_engine_binding',
 '        QKC_ENGINE_PARAMETER_BINDING_MISMATCH refuse();',
 '    end endgenerate',
 '    wire [16:0] eng_reset_a, eng_reset_b;',
 '    ot_host_reset_bank #(.N(17)) u_eng_reset_a (.clk(clk_i), .async_rst_n(rst_n), .sync_rst_n(eng_reset_a));',
 '    ot_host_reset_bank #(.N(17)) u_eng_reset_b (.clk(clk_i), .async_rst_n(rst_n), .sync_rst_n(eng_reset_b));',
 '    wire take_p_a, take_p_b;',
 '    qkc_ingest_take_copy u_take_a (.a(hv_i), .b(!f_any), .c(hcl==2\'d2), .y(take_p_a));',
 '    qkc_ingest_take_copy u_take_b (.a(hv_i), .b(!f_any), .c(hcl==2\'d2), .y(take_p_b));',
 '    wire e_done_a, e_done_b;',
 '    qkd_host_native_engine_n32 u_eng (',
 '        .clk(clk_i), .clk_bank(clk_i_bank), .clk_out(clk_i_out), .rst_n(eng_reset_a[0]),']
for k in range(1,34):
 bank,idx=('a',k) if k<17 else ('b',k-17)
 lines.append(f'        .rst_n__c{k}(eng_reset_{bank}[{idx}]),')
lines += ['        .d_v(take_d), .d_rdy(e_drdy), .d_data(hdesc),',
 '        .in_v(take_p_a), .in_v__c1(take_p_b), .in_rdy(e_inrdy), .in_data(pay),',
 '        .w_v(e_wv), .w_rdy(e_wrdy), .w_addr(e_waddr), .w_data(e_wdata),',
 '        .r_v(e_rv), .r_rdy(e_rrdy), .r_addr(e_raddr), .rd_v(e_rdv), .rd_data(e_rdd),',
 '        .done_v(e_done), .done_v__c1(e_done_a), .done_v__c2(e_done_b),',
 '        .done_tag(e_tag), .busy(e_busy), .n_sectors(e_nsec), .n_beats(e_nbeat));',
 '`else', original, '`endif']
s=s[:start]+'\n'.join(lines)+s[end:]
old="""        if (e_done) cx_w <= {8'h01, 8'd0, (MUT == 2) ? e_tag + 8'd1 : e_tag, 8'd0, e_nsec};
        else if (f_any && !f_sent) cx_w <= {8'hFF, 48'd0, f_code};"""
assert s.count(old)==1
new="""`ifdef OT_ENG_N32
        if (e_done_a) cx_w[31:0] <= e_nsec;
        else if (f_any && !f_sent) cx_w[31:0] <= {24'd0, f_code};
        if (e_done_b) cx_w[63:32] <= {8'h01, 8'd0, (MUT == 2) ? e_tag + 8'd1 : e_tag, 8'd0};
        else if (f_any && !f_sent) cx_w[63:32] <= {8'hFF, 24'd0};
`else
"""+old+"\n`endif"
s=s.replace(old,new)
# Use the already-supported same-edge kept address copies; Gray control stays RTL.
old='ot_link_afifo #(.W(64), .AW(CFA)) u_cx'
assert s.count(old)==1
s=s.replace(old,'ot_link_afifo #(.W(64), .AW(CFA), .RCOPY(24)) u_cx')
s += """
`ifdef OT_ENG_N32
(* keep_hierarchy *)
module qkc_ingest_take_copy(input wire a,b,c,output wire y);
    (* keep *) AND3x1_ASAP7_75t_R u_cell (.A(a), .B(b), .C(c), .Y(y));
endmodule
`endif
"""
a.out.write_text(s)
print('PRIVATE_HYBRID_SHELL_PROPOSAL',a.out)
