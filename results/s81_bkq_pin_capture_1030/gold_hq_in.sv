module gold_hq_in (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [514:0] lane,
    output reg          b_v,
    output reg  [15:0]  b_lv,
    output reg  [255:0] b_val,
    output reg  [319:0] b_idx,
    output reg          b_last,
    output reg          h_v,
    output reg  [9:0]   h_k,
    output reg  [7:0]   h_tag,
    output reg  [1:0]   h_q,
    output reg          act,
    output reg  [1:0]   act_q,
    output reg          e_fmt,
    output reg          e_orphan,
    output reg          e_link
);
    localparam integer DW = 482;
    localparam integer UW = DW + 15;
    wire [UW-1:0] u = {lane[514], lane[513], lane[512:501], lane[DW:1], lane[0]};
    reg  [UW-1:0] s0;
    always @(posedge clk) s0 <= u;
    // kept copy of {type, valid} for the position next state (cur_n): the case decode keeps s0's own bits
    (* keep = "true" *) reg [4:0] s0c, s0d;           // one per half of cur
    always @(posedge clk) begin s0c <= {lane[512:509], lane[0]}; s0d <= {lane[512:509], lane[0]}; end
    // type-8 select copies: 13 lanes x {val lo 8, val hi 8, idx lo 10, idx hi 10} + {lv/last} = 53 copies over four
    // decodes (<= 14 each)
`ifdef OT_S81PH_HQ_INPUT_RAW
    // Structural successor: land raw type bits at the existing first edge;
    // decode locally at the existing second-stage payload mux. Four-select groups
    // keep each type bit below32 loads, with zero additional pipeline edges.
    localparam integer NF = 53, NT = 14;
    (* keep = "true" *) reg [4*NT-1:0] raw_type;
`ifdef OT_S81PH_HQ_INPUT_RAW_MUT
    reg [3:0] raw_type_prev;
    always @(posedge clk) raw_type_prev <= lane[512:509];
`endif
    genvar rt;
    generate for (rt = 0; rt < NT; rt = rt + 1) begin : g_raw_type
        always @(posedge clk) begin
`ifdef OT_S81PH_HQ_INPUT_RAW_MUT
            if (`OT_S81PH_HQ_INPUT_RAW_MUT == 2) raw_type[4*rt +: 4] <= raw_type_prev;
            else
`endif
                raw_type[4*rt +: 4] <= lane[512:509];
        end
    end endgenerate
    wire [NF-1:0] f;
    genvar fs;
    generate for (fs = 0; fs < NF; fs = fs + 1) begin : g_f
        wire [3:0] t = raw_type[4*(fs / 4) +: 4];
        wire [3:0] dec = {t[3] & ~t[1] & ~t[0],
                          t[3] & ~t[2] & ~t[0],
                          t[3] & ~t[2] & ~t[1],
                          t == 4'd8};
`ifdef OT_S81PH_HQ_INPUT_RAW_MUT
        assign f[fs] = (`OT_S81PH_HQ_INPUT_RAW_MUT == 1) ? ~dec[fs % 4] : dec[fs % 4];
`else
        assign f[fs] = dec[fs % 4];
`endif
    end endgenerate
`else
    wire [3:0] t = lane[512:509];
    wire [3:0] dec = {t[3] & ~t[1] & ~t[0],             // {8, 12}
                      t[3] & ~t[2] & ~t[0],             // {8, 10}
                      t[3] & ~t[2] & ~t[1],             // {8, 9}
                      t == 4'd8};
    localparam integer NF = 53;
    wire [NF-1:0] f;
    genvar fs;
    generate for (fs = 0; fs < NF; fs = fs + 1) begin : g_f
        (* keep = "true" *) reg r;
        always @(posedge clk) r <= dec[fs % 4];
        assign f[fs] = r;
    end endgenerate
`endif
    wire          v   = s0[0];
    wire [481:0]  d   = s0[DW:1];
    wire [7:0]    tag = s0[DW+8:DW+1];
    wire [3:0]    t4  = s0[DW+12:DW+9];
    reg  [19:0]   cur;
    wire [20:0]   nxt = {1'b0, cur} + 21'd16;
    // position next state (the original update rule) and its kept copies (index adders, 4 lanes each)
    wire [19:0]   cur_n;
    assign cur_n[9:0]   = !s0c[0] ? cur[9:0] : (s0c[4:1] == 4'd1 || s0c[4:1] == 4'd6) ? d[9:0] :
                          (s0c[4:1] == 4'd2 && act) ? nxt[9:0] : cur[9:0];
    assign cur_n[19:10] = !s0d[0] ? cur[19:10] : (s0d[4:1] == 4'd1 || s0d[4:1] == 4'd6) ? d[19:10] :
                          (s0d[4:1] == 4'd2 && act) ? nxt[19:10] : cur[19:10];
    wire [4*20-1:0] curc;
    generate for (fs = 0; fs < 4; fs = fs + 1) begin : g_cur
        (* keep = "true" *) reg [19:0] r;
        always @(posedge clk or negedge rst_n) if (!rst_n) r <= 20'd0; else r <= cur_n;
        assign curc[20*fs +: 20] = r;
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            b_v <= 1'b0; h_v <= 1'b0; act <= 1'b0; act_q <= 2'd0; cur <= 20'd0;
            e_fmt <= 1'b0; e_orphan <= 1'b0; e_link <= 1'b0;
        end else begin
            b_v <= 1'b0; h_v <= 1'b0; e_fmt <= 1'b0; e_orphan <= 1'b0;
            e_link <= s0[UW-1] | (v & ~s0[UW-2]);
            cur <= cur_n;
            if (v) begin
                case (t4)
                    4'd1: begin h_v <= 1'b1; act <= 1'b1; act_q <= d[31:30]; end
                    4'd6: begin if (!act) e_orphan <= 1'b1; end
                    4'd8: begin
                        if (!act) e_orphan <= 1'b1;
                        else begin b_v <= 1'b1; if (d[481]) act <= 1'b0; end
                    end
                    4'd2: begin
                        if (!act) e_orphan <= 1'b1;
                        else begin
                            b_v <= 1'b1;
                            if (nxt[20] && !d[272]) e_fmt <= 1'b1;
                            if (d[272]) act <= 1'b0;
                        end
                    end
                    default: e_fmt <= 1'b1;
                endcase
            end
        end
    end
    integer l;
    always @(posedge clk) begin
        b_lv   <= f[52] ? {3'b000, d[480:468]} : d[271:256];
        b_last <= f[52] ? d[481] : d[272];
        for (l = 0; l < 16; l = l + 1) begin
            if (l < 13) begin
                b_val[16*l +: 8]      <= f[4*l + 0] ? d[36*l +: 8]        : d[16*l +: 8];
                b_val[16*l + 8 +: 8]  <= f[4*l + 1] ? d[36*l + 8 +: 8]    : d[16*l + 8 +: 8];
                b_idx[20*l +: 10]     <= f[4*l + 2] ? d[36*l + 16 +: 10]  : 10'(curc[20*(l/4) +: 20] + l[19:0]);
                b_idx[20*l + 10 +: 10] <= f[4*l + 3] ? d[36*l + 26 +: 10] : 10'((curc[20*(l/4) +: 20] + l[19:0]) >> 10);
            end else begin
                b_val[16*l +: 16] <= d[16*l +: 16];
                b_idx[20*l +: 20] <= curc[20*(l/4) +: 20] + l[19:0];
            end
        end
        h_k <= d[29:20];
        h_tag <= tag;
        h_q <= d[31:30];
    end
endmodule
