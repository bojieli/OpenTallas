`timescale 1ps/1ps
// ---------------------------------------------------------------------------------------------------------------
// tb_dsfd_vm_a2f_diff (S-VM-RTL, 2026-10-16): randomized full-traffic DIFFERENTIAL bench, legacy VM core vs the A2-F /
// hop-1 VM core, both built from real RTL with 128 real SRAM models each (256 macros).
//   ref  dsfd_vm_static_core #(READ_PIPE 4, WSCATTER_PIPE `A2F_REF_WSP) -- the legacy path of dsfd_sp_vm (1 = the selected
//        native profile s81_vm_r4_c2_w1, 0 = s81_vm_r4_c2_w0)
//   dut  dsfd_vm_a2f_core   #(READ_PIPE 4, HOP1 `A2F_HOP1)   -- A2-F front + hop-1 (or hop-2 with A2F_HOP1=0) storage
// Both receive the SAME pins on the SAME edges: all 53 write sources (SU 16, HC 8, MIX4 4, capture 16, collective 4,
// WFC 1, and the 4 static landing lanes armed by real engine-12 LARM commands), and every read client (SU 2..15, HC 2,
// PQ x (4 rows), aux 4..11, MIX4 20 on their own edges).  The schedule is a legal static program (per-bank capture
// lane <= 2, unique drain edge per bank, distinct banks / FSR slots per read edge, RAW guard).
// Checks, every edge, both designs, every bit:
//   * read data: every valid on every read output equals the bench memory model at the read's issue edge, at EXACTLY
//     issue + L (ref L = 16; dut L = 16 + DREAD); any extra / missing / late valid fails;
//   * commits: every returned commit (u_mem.commit_v/addr/mask/tag, 128 banks) and every raw SRAM write (bank128
//     o_commit / o_ca / o_cm / o_ct) equals the expected record of the source pin sample P at EXACTLY P + lane + Lc;
//     Lc is calibrated by one isolated write per design, then held constant for every record;
//   * documented deltas: dut - ref raw write = DRAW, returned commit = DRET, read = DREAD
//       vs WSCATTER_PIPE 1: A2F_HOP1=1: DRAW +1 (A2 +2, hop-1 -1), DRET 0 (A2 +2, hop-1 -2), DREAD -2 (raw read -1)
//                           A2F_HOP1=0: DRAW +2, DRET +2, DREAD 0
//       vs WSCATTER_PIPE 0: every write delta +1 more (the legacy w0 scatter has no pin register)
//   * no fault on either design (vm_fault, every storage / write-front fault) under the legal program.
// Prints TB_A2F_DIFF PASS / FAIL.  Mutants (DUT defines) must print FAIL.
// ---------------------------------------------------------------------------------------------------------------
`ifndef A2F_HOP1
`define A2F_HOP1 1
`endif
`ifndef A2F_REF_WSP
`define A2F_REF_WSP 1
`endif
module tb_dsfd_vm_a2f_diff;
    localparam integer HOP1 = `A2F_HOP1;
    localparam integer RP = 4;
    localparam integer LREF = 12 + RP;
    localparam integer WSP = `A2F_REF_WSP;      // legacy WSCATTER_PIPE: 1 = profile s81_vm_r4_c2_w1, 0 = s81_vm_r4_c2_w0
    localparam integer DREAD = HOP1 ? -2 : 0, DRAW = (HOP1 ? 1 : 2) + (1 - WSP), DRET = (HOP1 ? 0 : 2) + (1 - WSP);
    localparam integer LDUT = LREF + DREAD;
    localparam integer NRL = HOP1 ? 16 : 48;
    localparam integer GUARD = 24;
    reg t_ck = 1, rss = 0;
    always #417 t_ck = ~t_ck;
    // ---------------------------------------------------------------- shared pins
    reg  [84:0] c_cmd = 0;
    reg  [15:0] su_rqv = 0; reg [223:0] su_rq = 0;
    reg  [15:0] su_wqv = 0; reg [223:0] su_wq = 0; reg [255:0] su_wqm = 0; reg [8191:0] su_wqd = 0;
    reg  [1:0]  hc_rqv = 0; reg [27:0] hc_rq = 0;
    reg  [7:0]  hc_wqv = 0; reg [111:0] hc_wq = 0; reg [127:0] hc_wqm = 0; reg [4095:0] hc_wqd = 0;
    reg  [19:0] pqx = 0;
    reg  [7:0]  x_av = 0; reg [111:0] x_ar = 0;
    reg  [19:0] mx_rqv = 0; reg [279:0] mx_rq = 0;
    reg  [3:0]  mx_wqv = 0; reg [55:0] mx_wq = 0; reg [63:0] mx_wqm = 0; reg [2047:0] mx_wqd = 0;
    reg  [3:0]  l_v = 0; reg [2047:0] l_d = 0;
    reg  [15:0] cp_v = 0; reg [223:0] cp_row = 0; reg [255:0] cp_m = 0; reg [8191:0] cp_d = 0;
    reg  [3:0]  cl_v = 0; reg [55:0] cl_row = 0; reg [63:0] cl_m = 0; reg [2047:0] cl_d = 0; reg [31:0] cl_t = 0;
    reg         wf_v = 0; reg [13:0] wf_row = 0; reg [511:0] wf_d = 0;
    // ---------------------------------------------------------------- outputs
    wire [8:0] r_done, d_done; wire [1:0] r_st, d_st; wire r_isu, r_ihc, d_isu, d_ihc;
    wire [15:0] r_su_rsv, d_su_rsv; wire [8191:0] r_su_rs, d_su_rs;
    wire [1:0] r_hc_rsv, d_hc_rsv; wire [1023:0] r_hc_rs, d_hc_rs;
    wire [2048:0] r_pqx, d_pqx; wire [7:0] r_xrv, d_xrv; wire [4095:0] r_xrd, d_xrd;
    wire r_nfv, d_nfv; wire [83:0] r_nfd, d_nfd;
    wire [19:0] r_mxv, d_mxv; wire [10239:0] r_mxd, d_mxd; wire r_flt, d_flt;
    dsfd_vm_static_core #(.READ_PIPE(RP), .WSCATTER_PIPE(WSP)) ref_vm (.cks(t_ck), .rss(rss),
        .ck_rsched(t_ck), .ck_seq(t_ck), .ck_landing(t_ck), .ck_mem_fsr({16{t_ck}}), .ck_mem_return({16{t_ck}}),
        .ck_mem_bank({128{t_ck}}), .ck_mem_wcapture({128{t_ck}}), .ck_mem_wscatter({16{t_ck}}),
        .ck_mem_relay_req({48{t_ck}}), .ck_mem_relay_rsp({48{t_ck}}),
        .ck_write_control(t_ck), .ck_write_header(t_ck), .ck_write_payload({4{t_ck}}), .ck_write_dispatch({16{t_ck}}),
        .ck_write_stage({128{t_ck}}),
        .rst_rsched_n(rss), .rst_seq_n(rss), .rst_landing_n(rss), .rst_mem_fsr_n({16{rss}}), .rst_mem_return_n({4{rss}}),
        .rst_mem_bank_n({128{rss}}), .rst_mem_wcapture_n({128{rss}}), .rst_mem_wscatter_n({16{rss}}), .rst_mem_relay_n({48{rss}}),
        .rst_write_control_n(rss), .rst_write_header_n(rss), .rst_write_payload_n({4{rss}}), .rst_write_dispatch_n({16{rss}}),
        .rst_write_stage_n({128{rss}}),
        .ck_read_data({64{t_ck}}), .rst_read_data_n({64{rss}}), .ck_read_valid({8{t_ck}}), .rst_read_valid_n({8{rss}}),
        .c_cmd(c_cmd), .c_done(r_done), .c_st(r_st), .t_inp_su(r_isu), .t_inp_hc(r_ihc),
        .f_su_rqv(su_rqv), .f_su_rq(su_rq), .t_su_rsv(r_su_rsv), .t_su_rs(r_su_rs),
        .f_su_wqv(su_wqv), .f_su_wq(su_wq), .f_su_wqm(su_wqm), .f_su_wqd(su_wqd),
        .f_hc_rqv(hc_rqv), .f_hc_rq(hc_rq), .t_hc_rsv(r_hc_rsv), .t_hc_rs(r_hc_rs),
        .f_hc_wqv(hc_wqv), .f_hc_wq(hc_wq), .f_hc_wqm(hc_wqm), .f_hc_wqd(hc_wqd),
        .f_pqx(pqx), .t_pqx(r_pqx), .x_av(x_av), .x_ar(x_ar), .x_rv(r_xrv), .x_rd(r_xrd), .nf_v(r_nfv), .nf_d(r_nfd),
        .f_mx_rqv(mx_rqv), .f_mx_rq(mx_rq), .t_mx_rsv(r_mxv), .t_mx_rs(r_mxd),
        .f_mx_wqv(mx_wqv), .f_mx_wq(mx_wq), .f_mx_wqm(mx_wqm), .f_mx_wqd(mx_wqd), .l_v(l_v), .l_d(l_d),
        .cp_v(cp_v), .cp_row(cp_row), .cp_m(cp_m), .cp_d(cp_d), .cl_v(cl_v), .cl_row(cl_row), .cl_m(cl_m), .cl_d(cl_d), .cl_t(cl_t),
        .wf_v(wf_v), .wf_row(wf_row), .wf_d(wf_d), .x_al(3'd0), .x_hdr(9'd0), .edge_f(3'd0), .vm_fault(r_flt));
    dsfd_vm_a2f_core #(.READ_PIPE(RP), .HOP1(HOP1)) dut_vm (.cks(t_ck), .rss(rss),
        .ck_rsched(t_ck), .ck_seq(t_ck), .ck_landing({5{t_ck}}), .ck_mem_fsr({16{t_ck}}), .ck_mem_return({16{t_ck}}),
        .ck_mem_bank({128{t_ck}}), .ck_mem_wscatter({16{t_ck}}),
        .ck_mem_relay_req({NRL{t_ck}}), .ck_mem_relay_rsp({NRL{t_ck}}),
        .ck_write_header(t_ck), .ck_write_payload({4{t_ck}}), .ck_write_control({4{t_ck}}), .ck_write_fault({4{t_ck}}),
        .ck_write_meta({28{t_ck}}), .ck_write_data({128{t_ck}}),
        .rst_rsched_n(rss), .rst_seq_n(rss), .rst_landing_n(rss), .rst_mem_fsr_n({16{rss}}), .rst_mem_return_n({4{rss}}),
        .rst_mem_bank_n({128{rss}}), .rst_mem_wscatter_n({16{rss}}), .rst_mem_relay_n({NRL{rss}}),
        .rst_write_header_n(rss), .rst_write_payload_n({4{rss}}), .rst_write_control_n({4{rss}}), .rst_write_fault_n({4{rss}}),
        .rst_write_meta_n({28{rss}}), .rst_write_data_n({128{rss}}),
        .ck_read_data({64{t_ck}}), .rst_read_data_n({64{rss}}), .ck_read_valid({8{t_ck}}), .rst_read_valid_n({8{rss}}),
        .c_cmd(c_cmd), .c_done(d_done), .c_st(d_st), .t_inp_su(d_isu), .t_inp_hc(d_ihc),
        .f_su_rqv(su_rqv), .f_su_rq(su_rq), .t_su_rsv(d_su_rsv), .t_su_rs(d_su_rs),
        .f_su_wqv(su_wqv), .f_su_wq(su_wq), .f_su_wqm(su_wqm), .f_su_wqd(su_wqd),
        .f_hc_rqv(hc_rqv), .f_hc_rq(hc_rq), .t_hc_rsv(d_hc_rsv), .t_hc_rs(d_hc_rs),
        .f_hc_wqv(hc_wqv), .f_hc_wq(hc_wq), .f_hc_wqm(hc_wqm), .f_hc_wqd(hc_wqd),
        .f_pqx(pqx), .t_pqx(d_pqx), .x_av(x_av), .x_ar(x_ar), .x_rv(d_xrv), .x_rd(d_xrd), .nf_v(d_nfv), .nf_d(d_nfd),
        .f_mx_rqv(mx_rqv), .f_mx_rq(mx_rq), .t_mx_rsv(d_mxv), .t_mx_rs(d_mxd),
        .f_mx_wqv(mx_wqv), .f_mx_wq(mx_wq), .f_mx_wqm(mx_wqm), .f_mx_wqd(mx_wqd), .l_v(l_v), .l_d(l_d),
        .cp_v(cp_v), .cp_row(cp_row), .cp_m(cp_m), .cp_d(cp_d), .cl_v(cl_v), .cl_row(cl_row), .cl_m(cl_m), .cl_d(cl_d), .cl_t(cl_t),
        .wf_v(wf_v), .wf_row(wf_row), .wf_d(wf_d), .x_al(3'd0), .x_hdr(9'd0), .edge_f(3'd0), .vm_fault(d_flt));
    // ---------------------------------------------------------------- raw SRAM write observations (bank128 o_commit)
    wire [127:0] r_bc, d_bc; wire [1151:0] r_ba, d_ba; wire [511:0] r_bm, d_bm; wire [1023:0] r_bt, d_bt;
    genvar gs, gb;
    generate for (gs = 0; gs < 4; gs = gs + 1) begin : obs_s
        for (gb = 0; gb < 32; gb = gb + 1) begin : obs_b
            assign r_bc[32*gs+gb] = ref_vm.u_mem.slice[gs].u_slice.bank[gb].u_bank.o_commit;
            assign r_ba[9*(32*gs+gb) +: 9] = ref_vm.u_mem.slice[gs].u_slice.bank[gb].u_bank.o_ca;
            assign r_bm[4*(32*gs+gb) +: 4] = ref_vm.u_mem.slice[gs].u_slice.bank[gb].u_bank.o_cm;
            assign r_bt[8*(32*gs+gb) +: 8] = ref_vm.u_mem.slice[gs].u_slice.bank[gb].u_bank.o_ct;
            assign d_bc[32*gs+gb] = dut_vm.u_mem.slice[gs].u_slice.bank[gb].u_bank.o_commit;
            assign d_ba[9*(32*gs+gb) +: 9] = dut_vm.u_mem.slice[gs].u_slice.bank[gb].u_bank.o_ca;
            assign d_bm[4*(32*gs+gb) +: 4] = dut_vm.u_mem.slice[gs].u_slice.bank[gb].u_bank.o_cm;
            assign d_bt[8*(32*gs+gb) +: 8] = dut_vm.u_mem.slice[gs].u_slice.bank[gb].u_bank.o_ct;
        end
    end endgenerate
    // raw SRAM read edge of slice 0 bank 5 (calibration read): bank128 rdue = r_ce sampled by the macro on this edge
    wire r_rraw = ref_vm.u_mem.slice[0].u_slice.bank[5].u_bank.rdue, d_rraw = dut_vm.u_mem.slice[0].u_slice.bank[5].u_bank.rdue;
    wire [127:0] r_cv = ref_vm.cm_v, d_cv = dut_vm.cm_v;
    wire [1151:0] r_ca = ref_vm.cm_a, d_ca = dut_vm.cm_a;
    wire [511:0] r_cm = ref_vm.cm_m, d_cm = dut_vm.cm_m;
    wire [1023:0] r_ct = ref_vm.cm_t, d_ct = dut_vm.cm_t;
    // ---------------------------------------------------------------- bench state
    integer seed = 1, bad = 0, tk = -1, i, NMIX = 2400, NEND;
    reg [31:0] rs;
    function [31:0] rnd32; begin rs = rs ^ (rs << 13); rs = rs ^ (rs >> 17); rs = rs ^ (rs << 5); rnd32 = rs; end endfunction
    function integer ur(input integer n); begin ur = rnd32() % n; end endfunction
    function [4:0] bank_of(input [13:0] r); bank_of = r[4:0] ^ {r[7:5], 2'b00}; endfunction
    function [511:0] rnd512; integer w; begin for (w = 0; w < 16; w = w + 1) rnd512[32*w +: 32] = rnd32(); end endfunction
    reg [511:0] mem [0:16383]; integer lastw [0:16383]; reg wr [0:16383];
    initial for (i = 0; i < 16384; i = i + 1) begin wr[i] = 0; lastw[i] = -1000; end
    // drain-edge reservation per bank (D = P + lane), ring 256
    reg [255:0] busy [0:31];
    initial for (i = 0; i < 32; i = i + 1) busy[i] = 0;
    // read expectations by ISSUE edge (ring 64): slots 0..15 SU, 16..17 HC, 18..21 PQ rows, 22..29 aux 4..11, 30..49 MIX
    reg [49:0] iv [0:63]; reg [511:0] idt [0:63][0:49];
    initial for (i = 0; i < 64; i = i + 1) iv[i] = 0;
    // commit expectations by DRAIN key D = P + lane (ring 256), per bank: {addr 9, 16-b mask, tag 8}
    reg [255:0] ev [0:31]; reg [8:0] ea [0:31][0:255]; reg [15:0] em [0:31][0:255]; reg [7:0] et [0:31][0:255];
    initial for (i = 0; i < 32; i = i + 1) ev[i] = 0;
    integer n_rd = 0, n_wr = 0, n_cm_r = 0, n_cm_d = 0, n_raw_r = 0, n_raw_d = 0, n_land = 0, n_mixrd = 0;
    integer lc_r_raw = -1, lc_d_raw = -1, lc_r_ret = -1, lc_d_ret = -1, lr_r_raw = -1, lr_d_raw = -1;
    integer src_cnt [0:52]; initial for (i = 0; i < 53; i = i + 1) src_cnt[i] = 0;
    // engine command (LARM): drive for the next edge
    function [84:0] mkcmd(input [2:0] code, input [20:0] op, input [6:0] row);
        mkcmd = {1'b1, 1'b0, 10'd37, 21'd5000 + 21'(row), 21'd77, code, op, row};
    endfunction
    integer cmd_row = 0;
    // landing windows: [start, start+len) ; groups 0 (scan pairs), 5 (selector), 6 (collector)
    localparam integer LW0 = 700, LW5 = 1100, LW6 = 1500, LLEN = 24;
    function integer in_land(input integer t);
        in_land = (t >= LW0 - 40 && t < LW0 + LLEN + 40) || (t >= LW5 - 40 && t < LW5 + LLEN + 40) ||
                  (t >= LW6 - 40 && t < LW6 + LLEN + 40);
    endfunction
    // ---------------------------------------------------------------- program generator
    // phase F (fill): full-mask writes of rows 0..8191; phase M: random partial writes + reads; phase E: read-back sweep
    integer fill_next = 0;
    reg [31:0] rd_bank;                           // banks used by this edge's reads
    reg [3:0] rd_slot;                            // HC slots used
    task try_read_row(input integer slot, input integer row, output reg ok);
        begin
            ok = 0;
            if (row >= 0 && row < 16384 && wr[row] && lastw[row] < tk + 1 - GUARD && !rd_bank[bank_of(14'(row))]) begin
                ok = 1; rd_bank[bank_of(14'(row))] = 1'b1;
                iv[(tk + 1) % 64][slot] = 1'b1; idt[(tk + 1) % 64][slot] = mem[row];
            end
        end
    endtask
    integer sw [0:3];
    initial for (i = 0; i < 4; i = i + 1) sw[i] = 0;
    function integer rrow; begin rrow = (ur(100) < 25) ? 9000 + ur(500) : ur(8192); end endfunction
    task gen_sweep;                                // read-back of rows 0..8191, SU ports 2..15 (row class p mod 4)
        integer p, r; reg ok;
        begin
            rd_bank = 0;
            for (p = 2; p < 16; p = p + 1) if (sw[p % 4] < 2048) begin
                r = 4 * sw[p % 4] + p % 4;
                try_read_row(p, r, ok);
                if (ok) begin su_rqv[p] = 1'b1; su_rq[14*p +: 14] = 14'(r); n_rd = n_rd + 1; sw[p % 4] = sw[p % 4] + 1; end
            end
        end
    endtask
    task gen_reads(input integer density);
        integer p, r, a, k, base; reg ok;
        begin
            rd_bank = 0;
            for (p = 2; p < 16; p = p + 1) if (ur(100) < density) begin
                for (k = 0; k < 4; k = k + 1) begin
                    r = (rrow() & ~3) | (p % 4);
                    try_read_row(p, r, ok);
                    if (ok) begin su_rqv[p] = 1'b1; su_rq[14*p +: 14] = 14'(r); n_rd = n_rd + 1; k = 4; end
                end
            end
            rd_slot = 0;
            for (p = 0; p < 2; p = p + 1) if (ur(100) < density) begin
                r = rrow();
                if (!rd_slot[r % 4]) begin
                    try_read_row(16 + p, r, ok);
                    if (ok) begin hc_rqv[p] = 1'b1; hc_rq[14*p +: 14] = 14'(r); rd_slot[r % 4] = 1'b1; n_rd = n_rd + 1; end
                end
            end
            if (ur(100) < density) begin : pq
                reg [3:0] okv; reg [31:0] save; reg [49:0] sv_iv;
                base = ur(2048) * 4; okv = 0; save = rd_bank; sv_iv = iv[(tk + 1) % 64];
                for (a = 0; a < 4; a = a + 1) begin try_read_row(18 + a, base + a, ok); okv[a] = ok; end
                if (okv == 4'hf) begin pqx = {1'b0, 12'(base / 4), 6'd0, 1'b1}; n_rd = n_rd + 4; end
                else begin rd_bank = save; iv[(tk + 1) % 64] = sv_iv; end
            end
            for (a = 4; a < 12; a = a + 1) if (ur(100) < density) begin
                r = (rrow() & ~3) | (a % 4);
                try_read_row(22 + a - 4, r, ok);
                if (ok) begin x_av[a - 4] = 1'b1; x_ar[14*(a-4) +: 14] = 14'(r); n_rd = n_rd + 1; end
            end
        end
    endtask
    task gen_mix_reads;                            // MIX4 edge: 20 lanes, only MIX on the read ports this edge
        integer l, g, r, k; reg ok; reg [3:0] used;
        begin
            rd_bank = 0;
            for (g = 0; g < 5; g = g + 1) begin
                used = 0;
                for (l = 4 * g; l < 4 * g + 4; l = l + 1) if (ur(100) < 70) begin
                    for (k = 0; k < 6; k = k + 1) begin
                        r = rrow();
                        if (!used[r % 4]) begin
                            try_read_row(30 + l, r, ok);
                            if (ok) begin used[r % 4] = 1'b1; mx_rqv[l] = 1'b1; mx_rq[14*l +: 14] = 14'(r); n_mixrd = n_mixrd + 1; k = 6; end
                        end
                    end
                end
            end
        end
    endtask
    // write generator: source c gets row r if bank lane / drain edge are free
    integer lane_cnt [0:31];
    function integer can_write(input integer r);
        integer b, l;
        begin
            b = bank_of(14'(r)); l = lane_cnt[b];
            can_write = (r >= 0 && r < 16384 && l < 3 && !busy[b][(tk + 1 + l) % 256] && lastw[r] < tk + 1 - 8);
        end
    endfunction
    reg [13:0] used_row [0:52]; integer n_used;
    function integer row_used(input integer r); integer k; begin row_used = 0; for (k = 0; k < n_used; k = k + 1) if (used_row[k] == 14'(r)) row_used = 1; end endfunction
    task pick_row(input integer fill, output integer r);
        integer k;
        begin
            r = -1;
            for (k = 0; k < 4 && r < 0; k = k + 1) begin : t
                integer c;
                c = fill ? fill_next : ur(8192);
                if (can_write(c) && !row_used(c)) begin
                    r = c; lane_cnt[bank_of(14'(c))] = lane_cnt[bank_of(14'(c))] + 1; used_row[n_used] = 14'(c); n_used = n_used + 1;
                    if (fill) fill_next = fill_next + 1;
                end else if (fill) k = 4;        // keep fill order: retry next edge
            end
        end
    endtask
    function [15:0] rmask(input integer fill); begin rmask = fill ? 16'hffff : (ur(4) == 0 ? 16'hffff : 16'(rnd32())); end endfunction
    task gen_writes(input integer density, input integer fill);
        integer c, r;
        begin
            for (c = 0; c < 32; c = c + 1) lane_cnt[c] = 0;
            n_used = 0;
            for (c = 0; c < 53; c = c + 1) if (!(c >= 24 && c < 28) && (fill || ur(100) < density)) begin
                if (fill && fill_next >= 8192) c = 53;
                else begin
                    pick_row(fill, r);
                    if (r >= 0) begin
                        if (c < 16) begin su_wqv[c] = 1; su_wq[14*c +: 14] = 14'(r); su_wqm[16*c +: 16] = rmask(fill); su_wqd[512*c +: 512] = rnd512(); end
                        else if (c < 24) begin hc_wqv[c-16] = 1; hc_wq[14*(c-16) +: 14] = 14'(r); hc_wqm[16*(c-16) +: 16] = rmask(fill); hc_wqd[512*(c-16) +: 512] = rnd512(); end
                        else if (c < 32) begin mx_wqv[c-28] = 1; mx_wq[14*(c-28) +: 14] = 14'(r); mx_wqm[16*(c-28) +: 16] = rmask(fill); mx_wqd[512*(c-28) +: 512] = rnd512(); end
                        else if (c < 44 || (c >= 48 && c < 52)) begin : cap
                            integer ln; ln = (c < 44) ? c - 32 : c - 36;
                            cp_v[ln] = 1; cp_row[14*ln +: 14] = 14'(r); cp_m[16*ln +: 16] = rmask(fill); cp_d[512*ln +: 512] = rnd512();
                        end
                        else if (c < 48) begin cl_v[c-44] = 1; cl_row[14*(c-44) +: 14] = 14'(r); cl_m[16*(c-44) +: 16] = rmask(fill); cl_d[512*(c-44) +: 512] = rnd512(); cl_t[8*(c-44) +: 8] = 8'(rnd32()); end
                        else begin wf_v = 1; wf_row = 14'(r); wf_d = rnd512(); end
                    end
                end
            end
        end
    endtask
    // ---------------------------------------------------------------- stimulus (drive after edge tk for edge tk+1)
    integer FILL0 = 60, MIX0, SWEEP0;
    always @(posedge t_ck) if (rss) begin : prog
        integer k, r;
        tk = tk + 1;
        #10;
        c_cmd = 0; su_rqv = 0; su_wqv = 0; hc_rqv = 0; hc_wqv = 0; pqx = 0; x_av = 0; mx_rqv = 0; mx_wqv = 0;
        l_v = 0; cp_v = 0; cl_v = 0; wf_v = 0;
        iv[(tk + 1) % 64] = 0;
        // calibration: one isolated full-mask write (SU0, row 5) at edge 21, nothing else for 40 edges
        if (tk == 20) begin su_wqv[0] = 1; su_wq[13:0] = 14'd5; su_wqm[15:0] = 16'hffff; su_wqd[511:0] = rnd512(); end
        else if (tk == 50) begin : calrd reg ok; rd_bank = 0; try_read_row(5, 5, ok); if (ok) begin su_rqv[5] = 1; su_rq[14*5 +: 14] = 14'd5; end else bad = bad + 1; end
        else if (tk >= FILL0 && fill_next < 8192) gen_writes(100, 1);
        else if (tk >= MIX0 && tk < SWEEP0) begin
            if (!in_land(tk)) gen_writes(45, 0);
            if (tk % 7 == 3) gen_mix_reads; else gen_reads(55);
        end else if (tk >= SWEEP0) gen_sweep;
        // landing: LARM 30 edges before each window, rows each edge of the window
        if (tk == LW0 - 30) begin c_cmd = mkcmd(3'd6, {4'd0, 3'd0, 14'd9000}, 7'(cmd_row)); cmd_row = cmd_row + 1; end
        if (tk == LW5 - 30) begin c_cmd = mkcmd(3'd6, {4'd5, 3'd0, 14'd9200}, 7'(cmd_row)); cmd_row = cmd_row + 1; end
        if (tk == LW6 - 30) begin c_cmd = mkcmd(3'd6, {4'd6, 3'd0, 14'd9400}, 7'(cmd_row)); cmd_row = cmd_row + 1; end
        if (tk >= LW0 && tk < LW0 + LLEN) begin l_v[1:0] = 2'b11; l_d[1023:0] = {rnd512(), rnd512()}; end
        if (tk >= LW5 && tk < LW5 + LLEN) begin l_v[2] = 1'b1; l_d[1535:1024] = rnd512(); end
        if (tk >= LW6 && tk < LW6 + LLEN) begin l_v[3] = 1'b1; l_d[2047:1536] = rnd512(); end
        // ---- record the source pins sampled at edge tk+1 (ref and dut share them: assert), update the model
        #10;
        if (ref_vm.s_v !== dut_vm.s_v || ref_vm.s_row !== dut_vm.s_row || ref_vm.s_m !== dut_vm.s_m || ref_vm.s_d !== dut_vm.s_d ||
            ref_vm.s_t !== dut_vm.s_t) begin bad = bad + 1; $display("SOURCE PIN DIVERGENCE tk %0d", tk); end
        for (k = 0; k < 32; k = k + 1) lane_cnt[k] = 0;
        for (k = 0; k < 53; k = k + 1) if (ref_vm.s_v[k]) begin : rec
            integer b, l, D, w; reg [13:0] row; reg [15:0] m;
            row = ref_vm.s_row[14*k +: 14]; m = ref_vm.s_m[16*k +: 16]; b = bank_of(row); l = lane_cnt[b]; lane_cnt[b] = l + 1;
            D = (tk + 1 + l) % 256;
            if (l >= 3 || ev[b][D]) begin bad = bad + 1; $display("BENCH SCHEDULE ILLEGAL tk %0d src %0d bank %0d lane %0d", tk, k, b, l); end
            ev[b][D] = 1'b1; ea[b][D] = row[13:5]; em[b][D] = m; et[b][D] = ref_vm.s_t[8*k +: 8]; busy[b][D] = 1'b1;
            for (w = 0; w < 16; w = w + 1) if (m[w]) mem[row][32*w +: 32] = ref_vm.s_d[512*k + 32*w +: 32];
            wr[row] = 1'b1; lastw[row] = tk + 1; n_wr = n_wr + 1; src_cnt[k] = src_cnt[k] + 1;
            if (k >= 24 && k < 28) n_land = n_land + 1;
        end
        // free drain reservations far in the past (ring reuse)
        for (k = 0; k < 32; k = k + 1) busy[k][(tk + 1 + 128) % 256] = 1'b0;
    end
    // ---------------------------------------------------------------- checks (sample after edge tk settles)
    task chk_reads(input integer which, input integer L,
                   input [15:0] su_v, input [8191:0] su_d, input [1:0] hc_v, input [1023:0] hc_d, input [2048:0] pq,
                   input [7:0] xv, input [4095:0] xd, input [19:0] mv, input [10239:0] md);
        integer E, p; reg [49:0] e;
        begin
            E = tk - L;
            e = (E >= 0) ? iv[E % 64] : 50'd0;
            for (p = 0; p < 16; p = p + 1) begin
                if (su_v[p] !== e[p]) begin bad = bad + 1; if (bad < 20) $display("%s SU VALID port %0d tk %0d got %b exp %b", which ? "DUT" : "REF", p, tk, su_v[p], e[p]); end
                else if (e[p] && su_d[512*p +: 512] !== idt[E % 64][p]) begin bad = bad + 1; if (bad < 20) $display("%s SU DATA port %0d tk %0d", which ? "DUT" : "REF", p, tk); end
            end
            for (p = 0; p < 2; p = p + 1) begin
                if (hc_v[p] !== e[16+p]) begin bad = bad + 1; if (bad < 20) $display("%s HC VALID %0d tk %0d", which ? "DUT" : "REF", p, tk); end
                else if (e[16+p] && hc_d[512*p +: 512] !== idt[E % 64][16+p]) begin bad = bad + 1; if (bad < 20) $display("%s HC DATA %0d tk %0d", which ? "DUT" : "REF", p, tk); end
            end
            if (pq[0] !== e[18]) begin bad = bad + 1; if (bad < 20) $display("%s PQ VALID tk %0d", which ? "DUT" : "REF", tk); end
            else if (e[18]) for (p = 0; p < 4; p = p + 1) if (pq[1 + 512*p +: 512] !== idt[E % 64][18+p]) begin bad = bad + 1; if (bad < 20) $display("%s PQ DATA row %0d tk %0d", which ? "DUT" : "REF", p, tk); end
            for (p = 0; p < 8; p = p + 1) begin
                if (xv[p] !== e[22+p]) begin bad = bad + 1; if (bad < 20) $display("%s AUX VALID %0d tk %0d", which ? "DUT" : "REF", p, tk); end
                else if (e[22+p] && xd[512*p +: 512] !== idt[E % 64][22+p]) begin bad = bad + 1; if (bad < 20) $display("%s AUX DATA %0d tk %0d", which ? "DUT" : "REF", p, tk); end
            end
            for (p = 0; p < 20; p = p + 1) begin
                if (mv[p] !== e[30+p]) begin bad = bad + 1; if (bad < 20) $display("%s MIX VALID %0d tk %0d", which ? "DUT" : "REF", p, tk); end
                else if (e[30+p] && md[512*p +: 512] !== idt[E % 64][30+p]) begin bad = bad + 1; if (bad < 20) $display("%s MIX DATA %0d tk %0d", which ? "DUT" : "REF", p, tk); end
            end
        end
    endtask
    // commit check: every (slice, bank) valid / addr / mask nibble / tag equals the record with drain key tk - L
    task chk_commits(input integer which, input integer raw, input integer L, input [127:0] cv, input [1151:0] ca,
                     input [511:0] cm, input [1023:0] ct, inout integer n);
        integer s, b, D; reg e;
        begin
            for (b = 0; b < 32; b = b + 1) begin
                D = tk - L; e = (D >= 0) ? ev[b][D % 256] : 1'b0;
                for (s = 0; s < 4; s = s + 1) begin
                    if (cv[32*s+b] !== e) begin bad = bad + 1; if (bad < 20) $display("%s %s COMMIT VALID slice %0d bank %0d tk %0d got %b exp %b", which ? "DUT" : "REF", raw ? "RAW" : "RET", s, b, tk, cv[32*s+b], e); end
                    else if (e && (ca[9*(32*s+b) +: 9] !== ea[b][D % 256] || cm[4*(32*s+b) +: 4] !== em[b][D % 256][4*s +: 4] ||
                                   ct[8*(32*s+b) +: 8] !== et[b][D % 256])) begin bad = bad + 1; if (bad < 20) $display("%s %s COMMIT META slice %0d bank %0d tk %0d", which ? "DUT" : "REF", raw ? "RAW" : "RET", s, b, tk); end
                    if (e) n = n + 1;
                end
            end
        end
    endtask
    integer cal_b;
    always @(posedge t_ck) if (rss) begin : chk
        integer b;
        #30;
        // calibration (isolated record P = 21, lane 0, bank of row 5): first commit edge of each observation point
        cal_b = bank_of(14'd5);
        if (tk > 21 && tk < 60) begin
            if (lc_r_raw < 0 && r_bc[cal_b]) lc_r_raw = tk - 21;
            if (lc_d_raw < 0 && d_bc[cal_b]) lc_d_raw = tk - 21;
            if (lc_r_ret < 0 && r_cv[cal_b]) lc_r_ret = tk - 21;
            if (lc_d_ret < 0 && d_cv[cal_b]) lc_d_ret = tk - 21;
        end
        if (tk > 51 && tk < 60) begin
            if (lr_r_raw < 0 && r_rraw) lr_r_raw = tk - 51;
            if (lr_d_raw < 0 && d_rraw) lr_d_raw = tk - 51;
        end
        if (tk >= 60) begin
            chk_reads(0, LREF, r_su_rsv, r_su_rs, r_hc_rsv, r_hc_rs, r_pqx, r_xrv, r_xrd, r_mxv, r_mxd);
            chk_reads(1, LDUT, d_su_rsv, d_su_rs, d_hc_rsv, d_hc_rs, d_pqx, d_xrv, d_xrd, d_mxv, d_mxd);
            chk_commits(0, 1, lc_r_raw, r_bc, r_ba, r_bm, r_bt, n_raw_r);
            chk_commits(1, 1, lc_d_raw, d_bc, d_ba, d_bm, d_bt, n_raw_d);
            chk_commits(0, 0, lc_r_ret, r_cv, r_ca, r_cm, r_ct, n_cm_r);
            chk_commits(1, 0, lc_d_ret, d_cv, d_ca, d_cm, d_ct, n_cm_d);
            if (r_done !== d_done) begin bad = bad + 1; if (bad < 20) $display("ENGINE DONE DIVERGENCE tk %0d", tk); end
        end
        // retire commit expectations once both designs have passed them
        if (tk >= 60) for (b = 0; b < 32; b = b + 1) ev[b][(tk - 40 + 256) % 256] = 1'b0;
    end
    // ---------------------------------------------------------------- run
    integer s_used;
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("nmix=%d", NMIX)) NMIX = 2400;
        rs = 32'h9e3779b9 ^ (32'(seed) * 32'h01000193);
        MIX0 = 60 + 8192 / 20 + 120; SWEEP0 = MIX0 + NMIX; NEND = SWEEP0 + 1500;
        if (MIX0 + 40 > LW0) begin MIX0 = LW0 - 60; SWEEP0 = MIX0 + NMIX; NEND = SWEEP0 + 1500; end
        #(834 * 4 - 100); rss = 1;
        #(834 * NEND);
        if (r_flt !== 1'b0 || d_flt !== 1'b0 || ref_vm.w_flt !== 1'b0 || dut_vm.w_flt !== 1'b0 || |ref_vm.m_flt || |dut_vm.m_flt ||
            r_st[0] || d_st[0]) begin
            bad = bad + 1; $display("UNEXPECTED FAULT ref vm %b w %b m %h st %b | dut vm %b w %b m %h st %b", r_flt, ref_vm.w_flt, ref_vm.m_flt, r_st,
                d_flt, dut_vm.w_flt, dut_vm.m_flt, d_st);
        end
        s_used = 0; for (i = 0; i < 53; i = i + 1) if (src_cnt[i] > 0) s_used = s_used + 1;
        $display("TB_A2F_DIFF LAT hop1 %0d ref_wsp %0d | ref write raw P+%0d+lane commit P+%0d+lane read raw Q+%0d return Q+%0d | dut write raw P+%0d+lane commit P+%0d+lane read raw Q+%0d return Q+%0d | delta write %0d commit %0d read_raw %0d read %0d (expect %0d %0d %0d %0d)",
                 HOP1, WSP, lc_r_raw, lc_r_ret, lr_r_raw, LREF, lc_d_raw, lc_d_ret, lr_d_raw, LDUT, lc_d_raw - lc_r_raw, lc_d_ret - lc_r_ret, lr_d_raw - lr_r_raw, LDUT - LREF,
                 DRAW, DRET, HOP1 ? -1 : 0, DREAD);
        if (lc_r_raw < 0 || lc_d_raw < 0 || lr_r_raw < 0 || lr_d_raw < 0 || lc_d_raw - lc_r_raw != DRAW || lc_d_ret - lc_r_ret != DRET ||
            lr_d_raw - lr_r_raw != (HOP1 ? -1 : 0)) begin bad = bad + 1; $display("LATENCY DELTA MISMATCH"); end
        $display("TB_A2F_DIFF RESULT seed %0d edges %0d writes %0d landing %0d sources_used %0d reads %0d mix_reads %0d raw_commits ref %0d dut %0d returned ref %0d dut %0d bad %0d",
                 seed, NEND, n_wr, n_land, s_used, n_rd, n_mixrd, n_raw_r, n_raw_d, n_cm_r, n_cm_d, bad);
        $display("TB_A2F_DIFF %s", (bad == 0 && s_used == 53 && n_raw_r == n_raw_d && n_cm_r == n_cm_d && n_cm_r == 4 * (n_wr - 1) &&
                                    n_rd > 1000 && n_mixrd > 100 && sw[0] == 2048 && sw[1] == 2048 && sw[2] == 2048 && sw[3] == 2048) ? "PASS" : "FAIL");
        $finish;
    end
endmodule
