`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Does hardware fan-out plus descriptor coarsening actually remove the control
// bottleneck? Measured on 16 REAL compute units, each with its real weight SRAM,
// driven by the real cluster dispatcher.
//
// The control plane is modelled as what it is measured to be: a source that can
// deliver one descriptor every 567 datapath cycles (116.4 sequencer cycles at
// 265 MHz, seen from 1,290 MHz). It holds a descriptor until the queue takes it,
// because that is what a stalled sequencer does.
//
// The metric is ARRAY utilisation -- summed busy cycles over all units, divided
// by units times elapsed cycles -- not single-unit utilisation, because the
// bottleneck being tested is precisely the one that appears when a sequencer has
// to feed many units.
//
// The prediction under test, from tools/audit_control_path_throughput.py: one
// K-pass per descriptor gives about 48 %, and three or more gives ~100 %.
// ---------------------------------------------------------------------------
module tb_cluster_dispatch_throughput;
    localparam integer UNITS = 16, LANES = 16, ACC_W = 40, PASS_W = 6;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;

    reg              desc_valid;
    wire             desc_ready;
    reg [8:0]        desc_k;
    reg [7:0]        desc_scale;
    reg [PASS_W-1:0] desc_passes;

    wire             cu_start;
    wire [8:0]       cu_cfg_k;
    wire [7:0]       cu_cfg_scale;
    wire [UNITS-1:0] cu_busy, cu_done;

    wire [31:0] descs, passes, cl_cycles, starved;
    wire [63:0] unit_busy;

    ot_cluster_dispatcher #(.UNITS(UNITS), .QUEUE_LOG2(3), .PASS_W(PASS_W)) disp (
        .clk(clk), .rst_n(rst_n),
        .desc_valid(desc_valid), .desc_ready(desc_ready),
        .desc_k(desc_k), .desc_scale(desc_scale), .desc_passes(desc_passes),
        .cu_start(cu_start), .cu_cfg_k(cu_cfg_k), .cu_cfg_scale(cu_cfg_scale),
        .cu_busy(cu_busy), .cu_done(cu_done),
        .descriptors_retired(descs), .passes_launched(passes),
        .unit_busy_cycles(unit_busy), .cluster_cycles(cl_cycles),
        .starved_cycles(starved));

    //: SIXTEEN real compute units, each with its own pair of fakeram macros.
    //: Modelling them as counters would assume away exactly what is being
    //: measured -- that a broadcast start and a gathered done actually keep every
    //: unit busy.
    genvar g;
    generate
        for (g = 0; g < UNITS; g = g + 1) begin : unit
            wire [ACC_W-1:0] res;
            wire [LANES-1:0] drop;
            wire rr, st;
            ot_compute_unit #(.LANES(LANES), .ACC_W(ACC_W), .K_MAX(256)) cu (
                .clk(clk), .rst_n(rst_n),
                .start(cu_start), .cfg_k(cu_cfg_k), .cfg_scale(cu_cfg_scale),
                .busy(cu_busy[g]), .done(cu_done[g]),
                .wr_en(1'b0), .wr_addr(8'b0), .wr_data({16*LANES{1'b0}}),
                .act_we(1'b0), .act_waddr(9'b0), .act_wdata(16'b0),
                .refill_valid(1'b1), .refill_ready(rr), .stalled(st),
                .res_sel(5'b0), .res_data(res), .dropped_mask(drop));
        end
    endgenerate

    task run_case(input integer k, input integer np, input integer interval,
                  input integer ndesc);
        integer sent, countdown, guard;
        real util, starve_frac;
        begin
            rst_n = 0; desc_valid = 0;
            desc_k = k[8:0]; desc_scale = 8'd200; desc_passes = np[PASS_W-1:0];
            repeat (4) @(negedge clk);
            rst_n = 1;
            @(negedge clk);

            sent = 0; countdown = 0; guard = 0;
            while (!(descs >= ndesc) && guard < 400000) begin
                desc_valid = (countdown == 0) && (sent < ndesc);
                @(negedge clk);
                if (desc_valid && desc_ready) begin
                    sent = sent + 1; countdown = interval - 1;
                end else if (countdown > 0) countdown = countdown - 1;
                guard = guard + 1;
            end
            desc_valid = 0;

            util = (cl_cycles > 0)
                 ? 100.0 * unit_busy / (1.0 * UNITS * cl_cycles) : 0.0;
            starve_frac = (cl_cycles > 0) ? 100.0 * starved / cl_cycles : 0.0;
            $display("  K=%3d passes=%2d interval=%3d : descs=%3d passes=%4d  array util=%5.1f%%  starved=%5.1f%%",
                     k, np, interval, descs, passes, util, starve_frac);
        end
    endtask

    initial begin
        $display("16 real compute units, real cluster dispatcher, control modelled at its measured rate");
        $display("  interval 567 datapath cycles = 116.4 sequencer cycles at 265 MHz seen from 1290 MHz");
        $display("  -- fan-out only, one K-pass per descriptor: the audit predicts ~48%% --");
        run_case(256, 1, 567, 30);
        $display("  -- fan-out plus coarsening: the audit predicts ~100%% from 3 passes --");
        run_case(256, 2, 567, 30);
        run_case(256, 3, 567, 30);
        run_case(256, 4, 567, 30);
        run_case(256, 8, 567, 20);
        $display("  -- control infinitely fast, for the dispatcher's own ceiling --");
        run_case(256, 1, 1, 30);
        run_case(256, 4, 1, 30);
        $display("DONE cluster dispatch sweep");
        $finish;
    end
endmodule
