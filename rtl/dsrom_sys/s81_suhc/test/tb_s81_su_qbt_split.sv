`timescale 1ns/1ps
// Lockstep bench of the split QB tap (el1013-s81su, 2026-10-13): ot_s81_su_qbtl + the data half-tap ot_s81_su_swth
// against the single rate-aligned tap ot_s81_su_qbt (g_al, the tap of the SU composition gate: full m0 PASS 0/1722 at
// 3,149 cycles) at the production parameters.  Contract: every output of the pair equals the single tap's output in
// the SAME cycle, from the first cycle out of reset, for legal traffic (job announce, descriptor alone in slot 0,
// S_RD-full operand cycles, idle gaps), illegal traffic (partial cycles, a descriptor sharing its cycle: o_fo),
// foreign job kinds, an announce over a running job and a reset in mid job.
// Negative controls: -GMUT=1 the low half's pass tag one pass early, -GMUT=2 the high half with one register.
module tb_s81_su_qbt_split #(parameter integer MUT = 0, NCYC = 60000);
    localparam integer S_RD = 16, NPB = 8, QB_NB = 32, DW = S_RD * 512, HW = S_RD * 256;
    reg clk = 0, rst = 0;
    always #1 clk = ~clk;
    reg         st;  reg [3:0] kind; reg [1:0] gsel; reg fp4; reg [7:0] jid; reg [S_RD-1:0] v; reg [DW-1:0] d;
    wire [DW-1:0] r_d, n_d;
    wire [15:0] r_v, n_v;  wire [191:0] r_t, n_t;  wire [13:0] r_ob, n_ob;  wire r_f4, n_f4;
    wire        r_fu, r_fo, r_al, r_de, r_rd, n_fu, n_fo, n_al, n_de, n_rd;  wire [7:0] r_rj, n_rj;
    ot_s81_su_qbt #(.QB_NB(QB_NB), .S_RD(S_RD), .NPB(NPB)) u_ref (
        .clk(clk), .rst_in(rst), .dn_st_i(st), .dn_kind_i(kind), .dn_gsel_i(gsel), .dn_fp4_i(fp4), .dn_jid_i(jid),
        .dn_v_i(v), .dn_d_i(d), .e_v(r_v), .e_d(r_d), .e_t(r_t), .e_ob(r_ob), .e_f4(r_f4),
        .o_fu(r_fu), .o_fo(r_fo), .o_alive(r_al), .o_den(r_de), .o_rdy(r_rd), .o_rjid(r_rj));
    ot_s81_su_qbtl #(.QB_NB(QB_NB), .S_RD(S_RD), .NPB(NPB), .MUT(MUT == 1)) u_l (
        .clk(clk), .rst_in(rst), .dn_st_i(st), .dn_kind_i(kind), .dn_gsel_i(gsel), .dn_fp4_i(fp4), .dn_jid_i(jid),
        .dn_v_i(v), .dn_d_i(d[HW-1:0]), .e_v(n_v), .e_d(n_d[HW-1:0]), .e_t(n_t), .e_ob(n_ob), .e_f4(n_f4),
        .o_fu(n_fu), .o_fo(n_fo), .o_alive(n_al), .o_den(n_de), .o_rdy(n_rd), .o_rjid(n_rj));
    ot_s81_su_swth #(.S_RD(S_RD), .MUT(MUT == 2)) u_h (.clk(clk), .dn_d_i(d[DW-1:HW]), .e_d(n_d[DW-1:HW]));
    localparam integer OW = DW + 16 + 192 + 14 + 1 + 5 + 8;
    wire [OW-1:0] r_o = {r_d, r_v, r_t, r_ob, r_f4, r_fu, r_fo, r_al, r_de, r_rd, r_rj};
    wire [OW-1:0] n_o = {n_d, n_v, n_t, n_ob, n_f4, n_fu, n_fo, n_al, n_de, n_rd, n_rj};
    integer cyc = 0, bad = 0, chk = 0, hold = 4;
    integer n_op = 0, c_fo = 0, n_pass[0:3], n_job = 0, n_obnz = 0, c_f4 = 0, n_dnz = 0;
    integer state = 0, left = 0, gap = 0, i;
    reg [31:0] rnd;
    wire ill = cyc > 7 * NCYC / 8;                               // illegal traffic only in the last eighth
    task automatic rdata;
        integer k;
        begin for (k = 0; k < DW / 32; k = k + 1) d[32 * k +: 32] = $urandom; end
    endtask
    initial begin for (i = 0; i < 4; i = i + 1) n_pass[i] = 0; st = 0; kind = 0; gsel = 0; fp4 = 0; jid = 0; v = 0; d = 0; end
    always @(negedge clk) begin
        cyc <= cyc + 1;
        rnd = $urandom;
        if (cyc == 6) rst <= 1'b1;
        if (cyc == NCYC / 2) rst <= 1'b0;                         // a reset in mid traffic
        if (cyc == NCYC / 2 + 5) rst <= 1'b1;
        st <= 1'b0; v <= 0; rdata(); kind <= rnd[3:0]; gsel <= rnd[5:4]; fp4 <= rnd[6]; jid <= rnd[15:8];
        case (state)
            0: if (rnd[18:16] == 0) begin st <= 1'b1; kind <= (rnd[7:4] < 12) ? 4'd2 : rnd[3:0]; state <= 1; gap <= rnd[21:20]; n_job <= n_job + 1; end
            1: if (gap != 0) gap <= gap - 1;
               else begin v <= (rnd[27:23] == 0 && ill) ? 16'h0003 : 16'h0001; state <= 2; left <= 4 * (1 + rnd[11:9]) * (1 + rnd[14:12]); end
            2: if (rnd[22:20] == 0) v <= 0;                                         // an idle spine cycle
               else if (rnd[31:25] == 0 && ill) v <= {rnd[15:1], 1'b1};                    // a partial operand cycle (fault 5)
               else begin v <= 16'hffff; left <= left - 1; if (left <= 1) state <= 0; end
        endcase
        if (rnd[31:22] == 0 && state == 2) begin st <= 1'b1; kind <= 4'd2; state <= 1; gap <= 0; end   // announce over a running job
    end
    always @(posedge clk) begin
        if (!rst) hold <= 4;                                       // not compared: reset asserted and the cycles after
        else if (hold != 0) hold <= hold - 1;
        else begin
            chk <= chk + 1;
            if (n_o !== r_o) begin
                bad <= bad + 1;
                if (bad < 6) $display("mismatch cyc %0d: dlo %0d dhi %0d v %h/%h t0 %h/%h ob %h/%h f4 %b/%b st %b/%b rj %h/%h", cyc,
                    n_d[HW-1:0] !== r_d[HW-1:0], n_d[DW-1:HW] !== r_d[DW-1:HW], n_v, r_v, n_t[11:0], r_t[11:0], n_ob, r_ob, n_f4, r_f4,
                    {n_fu, n_fo, n_al, n_de, n_rd}, {r_fu, r_fo, r_al, r_de, r_rd}, n_rj, r_rj);
            end
            if (&n_v) begin n_op <= n_op + 1; n_pass[n_t[1:0]] <= n_pass[n_t[1:0]] + 1; if (n_d[DW-1:HW] != 0 && n_d[HW-1:0] != 0) n_dnz <= n_dnz + 1; end
            if (n_fo) c_fo <= c_fo + 1;
            if (n_ob != 0) n_obnz <= n_obnz + 1;
            if (n_f4) c_f4 <= c_f4 + 1;
        end
        if (cyc == NCYC) begin
            $display("QBT_SPLIT mut=%0d cyc=%0d checks=%0d mismatches=%0d jobs=%0d passes=%0d pass=%0d/%0d/%0d/%0d fo_cyc=%0d ob_nz=%0d f4=%0d dnz=%0d",
                     MUT, cyc, chk, bad, n_job, n_op, n_pass[0], n_pass[1], n_pass[2], n_pass[3], c_fo, n_obnz, c_f4, n_dnz);
            if (bad == 0 && chk > NCYC - 100 && n_op > 2000 && n_pass[0] > 100 && n_pass[1] > 100 && n_pass[2] > 100
                && n_pass[3] > 100 && c_fo > 10 && n_obnz > 1000 && c_f4 > 1000 && n_dnz > 2000) $display("QBT_SPLIT PASS");
            else $display("QBT_SPLIT FAIL");
            $finish;
        end
    end
endmodule
