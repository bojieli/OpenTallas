`timescale 1ns/1ps
// Selected source components at their real pins. All five CAP clocks have a
// common, explicitly pinned phase in this bounded source test.
module tb_dense_xs_cap;
    reg clk = 0;
    always #0.5 clk = ~clk;
    reg rst_n = 0;
    integer cyc = 0, T = 4000, mut = 0;
    reg [2:0] gv = 0;
    reg [20:0] gi = 0;
    reg [3071:0] gd = 0;
    reg iv = 0;
    reg [159:0] id = 0;
    wire xv, xf;
    wire [1100:0] xw;
    ot_s81sl_xs4 u_xs (.clk(clk), .rst_n(rst_n), .g_v(gv), .g_fam(3'd0), .g_idx(gi), .g_d(gd),
        .is_v(iv), .is_d(id), .xw_v(xv), .xw_d(xw), .fault(xf));
    reg [7:0] mkq = 0;
    always @(posedge clk) if (!rst_n) mkq <= 0; else mkq <= {mkq[6:0],1'b1};
    // Actual slice chain word (no synthetic frame-return injection).
    wire [1103:0] x = {xw[1100:565],xw[0],mkq[7],xw[564:0],mkq[7]};
    wire [1103:0] xo;
    wire [3:0] xok;
    wire [69:0] ret;
    col_h9_l4_lp_b #(.INSTANCE("f")) u_frame (.clk(clk), .cr(clk), .cr_s(clk), .rst_n(rst_n),
        .x(x), .xk({4{clk}}), .xo(xo), .xok(xok), .ret(ret));
    reg cfgv = 0;
    reg [159:0] cfgd = 0;
    reg [159:0] cfgmem [0:0];
    // Inactive lanes carry their released reset marker. The active frame is W0.
    wire [279:0] rw = {70'd1,70'd1,70'd1,ret};
    wire [279:0] re = {4{70'd1}};
    wire [5:0] sv;
    wire [71:0] sa;
    wire [191:0] sd;
    wire [3:0] nv;
    wire [47:0] na;
    wire [127:0] nd;
    wire cf;
    ot_s81sl_capc5r u_cap (.rt_w(rw), .rt_e(re), .cfg_v(cfgv), .cfg_d(cfgd),
        .cw_s_v(sv), .cw_s_a(sa), .cw_s_d(sd), .cw_n_v(nv), .cw_n_a(na), .cw_n_d(nd), .fault(cf),
        .ck_rt(clk), .ck_cw(clk), .ck_ce(clk), .ck_rn(clk), .ck_rs(clk),
        .rst_n_rt(rst_n), .rst_n_cw(rst_n), .rst_n_ce(rst_n), .rst_n_rn(rst_n), .rst_n_rs(rst_n));
    reg [8191:0] dir;
    integer fd, rc, nev = 0, ep = 0, et [0:511], ek [0:511], ti, ki, j;
    reg [1030:0] eh [0:511], hi;
    initial begin
        void'($value$plusargs("T=%d",T));
        void'($value$plusargs("mut=%d",mut));
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
                // Same compiled mechanism, causal input corruption control.
                if (mut && gi[6:0] == 0) gd[531:0] = 0;
            end
            ep = ep+1;
        end
    end
    always @(posedge clk) begin
        cyc <= cyc+1;
        if (cyc > 30 && xv && (xw[550] || xw[551]))
            $display("XCTRL %0d cfg=%b go=%b",cyc,xw[551],xw[550]);
        if (rst_n && ret[1]) $display("RET %0d %017h",cyc,ret[67:2]);
        for (j=0;j<6;j=j+1) if (sv[j]) $display("CAP S %0d %0d %0d %08h",cyc,j,sa[12*j+:12],sd[32*j+:32]);
        for (j=0;j<4;j=j+1) if (nv[j]) $display("CAP N %0d %0d %0d %08h",cyc,j,na[12*j+:12],nd[32*j+:32]);
        if (cyc == T) begin
            $display("DENSE_SOURCE_END cycles=%0d events=%0d consumed=%0d xs_fault=%b frame_fault=%b cap_fault=%b mutant=%0d",cyc,nev,ep,xf,ret[69],cf,mut);
            $finish;
        end
    end
endmodule
