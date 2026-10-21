// Exact baseline tr_x module, name-only substitution.
module ot_hdc_v41x_attn_tr_x_ref #(
    parameter integer TD = 64,
    parameter integer DPT = 16,
    parameter integer NL = 4,
    parameter integer XOFF = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              w_en_i,
    input  wire              w_half_i,
    input  wire [7:0]        w_cnt_i,
    input  wire [NL-1:0]     w_pad_i,
    input  wire [NL*265-1:0] w_g,
    input  wire              r_half_i,
    input  wire [7:0]        r_c_i,
    input  wire              sel_i,
    input  wire [TD*18-1:0]  qk_ib,
    output wire [TD*18-1:0]  col,
    output wire [TD*18-1:0]  eib
);
    localparam integer GW = 265;
    localparam integer NS = 2 * DPT;          // read positions (half, dim)
    localparam integer NR = 2 * TD;           // stored rows (half, row)
    function automatic [17:0] elem(input [GW-1:0] gw, input integer x, input pad);
        begin
            if (gw[264]) elem = {pad, 1'b1, 4'd0, gw[4*x +: 4], gw[128 + 8*(x/16) +: 8]};
            else         elem = {pad, 1'b0, gw[8*x +: 8], gw[263:256]};
        end
    endfunction
    // one-hot read position and write row, from the controller's values (registered below, as tr's rb_t/rc_t/fc_t)
    wire [NS-1:0] rsel_c;
    wire [NR-1:0] wrow_c;
    genvar gs, gr, gx;
    generate
        for (gs = 0; gs < NS; gs = gs + 1) begin : g_rs
            assign rsel_c[gs] = (r_half_i == (gs / DPT)) && (r_c_i == (gs % DPT));
        end
        for (gr = 0; gr < NR; gr = gr + 1) begin : g_ws
            assign wrow_c[gr] = w_en_i && (w_half_i == (gr / TD)) && (w_cnt_i == ((gr % TD) / NL));
        end
    endgenerate
    reg [NL-1:0] fp_t;
    always @(posedge clk) fp_t <= w_pad_i;
    reg [17:0] tr [0:NR*DPT-1];
    generate
        // writes: row gr (half gr/TD, row gr%TD) takes lane r = gr % NL of the fill word
        for (gr = 0; gr < NR; gr = gr + 1) begin : g_w
            wire we;
            ot_hdc_v41x_kreg #(.W(1), .R(1)) u_we (.clk(clk), .rst_n(rst_n), .d(wrow_c[gr]), .q(we));
            for (gx = 0; gx < DPT; gx = gx + 1) begin : g_x
                always @(posedge clk)
                    if (we) tr[gr * DPT + gx] <= elem(w_g[(gr % NL)*GW +: GW], XOFF + gx, fp_t[gr % NL]);
            end
        end
        // reads: element gs selects position (half, dim) with its own one-hot copy
        for (gs = 0; gs < TD; gs = gs + 1) begin : g_c
            wire [NS-1:0] oh;
            wire          sel;
            ot_hdc_v41x_kreg #(.W(NS), .R(0)) u_rs (.clk(clk), .rst_n(rst_n), .d(rsel_c), .q(oh));
            ot_hdc_v41x_kreg #(.W(1), .R(1)) u_sl (.clk(clk), .rst_n(rst_n), .d(sel_i), .q(sel));
            reg [17:0] v;
            integer k;
            always @* begin
                v = 18'd0;
                for (k = 0; k < NS; k = k + 1)
                    v = v | ({18{oh[k]}} & tr[((k / DPT) * TD + gs) * DPT + (k % DPT)]);
            end
            assign col[gs*18 +: 18] = v;
            reg [17:0] e;
            always @(posedge clk) e <= sel ? v : qk_ib[gs*18 +: 18];
            assign eib[gs*18 +: 18] = e;
        end
    endgenerate
endmodule
