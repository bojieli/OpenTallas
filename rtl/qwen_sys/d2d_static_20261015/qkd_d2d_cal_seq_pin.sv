`timescale 1ns/1ps
// Actual pin-capture successor of the compiler-constant KV calendar sequencer.
// EP_SKEW is the declared package/physical-path anchor skew at the external
// pins, including neither this local input capture nor generic extra pin FFs.
// Epoch/functional inputs: +1 capture; local reset release: +2 fixed edges.
// Reload and halt are exceptional inputs, observed one edge later explicitly.
// All cfg/cal outputs remain the actual sequencer output registers (no extra
// output cycle); internal EP_SKEW-1 compensates the epoch input capture.
// Must be re-proved/physically gated with its own name; no inherited raw view.
module qkd_d2d_cal_seq_pin #(parameter integer GO_OFS = 0, parameter [20*36-1:0] START_ADJ = '0, parameter integer EP_SKEW = 3) (
    input wire ck, rst_n, reload, tok_go, epoch_go, halt,
    output wire cfg_tx_we, cfg_rx_we, output wire [5:0] cfg_addr, output wire [31:0] cfg_data,
    output wire cal_start, cal_seg, cal_ready, running, output wire [5:0] layer, output wire adm_done, tok_start, fault);
    // Pin capture consumes exactly one epoch edge. Keep the output calendar
    // at the same declared package anchor by subtracting this fixed edge.
    // No ready/credit/arrival signal can reschedule the normal programme.
    reg [1:0] release_q;
    reg reload_q,tok_go_q,epoch_go_q,halt_q;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            release_q<=0;reload_q<=0;tok_go_q<=0;epoch_go_q<=0;halt_q<=1;
        end else begin
            release_q<={release_q[0],1'b1};
            reload_q<=reload;tok_go_q<=tok_go;epoch_go_q<=epoch_go;halt_q<=halt;
        end
    end
    qkd_d2d_cal_seq #(.GO_OFS(GO_OFS),.START_ADJ(START_ADJ),.EP_SKEW(EP_SKEW-1)) u_seq(
        .ck(ck),.rst_n(release_q[1]),.reload(reload_q),.tok_go(tok_go_q),.epoch_go(epoch_go_q),.halt(halt_q),
        .cfg_tx_we(cfg_tx_we),.cfg_rx_we(cfg_rx_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .cal_start(cal_start),.cal_seg(cal_seg),.cal_ready(cal_ready),.running(running),.layer(layer),
        .adm_done(adm_done),.tok_start(tok_start),.fault(fault));
endmodule
