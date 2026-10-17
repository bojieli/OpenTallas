`timescale 1ns/1ps
// KVJ-D 2026-10-17 (kv_static_join_plan item 7): the ASTK e-read folded into the ASTK strip as an inline leaf on
// the SO/SI bus.  qkd_astk_native_er_service_w passes 8 x (425 + 634) bits through unchanged and touches only
// so[12:0] (the read-request field, which the service owns: a legacy ECTL read there is a fault) and si[632:569]
// (the EP's registered e_rdq) of each EP owner.  This leaf carries exactly those bits (8 x 13 + 8 x 1 in,
// 8 x 13 out, 8 x 64 in) instead of ~17k pass-through pins; the untouched bus stays a parent net.  Logic, edges
// and fault law are those of qkd_astk_native_er_service_w (ERL 3, N <= 8): a cycle-exact replica proved by
// tb_qkd_astk_er_tap against the service on the full bus.
module qkd_astk_er_tap #(parameter integer N=4, ERL=3) (
    input  wire            ck, rst_n,
    input  wire [N-1:0]    read_v,
    input  wire [11*N-1:0] read_addr,
    // owners 0..3 (strip rows 0, 1: S face) and 4..7 (rows 2, 3: N face)
    input  wire [3:0]      eso_v_lo, eso_v_hi,   // engine so[0] of each EP owner (legacy ECTL read valid: must stay 0)
    output wire [13*4-1:0] aso_lo, aso_hi,       // so[12:0] of each EP owner as the strip sees it
    input  wire [64*4-1:0] esi_lo, esi_hi,       // si[632:569] (e_rdq) of each EP owner
    output wire [N-1:0]    response_v,
    output wire [11*N-1:0] response_addr,
    output wire [64*N-1:0] response_data,
    output reg             fault
);
    wire [7:0] eso_v = {eso_v_hi, eso_v_lo};
    wire [64*8-1:0] esi = {esi_hi, esi_lo};
    reg  [13*8-1:0] aso;
    assign aso_lo = aso[0 +: 52]; assign aso_hi = aso[52 +: 52];
    reg [N-1:0] val[0:ERL-1];
    reg [10:0] tag[0:ERL-1][0:N-1];
    reg collide;
    integer i,j,e;
    always @* begin
        aso=104'd0;
        collide=1'b0;
        for(j=0;j<N;j=j+1)
            if(read_v[j]) begin
                for(i=0;i<j;i=i+1)
                    if(read_v[i] && read_addr[11*i+3+:3]==read_addr[11*j+3+:3]) collide=1'b1;
                aso[13*read_addr[11*j+3+:3]+:13]={1'b0,read_addr[11*j+:11],1'b1};
            end
    end
    always @(posedge ck or negedge rst_n)
        if(!rst_n)begin for(i=0;i<ERL;i=i+1)val[i]<=0;fault<=0;end
        else begin
            val[0]<=read_v;for(i=1;i<ERL;i=i+1)val[i]<=val[i-1];
            if(collide)fault<=1;
            for(e=0;e<8;e=e+1)if(eso_v[e])fault<=1;
        end
    always @(posedge ck)begin
        for(j=0;j<N;j=j+1)begin tag[0][j]<=read_addr[11*j+:11];for(i=1;i<ERL;i=i+1)tag[i][j]<=tag[i-1][j];end
    end
    genvar g;
    generate for(g=0;g<N;g=g+1)begin:g_rsp
        wire [2:0] owner=tag[ERL-1][g][5:3];
        assign response_v[g]=val[ERL-1][g];
        assign response_addr[11*g+:11]=tag[ERL-1][g];
        // decoded constant-index select (one-hot AND-OR; same function as esi[64*owner +: 64], no runtime part-select)
        reg [63:0] sel;
        integer o;
        always @* begin sel=64'd0; for(o=0;o<8;o=o+1) sel=sel|({64{owner==3'(o)}}&esi[64*o+:64]); end
        assign response_data[64*g+:64]=sel;
    end endgenerate
    initial if(ERL!=3 || N<1 || N>8) $fatal(1,"native EP ABI requires ERL3, 1<=N<=8");
endmodule

// Wires-only strip successor: the die's ASTK strip with the e-read inline on its SO/SI bus.  Engine so[12:0] is
// replaced by the tap's request field; so[424:13] and the whole si bus are parent nets (si also feeds the tap's e_rdq).
module qkd_astk_strip_er_s #(parameter integer RL = 1, N = 4) (
    input  wire          ck_c, input wire [3:0] ck_z, input wire [63:0] ck_v, input wire [31:0] ck_x, input wire [7:0] ck_e,
    input  wire          ck_r, ck_er, rst_n,
    input  wire [1:0]    st, input wire [539:0] aq, input wire [35:0] am,
    output wire [562:0]  ap, output wire [1:0] pv_done, output wire af, output wire [20:0] lt,
    input  wire [425*8-1:0]  so, output wire [634*8-1:0] si, input wire [4096*8-1:0] nb,
    input  wire [N-1:0]  read_v, input wire [11*N-1:0] read_addr,
    output wire [N-1:0]  response_v, output wire [11*N-1:0] response_addr, output wire [64*N-1:0] response_data,
    output wire          er_fault
);
    wire [13*8-1:0] aso; wire [7:0] eso_v; wire [64*8-1:0] esi; wire [425*8-1:0] so_s;
    genvar e;
    generate for (e = 0; e < 8; e = e + 1) begin : g_e
        assign eso_v[e] = so[425*e];
        assign so_s[425*e +: 425] = {so[425*e+13 +: 412], aso[13*e +: 13]};
        assign esi[64*e +: 64] = si[634*e+569 +: 64];
    end endgenerate
    qkd_astk_er_tap #(.N(N), .ERL(3)) u_er (.ck(ck_er), .rst_n(rst_n), .read_v(read_v), .read_addr(read_addr),
        .eso_v_lo(eso_v[3:0]), .eso_v_hi(eso_v[7:4]), .aso_lo(aso[0 +: 52]), .aso_hi(aso[52 +: 52]),
        .esi_lo(esi[0 +: 256]), .esi_hi(esi[256 +: 256]), .response_v(response_v), .response_addr(response_addr),
        .response_data(response_data), .fault(er_fault));
    qkd_astk_strip_s #(.RL(RL)) u_strip (.ck_c(ck_c), .ck_z(ck_z), .ck_v(ck_v), .ck_x(ck_x), .ck_e(ck_e), .ck_r(ck_r),
        .rst_n(rst_n), .st(st), .aq(aq), .am(am), .ap(ap), .pv_done(pv_done), .af(af), .lt(lt),
        .so0(so_s[0+:425]), .so1(so_s[425+:425]), .so2(so_s[850+:425]), .so3(so_s[1275+:425]),
        .so4(so_s[1700+:425]), .so5(so_s[2125+:425]), .so6(so_s[2550+:425]), .so7(so_s[2975+:425]),
        .si0(si[0+:634]), .si1(si[634+:634]), .si2(si[1268+:634]), .si3(si[1902+:634]),
        .si4(si[2536+:634]), .si5(si[3170+:634]), .si6(si[3804+:634]), .si7(si[4438+:634]),
        .nb0_0(nb[0*1024+:1024]), .nb0_1(nb[1*1024+:1024]), .nb0_2(nb[2*1024+:1024]), .nb0_3(nb[3*1024+:1024]),
        .nb1_0(nb[4*1024+:1024]), .nb1_1(nb[5*1024+:1024]), .nb1_2(nb[6*1024+:1024]), .nb1_3(nb[7*1024+:1024]),
        .nb2_0(nb[8*1024+:1024]), .nb2_1(nb[9*1024+:1024]), .nb2_2(nb[10*1024+:1024]), .nb2_3(nb[11*1024+:1024]),
        .nb3_0(nb[12*1024+:1024]), .nb3_1(nb[13*1024+:1024]), .nb3_2(nb[14*1024+:1024]), .nb3_3(nb[15*1024+:1024]),
        .nb4_0(nb[16*1024+:1024]), .nb4_1(nb[17*1024+:1024]), .nb4_2(nb[18*1024+:1024]), .nb4_3(nb[19*1024+:1024]),
        .nb5_0(nb[20*1024+:1024]), .nb5_1(nb[21*1024+:1024]), .nb5_2(nb[22*1024+:1024]), .nb5_3(nb[23*1024+:1024]),
        .nb6_0(nb[24*1024+:1024]), .nb6_1(nb[25*1024+:1024]), .nb6_2(nb[26*1024+:1024]), .nb6_3(nb[27*1024+:1024]),
        .nb7_0(nb[28*1024+:1024]), .nb7_1(nb[29*1024+:1024]), .nb7_2(nb[30*1024+:1024]), .nb7_3(nb[31*1024+:1024]));
endmodule
