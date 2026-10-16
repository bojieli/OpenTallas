`timescale 1ns/1ps
// Actual compact E-side HOST control projection from dsfd_host_c.
// Source-only successor: physical clock/pin/die qualification remains OPEN.
module dsfd_host_c_ectl #(parameter integer NS = 1, KVS = 1, ENG = -1, MUT = 0, PWD = 16) (
    input  wire          ck,
    input  wire          rst,

    input wire ck_boot, // real die-delivered300MHz initialization root:4ck=3ckv

    input  wire          ckv,
    input  wire          rsv,

    input  wire [514:0]        f_collective,
    output wire [76:0]         t_collective,
    input  wire [4*NS-1:0]     f_lf,

    output reg  [35:0]         t_sseq_pw,

    input wire ck_return, // phase-equivalent independently compensated return latch root
    output reg [35:0] t_pq_pw, // CSR 0x12: same PW36 packing, routed to fixed PQ boot mailbox

    output reg  [7:0]          t_sseq_plen,
    input  wire [5:0]          f_sseq_st,
    input  wire [3:0]          f_wfc_ft,
    output wire [36*NS-1:0] hw_control,
    output wire [514:0] native_host_word,
    output wire native_tcr,
    input wire [3:0] data_fault,
    input wire native_tv, native_fault,
    input wire [63:0] native_td,
    input wire native_ov, native_owe,
    input wire [31:0] native_oa,
    input wire [1:0] native_marker,
    output wire native_ocr,
    output wire [7:0] native_ack,
    input  wire [9*NS-1:0]     hc
);
    reg [1:0] rq, rvq;
    always @(posedge ck or negedge rst) if (!rst) rq <= 2'b00; else rq <= {rq[0], 1'b1};
    always @(posedge ckv or negedge rsv) if (!rsv) rvq <= 2'b00; else rvq <= {rvq[0], 1'b1};
    wire rn = rq[1], rvn = rvq[1];

    // Each raw assertion flushes both boot FIFO interfaces; each release is
    // conditioned only by its own clock. Never drive cross-root reset pins
    // from another root's conditioned reset.
    wire pwrn,pwrrn;
    ot_reset_sync pw_wrs(.clk(ck),.async_rst_n(rst&&rsv),.sync_rst_n(pwrn));
    ot_reset_sync pw_rrs(.clk(ckv),.async_rst_n(rst&&rsv),.sync_rst_n(pwrrn));

    // ---------------- input pin flops
    reg [515:0] fi;

    always @(posedge ck) fi <= rn ? {1'b0, f_collective} : 516'd0;
    reg tcr_l;                           // local completion-credit return: one edge after each completion leaves
    wire        hv = fi[0], tcr = tcr_l;

    wire [511:0] hd = fi[512:1];
    wire [1:0]  hcl = fi[514:513];
    wire csr_p = hv && hcl == 2'd0 && hd[7:0] == 8'h10;
    wire csr_l = hv && hcl == 2'd0 && hd[7:0] == 8'h11;
    
    wire csr_pq = hv && hcl == 2'd0 && hd[7:0] == 8'h12;

    localparam PWW=37; // {kind2, data35}:0stage,1PQ,2length

    wire to_ing = hv && !csr_p && !csr_l && !csr_pq;
    // ---------------- ingest (single stream clock on a layer die: clk_h = clk_i = ck)
    wire [4:0] crn=0; wire t_v=native_tv; wire [63:0] t_d=native_td;
    wire hf=native_fault;wire sf;
    assign native_host_word={hcl,hd,hv};
    assign native_tcr=tcr;
    wire pw_wr, pw_v, pw_ovf, pw_unf, pw_take; wire [PWW-1:0] pw_d;
    reg [1:0] pace;

    reg [65:0] ret_seam;
    always @* if (!ck_return) ret_seam={hf,t_v,t_d};
    wire hf_core=ret_seam[65],tv_core=ret_seam[64];
    wire [63:0] td_core=ret_seam[63:0];

    dsfd_host_sd_control #(.NS(NS),.KVS(KVS),.ENG(ENG)) sd_control(
      .ck(ck),.rst_n(rst),.o_v(native_ov),.o_we(native_owe),.o_addr(native_oa),
      .marker_class(native_marker),.hc(hc),.hw_control(hw_control),
      .o_cr(native_ocr),.host_ack_n(native_ack),.fault(sf));
    // ---------------- intercepted CSR words: program -> ckv FIFO, length register; their receive credit returned here:
    // a length word's at once, a program word's when it LEAVES the crossing FIFO on ckv (pop toggle, synchronised), so
    // the sender's credit window (<= PWD words) bounds the FIFO: it never overflows

    // Static layer host has no credit return. Do not synthesize a dormant
    // serial->core pop-toggle counter solely to feed a false overflow alarm.
    wire [6:0]crn_x=0;wire[5:0]crn_sum=0;
    reg pop_t;

    wire boot_rn;
    ot_reset_sync boot_rs(.clk(ck_boot),.async_rst_n(rst&&rsv),.sync_rst_n(boot_rn));
    wire bridge_v,bridge_ready,up_ov,up_un,down_ov;
    wire[PWW-1:0]bridge_d;
    wire boot_write=csr_l||((csr_p||csr_pq)&&(MUT!=1));
    wire[PWW-1:0]boot_data=csr_l?{2'd2,27'd0,hd[39:32]}:
      {1'b0,(csr_pq^(MUT==5)),hd[102:96],hd[59:32]};
    ot_async_fifo #(.WIDTH(PWW),.DEPTH(PWD),.EXT_RST(1))u_pw_source(
      .wr_clk(ck),.wr_rst_n(pwrn),.wr_valid(boot_write),.wr_ready(pw_wr),.wr_data(boot_data),.wr_overflow(up_ov),
      .rd_clk(ck_boot),.rd_rst_n(boot_rn),.rd_valid(bridge_v),.rd_ready(1'b1),.rd_data(bridge_d),.rd_underflow(up_un));
    // Every boot edge services the head. Fullness only detects a violated
    // initialization capacity contract; it never reschedules a transfer.
    ot_async_fifo #(.WIDTH(PWW),.DEPTH(PWD),.EXT_RST(1))u_pw(
      .wr_clk(ck_boot),.wr_rst_n(boot_rn),.wr_valid(bridge_v),.wr_ready(bridge_ready),.wr_data(bridge_d),.wr_overflow(down_ov),
      .rd_clk(ckv),.rd_rst_n(pwrrn),.rd_valid(pw_v),.rd_ready(pw_take),.rd_data(pw_d),.rd_underflow(pw_unf));
    reg boot_bad;
    always @(posedge ck_boot or negedge boot_rn)if(!boot_rn)boot_bad<=0;
       else if(bridge_v&&!bridge_ready)boot_bad<=1;
    reg boot_bad_seam;reg[1:0]boot_bad_sync;
    always @*if(!ck_boot)boot_bad_seam=boot_bad;  // plain lockup latch (boot_bad is 0 while boot_rn is low)
    always @(posedge ck or negedge rn)if(!rn)boot_bad_sync<=0;else boot_bad_sync<={boot_bad_sync[0],boot_bad_seam};
    assign pw_ovf=up_ov|boot_bad_sync[1];

    assign pw_take = pw_v && pace == 2'd0;
    always @(posedge ckv or negedge rvn)
        if (!rvn) begin

            t_sseq_plen<=0;

            pace <= 0; t_sseq_pw <= 36'd0;

            t_pq_pw <= 36'd0;

            pop_t <= 1'b0; end
        else begin

            t_pq_pw<=pw_take&&pw_d[36:35]==1?{1'b1,pw_d[34:0]}:36'd0;
            t_sseq_pw<=pw_take&&pw_d[36:35]==0?{1'b1,pw_d[34:0]}:36'd0;
            if(pw_take&&pw_d[36:35]==2)t_sseq_plen<=pw_d[7:0];

            if (pw_take) pop_t <= ~pop_t;
            pace <= pw_take ? 2'd3 : (pace != 0 ? pace - 1'b1 : 2'd0);
        end

    // Fixed diagnostic-status contract: if C0 is the first ck edge that
    // samples the source's declared f_sseq_st status edge, to exports that
    // status at C0+2 ck (ss1 -> ss2 -> to). This is recurring status transport,
    // not a token-success decision. This module has no t_kd/KIT/raw-END input.
    // tv_core/td_core below are native ingest physical-write completions and
    // MUST NOT be interpreted as successful token execution. The actual KIT
    // consumer must evaluate its compiler-declared fault-status edge; it must
    // not wait dynamically for status or declare success from raw END/KIT alone.
    // ---------------- status (ck): sequencer status (ckv, 2-flop), WFC faults, ingest / decode / crossing faults
    reg [5:0] ss1, ss2; reg [3:0] wf;
    always @(posedge ck) begin ss1 <= f_sseq_st; ss2 <= ss1; wf <= f_wfc_ft; end
    reg[3:0] data_fault_q;
    always @(posedge ck)data_fault_q<=data_fault;
    reg xf;
    always @(posedge ck or negedge rn) if (!rn) xf <= 1'b0; else if (pw_ovf || ((csr_p || csr_pq

        || csr_l

    ) && !pw_wr) || crn_x == 7'd127) xf <= 1'b1;

    // lane faults (odd bits of f_lf), pin-registered

    reg [4*NS-1:0] lf_pins;
    always @(posedge ck) lf_pins <= f_lf;

    reg lf_q; integer li;
    always @(posedge ck or negedge rn)
        if (!rn) lf_q <= 1'b0;
        else begin : lfo
            reg a; a = 1'b0;
            for (li = 0; li < 2 * NS; li = li + 1) a = a | lf_pins[2 * li + 1];
            lf_q <= a && (MUT != 4);
        end
    always @(posedge ck or negedge rn) if (!rn) tcr_l <= 1'b0; else tcr_l <= tv_core;
    reg [76:0] to;
    always @(posedge ck) to <= rn ? {1'b1, hf_core | sf | xf | (|data_fault_q) | lf_q | ss2[5] | (|wf), wf, ss2, tv_core && (MUT != 3), td_core} : 77'd0;
    assign t_collective = to;

endmodule

// Real native ROWS/IKEY/RAW ingest plus physical-write visibility fence.
// The launch/host/core/write clocks are separate physical pins of the fixed
// source family. Source-clock lockups stay INSIDE this leaf; no unregistered
// host-word arithmetic is exposed on the parent boundary.
module dsfd_host_native_leaf(
 input wire ck_launch,ck_host,ck_core,ck_write,rst_n,
 input wire[514:0]host_word,input wire t_cr,input wire o_cr,
 input wire[7:0]host_ack_n,
 output wire o_v,o_we,output wire[31:0]o_addr,output wire[255:0]o_d,
 output wire t_v,output wire[63:0]t_d,output reg fault);
 wire hv=host_word[0];wire[1:0]hcl=host_word[514:513];wire[511:0]hd=host_word[512:1];
 wire csr=hv&&hcl==0&&(hd[7:0]==8'h10||hd[7:0]==8'h11||hd[7:0]==8'h12);
 reg[514:0]host_seam;reg tcr_seam;
 always @*if(!ck_launch)begin host_seam={hcl,hd,hv&&!csr};tcr_seam=t_cr;end
 wire hf;wire[4:0]unused_cr;wire rn_h;
 ot_reset_sync rs_h(.clk(ck_host),.async_rst_n(rst_n),.sync_rst_n(rn_h));
 // Physical commit-ACK input boundary: sampled on ck_write, then counted
 // by the native visibility fence on the next ck_write edge (+1). This
 // stage cannot defer/merge an ACK or reschedule a payload. Local reset
 // release uses only this root. Compiler commit visibility includes it.
 wire rn_ack; reg [7:0] ack_pin;
 ot_reset_sync rs_ack(.clk(ck_write),.async_rst_n(rst_n),.sync_rst_n(rn_ack));
 always @(posedge ck_write or negedge rn_ack) if(!rn_ack)ack_pin<=0;else ack_pin<=host_ack_n;
 dsfd_host_native #(.ENABLE(1),.FPIPE(2),.ENG_TRIM(1),.APIPE(3))native_ingest(
  .rst_n(rst_n),.clk_h(ck_host),.h_v(host_seam[0]),.h_cls(host_seam[514:513]),
  .h_d(host_seam[512:1]),.h_crn(unused_cr),.t_v(t_v),.t_d(t_d),.t_cr(tcr_seam),
  .clk_i(ck_core),.ck(ck_write),.o_v(o_v),.o_we(o_we),.o_addr(o_addr),.o_d(o_d),
  .o_cr(o_cr),.i_rv(1'b0),.i_rd(256'd0),.host_ack_n(ack_pin),.fault(hf));
 // Native fault OR is hardened behind a source pin FF. +1 host diagnostic
 // edge is explicit; native payload/ACK completion edges are unchanged.
 always @(posedge ck_host or negedge rn_h)if(!rn_h)fault<=0;else fault<=hf;
endmodule

// Structural initialization-ingress successor. This parent contains only wires and real
// hardened-leaf instances. Every clock is an actual independent die input,
// delivered at phi-R for that child's own measured insertion. There is no
// reference result producer. STATIC1 sector service removes credit deferral,
// but queue-nonempty service does NOT establish normal-token reservations or
// native throughput. Production normal emit/commit calendar binding is OPEN.
// Global defines for its shared FIFO implementations:
// DSFD_HOST_C_STATIC, DSFD_HOST_PQ_BOOT, OT_S81_HOST_PHASESAFE, OT_S81_HOST_BOOT300.
module dsfd_host_c_sliced #(
 parameter integer NS=1,KVS=1,ENG=-1,MUT=0,PWD=16
)(input wire ck,ckv,ck_boot,ck_return,ck_launch,ck_native,
 input wire[1:0]ck_ingest,input wire[3:0]ck_data,
 input wire rst,rsv,input wire[514:0]f_collective,input wire[4*NS-1:0]f_lf,
 output wire[76:0]t_collective,output wire[35:0]t_sseq_pw,t_pq_pw,
 output wire[7:0]t_sseq_plen,input wire[5:0]f_sseq_st,input wire[3:0]f_wfc_ft,
 output wire[292*NS-1:0]hw,input wire[9*NS-1:0]hc);
 wire[514:0]host_word;wire tcr,tv,nf,ov,owe,ocr;wire[63:0]td;
 wire[31:0]oa;wire[255:0]od_native;wire[255:0]od=(MUT==6)?od_native^256'h100:od_native;wire[7:0]ack;
 wire[36*NS-1:0]ctrl;wire[NS-1:0]hc_cr;wire[3:0]df;
 wire[76:0]control_to;
 dsfd_host_c_ectl #(.NS(NS),.KVS(KVS),.ENG(ENG),.MUT(MUT),.PWD(PWD))control(
  .ck(ck),.ckv(ckv),.ck_boot(ck_boot),.ck_return(ck_return),.rst(rst),.rsv(rsv),
  .f_collective(f_collective),.t_collective(control_to),.f_lf(f_lf),
  .t_sseq_pw(t_sseq_pw),.t_pq_pw(t_pq_pw),.t_sseq_plen(t_sseq_plen),
  .f_sseq_st(f_sseq_st),.f_wfc_ft(f_wfc_ft),.hc(hc),.hw_control(ctrl),
  .native_host_word(host_word),.native_tcr(tcr),.native_tv(tv),.native_td(td),
  .data_fault(df),.native_fault(nf),.native_ov(ov),.native_owe(owe),.native_oa(oa),
  .native_marker(od[65:64]),.native_ocr(ocr),.native_ack(ack));
 dsfd_host_native_leaf ingest(
  .ck_launch(ck_launch),.ck_host(ck_ingest[0]),.ck_core(ck_ingest[1]),
  .ck_write(ck_native),.rst_n(rst),.host_word(host_word),.t_cr(tcr),.o_cr(ocr),
  .host_ack_n(ack),.o_v(ov),.o_we(owe),.o_addr(oa),.o_d(od_native),
  .t_v(tv),.t_d(td),.fault(nf));
 for(genvar s=0;s<NS;s=s+1)begin:g_rebuild
  assign hc_cr[s]=hc[9*s];
  assign hw[292*s+257+:35]=ctrl[36*s+1+:35];
 end
 for(genvar k=0;k<4;k=k+1)begin:g_data
  wire[64*NS-1:0]data;wire[NS-1:0]valid;
  dsfd_host_sd_data64 #(.NS(NS),.KVS(KVS),.ENG(ENG),.SLICE(k))leaf(
   .ck(ck_data[k]),.rst_n(rst),.o_v(ov),.o_we(owe),.o_addr(oa),
   .o_d(od[64*k+:64]),.marker_class(od[65:64]),.hc_cr(hc_cr),
   .hw_data(data),.hw_valid(valid),.fault(df[k]));
  for(genvar s=0;s<NS;s=s+1)begin:g_stack
   assign hw[292*s+1+64*k+:64]=data[64*s+:64];
   if(k==0)assign hw[292*s]=valid[s];
  end
 end
 // Diagnostic leaf-fault reduction is pin-captured and registered inside
 // the actual E control leaf; this parent remains wires-only.
 assign t_collective=control_to;
endmodule
