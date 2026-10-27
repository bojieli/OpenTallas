module ep_rx_gate #(parameter integer MUT = 0) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [511:0] beat,           // pin register (from hfd_ep_static)
    input  wire [7:0]   data_r,         // replicated pin-register copies of !beat[1] (one per 64-b slice of pg)
    output reg          f_v,            // registered
    output reg  [611:0] f_d,
    output reg          locked,
    output reg          lock_lost       // sticky: lock dropped after it was acquired
);
    // Physical structure: the slot select is a per-slice replicated one-hot phase register (keep); pg loads under a
    // replicated copy of the pin register's data bit; f_d loads every edge (f_v qualifies it), so no enable net.
    localparam integer SL = 64, NSL = (613 + SL - 1) / SL;
    wire data = (MUT == 2) ? 1'b1 : !beat[1];
    wire mk = beat[0];
    wire [509:0] gcur = beat[511:2];
    reg [509:0] pg;
    reg [2:0] ph, cnt;
    reg seen;
    (* keep *) reg [NSL*4-1:0] oh;      // per slice: phase 1..4 one-hot (phase 0 = all zero)
    reg [612:0] slot;
    reg [2:0] ph_n; reg lk_n;
    integer s, j, k;
    always @(*) begin
        for (j = 0; j < 613; j = j + 1) begin
            s = j / SL;
            slot[j] = (oh[s*4+0] & ((MUT == 3) ? (j < 103 ? pg[j] : gcur[j - 103]) : (j < 510 ? pg[j] : gcur[j - 510])))
                    | (oh[s*4+1] & (j < 407 ? pg[103 + j] : gcur[j - 407]))
                    | (oh[s*4+2] & (j < 304 ? pg[206 + j] : gcur[j - 304]))
                    | (oh[s*4+3] & (j < 201 ? pg[309 + j] : gcur[j - 201]));
        end
    end
    // next lock state / phase (control only)
    always @(*) begin
        ph_n = ph; lk_n = locked;
        if (data) begin
            if (!locked) begin
                if (mk && seen && cnt == 3'd4) begin lk_n = 1'b1; ph_n = 3'd1; end
            end else if ((ph == 3'd0) != mk) begin
                lk_n = 1'b0; ph_n = 3'd0;
            end else ph_n = (ph == 3'd4) ? 3'd0 : ph + 3'd1;
        end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            locked <= 1'b0; lock_lost <= 1'b0; ph <= 3'd0; cnt <= 3'd0; seen <= 1'b0; f_v <= 1'b0; oh <= {(NSL*4){1'b0}};
        end else begin
            f_v <= data && locked && ((ph == 3'd0) == mk) && ph != 3'd0 && slot[0];
            ph <= ph_n; locked <= lk_n;
            oh <= {NSL{(lk_n && ph_n != 3'd0) ? (4'b0001 << (ph_n - 3'd1)) : 4'b0000}};
            if (data) begin
                if (!locked) begin
                    if (mk) begin seen <= 1'b1; cnt <= 3'd0; end
                    else if (cnt != 3'd7) cnt <= cnt + 3'd1;
                end else if ((ph == 3'd0) != mk) begin
                    lock_lost <= 1'b1; seen <= mk; cnt <= 3'd0;
                end
            end
        end
    always @(posedge clk) begin
        for (k = 0; k < 510; k = k + 1) if ((MUT == 2) ? 1'b1 : data_r[k / SL]) pg[k] <= gcur[k];
        f_d <= slot[612:1];
    end
endmodule
