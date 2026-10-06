// Opt-in structural successor: one identical hard lane, replicated64.
// bank_id is a parent constant strap, stable for the lifetime of SRAM contents.
// Existing encoder, protection, capture registers and latency are unchanged.
`timescale 1ns/1ps
// Full TP4 head-rank LG staging: 32,320 FP32 logits, G4 W16.
// One protected macro per independently masked lane; no warm-lane overwrite.
// Requests are bank-aligned words relative to LG_BASE_WORD, with row bounds.
// Macro -> raw-codeword register -> corrected/identity-checked data register.
// This adds two return cycles, or three with default-off PROTECT_SPLIT.
// SECDED applies to mutable SRAM only.
module ot_hdc_v41_fh_sram_return_hardened #(
    parameter integer W=16,G=4,AW=24,ROWS=505,PROTECT_SPLIT=1,
    // ADDR_PIPE (default 0; margin-first 2): request distribution registers between the group
    // request decode and each lane's macro pins: one per-group stage, one kept per-lane stage at the
    // lane. Reads and writes are delayed alike (order preserved); address faults keep their cycle.
    // Read return latency grows by ADDR_PIPE (the head's RETURN_EXTRA = 2 + PROTECT_SPLIT + ADDR_PIPE).
    parameter integer ADDR_PIPE=0,
    parameter [AW-1:0] LG_BASE_WORD=0
)(
    input wire clk,rst_n,
    input wire [G-1:0] rd_en,
    input wire [G*AW-1:0] rd_addr,
    output wire [G*W*32-1:0] rd_data,
    output wire [G*W-1:0] rd_valid, corrected, poisoned,
    input wire [G-1:0] wr_en,
    input wire [G*AW-1:0] wr_addr,
    input wire [G*W-1:0] wr_mask,
    input wire [G*W*32-1:0] wr_data,
    output wire [G*W-1:0] wr_committed,
    output wire fault,
    output wire [G-1:0] address_fault_bits
);
    localparam integer LG=$clog2(G);
    wire [G-1:0] read_ok,write_ok;
    wire [G*9-1:0] read_row,write_row;
    reg [G-1:0] address_fault;
    for(genvar g=0;g<G;g=g+1) begin : g_address
        wire [AW-1:0] ra=rd_addr[g*AW+:AW]-LG_BASE_WORD;
        wire [AW-1:0] wa=wr_addr[g*AW+:AW]-LG_BASE_WORD;
        assign read_ok[g]=rd_en[g] && rd_addr[g*AW+:AW]>=LG_BASE_WORD &&
            ra[LG-1:0]==g && (ra>>LG)<ROWS;
        assign write_ok[g]=wr_en[g] && wr_addr[g*AW+:AW]>=LG_BASE_WORD &&
            wa[LG-1:0]==g && (wa>>LG)<ROWS;
        assign read_row[g*9+:9]=9'(ra>>LG);
        assign write_row[g*9+:9]=9'(wa>>LG);
        always @(posedge clk or negedge rst_n)
            if(!rst_n) address_fault[g]<=0;
            else if((rd_en[g]&&!read_ok[g])||(wr_en[g]&&!write_ok[g])) address_fault[g]<=1;
    end
    // request seen by each lane (ADDR_PIPE=0: the group decode directly, as before)
    wire [G*W-1:0] l_read_ok,l_write_ok;
    wire [G*W*9-1:0] l_read_row,l_write_row;
    wire [G*W*32-1:0] l_wr_data;
    generate if(ADDR_PIPE==0) begin : g_direct
        for(genvar b=0;b<G*W;b=b+1) begin : g_l
            assign l_read_ok[b]=read_ok[b/W]; assign l_read_row[9*b+:9]=read_row[9*(b/W)+:9];
            assign l_write_ok[b]=write_ok[b/W]&&wr_mask[b]; assign l_write_row[9*b+:9]=write_row[9*(b/W)+:9];
            assign l_wr_data[32*b+:32]=wr_data[32*b+:32];
        end
    end else begin : g_pipe
`ifndef SYNTHESIS
        initial if(ADDR_PIPE!=2) $fatal(1,"ADDR_PIPE must be 0 or 2");
`endif
        // stage 1: group request registers (+ per-lane write mask/data)
        reg [G-1:0] g_rok,g_wok; reg [G*9-1:0] g_rrow,g_wrow;
        reg [G*W-1:0] s_wmask; reg [G*W*32-1:0] s_wdata;
        always @(posedge clk or negedge rst_n)
            if(!rst_n) begin g_rok<=0; g_wok<=0; end
            else begin g_rok<=read_ok; g_wok<=write_ok; end
        always @(posedge clk) begin g_rrow<=read_row; g_wrow<=write_row; s_wmask<=wr_mask; s_wdata<=wr_data; end
        // stage 2: one kept request register per lane, placed at the lane's macro pins
        for(genvar b=0;b<G*W;b=b+1) begin : g_l
            localparam integer GR=b/W;
            ot_hdc_v41_fh_lane_req u_req (.clk(clk),.rst_n(rst_n),
                .read_ok_d(g_rok[GR]),.read_row_d(g_rrow[9*GR+:9]),
                .write_ok_d(g_wok[GR]&&s_wmask[b]),.write_row_d(g_wrow[9*GR+:9]),.wr_data_d(s_wdata[32*b+:32]),
                .read_ok(l_read_ok[b]),.read_row(l_read_row[9*b+:9]),
                .write_ok(l_write_ok[b]),.write_row(l_write_row[9*b+:9]),.wr_data(l_wr_data[32*b+:32]));
        end
    end endgenerate
    for(genvar b=0;b<G*W;b=b+1) begin : g_bank
        ot_hdc_v41_fh_sram_lane_hardened u_lane (
            .bank_id(6'(b)),
            .clk(clk),.rst_n(rst_n),.read_ok(l_read_ok[b]),.read_row(l_read_row[9*b+:9]),
            .write_ok(l_write_ok[b]),.write_row(l_write_row[9*b+:9]),.wr_data(l_wr_data[32*b+:32]),
            .rd_data(rd_data[32*b+:32]),.rd_valid(rd_valid[b]),.corrected(corrected[b]),
            .poisoned(poisoned[b]),.wr_committed(wr_committed[b]));
    end
    assign address_fault_bits=address_fault;
    assign fault=(|address_fault)||(|poisoned);
`ifndef SYNTHESIS
    initial if(G!=4||W!=16||ROWS>512||ROWS<1||PROTECT_SPLIT!=1) $fatal(1,"G4W16/512-row geometry required");
`endif
endmodule

(* keep_hierarchy *)
module ot_hdc_v41_fh_sram_lane_hardened(
    input wire [5:0] bank_id,
    input wire clk,rst_n,read_ok,write_ok,
    input wire [8:0] read_row,write_row,
    input wire [31:0] wr_data,
    output wire [31:0] rd_data,
    output wire rd_valid,corrected,poisoned,wr_committed
);
        // Fixed hard-macro interface: no parameter specialization at insertion.
        localparam integer PROTECT_SPLIT=1;
        // Capture the incoming write transaction before protection encoding.
        reg [31:0] write_payload_r;
        reg [8:0] write_row_r,write_row_encoded_r;
        reg write_v_r,write_encoded_v_r;
        reg [54:0] encoded_r;
        wire [47:0] identity_payload={1'b0,write_row_r,bank_id,write_payload_r};
        wire [54:0] encoded;
        ot_hdc_v41_fh_sram_enc u_encode(.payload(identity_payload),.word(encoded));
        always @(posedge clk) begin
            write_payload_r<=wr_data;
            write_row_r<=write_row;
            encoded_r<=encoded;
            write_row_encoded_r<=write_row_r;
        end
        always @(posedge clk or negedge rst_n)
            if(!rst_n) begin write_v_r<=0;write_encoded_v_r<=0;end
            else begin
                write_v_r<=write_ok;
                write_encoded_v_r<=write_v_r;
            end
        reg committed_q;
        always @(posedge clk or negedge rst_n)
            if(!rst_n) committed_q<=0;else committed_q<=write_encoded_v_r;
        assign wr_committed=committed_q;
        wire [127:0] macro_word;
        ot_sram_1r1w_512x128_m4_r2c2 u_sram (
            .clk(clk),.r_ce_in(read_ok),.r_addr_in(read_row),.rd_out(macro_word),
            .w_ce_in(write_encoded_v_r),.w_addr_in(write_row_encoded_r),
            .wd_in({73'b0,encoded_r}),.w_mask_in({73'b0,{55{1'b1}}}),
            .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(14'b0));
        reg [54:0] raw_word_r;
        reg [8:0] requested_row_r,capture_row_r;
        reg request_v_r,capture_v_r;
        always @(posedge clk) begin
            requested_row_r<=read_row;
            capture_row_r<=requested_row_r;
            raw_word_r<=macro_word[54:0];
        end
        always @(posedge clk or negedge rst_n)
            if(!rst_n) begin request_v_r<=0;capture_v_r<=0;end
            else begin request_v_r<=read_ok;capture_v_r<=request_v_r;end
        wire [47:0] decoded;
        wire ce,ue;
        ot_rom_secded_dec #(.K(48)) u_decode (.cw(raw_word_r),.data(decoded),.corrected(ce),.uncorrectable(ue));
        wire [47:0] checked;
        wire checked_ce,checked_ue,checked_v;
        wire [8:0] checked_row;
        generate if(PROTECT_SPLIT) begin : g_decode_capture
            reg [47:0] decoded_r;
            reg [8:0] row_r;
            reg ce_r,ue_r,valid_r;
            always @(posedge clk) begin
                decoded_r<=decoded;row_r<=capture_row_r;ce_r<=ce;ue_r<=ue;
            end
            always @(posedge clk or negedge rst_n)
                if(!rst_n) valid_r<=0;else valid_r<=capture_v_r;
            assign checked=decoded_r;assign checked_row=row_r;
            assign checked_ce=ce_r;assign checked_ue=ue_r;assign checked_v=valid_r;
        end else begin : g_decode_direct
            assign checked=decoded;assign checked_row=capture_row_r;
            assign checked_ce=ce;assign checked_ue=ue;assign checked_v=capture_v_r;
        end endgenerate
        wire identity_ok=checked[47:32]=={1'b0,checked_row,bank_id};
        reg [31:0] payload_q;
        reg valid_q,corrected_q,poison_q;
        always @(posedge clk) if(checked_v&&!checked_ue&&identity_ok) payload_q<=checked[31:0];
        always @(posedge clk or negedge rst_n)
            if(!rst_n) begin valid_q<=0;corrected_q<=0;poison_q<=0;end
            else begin
                valid_q<=checked_v&&!checked_ue&&identity_ok;
                corrected_q<=checked_v&&checked_ce&&!checked_ue&&identity_ok;
                if(checked_v&&(checked_ue||!identity_ok)) poison_q<=1;
            end
        assign rd_data=payload_q;
        assign rd_valid=valid_q&&!poison_q;
        assign corrected=corrected_q;
        assign poisoned=poison_q;
endmodule

// Kept per-lane request register (ADDR_PIPE stage 2): the lane macro's inputs leave a flop beside it.
(* keep_hierarchy *)
module ot_hdc_v41_fh_lane_req(
    input wire clk,rst_n,read_ok_d,write_ok_d,
    input wire [8:0] read_row_d,write_row_d,
    input wire [31:0] wr_data_d,
    output reg read_ok,write_ok,
    output reg [8:0] read_row,write_row,
    output reg [31:0] wr_data
);
    always @(posedge clk or negedge rst_n)
        if(!rst_n) begin read_ok<=0; write_ok<=0; end
        else begin read_ok<=read_ok_d; write_ok<=write_ok_d; end
    always @(posedge clk) begin read_row<=read_row_d; write_row<=write_row_d; wr_data<=wr_data_d; end
endmodule
