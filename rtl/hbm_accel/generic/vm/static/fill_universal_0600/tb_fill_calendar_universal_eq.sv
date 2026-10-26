`timescale 1ns/1ps
`default_nettype none
// H-NETLIST 0600: the HBM fill calendar vmfc_<q> (ot_vms_calendar_static W=89) is replaced on the die by the CLOSED
// universal VM calendar master hfd_hgi_vm_calendar (W=187, native PASS). This bench runs both on the same W89
// programme images and launches (reserved bits 89..223 zero) and compares calendar[88:0] (= the universal's packed
// fields client_seq..rslot[7:0]), calendar_v, ordinal, active, done and fault on EVERY edge after reset release.
// MUT=1/2: the reference engine's own mutants (wrong wrap PC / extra loop edge) must be detected.
module tb_fill_calendar_universal_eq;
    parameter integer MUT=0, SEED=1;
    reg clk=0; always #5 clk=~clk;
    wire clk_cap=clk, clk_mem=clk;
    reg rst_n=0, cfg_we=0, start_v=0;
    reg [9:0] cfg_addr=0, start_base=0; reg [255:0] cfg_data=0; reg [10:0] start_limit=0; reg [15:0] start_loops=0;
    wire [88:0] ref_cal; wire ref_v, ref_active, ref_done, ref_fault; wire [31:0] ref_ord;
    ot_vms_calendar_static #(.W(89), .MUT(MUT)) ref_cal_i(.clk(clk), .rst_n(rst_n), .cfg_we(cfg_we), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data), .start_v(start_v), .start_base(start_base), .start_limit(start_limit), .start_loops(start_loops),
        .calendar(ref_cal), .calendar_v(ref_v), .ordinal(ref_ord), .active(ref_active), .done(ref_done), .fault(ref_fault));
    wire calendar_v, active, done, fault; wire [31:0] ordinal;
    wire [9:0] client_seq; wire [4:0] response_enable; wire [9:0] response_seq; wire [7:0] bank_enable;
    wire [23:0] bank_client; wire [1:0] hub_ring_enable; wire [5:0] hub_ring_client; wire [7:0] rslot_v, wslot_v;
    wire [23:0] rslot, wslot; wire [1:0] ring_tx_enable; wire [5:0] ring_tx_source; wire replay_enable, replay_source;
    wire [23:0] lg_local_read, lg_local_write;
    hfd_hgi_vm_calendar dut(.*);
    wire [186:0] got = {lg_local_write, lg_local_read, replay_source, replay_enable, ring_tx_source, ring_tx_enable, wslot,
                        rslot, wslot_v, rslot_v, hub_ring_client, hub_ring_enable, bank_client, bank_enable, response_seq,
                        response_enable, client_seq};
    integer errors=0, checked=0, launches=0, nonzero=0, i, l, seed;
    reg compare=0;
    always @(negedge clk) if (compare) begin
        checked = checked + 1;
        if (got[88:0] !== ref_cal || got[186:89] !== 98'd0 || calendar_v !== ref_v || ordinal !== ref_ord ||
            active !== ref_active || done !== ref_done || fault !== ref_fault) begin
            errors = errors + 1;
            if (errors < 6) $display("MISMATCH t=%0t cal %h/%h v %b/%b ord %0d/%0d act %b/%b done %b/%b fault %b/%b", $time,
                got[88:0], ref_cal, calendar_v, ref_v, ordinal, ref_ord, active, ref_active, done, ref_done, fault, ref_fault);
        end
        if (ref_v && ref_cal != 0) nonzero = nonzero + 1;
    end
    task automatic tick; begin @(posedge clk); #1; end endtask
    reg [88:0] w;
    integer base, len, loops;
    initial begin
        seed = SEED;
        repeat (3) tick; rst_n = 1; repeat (4) tick; compare = 1;
        // install 1024 programme words: magic c7a1, PC identity = row, random W89 payload, reserved zero
        for (i = 0; i < 1024; i = i + 1) begin
            w = {$random(seed), $random(seed), $random(seed)};
            cfg_we = 1; cfg_addr = i[9:0]; cfg_data = {16'hc7a1, 6'd0, i[9:0], 135'd0, w}; tick;
        end
        cfg_we = 0; repeat (8) tick;
        for (l = 0; l < 24; l = l + 1) begin
            base = ($random(seed) & 1023); len = 1 + ($random(seed) & 63); if (base + len > 1024) base = 1024 - len;
            loops = 1 + ($random(seed) & 3);
            start_v = 1; start_base = base[9:0]; start_limit = base + len; start_loops = loops[15:0]; tick; start_v = 0;
            launches = launches + 1;
            repeat (len * loops + 12) tick;
        end
        compare = 0;
        if (errors == 0 && nonzero > 0)
            $display("FILL_UNIVERSAL_EQ PASS checks=%0d launches=%0d nonzero_edges=%0d", checked, launches, nonzero);
        else begin $display("FILL_UNIVERSAL_EQ FAIL errors=%0d checks=%0d nonzero_edges=%0d", errors, checked, nonzero); $fatal(1, "eq"); end
        $finish;
    end
endmodule
`default_nettype wire
