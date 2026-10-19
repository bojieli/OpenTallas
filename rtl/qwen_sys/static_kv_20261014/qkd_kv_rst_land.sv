`timescale 1ns/1ps
// TW2-KVGRP 2026-10-19: registered reset LANDING + replicated relay of a generated KV static tile (the group tiles
// qkd_kvs_grp / qkd_kvs_grp_h under OT_KV_TILE_KITS=1; generator tools/qwen_kv_die/kv_static_die.py).
//
// Standards: ROOT-RST 2026-10-19 (a reset INPUT lands at the face; the port net reaches at most the two reset pins of an
// async-assert synchroniser, textbook_lint reset_landing) + the 10-10 regional reset relay (one register copy per
// consumer, so no reset net from the port or from one flop spans the 1,186-um tile; the --cts gates @de94cee48 had
// rst_n / hrst_n straight to ~14 k RESETN / reset-D pins: setup -642 ps).
//   s[1:0]  async-assert / sync-release synchroniser on the port (the ONLY loads of rst_n_in: 2 CLR pins)
//   q[N-1:0] one kept plain register per consumer (D = s[1]); consumers reset from q[k]
// Assert: the synchroniser clears at once, every consumer sees it 1 edge later (the clock runs during reset).
// Release: 3 edges after the port (s[0], s[1], q).  Kit record: kv_static_die.kit_delays()['rst'] / grp_chain().rst_relay.
module qkd_kv_rst_land #(
    parameter integer N = 1
) (
    input  wire         ck,
    input  wire         rst_n_in,
    output wire [N-1:0] rst_n
);
    (* async_reg = "true" *) reg [1:0] s;
    always @(posedge ck or negedge rst_n_in) begin
        if (!rst_n_in) s <= 2'b00;
        else           s <= {s[0], 1'b1};
    end
    (* keep = "true", dont_touch = "true" *) reg [N-1:0] q;
    always @(posedge ck) q <= {N{s[1]}};
    assign rst_n = q;
endmodule
