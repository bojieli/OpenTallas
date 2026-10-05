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
    output reg                  o_valid,
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
    // output: a 4-entry FIFO; the control decides a drain two cycles before it lands here, so it
    // drains only while at most one entry is held (this one + two in flight fit)
    reg [15:0]       f_kv  [0:3];
    reg [16*544-1:0] f_key [0:3];
    reg [2*LBW-1:0]  f_blk [0:3];
    reg [1:0]        f_wp, f_rp;
    reg [2:0]        f_n;
    reg [2:0] reserved,reserved_n;reg ready_q;
    wire state_ok=(reserved==~reserved_n)&&(reserved<=4);
    wire pop=o_valid&&o_ready;
    wire [3:0] next_reserved={1'b0,reserved}+(reserve?4'd1:4'd0)-(pop?4'd1:4'd0);
    reg reservation_fault;
    assign fault=reservation_fault;
    assign dr_ready=ready_q&&state_ok&&!reservation_fault;
    always @(posedge clk)begin
        if(!rst_n)begin reserved<=0;reserved_n<=3'b111;ready_q<=1;reservation_fault<=0;end
        else begin
            if(!state_ok||next_reserved>4||(pop&&reserved==0))reservation_fault<=1;
            else begin reserved<=next_reserved[2:0];reserved_n<=~next_reserved[2:0];ready_q<=(next_reserved<4);end
        end
    end
    always @* begin
        o_valid = (f_n != 0);
        o_kv = f_kv[f_rp]; o_key = f_key[f_rp]; o_blk = f_blk[f_rp];
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
    always @(posedge clk) begin
        if (!rst_n) begin f_wp <= 0; f_rp <= 0; f_n <= 0; end
        else begin
            if (dr_v != 2'b00) begin
                f_kv[f_wp] <= g_kv; f_key[f_wp] <= g_key; f_blk[f_wp] <= dr_blk; f_wp <= f_wp + 1'b1;
            end
            if (o_valid && o_ready) f_rp <= f_rp + 1'b1;
            f_n <= f_n + ((dr_v != 2'b00) ? 3'd1 : 3'd0) - ((o_valid && o_ready) ? 3'd1 : 3'd0);
        end
    end
endmodule