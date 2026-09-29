`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_link_chan_model: SIMULATION-ONLY model of the analog PHY and channel of
// one link direction (W15).  Not synthesizable; it stands for the parts no
// digital RTL can: serializer and driver, the channel flight, the receiver's
// analog front end / ADC / DSP equaliser and clock recovery.
//
// Frames launched on the transmit link clock edge n arrive at time
//     t_n + DLY_NS + wander(t) + jitter_n
// and are captured by the RECOVERED clock, which is the transmit clock
// delayed by DLY_NS + wander(t) + half a period (the CDR locks mid-eye).
// A frame therefore reaches the receiving PCS on recovered edge n exactly
// while |jitter_n| < half a period: jitter inside the eye does not move a
// frame between cycles, which is what "within spec" means for a PHY.  What
// DOES move the digital timing is
//   * the static latency, drawn per link per run in
//     [DLY_NS, DLY_NS + JSTATIC_NS] (PHY lock / gearbox / deskew-FIFO
//     pointer placement differs at every link training), and
//   * slow wander of up to +-WANDER_NS over the run (temperature, supply),
// both of which shift the recovered clock against the receiving die's core
// clock, and so change the cycle a synchroniser passes a frame through.
// SEED selects the draw; the testbench sweeps seeds.
//
// FLIP_AT >= 0 flips one payload bit of frame FLIP_AT (an uncorrectable
// error past the FEC; the receiver's CRC must catch it).
// ---------------------------------------------------------------------------
module ot_link_chan_model #(
    parameter integer FRW        = 64,
    parameter real    T_NS       = 1.0,     // link clock period (recovered clock period)
    parameter real    JDYN_FRAC  = 0.0,     // per-frame jitter as a fraction of half a period (< 1)
    parameter integer HIST       = 1024
) (
    input  wire            clk_tx,
    input  wire            f_valid,
    input  wire [FRW-1:0]  f_data,
    input  real            DLY_NS,      // nominal launch-to-arrival latency
    input  real            JSTATIC_NS,  // static latency variation drawn per run
    input  real            WANDER_NS,   // slow wander amplitude
    input  integer         seed,
    input  integer         flip_at,
    output reg             rclk,
    output reg             rf_valid,
    output reg [FRW-1:0]   rf_data
);
    real           static_ns;
    reg  [FRW-1:0] hd [0:HIST-1];
    reg            hv [0:HIST-1];
    real           ta [0:HIST-1];                        // arrival time of frame n
    integer ntx = 0, nrx = 0, s;
    real    t0 = -1.0, wan, jit, dly;
    integer late = 0;
    initial begin
        rclk = 1'b0; rf_valid = 1'b0; rf_data = 0;
        #0.001;
        s = seed;
        static_ns = DLY_NS + JSTATIC_NS * ($unsigned($random(s)) % 1000001) / 1000000.0;
    end
    function automatic real wander_at(input real t);
        // a slow triangle of period ~20 us and amplitude WANDER_NS, phase set by the seed
        real ph, x;
        begin
            ph = (t + 1000.0 * (seed % 17)) / 20000.0;
            x = ph - $floor(ph);
            wander_at = WANDER_NS * (x < 0.5 ? (4.0 * x - 1.0) : (3.0 - 4.0 * x));
        end
    endfunction
    always @(posedge clk_tx) begin
        if (t0 < 0.0) t0 = $realtime;
        jit = JDYN_FRAC * (T_NS / 2.0) * ((($unsigned($random(s)) % 2000001) / 1000000.0) - 1.0);
        hd[ntx % HIST] = (ntx == flip_at) ? (f_data ^ {{(FRW-1){1'b0}}, 1'b1} << (ntx % (FRW - 32))) : f_data;
        hv[ntx % HIST] = f_valid;
        ta[ntx % HIST] = $realtime + static_ns + wander_at($realtime) + jit;
        ntx = ntx + 1;
    end
    // recovered clock: edge n at t0 + n*T + static + wander + T/2
    initial begin : g_rclk
        real tn;
        integer n;
        wait (t0 >= 0.0);
        n = 0;
        forever begin
            tn = t0 + n * T_NS + static_ns + wander_at(t0 + n * T_NS) + T_NS / 2.0;
            if (tn > $realtime) #(tn - $realtime);
            rclk = 1'b1;
            #(T_NS / 2.0);
            rclk = 1'b0;
            n = n + 1;
        end
    end
    always @(posedge rclk) begin
        if (nrx < ntx) begin
            if (ta[nrx % HIST] > $realtime) late = late + 1;   // cannot happen while |jitter| < T/2
            rf_valid <= hv[nrx % HIST];
            rf_data  <= hd[nrx % HIST];
            nrx = nrx + 1;
        end else rf_valid <= 1'b0;
    end
endmodule
