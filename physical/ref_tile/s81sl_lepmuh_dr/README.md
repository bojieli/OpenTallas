s81sl_lepmuh_dr -- MU endpoint (ot_s81sl_lep_mu_h, RX_SRAM=1, IN_PIPE=1) gate kit, S81-MUBUF3 10-19 (lane of LEAD3-S81).
Structural successor of s81sl_lepmuh_b64 (gate FAIL GPL-0305 NaN, routability inflation ~170%) and s81sl_lepmuh_sf
(gate FAIL DPL on a 32.4 um band). RTL, params, keep list and benches are byte-identical to the b64 kit.

Why the band family fails (cut analysis): every SRAM here has its 397-437 signal pins on its W/E faces (8,740 macro pins
in all) and the tile has 6.9k face pins. A central std band puts ALL the logic for those pins in one strip, so the
horizontal cut at the band edge (y=324 in b64) carries ~5.7k macro nets (TX3/TX4 + all RX) + 2.2k N-face nets against
~3.3k vertical M3/M5 tracks (channels + M5 over macros): ~2.4x over. GPL's routability inflation (179%/164%) then
diverges (NaN); a thinner band (sf) is too dense for DPL. Neither is fixable by band height.

Change: no row pruning, no GPL row envelope. Standard full-core rows with 10.8 um macro halos, so the macro interface
flops sit beside the macro faces and the face-pin flops beside their faces. Every row between macro rows is full width
and PDN-connected (no islands). Macros back on the _sf 43.2-lattice rows (TX 43.2..388.8 at 86.4 pitch, RX 475.2/518.4),
outline 475.2 x 561.6 (b64 604.8), std_area_um2 = SYNTHESIS area (b64 gate measured).

SAFE-DESIGN checklist (pre-gate; gate packet re-checks 3/6/7 on actual placement):
 1 Pins: PASS -- source-registered pin flops (as b64); reset_landing 2 stages.
 2 Reach: PASS -- rows next to every macro face and face; farthest pin->macro face < 300 um.
 3 Fanout: FIXED (b64) -- 6 kept ot_s81sl_lep_vcopy copies <= 28 loads; keep_modules gate item checks survival.
 4 Depth: PASS -- mapped depth ~368 ps (b64 gate textbook).
 5 Storage: PASS -- RX + TX in 20 SRAM macros.
 6 Floorplan: FIXED -- distributed full-width rows; 43.2 lattice; channels >= 22.4; aspect 1.18. Fill 26-27% is
   macro-lattice/channel bound (TX 86.4 pitch, 2 columns), not std-area bound: waived via fill_reason (spec).
   Known open (shared SRAM owner, LEP-HIERARCHY): macro-face contact density ~11/um > 6/um.
 7 Clock: gate-checked -- clk W pin at mid-height (272.8-280.8), one root ~18.1k sinks (guidance); spread <= 80 TT+FF.
 8 Schedule: unchanged vs b64 (+1 edge IN_PIPE already in the LEAD2-S81 INBOX).
