`timescale 1ns/1ps
// Dual-clock Gray-pointer FIFO.  Assertion of either interface reset flushes
// both pointer domains.  Deassertion is conditioned independently on each
// clock, followed by an online rendezvous before either interface reopens.
// DEPTH must be a power of two and at least four.  Data memory is intentionally
// not reset, because validity is carried solely by synchronized pointers.
module ot_async_fifo #(
    parameter integer WIDTH = 32,
    parameter integer DEPTH = 4,
    // EXT_RST 1 (el1013-s81-vmfe/B8, coordinator decision 10-13): wr_rst_n / rd_rst_n are ALREADY the two domains' own
    // conditioned resets (each the output of that domain's reset synchroniser + registered tree, both synchronisers
    // cleared by the SAME asynchronous source, so an assertion still flushes both sides together).  No conditioner is
    // built here and no flop of one domain reaches a reset pin of the other: every recovery / removal arc is same-clock.
    parameter integer EXT_RST = 0
`ifdef OT_VMFE_FCC_PIPE
    , parameter integer FIFO_PIPE = 0, parameter integer PIPE_CHUNK = 128
`endif
) (
    input  wire             wr_clk,
    input  wire             wr_rst_n,
    input  wire             wr_valid,
    output wire             wr_ready,
    input  wire [WIDTH-1:0] wr_data,
    output reg              wr_overflow,
    input  wire             rd_clk,
    input  wire             rd_rst_n,
    output wire             rd_valid,
    input  wire             rd_ready,
    output wire [WIDTH-1:0] rd_data,
    output reg              rd_underflow
`ifdef OT_SPVM_RESET_ACK
    , output wire wr_reset_live, output wire rd_reset_live
`endif
);
    initial begin
        if (DEPTH < 4 || (DEPTH & (DEPTH-1)) != 0)
            $error("ot_async_fifo DEPTH must be a power of two >= 4");
    end

    localparam integer ADDR_W = $clog2(DEPTH);
    localparam integer PTR_W = ADDR_W + 1;
    wire fifo_async_rst_n = wr_rst_n && rd_rst_n;
    wire wr_domain_rst_n;
    wire rd_domain_rst_n;
    generate if (EXT_RST != 0) begin : g_xr
        assign wr_domain_rst_n = wr_rst_n;
        assign rd_domain_rst_n = rd_rst_n;
    end else begin : g_ir
        ot_reset_sync wr_reset_conditioner (
            .clk(wr_clk), .async_rst_n(fifo_async_rst_n),
            .sync_rst_n(wr_domain_rst_n));
        ot_reset_sync rd_reset_conditioner (
            .clk(rd_clk), .async_rst_n(fifo_async_rst_n),
            .sync_rst_n(rd_domain_rst_n));
    end endgenerate

    reg [WIDTH-1:0] mem [0:DEPTH-1];
`ifdef OT_VMFE_FCC_PIPE
    wire [PTR_W-1:0] wr_gray_visible;
`endif
    reg [PTR_W-1:0] wr_bin, wr_gray;
    reg [PTR_W-1:0] rd_bin, rd_gray;
    (* async_reg = "true" *) reg [PTR_W-1:0] rd_gray_w1, rd_gray_w2;
    (* async_reg = "true" *) reg [PTR_W-1:0] wr_gray_r1, wr_gray_r2;
    reg wr_online, rd_online;
    (* async_reg = "true" *) reg rd_online_w1, rd_online_w2;
    (* async_reg = "true" *) reg wr_online_r1, wr_online_r2;
`ifdef OT_S81_HOST_PHASESAFE
    reg [PTR_W-1:0] wr_gray_seam, rd_gray_seam;
    reg wr_online_seam, rd_online_seam;
    always @* if (!wr_domain_rst_n) begin wr_gray_seam='0;wr_online_seam=0;end
              else if (!wr_clk) begin wr_gray_seam=wr_gray;wr_online_seam=wr_online;end
    always @* if (!rd_domain_rst_n) begin rd_gray_seam='0;rd_online_seam=0;end
              else if (!rd_clk) begin rd_gray_seam=rd_gray;rd_online_seam=rd_online;end
`else
    wire [PTR_W-1:0] wr_gray_seam=wr_gray,rd_gray_seam=rd_gray;
    wire wr_online_seam=wr_online,rd_online_seam=rd_online;
`endif
    reg wr_full, rd_empty;
    wire wr_fire = wr_valid && wr_ready;
    wire rd_fire = rd_valid && rd_ready;
    wire [PTR_W-1:0] wr_increment = {{(PTR_W-1){1'b0}},wr_fire};
    wire [PTR_W-1:0] wr_bin_next = wr_bin + wr_increment;
    wire [PTR_W-1:0] wr_gray_next = (wr_bin_next >> 1) ^ wr_bin_next;
    wire [PTR_W-1:0] rd_increment = {{(PTR_W-1){1'b0}},rd_fire};
    wire [PTR_W-1:0] rd_bin_next = rd_bin + rd_increment;
    wire [PTR_W-1:0] rd_gray_next = (rd_bin_next >> 1) ^ rd_bin_next;
    wire wr_full_next;
    wire rd_empty_next;

    // For a binary reflected Gray pointer, full is the write pointer one lap
    // ahead of read, i.e. the synchronized read pointer with its two MSBs
    // inverted.
    assign wr_full_next = (wr_gray_next ==
                           {~rd_gray_w2[PTR_W-1:PTR_W-2],
                            rd_gray_w2[PTR_W-3:0]});
    assign rd_empty_next = (rd_gray_next == wr_gray_r2);
    assign wr_ready = wr_domain_rst_n && rd_online_w2 && !wr_full;
    assign rd_valid = rd_domain_rst_n && wr_online_r2 && !rd_empty;
`ifdef OT_SPVM_RESET_ACK
    // Existing local online/rendezvous states; fullness/emptiness is not reset readiness.
    assign wr_reset_live = wr_domain_rst_n && wr_online && rd_online_w2;
    assign rd_reset_live = rd_domain_rst_n && rd_online && wr_online_r2;
`endif
`ifdef OT_VMFE_FCC_PIPE
    generate if (FIFO_PIPE != 0) begin : g_pipe
        localparam integer NCH = (WIDTH + PIPE_CHUNK - 1) / PIPE_CHUNK;
        reg [WIDTH-1:0] data_q;
        reg [PTR_W-1:0] pub_q;
        wire [DEPTH-1:0] selected [0:NCH-1], read_sel [0:NCH-1];
        wire [DEPTH-1:0] w_sel = {{(DEPTH-1){1'b0}},1'b1} << wr_bin[ADDR_W-1:0];
`ifdef OT_VMFE_MUT_FCC_PIPE_SELECT
        // Candidate-specific negative control: select the following entry.
        wire [ADDR_W-1:0] bad_read_addr = rd_bin_next[ADDR_W-1:0] + 1'b1;
        wire [DEPTH-1:0] r_sel_next = {{(DEPTH-1){1'b0}},1'b1} << bad_read_addr;
`else
        wire [DEPTH-1:0] r_sel_next = {{(DEPTH-1){1'b0}},1'b1} << rd_bin_next[ADDR_W-1:0];
`endif
        always @(posedge wr_clk) data_q <= wr_data; // payload reset-free, no valid-gated fanout
        always @(posedge wr_clk or negedge wr_domain_rst_n)
            if (!wr_domain_rst_n) pub_q <= {PTR_W{1'b0}};
            else pub_q <= wr_gray; // publish only when the preceding accepted entry commits
        assign wr_gray_visible = pub_q;
        for (genvar pc=0;pc<NCH;pc=pc+1) begin : g_c
            localparam integer LO=pc*PIPE_CHUNK;
            localparam integer CW=(WIDTH-LO < PIPE_CHUNK) ? WIDTH-LO : PIPE_CHUNK;
            // Distinct kept per-chunk select flops cap each real Q fanout at128 bits.
            ot_async_fifo_select_copy #(.W(DEPTH),.ID(pc),.RESET_ONE(0)) u_wsel
              (.clk(wr_clk),.rst_n(wr_domain_rst_n),.d(w_sel & {DEPTH{wr_fire}}),.q(selected[pc]));
            ot_async_fifo_select_copy #(.W(DEPTH),.ID(100+pc),.RESET_ONE(1)) u_rsel
              (.clk(rd_clk),.rst_n(rd_domain_rst_n),.d(r_sel_next),.q(read_sel[pc]));
            always @(posedge wr_clk) begin : p_write integer pe;
                for(pe=0;pe<DEPTH;pe=pe+1)
                    if(selected[pc][pe]) mem[pe][LO+:CW] <= data_q[LO+:CW];
            end
            reg [CW-1:0] row_or;
            always @* begin : p_read integer pe;
                row_or={CW{1'b0}};
                for(pe=0;pe<DEPTH;pe=pe+1)
                    row_or=row_or | (mem[pe][LO+:CW] & {CW{read_sel[pc][pe]}});
            end
            assign rd_data[LO+:CW]=row_or;
        end
    end else begin : g_no_pipe
        assign wr_gray_visible=wr_gray;
        assign rd_data=mem[rd_bin[ADDR_W-1:0]];
        always @(posedge wr_clk) if(wr_domain_rst_n && wr_fire) mem[wr_bin[ADDR_W-1:0]] <= wr_data;
    end endgenerate
`else
`ifdef OT_S81_HOST_PHASESAFE
    reg [WIDTH-1:0] head_seam;
    always @* if (rd_clk) head_seam=mem[rd_bin[ADDR_W-1:0]];
    assign rd_data=head_seam;
`else
    assign rd_data = mem[rd_bin[ADDR_W-1:0]];
`endif
`endif

    always @(posedge wr_clk or negedge wr_domain_rst_n) begin
        if (!wr_domain_rst_n) begin
            rd_gray_w1 <= {PTR_W{1'b0}};
            rd_gray_w2 <= {PTR_W{1'b0}};
            rd_online_w1 <= 1'b0;
            rd_online_w2 <= 1'b0;
            wr_online <= 1'b0;
            wr_bin <= {PTR_W{1'b0}};
            wr_gray <= {PTR_W{1'b0}};
            wr_full <= 1'b0;
            wr_overflow <= 1'b0;
        end else begin
            wr_online <= 1'b1;
            rd_online_w1 <= rd_online_seam;
            rd_online_w2 <= rd_online_w1;
            rd_gray_w1 <= rd_gray_seam;
            rd_gray_w2 <= rd_gray_w1;
            // Valid may legally remain asserted while ready is low.
`ifndef OT_VMFE_FCC_PIPE
            if (wr_fire)
                mem[wr_bin[ADDR_W-1:0]] <= wr_data;
`endif
            wr_bin <= wr_bin_next;
            wr_gray <= wr_gray_next;
            wr_full <= wr_full_next;
        end
    end

    always @(posedge rd_clk or negedge rd_domain_rst_n) begin
        if (!rd_domain_rst_n) begin
            wr_gray_r1 <= {PTR_W{1'b0}};
            wr_gray_r2 <= {PTR_W{1'b0}};
            wr_online_r1 <= 1'b0;
            wr_online_r2 <= 1'b0;
            rd_online <= 1'b0;
            rd_bin <= {PTR_W{1'b0}};
            rd_gray <= {PTR_W{1'b0}};
            rd_empty <= 1'b1;
            rd_underflow <= 1'b0;
        end else begin
            rd_online <= 1'b1;
            wr_online_r1 <= wr_online_seam;
            wr_online_r2 <= wr_online_r1;
`ifdef OT_VMFE_FCC_PIPE
            wr_gray_r1 <= wr_gray_visible;
`else
            wr_gray_r1 <= wr_gray_seam;
`endif
            wr_gray_r2 <= wr_gray_r1;
            // Ready may legally remain asserted while valid is low.
            rd_bin <= rd_bin_next;
            rd_gray <= rd_gray_next;
            rd_empty <= rd_empty_next;
        end
    end

`ifndef SYNTHESIS
    // Gray pointers may only change one bit per local write/read event.
    reg [PTR_W-1:0] wr_gray_prev, rd_gray_prev;
    wire [PTR_W-1:0] wr_gray_delta = wr_gray ^ wr_gray_prev;
    wire [PTR_W-1:0] rd_gray_delta = rd_gray ^ rd_gray_prev;
    wire [PTR_W-1:0] gray_one = {{(PTR_W-1){1'b0}},1'b1};
    wire wr_gray_multi = |(wr_gray_delta & (wr_gray_delta - gray_one));
    wire rd_gray_multi = |(rd_gray_delta & (rd_gray_delta - gray_one));
    always @(posedge wr_clk or negedge wr_domain_rst_n) begin
        if (!wr_domain_rst_n)
            wr_gray_prev <= {PTR_W{1'b0}};
        else begin
            if (wr_gray_multi)
                $error("ot_async_fifo write Gray pointer changed multiple bits");
            wr_gray_prev <= wr_gray;
        end
    end
    always @(posedge rd_clk or negedge rd_domain_rst_n) begin
        if (!rd_domain_rst_n)
            rd_gray_prev <= {PTR_W{1'b0}};
        else begin
            if (rd_gray_multi)
                $error("ot_async_fifo read Gray pointer changed multiple bits");
            rd_gray_prev <= rd_gray;
        end
    end
`endif
endmodule

`ifdef OT_VMFE_FCC_PIPE
// These are real in-leaf flops, not external hard-child placeholders.
(* keep_hierarchy = "yes" *)
module ot_async_fifo_select_copy #(parameter integer W=16,ID=0,RESET_ONE=0)
(input wire clk,rst_n,input wire [W-1:0] d,output reg [W-1:0] q);
    (* keep = 1 *) wire [W-1:0] dq=d;
    always @(posedge clk or negedge rst_n)
        if(!rst_n) q <= RESET_ONE ? {{(W-1){1'b0}},1'b1} : {W{1'b0}};
        else q<=dq;
endmodule
`endif
