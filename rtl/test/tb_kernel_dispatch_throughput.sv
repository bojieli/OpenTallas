`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// IS THE CONTROL PATH THE BOTTLENECK?
//
// The datapath closes at 1,290 MHz and the control plane at 548 MHz, spending
// about 39 of its own cycles per engine command. Whether that starves the array
// is not a matter of opinion and it is not answered by comparing the two clock
// numbers: it depends on how long ONE descriptor keeps the array busy. This
// bench measures it.
//
// The control plane is modelled as what it is measured to be -- a source that
// produces one descriptor every ISSUE_INTERVAL datapath cycles. That interval is
// the control plane's real cost translated into the datapath's clock:
//
//     ISSUE_INTERVAL = ctrl_cycles_per_desc * (f_datapath / f_control)
//                    = 39 * (1290/548) = 92 datapath cycles
//
// Modelling it this way rather than instantiating the 2,098-line sequencer is
// deliberate and is the stronger test: the sequencer's issue rate is already
// measured end-to-end by G1e against a golden model, and what is unknown is what
// that rate does to array utilisation. Driving the real dispatcher and the real
// compute unit from a rate-accurate source isolates exactly that, and it lets the
// interval be SWEPT, which the fixed sequencer cannot be.
//
// The measurement is array utilisation, separated into the two reasons the array
// can be idle: a descriptor was waiting and the dispatcher did not launch it
// (the dispatcher's fault), or the queue was empty (the control plane's fault).
// Only the second is control being the bottleneck.
// ---------------------------------------------------------------------------
module tb_kernel_dispatch_throughput;
    localparam integer LANES = 16, ACC_W = 40;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;

    // ---- descriptor source: the control plane's measured issue rate --------
    reg        desc_valid;
    wire       desc_ready;
    reg [8:0]  desc_k;
    reg [7:0]  desc_scale;

    wire       cu_start, cu_busy, cu_done;
    wire [8:0] cu_cfg_k;
    wire [7:0] cu_cfg_scale;
    wire [31:0] launched, busy_c, idle_c, starved_c;

    ot_kernel_dispatcher #(.LANES(LANES), .ACC_W(ACC_W), .QUEUE_LOG2(3)) disp (
        .clk(clk), .rst_n(rst_n),
        .desc_valid(desc_valid), .desc_ready(desc_ready),
        .desc_k(desc_k), .desc_scale(desc_scale),
        .cu_start(cu_start), .cu_cfg_k(cu_cfg_k), .cu_cfg_scale(cu_cfg_scale),
        .cu_busy(cu_busy), .cu_done(cu_done),
        .kernels_launched(launched), .busy_cycles(busy_c),
        .idle_cycles(idle_c), .starved_cycles(starved_c));

    // the real compute unit, weights always available (refill_valid high): this
    // bench isolates CONTROL, so the memory path is deliberately not the limiter
    wire [ACC_W-1:0] res_data;
    wire [LANES-1:0] dropped;
    wire refill_ready, stalled;
    wire [8:0] refill_col;

    ot_compute_unit #(.LANES(LANES), .ACC_W(ACC_W), .K_MAX(256)) cu (
        .clk(clk), .rst_n(rst_n),
        .start(cu_start), .cfg_k(cu_cfg_k), .cfg_scale(cu_cfg_scale),
        //: default REFILL_DECOUPLED=0: refill_valid is a token, so the payload is
        //: tied off and wgt_reload is high on every start.  This bench isolates
        //: CONTROL and checks no results, so the weight store is never written.
        .wgt_reload(1'b1), .acc_continue(1'b0), .acc_scale_violation(),
        .busy(cu_busy), .done(cu_done),
        .wr_en(1'b0), .wr_addr(8'b0), .wr_data({16*LANES{1'b0}}),
        .act_we(1'b0), .act_waddr(9'b0), .act_wdata(16'b0),
        .refill_valid(1'b1), .refill_data({16*LANES{1'b0}}),
        .refill_col(refill_col), .refill_ready(refill_ready), .stalled(stalled),
        .res_sel(5'b0), .res_data(res_data), .dropped_mask(dropped));


    //: A control plane that produces one descriptor every `interval` cycles and
    //: HOLDS it until the queue accepts it.  Offering a descriptor for one cycle
    //: and dropping it when the queue is full models nothing real, and it
    //: inverted the whole result: interval=1 came out with LOWER utilisation than
    //: interval=92, because a fast source filled the 8-deep queue, lost every
    //: descriptor it could not place, and then had none left to send.
    //:
    //: Measurement stops the cycle the last kernel retires.  Counting the cycles
    //: after that charges the control plane for an idle array that has no work
    //: left to do, which is not starvation.
    task run_case(input integer k, input integer interval, input integer kernels);
        integer sent, countdown, guard;
        real util, starve_frac, per_kernel;
        begin
            rst_n = 0; desc_valid = 0; desc_k = k[8:0]; desc_scale = 8'd200;
            repeat (4) @(negedge clk);
            rst_n = 1;
            @(negedge clk);

            sent = 0; countdown = 0; guard = 0;
            while (!(launched == kernels && !cu_busy) && guard < 200000) begin
                desc_valid = (countdown == 0) && (sent < kernels);
                @(negedge clk);
                if (desc_valid && desc_ready) begin
                    sent = sent + 1;
                    countdown = interval - 1;
                end else if (countdown > 0)
                    countdown = countdown - 1;
                guard = guard + 1;
            end
            desc_valid = 0;

            util = (busy_c + idle_c + starved_c) > 0
                 ? 100.0 * busy_c / (busy_c + idle_c + starved_c) : 0.0;
            starve_frac = (busy_c + idle_c + starved_c) > 0
                 ? 100.0 * starved_c / (busy_c + idle_c + starved_c) : 0.0;
            per_kernel = (launched > 0) ? 1.0 * busy_c / launched : 0.0;
            $display("  K=%3d interval=%3d : launched=%2d busy=%5d idle=%3d starved=%5d  util=%5.1f%%  starved=%5.1f%%  busy/kernel=%0.1f",
                     k, interval, launched, busy_c, idle_c, starved_c, util, starve_frac, per_kernel);
        end
    endtask

    initial begin
        $display("control-plane issue rate vs array utilisation, real dispatcher + real compute unit");
        $display("  (interval 92 datapath cycles = the measured 39 control cycles at 548 MHz, seen from 1,290 MHz)");
        // a descriptor that keeps the array busy far longer than control takes
        //: interval=1 is the ceiling: control never limits, so utilisation here
        //: is the DISPATCHER's own overhead and nothing else.
        run_case(256, 1,  40);
        run_case(256, 92, 40);
        run_case(256, 280, 40);
        run_case(256, 540, 40);
        run_case( 64, 1,  40);
        run_case( 64, 92, 40);
        run_case( 64, 200, 40);
        run_case( 16, 1,  40);
        run_case( 16, 92, 40);
        $display("DONE dispatch throughput sweep");
        $finish;
    end
endmodule
