#!/usr/bin/env python3
"""Deterministic additive H1 local-TX variant; pinned originals never modified."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / 'rtl/qwen_sys/emb_hbm_20261008'

def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)

def generate():
    original = (RTL / 'ot_qwen_die_hub_emb.sv').read_text()
    text = original[:original.index('// Routed top of qfd_hub_emb:')]
    text = text[text.index('module ot_qwen_die_hub_emb #('):]
    text = replace_once(text, 'module ot_qwen_die_hub_emb #(', 'module ot_qwen_die_hub_emb_integrated_impl #(')
    text = replace_once(text, '    output wire              x3_cr,', '''    output wire              x3_cr,
    input wire host_v, host_we,
    input wire [31:0] host_addr,
    input wire [255:0] host_d,
    output wire host_boot_credit, host_boot_accept, host_runtime_v, merge_fault,''')
    start = text.index('    // ---- transmit side:')
    end = text.index('    // ---- embedding gateway', start)
    text = text[:start] + '''    // H1: only this local TX section changes. Separate queue identity owns
    // class and credit; every SU outer tag bit remains transaction data.
    reg xv_q; reg [511:0] xd_q; reg [10:0] xt_q;
    reg hv_q; reg [511:0] hd_q; reg [10:0] ht_q;
    wire host_end = host_addr == 32'hffffffff;
    wire host_bad = host_v && host_addr[31] &&
        (!host_we || (!host_end && (host_addr[30:25] != 0 || host_addr[24:0] >= E_END)));
    wire host_qualified = host_v && host_we && host_addr[31] && !host_bad;
    wire [511:0] host_packet = host_end ? {448'b0,host_d[63:0]} : {231'b0,host_d,host_addr[24:0]};
    wire [10:0] host_tag = host_end ? 11'h600 : 11'h500;
    assign host_runtime_v = host_v && !host_addr[31];
    assign host_boot_accept = hv_q;
    always @(posedge ck) begin
        xd_q <= x3_d; xt_q <= x3_tag;
        hd_q <= host_packet; ht_q <= host_tag;
    end
    always @(posedge ck or negedge rn)
        if (!rn) begin xv_q <= 0; hv_q <= 0; end
        else begin xv_q <= x3_v && !merge_fault && !flow_bad; hv_q <= host_qualified && !merge_fault && !flow_bad; end
    reg [511:0] sd [0:XS-1]; reg [10:0] st [0:XS-1]; reg [1:0] sdst [0:XS-1]; reg sbc [0:XS-1];
    reg [511:0] hd [0:XS-1]; reg [10:0] ht [0:XS-1]; reg [1:0] hdst [0:XS-1]; reg hbc [0:XS-1];
    reg [XA:0] sw, sr, hw, hr;
    wire sne = sw != sr;
    wire hne = hw != hr;
    wire choose_host = !sne && hne;
    wire [XA:0] scount = sw-sr;
    wire [XA:0] hcount = hw-hr;
    reg [CW-1:0] lc [0:NL-1]; reg [3:0] lseen [0:NL-1];
    reg [NL*LW-1:0] lo_q;
    reg xcr_q, hcr_q, ovf, hovf, lco;
    wire [511:0] shd = choose_host ? hd[hr[XA-1:0]] : sd[sr[XA-1:0]];
    wire [10:0] sht = choose_host ? ht[hr[XA-1:0]] : st[sr[XA-1:0]];
    wire semb = choose_host;
    wire [1:0] dst = choose_host ? hdst[hr[XA-1:0]] : sdst[sr[XA-1:0]];
    wire sbcw = choose_host ? hbc[hr[XA-1:0]] : sbc[sr[XA-1:0]];
    wire g_v; wire [10:0] g_tag; wire [511:0] g_d;
    reg [NL-1:0] lcnz;
    always @(*) for (i=0;i<NL;i=i+1) lcnz[i] = lc[i] != 0;
    wire gsend = g_v && (&lcnz);
    wire send_pre = !gsend && (sne || hne) && (sbcw ? (&lcnz) : lcnz[dst]);
    // Include pin-pending reservations. No hidden ninth slot or speculative credit.
    wire [XA+2:0] soccupancy = {2'b0,scount} + xv_q;
    wire [XA+2:0] hoccupancy = {2'b0,hcount} + hv_q;
    wire [XA+2:0] snext = soccupancy + x3_v - (send_pre && !choose_host);
    wire [XA+2:0] hnext = hoccupancy + host_qualified - (send_pre && choose_host);
    wire su_bad = scount > XS || soccupancy > XS || snext > XS;
    wire host_flow_bad = hcount > XS || hoccupancy > XS || hnext > XS || host_bad;
    wire flow_bad = su_bad || host_flow_bad;
    assign merge_fault = ovf || hovf;
    wire send = send_pre && !merge_fault && !flow_bad;
    wire bend_v = send && choose_host && sbcw;
    function [3:0] g2b(input [3:0] g); g2b = {g[3],g[3]^g[2],g[3]^g[2]^g[1],g[3]^g[2]^g[1]^g[0]}; endfunction
    reg [CW-1:0] lc_n [0:NL-1]; reg [3:0] dlt;
    always @(*) for (i=0;i<NL;i=i+1) begin
        dlt = g2b(rcnt[i])-g2b(lseen[i]);
        lc_n[i] = lc[i] - (((send && (sbcw || dst == i)) || gsend) ? {{(CW-1){1'b0}},1'b1} : {CW{1'b0}}) + {{(CW-4){1'b0}},dlt};
    end
    always @(posedge ck) if (!merge_fault && !flow_bad) begin
        if (xv_q) begin
            sd[sw[XA-1:0]] <= xd_q; st[sw[XA-1:0]] <= xt_q;
            sdst[sw[XA-1:0]] <= xd_q[511:510]; sbc[sw[XA-1:0]] <= 0;
        end
        if (hv_q) begin
            hd[hw[XA-1:0]] <= hd_q; ht[hw[XA-1:0]] <= ht_q;
            hdst[hw[XA-1:0]] <= stack_of(hd_q[24:0]); hbc[hw[XA-1:0]] <= ht_q[9:8] == K_BOOT_END;
        end
    end
    always @(posedge ck or negedge rn)
        if (!rn) begin
            sw<=0;sr<=0;hw<=0;hr<=0;xcr_q<=0;hcr_q<=0;ovf<=0;hovf<=0;lco<=0;lo_q<=0;
            for (i=0;i<NL;i=i+1) begin lc[i]<=CR[CW-1:0];lseen[i]<=0;end
        end else begin
            if (su_bad) ovf<=1;
            if (host_flow_bad) hovf<=1;
            if (!merge_fault && !flow_bad) begin
                if (xv_q) sw<=sw+1'b1;
                if (hv_q) hw<=hw+1'b1;
                if (send && !choose_host) sr<=sr+1'b1;
                if (send && choose_host) hr<=hr+1'b1;
            end
            xcr_q <= send && !choose_host;
            hcr_q <= send && choose_host;
            for (i=0;i<NL;i=i+1) begin
                lc[i]<=lc_n[i];if(lc_n[i]>CR[CW-1:0])lco<=1;
                lseen[i]<=rcnt[i];
                lo_q[i*LW+:LW] <= gsend ? {g_d,g_tag,rcg[i],1'b1} :
                    (send && (sbcw || dst==i)) ? {semb ? shd : {shd[509:0],2'b00},sht,rcg[i],1'b1} :
                    {512'd0,11'd0,rcg[i],1'b0};
            end
        end
    assign l_o = lo_q;
    assign x3_cr = xcr_q;
    assign host_boot_credit = hcr_q;
''' + text[end:]
    text = replace_once(text, '(|wf2), ovf}', '(|wf2), (ovf || hovf)}')
    text = '`timescale 1ns/1ps\n// Generated by tools/emb_hbm_integrated_hub_sources.py. H1 TX-only variant.\n// Receive still uses historical tag[10] class: high-seq KV RX/package binding OPEN.\n' + text
    (RTL/'ot_qwen_die_hub_emb_integrated_impl.sv').write_text(text)
    top = (RTL/'ot_qwen_die_hub_emb_boot_top.sv').read_text()
    top = top[:top.index('    wire mx_v')]
    top = top.replace('ot_qwen_die_hub_emb_boot_top', 'ot_qwen_die_hub_emb_integrated_top')
    common = '''(.ck(ck), .rst_n(rst_n), .fck({fck3,fck2,fck1,fck0}),
        .l_i({l3_i,l2_i,l1_i,l0_i}), .l_o({l3_o,l2_o,l1_o,l0_o}),
        .x3_v(x3_v), .x3_d(x3_d), .x3_tag(x3_tag), .x3_cr(x3_cr),
        .ar_v(ar_v), .ar_d(ar_d), .ar_cr(ar_cr), .fault(fault), .fault_cause(fault_cause),
        .ea_v(ea_v), .ea_kind(ea_kind), .ea_addr(ea_addr), .ea_cr(ea_cr),
        .eq_v(eq_v), .eq_d(eq_d), .emb_ready(emb_ready), .emb_fault(emb_fault), .emb_fault_code(emb_fault_code)'''
    params = '#(.NL(4),.LW(528),.CR(CR),.OD(OD),.XS(XS),.ARC(ARC),.RQD(RQD),.MUT(MUT))'
    top += '    generate if (BOOT_MERGE != 0) begin: enabled\n'
    top += '    ot_qwen_die_hub_emb_integrated_impl '+params+' u '+common+',\n'
    top += '''        .host_v(host_v),.host_we(host_we),.host_addr(host_addr),.host_d(host_d),
        .host_boot_credit(host_boot_credit),.host_boot_accept(host_boot_accept),.host_runtime_v(host_runtime_v),.merge_fault(merge_fault));
    end else begin: disabled
'''
    top += '    ot_qwen_die_hub_emb '+params+' u '+common+');\n'
    top += '''    assign host_boot_credit=0;assign host_boot_accept=0;assign merge_fault=0;
    assign host_runtime_v=host_v && !host_addr[31];
    end endgenerate
endmodule
'''
    (RTL/'ot_qwen_die_hub_emb_integrated_top.sv').write_text(top)

if __name__ == '__main__':
    generate()
