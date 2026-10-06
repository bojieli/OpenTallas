module ot_dsrom_reindex_kgdata_parent #(
    parameter integer NPC  = 32,
    parameter integer WB   = 128,
    parameter integer TAGW = 16,
    parameter integer BEATW = 4,
    parameter integer DW   = 256,
    parameter integer LBW  = 14
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input wire reserve,
    output wire fault,
    input  wire [NPC-1:0]       rsp_v,
    input  wire [NPC*TAGW-1:0]  rsp_tag,
    input  wire [NPC*BEATW-1:0] rsp_beat,
    input  wire [NPC*DW-1:0]    rsp_data,
    input  wire [1:0]           dr_v,
    input  wire [$clog2(WB)-1:0] dr_slot,
    input  wire [2*7-1:0]       dr_j,
    input  wire [2*5-1:0]       dr_fc,
    input  wire [2*5-1:0]       dr_f0,
    input  wire [2*LBW-1:0]     dr_blk,
    output wire                 dr_ready,
    output wire                 o_valid,
    input  wire                 o_ready,
    output reg  [15:0]          o_kv,
    output reg  [16*544-1:0]    o_key,
    output reg  [2*LBW-1:0]     o_blk
);
    localparam integer SW = $clog2(WB);
    reg [DW-1:0] code_mem  [0:NPC*WB*4-1];
    reg [DW-1:0] scale_mem [0:NPC*WB-1];
    integer p, b, k;
    always @(posedge clk)
        for (p = 0; p < NPC; p = p + 1)
            if (rsp_v[p]) begin
                if (rsp_tag[p*TAGW + SW])
                    scale_mem[p * WB + rsp_tag[p*TAGW +: SW]] <= rsp_data[p*DW +: DW];
                else
                    code_mem[(p * WB + rsp_tag[p*TAGW +: SW]) * 4 + rsp_beat[p*BEATW +: 2]] <= rsp_data[p*DW +: DW];
            end
    reg [16*544-1:0] f_key[0:3];
    wire [1:0] f_wp,f_rp;
    wire [70:0] header;
    ot_dsrom_reindex_drain_queue u_queue(
        .clk(clk),.rst_n(rst_n),.reserve(reserve),.in_valid(|dr_v),
        .in_data({dr_v,dr_slot,dr_j,dr_fc,dr_f0,dr_blk}),
        .write_address(f_wp),.read_address(f_rp),.ready(dr_ready),
        .out_valid(o_valid),.out_ready(o_ready),.out_data(header),.fault(fault));
    always @*begin
        o_kv={{8{header[70]}},{8{header[69]}}};
        o_key=f_key[f_rp];o_blk=header[27:0];
    end
    reg [15:0]     g_kv;
    reg [16*544-1:0] g_key;
    reg [4:0]      col, bank, sb;
    reg [SW-1:0]   slot;
    always @* begin
        g_kv = 0; g_key = 0;
        for (b = 0; b < 2; b = b + 1) begin
            slot = dr_slot + SW'(b);
            sb = dr_j[7*b+2 +: 5] ^ dr_f0[5*b +: 5];
            for (k = 0; k < 8; k = k + 1) begin
                col = {dr_j[7*b +: 3], 2'b00} + 5'(k / 2);
                bank = col ^ dr_fc[5*b +: 5];
                g_kv[8*b + k] = dr_v[b];
                if (dr_v[b])
                    g_key[(8*b + k)*544 +: 544] = {scale_mem[sb * WB + slot][32*k +: 32],
                                                   code_mem[(bank * WB + slot) * 4 + 2 * (k % 2) + 1],
                                                   code_mem[(bank * WB + slot) * 4 + 2 * (k % 2)]};
            end
        end
    end
    always @(posedge clk) if(rst_n && dr_v!=0 && !fault) f_key[f_wp]<=g_key;
endmodule
