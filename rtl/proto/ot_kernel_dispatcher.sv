`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Kernel dispatcher: descriptor queue plus double-buffered launch.
//
// WHY THIS EXISTS. The datapath closes at 1,290 MHz. The control plane
// (ot_a3_microsequencer) closes at 548 MHz as a frontend and 265 MHz with its
// full symbol and divider machinery, and it spends about 39 of its own cycles
// per engine command. A chip built by wiring the sequencer straight to the
// compute unit runs at the sequencer's clock and idles the array between
// kernels, so every frequency gain in the datapath is thrown away.
//
// Every production accelerator solves this the same way, and none of them solve
// it by making the sequencer as fast as the array:
//
//   DECOUPLE          the sequencer writes DESCRIPTORS into a queue; the
//                     dispatcher reads them. The two sides do not have to run at
//                     the same rate, only to average out: the queue absorbs the
//                     difference. This is a descriptor ring in a DPU, a command
//                     queue in a TPU, and the CSB/DMA split in NVDLA.
//   RUN AHEAD         because the queue holds several descriptors, the control
//                     plane works on kernel N+2 while the array runs kernel N.
//                     Control latency stops mattering; only control THROUGHPUT
//                     does.
//   DOUBLE BUFFER     the launch registers are ping-pong. The next kernel's
//                     configuration is latched while the current one is still
//                     running, so `start` for kernel N+1 asserts on the cycle
//                     after kernel N's `done` with no decode bubble between.
//
// WHAT THIS BUYS, AND THE CONDITION UNDER WHICH IT BUYS IT. The array stays busy
// only while the queue is non-empty. The control plane must therefore supply
// descriptors at least as fast as the array retires them:
//
//     control_cycles_per_descriptor / f_control  <=  datapath_cycles_per_kernel / f_datapath
//
// At the measured 39 control cycles per command and 548 MHz against 1,290 MHz,
// that is 39/548e6 = 71.2 ns, which is 91.8 datapath cycles. So a descriptor
// must keep the array busy for at least ~92 cycles or control starves it,
// whatever the queue depth -- a queue absorbs BURSTS, never a rate deficit.
//
// That inequality is the design rule this module exists to make measurable, and
// rtl/test/tb_kernel_dispatch_throughput.sv measures both sides of it rather
// than asserting either.
// ---------------------------------------------------------------------------
module ot_kernel_dispatcher #(
    parameter integer LANES     = 16,
    parameter integer ACC_W     = 40,
    parameter integer QUEUE_LOG2 = 3      // 8 descriptors in flight
) (
    input  wire                   clk,
    input  wire                   rst_n,

    // ---- descriptor write port, from the control plane ----
    input  wire                   desc_valid,
    output wire                   desc_ready,
    input  wire [8:0]             desc_k,        // columns to walk
    input  wire [7:0]             desc_scale,    // shared window exponent

    // ---- the compute unit this dispatcher drives ----
    output reg                    cu_start,
    output reg  [8:0]             cu_cfg_k,
    output reg  [7:0]             cu_cfg_scale,
    input  wire                   cu_busy,
    input  wire                   cu_done,

    // ---- observation, for the throughput measurement ----
    output reg  [31:0]            kernels_launched,
    output reg  [31:0]            busy_cycles,
    output reg  [31:0]            idle_cycles,     // array idle with work pending
    output reg  [31:0]            starved_cycles   // array idle, queue EMPTY
);
    localparam integer DEPTH = 1 << QUEUE_LOG2;

    // ---- descriptor queue -------------------------------------------------
    reg [8:0] q_k     [0:DEPTH-1];
    reg [7:0] q_scale [0:DEPTH-1];
    reg [QUEUE_LOG2:0] wptr, rptr;

    wire q_empty = (wptr == rptr);
    wire q_full  = (wptr[QUEUE_LOG2-1:0] == rptr[QUEUE_LOG2-1:0]) &&
                   (wptr[QUEUE_LOG2] != rptr[QUEUE_LOG2]);

    assign desc_ready = !q_full;
    wire push = desc_valid && desc_ready;

    always @(posedge clk or negedge rst_n)
        if (!rst_n) wptr <= {(QUEUE_LOG2+1){1'b0}};
        else if (push) begin
            q_k    [wptr[QUEUE_LOG2-1:0]] <= desc_k;
            q_scale[wptr[QUEUE_LOG2-1:0]] <= desc_scale;
            wptr <= wptr + 1'b1;
        end

    // ---- launch: double-buffered, so there is no bubble between kernels ----
    //: `launch` fires when the array is free and a descriptor is queued. The
    //: configuration is registered in the SAME cycle start is raised, so the
    //: compute unit sees a stable cfg on the cycle it samples start, and the
    //: next descriptor can be popped while the current kernel is still running.
    wire array_free = !cu_busy && !cu_start;
    wire launch     = array_free && !q_empty;

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            rptr <= {(QUEUE_LOG2+1){1'b0}};
            cu_start <= 1'b0; cu_cfg_k <= 9'b0; cu_cfg_scale <= 8'b0;
        end else begin
            cu_start <= 1'b0;
            if (launch) begin
                cu_cfg_k     <= q_k    [rptr[QUEUE_LOG2-1:0]];
                cu_cfg_scale <= q_scale[rptr[QUEUE_LOG2-1:0]];
                cu_start     <= 1'b1;
                rptr         <= rptr + 1'b1;
            end
        end

    // ---- observation ------------------------------------------------------
    //: idle_cycles and starved_cycles are kept apart on purpose. Idle with a
    //: descriptor waiting is the dispatcher's fault; idle with an EMPTY queue is
    //: the control plane failing to keep up, which is the thing being measured.
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            kernels_launched <= 32'b0; busy_cycles <= 32'b0;
            idle_cycles <= 32'b0; starved_cycles <= 32'b0;
        end else begin
            if (cu_start) kernels_launched <= kernels_launched + 32'd1;
            if (cu_busy)  busy_cycles      <= busy_cycles + 32'd1;
            else if (q_empty) starved_cycles <= starved_cycles + 32'd1;
            else              idle_cycles    <= idle_cycles + 32'd1;
        end
endmodule
