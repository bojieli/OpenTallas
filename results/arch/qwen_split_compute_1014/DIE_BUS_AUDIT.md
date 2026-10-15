# Qwen split compute die: die-bus audit against the reference array (2026-10-14, compute-die lead r2)

Reference: `rtl/hdc/ot_qwen_me_array_w12.sv` (`ot_qwen_me_array_w12` + `ot_qwen_me_spine_w12`), production TP8
parameters W 16, AW 24, NW 18, GT 3,072, TG 4, SMIN 7, SMAX 11, TCUT 6, IL 8 (768 tiles, 48 block words, NXL 512).
Die: the split compute generator (`OT_TP8_SPLIT=compute`), measured on build C3 (src b723ed282, Codex) and the
C4..C7 plan. Arrival model: `tools/qwen_split/tree_skew.py <build>/out/rom_tp8b.json`.
Port binding: `tools/qwen_split/die_port_bind.py <case>/die.v`.

The reference is a LOCKSTEP array: one BD for every tile, one NWS per tree level, one TWS for all 48 block words, and
the node takes `valid` from leg a only. The die is not lockstep by construction: every tile sees go after its own
head + corridor stages and every leg has its own relay count. Everything below that says "pad" is required for the
die to compute the reference's values, not for timing.

| # | Bus | Reference (port, width, distinct / broadcast, rate) | Die (C3) | Verdict / fix (build) |
|---|-----|------|------|------|
| 1 | instruction go + ib | `tgo` 1 + `tb` 379 (3 NW + 13 AW + 13), one broadcast to 768 tiles, uniform BD | head chain + corridor stations, station word 508 + ready; go arrival 18..73 stages per tile | width OK, broadcast OK. Skew is legal only because the top waits XD = max and the node legs are padded (row 3). |
| 2 | x lines | `xl` TG x 32 = 128 b per tile, line t mod 512 (distinct per tile, tiles t / t+512 share), one quad per IL 8 edges, held | central VM x network (retired) | DVM (owner 10-14): `qfd_xcst` corridor word 516 = {go, ib 379, xl 128, tag 8}, TDM 8 tiles x 128 b per 8 edges = the reference rate. Exact array bench PASS (DX8, el1014-qwen-dvm-build.log). |
| 3 | tree legs | `n_a` / `n_b` W x 32 = 512 + `n_va` (leg a) per node, NWS per level uniform, distinct per node | 512 b, NO valid, NO fault; 503 of 720 nodes misaligned (max leg skew 106 stages, 4,027 pad cycles); tp8b carries no tree pads (only tp8a had the frozen pad file) | FIX C5+: every node's early leg padded from the build's own chains (inline `arrival_pads`); FIX C6+: tree word = {fault, valid, 512} = 514 b on t_out / n_a / n_b / n_y (one width for the one tile master; the node may check va == vb). |
| 4 | block words (level TCUT -> top) | `t_lvl` 48 x 512, uniform TWS | bword stages 6..149; arrival spread at a slab up to 220 cycles vs the slab's 4-deep BW FIFO | FIX C5+: pad every block word to its slab's latest arrival; C6+: 514 b {fault, valid, 512}. OPEN (r5 / slab owners): W half (prim) vs E half (f1 + pfrag) alignment at the band primary, and band -> tree top (tt_c / tt_f) alignment: the slab RTL must join on valid with depth >= the residual skew the build reports. |
| 5 | tile id | `tile_id` = t (0..767): sets i_gbase = t x TG (output rows), the ROM image and the x chunk TG x t mod S; tree pairs t (2k, 2k+1) | NO strap on the die (Codex 10-14); DVM builder assumed column x 16 + row | FIX C6+: tie `tile_id` = 16 x block + morton(c mod 4, r mod 4), block = 4 x (c div 4) + r div 4 (the die tree pairs in morton order, block b = top word b). DVM's tid0 + row arithmetic does NOT match (ids are not affine in the row): die gives each `qfd_xcol` a 256-b strap `tids` (16 ids, N stations 0..7 then S 8..15). RTL CHANGE REQUEST to the DVM builder (xhead takes tids). |
| 6 | fault | `fab_fault` = OR of every tile fault -> top fault | tile `fault` not wired (768 outputs unread) | FIX C6+: fault rides the tree / block words (bit 513), OR at every node. Tile RTL change (q-tile). xcol `fault` (48) still unread: DIE REQUEST to the DVM builder (chain it inward on the head row). |
| 7 | KV port | `t_kv_re` / `t_kv_addr` / `t_kv_q` (2,048 b per tile in) global KV (KV_LOCAL 0) | not on the die (wsrc ops are KV/system-die ops) | the qfd_tile_nk RTL wrapper must be the NO-KV variant (wsrc 1 faults); a tied kv_q would be a tied functional input (owner no-stub rule). Request to q-tile. |
| 8 | scale ROM | `scale_q` 24 x 256 per result port group | port-local scale ROM in the port tiles (SCALE_LOCAL) | no die bus: OK. |
| 9 | results | 24 port groups `o_we/o_addr/o_mask/o_data` (512 data), ORD | slabs -> res_ser (rq 4,425) -> VM (rs 551 per band, credit rc, rok rk) | serialised by design (res_ser c2 view); measured rate against ORD is the r5 res_ser item. |
| 10 | tap ready | tile has no back-pressure | station `tap_r` tied 1 on 768 stations | protocol truth of a lockstep tile; recorded tie. Cleaner: an `xcst` variant without tap_r (DVM builder). |
| 11 | DVM chain termini | n/a | outermost xcst ready (a_r / b_r) and edge xcol (w_r / e_r) | C7: tied 1 (no downstream) and recorded; the downstream word outputs are unread. |
| 12 | per-child clocks | n/a | tt_up4 one ck; xcol one ck | C7: tt_up4 ck_pin + ck_l0..3 (RTL define OT_QFD_UP4_CK_ENTRIES); xcol ck0..ck8 die ports (DIE REQUEST: scalar ck0..ck8 in the slot wrapper; RTL today ck[8:0]). |

Head-root word (DVM): the head roots take ONE word from the x tap (`qfd_xs_tap` hw / he 1,567 b = {go, ib, desc,
fill}); the tree top's go / ib (tt_ib 380) goes to the tap, not to the VM, so go and fill share one pipeline and the
fill-before-go order holds by construction. RTL CHANGE REQUEST to the DVM builder: tap input gi[379:0], two registered
copies hw / he of the head word; the central VM drops xw / xe / ib (VM6) and exposes the attention-return write xaw
(553 b) to the tap; the SU exposes its lane write xsw (2,137 b).
