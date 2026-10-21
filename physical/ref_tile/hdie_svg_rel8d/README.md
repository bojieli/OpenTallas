# hdie_svg_rel8d -- ot_hbm_svc_sm_group_rel_h (HBM svg hard view, r11 params + QINT8 S1) -- FALLBACK 604.8 x 561.6 (rel8b geometry, enlarged)

Successor of hdie_svg_rel8a/b (HBM-SVGREL8). HBM-COLLECT10/SVG 2026-10-21.

## Why rel8c
rel8a/b gates sat > 8 h in synth_odb.tcl (ep7 / agidock128). The step was the OT_GF finite-path proof (ot_gf_verify): the
CDC census tagged 492,643 bounded storage->consumer crossings (8 landing response FIFOs x ~61.8k pairs + descriptor 2.6k),
about 985k find_timing_paths calls. Each landing bank decoded its identity check and the seen/received/sticky updates straight
from the FIFO head (8-slot storage mux -> compare -> 256 seen bits), so every one of those registers was a cross-family
consumer of ~200 storage bits. Fix (RTL, ot_hbm_svc_sm8_landing_bank_h): stage A copies the RAW head word into
reader-family registers (loaded under rd_valid through KEPT-qualified slice ANDs; each bit reads only its 8 storage bits);
stage B runs the identity check / seen / received / sticky / completion on those registers. Bank state is held in flat vectors, not reg arrays: an array indexed by the registered h_bank became a yosys $mem, and MEMORY_DFF cloned h_bank into an anonymous flop (gate r1 failed with an OT_GF unapproved crossing). Expected pairs ~8 x 2.3k + 2.6k.

Async clock groups were checked and rejected: in OpenSTA, set_clock_groups -asynchronous removes the set_max_delay /
set_min_delay -ignore_clock_latency pairs ("No paths found", 512/512 pairs in a 833.333/1024 ps test,
scratch/hbm-collect10-svg/stacg2). The reviewed_gray_fifos proof would then fail and the Gray-pointer skew bounds would be
lost. The two families stay asynchronous in the tool's bounded form (only the reviewed FIFO crossings; no other cross-family path).

## Schedule (handed to the die schedule)
+1 stream edge landing -> resident (complete_v), +1 stream edge bad identity -> fault. Both are on the elastic HBM side,
before block_ready. SM-port stream (sm_packet / sm_command / run_done) and go slots unchanged. Ports identical to rel8a/b.

## SAFE-DESIGN checklist
1 pins: K request/response through 2-entry registered skids (hbm family); SM/host faces land in die relays (10-20: pin regs
  only at region crossings / > 405 um); kit pin stage off (it cannot span two families). PASS per rule.
2 reach: tile edge > 405 um; logic stays beside its SRAM column; flow repeaters; gate/route timing decides. Guidance.
3 fanout: r2 census FAIL 1085 drivers > 32. Max 571 is inside the fingerprinted ot_hbm_svc_async_fifo, which cannot be changed.
  Outside it the max is 328 (skid). rel8c removes the head->256-way seen decode cone. WAIVED pending the coordinator census scope
  (owner 10-20 09:35: tile rules are guidance; die results decide).
4 depth: cross-family storage->identity->seen update split into storage->h (8:1 mux only) and h->update. FIXED (+1 edge).
5 storage: 17 SRAM macros (5 cache, 2 descriptor, 8 landing, 2 programme). The flop arrays left are the reviewed CDC FIFO
  storage (8x285 per landing bank, required by the primitive) and the packed136 16x256 ring (r2 2-edge sector pipeline). WAIVED with reason.
6 floorplan: FALLBACK 604.8 x 561.6 (rel8b geometry, enlarged); aspect <= 1.08; fill ~44 % (main) / ~38 % (fallback) of r2 synthesis area. PASS.
7 clock: stream 833.333 / hbm 1024 are independent families (reviewed_gray_fifos). Each has its own CTS root; spread <= 80 ps
  inside a family is judged by the --cts gate; io hold margin 0.03. PASS (gate decides).
8 reset/schedule: control/valid reset only (ot_rst_relay / ot_rst_fanout leaves, one reviewed ot_reset_sync per family);
  static SM side; added cycles listed above. PASS.

## Benches
tb_toksim_smhbm (Verilator 5.050, ot-epyc5 /srv/opentallas-scratch/claude/hbm-collect10-svg): c_ds (DS L14 p96), c_q8 (Qwen INT8
qkv), c_bw (BF16w o). PKHASH vs rel_id/r2: DS 2e16693d97a11ba7, Q8 9546cc94b9874161. Mutants: cm6 (new, landing row bit 0
flipped), cm1 (packed136 record phase), cm3 (go-queue head late).
