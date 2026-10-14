`timescale 1ns/1ps
// Distinct functional prototype; allocator and transport must supply actual TAG59.
module ot_qwen_tp_seq_w12_vrl_native59 #(
    parameter integer VRL = 1,     // vre -> vrq edges
    parameter integer RMUT = 0,    // el1011-q-seq negative control: vm_wdata bit 0 flipped on the AR write
    parameter integer CRED = 0,    // 0: c_ready = ready (base); > 0: c_ready = credit return pulse, CRED credits
    parameter integer ENABLE_AR256 = 0,
    parameter integer N    = 4,
    parameter integer NW   = 16,
    parameter integer PAW  = 12,
    parameter integer VWA  = 8,
    parameter integer DAW  = 6,
    parameter integer FW   = 512,
    parameter integer TAGW = 59,
    // Qwen full-vocabulary descriptors extend row0 with reserved bits
    // [19:18]; the existing 64-bit descriptor shape is unchanged.
    parameter integer QWEN_FULLSHAPE = 0,
    parameter integer RB   = (N > 1) ? $clog2(N) : 1
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              rst_nw,      // vm_wdata reset copy (el1011-q-seq RRG; logically rst_n)
    // package controller side (the core's handshake)
    input wire [15:0] tag_epoch,
    input wire [5:0] tag_stage,
    input wire [58:0] r_tag,
    input  wire              start,
    input  wire [NW-1:0]     token,
    input  wire [NW-1:0]     pos,
    output reg               done,
    output reg  [NW-1:0]     next_token,
    output reg  [31:0]       next_val,
    output reg               fault,
    output wire              coll_busy,
    // decode core
    output wire              core_start,
    output wire [NW-1:0]     core_token,
    output wire [NW-1:0]     core_pos,
    input  wire              core_done,
    input  wire [NW-1:0]     core_next_token,
    input  wire [31:0]       core_next_val,
    input  wire              core_fault,
    output reg  [PAW-1:0]    prog_base,
    // segment descriptors (synchronous read)
    output reg               desc_re,
    output reg  [DAW-1:0]    desc_addr,
    input  wire [63:0]       desc_q,
    // vector memory word port (synchronous read)
    output reg               vm_re,
    output reg  [VWA-1:0]    vm_raddr,
    input  wire [FW-1:0]     vm_rq,
    output reg               vm_we,
    output reg  [VWA-1:0]    vm_waddr,
    output reg  [FW-1:0]     vm_wdata,
    // one-shot collective unit (ot_rom_oneshot_allreduce die port)
    output wire              c_valid,
    input  wire              c_ready,
    output wire [FW-1:0]     c_data,
    output wire              c_last,
    output wire              c_mode,
    output wire [TAGW-1:0]   c_tag,
    input  wire              r_valid,
    input  wire [FW-1:0]     r_data,
    input  wire              r_last,
    input  wire [RB-1:0]     r_rank,
    input  wire              r_err
);
    localparam [1:0] K_END = 2'd0, K_AR = 2'd1, K_ARGMAX = 2'd2;
    localparam [2:0] S_IDLE = 0, S_DESC = 1, S_DLAT = 2, S_RUN = 3, S_CWAIT = 4, S_COLL = 5;
    reg [2:0]     st;
    reg [NW-1:0]  tok_r, pos_r;
    reg [DAW-1:0] seg;
    reg [1:0]     kind;
    reg [VWA-1:0] vw;
    reg [8:0]     nw;
    reg [NW-1:0]  row0;

    assign core_start = (st == S_RUN);
    assign core_token = tok_r;
    assign core_pos   = pos_r;
    assign coll_busy  = (st == S_COLL);
    reg [15:0] epoch_r; reg [5:0] stage_r;
    initial if (NW!=18 || TAGW!=59 || DAW!=6 || RB!=3 || N!=8) $error("native59 fixed identity ABI");
    assign c_tag = {epoch_r, stage_r, tok_r, pos_r[12:0], seg};
    wire identity_valid = token <= 18'd151935 && pos <= 18'd8191 && tag_stage <= 6'd37;
    wire return_match = r_tag == c_tag;
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin epoch_r<=0;stage_r<=0;end
      else if (start && st==S_IDLE && identity_valid) begin epoch_r<=tag_epoch;stage_r<=tag_stage;end

    // argmax order: larger logit wins (ties are impossible across ranks' rows
    // except by value, and then the earlier rank -- the lower row -- stays)
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction

    // -- transmit: vector-memory words (all-reduce) or the argmax record ------------------
    localparam integer QB = (VRL > 1) ? $clog2(VRL + 4) : 2;   // queue address bits
    localparam integer QD = 1 << QB;
    reg [FW-1:0] q_d [0:QD-1];
    reg [QB-1:0] q_w, q_r;
    reg [QB:0]   q_n;
    reg [8:0]    rd_k, tx_k, rx_k;
    reg [VRL-1:0] rd_p;                 // reads in flight, oldest at VRL-1
    wire          rd_v = rd_p[VRL-1];
    integer       rd_i, rd_n;
    always @(*) begin rd_n = 0; for (rd_i = 0; rd_i < VRL; rd_i = rd_i + 1) rd_n = rd_n + rd_p[rd_i]; end
    reg [7:0] c_cred;   // credit mode: a word leaves only with a credit (valid = send)
    assign c_valid = (st == S_COLL) && (q_n != 0) && (CRED == 0 || c_cred != 8'd0);
    assign c_data  = q_d[q_r];
    assign c_mode  = (kind == K_ARGMAX);
    assign c_last  = (tx_k == ((kind == K_ARGMAX) ? 9'd0 : nw - 1'b1));
    wire   c_fire  = c_valid && ((CRED == 0) ? c_ready : 1'b1);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) c_cred <= 8'(CRED);
        else if (CRED != 0) c_cred <= c_cred - (c_fire ? 8'd1 : 8'd0) + ((c_ready && (c_cred < CRED || c_fire)) ? 8'd1 : 8'd0);
    wire   rd_go   = (st == S_COLL) && kind == K_AR && rd_k < nw && (q_n + rd_n) < QD;

    reg [NW-1:0] best_i;
    reg [31:0]   best_v;
    wire [31:0]  g_val = r_data[31:0];
    wire [NW-1:0] g_idx = r_data[32 +: NW];
    wire [8:0]   rx_total = (kind == K_ARGMAX) ? N : nw;

    always @(*) begin
        vm_re = rd_go;
        vm_raddr = vw + rd_k;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; done <= 1'b0; fault <= 1'b0; next_token <= 0; next_val <= 0;
            tok_r <= 0; pos_r <= 0; seg <= 0; kind <= K_END; vw <= 0; nw <= 0; row0 <= 0;
            prog_base <= 0; desc_re <= 1'b0; desc_addr <= 0;
            vm_we <= 1'b0; vm_waddr <= 0;
            q_w <= 0; q_r <= 0; q_n <= 0; rd_k <= 0; tx_k <= 0; rx_k <= 0; rd_p <= {VRL{1'b0}};
            best_i <= 0; best_v <= 0;
        end else begin
            desc_re <= 1'b0;
            vm_we <= 1'b0;
            rd_p <= (VRL > 1) ? {rd_p, rd_go} : rd_go;
            // Reject before receive counters, vector writes or argmax updates.
            if (r_valid && (st != S_COLL || !return_match)) fault <= 1'b1;
            if (CRED!=0 && c_ready && c_cred==CRED && !c_fire) fault <= 1'b1;
            case (st)
                S_IDLE: if (start && !identity_valid) fault <= 1'b1; else if (start) begin
                    tok_r <= token; pos_r <= pos; seg <= 0; done <= 1'b0;
                    desc_re <= 1'b1; desc_addr <= 0; st <= S_DLAT;
                end
                S_DESC: begin desc_re <= 1'b1; desc_addr <= seg; st <= S_DLAT; end
                S_DLAT: if (!desc_re) begin
                    kind <= desc_q[1:0]; vw <= desc_q[2 +: 8];
                    nw <= (ENABLE_AR256 != 0 && desc_q[1:0] == K_AR && desc_q[10 +: 8] == 8'd0) ? 9'd256 : {1'b0, desc_q[10 +: 8]};
                    prog_base <= desc_q[32 +: PAW];
                    row0 <= (QWEN_FULLSHAPE != 0) ?
                            ({desc_q[19:18], desc_q[63:48]}) : desc_q[48 +: NW];
                    st <= S_RUN;
                end
                S_RUN: st <= S_CWAIT;              // the core samples core_start on this edge
                S_CWAIT: if (core_done) begin
                    if (core_fault) fault <= 1'b1;
                    rd_k <= 0; tx_k <= 0; rx_k <= 0;
                    if (kind == K_END) begin
                        done <= 1'b1; next_token <= core_next_token + row0; next_val <= core_next_val;
                        st <= S_IDLE;
                    end else begin
                        if (kind == K_ARGMAX) begin
                            // the die's own {logit, row} is the one record it gathers
                            q_d[q_w] <= {{(FW - 32 - NW){1'b0}}, core_next_token + row0, core_next_val};
                            q_w <= q_w + 1'b1;
                            q_n <= q_n + 1'b1;
                        end
                        st <= S_COLL;
                    end
                end
                S_COLL: begin
                    // queue: vector-memory words read one cycle earlier; pop on send
                    if (rd_go) rd_k <= rd_k + 1'b1;
                    if (rd_v) begin q_d[q_w] <= vm_rq; q_w <= q_w + 1'b1; end
                    if (c_fire) begin q_r <= q_r + 1'b1; tx_k <= tx_k + 1'b1; end
                    q_n <= q_n + (rd_v ? 1'b1 : 1'b0) - (c_fire ? 1'b1 : 1'b0);
                    // receive
                    if (r_valid && return_match) begin
                        if (r_err) fault <= 1'b1;
                        rx_k <= rx_k + 1'b1;
                        if (r_last != (rx_k == rx_total - 1'b1)) fault <= 1'b1;
                        if (kind == K_AR) begin
                            vm_we <= 1'b1; vm_waddr <= vw + rx_k;
                        end else begin
                            if (r_rank != rx_k[RB-1:0]) fault <= 1'b1;
                            if (rx_k == 0 || okey(g_val) > okey(best_v)) begin
                                best_v <= g_val; best_i <= g_idx;
                            end
                        end
                        if (rx_k == rx_total - 1'b1) begin
                            if (kind == K_AR) begin
                                seg <= seg + 1'b1; st <= S_DESC;
                            end else begin
                                done <= 1'b1; st <= S_IDLE;
                                if (okey(g_val) > okey(best_v)) begin
                                    next_token <= g_idx; next_val <= g_val;
                                end else begin
                                    next_token <= best_i; next_val <= best_v;
                                end
                            end
                        end
                    end
                end
                default: st <= S_IDLE;
            endcase
        end
    end
    // vm_wdata: the AR receive word (the S_COLL / r_valid / K_AR edge of the main block), own reset copy
    always @(posedge clk or negedge rst_nw)
        if (!rst_nw) vm_wdata <= {FW{1'b0}};
        else if (st == S_COLL && r_valid && return_match && kind == K_AR) vm_wdata <= r_data ^ FW'(RMUT != 0);
endmodule
