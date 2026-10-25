`timescale 1ns/1ps
// DRIVE-S81-GUPROP bench (10-20): the SW CONSUMER of the GU_PROP gate/up gather on ONE beat leaf -- copy of tb_vs_lowered.sv
// (LB2-S81/CC-VS) with (a) kind 6 beats = RD row pairs written into the leaf store exactly as ot_s81sl_xr's RD unpacker
// does (one row pair a cycle on vp's row-pair write port sw_v / sw_a / sw_m = 8'hFF / sw_d = rd.mem[idx]; the payload is
// the SOURCE slice's capture row pair named by the compiler's gather record, tools/s81_dv/layer_prog/gu_gather.py), and
// (b) parameter VS_MUT (ot_s81sl_vs negative controls).  Real ot_s81sl_vp + _vs + _vsw + RA lane pair + _vq as the parent.
// Prints GUPROP_SPAN first RD edge -> SW command -> last result.  Checks as the parent: SW result rows (RDOUT) and the vq
// XQ beats bit exact vs the layer fixture (BF16(route_w) / quant2, golden order), no fault, slot within VS_DUR.
module tb_vs_guprop #(parameter integer VS_MUT = 0);
    // the leaf (vq straps), expected XQ beats and the last programme edge: plusargs (one build for every leaf / mutant)
    integer SID = 0, KL = 0, NXQ = 0, LAST = 1000;
    reg [3:0] sid_s = 0; reg [2:0] k_s = 0;
    initial begin
        if (!$value$plusargs("sid=%d", SID)) SID = 0;
        if (!$value$plusargs("k=%d", KL)) KL = 0;
        if (!$value$plusargs("nxq=%d", NXQ)) NXQ = 0;
        if (!$value$plusargs("last=%d", LAST)) LAST = 1000;
        sid_s = SID[3:0]; k_s = KL[2:0];
    end
    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    reg [127:0] img [0:1023]; reg imgv [0:1023];
    reg [255:0] prog [0:127];
    reg [255:0] exp_ [0:255]; reg [7:0] expm [0:255];
    reg [531:0] xqe [0:7]; reg [7:0] xqi [0:7];
    reg [255:0] rdm [0:255];
    integer nrd = 0, t_rd0 = -1, t_rdl = -1, t_sw = -1, t_end = 0;
    initial begin
        $readmemh("img.mem", img); $readmemh("imgv.mem", imgv); $readmemh("prog.mem", prog);
        $readmemh("exp.mem", exp_); $readmemh("expm.mem", expm); $readmemh("xq.mem", xqe); $readmemh("xqi.mem", xqi);
        $readmemh("rd.mem", rdm);
    end
    reg rst_n = 1'b0, c_v = 1'b0, sw_v = 1'b0;
    reg [159:0] c_d = 0; reg [9:0] sw_a = 0; reg [255:0] sw_d = 0; reg [7:0] sw_m = 0;
    wire lo_v; wire [255:0] lo_d; wire fp, fs, fq;
    wire s_v; wire [159:0] s_d; wire x_rv, x_qv, x_wv; wire [9:0] x_ra, x_wa; wire [7:0] x_wm; wire [255:0] x_qd, x_wd;
    wire u_v, um_v, um_q, um_b; wire [2:0] u_i; wire [255:0] u; wire [7:0] um_i;
    wire swv, swvi, swfi; wire [255:0] swd; wire [31:0] sww, swl; wire [63:0] swri;
    wire rav, ravi, rafi, rfv, rff; wire [31:0] rax, rfmx; wire [30:0] rfu, rfu2, rari;
`ifdef OT_FINAL_FFN_POST
    wire hw_v, hw_hf, hr_v, hr_hf, hq_v, fn;
    wire [2:0] hw_j, hr_j;
    wire [255:0] hw_d, hq_d;
    ot_s81sl_vn u_n (.clk(clk), .rst_n(rst_n), .hw_v(hw_v), .hw_j(hw_j), .hw_hf(hw_hf), .hw_d(hw_d),
        .hr_v(hr_v), .hr_j(hr_j), .hr_hf(hr_hf), .hq_v(hq_v), .hq_d(hq_d), .n_go(1'b0), .n_pre(128'd0),
        .wl_v(1'b0), .wl_i(3'd0), .wl_d(256'd0), .rb_v(1'b0), .rb_d(32'd0),
        .p_v(), .p_d(), .y_v(), .y_i(), .y(), .fault(fn));
`endif
    ot_s81sl_vp u_p (.clk(clk), .rst_n(rst_n), .c_v(c_v), .c_d(c_d), .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d),
        .cw_v(2'b00), .cw_a(24'd0), .cw_d(64'd0), .lo_v(lo_v), .lo_d(lo_d),
        .s_v(s_v), .s_d(s_d), .x_rv(x_rv), .x_ra(x_ra), .x_qv(x_qv), .x_qd(x_qd), .x_wv(x_wv), .x_wa(x_wa), .x_wm(x_wm), .x_wd(x_wd),
`ifdef OT_FINAL_FFN_POST
        .hw_v(hw_v), .hw_j(hw_j), .hw_hf(hw_hf), .hw_d(hw_d), .hr_v(hr_v), .hr_j(hr_j), .hr_hf(hr_hf), .hq_v(hq_v), .hq_d(hq_d),
`else
        .hw_v(), .hw_j(), .hw_hf(), .hw_d(), .hr_v(), .hr_j(), .hr_hf(), .hq_v(1'b0), .hq_d(256'd0),
`endif
        .n_go(), .n_pre(), .m_v(), .m_q(), .m_b(), .m_i(), .wl_v(), .wl_i(), .wl_d(), .fault(fp));
    ot_s81sl_vs #(.MUT(VS_MUT)) u_s (.clk(clk), .rst_n(rst_n), .s_v(s_v), .s_d(s_d),
        .x_rv(x_rv), .x_ra(x_ra), .x_qv(x_qv), .x_qd(x_qd), .x_wv(x_wv), .x_wa(x_wa), .x_wm(x_wm), .x_wd(x_wd),
        .u_v(u_v), .u_i(u_i), .u(u), .um_v(um_v), .um_q(um_q), .um_b(um_b), .um_i(um_i),
        .sw_v(swv), .sw_d(swd), .sw_w(sww), .sw_lim(swl), .sw_vi(swvi), .sw_ri(swri), .sw_fi(swfi),
        .ra_v(rav), .ra_x(rax), .ra_vi(ravi), .ra_ri(rari), .ra_fi(rafi),
        .ve_rv(), .ve_rc(), .ve_rh(), .ve_rk(), .ve_rw(), .ve_pv(1'b0), .ve_pc(2'd0), .ve_phh(32'd0), .ve_pkk(32'd0),
        .ve_pdd(32'd0), .ve_av(), .ve_ac(), .ve_ah(), .ve_aval(), .ve_ag(), .ve_ov(1'b0), .ve_oc(2'd0), .ve_oy(128'd0),
        .ve_fi(1'b0), .e_v(), .e_c(), .e_d(), .g_v(1'b0), .g_c(2'd0), .g_d(32'd0), .fault(fs));
    ot_s81sl_vsw u_w (.clk(clk), .rst_n(rst_n), .i_v(swv), .i_d(swd), .i_w(sww), .i_lim(swl), .o_v(swvi), .o_d(swri), .o_f(swfi));
    dsfd_su_t_rxsf u_rf (.ck(clk), .rst(rst_n), .i_v(rav), .i_x(rax), .o_v(rfv), .o_u(rfu), .o_u2(rfu2), .o_mx(rfmx), .o_f(rff));
    dsfd_su_t_rxsb u_rb (.ck(clk), .rst(rst_n), .i_v(rfv), .i_u(rfu), .i_u2(rfu2), .i_mx(rfmx), .i_f(rff), .o_v(ravi), .o_r(rari), .o_f(rafi));
    wire xf_v, xf_s; wire [275:0] xf;
    ot_s81sl_vq u_q (.clk(clk), .rst_n(rst_n), .y_v(1'b0), .y_i(3'd0), .y(128'd0), .u_v(u_v), .u_i(u_i), .u(u),
        .sid(sid_s), .k(k_s), .m_v(1'b0), .m_q(1'b0), .m_b(1'b0), .m_i(8'd0), .um_v(um_v), .um_q(um_q), .um_b(um_b), .um_i(um_i),
        .xf_v(xf_v), .xf_s(xf_s), .xf(xf), .fault(fq));

    // vq fragments -> ring beats (as the ring stop)
    reg [1103:0] xo = 0; reg [1:0] frn = 0; reg xo_v = 0;
    always @(posedge clk) begin
        xo_v <= 1'b0;
        if (xf_v) begin
            if (xf_s) begin xo[275:0] <= xf; frn <= 2'd1; end
            else begin xo[276 * frn +: 276] <= xf; frn <= frn + 2'd1; if (frn == 2'd3) xo_v <= 1'b1; end
        end
    end
    integer cyc = 0, pc = 0, st = 0, wt = 0, idl = 0, k, w, nxq = 0, npair = 0, cidx = 0, cpair = 0, cop = 0;
    integer errs = 0, slot_err = 0, miss = 0, ncmd = 0, nrw = 0, nck = 0, tc = -1, tl = 0, cdur = 0, top = 0;
`ifdef OT_FINAL_FFN_POST
    always @(posedge clk) if (x_wv || u_v || hw_v) tl <= cyc;
`else
    always @(posedge clk) if (x_wv || u_v) tl <= cyc;
`endif
    always @(posedge clk) if (x_wv || u_v) t_end <= cyc;
    task close_cmd;
        begin
            if (tc >= 0) begin
                $display("VSOP op=%0d cmd=%0d cycles_cmd_to_last_result=%0d slot=%0d", top, tc, tl - tc, cdur);
                if (tl - tc > cdur || tl < tc) begin slot_err = slot_err + 1; $display("SLOT_OVERRUN op=%0d cmd=%0d", top, tc); end
            end
        end
    endtask
    always @(posedge clk) begin
        cyc <= cyc + 1;
        c_v <= 1'b0; sw_v <= 1'b0;
        if (cyc == 3) rst_n <= 1'b1;
        // upstream operand rows (the deliveries of the producing families), before the programme
        if (cyc >= 10 && cyc < 522 && (imgv[2 * (cyc - 10)] || imgv[2 * (cyc - 10) + 1])) begin
            sw_v <= 1'b1; sw_a <= 2 * (cyc - 10); sw_d <= {img[2 * (cyc - 10) + 1], img[2 * (cyc - 10)]};
            sw_m <= {{4{imgv[2 * (cyc - 10) + 1]}}, {4{imgv[2 * (cyc - 10)]}}};
        end
        case (st)
            0: if (cyc >= 530) begin
                   // timed beats: kind 1 vp command (target 0), kind 3 row write (target 5), at their calendar edge
                   if (prog[pc][255:252] == 4'd1 || prog[pc][255:252] == 4'd3 || prog[pc][255:252] == 4'd4 || prog[pc][255:252] == 4'd5 || prog[pc][255:252] == 4'd6) begin
                       if (prog[pc][251:228] < cyc) begin miss = miss + 1; $display("MISSED beat %0d at %0d", pc, prog[pc][251:228]); pc = pc + 1; end
                       else if (prog[pc][251:228] == cyc) begin
                           if (prog[pc][255:252] == 4'd6) begin
                               // RD row pair (xr RD unpacker -> the leaf's row-pair write port), one a cycle
                               sw_v <= 1'b1; sw_a <= prog[pc][9:0]; sw_m <= 8'hFF; sw_d <= rdm[prog[pc][25:16]];
                               nrd = nrd + 1; if (t_rd0 < 0) t_rd0 = cyc; t_rdl = cyc;
                           end else if (prog[pc][255:252] == 4'd1) begin
                               if (prog[pc][3:0] == 4'd8) t_sw = cyc;
                               close_cmd();
                               c_v <= 1'b1; c_d <= prog[pc][159:0]; tc = cyc; tl = cyc; top = prog[pc][227:224];
                               cdur = prog[pc][201:186]; ncmd = ncmd + 1;
                           end else if (prog[pc][255:252] == 4'd5) begin
                               // Fixed calendar idle edge; never waits on runtime ready/busy.
                           end else if (prog[pc][255:252] == 4'd4) begin
                               close_cmd(); tc = -1; c_v <= 1'b1; c_d <= prog[pc][159:0]; ncmd = ncmd + 1;
                           end else begin
                               sw_v <= 1'b1; sw_a <= prog[pc][9:0]; sw_m <= {4'd0, prog[pc][13:10]};
                               sw_d <= {128'd0, prog[pc][141:14]}; nrw = nrw + 1;
                           end
                           pc = pc + 1;
                       end
                   end else begin st = 1; wt = 0; idl = 0; end
               end
            1: begin                                     // drain: vs idle 8 edges, then the result read-back
                   wt = wt + 1;
                   idl = (!u_s.busy) ? idl + 1 : 0;
                   if (idl == 8) begin close_cmd(); st = 2; end
                   else if (wt > 4000) begin $display("DRAIN TIMEOUT"); errs = errs + 1; close_cmd(); st = 2; end
               end
            2: if (prog[pc][255:252] == 4'd2) begin
                   cop = prog[pc][227:224]; cidx = prog[pc][223:210]; cpair = prog[pc][209:202];
                   c_v <= 1'b1; c_d <= {128'd0, cpair[7:0], 10'd0, prog[pc][9:0], 4'd6}; npair = 0; st = 3; wt = 0;
               end else begin st = 4; wt = 0; end
            3: begin
                   wt = wt + 1;
                   if (lo_v) begin
                       for (w = 0; w < 8; w = w + 1)
                           if (expm[cidx + npair][w] && lo_d[32 * w +: 32] !== exp_[cidx + npair][32 * w +: 32]) begin
                               if (errs < 12) $display("MISMATCH check %0d pair %0d word %0d got %h want %h", cop, npair, w,
                                                       lo_d[32 * w +: 32], exp_[cidx + npair][32 * w +: 32]);
                               errs = errs + 1;
                           end
                       nck = nck + 1; npair = npair + 1;
                   end
                   if (npair == cpair && wt > cpair + 8) begin pc = pc + 1; st = 2; end
                   else if (wt > 1000) begin $display("RDOUT TIMEOUT"); errs = errs + 1; pc = pc + 1; st = 2; end
               end
            4: begin
                   wt = wt + 1;
                   if (wt == 100) begin
                       $display("GUPROP_SPAN rd_pairs=%0d rd_first=%0d rd_last=%0d sw_cmd=%0d last_result=%0d rd_to_last_result=%0d sw_to_last_result=%0d",
                                nrd, t_rd0, t_rdl, t_sw, t_end, t_end - t_rd0, t_end - t_sw);
                       $display("SLVSL sid=%0d k=%0d cmds=%0d rowwrites=%0d checked_pairs=%0d xq=%0d/%0d errors=%0d slot_overruns=%0d missed=%0d fault=vp%b/vs%b/vq%b",
                                SID, KL, ncmd, nrw, nck, nxq, NXQ, errs, slot_err, miss, fp, fs, fq);
                       if (errs == 0 && slot_err == 0 && miss == 0 && nxq == NXQ && !fp && !fs && !fq && nck > 0
`ifdef OT_FINAL_FFN_POST
                           && !fn
`endif
                           ) $display("PASS");
                       else $display("FAIL");
                       $finish;
                   end
               end
            default: ;
        endcase
        if (xo_v) begin
            if (nxq >= NXQ || xo[3:1] !== 3'd1 || xo[21 +: 532] !== xqe[nxq] || xo[20:13] !== xqi[nxq]) begin
                errs = errs + 1;
                $display("XQ MISMATCH beat %0d kind %0d idx %h/%h e0 %h/%h e1 %h/%h", nxq, xo[3:1], xo[20:13], xqi[nxq],
                         xo[21 + 256 +: 10], xqe[nxq][256 +: 10], xo[21 + 522 +: 10], xqe[nxq][522 +: 10]);
            end
            nxq = nxq + 1;
        end
        if (cyc == LAST + 8000) begin $display("GLOBAL TIMEOUT"); $display("FAIL"); $finish; end
    end
endmodule
