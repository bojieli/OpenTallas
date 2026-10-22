// Private same-clock COMPONENT join; no public binding activation.
`timescale 1ns/1ps
// Qwen host CONTROL leaf; this is not the complete qkd_host ingest/SerDes master.
// All host request fields are the existing ot_host_if MODE0 -> ot_qfd_pkgctl
// engine interface. No wire opcode or AXI termination is invented here.
// req[60:0], LSB first: eng_start, eng_token18, eng_pos18, eng_kv_base24.
// pr[142:0], LSB first: pw_data64,pw_addr10,pw_v,dw_data64,dw_addr3,dw_v.
// tk[d*93+:93] is exactly the merged sequencer RAW status word, not a packet.
// hc[181:0] is RAW: pos18,token18,gen2,start,pw75,dw68. Broadcast per package.
// res[119:0], LSB first: done,fault,next_token18,next_val32,cycles32,
// {disagree,watchdog,start_unready,die_fault},n_steps32.
// ready,req,pr,tk are captured without input logic; hc/res leave pin flops.
// ND=8 aggregates the TP8 dies. ND=1 is a die-local test/integration option;
// physical wiring of remote die statuses is a required host contract revision.
module qkd_host_ctl_rc #(
    parameter integer ND=8,
    parameter integer WDOG=1<<22,
    parameter integer MUT=0,
    // MU-QWEN-HOST 10-18 (opt-in; 0 = unchanged): 1 = ot_qfd_pkgctl MU (4 steps outstanding, gen = step tag) and the
    // step's user on hc pos[17:16] (user = kv_base / 1024, the host's slot * KVW; positions are < 8192, so pos[17:13]
    // are always zero today).  The 182-bit hc contract keeps its width and fields.
    parameter integer MU=0
)(
    input wire ck, rst_n,
    input wire ready,
    input wire [60:0] req,
    input wire [142:0] pr,
    input wire [ND*93-1:0] tk,
    output wire [181:0] hc,
    output wire package_start_v, output wire [17:0] package_token, package_pos, output wire [1:0] package_gen,
    output reg [119:0] res
);
    reg ready_q;
    reg [60:0] req_q;
    reg [142:0] pr_q;
    reg [ND*93-1:0] tk_q;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin ready_q<=0; req_q<=0; pr_q<=0; tk_q<=0; end
        else begin ready_q<=ready; req_q<=req; pr_q<=pr; tk_q<=tk; end
    wire [ND-1:0] dn,dr,df;
    wire [ND*2-1:0] dg;
    wire [ND*18-1:0] nt;
    wire [ND*32-1:0] nv;
    for(genvar d=0;d<ND;d=d+1) begin:g_tk
        assign dn[d]=tk_q[d*93+92];
        assign dg[d*2+:2]=tk_q[d*93+90+:2];
        assign dr[d]=tk_q[d*93+89];
        assign df[d]=tk_q[d*93+88];
        assign nt[d*18+:18]=tk_q[d*93+64+:18];
        assign nv[d*32+:32]=tk_q[d*93+32+:32];
    end
    wire done,fault,start,disagree,wdog,unready,die_fault;
    wire [17:0] token,pos,next_token;
    wire [23:0] kv_base;
    wire [1:0] gen;
    wire [31:0] next_val,cycles,n_steps;
    ot_qfd_pkgctl #(.D(ND),.WDOG(WDOG),.DONE_REG(1),.MU(MU)) u_pkg(
        .clk(ck),.rst_n(rst_n),.ready(ready_q),
        .eng_start(req_q[0]),.eng_token(req_q[18:1]),.eng_pos(req_q[36:19]),.eng_kv_base(req_q[60:37]),
        .eng_done(done),.eng_next_token(next_token),.eng_next_val(next_val),.eng_cycles(cycles),.eng_fault(fault),
        .d_start(start),.d_token(token),.d_pos(pos),.d_kv_base(kv_base),.d_gen(gen),
        .d_done(dn),.d_done_gen(dg),.d_next_token(nt),.d_next_val(nv),.d_drained(dr),.d_fault(df),
        .disagree(disagree),.wdog_fault(wdog),.start_unready(unready),.die_fault(die_fault),.n_steps(n_steps));
    // kv_base is the pkgctl engine field, not part of the raw dctl interface.
    // The immutable KV map is the merged sequencer's existing implementation.
    wire [17:0] hc_pos = (MU!=0) ? {kv_base[11:10],pos[15:0]} : pos;
    assign hc={pr_q,start,gen,token ^ ((MUT!=0 && start)?18'd1:18'd0),hc_pos};
    assign package_start_v=hc[38];
    assign package_token=hc[35:18]; assign package_pos=hc[17:0]; assign package_gen=hc[37:36];
    always @(posedge ck or negedge rst_n)
        if (!rst_n) res<=0;
        else res<={n_steps,die_fault,unready,wdog,disagree,cycles,next_val,next_token,fault,done};
endmodule
