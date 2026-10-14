(* keep_hierarchy = "yes" *)
module dsfd_vm_be_kreg #(parameter integer W = 1, parameter integer ID = 0) (input wire clk, input wire [W-1:0] d, output reg [W-1:0] q);
    always @(posedge clk) q <= d;
endmodule

module dsfd_vm_be_rcdc #(
    parameter integer W = 128, parameter integer DEPTH = 8, parameter integer HOLD = 2, parameter integer NC = 2,
    parameter integer IDB = 0
) (
`ifdef OT_BE_RCDC_GRAY
    input wire raw_epoch_n,
`endif
    input  wire          wclk, wrst_n, w_v,
    output wire          w_rdy,
    input  wire [W-1:0]  w_d,
    input  wire          rclk, rrst_n,
    output wire          r_v,
    input  wire          r_rdy,
    output reg           o_v,
    output wire [W-1:0]  o_d,
    output wire [NC-1:0] o_vc
`ifdef OT_BE_RCDC_GRAY
    ,output wire reset_ack_w, reset_ack_r
`endif
);
`ifdef OT_BE_RCDC_GRAY
    wire qv;
    dsfd_vm_be_rcdc_gray #(.W(W),.DEPTH(DEPTH),.HOLD(HOLD),.NC(NC),.IDB(IDB)) u_gray
      (.raw_epoch_n(raw_epoch_n),.wclk(wclk),.wrst_n(wrst_n),.w_v(w_v),.w_rdy(w_rdy),.w_d(w_d),
       .rclk(rclk),.rrst_n(rrst_n),.r_v(r_v),.r_rdy(r_rdy),.o_v(qv),.o_d(o_d),.o_vc(o_vc),.reset_ack_w(reset_ack_w),.reset_ack_r(reset_ack_r));
    always @* o_v=qv;
`else
    localparam integer AW = $clog2(DEPTH);
    localparam integer CW = $clog2(HOLD + 1);
    localparam integer CB = W / NC;
    localparam [1:0] S_DOWN = 2'b00, S_WAIT = 2'b01, S_RUN = 2'b10;
    localparam [AW:0] DP = DEPTH;
    localparam [CW-1:0] HL = HOLD;
    reg [AW:0]   wp, wp_pub, rp_w, rp, wp_r;
    reg [1:0]    w_st, r_st_w, r_st, w_st_r;
    reg [CW-1:0] w_cnt, r_cnt;
    reg          w_ok, r_ok;
    always @(posedge wclk) begin rp_w <= rp; r_st_w <= r_st; end
    wire w_live = (w_st == S_RUN) && (r_st_w != S_DOWN);
    assign w_rdy = wrst_n && w_live && ((wp - rp_w) != DP);
    wire w_fire = w_v && w_rdy;
    reg [AW:0] wp_nx;
    always @* begin
        wp_nx = wp;
        if (!wrst_n) wp_nx = {(AW+1){1'b0}};
        else case (w_st)
            S_DOWN, S_WAIT: wp_nx = {(AW+1){1'b0}};
            default: if (r_st_w == S_DOWN) wp_nx = {(AW+1){1'b0}}; else if (w_fire) wp_nx = wp + 1'b1;
        endcase
    end
    always @(posedge wclk) begin
        wp <= wp_nx;
        wp_pub <= wp;                       // LAG 1
        if (!wrst_n) begin
            w_st <= S_DOWN; w_cnt <= HL; w_ok <= 1'b0;
        end else begin
            case (w_st)
                S_DOWN: begin
                    if (r_st_w != S_RUN) w_ok <= 1'b1;
                    if (w_cnt != {CW{1'b0}}) w_cnt <= w_cnt - 1'b1;
                    else if (w_ok || r_st_w != S_RUN) w_st <= S_WAIT;
                end
                S_WAIT: if (r_st_w != S_DOWN) w_st <= S_RUN;
                default: if (r_st_w == S_DOWN) begin w_st <= S_DOWN; w_cnt <= HL; w_ok <= 1'b1; end
            endcase
        end
    end
    always @(posedge rclk) begin wp_r <= wp_pub; w_st_r <= w_st; end
    wire r_live = (r_st == S_RUN) && (w_st_r != S_DOWN);
    assign r_v = rrst_n && r_live && (wp_r != rp);
    wire r_take = r_v && r_rdy;
    reg [AW:0] rp_nx;
    always @* begin
        rp_nx = rp;
        if (!rrst_n) rp_nx = {(AW+1){1'b0}};
        else case (r_st)
            S_DOWN, S_WAIT: rp_nx = {(AW+1){1'b0}};
            default: if (w_st_r == S_DOWN) rp_nx = {(AW+1){1'b0}}; else if (r_take) rp_nx = rp + 1'b1;
        endcase
    end
    always @(posedge rclk) begin
        rp <= rp_nx;
        o_v <= r_take;
        if (!rrst_n) begin
            r_st <= S_DOWN; r_cnt <= HL; r_ok <= 1'b0;
        end else begin
            case (r_st)
                S_DOWN: begin
                    if (w_st_r != S_RUN) r_ok <= 1'b1;
                    if (r_cnt != {CW{1'b0}}) r_cnt <= r_cnt - 1'b1;
                    else if (r_ok || w_st_r != S_RUN) r_st <= S_WAIT;
                end
                S_WAIT: if (w_st_r != S_DOWN) r_st <= S_RUN;
                default: if (w_st_r == S_DOWN) begin r_st <= S_DOWN; r_cnt <= HL; r_ok <= 1'b1; end
            endcase
        end
    end
    wire [DEPTH-1:0] oh_nx = {{(DEPTH-1){1'b0}}, 1'b1} << rp_nx[AW-1:0];
    wire [DEPTH-1:0] woh_nx = {{(DEPTH-1){1'b0}}, 1'b1} << wp_nx[AW-1:0];
    genvar c;
    generate for (c = 0; c < NC; c = c + 1) begin : g_c
        wire [DEPTH-1:0] oh, woh;
        dsfd_vm_be_kreg #(.W(DEPTH), .ID(IDB + c)) u_oh (.clk(rclk), .d(oh_nx), .q(oh));
        dsfd_vm_be_kreg #(.W(1), .ID(IDB + NC + c)) u_vc (.clk(rclk), .d(r_take), .q(o_vc[c]));
        dsfd_vm_be_kreg #(.W(DEPTH), .ID(IDB + 2*NC + c)) u_woh (.clk(wclk), .d(woh_nx), .q(woh));
        reg [CB-1:0] mem [0:DEPTH-1]; reg [CB-1:0] sh [0:DEPTH-1];
        always @(posedge wclk) begin : p_w integer i;
            for (i = 0; i < DEPTH; i = i + 1) if (w_fire && woh[i]) mem[i] <= w_d[c*CB +: CB];
        end
        always @(posedge rclk) begin : p_sh integer i;
            for (i = 0; i < DEPTH; i = i + 1) sh[i] <= mem[i];
        end
        reg [CB-1:0] od;
        always @(posedge rclk) begin : p_od integer i; reg [CB-1:0] a;
            a = {CB{1'b0}};
            for (i = 0; i < DEPTH; i = i + 1) a = a | (sh[i] & {CB{oh[i]}});
            od <= a;
        end
        assign o_d[c*CB +: CB] = od;
    end endgenerate
`endif
endmodule

module dsfd_vm_be_rcdc_gray #(
    parameter integer W = 128, parameter integer DEPTH = 8, parameter integer HOLD = 2, parameter integer NC = 2,
    parameter integer IDB = 0
) (
    input wire raw_epoch_n,
    input wire wclk, wrst_n, w_v,
    output wire          w_rdy,
    input  wire [W-1:0]  w_d,
    input  wire          rclk, rrst_n,
    output wire          r_v,
    input  wire          r_rdy,
    output reg           o_v,
    output wire [W-1:0]  o_d,
    output wire [NC-1:0] o_vc
    ,output wire reset_ack_w, reset_ack_r
);
    initial if (DEPTH < 4 || (DEPTH & (DEPTH-1)) != 0 || W % NC != 0) $error("invalid gray CDC geometry");
    localparam integer AW = $clog2(DEPTH);
    localparam integer CW = $clog2(HOLD + 1);
    localparam integer CB = W / NC;
    localparam [1:0] S_DOWN = 2'b00, S_WAIT = 2'b01, S_RUN = 2'b11;
    localparam [AW:0] DP = DEPTH;
    localparam [CW-1:0] HL = HOLD;
    wire wn, rn;
`ifdef OT_BE_RCDC_MUT_MISS_EPOCH
    wire epoch_n=wrst_n && rrst_n;
`else
    wire epoch_n=raw_epoch_n;
`endif
    ot_reset_sync u_wrs (.clk(wclk), .async_rst_n(epoch_n), .sync_rst_n(wn));
    ot_reset_sync u_rrs (.clk(rclk), .async_rst_n(epoch_n), .sync_rst_n(rn));
    wire w_reset_n = wrst_n && wn, r_reset_n = rrst_n && rn;
    assign reset_ack_w=w_reset_n; assign reset_ack_r=r_reset_n;
    reg [AW:0] wp, rp, wp_gray_pub, rp_gray;
    (* async_reg = "true" *) reg [AW:0] rp_gw1, rp_gw2, wp_gr1, wp_gr2;
    (* async_reg = "true" *) reg rd_w1, rd_w2, rr_w1, rr_w2;
    (* async_reg = "true" *) reg wd_r1, wd_r2, wr_r1, wr_r2;
    // Cross independent one-bit registered down/run flags, never a binary state.
    // DOWN wins any temporary flag disagreement during an epoch transition.
    wire [1:0] r_st_w=rd_w2 ? S_DOWN : (rr_w2 ? S_RUN : S_WAIT);
    wire [1:0] w_st_r=wd_r2 ? S_DOWN : (wr_r2 ? S_RUN : S_WAIT);
    function automatic [AW:0] ungray(input [AW:0] g);
        integer j; begin ungray[AW]=g[AW]; for(j=AW-1;j>=0;j=j-1) ungray[j]=ungray[j+1]^g[j]; end
    endfunction
    wire [AW:0] rp_w=ungray(rp_gw2);
`ifdef OT_BE_RCDC_MUT_EARLY_PUB
    wire [AW:0] wp_r=ungray(wp_gr1);
`else
    wire [AW:0] wp_r=ungray(wp_gr2);
`endif
    reg [1:0] w_st, r_st;
    reg [CW-1:0] w_cnt, r_cnt;
    reg          w_ok, r_ok;
    always @(posedge wclk) begin
        if (!w_reset_n) begin rp_gw1<=0;rp_gw2<=0;rd_w1<=1;rd_w2<=1;rr_w1<=0;rr_w2<=0; end
        else begin rp_gw1<=rp_gray;rp_gw2<=rp_gw1;rd_w1<=!r_st[0];rd_w2<=rd_w1;rr_w1<=r_st[1];rr_w2<=rr_w1; end
    end
    wire w_live = (w_st == S_RUN) && (r_st_w != S_DOWN);
    assign w_rdy = w_reset_n && w_live && ((wp - rp_w) != DP);
    wire w_fire = w_v && w_rdy;
    reg [AW:0] wp_nx;
    always @* begin
        wp_nx = wp;
        if (!w_reset_n) wp_nx = {(AW+1){1'b0}};
        else case (w_st)
            S_DOWN, S_WAIT: wp_nx = {(AW+1){1'b0}};
            default: if (r_st_w == S_DOWN) wp_nx = {(AW+1){1'b0}}; else if (w_fire) wp_nx = wp + 1'b1;
        endcase
    end
    always @(posedge wclk) begin
        wp <= wp_nx;
        `ifdef OT_BE_RCDC_MUT_EARLY_PUB
        wp_gray_pub <= !w_reset_n ? 0 : ((wp_nx >> 1) ^ wp_nx);
`else
        wp_gray_pub <= !w_reset_n ? 0 : ((wp >> 1) ^ wp); // every accepted pointer, LAG1
`endif
        if (!w_reset_n) begin
            w_st <= S_DOWN; w_cnt <= HL; w_ok <= 1'b0;
        end else begin
            case (w_st)
                S_DOWN: begin
                    if (r_st_w != S_RUN) w_ok <= 1'b1;
                    if (w_cnt != {CW{1'b0}}) w_cnt <= w_cnt - 1'b1;
                    else if (w_ok || r_st_w != S_RUN) w_st <= S_WAIT;
                end
                S_WAIT: if (r_st_w != S_DOWN) w_st <= S_RUN;
                default: if (r_st_w == S_DOWN) begin w_st <= S_DOWN; w_cnt <= HL; w_ok <= 1'b1; end
            endcase
        end
    end
    always @(posedge rclk) begin
        if (!r_reset_n) begin wp_gr1<=0;wp_gr2<=0;wd_r1<=1;wd_r2<=1;wr_r1<=0;wr_r2<=0; end
        else begin wp_gr1<=wp_gray_pub;wp_gr2<=wp_gr1;wd_r1<=!w_st[0];wd_r2<=wd_r1;wr_r1<=w_st[1];wr_r2<=wr_r1; end
    end
    wire r_live = (r_st == S_RUN) && (w_st_r != S_DOWN);
    assign r_v = r_reset_n && r_live && (wp_r != rp);
    wire r_take = r_v && r_rdy;
    reg [AW:0] rp_nx;
    always @* begin
        rp_nx = rp;
        if (!r_reset_n) rp_nx = {(AW+1){1'b0}};
        else case (r_st)
            S_DOWN, S_WAIT: rp_nx = {(AW+1){1'b0}};
            default: if (w_st_r == S_DOWN) rp_nx = {(AW+1){1'b0}}; else if (r_take) rp_nx = rp + 1'b1;
        endcase
    end
    always @(posedge rclk) begin
        rp <= rp_nx; rp_gray <= (rp_nx >> 1) ^ rp_nx;
        o_v <= r_take;
        if (!r_reset_n) begin
            r_st <= S_DOWN; r_cnt <= HL; r_ok <= 1'b0;
        end else begin
            case (r_st)
                S_DOWN: begin
                    if (w_st_r != S_RUN) r_ok <= 1'b1;
                    if (r_cnt != {CW{1'b0}}) r_cnt <= r_cnt - 1'b1;
                    else if (r_ok || w_st_r != S_RUN) r_st <= S_WAIT;
                end
                S_WAIT: if (w_st_r != S_DOWN) r_st <= S_RUN;
                default: if (w_st_r == S_DOWN) begin r_st <= S_DOWN; r_cnt <= HL; r_ok <= 1'b1; end
            endcase
        end
    end
    wire [DEPTH-1:0] oh_nx = {{(DEPTH-1){1'b0}}, 1'b1} << rp_nx[AW-1:0];
    wire [DEPTH-1:0] woh_nx = {{(DEPTH-1){1'b0}}, 1'b1} << wp_nx[AW-1:0];
    genvar c;
    generate for (c = 0; c < NC; c = c + 1) begin : g_c
        wire [DEPTH-1:0] oh, woh;
        // Only published selected memory is captured; no speculative all-slot sampling.
        dsfd_vm_be_kreg #(.W(1), .ID(IDB + NC + c)) u_vc (.clk(rclk), .d(r_take), .q(o_vc[c]));
        dsfd_vm_be_kreg #(.W(DEPTH), .ID(IDB + 2*NC + c)) u_woh (.clk(wclk), .d(woh_nx), .q(woh));
        reg [CB-1:0] mem [0:DEPTH-1];
        always @(posedge wclk) begin : p_w integer i;
            for (i = 0; i < DEPTH; i = i + 1) if (w_fire && woh[i]) mem[i] <= w_d[c*CB +: CB];
        end
        reg [CB-1:0] od;
        always @(posedge rclk) begin
`ifdef OT_BE_RCDC_MUT_WRONG_ENTRY
            if (r_take) od <= mem[(rp[AW-1:0]+1'b1) & (DEPTH-1)];
`else
            if (r_take) od <= mem[rp[AW-1:0]];
`endif
        end
        assign o_d[c*CB +: CB] = od;
    end endgenerate
endmodule
