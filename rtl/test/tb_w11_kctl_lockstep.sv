`timescale 1ns/1ps
// lockstep equivalence: ot_hdc_v41x_idx_kctl_ring (new) vs the compare form (ref: the module at 7361f422, renamed
// ot_hdc_v41x_idx_kctl_ring_ref); every output port compared on every cycle, one HBM model driven from the ref
module tb_w11_kctl_lockstep #(parameter integer NPC = 32, WB = 128, GA = 120, AW = 30, HW = 23, TAGW = 16, LENW = 4,
                    BEATW = 4, NSCAN = 2000, MAXK = 6000, SEED = 1, RDYP = 70, DRP = 60, RSPP = 70) (input wire clk);
    localparam integer FD = 1024;
    reg rst_n = 0;
    reg cmd_v = 0;
    reg [HW-1:0] cmd_base = 0, cmd_base2 = 0;
    reg [9:0] cmd_skip = 0;
    reg [HW+9:0] cmd_nkeys = 0, cmd_nkeys2 = 0;
    reg [NPC-1:0] req_rdy = 0, rsp_v_m = 0;
    reg dr_ready = 0;
    wire [NPC-1:0] rsp_v;
    reg [NPC*TAGW-1:0] rsp_tag;
    wire [NPC*BEATW-1:0] rsp_beat = 0;
    wire busy_r, busy_n, drs_r, drs_n, drq_r, drq_n;
    wire [NPC-1:0] rv_r, rv_n, rr_r, rr_n;
    wire [NPC*AW-1:0] ra_r, ra_n;
    wire [NPC*LENW-1:0] rl_r, rl_n;
    wire [NPC*TAGW-1:0] rt_r, rt_n;
    wire [$clog2(WB)-1:0] ds_r, ds_n;
    wire [1:0] dq_r, dq_n;
    wire [4:0] df_r, df_n, dk_r, dk_n;
    wire [5:0] dx_r, dx_n;
    ot_hdc_v41x_idx_kctl_ring_ref #(.NPC(NPC),.WB(WB),.GA(GA),.AW(AW),.HW(HW),.TAGW(TAGW),.LENW(LENW),.BEATW(BEATW)) u_r (
        .clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd_base(cmd_base),.cmd_skip(cmd_skip),.cmd_nkeys(cmd_nkeys),
        .cmd_base2(cmd_base2),.cmd_nkeys2(cmd_nkeys2),.busy(busy_r),.req_v(rv_r),.req_rdy(req_rdy),.req_addr(ra_r),
        .req_len(rl_r),.req_tag(rt_r),.rsp_v(rsp_v),.rsp_rdy(rr_r),.rsp_tag(rsp_tag),.rsp_beat(rsp_beat),
        .dr_scale(drs_r),.dr_quarter(drq_r),.dr_slot(ds_r),.dr_q(dq_r),.dr_fold(df_r),.dr_sidx(dx_r),.dr_nkeys(dk_r),
        .dr_ready(dr_ready));
    ot_hdc_v41x_idx_kctl_ring #(.NPC(NPC),.WB(WB),.GA(GA),.AW(AW),.HW(HW),.TAGW(TAGW),.LENW(LENW),.BEATW(BEATW)) u_n (
        .clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd_base(cmd_base),.cmd_skip(cmd_skip),.cmd_nkeys(cmd_nkeys),
        .cmd_base2(cmd_base2),.cmd_nkeys2(cmd_nkeys2),.busy(busy_n),.req_v(rv_n),.req_rdy(req_rdy),.req_addr(ra_n),
        .req_len(rl_n),.req_tag(rt_n),.rsp_v(rsp_v),.rsp_rdy(rr_n),.rsp_tag(rsp_tag),.rsp_beat(rsp_beat),
        .dr_scale(drs_n),.dr_quarter(drq_n),.dr_slot(ds_n),.dr_q(dq_n),.dr_fold(df_n),.dr_sidx(dx_n),.dr_nkeys(dk_n),
        .dr_ready(dr_ready));
    // per-channel in-order return queue
    reg [TAGW-1:0] ft [0:NPC*FD-1];
    reg [31:0]     fti[0:NPC*FD-1];
    reg [15:0] wp [0:NPC-1];
    reg [15:0] rp [0:NPC-1];
    reg [31:0] last_t [0:NPC-1];
    reg [31:0] cyc = 0;
    integer p, k, nscan = 0, idle = 0, mism = 0, nreq = 0, nbeat = 0, scyc = 0, lat;
    reg [NPC-1:0] have;
    always @* for (p = 0; p < NPC; p = p + 1) begin
        have[p] = (wp[p] != rp[p]) && (fti[p*FD + (rp[p] % FD)] <= cyc);
        rsp_tag[p*TAGW +: TAGW] = ft[p*FD + (rp[p] % FD)];
    end
    assign rsp_v = have & rsp_v_m;
    initial for (p = 0; p < NPC; p = p + 1) begin wp[p] = 0; rp[p] = 0; last_t[p] = 0; end
    function automatic [HW+9:0] rkeys(input integer dummy);
        integer r;
        begin
            r = $unsigned($random) % 8;
            if (r == 0) rkeys = 0;
            else if (r == 1) rkeys = 1 + $unsigned($random) % 70;
            else if (r == 2) rkeys = 1024 * (1 + $unsigned($random) % 5);
            else if (r == 3) rkeys = 1024 * (1 + $unsigned($random) % 5) + ($unsigned($random) % 3) - 1;
            else rkeys = 1 + $unsigned($random) % MAXK;
        end
    endfunction
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 5) rst_n <= 1;
        req_rdy <= 0; rsp_v_m <= 0;
        for (p = 0; p < NPC; p = p + 1) begin
            if (($unsigned($random) % 100) < RDYP && (wp[p] - rp[p]) < FD - 32) req_rdy[p] <= 1'b1;
            if (($unsigned($random) % 100) < RSPP) rsp_v_m[p] <= 1'b1;
        end
        dr_ready <= ($unsigned($random) % 100) < DRP;
        if (rst_n) begin
            // compare every port
            if ({busy_r, rv_r, ra_r, rl_r, rt_r, rr_r, drs_r, drq_r, ds_r, dq_r, df_r, dx_r, dk_r} !==
                {busy_n, rv_n, ra_n, rl_n, rt_n, rr_n, drs_n, drq_n, ds_n, dq_n, df_n, dx_n, dk_n}) begin
                mism = mism + 1;
                if (mism < 10) $display("MISMATCH cyc=%0d scan=%0d busy %b/%b rv %h/%h rr %h/%h drs %b/%b drq %b/%b ds %0d/%0d dk %0d/%0d ra_eq=%0d rt_eq=%0d rl_eq=%0d",
                    cyc, nscan, busy_r, busy_n, rv_r, rv_n, rr_r, rr_n, drs_r, drs_n, drq_r, drq_n, ds_r, ds_n, dk_r, dk_n,
                    ra_r == ra_n, rt_r == rt_n, rl_r == rl_n);
            end
            // HBM model (driven from the reference's outputs)
            for (p = 0; p < NPC; p = p + 1) begin
                if (rsp_v[p] && rr_r[p]) begin rp[p] <= rp[p] + 1; nbeat = nbeat + 1; end
                if (rv_r[p] && req_rdy[p]) begin
                    nreq = nreq + 1;
                    lat = 1 + $unsigned($random) % 24;
                    if (last_t[p] < cyc + lat) last_t[p] <= cyc + lat;
                    for (k = 0; k < rl_r[p*LENW +: LENW]; k = k + 1) begin
                        ft[p*FD + ((wp[p] + k) % FD)] = rt_r[p*TAGW +: TAGW];
                        fti[p*FD + ((wp[p] + k) % FD)] = ((last_t[p] > cyc + lat) ? last_t[p] : cyc + lat) + k;
                    end
                    wp[p] <= wp[p] + rl_r[p*LENW +: LENW];
                end
            end
            cmd_v <= 1'b0;
            if (!busy_r && !cmd_v) begin
                idle = idle + 1;
                if (idle > ($unsigned($random) % 4)) begin
                    if (nscan == NSCAN) begin
                        $display("W11_KCTL_LOCKSTEP %s scans=%0d cycles=%0d requests=%0d beats=%0d mismatches=%0d",
                                 (mism == 0) ? "PASS" : "FAIL", nscan, cyc, nreq, nbeat, mism);
                        $finish;
                    end
                    idle = 0; nscan = nscan + 1;
                    cmd_v <= 1'b1;
                    cmd_base <= ($unsigned($random) % 4 == 0) ? (HW'(1) << (HW - 1)) - HW'($unsigned($random) % 64) : HW'($unsigned($random));
                    cmd_skip <= ($unsigned($random) % 3 == 0) ? 10'd0 : 10'($unsigned($random));
                    cmd_nkeys <= rkeys(0);
                    cmd_nkeys2 <= ($unsigned($random) % 2) ? rkeys(0) : 0;
                    cmd_base2 <= HW'($unsigned($random));
                end
            end else if (busy_r && ($unsigned($random) % 50 == 0)) begin
                // a command while busy is ignored
                cmd_v <= 1'b1; cmd_nkeys <= rkeys(0); cmd_base <= HW'($unsigned($random));
            end
        end
        if (cyc > 200000000) begin $display("W11_KCTL_LOCKSTEP TIMEOUT"); $finish; end
    end
endmodule
