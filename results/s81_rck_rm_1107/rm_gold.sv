module rm_gold (
    input  wire          wclk, wrst_n,
    input  wire          w_v,
    input  wire [511:0]  w_d,
    input  wire          rclk, rrst_n,
    output reg  [511:0]  r_d,
    output wire          fault
);
    reg  [511:0] mem [0:7];
    reg  [3:0] wp, rp, wp_g, rp_g;
    reg  [3:0] rp_g1, rp_g2, wp_g1, wp_g2;
    function automatic [3:0] g2b(input [3:0] g); begin g2b = {g[3], g[3]^g[2], g[3]^g[2]^g[1], g[3]^g[2]^g[1]^g[0]}; end endfunction
    always @(posedge wclk or negedge wrst_n) if (!wrst_n) begin rp_g1 <= 0; rp_g2 <= 0; end else begin rp_g1 <= rp_g; rp_g2 <= rp_g1; end
    always @(posedge rclk or negedge rrst_n) if (!rrst_n) begin wp_g1 <= 0; wp_g2 <= 0; end else begin wp_g1 <= wp_g; wp_g2 <= wp_g1; end
    wire [3:0] fill_w = wp - g2b(rp_g2);
    wire idle = w_d[1] && !w_d[0];
    wire full = fill_w == 4'd8;
    wire push = w_v && !full && !(idle && fill_w >= 4'd6);
    reg flt;
    // S81-RCK-4 11-07 OT_S81_RM_STAGED: rate matcher form for the 2.9-mm serdes types (class: one enable/select across
    // 4096 mem bits, one reset to 512 flops; TT rp->r_d -300..-872, rp_g2->mem -99..-239).
    //  write: push decided as before; data + per-slice one-hot write enables take one wclk stage, mem written one wclk
    //    later.  wp/wp_g move on the old edge; the reader sees wp_g two rclk later and reads on the third: no PIN CYCLE.
    //  read:  r_m = mux stage beside mem; r_d = free stage for the hop to the output face: +1 rclk PIN CYCLE on r_d.
    //  r_m/r_d carry no reset: pointers reset => empty => IDLE after 2 rclk edges (reset low >= 64 clk, boot contract).
    localparam integer RM_NS = 8;           // write-enable copies: one per 64-bit slice
    reg  [511:0] w_dq;
    (* keep *) reg [7:0] we_q [0:RM_NS-1];
    integer rm_i, rm_j;
    reg  [511:0] r_m;
    reg  [511:0] mem_rd;
    always @(posedge wclk) w_dq <= w_d;
    always @(posedge wclk or negedge wrst_n)
        if (!wrst_n) for (rm_i = 0; rm_i < RM_NS; rm_i = rm_i + 1) we_q[rm_i] <= 8'd0;
        else for (rm_i = 0; rm_i < RM_NS; rm_i = rm_i + 1) we_q[rm_i] <= push ? (8'd1 << wp[2:0]) : 8'd0;
    always @(posedge wclk)
        for (rm_i = 0; rm_i < RM_NS; rm_i = rm_i + 1)
            for (rm_j = 0; rm_j < 8; rm_j = rm_j + 1)
                if (we_q[rm_i][rm_j]) mem[rm_j][rm_i*64 +: 64] <= w_dq[rm_i*64 +: 64];
    always @(posedge wclk or negedge wrst_n)
        if (!wrst_n) begin wp <= 0; wp_g <= 0; flt <= 1'b0; end
        else begin
            if (push) begin wp <= wp + 1'b1; wp_g <= (wp + 1'b1) ^ ((wp + 1'b1) >> 1); end
            if (w_v && full && !idle) flt <= 1'b1;
        end
    wire empty = g2b(wp_g2) == rp;
    always @(posedge rclk or negedge rrst_n)
        if (!rrst_n) begin rp <= 0; rp_g <= 0; end
        else if (!empty) begin rp <= rp + 1'b1; rp_g <= (rp + 1'b1) ^ ((rp + 1'b1) >> 1); end
    always @(posedge rclk) begin
        r_m <= empty ? 512'd2 : mem[rp[2:0]];
        r_d <= r_m;
    end
    reg f1, f2; always @(posedge rclk or negedge rrst_n) if (!rrst_n) begin f1 <= 0; f2 <= 0; end else begin f1 <= flt; f2 <= f1; end
    assign fault = f2;
endmodule
