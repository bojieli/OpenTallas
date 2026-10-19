`timescale 1ns/1ps
// Simulation-only, read-only observation of a REAL ot_s81sl_lep_core.
// Attach to the actual source and mapped far endpoint; never drive any DUT pin.
// All values are sampled before NBA at a rising edge. Therefore release at D
// is visible as ri/ml_wv at D+1; ml_rv at E is visible as ri at E+2.
// The caller supplies the existing bench cycle counter, not a new time origin.
// Valid bits qualify every payload; zero/held payload is never a valid event.
module s81_link_observation_probe #(
    parameter string ENDPOINT = "UNBOUND",
    parameter string OUTFILE = "UNBOUND.jsonl"
) (
    input wire clk, rst_n,
    input wire [63:0] bench_cycle,
    input wire rov, hp_go, kp_go, push, bsel,
    input wire [1:0] sq,
    input wire [1103:0] roq, fr,
    input wire rel, rpb,
    input wire [552:0] h0, h1,
    input wire ml_wv, ml_rv,
    input wire [1103:0] ml_wd, ml_rd, ri,
    input wire [31:0] mu_rt,
    input wire fault
);
    integer fd;
    initial begin
        if (ENDPOINT == "UNBOUND" || OUTFILE == "UNBOUND.jsonl")
            $fatal(1, "LINK_OBSERVER requires exact mapped endpoint and unique output path");
        fd = $fopen(OUTFILE, "w");
        if (fd == 0) $fatal(1, "LINK_OBSERVER cannot open output");
        $fdisplay(fd, "{\"schema\":\"opentallas.s81.actual_link_trace.v1\",\"endpoint\":\"%s\",\"sampling\":\"posedge_pre_NBA\"}", ENDPOINT);
    end
    always @(posedge clk) begin
        // Record reset/fault transitions as well as every qualified event.
        $fdisplay(fd, "{\"cycle\":%0d,\"reset_n\":%0d,\"fault\":%0d,\"rov\":%0d,\"hp_go\":%0d,\"kp_go\":%0d,\"push\":%0d,\"pair\":%0d,\"sq\":%0d,\"roq\":\"%0276h\",\"fr\":\"%0276h\",\"release\":%0d,\"release_pair\":%0d,\"h0\":\"%0139h\",\"h1\":\"%0139h\",\"ml_wv\":%0d,\"ml_wd\":\"%0276h\",\"ml_rv\":%0d,\"ml_rd\":\"%0276h\",\"ri\":\"%0276h\",\"mu_rt\":\"%08h\"}",
            bench_cycle, rst_n, fault, rov, hp_go, kp_go, push, bsel,
            sq, rov ? roq : 1104'd0, push ? fr : 1104'd0,
            rel, rpb, rel ? h0 : 553'd0, rel ? h1 : 553'd0,
            ml_wv, ml_wv ? ml_wd : 1104'd0,
            ml_rv, ml_rv ? ml_rd : 1104'd0,
            ri[0] ? ri : 1104'd0, ri[0] ? mu_rt : 32'd0);
    end
    final begin
        $fdisplay(fd, "{\"end\":true}");
        $fclose(fd);
    end
endmodule
