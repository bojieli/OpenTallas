`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_vm_wfc_ep: the VM-side end of the WFC kit's VM channels (Claude mtp-wfc, 2026-10-10; main decision: posted
// writes on an in-order channel under the PCIe / AXI same-ID rule).  Serial (0.9 GHz) domain, one VM request port.
//
//   kit vmx --(grant link, VF/VR hub stations)--> [lrx_rtt sw] -+-> one in-order op pipe (PIPE stages) --> VM port
//                                                [lrx_rtt sr] -+        (write / read / START doorbell)
//   VM port fixed-latency read data --> t_srq {rv, rq}   (push-only; the vmx holds response-queue space per read)
//   START doorbell at the pipe exit --> t_ks {start, user, token, pos} toward the capture (stage core start)
//   sticky status --> t_err (level; the vmx checks it at k_done, i.e. at the transaction end)
//
// Ordering proof (by construction):
//   (a) the vmx issues its writes, then the START doorbell, on ONE channel in order (ot_dsrom_wfc_vmx POSTED 1);
//   (b) the hub stations and the RTT receiver are FIFOs: one queue per hop, no reordering;
//   (c) here every op, the doorbell included, enters ONE pipe in arrival order; a write reaches the VM pins PIPE
//       cycles after it leaves the receiver, and the doorbell raises START only when it leaves the same pipe, i.e.
//       at least one cycle after every earlier write has been presented at the VM pins;
//   (d) the VM (ot_s81ph_vm_mem / dsfd_vm_bgq) applies ops in global (issue cycle, port) order with per-bank in-order
//       queues, so any read the core issues after START (it cannot issue earlier) sees every earlier write.
//   No bank-level reordering exists to defeat (d); so no per-address scoreboard is needed.
// Reads (the vmx's outbound prefetch) take the same pipe; the core's TX writes precede k_done, and the vmx issues
// those reads only after k_done, so the read-after-write order on the way out is the core's own issue order.
// Mutant OT_VMWFC_MUT_EARLY_START: START at the pipe ENTRY (before the earlier writes reach the VM) -> must FAIL.
// ---------------------------------------------------------------------------------------------------------------
module dsfd_vm_wfc_ep #(
    parameter integer FLIT = 512, parameter integer NW = 21, parameter integer USER_W = 10, parameter integer VWA = 15,
    parameter integer VF = 13, parameter integer VR = 13,     // hub stations kit -> VM (requests) / VM -> kit (grants)
    parameter integer PIPE = 2,                               // registered stages from the receivers to the VM pins
    parameter integer RL = 6,                                 // VM port read latency (cycles from the pins)
    parameter integer VMROWS = 16384,                         // VM rows (ot_s81ph_vm_mem NB 32 x 512); beyond -> error
    parameter integer RD2 = 0                                 // 2-port prefetch: request {v1, row1, row0}, VM ports 0 + 1
) (
    input  wire [0:0] ck, rst,
    input  wire [0:0] f_swv, input wire [VWA+FLIT-1:0] f_swd, output wire [0:0] t_swg,   // kit writes + doorbell
    input  wire [0:0] f_srv, input wire [(RD2 ? 2*VWA+1 : VWA)-1:0] f_srd, output wire [0:0] t_srg,   // kit reads
    output reg  [(RD2 ? 2*FLIT+2 : FLIT+1)-1:0] t_srq,                                    // {[rv1, rq1,] rv, rq}
    output reg  [0:0] t_err,                                                               // sticky status level
    output reg  [USER_W+2*NW:0] t_ks,                                                      // START toward the core
    // VM request port (one op a cycle, never stalls) and its fixed-latency read return
    output reg  [0:0] m_v, output reg [0:0] m_we, output reg [VWA-1:0] m_row, output reg [FLIT-1:0] m_d,
    input  wire [0:0] m_ov, input wire [FLIT-1:0] m_od,
    input  wire [0:0] m_fault,
    output reg  [0:0] m1_v, output reg [VWA-1:0] m1_row,                                   // RD2: VM port 1 (odd reads)
    input  wire [0:0] m1_ov, input wire [FLIT-1:0] m1_od
);
    localparam integer MARK = (1 << VWA) - 1;
    wire clk = ck[0];
    reg [1:0] rs_q; always @(posedge clk or negedge rst[0]) if (!rst[0]) rs_q <= 2'b00; else rs_q <= {rs_q[0], 1'b1};
    wire rn = rs_q[1];
    localparam integer SRW = RD2 ? 2*VWA+1 : VWA;
    wire wv, rv; wire [VWA+FLIT-1:0] wd; wire [SRW-1:0] rd; wire wr_, rr_;
    ot_dsrom_mtp_lrx_rtt #(.W(VWA+FLIT), .D(VF+VR+4), .ENABLE_RTT(1), .FORWARD_HOPS(VF), .RETURN_HOPS(VR)) u_sw (
        .clk(clk), .rst_n(rn), .l_valid(f_swv[0]), .l_ready(t_swg[0]), .l_data(f_swd), .c_valid(wv), .c_ready(wr_), .c_data(wd));
    ot_dsrom_mtp_lrx_rtt #(.W(SRW), .D(VF+VR+4), .ENABLE_RTT(1), .FORWARD_HOPS(VF), .RETURN_HOPS(VR)) u_sr (
        .clk(clk), .rst_n(rn), .l_valid(f_srv[0]), .l_ready(t_srg[0]), .l_data(f_srd), .c_valid(rv), .c_ready(rr_), .c_data(rd));
    // one op a cycle into the pipe: the write channel first (its doorbell must not be passed by nothing it orders;
    // reads are independent of the inbound writes: different VM regions, issued only after k_done)
    assign wr_ = 1'b1;
    assign rr_ = !wv;
    wire take_w = wv, take_r = rv && !wv;
    wire is_mark = take_w && wd[FLIT +: VWA] == VWA'(MARK);
    // op pipe: {v, we, mark, row, data}
    reg p_v [0:PIPE-1]; reg p_we [0:PIPE-1]; reg p_mk [0:PIPE-1]; reg [VWA-1:0] p_row [0:PIPE-1]; reg [FLIT-1:0] p_d [0:PIPE-1];
    reg p_v1 [0:PIPE-1]; reg [VWA-1:0] p_row1 [0:PIPE-1];
    integer i;
    always @(posedge clk) begin
        if (!rn) for (i = 0; i < PIPE; i = i + 1) begin p_v[i] <= 1'b0; p_mk[i] <= 1'b0; p_v1[i] <= 1'b0; end
        else begin
            p_v[0] <= take_w || take_r; p_we[0] <= take_w; p_mk[0] <= is_mark;
            p_row[0] <= take_w ? wd[FLIT +: VWA] : rd[VWA-1:0]; p_d[0] <= wd[FLIT-1:0];
            p_v1[0] <= RD2 && take_r && rd[SRW-1]; p_row1[0] <= rd[(RD2 ? VWA : 0) +: VWA];
            for (i = 1; i < PIPE; i = i + 1) begin
                p_v[i] <= p_v[i-1]; p_we[i] <= p_we[i-1]; p_mk[i] <= p_mk[i-1]; p_row[i] <= p_row[i-1]; p_d[i] <= p_d[i-1];
                p_v1[i] <= p_v1[i-1]; p_row1[i] <= p_row1[i-1];
            end
        end
    end
    // VM pins (registered): the doorbell is NOT a VM op; it raises START one cycle after it leaves the pipe
    always @(posedge clk) begin
        if (!rn) begin m_v <= 1'b0; m1_v <= 1'b0; t_ks <= '0; t_err <= 1'b0; end
        else begin
            m_v <= p_v[PIPE-1] && !p_mk[PIPE-1]; m_we <= p_we[PIPE-1]; m_row <= p_row[PIPE-1]; m_d <= p_d[PIPE-1];
            m1_v <= p_v1[PIPE-1]; m1_row <= p_row1[PIPE-1];             // the pair's odd read, same cycle, port 1
`ifdef OT_VMWFC_MUT_EARLY_START
            t_ks <= is_mark ? {1'b1, wd[USER_W+2*NW-1:0]} : '0;           // MUTANT: START at the pipe entry
`else
            t_ks <= (p_v[PIPE-1] && p_mk[PIPE-1]) ? {1'b1, p_d[PIPE-1][USER_W+2*NW-1:0]} : '0;
`endif
            if (m_fault || (p_v[PIPE-1] && !p_mk[PIPE-1] && p_row[PIPE-1] >= VWA'(VMROWS))) t_err <= 1'b1;   // sticky
        end
    end
    // fixed-latency read return -> push to the kit (the vmx reserved the response-queue slot when it issued)
    always @(posedge clk) t_srq <= !rn ? '0 : RD2 ? {m1_ov, m1_od, m_ov, m_od} : {m_ov, m_od};
endmodule
