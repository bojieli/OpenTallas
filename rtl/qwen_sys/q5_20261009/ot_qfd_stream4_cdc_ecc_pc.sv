`timescale 1ns/1ps
// Additive source-matched native CDC successor. No PHY/storage-free claim.
module ot_qfd_stream4_cdc_ecc_pc #(
    parameter integer ENABLE = 0, INTERLEAVED = 1, TAGW = 9,
    parameter integer LD   = 64,            // landing depth, power of two
    parameter integer WB   = 16,            // write-queue depth, power of two
    parameter integer AD   = 64,            // write-done depth, power of two
    parameter integer SYNC = 2,             // synchronizer flops per crossing
    // r8 (default 0 = r6/r7 structure): RSEL 1 = every landing read column group owns a one-hot select
    // register in its own kept hierarchy (ot_hdc_v41x_kreg), loaded with decode(next read index): the
    // r7 routes showed yosys merging the r3 (* keep *) index copies back into lr_bin (one driver, a
    // 9/14/30/31 buffer tree into the 64:1 mux, SS -1.1..-49.9 ps).  RNG = column groups when RSEL = 1.
    parameter integer RSEL = 0,
    parameter integer RNG  = 10,
    // MARGIN 1 (owner margin rule 2026-10-06; default 0 = the structure above, unchanged): every data input is
    // registered at its pin (w_* in CLK, h_l* / h_a* in HCLK: one cycle of latency, flow control unchanged: w_room
    // keeps one more slot in flight), and the landing is CREDIT-based: l_pop is a registered credit return (one per
    // word the receiver consumed), l_v is a one-cycle push of the word on l_* (the receiver queues it), at most LCRED
    // words outstanding.  No input reaches a register enable or a mux select inside the element.
    parameter integer MARGIN = 0,
    parameter integer LCRED = 6
) (
    // ---- CLK (core) domain ----
    input  wire             clk,
    input  wire             c_arst_n,
    output wire              l_v,
    output wire  [16:0]      l_sec,           // driven by the group registers l_q
    output wire  [7:0]       l_row,
    output wire  [255:0]     l_data,
    input  wire             l_pop,
    input  wire             w_v,
    input  wire [23:0]      w_sec,
    input  wire [255:0]     w_data,
    input  wire [TAGW-1:0]  w_tag,
    output wire              w_room,
    output wire              wd_v,
    output wire  [TAGW-1:0]  wd_tag,
    output wire              c_fault,        // write pushed into a full queue
    // ---- HCLK (controller) domain ----
    input  wire             hclk,
    input  wire             h_arst_n,
    input  wire             h_lv,           // landing push (a returned RD beat)
    input  wire [16:0]      h_lsec,
    input  wire [7:0]       h_lrow,
    input  wire [287:0]     h_lcode,
    output wire  [2:0]       h_cred,         // landing slots freed since the previous HCLK edge
    output wire              h_wv,           // write-queue head (hand-off pointer) valid
    output wire  [23:0]      h_wsec,         // its sector
    input  wire             h_hand,         // head handed to the access queue (h_wv && wr_r)
    input  wire             h_wcon,         // WR column command consumes the completion entry
    output wire              h_cv,           // captured completion entry (one edge after h_wcon)
    output wire  [23:0]      h_csec,
    output wire  [255:0]     h_cdata,
    output wire  [TAGW-1:0]  h_ctag,
    input  wire             h_av,           // write-done push
    input  wire [TAGW-1:0]  h_atag,
    output wire              h_fault,
    output wire h_ecc_fault,output wire [31:0] h_ce_count // landing / write-done push into a full FIFO, or WR with empty queue
);
    wire decoded_v,ce,ue,ecc_fault,cdc_h_fault;
    wire [255:0] decoded_data;wire [16:0] decoded_sec;wire [7:0] decoded_row;
    ot_qfd_kv_landing_ecc #(.ENABLE(ENABLE),.INTERLEAVED(INTERLEAVED)) landing(
     .hclk(hclk),.h_rst_n(h_arst_n),.i_v(h_lv),.i_code(h_lcode),.i_sec(h_lsec),.i_row(h_lrow),
     .o_v(decoded_v),.o_data(decoded_data),.o_sec(decoded_sec),.o_row(decoded_row),
     .ce(ce),.ue(ue),.fault(ecc_fault),.ce_count(h_ce_count));
    assign h_ecc_fault=ecc_fault;
    assign h_fault=cdc_h_fault||ecc_fault;
    (* async_reg="true" *) reg ef1,ef2;
    always @(posedge clk or negedge c_arst_n)
     if(!c_arst_n)begin ef1<=0;ef2<=0;end else begin ef1<=ecc_fault;ef2<=ef1;end
    wire cv,cf;wire [2:0] credit;
    assign l_v=cv&&!ef2;
    assign c_fault=cf||ef2;
    // A quarantined UE is never successful retirement. Keep the controller
    // stopped once faulted, including already synchronized credit returns.
    assign h_cred=ecc_fault?3'b0:credit;
    ot_qwen_stream4_cdc_pc #(.TAGW(TAGW),.LD(LD),.WB(WB),.AD(AD),.SYNC(SYNC),.RSEL(RSEL),.RNG(RNG),.MARGIN(MARGIN)) cdc(
     .clk(clk),.c_arst_n(c_arst_n),.l_v(cv),.l_sec(l_sec),.l_row(l_row),.l_data(l_data),.l_pop(l_pop&&!ef2),
     .w_v((ENABLE!=0)&&w_v&&!ef2),.w_sec(w_sec),.w_data(w_data),.w_tag(w_tag),.w_room(w_room),.wd_v(wd_v),.wd_tag(wd_tag),.c_fault(cf),
     .hclk(hclk),.h_arst_n(h_arst_n),.h_lv(decoded_v),.h_lsec(decoded_sec),.h_lrow(decoded_row),.h_ldata(decoded_data),.h_cred(credit),
     .h_wv(h_wv),.h_wsec(h_wsec),.h_hand(h_hand),.h_wcon(h_wcon),.h_cv(h_cv),.h_csec(h_csec),.h_cdata(h_cdata),.h_ctag(h_ctag),
     .h_av(h_av),.h_atag(h_atag),.h_fault(cdc_h_fault));
endmodule
