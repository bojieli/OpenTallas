`timescale 1ns/1ps
// Item9 additive GEO default0: geographic Boolean tree, retained intermediates.
// Original tree/source preserved. No new pipeline, memory, credit or rounding.
module ot_gpu_coll_mux_item9_geo #(
    parameter integer ENABLE = 0,
    parameter integer NSM    = 2,
    parameter integer NL     = 128,
    parameter integer ODUP   = 16,
    parameter integer TREE = 0,
    parameter integer GEO = 0
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire [NSM-1:0]        s_req_v,
    output wire [NSM-1:0]        s_req_rdy,
    input  wire [NSM-1:0]        s_mode,
    input  wire [NSM*8-1:0]      s_count,
    input  wire [NSM*NL*32-1:0]  s_data,
    output wire [NSM-1:0]        s_rsp_v,
    input  wire [NSM-1:0]        s_rsp_rdy,
    output wire [NL*32-1:0]      s_rsp_data,
    output wire                  m_req_v,
    input  wire                  m_req_rdy,
    output wire                  m_mode,
    output wire [7:0]            m_count,
    output wire [NL*32-1:0]      m_data,
    input  wire                  m_rsp_v,
    output wire                  m_rsp_rdy,
    input  wire [NL*32-1:0]      m_rsp_data
);
generate if(GEO==0)begin:g_original
    ot_gpu_coll_mux_item9_tree #(.ENABLE(ENABLE),.NSM(NSM),.NL(NL),.ODUP(ODUP),.TREE(TREE)) u_original(
        .clk(clk),.rst_n(rst_n),.s_req_v(s_req_v),.s_req_rdy(s_req_rdy),
        .s_mode(s_mode),.s_count(s_count),.s_data(s_data),.s_rsp_v(s_rsp_v),
        .s_rsp_rdy(s_rsp_rdy),.s_rsp_data(s_rsp_data),.m_req_v(m_req_v),
        .m_req_rdy(m_req_rdy),.m_mode(m_mode),.m_count(m_count),.m_data(m_data),
        .m_rsp_v(m_rsp_v),.m_rsp_rdy(m_rsp_rdy),.m_rsp_data(m_rsp_data));
end else if (ENABLE == 0) begin : g_off
    assign s_req_rdy = {NSM{1'b0}}; assign s_rsp_v = {NSM{1'b0}}; assign s_rsp_data = {NL*32{1'b0}};
    assign m_req_v = 1'b0; assign m_mode = 1'b0; assign m_count = 8'd0; assign m_data = {NL*32{1'b0}};
    assign m_rsp_rdy = 1'b0;
end else begin : g_on
    localparam integer SB = (NSM > 1) ? $clog2(NSM) : 1;
    reg          busy, sent;
    reg [SB-1:0] own;
    reg [SB-1:0] pick;
    reg          any;
    integer i;
    always @* begin
        any = 1'b0; pick = {SB{1'b0}};
        for (i = NSM - 1; i >= 0; i = i - 1) if (s_req_v[i]) begin any = 1'b1; pick = i[SB-1:0]; end
    end
    wire [SB-1:0] sel = busy ? own : pick;
    assign m_req_v = busy && !sent && s_req_v[own];
    assign m_mode = s_mode[own];
    assign m_count = s_count[own*8 +: 8];
    localparam integer DS = (NL * 32 + ODUP - 1) / ODUP;
    wire [SB-1:0] own_n = (!busy && any) ? sel : own;
    genvar dsl;
    for (dsl = 0; dsl < ODUP; dsl = dsl + 1) begin : g_dsl
        localparam integer LO = dsl * DS;
        localparam integer HI = ((dsl + 1) * DS > NL * 32) ? NL * 32 : (dsl + 1) * DS;
        if (LO < NL * 32) begin : g_on
            wire [SB-1:0] own_c;
            ot_gpu_kreg_oh #(.W(SB), .RV({SB{1'b0}})) u_own (.clk(clk), .rst_n(rst_n), .d(own_n), .q(own_c));
            // Equalities are mutually exclusive; the explicit tree preserves bit order.
            localparam integer LEAVES = 1 << SB;
            (* keep = 1 *) wire [HI-LO-1:0] nodes [1:2*LEAVES-1];
            for(genvar q=0;q<LEAVES;q=q+1)begin:g_leaf
                if(q<NSM)begin:g_valid
                    // Actual sm0..7,16..23 are west; sm8..15,24..31 east.
                    // Boolean select changes physical grouping only, never arbitration.
                    localparam integer SOURCE = NSM==32 ? (q<8 ? q : q<16 ? q+8 : q<24 ? q-8 : q) : q;
                    (* keep = 1 *) wire match_owner = own_c == SOURCE;
                    assign nodes[LEAVES+q] = s_data[SOURCE*NL*32+LO+:HI-LO] & {(HI-LO){match_owner}};
                end else begin:g_pad
                    assign nodes[LEAVES+q]='0;
                end
            end
            for(genvar q=1;q<LEAVES;q=q+1)begin:g_merge
                assign nodes[q]=nodes[2*q] | nodes[2*q+1];
            end
            assign m_data[HI-1:LO] = nodes[1];
        end
    end
    genvar s;
    for (s = 0; s < NSM; s = s + 1) begin : g_s
        assign s_req_rdy[s] = busy && !sent && (own == s) && m_req_rdy;
        assign s_rsp_v[s] = busy && sent && (own == s) && m_rsp_v;
    end
    assign s_rsp_data = m_rsp_data;
    assign m_rsp_rdy = busy && sent && s_rsp_rdy[own];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin busy <= 1'b0; sent <= 1'b0; own <= {SB{1'b0}}; end
        else begin
            if (!busy && any) begin busy <= 1'b1; sent <= 1'b0; own <= sel; end
            else if (busy && !sent && m_req_v && m_req_rdy) sent <= 1'b1;
            else if (busy && sent && m_rsp_v && m_rsp_rdy) begin busy <= 1'b0; sent <= 1'b0; end
        end
    end
end endgenerate
endmodule
