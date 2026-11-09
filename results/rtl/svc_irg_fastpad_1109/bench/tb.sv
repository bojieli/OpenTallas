`timescale 1ns/1ps
// IRG fastpad bench: original dsdv_idx_rg2_chunk (8 x ot_hdc_v41x_idx_hslice) vs fastpad chunk
// (8 x ot_hdc_v41x_idx_hslice_fp), same pre-recorded trace, same cycle.
//  * c_sum / c_fault compared same cycle for every valid record (metadata ring of 106, cleared on rst_n low = aborted)
//  * Q / key outputs of every slice h: fastpad at cycle m - 7(h+1) == original at cycle m (outside reset windows)
//  * terminal fastpad key out (ky[8]) == bench k_key 17 edges earlier (chunk input register + 8 x 2)
module tb;
    localparam integer N_MAX = 200000, LAT = 106, HC = 8, KW = 544, QW = 1 + 8 + 512 + 32 + 16;
    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg [1119:0] tr [0:N_MAX-1];
    integer n_rows, hb_i;
    reg rst_n; reg ql_v; reg [7:0] ql_head; reg [511:0] ql_codes; reg [31:0] ql_sc; reg [15:0] ql_w; reg [543:0] k_key;
    reg kvalid; reg [7:0] hb;
    wire [31:0] rs_sum, fs_sum; wire rs_f, fs_f;
    chk_ref u_ref (.clk(clk), .rst_n(rst_n), .hb(hb), .ql_v(ql_v), .ql_head(ql_head), .ql_codes(ql_codes), .ql_sc(ql_sc),
                   .ql_w(ql_w), .k_key(k_key), .c_sum(rs_sum), .c_fault(rs_f));
    chk_fp  u_fp  (.clk(clk), .rst_n(rst_n), .hb(hb), .ql_v(ql_v), .ql_head(ql_head), .ql_codes(ql_codes), .ql_sc(ql_sc),
                   .ql_w(ql_w), .k_key(k_key), .c_sum(fs_sum), .c_fault(fs_f));
    // metadata ring: validity of the record whose result is at c_sum now
    reg [LAT-1:0] ring;
    // reset window tracker (cycles since last rst_n low)
    integer since_rst;
    // fastpad Q / key output history (depth 64) per slice output index 1..8
    reg [KW-1:0] fk_hist [1:HC][0:63];
    reg [QW-1:0] fq_hist [1:HC][0:63];
    reg [KW-1:0] kin_hist [0:63];
    integer cyc, i, h;
    integer n_valid, n_vfault, n_vmis, n_all_mis, n_zero, n_kq_cmp, n_kq_mis, n_term_cmp, n_term_mis, n_resets;
    reg [KW-1:0] rk [1:HC]; reg [QW-1:0] rq [1:HC]; reg [KW-1:0] fk [1:HC]; reg [QW-1:0] fq [1:HC];
    always @(*) begin
        rk[1] = u_ref.ky[1]; rk[2] = u_ref.ky[2]; rk[3] = u_ref.ky[3]; rk[4] = u_ref.ky[4];
        rk[5] = u_ref.ky[5]; rk[6] = u_ref.ky[6]; rk[7] = u_ref.ky[7]; rk[8] = u_ref.ky[8];
        fk[1] = u_fp.ky[1];  fk[2] = u_fp.ky[2];  fk[3] = u_fp.ky[3];  fk[4] = u_fp.ky[4];
        fk[5] = u_fp.ky[5];  fk[6] = u_fp.ky[6];  fk[7] = u_fp.ky[7];  fk[8] = u_fp.ky[8];
        rq[1] = {u_ref.qv[1], u_ref.qh[1], u_ref.qc[1], u_ref.qs[1], u_ref.qw[1]};
        rq[2] = {u_ref.qv[2], u_ref.qh[2], u_ref.qc[2], u_ref.qs[2], u_ref.qw[2]};
        rq[3] = {u_ref.qv[3], u_ref.qh[3], u_ref.qc[3], u_ref.qs[3], u_ref.qw[3]};
        rq[4] = {u_ref.qv[4], u_ref.qh[4], u_ref.qc[4], u_ref.qs[4], u_ref.qw[4]};
        rq[5] = {u_ref.qv[5], u_ref.qh[5], u_ref.qc[5], u_ref.qs[5], u_ref.qw[5]};
        rq[6] = {u_ref.qv[6], u_ref.qh[6], u_ref.qc[6], u_ref.qs[6], u_ref.qw[6]};
        rq[7] = {u_ref.qv[7], u_ref.qh[7], u_ref.qc[7], u_ref.qs[7], u_ref.qw[7]};
        rq[8] = {u_ref.qv[8], u_ref.qh[8], u_ref.qc[8], u_ref.qs[8], u_ref.qw[8]};
        fq[1] = {u_fp.qv[1], u_fp.qh[1], u_fp.qc[1], u_fp.qs[1], u_fp.qw[1]};
        fq[2] = {u_fp.qv[2], u_fp.qh[2], u_fp.qc[2], u_fp.qs[2], u_fp.qw[2]};
        fq[3] = {u_fp.qv[3], u_fp.qh[3], u_fp.qc[3], u_fp.qs[3], u_fp.qw[3]};
        fq[4] = {u_fp.qv[4], u_fp.qh[4], u_fp.qc[4], u_fp.qs[4], u_fp.qw[4]};
        fq[5] = {u_fp.qv[5], u_fp.qh[5], u_fp.qc[5], u_fp.qs[5], u_fp.qw[5]};
        fq[6] = {u_fp.qv[6], u_fp.qh[6], u_fp.qc[6], u_fp.qs[6], u_fp.qw[6]};
        fq[7] = {u_fp.qv[7], u_fp.qh[7], u_fp.qc[7], u_fp.qs[7], u_fp.qw[7]};
        fq[8] = {u_fp.qv[8], u_fp.qh[8], u_fp.qc[8], u_fp.qs[8], u_fp.qw[8]};
    end
    reg [1119:0] w;
    initial begin
        if (!$value$plusargs("hb=%d", hb_i)) hb_i = 0;
        hb = 8'(hb_i);
        if (!$value$plusargs("rows=%d", n_rows)) n_rows = 0;
        $readmemh("trace.hex", tr, 0, n_rows - 1);
        ring = '0; since_rst = 0;
        n_valid = 0; n_vfault = 0; n_vmis = 0; n_all_mis = 0; n_zero = 0; n_kq_cmp = 0; n_kq_mis = 0;
        n_term_cmp = 0; n_term_mis = 0; n_resets = 0;
        rst_n = 1'b0; ql_v = 0; ql_head = 0; ql_codes = 0; ql_sc = 0; ql_w = 0; k_key = 0; kvalid = 0;
        for (cyc = 0; cyc < n_rows + LAT + 4; cyc = cyc + 1) begin
            @(negedge clk);
            // ---- sample (state after the previous posedge)
            if (ring[LAT-1]) begin
                n_valid = n_valid + 1;
                if (rs_f) n_vfault = n_vfault + 1;
                if (rs_sum == 32'd0) n_zero = n_zero + 1;
                if (rs_sum !== fs_sum || rs_f !== fs_f) begin
                    n_vmis = n_vmis + 1;
                    if (n_vmis <= 10) $display("VMIS cyc %0d ref %h/%0d fp %h/%0d", cyc, rs_sum, rs_f, fs_sum, fs_f);
                end
            end
            if (cyc > 300 && since_rst > 400 && (rs_sum !== fs_sum || rs_f !== fs_f)) n_all_mis = n_all_mis + 1;
            for (h = 1; h <= HC; h = h + 1) begin
                if (cyc > 300 && since_rst > 400) begin
                    n_kq_cmp = n_kq_cmp + 1;
                    if (fk_hist[h][(cyc - 7 * h) % 64] !== rk[h] || fq_hist[h][(cyc - 7 * h) % 64] !== rq[h]) begin
                        n_kq_mis = n_kq_mis + 1;
                        if (n_kq_mis <= 10) $display("KQMIS cyc %0d out %0d", cyc, h);
                    end
                end
                fk_hist[h][cyc % 64] = fk[h]; fq_hist[h][cyc % 64] = fq[h];
            end
            if (cyc > 300) begin
                n_term_cmp = n_term_cmp + 1;
                if (fk[8] !== kin_hist[(cyc - 17) % 64]) n_term_mis = n_term_mis + 1;
            end
            // ---- drive next row
            if (cyc < n_rows) w = tr[cyc]; else w = '0 | 1'b1;
            rst_n = w[0]; ql_v = w[1]; ql_head = hb + w[9:2]; ql_codes = w[521:10]; ql_sc = w[553:522];
            ql_w = w[569:554]; k_key = w[1113:570]; kvalid = w[1114];
            kin_hist[cyc % 64] = k_key;
            if (!rst_n) begin
                if (since_rst != 0) n_resets = n_resets + 1;
                ring = '0; since_rst = 0;
            end else begin
                ring = {ring[LAT-2:0], kvalid}; since_rst = since_rst + 1;
            end
        end
        $display("hb %0d rows %0d warm_resets %0d valid_records %0d valid_faults %0d valid_zero %0d valid_mismatch %0d",
                 hb_i, n_rows, n_resets, n_valid, n_vfault, n_zero, n_vmis);
        $display("all_cycle_mismatch_outside_reset %0d qk_age_compares %0d qk_age_mismatch %0d term_key16_compares %0d term_key16_mismatch %0d",
                 n_all_mis, n_kq_cmp, n_kq_mis, n_term_cmp, n_term_mis);
        if (n_vmis == 0 && n_kq_mis == 0 && n_term_mis == 0 && n_all_mis == 0 && n_valid > 1000 && n_vfault > 0
            && n_vfault < n_valid)
            $display("PASS irg_fastpad_chunk hb %0d", hb_i);
        else
            $display("FAIL irg_fastpad_chunk hb %0d", hb_i);
        $finish;
    end
endmodule
