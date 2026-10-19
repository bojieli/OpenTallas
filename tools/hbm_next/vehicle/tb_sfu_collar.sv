`timescale 1ns/1ps
`default_nettype none
// VEH-FMT-COLL2/SFU (10-18): format pre-check of sfu_images.py on the REAL col_sfu_SW collar (ot_hbm_static_cfg_collar,
// slice parameters) + sfup_SW programme store (ot_hgi_sfu_programme_store_r10 PAGE_AW 1), wired exactly as slice.v
// (sw2 bundle).  The hleaf_SW a-side output pins are driven from the event file ('<cyc> <kind> <addr> <data>' hex;
// kind 1 cfg row to tgt 116, 2 descriptor, 3 launch), one pulse right after edge <cyc>.  Checks: no collar / store
// fault, collar ready before the launch, io_word reproduces io.hex and compiler_control reproduces ctl.hex bit-exactly
// on consecutive edges from their first non-zero word (then zero), programme_done and io_done seen, collar idle at end.
// Prints SFUCOL PASS / FAIL and the measured launch -> io / io -> control edge offsets.
module tb_sfu_collar;
    string EV = "events.txt";
    parameter string CTL = "ctl.hex";
    parameter string IO = "io.hex";
    parameter integer NCTL = 1334, NIO = 4;
    reg clk = 0, rst_n = 0; always #0.5 clk = ~clk;
    reg cfg_v = 0, desc_v = 0, launch_v = 0; reg [7:0] cfg_target = 0; reg [11:0] cfg_addr = 0; reg [255:0] cfg_data = 0;
    wire [1:0] pw_we; wire [13:0] pw_addr; wire [255:0] pw_data, prm; wire start_v, go, ready, active, cfault;
    wire [220:0] rec;
    wire p_act, p_done, io_act, io_done, sfault; wire [31:0] p_ord, io_ord; wire [470:0] io_word; wire [1741:0] cc;
    ot_hbm_static_cfg_collar #(.PAGE_W(3), .NS(2), .NPR(1), .NREC(0), .NGO(1), .NB(2), .NF(1), .XSER(0)) col(
        .clk(clk), .clk_in(clk), .rst_n(rst_n), .tgt(8'd116), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data), .desc_v(desc_v), .launch_v(launch_v), .c_busy({io_act, p_act}), .c_done(io_done),
        .c_fault(1'b0), .pw_we(pw_we), .pw_addr(pw_addr), .pw_data(pw_data), .prm(prm), .start_v(start_v), .go(go),
        .rec(rec), .ready(ready), .active(active), .fault(cfault));
    ot_hgi_sfu_programme_store_r10 #(.PAGE_AW(1)) st(
        .clk(clk), .rst_n(rst_n), .cfg_we(pw_we[0]), .cfg_stripe(pw_addr[13:11]), .cfg_addr(pw_addr[10:0]),
        .cfg_data(pw_data), .start_base(prm[10:0]), .start_limit(prm[22:11]), .start_loops(prm[38:23]),
        .programme_active(p_act), .programme_done(p_done), .programme_ordinal(p_ord),
        .io_cfg_we(pw_we[1]), .io_cfg_stripe(pw_addr[12:11]), .io_cfg_addr(pw_addr[10:0]), .io_cfg_data(pw_data),
        .io_start_v(start_v), .io_start_base(prm[49:39]), .io_start_limit(prm[61:50]), .io_start_loops(prm[77:62]),
        .io_active(io_act), .io_done(io_done), .io_ordinal(io_ord), .io_word(io_word), .compiler_control(cc), .fault(sfault));
    reg [1741:0] ectl [0:NCTL-1];
    reg [470:0] eio [0:NIO-1];
    integer fd, r, cnt = -1, ev_c, ev_k, last = 0, lc = -1, io0 = -1, cc0 = -1, ioi = 0, cci = 0, errs = 0;
    integer seen_pd = 0, seen_iod = 0, ready_at_launch = 0, cf_at = -1, sf_at = -1;
    reg [11:0] ev_a; reg [255:0] ev_d; reg have = 0;
    initial begin
        if (!$value$plusargs("EV=%s", EV)) EV = "events.txt";
        $readmemh(CTL, ectl); $readmemh(IO, eio);
        fd = $fopen(EV, "r"); if (fd == 0) $fatal(1, "no event file");
        r = $fscanf(fd, "%h %h %h %h\n", ev_c, ev_k, ev_a, ev_d); have = (r == 4);
        repeat (6) @(posedge clk); rst_n = 1;
        repeat (20) @(posedge clk);
        cnt = 0;
    end
    always @(posedge clk) if (cnt >= 0) begin
        // ---- drive: events of cycle cnt take effect right after this edge
        cfg_v <= 0; desc_v <= 0; launch_v <= 0;
        while (have && ev_c == cnt) begin
            if (ev_k == 1) begin cfg_v <= 1; cfg_target <= 8'd116; cfg_addr <= ev_a; cfg_data <= ev_d; end
            else if (ev_k == 2) begin desc_v <= 1; cfg_target <= 8'd116; end
            else if (ev_k == 3) begin launch_v <= 1; lc = cnt; ready_at_launch = ready; end
            last = cnt;
            r = $fscanf(fd, "%h %h %h %h\n", ev_c, ev_k, ev_a, ev_d); have = (r == 4);
        end
        // ---- checks on the store outputs at this edge
        if (cfault && cf_at < 0) cf_at = cnt;
        if (sfault && sf_at < 0) sf_at = cnt;
        if (p_done) seen_pd = 1;
        if (io_done) seen_iod = 1;
        if (io0 < 0 && io_word != 0) io0 = cnt;
        if (io0 >= 0) begin
            if (ioi < NIO) begin
                if (io_word !== eio[ioi]) begin errs = errs + 1; if (errs < 6) $display("MISMATCH io row %0d edge %0d", ioi, cnt); end
                ioi = ioi + 1;
            end else if (io_word != 0) begin errs = errs + 1; if (errs < 6) $display("MISMATCH io trailing edge %0d", cnt); end
        end
        if (cc0 < 0 && cc != 0) cc0 = cnt;
        if (cc0 >= 0) begin
            if (cci < NCTL) begin
                if (cc !== ectl[cci]) begin errs = errs + 1; if (errs < 6) $display("MISMATCH ctl row %0d edge %0d", cci, cnt); end
                cci = cci + 1;
            end else if (cc != 0) begin errs = errs + 1; if (errs < 6) $display("MISMATCH ctl trailing edge %0d", cnt); end
        end
        cnt <= cnt + 1;
        if (!have && cnt > last + NCTL + 400) begin
            $display("SFUCOL launch=%0d io_first=%0d ctl_first=%0d launch_to_io=%0d io_to_ctl=%0d ctl_rows=%0d io_rows=%0d",
                     lc, io0, cc0, io0 - lc, cc0 - io0, cci, ioi);
            $display("SFUCOL collar_fault_at=%0d store_fault_at=%0d ready_at_launch=%0d programme_done=%0d io_done=%0d active_end=%0d",
                     cf_at, sf_at, ready_at_launch, seen_pd, seen_iod, active);
            if (cf_at < 0 && sf_at < 0 && ready_at_launch && seen_pd && seen_iod && !active && errs == 0 && lc >= 0 &&
                cci == NCTL && ioi == NIO)
                $display("SFUCOL PASS");
            else $display("SFUCOL FAIL errs=%0d", errs);
            $finish;
        end
    end
endmodule
`default_nettype wire
