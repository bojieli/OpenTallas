// Slot cell qkd_kvwq_ctl_bin through its OWN ports against an independent bundle model: the benched body
// ot_qkvd_kv_wq_ctl_binary #(FLANE_BINARY=1) runs in lock step on the same stimulus and every slot bundle is compared
// bit-exact, every cycle, with the documented packing.  Stimulus is credit-true: a row is posted only while fewer than
// QD rows are outstanding, every feed beat is acknowledged 3 cycles after it leaves the CELL's pin (1/64 of them bad).
// sl2: the cell adds a pin stage on f0..f3 / fault: those pins are compared with the body's fields one cycle earlier.
`timescale 1ns/1ps
module tb_qkd_kvwq_ctl_bin_slot;
    localparam integer N = 40000;
    reg ck = 0, rst_n = 0;
    always #1 ck = ~ck;
    reg  [1046:0] kvn_d = 0;
    wire          kvn_cr, fault, m_cr, m_fault, m_rw_v;
    wire [292:0]  f [0:3];
    reg  [1:0]    r [0:3];
    wire [22:0]   durable;
    wire [3:0]    m_fv; wire [1023:0] m_fd; wire [95:0] m_fsec; wire [31:0] m_flane; wire [35:0] m_ftag; wire [21:0] m_rw_id;
    qkd_kvwq_ctl_bin dut (.ck(ck), .rst_n(rst_n), .kvn_d(kvn_d), .kvn_cr(kvn_cr), .f0(f[0]), .f1(f[1]), .f2(f[2]), .f3(f[3]),
        .r0(r[0]), .r1(r[1]), .r2(r[2]), .r3(r[3]), .durable(durable), .fault(fault));
    ot_qkvd_kv_wq_ctl_binary #(.FLANE_BINARY(1)) mdl (.clk(ck), .rst_n(rst_n),
        .kvw_v(kvn_d[1046]), .kvw_vg(kvn_d[1045:1044]), .kvw_t(kvn_d[1043:1030]), .kvw_layer(kvn_d[1029:1024]),
        .kvw_d(kvn_d[1023:0]), .kvw_cr(m_cr), .f_v(m_fv), .f_d(m_fd), .f_sec(m_fsec), .f_lane(m_flane), .f_tag(m_ftag),
        .r_v({r[3][1], r[2][1], r[1][1], r[0][1]}), .r_bad({r[3][0], r[2][0], r[1][0], r[0][0]}),
        .rw_v(m_rw_v), .rw_id(m_rw_id), .fault(m_fault));
    integer i, g, k, out = 0, err = 0, rows = 0, feeds = 0, dur = 0, lanehi = 0;
    reg [3:0] d1 = 0, d2 = 0;
    reg [292:0] e;
    reg [292:0] e1 [0:3];             // sl2: the cell's feed pins are the body's feed one cycle later (pin stage)
    reg         mf1 = 0;              //      and so is the fault level
    reg [3:0]   dfv;
    initial for (g = 0; g < 4; g = g + 1) e1[g] = 0;
    initial begin
        for (g = 0; g < 4; g = g + 1) r[g] = 0;
        repeat (8) @(posedge ck);
        #0.2 rst_n = 1;
        for (i = 0; i < N; i = i + 1) begin
            @(posedge ck); #0.2;
            for (g = 0; g < 4; g = g + 1) begin
                e = {m_fv[g], m_fd[256*g +: 256], m_fsec[24*g +: 24], m_flane[8*g +: 3], m_ftag[9*g +: 9]};
                if (i > 0 && f[g] !== e1[g]) begin err = err + 1; if (err < 4) $display("MISMATCH cyc %0d f%0d", i, g); end
                e1[g] = e;
                if (m_fv[g]) feeds = feeds + 1;
                if (m_flane[8*g+3 +: 5] !== 5'd0 && m_fv[g]) lanehi = lanehi + 1;
            end
            if (durable !== {m_rw_v, m_rw_id}) err = err + 1;
            if (kvn_cr !== m_cr || (i > 0 && fault !== mf1)) err = err + 1;
            mf1 = m_fault;
            if (m_rw_v) dur = dur + 1;
            if (m_cr) out = out - 1;
            for (g = 0; g < 4; g = g + 1) r[g] = {d2[g], d2[g] && ($urandom % 64 == 0)};
            dfv = {f[3][292], f[2][292], f[1][292], f[0][292]};
            d2 = d1; d1 = dfv;
            for (k = 0; k < 1024; k = k + 32) kvn_d[k +: 32] = $urandom;
            kvn_d[1045:1024] = $urandom;
            kvn_d[1046] = (out < 4) && ($urandom % 3 == 0);
            if (kvn_d[1046]) begin out = out + 1; rows = rows + 1; end
        end
        if (err == 0 && rows > 1000 && feeds > 4000 && dur > 1000 && lanehi == 0)
            $display("PASS kv_slots kvwq_ctl_bin cycles=%0d rows=%0d feed_beats=%0d durable=%0d mismatches=0", N, rows, feeds, dur);
        else
            $display("FAIL kv_slots kvwq_ctl_bin cycles=%0d rows=%0d feed_beats=%0d durable=%0d mismatches=%0d lane_hi=%0d", N, rows, feeds, dur, err, lanehi);
        $finish;
    end
endmodule
