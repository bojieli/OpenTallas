module ot_hdc_v41x_bmul_l #(
    parameter integer ML = 3
) (
    input  wire        clk,
    input  wire [15:0] a,
    input  wire [15:0] w,
    output reg  [15:0] y,
    output reg         ovf
);
     
    wire        az = a[15] || (a[14:0] == 15'd0);
    wire        wz = (w[14:0] == 15'd0);
    wire [7:0]  ma = {a[14:7] != 8'd0, a[6:0]};
    wire [7:0]  mw = {w[14:7] != 8'd0, w[6:0]};
    wire [8:0]  ea = (a[14:7] == 8'd0) ? 9'd1 : {1'b0, a[14:7]};
    wire [8:0]  ew = (w[14:7] == 8'd0) ? 9'd1 : {1'b0, w[14:7]};
    wire signed [11:0] e1 = $signed({3'b000, ea}) + $signed({3'b000, ew}) - 12'sd268;    
    wire signed [11:0] k1 = e1 + 12'sd149;                   
    wire [11:0] nk1 = -k1;
    reg  [15:0] rp;
    reg  signed [11:0] re;
    reg         rs, rz, rkneg;
    reg  [4:0]  rkl, rkr;
    always @(posedge clk) begin
        rp <= ma * mw;
        re <= e1;
        rs <= w[15];
        rz <= az || wz;
        rkneg <= k1[11];
        rkl <= k1[4:0];
        rkr <= (nk1 > 12'd17) ? 5'd17 : nk1[4:0];
    end

`line 200 "/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv" 0
     
    reg  [4:0]  lz0;
    integer kq;
    always @* begin
        lz0 = 5'd16;
        for (kq = 0; kq < 16; kq = kq + 1) if (rp[kq]) lz0 = 5'd15 - kq[4:0];
    end
    wire [4:0]         lz;
    wire [15:0]        p2;
    wire signed [11:0] e2;
    wire               s2s, s2z, s2kneg;
    wire [4:0]         s2kl, s2kr;
    ot_hdc_delay #(.W(5 + 16 + 12 + 3 + 10), .D((ML >= 5) ? 1 : 0)) u_cut2 (.clk(clk), .rst_n(1'b1),
        .d({lz0, rp, re, rs, rz, rkneg, rkl, rkr}), .q({lz, p2, e2, s2s, s2z, s2kneg, s2kl, s2kr}));
    wire [15:0]        pn = p2 << lz;
    wire signed [11:0] be = e2 + 12'sd142 - $signed({7'd0, lz});    
    wire [32:0]        xr = {p2, 17'd0} >> s2kr;
    wire [23:0]        fl = {8'd0, p2} << s2kl;
    reg  [15:0] s_pn;
    reg  [7:0]  s_be;
    reg         s_nrm, s_o32, s_zero, s_sign, s_kneg;
    reg  [16:0] s_q;                
    reg         s_g, s_st;
    reg  [23:0] s_fl;               
    always @(posedge clk) begin
        s_pn <= pn;
        s_be <= be[7:0];
        s_nrm <= (be >= 12'sd1);
        s_o32 <= !s2z && (p2 != 16'd0) && (be >= 12'sd255);
        s_zero <= s2z || (p2 == 16'd0);
        s_sign <= s2s;
        s_kneg <= s2kneg;
        s_q <= xr[32:17] ;
        s_g <= xr[16];
        s_st <= |xr[15:0];
        s_fl <= fl;
    end

`line 238 "/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv" 0
     
     
    wire [8:0]  nr = {1'b0, s_pn[15:8]} + ((s_pn[7] && ((|s_pn[6:0]) || s_pn[8])) ? 9'd1 : 9'd0);
    wire [8:0]  nbe = {1'b0, s_be} + {8'd0, nr[8]};            
    wire [15:0] ynorm0 = {s_sign, nbe[7:0], nr[8] ? 7'd0 : nr[6:0]};
    wire        onorm0 = (nbe >= 9'd255);
     
    wire [23:0] fr = {7'd0, s_q} + ((s_g && (s_st || s_q[0])) ? 24'd1 : 24'd0);
    wire [23:0] f0 = s_kneg ? fr : s_fl;
    wire [15:0] ynorm;
    wire        onorm, t_sign, t_zero, t_o32, t_nrm;
    wire [23:0] f;
    ot_hdc_delay #(.W(16 + 1 + 24 + 4), .D((ML >= 4) ? 1 : 0)) u_cut3 (.clk(clk), .rst_n(1'b1),
        .d({ynorm0, onorm0, f0, s_sign, s_zero, s_o32, s_nrm}), .q({ynorm, onorm, f, t_sign, t_zero, t_o32, t_nrm}));
    wire [32:0] fb = {9'd0, f} + 33'h7FFF + {32'd0, f[16]};
    wire [15:0] ysub = (f == 24'd0) ? 16'd0 : {t_sign, fb[30:16]};
    always @(posedge clk) begin
        ovf <= t_o32 || (!t_zero && t_nrm && onorm);
        y <= (t_zero || t_o32 || (t_nrm && onorm)) ? 16'd0 : (t_nrm ? ynorm : ysub);
    end
endmodule
