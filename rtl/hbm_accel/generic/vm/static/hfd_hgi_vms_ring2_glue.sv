`timescale 1ns/1ps
`default_nettype none
// HBM-BIND 2026-10-24 (B2 die = NW + NE quadrants of r18h5; SW + SE dropped): two-stop VM ring hub masters.
// Hand-written; the glue logic is ot_vms_slice_static_glue (hfd_hgi_vms_static_glue.sv) with NSTOP=2, unchanged
// otherwise. The four-stop masters (hfd_hgi_vms_glue_nw_t, hfd_hgi_vms_static_NE_glue, ...) are untouched.
//
// Ring (PHYSICAL_RING ranks SW0 SE1 NE2 NW3; cw = rank+1). The B2 die keeps exactly the two as-built links between
// the pair, one per direction:   NW.ccw_out -> NE.ccw_in   (NW -> NE)       NE.cw_out -> NW.cw_in   (NE -> NW)
// so every hub keeps ONE ring output and ONE ring input; the as-built NW.cw_out / NW.ccw_in / NE.ccw_out / NE.cw_in
// (to/from SW, SE) are absent from these port lists. Per hub: TX stop = NW u_ccw / NE u_cw (owns the outgoing link,
// injects PREQ, mirror egress, PRSP replay, WACK); RX stop = NW u_cw / NE u_ccw (ejects into hub/replay/banks).
// The idle half of each stop is structurally constant (the TX stop's input and the RX stop's output/controls) and
// is removed by synthesis; it is internal to the master, not a die tie-off.
// Ring controls kept per master = the TX direction's fields of the as-built calendar bundle:
//   ring_tx_enable   = as-built ring_tx_enable[TXD]       ring_tx_source = as-built ring_tx_source[3*TXD+:3]
//   hub_ring_enable  = as-built hub_ring_enable[TXD]      hub_ring_client = as-built hub_ring_client[CW*TXD+:CW]
//   replay_source    : removed (constant: requests only arrive on the RX stop; NW rce0 -> 0, NE rce1 -> 1)
// (TXD: NW 1 = ccw, NE 0 = cw.)  Bank side (b<k>_* / bk_*) is the as-built bus: the RX stop drives the bank remote
// write port of its direction (NW: xq from u_cw; NE: xq2 from u_ccw); the other port (NW xq2, NE xq) is driven by the
// TX stop's eject register, which is constant 0 in a two-stop ring (the banks are reused unchanged).
// Latency per hop is the four-stop one-hop latency (no stage added or removed); see run_vms_ring2_static.sh header.
// NW two-stop hub glue, NC=2 (client 0 = hb_argmax, client 1 = hb_idx__ctl: the two clients of the dropped
// hb_vms_SW, same slot order and calendar field widths as hfd_hgi_vms_static_SW_glue), sid 2, wq2-merge bk_flt.
module hfd_hgi_vms_static_NW2_glue #(parameter integer RMUT=0, HMUT=0) (
    input wire clk_hub,
    input wire [1:0] clk_ring,
    input wire clk_replay,
    input wire rst_n,
    input wire [675:0] cq,
    output wire [547:0] cr,
    input wire [5:0] client_seq,
    input wire [2:0] response_enable,
    input wire [5:0] response_seq,
    input wire [7:0] bank_enable,
    input wire [15:0] bank_client,
    input wire hub_ring_enable,              // ccw (TX) ring request enable
    input wire [1:0] hub_ring_client,        // ccw (TX) ring request client
    input wire [2223:0] cw_in,               // <- NE.cw_out
    output wire [2223:0] ccw_out,            // -> NE.ccw_in
    input wire ring_tx_enable,               // TX stop (u_ccw)
    input wire [2:0] ring_tx_source,
    input wire replay_enable,
    input wire [143:0] bank_status,
    output wire [2207:0] bk_xq,bk_xq2,
    input wire [7:0] bk_xq_done,bk_xq2_done,
    input wire [2207:0] bk_eg,
    output wire [2279:0] bk_pq,
    input wire [2127:0] bk_pr,
    input wire [7:0] bk_flt,                 // wq2-merge leaves vmm_NWb sticky flt -> bank status bit 17
    output wire [2:0] hub_status,
    output wire [1:0] mirror_busy,
    output wire [18:0] vmstat,
    output wire [2:0] ring_fault
);
    wire [143:0] bank_status_m;
    wire [2223:0] rx_stop_out;               // RX stop (u_cw) has no outgoing link in a two-stop ring
    genvar fb;
    generate for(fb=0;fb<8;fb=fb+1)begin:g_flt
        assign bank_status_m[fb*18+:18]={bank_status[fb*18+17]|bk_flt[fb],bank_status[fb*18+:17]};
    end endgenerate
    ot_vms_slice_static_glue #(.NC(2),.RG(5),.WG(3),.NATIVE_SHAPE(1),.BANK_PIN_IN(1),.NSTOP(2),.RMUT(RMUT),.HMUT(HMUT)) u_slice (
        .clk_hub(clk_hub),.clk_ring(clk_ring),.clk_replay(clk_replay),.rst_n(rst_n),
        .sid(2'd2),
        .cq(cq),.cr(cr),
        .client_seq(client_seq),.response_enable(response_enable),.response_seq(response_seq),
        .bank_enable(bank_enable),.bank_client(bank_client),
        .hub_ring_enable({hub_ring_enable,1'b0}),.hub_ring_client({hub_ring_client,2'd0}),
        .cw_in(cw_in),.ccw_in(2224'd0),.cw_out(rx_stop_out),.ccw_out(ccw_out),
        .ring_tx_enable({ring_tx_enable,1'b0}),.ring_tx_source({ring_tx_source,3'd0}),
        .replay_enable(replay_enable),.replay_source(1'b0),
        .bank_status(bank_status_m),
        .bk_xq(bk_xq),.bk_xq2(bk_xq2),.bk_xq_done(bk_xq_done),.bk_xq2_done(bk_xq2_done),
        .bk_eg(bk_eg),.bk_pq(bk_pq),.bk_pr(bk_pr),
        .hub_status(hub_status),.mirror_busy(mirror_busy),.vmstat(vmstat),.ring_fault(ring_fault));
endmodule
// NW two-stop hub-glue tile master (= hfd_hgi_vms_glue_nw_t with the two-stop ring + NC=2 client ports):
// one clock, per-bank ports. Replaces hfd_hgi_vms_glue_nw_t at hb_vms_NW on the B2 die.
module hfd_hgi_vms_glue_nw2_t #(parameter integer RMUT=0, HMUT=0) (
    input wire clk,
    input wire rst_n,
    input wire [675:0] cq,
    output wire [547:0] cr,
    input wire [5:0] client_seq,
    input wire [2:0] response_enable,
    input wire [5:0] response_seq,
    input wire [7:0] bank_enable,
    input wire [15:0] bank_client,
    input wire hub_ring_enable,
    input wire [1:0] hub_ring_client,
    input wire [2223:0] cw_in,
    output wire [2223:0] ccw_out,
    input wire ring_tx_enable,
    input wire [2:0] ring_tx_source,
    input wire replay_enable,
    output wire [275:0] b0_xq,
    output wire [275:0] b0_xq2,
    input wire b0_xq_done,
    input wire b0_xq2_done,
    input wire [275:0] b0_eg,
    output wire [284:0] b0_pq,
    input wire [265:0] b0_pr,
    input wire [17:0] b0_status,
    input wire b0_flt,
    output wire [275:0] b1_xq,
    output wire [275:0] b1_xq2,
    input wire b1_xq_done,
    input wire b1_xq2_done,
    input wire [275:0] b1_eg,
    output wire [284:0] b1_pq,
    input wire [265:0] b1_pr,
    input wire [17:0] b1_status,
    input wire b1_flt,
    output wire [275:0] b2_xq,
    output wire [275:0] b2_xq2,
    input wire b2_xq_done,
    input wire b2_xq2_done,
    input wire [275:0] b2_eg,
    output wire [284:0] b2_pq,
    input wire [265:0] b2_pr,
    input wire [17:0] b2_status,
    input wire b2_flt,
    output wire [275:0] b3_xq,
    output wire [275:0] b3_xq2,
    input wire b3_xq_done,
    input wire b3_xq2_done,
    input wire [275:0] b3_eg,
    output wire [284:0] b3_pq,
    input wire [265:0] b3_pr,
    input wire [17:0] b3_status,
    input wire b3_flt,
    output wire [275:0] b4_xq,
    output wire [275:0] b4_xq2,
    input wire b4_xq_done,
    input wire b4_xq2_done,
    input wire [275:0] b4_eg,
    output wire [284:0] b4_pq,
    input wire [265:0] b4_pr,
    input wire [17:0] b4_status,
    input wire b4_flt,
    output wire [275:0] b5_xq,
    output wire [275:0] b5_xq2,
    input wire b5_xq_done,
    input wire b5_xq2_done,
    input wire [275:0] b5_eg,
    output wire [284:0] b5_pq,
    input wire [265:0] b5_pr,
    input wire [17:0] b5_status,
    input wire b5_flt,
    output wire [275:0] b6_xq,
    output wire [275:0] b6_xq2,
    input wire b6_xq_done,
    input wire b6_xq2_done,
    input wire [275:0] b6_eg,
    output wire [284:0] b6_pq,
    input wire [265:0] b6_pr,
    input wire [17:0] b6_status,
    input wire b6_flt,
    output wire [275:0] b7_xq,
    output wire [275:0] b7_xq2,
    input wire b7_xq_done,
    input wire b7_xq2_done,
    input wire [275:0] b7_eg,
    output wire [284:0] b7_pq,
    input wire [265:0] b7_pr,
    input wire [17:0] b7_status,
    input wire b7_flt,
    output wire [2:0] hub_status,
    output wire [1:0] mirror_busy,
    output wire [18:0] vmstat,
    output wire [2:0] ring_fault
);
    wire [2207:0] bk_xq;
    assign b0_xq = bk_xq[275:0];
    assign b1_xq = bk_xq[551:276];
    assign b2_xq = bk_xq[827:552];
    assign b3_xq = bk_xq[1103:828];
    assign b4_xq = bk_xq[1379:1104];
    assign b5_xq = bk_xq[1655:1380];
    assign b6_xq = bk_xq[1931:1656];
    assign b7_xq = bk_xq[2207:1932];
    wire [2207:0] bk_xq2;
    assign b0_xq2 = bk_xq2[275:0];
    assign b1_xq2 = bk_xq2[551:276];
    assign b2_xq2 = bk_xq2[827:552];
    assign b3_xq2 = bk_xq2[1103:828];
    assign b4_xq2 = bk_xq2[1379:1104];
    assign b5_xq2 = bk_xq2[1655:1380];
    assign b6_xq2 = bk_xq2[1931:1656];
    assign b7_xq2 = bk_xq2[2207:1932];
    wire [7:0] bk_xq_done = {b7_xq_done, b6_xq_done, b5_xq_done, b4_xq_done, b3_xq_done, b2_xq_done, b1_xq_done, b0_xq_done};
    wire [7:0] bk_xq2_done = {b7_xq2_done, b6_xq2_done, b5_xq2_done, b4_xq2_done, b3_xq2_done, b2_xq2_done, b1_xq2_done, b0_xq2_done};
    wire [2207:0] bk_eg = {b7_eg, b6_eg, b5_eg, b4_eg, b3_eg, b2_eg, b1_eg, b0_eg};
    wire [2279:0] bk_pq;
    assign b0_pq = bk_pq[284:0];
    assign b1_pq = bk_pq[569:285];
    assign b2_pq = bk_pq[854:570];
    assign b3_pq = bk_pq[1139:855];
    assign b4_pq = bk_pq[1424:1140];
    assign b5_pq = bk_pq[1709:1425];
    assign b6_pq = bk_pq[1994:1710];
    assign b7_pq = bk_pq[2279:1995];
    wire [2127:0] bk_pr = {b7_pr, b6_pr, b5_pr, b4_pr, b3_pr, b2_pr, b1_pr, b0_pr};
    wire [143:0] bank_status = {b7_status, b6_status, b5_status, b4_status, b3_status, b2_status, b1_status, b0_status};
    wire [7:0] bk_flt = {b7_flt, b6_flt, b5_flt, b4_flt, b3_flt, b2_flt, b1_flt, b0_flt};
    hfd_hgi_vms_static_NW2_glue #(.RMUT(RMUT),.HMUT(HMUT)) u_glue (
        .clk_hub(clk),.clk_ring({clk, clk}),.clk_replay(clk),.rst_n(rst_n),
        .cq(cq),.cr(cr),.client_seq(client_seq),.response_enable(response_enable),.response_seq(response_seq),
        .bank_enable(bank_enable),.bank_client(bank_client),
        .hub_ring_enable(hub_ring_enable),.hub_ring_client(hub_ring_client),
        .cw_in(cw_in),.ccw_out(ccw_out),
        .ring_tx_enable(ring_tx_enable),.ring_tx_source(ring_tx_source),.replay_enable(replay_enable),
        .bank_status(bank_status),
        .bk_xq(bk_xq),.bk_xq2(bk_xq2),.bk_xq_done(bk_xq_done),.bk_xq2_done(bk_xq2_done),
        .bk_eg(bk_eg),.bk_pq(bk_pq),.bk_pr(bk_pr),.bk_flt(bk_flt),
        .hub_status(hub_status),.mirror_busy(mirror_busy),.vmstat(vmstat),.ring_fault(ring_fault));
endmodule
// NE two-stop hub glue (= hfd_hgi_vms_static_NE_glue with the two-stop ring): NC=0 (replay client only), sid 3.
// Replaces hfd_hgi_vms_static_NE_glue at hb_vms_NE on the B2 die.
module hfd_hgi_vms_static_NE2_glue #(parameter integer RMUT=0, HMUT=0) (
    input wire clk_hub,
    input wire [1:0] clk_ring,
    input wire clk_replay,
    input wire rst_n,
    input wire [1:0] client_seq,
    input wire response_enable,
    input wire [1:0] response_seq,
    input wire [7:0] bank_enable,
    input wire [7:0] bank_client,
    input wire hub_ring_enable,              // cw (TX) ring request enable
    input wire hub_ring_client,              // cw (TX) ring request client
    input wire [2223:0] ccw_in,              // <- NW.ccw_out
    output wire [2223:0] cw_out,             // -> NW.cw_in
    input wire ring_tx_enable,               // TX stop (u_cw)
    input wire [2:0] ring_tx_source,
    input wire replay_enable,
    input wire [143:0] bank_status,
    output wire [2207:0] bk_xq,bk_xq2,
    input wire [7:0] bk_xq_done,bk_xq2_done,
    input wire [2207:0] bk_eg,
    output wire [2279:0] bk_pq,
    input wire [2127:0] bk_pr,
    output wire [2:0] hub_status,
    output wire [1:0] mirror_busy,
    output wire [18:0] vmstat,
    output wire [2:0] ring_fault
);
    wire [273:0] vacant_cr; // NC=0: no local clients exist.
    wire [2223:0] rx_stop_out;               // RX stop (u_ccw) has no outgoing link in a two-stop ring
    ot_vms_slice_static_glue #(.NC(0),.RG(4),.WG(2),.NATIVE_SHAPE(1),.BANK_PIN_IN(1),.NSTOP(2),.RMUT(RMUT),.HMUT(HMUT)) u_slice (
        .clk_hub(clk_hub),.clk_ring(clk_ring),.clk_replay(clk_replay),.rst_n(rst_n),
        .sid(2'd3),
        .cq(338'd0),.cr(vacant_cr),
        .client_seq(client_seq),.response_enable(response_enable),.response_seq(response_seq),
        .bank_enable(bank_enable),.bank_client(bank_client),
        .hub_ring_enable({1'b0,hub_ring_enable}),.hub_ring_client({1'b0,hub_ring_client}),
        .cw_in(2224'd0),.ccw_in(ccw_in),.cw_out(cw_out),.ccw_out(rx_stop_out),
        .ring_tx_enable({1'b0,ring_tx_enable}),.ring_tx_source({3'd0,ring_tx_source}),
        .replay_enable(replay_enable),.replay_source(1'b1),
        .bank_status(bank_status),
        .bk_xq(bk_xq),.bk_xq2(bk_xq2),.bk_xq_done(bk_xq_done),.bk_xq2_done(bk_xq2_done),
        .bk_eg(bk_eg),.bk_pq(bk_pq),.bk_pr(bk_pr),
        .hub_status(hub_status),.mirror_busy(mirror_busy),.vmstat(vmstat),.ring_fault(ring_fault));
endmodule
`default_nettype wire
