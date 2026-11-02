module ot_hdc_v41x_q4dot_l #(
    parameter integer QL = 3       
) (
    input  wire         clk,
    input  wire [127:0] a,         
    input  wire [127:0] b,
    input  wire [7:0]   ua,        
    input  wire [7:0]   ub,
    output reg  [31:0]  y,         
    output reg          ovf        
);
    function automatic [3:0] dmag(input [2:0] mi);    
        case (mi)
            3'd0: dmag = 4'd0;  3'd1: dmag = 4'd1;  3'd2: dmag = 4'd2;  3'd3: dmag = 4'd3;
            3'd4: dmag = 4'd4;  3'd5: dmag = 4'd6;  3'd6: dmag = 4'd8;  default: dmag = 4'd12;
        endcase
    endfunction

`line 39 "/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv" 0
     
     
     
     
     
    function automatic [8:0] sprod(input [6:0] x);      
        reg [7:0] pm;
        begin
            pm = dmag(x[5:3]) * dmag(x[2:0]);
            sprod = x[6] ? (9'd0 - {1'b0, pm}) : {1'b0, pm};
        end
    endfunction
    function automatic [128*9-1:0] mktab(input integer dummy);
        integer j;
        begin
            for (j = 0; j < 128; j = j + 1) mktab[9*j +: 9] = sprod(j[6:0]) ^ 9'h100;
        end
    endfunction
    localparam [128*9-1:0] TAB = mktab(0);
    reg  [32*14-1:0] opa;
    reg  [8:0]       t;
    integer i;
    always @* begin
        for (i = 0; i < 32; i = i + 1) begin
            t = TAB[9 * {a[4*i + 3] ^ b[4*i + 3], a[4*i +: 3], b[4*i +: 3]} +: 9];
            opa[14*i +: 14] = {5'd0, t};
        end
    end
    wire [7*14-1:0]  qa;
    ot_hdc_v41x_csa #(.N(32), .M(7), .W(14)) u_ca (.d(opa), .q(qa));
    wire signed [9:0] ea = $signed({2'b00, ua}) + $signed({2'b00, ub}) - 10'sd256;
    wire refa = (ua >= 8'd253) || (ub >= 8'd253);
    reg [7*14-1:0] ra;
    reg signed [9:0] rea;
    reg rrefa;
    always @(posedge clk) begin
        ra <= qa;
        rea <= ea;
        rrefa <= refa;
    end

`line 80 "/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv" 0
     
     
    wire [2*14-1:0] qb0, qb;
    ot_hdc_v41x_csa #(.N(7), .M(2), .W(14)) u_cb (.d(ra), .q(qb0));
    wire signed [9:0] rea_b;
    wire rrefa_b;
    ot_hdc_delay #(.W(28 + 10 + 1), .D((QL >= 5) ? 1 : 0)) u_cutb (.clk(clk), .rst_n(1'b1),
        .d({qb0, rea, rrefa}), .q({qb, rea_b, rrefa_b}));
    wire [13:0] sb = (qb[13:0] + qb[27:14]) ^ 14'h2000;      
    wire [12:0] mb = sb[13] ? (~sb[12:0] + 13'd1) : sb[12:0];    
    wire signed [11:0] kb = $signed({{2{rea_b[9]}}, rea_b}) + 12'sd149;       
    wire [11:0] nkb = -kb;
    reg         rsg, rkneg;
    reg  [12:0] rm;
    reg  [4:0]  rkl;                  
    reg  [3:0]  rkr;                  
    reg signed [11:0] rnl, rov;       
    reg signed [9:0] reb;
    reg rrefb;
    always @(posedge clk) begin
        rsg <= sb[13];
        rm <= mb;
        rkneg <= kb[11];
        rkl <= kb[4:0];
        rkr <= (nkb > 12'd14) ? 4'd14 : nkb[3:0];
        rnl <= $signed({{2{rea_b[9]}}, rea_b}) + 12'sd138;
        rov <= $signed({{2{rea_b[9]}}, rea_b}) - 12'sd116;
        reb <= rea_b;
        rrefb <= rrefa_b;
    end

`line 111 "/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv" 0
     
     
    reg  [3:0]  lz0;
    integer kq;
    always @* begin
        lz0 = 4'd13;
        for (kq = 0; kq < 13; kq = kq + 1) if (rm[kq]) lz0 = 4'd12 - kq[3:0];
    end
    wire [26:0]       xr = {rm, 14'd0} >> rkr;
    wire [12:0]       qt = xr[26:14];
    wire              g = xr[13], st = |xr[12:0];
    wire [23:0]       fr = {11'd0, qt} + ((g && (st || qt[0])) ? 24'd1 : 24'd0);
    wire [23:0]       fl = {11'd0, rm} << rkl;
    wire [23:0]       f0 = rkneg ? fr : fl;
    wire [3:0]        lz;
    wire [12:0]       cm;
    wire [23:0]       f;
    wire signed [9:0] ceb;
    wire signed [11:0] cnl, cov;
    wire              csg, cref;
    ot_hdc_delay #(.W(4 + 13 + 24 + 10 + 12 + 12 + 2), .D((QL >= 4) ? 1 : 0)) u_cutc (.clk(clk), .rst_n(1'b1),
        .d({lz0, rm, f0, reb, rnl, rov, rsg, rrefb}), .q({lz, cm, f, ceb, cnl, cov, csg, cref}));
    wire [12:0]       mn = cm << lz;                          
    wire [7:0]        bef = ceb[7:0] + 8'd139 - {4'd0, lz};   
    wire              nrm = $signed({8'd0, lz}) <= cnl;
    wire              ovc = (cm != 13'd0) && ($signed({8'd0, lz}) <= cov);
    reg  [31:0] yc;
    reg         oc;
    always @* begin
        oc = cref || ovc;
        if (cm == 13'd0 || oc) yc = 32'd0;
        else if (nrm) yc = {csg, bef, mn[11:0], 11'd0};
        else if (f == 24'd0) yc = 32'd0;
        else yc = {csg, 7'd0, f};
    end
    always @(posedge clk) begin
        y <= yc;
        ovf <= oc;
    end
endmodule
