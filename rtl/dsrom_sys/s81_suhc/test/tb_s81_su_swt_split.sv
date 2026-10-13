`timescale 1ns/1ps
// Lockstep bench of the split SW tap (el1013-s81su-qual): ot_s81_su_swtl + ot_s81_su_swth against the single rate-aligned
// tap ot_s81_su_swt (the tap the SU gates qualified, full m0 PASS 0/1722) at the production parameters.  Contract: every
// output of the pair at cycle t equals the single tap's output at cycle t - 1 (the pin-flop stage), from the first cycle
// out of reset, for legal traffic (job announce, descriptor alone in slot 0, S_RD-full operand cycles, idle gaps),
// illegal traffic (partial cycles, a descriptor sharing its cycle: o_fo), foreign job kinds, lane faults and a reset in
// mid job.  The lane-fault input has a pin flop in both, so the pair takes it one cycle later (i_f delayed here).
// Negative controls: -GMUT=1 the low half's pass tag one pass early, -GMUT=2 the high half with one register.
module tb_s81_su_swt_split #(parameter integer MUT = 0, NCYC = 60000);
    localparam integer S_RD = 16, NSQ = 8, SW_W = 1024, NCH = 32, DW = S_RD * 512, HW = S_RD * 256;
    reg clk = 0, rst = 0;
    always #1 clk = ~clk;
    reg         st;  reg [3:0] kind; reg [1:0] gsel; reg fp4; reg [7:0] jid; reg [S_RD-1:0] v; reg [DW-1:0] d;
    reg [NCH-1:0] f, f1;
    wire [DW-1:0] r_d, n_d;
    wire [3:0]  r_gv, r_uv, n_gv, n_uv;  wire [11:0] r_t, n_t;  wire [31:0] r_w, r_lim, n_w, n_lim;  wire [13:0] r_ob, n_ob;
    wire        r_fu, r_fo, r_al, r_de, r_rd, n_fu, n_fo, n_al, n_de, n_rd;  wire [7:0] r_rj, n_rj;
    ot_s81_su_swt #(.SW_W(SW_W), .S_RD(S_RD), .NSQ(NSQ), .NCH(NCH)) u_ref (
        .clk(clk), .rst_in(rst), .dn_st_i(st), .dn_kind_i(kind), .dn_gsel_i(gsel), .dn_fp4_i(fp4), .dn_jid_i(jid),
        .dn_v_i(v), .dn_d_i(d), .i_f(f), .e_d(r_d), .e_gv(r_gv), .e_uv(r_uv), .e_t(r_t), .e_w(r_w), .e_lim(r_lim),
        .e_ob(r_ob), .o_fu(r_fu), .o_fo(r_fo), .o_alive(r_al), .o_den(r_de), .o_rdy(r_rd), .o_rjid(r_rj));
    ot_s81_su_swtl #(.SW_W(SW_W), .S_RD(S_RD), .NSQ(NSQ), .NCH(NCH), .MUT(MUT == 1)) u_l (
        .clk(clk), .rst_in(rst), .dn_st_i(st), .dn_kind_i(kind), .dn_gsel_i(gsel), .dn_fp4_i(fp4), .dn_jid_i(jid),
        .dn_v_i(v), .dn_d_i(d[HW-1:0]), .i_f(f1), .e_d(n_d[HW-1:0]), .e_gv(n_gv), .e_uv(n_uv), .e_t(n_t), .e_w(n_w),
        .e_lim(n_lim), .e_ob(n_ob), .o_fu(n_fu), .o_fo(n_fo), .o_alive(n_al), .o_den(n_de), .o_rdy(n_rd), .o_rjid(n_rj));
    ot_s81_su_swth #(.S_RD(S_RD), .MUT(MUT == 2)) u_h (.clk(clk), .dn_d_i(d[DW-1:HW]), .e_d(n_d[DW-1:HW]));
    // the single tap's outputs one cycle back
    localparam integer OW = DW + 8 + 12 + 64 + 14 + 5 + 8;
    wire [OW-1:0] r_o = {r_d, r_gv, r_uv, r_t, r_w, r_lim, r_ob, r_fu, r_fo, r_al, r_de, r_rd, r_rj};
    wire [OW-1:0] n_o = {n_d, n_gv, n_uv, n_t, n_w, n_lim, n_ob, n_fu, n_fo, n_al, n_de, n_rd, n_rj};
    reg  [OW-1:0] r_q;
    always @(posedge clk) begin r_q <= r_o; f1 <= f; end
    integer cyc = 0, bad = 0, chk = 0, hold = 4;
    integer n_desc = 0, n_g = 0, n_u = 0, c_fo = 0, c_fu = 0, n_pass[0:3], n_job = 0, n_wnz = 0;
    // traffic generator
    integer state = 0, left = 0, gap = 0, i;
    reg [31:0] rnd;
    wire ill = cyc > 7 * NCYC / 8;                               // illegal traffic (sticky o_fo) only in the last eighth
    task automatic rdata;
        integer k;
        begin for (k = 0; k < DW / 32; k = k + 1) d[32 * k +: 32] = $urandom; end
    endtask
    initial begin for (i = 0; i < 4; i = i + 1) n_pass[i] = 0; st = 0; kind = 0; gsel = 0; fp4 = 0; jid = 0; v = 0; d = 0; f = 0; f1 = 0; end
    always @(negedge clk) begin
        cyc <= cyc + 1;
        rnd = $urandom;
        if (cyc == 6) rst <= 1'b1;
        if (cyc == NCYC / 2) rst <= 1'b0;                         // a reset in mid traffic
        if (cyc == NCYC / 2 + 5) rst <= 1'b1;
        st <= 1'b0; v <= 0; rdata(); kind <= rnd[3:0]; gsel <= rnd[5:4]; fp4 <= rnd[6]; jid <= rnd[15:8];
        f <= (rnd[31:26] == 6'h25 && cyc > 3 * NCYC / 8 && cyc < 3 * NCYC / 8 + 2000) ? (32'd1 << rnd[19:15]) : 32'd0;   // lane faults: sticky o_fu until the reset
        case (state)
            0: if (rnd[18:16] == 0) begin st <= 1'b1; kind <= (rnd[7:4] < 12) ? 4'd3 : rnd[3:0]; state <= 1; gap <= rnd[21:20]; n_job <= n_job + 1; end
            1: if (gap != 0) gap <= gap - 1;
               else begin v <= (rnd[27:23] == 0 && ill) ? 16'h0003 : 16'h0001; state <= 2; left <= 4 * (1 + rnd[11:9]) * (1 + rnd[14:12]); end
            2: if (rnd[22:20] == 0) v <= 0;                                         // an idle spine cycle
               else if (rnd[31:25] == 0 && ill) v <= {rnd[15:1], 1'b1};                    // a partial operand cycle (fault 5)
               else begin v <= 16'hffff; left <= left - 1; if (left <= 1) state <= 0; end
        endcase
        if (rnd[31:22] == 0 && state == 2) begin st <= 1'b1; kind <= 4'd3; state <= 1; gap <= 0; end   // announce over a running job
    end
    always @(posedge clk) begin
        if (!rst) hold <= 4;                                       // not compared: reset asserted and the cycle after
        else if (hold != 0) hold <= hold - 1;
        else begin
            chk <= chk + 1;
            if (n_o !== r_q) begin
                bad <= bad + 1;
                if (bad < 6) $display("mismatch cyc %0d: d %0d gv %h/%h uv %h/%h t %h/%h w %h/%h lim %h/%h ob %h/%h st %b/%b", cyc,
                    n_d !== r_q[OW-1 -: DW], n_gv, r_q[OW-DW-1 -: 4], n_uv, r_q[OW-DW-5 -: 4], n_t, r_q[OW-DW-9 -: 12],
                    n_w, r_q[OW-DW-21 -: 32], n_lim, r_q[OW-DW-53 -: 32], n_ob, r_q[26:13], {n_fu, n_fo, n_al, n_de, n_rd}, r_q[12:8]);
            end
            if (|n_gv) n_g <= n_g + 1;
            if (|n_uv) n_u <= n_u + 1;
            for (i = 0; i < 4; i = i + 1) if (n_gv[i] || n_uv[i]) n_pass[i] <= n_pass[i] + 1;
            if (n_fo) c_fo <= c_fo + 1;
            if (n_fu) c_fu <= c_fu + 1;
            if ((|n_gv) && n_w != 0) n_wnz <= n_wnz + 1;
        end
        if (cyc == NCYC) begin
            $display("SWT_SPLIT mut=%0d cyc=%0d checks=%0d mismatches=%0d jobs=%0d g=%0d u=%0d pass=%0d/%0d/%0d/%0d fo_cyc=%0d fu_cyc=%0d wnz=%0d",
                     MUT, cyc, chk, bad, n_job, n_g, n_u, n_pass[0], n_pass[1], n_pass[2], n_pass[3], c_fo, c_fu, n_wnz);
            if (bad == 0 && chk > NCYC - 100 && n_g > 500 && n_u > 500 && n_pass[0] > 100 && n_pass[1] > 100 && n_pass[2] > 100
                && n_pass[3] > 100 && c_fo > 10 && c_fu > 10 && n_wnz > 100) $display("SWT_SPLIT PASS");
            else $display("SWT_SPLIT FAIL");
            $finish;
        end
    end
endmodule
