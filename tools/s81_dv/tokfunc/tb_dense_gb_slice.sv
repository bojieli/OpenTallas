`timescale 1ns/1ps
// TOK-ALL-17 (10-27): slice u_s_0S L0 a_proj GB composition, successor of tb_dense_xs_cap_gb (one frame).
// actual ot_s81sl_xs4 -> production 1104-bit lane word -> the six as-built GB frames of die_b178.v u_s_0S in their die
// chains: W  u_f_0L01 (col_h10_l4_lp_asb_x) -xo-> u_f_0L02 (col_h9_l4_lp_asb_x) -xo-> u_f_0L03 (col_h9_l4_lp_asb_nx)
//         E  u_f_0R01 (col_h10_l4_lp_asb_x) -xo-> u_f_0R02 (col_h9_l4_lp_asb_x) -xo-> u_f_0R03 (col_h9_l4_lp_asb_nx)
// -> each frame ret through the die_b178 return-lane cone (ret_cone, die_ret_cone.py: hop-0 ICG, real dsfd_dvrlyh
// stations, land-plan flight, real dsfd_dvland_70 at the die K strap, real die reset wavefront) -> ot_s81sl_capc5r_e6
// (rt = {0R03,0R02,0R01,0L03,0L02,0L01}).  +byp=1 feeds the frame ret pins straight to CAP (tok16 form, control).
// BOUND: one uniform clock phase on every frame region, CAP clock and die root clock; the XS -> 0L01/0R01 x lanes and the
// 0L02 -> 0L03 / 0R02 -> 0R03 x relay lanes (forwarded on the upstream xok) are NOT simulated (direct abutment).
module tb_dense_gb_slice;
    reg clk = 0;
    always #0.5 clk = ~clk;
    reg rst_n = 0;
    integer cyc = 0, T = 4000, mut = 0, byp = 0;
    reg [2:0] gv = 0;
    reg [20:0] gi = 0;
    reg [3071:0] gd = 0;
    reg iv = 0;
    reg [159:0] id = 0;
    wire xv, xf;
    wire [1100:0] xw;
    ot_s81sl_xs4 u_xs (.clk(clk), .rst_n(rst_n), .g_v(gv), .g_fam(3'd0), .g_idx(gi), .g_d(gd),
        .is_v(iv), .is_d(id), .xw_v(xv), .xw_d(xw), .fault(xf));
    reg [1:0] mkq = 0;
    always @(posedge clk) if (!rst_n) mkq <= 0; else mkq <= {mkq[0],1'b1};
    wire [1103:0] x = {xw[1100:565],xw[0],mkq[1],xw[564:0],mkq[1]};
    wire [1103:0] xo_0L01, xo_0L02, xo_0R01, xo_0R02;
    wire [3:0] xok_0L01, xok_0L02, xok_0R01, xok_0R02;
    wire [69:0] r [0:5];   // 0L01 0L02 0L03 0R01 0R02 0R03
    col_h10_l4_lp_asb_x #(.INSTANCE("u_f_0L01")) u_f_0L01 (.ck_r0(clk), .ck_r1(clk), .ck_r2(clk), .rst_n(rst_n), .x(x), .xo(xo_0L01), .xok(xok_0L01), .ret(r[0]));
    col_h9_l4_lp_asb_x  #(.INSTANCE("u_f_0L02")) u_f_0L02 (.ck_r0(clk), .ck_r1(clk), .ck_r2(clk), .rst_n(rst_n), .x(xo_0L01), .xo(xo_0L02), .xok(xok_0L02), .ret(r[1]));
    col_h9_l4_lp_asb_nx #(.INSTANCE("u_f_0L03")) u_f_0L03 (.ck_r0(clk), .ck_r1(clk), .ck_r2(clk), .rst_n(rst_n), .x(xo_0L02), .ret(r[2]));
    col_h10_l4_lp_asb_x #(.INSTANCE("u_f_0R01")) u_f_0R01 (.ck_r0(clk), .ck_r1(clk), .ck_r2(clk), .rst_n(rst_n), .x(x), .xo(xo_0R01), .xok(xok_0R01), .ret(r[3]));
    col_h9_l4_lp_asb_x  #(.INSTANCE("u_f_0R02")) u_f_0R02 (.ck_r0(clk), .ck_r1(clk), .ck_r2(clk), .rst_n(rst_n), .x(xo_0R01), .xo(xo_0R02), .xok(xok_0R02), .ret(r[4]));
    col_h9_l4_lp_asb_nx #(.INSTANCE("u_f_0R03")) u_f_0R03 (.ck_r0(clk), .ck_r1(clk), .ck_r2(clk), .rst_n(rst_n), .x(xo_0R02), .ret(r[5]));
    wire [69:0] l [0:5];
    wire land_fault;
    ret_cone u_rc (.ck(clk), .rst_n(rst_n),
        .ret_0L01(r[0]), .lnd_0L01(l[0]), .ret_0L02(r[1]), .lnd_0L02(l[1]), .ret_0L03(r[2]), .lnd_0L03(l[2]),
        .ret_0R01(r[3]), .lnd_0R01(l[3]), .ret_0R02(r[4]), .lnd_0R02(l[4]), .ret_0R03(r[5]), .lnd_0R03(l[5]), .land_fault(land_fault));
    wire [69:0] c [0:5];
    genvar g;
    generate for (g = 0; g < 6; g = g + 1) begin : g_sel
        assign c[g] = byp ? r[g] : l[g];
    end endgenerate
    reg cfgv = 0;
    reg [159:0] cfgd = 0;
    reg [159:0] cfgmem [0:0];
    wire [279:0] rw = {c[3], c[2], c[1], c[0]};
    wire [139:0] re = {c[5], c[4]};
    wire [5:0] sv;
    wire [71:0] sa;
    wire [191:0] sd;
    wire [3:0] nv;
    wire [47:0] na;
    wire [127:0] nd;
    wire cf;
    ot_s81sl_capc5r_e6 u_cap (.rt_w(rw), .rt_e(re), .cfg_v(cfgv), .cfg_d(cfgd),
        .cw_s_v(sv), .cw_s_a(sa), .cw_s_d(sd), .cw_n_v(nv), .cw_n_a(na), .cw_n_d(nd), .fault(cf),
        .ck_rt(clk), .ck_cw(clk), .ck_ce(clk), .ck_rn(clk), .ck_rs(clk),
        .rst_n_rt(rst_n), .rst_n_cw(rst_n), .rst_n_ce(rst_n), .rst_n_rn(rst_n), .rst_n_rs(rst_n));
    reg [8191:0] dir;
    integer fd, rc, nev = 0, ep = 0, et [0:511], ek [0:511], ti, ki, j;
    reg [1030:0] eh [0:511], hi;
    initial begin
        void'($value$plusargs("T=%d",T));
        void'($value$plusargs("mut=%d",mut));
        void'($value$plusargs("byp=%d",byp));
        if (!$value$plusargs("OT_ROM_DIR=%s",dir)) $fatal(1,"missing ROM directory");
        $readmemh({dir,"/capture.hex"},cfgmem);
        fd = $fopen({dir,"/dense_stim.txt"},"r");
        if (!fd) $fatal(1,"missing programme");
        while (!$feof(fd)) begin
            rc = $fscanf(fd,"%d %d %h\n",ti,ki,hi);
            if (rc == 3) begin et[nev]=ti; ek[nev]=ki; eh[nev]=hi; nev=nev+1; end
        end
        $fclose(fd);
    end
    always @(negedge clk) begin
        gv = 0; gi = 0; gd = 0; iv = 0; id = 0; cfgv = 0;
        if (cyc == 15) rst_n = 1;
        if (cyc == 150) begin cfgv = 1; cfgd = cfgmem[0]; end
        while (ep < nev && et[ep] == cyc) begin
            if (ek[ep] == 0) begin iv = 1; id = eh[ep][159:0]; end
            else begin
                gv[0] = 1; gi[6:0] = eh[ep][1030:1024]; gd[1023:0] = eh[ep][1023:0];
                if (mut && gi[6:0] == 0) gd[531:0] = 0;
            end
            ep = ep+1;
        end
    end
    reg [5:0] ffr = 0;
    integer lff = -1;
    always @(posedge clk) begin
        cyc <= cyc+1;
        if (cyc > 30 && xv && (xw[550] || xw[551]))
            $display("XCTRL %0d cfg=%b go=%b",cyc,xw[551],xw[550]);
        for (j=0;j<6;j=j+1) begin
            if (rst_n && r[j][1]) $display("RET %0d %0d %017h",j,cyc,r[j][67:2]);
            if (rst_n && l[j][1]) $display("LND %0d %0d %017h",j,cyc,l[j][67:2]);
            if (r[j][69] && !ffr[j]) begin ffr[j] = 1; $display("FRAME_FAULT %0d %0d",j,cyc); end
        end
        if (land_fault && lff < 0) begin lff = cyc; $display("LAND_FAULT %0d",cyc); end
        for (j=0;j<6;j=j+1) if (sv[j]) $display("CAP S %0d %0d %0d %08h",cyc,j,sa[12*j+:12],sd[32*j+:32]);
        for (j=0;j<4;j=j+1) if (nv[j]) $display("CAP N %0d %0d %0d %08h",cyc,j,na[12*j+:12],nd[32*j+:32]);
        if (cyc == T) begin
            $display("SLICE_END cycles=%0d events=%0d consumed=%0d xs_fault=%b frame_fault=%b land_fault=%b cap_fault=%b mutant=%0d byp=%0d",
                     cyc,nev,ep,xf,ffr,land_fault,cf,mut,byp);
            $finish;
        end
    end
endmodule
