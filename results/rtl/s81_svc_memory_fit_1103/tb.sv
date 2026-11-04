`timescale 1ns/1ps
// MEM v2 fit gate (S81 svc, 2026-11-03): each right-sized child against the child it replaces, same stimulus,
// 833 ps clock, two-state zero start (both forms start from zeroed arrays, as the T7 gates did).
//   LAND : ot_t7_land_capture_v2 vs ot_t7_land_capture_candidate, all 1060 q bits every edge
//   PMEM : ot_t7_pmem_capture_v2 vs ot_t7_pmem_capture_candidate, slot0/slot1 every edge
//   PVQ  : ot_t7_pvq_capture_v2  vs ot_t7_pvq_capture_candidate, out every edge
//   STAGE: ot_hdc_v41x_attn_staging_fit vs the unchanged module SRAM_MACRO=0 (native) and =1 (closure form),
//          rd_data compared when the sampled rd_addr < DEPTH (rows >= DEPTH do not exist natively)
module tb;
reg clk = 0;
always #0.4165 clk = ~clk;
// LAND
reg [223:0] WR_ADDR = 0; reg [1791:0] WR_DATA = 0, WR_EN = 0; reg [9:0] rc = 1;
reg [3:0] valid = 0, win = 0, need = 0; reg [31:0] scale = 0;
wire [1059:0] lq_ref, lq_new;
ot_t7_land_capture_candidate l_ref (clk, WR_ADDR, WR_DATA, WR_EN, rc, valid, win, need, scale, lq_ref);
ot_t7_land_capture_v2        l_new (clk, WR_ADDR, WR_DATA, WR_EN, rc, valid, win, need, scale, lq_new);
// PMEM
reg [8:0] pr = 0, pwa = 0; reg [1:0] pstep = 0; reg owner = 0, push = 0, wp = 0; reg [511:0] pwd = 0, pwm = 0;
wire [1023:0] s0_ref, s1_ref, s0_new, s1_new;
ot_t7_pmem_capture_candidate p_ref (clk, pr, pwa, pstep, owner, push, wp, pwd, pwm, s0_ref, s1_ref);
ot_t7_pmem_capture_v2        p_new (clk, pr, pwa, pstep, owner, push, wp, pwd, pwm, s0_new, s1_new);
// PVQ
reg dr_on = 0; reg [2:0] p_i = 0, ra = 0, vwa = 0; reg [2119:0] vwd = 0, vwm = 0; reg [47:0] prov = 0;
wire [512:0] v_ref, v_new;
ot_t7_pvq_capture_candidate v_r (clk, dr_on, p_i, ra, vwa, vwd, vwm, prov, v_ref);
ot_t7_pvq_capture_v2        v_n (clk, dr_on, p_i, ra, vwa, vwd, vwm, prov, v_new);
// STAGE
localparam integer SW = 1060;
reg [3:0] s_we = 0; reg [7:0] s_wa = 0, s_ra = 0; reg [SW-1:0] s_wd = 0;
wire [SW-1:0] g_nat, g_mac, g_fit;
ot_hdc_v41x_attn_staging     #(.D(32), .NL(4), .TROWS(640), .SRAM_MACRO(1'b0)) st_nat (clk, s_we, s_wa, s_wd, s_ra, g_nat);
ot_hdc_v41x_attn_staging     #(.D(32), .NL(4), .TROWS(640), .SRAM_MACRO(1'b1)) st_mac (clk, s_we, s_wa, s_wd, s_ra, g_mac);
ot_hdc_v41x_attn_staging_fit #(.D(32), .NL(4), .TROWS(640), .SRAM_MACRO(1'b1)) st_fit (clk, s_we, s_wa, s_wd, s_ra, g_fit);

integer i, j, cyc = 0, nl = 0, np = 0, nv = 0, ns = 0, lnz = 0, loob = 0, lwrap = 0, pnz = 0, vnz = 0, vpart = 0, snz = 0;
integer bad = 0;
reg [7:0] s_rs;
function automatic [9:0] row10(input integer r);
    row10 = (r % 16 == 0) ? 10'(640 + ($urandom % 384)) : 10'($urandom % 640);
endfunction
task automatic rnd(inout reg [2119:0] v, input integer n);
    for (j = 0; j < n / 32 + 1; j = j + 1) v[32*j +: 32] = $urandom;
endtask
reg [2119:0] tmp;
initial begin
    for (i = 0; i < 20000; i = i + 1) begin
        @(negedge clk);
        // ---- LAND: 7 writer slots, 3 channels; rows mostly < 640; rc mostly in range, sometimes 161..416 (oob, wrap)
        WR_EN = 0;
        for (j = 0; j < 7; j = j + 1) if ($urandom % 3 == 0) WR_EN[256*j] = 1'b1;
        for (j = 0; j < 7; j = j + 1) begin
            WR_ADDR[32*j +: 10] = row10($urandom);
            if (j == 0 || j == 3) WR_ADDR[32*j +: 8] = 8'($urandom);
        end
        tmp = 0; rnd(tmp, 1792); WR_DATA = tmp[1791:0];
        case ($urandom % 8)
            0: rc = 10'(161 + ($urandom % 256));
            1: rc = 10'($urandom);
            default: rc = 10'(1 + ($urandom % 160));
        endcase
        valid = 4'($urandom); win = 4'($urandom); need = 4'($urandom); scale = $urandom;
        // ---- PMEM
        pr = 9'($urandom); pwa = 9'($urandom); pstep = 2'($urandom); owner = $urandom; push = ($urandom % 3) != 0;
        wp = $urandom; tmp = 0; rnd(tmp, 512); pwd = tmp[511:0]; tmp = 0; rnd(tmp, 512);
        pwm = ($urandom % 4 == 0) ? {512{1'b1}} : ($urandom % 3 == 0) ? 512'd0 : tmp[511:0];
        if ($urandom % 2) pwm[511:256] = 0; else if ($urandom % 2) pwm[255:0] = 0;
        // ---- PVQ: masks per 64-bit bank: all-ones, zero or random, so pairs see one-sided writes
        dr_on = ($urandom % 4) != 0; p_i = 3'($urandom % 5); ra = 3'($urandom); vwa = 3'($urandom);
        tmp = 0; rnd(tmp, 2120); vwd = tmp; tmp = 0; rnd(tmp, 2120); vwm = tmp;
        for (j = 0; j < 33; j = j + 1)
            case ($urandom % 4) 0: vwm[64*j +: 64] = 0; 1: vwm[64*j +: 64] = '1; default: ; endcase
        if ($urandom % 2) vwm[2119:2112] = 0;
        prov = {$urandom, $urandom};
        // ---- STAGE: 10% out-of-range addresses, 25% read-during-write
        s_we = 4'($urandom); s_wa = ($urandom % 10 == 0) ? 8'(160 + $urandom % 96) : 8'($urandom % 160);
        s_ra = ($urandom % 10 == 0) ? 8'(160 + $urandom % 96) : 8'($urandom % 160);
        if ($urandom % 4 == 0) s_ra = s_wa;
        tmp = 0; rnd(tmp, SW); s_wd = tmp[SW-1:0];
        s_rs = s_ra;
        if (32'(rc) - 1 >= 160 && 32'(rc) - 1 < 256) loob = loob + 1;
        if (32'(rc) - 1 >= 256) lwrap = lwrap + 1;
        @(posedge clk); #0.2;
        cyc = cyc + 1;
        nl = nl + 1; if (lq_ref != 0) lnz = lnz + 1;
        if (lq_ref !== lq_new) begin bad = bad + 1; if (bad < 4) $display("FIT_FAIL LAND edge=%0d", i); end
        np = np + 1; if (s0_ref != 0 || s1_ref != 0) pnz = pnz + 1;
        if (s0_ref !== s0_new || s1_ref !== s1_new) begin bad = bad + 1; if (bad < 4) $display("FIT_FAIL PMEM edge=%0d", i); end
        nv = nv + 1; if (v_ref[511:0] != 0) vnz = vnz + 1;
        if (v_ref !== v_new) begin bad = bad + 1; if (bad < 4) $display("FIT_FAIL PVQ edge=%0d", i); end
        if (s_rs < 160) begin
            ns = ns + 1; if (g_nat != 0) snz = snz + 1;
            if (g_nat !== g_fit || g_mac !== g_fit) begin bad = bad + 1; if (bad < 4) $display("FIT_FAIL STAGE edge=%0d", i); end
        end
    end
    if (bad != 0) begin $display("FIT_FAIL total=%0d", bad); $fatal(1); end
    $display("FIT_PASS edges=%0d land=%0d(nz %0d, oob %0d, wrap %0d) pmem=%0d(nz %0d) pvq=%0d(nz %0d) stage=%0d(nz %0d)",
             cyc, nl, lnz, loob, lwrap, np, pnz, nv, vnz, ns, snz);
    $finish;
end
endmodule
