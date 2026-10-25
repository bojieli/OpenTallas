module dsdv_bk_selids #(
    parameter integer V   = 276,
    parameter integer EK  = 5,
    parameter integer UID = 8'h5C,
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst,       // active low
    input  wire [V-1:0]  vo,        // tap: u_sel.vo_s
    output reg  [V-1:0]  o,         // relay beat (0 = idle)
    output reg           fault
);
    reg [V-1:0] vr;
    always @(posedge ck or negedge rst) if (!rst) vr[0] <= 1'b0; else vr[0] <= vo[0];
    always @(posedge ck) vr[V-1:1] <= vo[V-1:1];
    wire [185:0] cp = vr[21 +: 186];
    wire jctl = vr[0] && vr[3:1] == 3'd0 && cp[7:0] == 8'(UID) && cp[10:8] == 3'd3;
    wire eg = vr[0] && vr[3:1] == 3'(EK);
    reg armed, e_h; reg [9:0] k_n, rk; reg [7:0] ot; reg [3:0] msk; reg [255:0] lo;
    wire [511:0] w = {vr[275:20], lo};
    wire wv = armed && eg && vr[6] && e_h && w[511:508] == 4'd3 && w[507:500] == ot;
    wire [15:0] lv = w[335:320];
    reg [4:0] cnt;
    always @* begin cnt = 5'd0; for (int i = 0; i < 16; i++) cnt = cnt + 5'(lv[i]); end
    wire pre = ((lv + 16'd1) & lv) == 16'd0;
    always @(posedge ck) if (eg && !vr[6]) lo <= vr[275:20];
    reg w1v; reg [V-1:0] b1;
    function automatic [V-1:0] beat(input [511:0] ww, input h, input [9:0] sf, input [4:0] sc, input [3:0] m);
        reg [V-1:0] b; integer e, l;
        b = '0; b[0] = 1'b1; b[12:9] = 4'hB; b[20:13] = 8'hA5;
        for (e = 0; e < 8; e = e + 1) begin
            l = 8 * h + e + ((MUT == 2) ? 1 : 0);
            if (8 * h + e < sc) b[21 + 21 * e +: 21] = (l < 16) ? {1'b0, ww[20 * l +: 20]} : 21'd0;
        end
        b[189] = h; b[199:190] = sf; b[204:200] = sc; b[208:205] = m;
        beat = b;
    endfunction
    always @(posedge ck or negedge rst)
        if (!rst) begin armed <= 1'b0; e_h <= 1'b0; rk <= 10'd0; fault <= 1'b0; w1v <= 1'b0; o[0] <= 1'b0; end
        else begin
            if (eg && !vr[6]) e_h <= 1'b1; else if (eg && vr[6]) e_h <= 1'b0;
            if (jctl) begin
                if (armed) fault <= 1'b1;                                       // a job while one is open
                armed <= cp[40:31] != 10'd0; rk <= 10'd0;
            end else if (wv) begin
                if (!pre || 11'(rk) + 11'(cnt) > 11'(k_n)) fault <= 1'b1;
                rk <= (MUT == 1) ? rk : rk + 10'(cnt);
                if (11'(rk) + 11'(cnt) >= 11'(k_n)) armed <= 1'b0;
            end
            o[0] <= (wv && cnt != 5'd0) | w1v; w1v <= wv && cnt != 5'd0;   // an empty word (lv 0) sends nothing
        end
    always @(posedge ck) begin
        if (jctl) begin k_n <= cp[40:31]; ot <= cp[68:61]; msk <= cp[72:69]; end
        if (wv) b1 <= beat(w, 1'b1, rk, cnt, msk);
        o[V-1:1] <= (wv && cnt != 5'd0) ? beat(w, 1'b0, rk, cnt, msk) >> 1 : w1v ? b1 >> 1 : {(V-1){1'b0}};
    end
endmodule
