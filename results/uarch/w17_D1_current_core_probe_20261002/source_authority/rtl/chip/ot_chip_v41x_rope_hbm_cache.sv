`timescale 1ns/1ps
// One token-position RoPE coefficient cache on the shared four-stack K port.
// A table is striped in 32-byte sectors: stack s owns pair indices 8*s..8*s+7,
// at two sectors per position. `plain_base`/`yarn_base` are per-stack sector
// addresses allocated by the die region ledger, not separate HBM ports.
// The 32 FP32 cos/sin pairs are held until pf_release so interleaved users cannot
// evict a token's coefficients between its first and final RoPE SU operations.
module ot_chip_v41x_rope_hbm_cache #(
    parameter integer HAW = 30,
    parameter integer TAGW = 16,
    parameter integer PW = 21,
    parameter integer MAX_POS = 1048576
) (
    input  wire                clk,
    input  wire                rst_n,
    input  wire                pf_v,
    output wire                pf_rdy,
    input  wire                pf_kind,       // 0 plain, 1 YaRN
    input  wire [PW-1:0]       pf_pos,
    input  wire                pf_release,
    output reg                 pf_done,
    output reg                 cache_valid,
    output reg                 cache_hold,
    output reg                 cache_kind,
    output reg  [PW-1:0]      cache_pos,
    output wire [2047:0]      cache_pairs,   // pair i = {sin[31:0],cos[31:0]}
    input  wire [1:0]          table_present,
    input  wire [4*HAW-1:0]    plain_base,
    input  wire [4*HAW-1:0]    yarn_base,
    // Four independent K-side stack clients. One 32-byte sector per request.
    output wire [3:0]          req_v,
    input  wire [3:0]          req_rdy,
    output wire [4*HAW-1:0]    req_addr,
    output wire [4*4-1:0]      req_len,
    output wire [4*TAGW-1:0]   req_tag,
    output wire [3:0]          req_we,
    output wire [4*256-1:0]    req_wdata,
    output wire [4*32-1:0]     req_wstrb,
    input  wire [3:0]          rsp_v,
    output wire [3:0]          rsp_rdy,
    input  wire [4*TAGW-1:0]   rsp_tag,
    input  wire [4*4-1:0]      rsp_beat,
    input  wire [4*256-1:0]    rsp_data,
    output reg                 fault,
    output reg  [31:0]         issued_sectors,
    output reg  [31:0]         received_sectors,
    output reg  [31:0]         stalled_cycles,
    output reg  [31:0]         cache_hits
);
    localparam [1:0] IDLE=0, ISSUE=1, WAIT=2;
    reg [1:0] state;
    reg [1:0] phase [0:3];
    reg [7:0] issued, received;
    reg [HAW-1:0] base [0:3];
    reg [255:0] sector [0:7];
    wire hit = cache_valid && cache_kind == pf_kind && cache_pos == pf_pos;
    wire [HAW:0] last_offset = (HAW+1)'(pf_pos) * 2 + 1;
    wire [3:0] base_overflow;
    assign pf_rdy = state == IDLE && (!cache_hold || hit);
    assign req_we = 4'b0;
    assign req_wdata = '0;
    assign req_wstrb = '0;
    genvar s;
    generate for (s=0;s<4;s=s+1) begin : g_stack
        wire [HAW:0] end_addr = {1'b0, (pf_kind ? yarn_base[s*HAW +: HAW] :
                                                 plain_base[s*HAW +: HAW])} + last_offset;
        assign req_v[s] = state == ISSUE && phase[s] < 2;
        // Capture the position offset at prefetch acceptance. The K-port
        // address path then has only the phase increment, not a wide
        // position multiply and add after the cache-pos register.
        assign req_addr[s*HAW +: HAW] = base[s] + HAW'(phase[s]);
        assign req_len[s*4 +: 4] = 4'd1;
        assign req_tag[s*TAGW +: TAGW] = TAGW'(phase[s]);
        assign rsp_rdy[s] = state == ISSUE || state == WAIT;
        assign cache_pairs[s*512 +: 512] = {sector[2*s+1],sector[2*s]};
        assign base_overflow[s] = end_addr[HAW];
    end endgenerate
    integer i;
    reg [2:0] req_n, rsp_n;
    always @(*) begin
        req_n=0; rsp_n=0;
        for (integer k=0;k<4;k=k+1) begin
            req_n=req_n + {2'b0, req_v[k] && req_rdy[k]};
            rsp_n=rsp_n + {2'b0, rsp_v[k] && rsp_rdy[k]};
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state<=IDLE; pf_done<=0; cache_valid<=0; cache_hold<=0;
            cache_kind<=0; cache_pos<=0; fault<=0;
            issued<=0; received<=0;
            issued_sectors<=0; received_sectors<=0; stalled_cycles<=0; cache_hits<=0;
            for (i=0;i<4;i=i+1) begin phase[i]<=0; base[i]<=0; end
            for (i=0;i<8;i=i+1) sector[i]<=0;
        end else begin
            pf_done<=0;
            if (pf_release && state == IDLE) cache_hold<=0;
            issued_sectors<=issued_sectors + {29'd0,req_n};
            received_sectors<=received_sectors + {29'd0,rsp_n};
            if (|(req_v & ~req_rdy)) stalled_cycles<=stalled_cycles+1;
            case (state)
                IDLE: if (pf_v && pf_rdy) begin
                    if (hit) begin
                        pf_done<=1; cache_hold<=1; cache_hits<=cache_hits+1;
                    end else if (pf_pos >= PW'(MAX_POS) || !table_present[pf_kind] || |base_overflow) begin
                        fault<=1;
                    end else begin
                        cache_valid<=0; cache_hold<=0; cache_kind<=pf_kind; cache_pos<=pf_pos;
                        issued<=0; received<=0;
                        for (i=0;i<4;i=i+1) begin
                            phase[i]<=0;
                            base[i]<=(pf_kind ? yarn_base[i*HAW +: HAW] :
                                                 plain_base[i*HAW +: HAW]) + HAW'(pf_pos * 2);
                        end
                        state<=ISSUE;
                    end
                end
                ISSUE: begin
                    for (i=0;i<4;i=i+1) if (req_v[i] && req_rdy[i]) begin
                        issued[2*i+int'(phase[i])]<=1;
                        phase[i]<=phase[i]+1'b1;
                    end
                    if (phase[0]==2 && phase[1]==2 && phase[2]==2 && phase[3]==2)
                        state<=WAIT;
                end
                WAIT: if (&received && !fault && !(|rsp_v)) begin
                    cache_valid<=1; cache_hold<=1; pf_done<=1; state<=IDLE;
                end
                default: state<=IDLE;
            endcase
            if (state==ISSUE || state==WAIT)
                for (i=0;i<4;i=i+1) if (rsp_v[i] && rsp_rdy[i]) begin
                    if ((rsp_tag[i*TAGW +: TAGW] >> 1) != 0 || rsp_beat[i*4 +: 4] != 0 ||
                        !issued[2*i+int'(rsp_tag[i*TAGW])] ||
                         received[2*i+int'(rsp_tag[i*TAGW])]) fault<=1;
                    else begin
                        sector[2*i+int'(rsp_tag[i*TAGW])]<=rsp_data[i*256 +: 256];
                        received[2*i+int'(rsp_tag[i*TAGW])]<=1;
                    end
                end
        end
    end
endmodule
