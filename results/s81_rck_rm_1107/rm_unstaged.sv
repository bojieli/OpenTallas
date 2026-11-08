module rm_unstaged (
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
    wire [3:0] rp_to_write = rp_g;
    always @(posedge wclk or negedge wrst_n) if (!wrst_n) begin rp_g1 <= 0; rp_g2 <= 0; end else begin rp_g1 <= rp_to_write; rp_g2 <= rp_g1; end
    wire [3:0] wp_to_read = wp_g;
    always @(posedge rclk or negedge rrst_n) if (!rrst_n) begin wp_g1 <= 0; wp_g2 <= 0; end else begin wp_g1 <= wp_to_read; wp_g2 <= wp_g1; end
    wire [3:0] fill_w = wp - g2b(rp_g2);
    wire idle = w_d[1] && !w_d[0];
    wire full = fill_w == 4'd8;
    wire push = w_v && !full && !(idle && fill_w >= 4'd6);
    reg flt;
    always @(posedge wclk or negedge wrst_n)
        if (!wrst_n) begin wp <= 0; wp_g <= 0; flt <= 1'b0; end
        else begin
            if (push) begin mem[wp[2:0]] <= w_d; wp <= wp + 1'b1; wp_g <= (wp + 1'b1) ^ ((wp + 1'b1) >> 1); end
            if (w_v && full && !idle) flt <= 1'b1;
        end
    wire empty = g2b(wp_g2) == rp;
    always @(posedge rclk or negedge rrst_n)
        if (!rrst_n) begin rp <= 0; rp_g <= 0; r_d <= 512'd2; end
        else if (!empty) begin r_d <= mem[rp[2:0]]; rp <= rp + 1'b1; rp_g <= (rp + 1'b1) ^ ((rp + 1'b1) >> 1); end
        else r_d <= 512'd2;                        // IDLE beat: bit 1 set, no marker, no reverse frame, no slot bits
    reg f1, f2; always @(posedge rclk or negedge rrst_n) if (!rrst_n) begin f1 <= 0; f2 <= 0; end else begin f1 <= flt; f2 <= f1; end
    assign fault = f2;
endmodule
