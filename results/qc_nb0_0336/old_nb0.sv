`timescale 1ns/1ps
module nb0_reference #(
    parameter integer CE_MUT    = 0,
    parameter integer ADD_LAT   = 7,
    parameter integer SKEW      = 14,
    parameter integer SCALE_LAT = 7,       // QR-TAIL1 10-21: scale mul encode cut (+1 result edge)
    parameter integer MUT       = 0,
    parameter integer JB        = 8,
    parameter integer PIN_IN    = 1,       // 1: every data/control input lands in one pin register (+1 edge, all inputs)
    parameter integer BT_LAT    = PIN_IN   // extra edges of the bt_word -> bt_q round trip beyond the monolith's
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          cfg_v_p,
    input  wire [1:0]    cfg_mode_p,
    input  wire          cfg_wsrc_p,
    input  wire [7:0]    cfg_nwords_p,
    input  wire [8:0]    cfg_sbase_p,
    input  wire [7:0]    cfg_kcm1_p,
    input  wire [63:0]   rs_s_lo_p, rs_s_hi_p, rs_n_lo_p, rs_n_hi_p,   // rs_x[64r +: 64], rs_x[514 + 64r +: 64]
    input  wire [3:0]    rs_s_c_p, rs_n_c_p,                       // {rs_x[1027], rs_x[1026], rs_x[513], rs_x[512]}
    output wire [63:0]   nb_od,
    output wire [1:0]    nb_oc,
    output reg           bt_re,
    output reg  [8:0]    bt_word,
    input  wire [31:0]   bt_q_p,                                 // bt_q[32r +: 32]
    output reg           r_v,
    output reg  [7:0]    r_idx,
    output reg           r_last,
    output reg  [63:0]   r_d,
    input  wire [3:0]    flt_bank_i,                           // landed fault ring: upstream region's writer
    input  wire [3:0]    flt_vld_i,
    output wire [3:0]    flt_bank_o,
    output wire [3:0]    flt_vld_o,
    output reg           fault
);
localparam integer NL = 2, NZ = 2*NL, DW = 32*NL;
// Reset lands at the face in two registered stages (rst_l0 -> rst_l1), then the equal-depth trees: release +2 edges.
reg rst_l0, rst_l1;
always @(posedge ck) begin rst_l0 <= rst_n; rst_l1 <= rst_l0; end
wire [43:0] sr_reset;
qfd_dv_reset_tree #(.N(44)) u_safe_reset (.ck(ck),.rst_n(rst_l1),.q(sr_reset));
wire [9:0] math_reset;
qfd_dv_reset_tree #(.N(10)) u_math_reset (.ck(ck),.rst_n(rst_l1),.q(math_reset));
// Pin registers (PIN_IN): every data / control input is one flop at its pin; the landed fault-ring inputs are read by the
// landing reader (its output register is the capture) and are not re-registered (that would shift the K=2 read).
wire cfg_v; wire [1:0] cfg_mode; wire cfg_wsrc; wire [7:0] cfg_nwords; wire [8:0] cfg_sbase; wire [7:0] cfg_kcm1;
wire [63:0] rs_s_lo, rs_s_hi, rs_n_lo, rs_n_hi, nb_d; wire [3:0] rs_s_c, rs_n_c; wire [1:0] nb_c; wire [31:0] bt_q;
localparam integer PW = 1+2+1+8+9+8 + 4*64 + 4+4 + 32;   // neighbour word + valid pins removed (l9 pair head)
wire [PW-1:0] pin_d = {cfg_v_p, cfg_mode_p, cfg_wsrc_p, cfg_nwords_p, cfg_sbase_p, cfg_kcm1_p, rs_s_lo_p, rs_s_hi_p, rs_n_lo_p,
                       rs_n_hi_p, rs_s_c_p, rs_n_c_p, bt_q_p};
wire [PW-1:0] pin_q;
generate if (PIN_IN) begin : g_pin
    reg [PW-1:0] r; always @(posedge ck) r <= pin_d; assign pin_q = r;
end else begin : g_nopin
    assign pin_q = pin_d;
end endgenerate
assign {cfg_v, cfg_mode, cfg_wsrc, cfg_nwords, cfg_sbase, cfg_kcm1, rs_s_lo, rs_s_hi, rs_n_lo, rs_n_hi, rs_s_c, rs_n_c, bt_q} = pin_q;
// l9 pair HEAD: no neighbour word.  nb_d / nb_c fold to the as-built literal 0, so nbv = 0: the mode-2
// neighbour add (h9 buffer, g_l9 adders, c9 / lead) never fires and synthesis removes it.
assign nb_d = (CE_MUT == 1 ? {64{1'b1}} : 64'd0); assign nb_c = (CE_MUT == 1 ? {2{1'b1}} : 2'd0);

reg[27:0] cfg_payload0,cfg_payload1;
wire[1:0] safe_cfg_mode; wire[0:0] safe_cfg_wsrc; wire[7:0] safe_cfg_nwords; wire[8:0] safe_cfg_sbase; wire[7:0] safe_cfg_kcm1;
assign {safe_cfg_mode,safe_cfg_wsrc,safe_cfg_nwords,safe_cfg_sbase,safe_cfg_kcm1}=cfg_payload1;
always @(posedge ck) begin cfg_payload0<={cfg_mode,cfg_wsrc,cfg_nwords,cfg_sbase,cfg_kcm1};cfg_payload1<=cfg_payload0;end
// cfg_v copies: one mid copy (same two-edge depth as the monolith), 24 final copies (<= 32 loads on the mid copy).
// final[0..3] mode units, final[0]/final[2] ws bits (as monolith final[2z]), final[4+k] control register k.
wire cfg_mid; wire[23:0] cfg_final;
(* keep_hierarchy="yes" *) qfd_dv_station_copy #(.ID(400)) u_cfg_mid(.ck(ck),.d(cfg_v),.q(cfg_mid));
for(genvar z=0;z<24;z=z+1) begin:g_cfg_final
(* keep_hierarchy="yes" *) qfd_dv_station_copy #(.ID(500+z)) u_c(.ck(ck),.d(cfg_mid),.q(cfg_final[z]));end
wire cfg_schedule_fault=(cfg_v||cfg_mid||cfg_final[0])&&(rs_s_c[0]||rs_s_c[2]||rs_n_c[0]||rs_n_c[2]||nb_c[0]);

wire[3:0] local_mode[0:NZ-1];
wire[3:0] local_mode2[0:NZ-1];
wire[1:0] mode_mid; wire[1:0] mode_payload[0:NZ-1];
(* keep_hierarchy="yes" *) qfd_dv_station_copy #(.W(2),.ID(0)) u_mode_mid(.ck(ck),.d(cfg_mode),.q(mode_mid));
for(genvar z=0;z<NZ;z=z+1) begin:g_mode_payload
 (* keep_hierarchy="yes" *) qfd_dv_station_copy #(.W(2),.ID(100+z)) u_p(.ck(ck),.d(mode_mid),.q(mode_payload[z]));
 (* keep_hierarchy="yes" *) qfd_dv_station_mode #(.ID(z),.USE2(z==0)) u_m(.ck(ck),.rst_n(sr_reset[22+z]),.cfg_v(cfg_final[z]),.mode(mode_payload[z]),.q(local_mode[z]));
 // second kept mode unit, same cfg edge: fd mux bits [15:8] (census: used_q 33 loads)
 (* keep_hierarchy="yes" *) qfd_dv_station_mode #(.ID(16+z),.USE2(z==0)) u_m2(.ck(ck),.rst_n(sr_reset[22+z]),.cfg_v(cfg_final[z]),.mode(mode_payload[z]),.q(local_mode2[z]));
end
wire[NL-1:0] ws_rep;
for(genvar z=0;z<NL;z=z+1) begin:g_ws
 wire ws_source;
 (* keep_hierarchy="yes" *) qfd_dv_station_cfgbit #(.ID(z)) u_c(.ck(ck),.rst_n(sr_reset[26+z]),.cfg_v(cfg_final[2*z]),.d(safe_cfg_wsrc),.q(ws_source));
 qfd_dv_s8s_ring_delay #(.W(1),.D(3+BT_LAT)) u_d(.clk(ck),.rst_n(sr_reset[28+z]),.d(ws_source),.q(ws_rep[z]));
end

    reg [1:0] mode; reg wsrc; reg [7:0] nwords; reg [8:0] sbase; reg [7:0] kcm1;
    always @(posedge ck or negedge sr_reset[0])
        if (!sr_reset[0]) kcm1 <= 8'd0;
        else if (cfg_final[4]) kcm1 <= (MUT == 14) ? 8'd0 : safe_cfg_kcm1;
    always @(posedge ck or negedge sr_reset[1])
        if (!sr_reset[1]) mode <= 2'd0;
        else if (cfg_final[5]) mode <= safe_cfg_mode;
    always @(posedge ck or negedge sr_reset[2])
        if (!sr_reset[2]) nwords <= 8'd0;
        else if (cfg_final[6]) nwords <= safe_cfg_nwords;
    always @(posedge ck or negedge sr_reset[3])
        if (!sr_reset[3]) sbase <= 9'd0;
        else if (cfg_final[7]) sbase <= safe_cfg_sbase;
    always @(posedge ck or negedge sr_reset[4])
        if (!sr_reset[4]) wsrc <= 1'b0;
        else if (cfg_final[8]) wsrc <= safe_cfg_wsrc;

    // Near (skewed) halves: data slice through the region's own SRAM rows, valid/bad bits through finite rings.
    wire [DW-1:0] ns_d, nn_d;
    wire [1:0] ns_c, nn_c, ns_c7, nn_c7;
    qfd_dv_s8s_sram_delay #(.W(DW), .D(SKEW), .MUT(MUT == 16)) u_sks (.ck(ck), .rst_n(sr_reset[30]), .d(rs_s_lo), .q(ns_d));
    qfd_dv_s8s_sram_delay #(.W(DW), .D(SKEW)) u_skn (.ck(ck), .rst_n(sr_reset[31]), .d(rs_n_lo), .q(nn_d));
    qfd_dv_s8s_ring_delay #(.W(2),.D(SKEW/2),.ID(1)) u_sks_c0 (.clk(ck),.rst_n(sr_reset[32]),.d(rs_s_c[1:0]),.q(ns_c7));
    qfd_dv_s8s_ring_delay #(.W(2),.D(SKEW-SKEW/2+((MUT == 16) ? -1 : 0)),.ID(2)) u_sks_c1 (.clk(ck),.rst_n(sr_reset[32]),.d(ns_c7),.q(ns_c));
    qfd_dv_s8s_ring_delay #(.W(2),.D(SKEW/2),.ID(3)) u_skn_c0 (.clk(ck),.rst_n(sr_reset[33]),.d(rs_n_c[1:0]),.q(nn_c7));
    qfd_dv_s8s_ring_delay #(.W(2),.D(SKEW-SKEW/2),.ID(4)) u_skn_c1 (.clk(ck),.rst_n(sr_reset[33]),.d(nn_c7),.q(nn_c));
    wire [1:0] fs_c = rs_s_c[3:2], fn_c = rs_n_c[3:2];
    wire [DW-1:0] fs_d = rs_s_hi, fn_d = rs_n_hi;
    wire plo = fs_c[0] & ns_c[0], phi = fn_c[0] & nn_c[0];
    localparam integer JBW = (JB > 1) ? $clog2(JB) : 1;
    reg [JBW-1:0] wlo, whi;
    reg [7:0]     klo, khi;
    reg           klast_lo, klast_hi;
    // LASTK counts actual words in each K block. A production tail may carry
    // fewer than JB words (e.g. LM48rows=3words); nwords>=JB keeps JB width.
    // Zero encodes the legacy full-width counter wrap and is not newly adopted.
    reg [JBW-1:0] word_last;
    always @(posedge ck or negedge sr_reset[2])
        if (!sr_reset[2]) word_last <= JBW'(JB - 1);
        else if (cfg_final[6]) word_last <= JBW'((safe_cfg_nwords != 0 && safe_cfg_nwords < JB) ? safe_cfg_nwords - 1 : JB - 1);
    wire          eblo = plo && wlo == word_last, ebhi = phi && whi == word_last;
    always @(posedge ck or negedge sr_reset[5])
        if (!sr_reset[5]) khi <= 8'd0;
        else if (cfg_final[9]) khi <= 8'd0;
        else if (ebhi) khi <= klast_hi ? 8'd0 : khi + 8'd1;
    always @(posedge ck or negedge sr_reset[6])
        if (!sr_reset[6]) klast_hi <= 1'b1;
        else if (cfg_final[10]) klast_hi <= (MUT == 14) || safe_cfg_kcm1 == 8'd0;
        else if (ebhi) klast_hi <= klast_hi ? kcm1 == 8'd0 : khi + 8'd1 == kcm1;
    always @(posedge ck or negedge sr_reset[7])
        if (!sr_reset[7]) klast_lo <= 1'b1;
        else if (cfg_final[11]) klast_lo <= (MUT == 14) || safe_cfg_kcm1 == 8'd0;
        else if (eblo) klast_lo <= klast_lo ? kcm1 == 8'd0 : klo + 8'd1 == kcm1;
    always @(posedge ck or negedge sr_reset[8])
        if (!sr_reset[8]) klo <= 8'd0;
        else if (cfg_final[12]) klo <= 8'd0;
        else if (eblo) klo <= klast_lo ? 8'd0 : klo + 8'd1;
    always @(posedge ck or negedge sr_reset[9])
        if (!sr_reset[9]) whi <= 0;
        else if (cfg_final[13]) whi <= 0;
        else if (phi) whi <= ebhi ? {JBW{1'b0}} : whi + 1'b1;
    always @(posedge ck or negedge sr_reset[10])
        if (!sr_reset[10]) wlo <= 0;
        else if (cfg_final[14]) wlo <= 0;
        else if (plo) wlo <= eblo ? {JBW{1'b0}} : wlo + 1'b1;
    wire vlo_in = plo & klast_lo, vhi_in = phi & klast_hi;
    wire [DW-1:0] ylo, yhi;
    wire [NL-1:0] vlol, vhil; wire[2*NL-1:0] vlo_rep,vhi_rep;
    wire [2*NL-1:0] elo, ehi;
    genvar l;
    generate for (l = 0; l < NL; l = l + 1) begin : g_l7
        qfd_dv_s8s_station_add_bounded #(.LAT(ADD_LAT), .DRST(0),.CV(l==0),.ID(l)) u_lo (.clk(ck), .rst_n(math_reset[l]), .valid_in(vlo_in),
            .a(fs_d[32*l +: 32]), .b(ns_d[32*l +: 32]), .y(ylo[32*l +: 32]), .err(elo[2*l +: 2]), .valid_rep(vlo_rep[2*l+:2]), .valid_out(vlol[l]));
        qfd_dv_s8s_station_add_bounded #(.LAT(ADD_LAT), .DRST(0),.CV(l==0),.ID(l),.REPS(0)) u_hi (.clk(ck), .rst_n(math_reset[NL+l]), .valid_in(vhi_in),
            .a(fn_d[32*l +: 32]), .b(nn_d[32*l +: 32]), .y(yhi[32*l +: 32]), .err(ehi[2*l +: 2]), .valid_rep(vhi_rep[2*l+:2]), .valid_out(vhil[l]));
    end endgenerate
    wire vlo = vlol[0], vhi = vhil[0];

    reg [2:0]   hw, hr;
    reg [3:0]   hn;
    wire        hpop = mode == 2'd0 && !vlo && hn != 4'd0;
    always @(posedge ck or negedge sr_reset[11])
        if (!sr_reset[11]) hn <= 4'd0;
        else if (cfg_final[15]) hn <= 4'd0;
        else hn <= hn + ((vhi && mode == 2'd0) ? 4'd1 : 4'd0) - (hpop ? 4'd1 : 4'd0);
    always @(posedge ck or negedge sr_reset[12])
        if (!sr_reset[12]) hr <= 3'd0;
        else if (cfg_final[16]) hr <= 3'd0;
        else if (hpop) hr <= hr + 3'd1;
    always @(posedge ck or negedge sr_reset[13])
        if (!sr_reset[13]) hw <= 3'd0;
        else if (cfg_final[17]) hw <= 3'd0;
        else if (vhi && mode == 2'd0) hw <= hw + 3'd1;

    wire [DW-1:0] hb_q;
    wire [2:0] hr_next = hr + (hpop ? 3'd1 : 3'd0);
    qfd_dv_s8s_sram_lookahead #(.W(DW)) u_hb (.ck(ck), .write(vhi && mode == 2'd0),
        .wa({2'b0, hw}), .wd(yhi), .ra({2'b0, cfg_final[18] ? 3'd0 : hr_next}), .q(hb_q));
    wire        v7 = (mode == 2'd0) && (vlo || hpop);
    wire[DW-1:0] y7;
    for(genvar z=0;z<NZ;z=z+1) begin:g_y7
     assign y7[16*z+:16]=vlo_rep[z]?ylo[16*z+:16]:hb_q[16*z+:16];
    end

    wire v8_in = vlo && vhi && mode != 2'd0;
    wire [DW-1:0] y8;
    wire [NL-1:0] v8l; wire[2*NL-1:0] v8_rep;
    wire [2*NL-1:0] e8;
    generate for (l = 0; l < NL; l = l + 1) begin : g_l8
        qfd_dv_s8s_station_add_bounded #(.LAT(ADD_LAT), .DRST(0),.CV(l==0),.ID(l)) u_add (.clk(ck), .rst_n(math_reset[2*NL+l]), .valid_in(v8_in),
            .a(ylo[32*l +: 32]), .b(yhi[32*l +: 32]), .y(y8[32*l +: 32]), .err(e8[2*l +: 2]), .valid_rep(v8_rep[2*l+:2]), .valid_out(v8l[l]));
    end endgenerate
    wire v8 = v8l[0];
    reg [2:0] c8, c9;
    reg [3:0] lead;
    wire nbv = nb_c[0];
    wire own9 = v8 && mode == 2'd2;
    wire v9_in = nbv && mode == 2'd2;
    always @(posedge ck or negedge sr_reset[14])
        if (!sr_reset[14]) c8 <= 3'd0;
        else if (cfg_final[19]) c8 <= 3'd0;
        else if (own9) c8 <= c8 + 3'd1;
    always @(posedge ck or negedge sr_reset[15])
        if (!sr_reset[15]) c9 <= 3'd0;
        else if (cfg_final[20]) c9 <= 3'd0;
        else if (v9_in) c9 <= c9 + 3'd1;
    always @(posedge ck or negedge sr_reset[16])
        if (!sr_reset[16]) lead <= 4'd0;
        else if (cfg_final[21]) lead <= 4'd0;
        else lead <= lead + (own9 ? 4'd1 : 4'd0) - (v9_in ? 4'd1 : 4'd0);

    wire [DW-1:0] h9_q;
    wire [2:0] c9_next = c9 + (v9_in ? 3'd1 : 3'd0);
    qfd_dv_s8s_sram_lookahead #(.W(DW), .MUT(MUT == 17)) u_h9 (.ck(ck), .write(own9),
        .wa({2'b0, c8}), .wd(y8), .ra({2'b0, cfg_final[22] ? 3'd0 : c9_next}), .q(h9_q));
    wire [DW-1:0] y9;
    wire [NL-1:0] v9l; wire[2*NL-1:0] v9_rep;
    wire [2*NL-1:0] e9;
    generate for (l = 0; l < NL; l = l + 1) begin : g_l9
        qfd_dv_s8s_station_add_bounded #(.LAT(ADD_LAT), .DRST(0),.CV(l==0),.ID(l),.REPS(0)) u_add (.clk(ck), .rst_n(math_reset[3*NL+l]), .valid_in(nbv && local_mode[2*l][2]),
            .a(h9_q[32*l +: 32]), .b(nb_d[32*l +: 32]), .y(y9[32*l +: 32]), .err(e9[2*l +: 2]), .valid_rep(v9_rep[2*l+:2]), .valid_out(v9l[l]));
    end endgenerate
    wire v9 = v9l[0];
    for(genvar z=0;z<NZ;z=z+1) begin:g_nb
     qfd_dv_station_out #(.W(16),.ID(z)) u_o(.ck(ck),.rst_n(sr_reset[34+z]),.d((v8_rep[z]&&local_mode[z][3])?y8[16*z+:16]:16'd0),.q(nb_od[16*z+:16]));
    end
    qfd_dv_station_out #(.W(2),.ID(100)) u_ov(.ck(ck),.rst_n(sr_reset[38]),.d({1'b0,v8&&mode==2'd3}),.q(nb_oc));
    wire        fv = (mode == 2'd0) ? v7 : (mode == 2'd1) ? v8 : (mode == 2'd2) ? v9 : 1'b0;
    wire[DW-1:0] fd;
    for(genvar z=0;z<NZ;z=z+1) begin:g_fd
     assign fd[16*z+:8]=local_mode[z][0]?y7[16*z+:8]:local_mode[z][1]?y8[16*z+:8]:y9[16*z+:8];
     assign fd[16*z+8+:8]=local_mode2[z][0]?y7[16*z+8+:8]:local_mode2[z][1]?y8[16*z+8+:8]:y9[16*z+8+:8];
    end
    reg  [7:0]  j;
    always @(posedge ck or negedge sr_reset[17])
        if (!sr_reset[17]) j <= 8'd0;
        else if (cfg_final[23]) j <= 8'd0;
        else if (fv) j <= j + 8'd1;
    always @(posedge ck or negedge sr_reset[18])
        if (!sr_reset[18]) bt_re <= 1'b0;
        else bt_re <= fv && !wsrc;
    always @(posedge ck or negedge sr_reset[19])
        if (!sr_reset[19]) bt_word <= 9'd0;
        else bt_word <= sbase + {1'b0, j} + ((MUT == 3) ? 9'd1 : 9'd0);

    wire [DW-1:0] fd3;
    qfd_dv_s8s_sram_delay #(.W(DW), .D(3+BT_LAT)) u_scale_wait (.ck(ck), .rst_n(sr_reset[39]), .d(fd), .q(fd3));
    wire fv3,ls3;wire[7:0] j3;
    qfd_dv_s8s_ring_delay #(.W(10),.D(3+BT_LAT)) u_meta(.clk(ck),.rst_n(sr_reset[40]),.d({fv,j,j+8'd1==nwords}),.q({fv3,j3,ls3}));
    wire [DW-1:0] y;
    wire [NL-1:0]  vs;
    wire [2*NL-1:0]  es;
    localparam integer SCALE_DRST = 0;
    generate for (l = 0; l < NL; l = l + 1) begin : g_sc
        qfd_dv_s8s_station_mul_bounded #(.LAT(SCALE_LAT), .DRST(SCALE_DRST),.CV(l==0),.ID(l),.BZ16(1)) u_mul (.clk(ck), .rst_n(math_reset[4*NL+l]), .valid_in(fv3),
            .a(fd3[32*l +: 32]), .b({ws_rep[l] ? 16'h3F80 : bt_q[16*l +: 16], 16'd0}),
            .y(y[32*l +: 32]), .err(es[2*l +: 2]), .valid_out(vs[l]));
    end endgenerate
    wire [7:0] jo; wire lo;
    qfd_dv_s8s_ring_delay #(.W(9), .D(SCALE_LAT)) u_jd (.clk(ck), .rst_n(sr_reset[41]), .d({ls3, j3}), .q({lo, jo}));
    always @(posedge ck or negedge sr_reset[20])
        if (!sr_reset[20]) r_v <= 1'b0;
        else r_v <= vs[0];
    always @(posedge ck) begin r_d <= y; r_idx <= jo; r_last <= lo; end

    wire in_bad = (fs_c[0] ^ ns_c[0]) | (fn_c[0] ^ nn_c[0]) | fs_c[1] | ns_c[1] | fn_c[1] | nn_c[1] | nb_c[1] |
                  (nbv && mode != 2'd2) | (mode != 2'd0 && (vlo ^ vhi)) | (vhi && mode == 2'd0 && hn == 4'd8 && !hpop) |
                  (v9_in && lead == 4'd0) | (fv && j >= nwords);
    wire fp_bad = (vlo && |elo) | (vhi && |ehi) | (v8 && |e8) | (v9 && |e9) | (vs[0] && |es);
    // Landed fault ring: writer at this region's clock, reader of the upstream region's writer at this clock.
    wire flt_up;
    ot_pl_land_phys_chunk_w #(.W(1),.D(4),.CHUNK_BITS(24)) u_flt_w (.ck(ck),.rsi(sr_reset[42]),.i(fault),.bank(flt_bank_o),.vld(flt_vld_o));
    ot_pl_land_phys_chunk_r #(.W(1),.D(4),.K(2),.CHUNK_BITS(24)) u_flt_r (.ck(ck),.rsi(sr_reset[43]),.bank(flt_bank_i),.vld(flt_vld_i),.o(flt_up));
    always @(posedge ck or negedge sr_reset[21])
        if (!sr_reset[21]) fault <= 1'b0;
        else fault <= fault | in_bad | fp_bad | cfg_schedule_fault | flt_up;
endmodule
