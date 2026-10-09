# MTP status matrix: DS-V4.1 ROM and HBM accelerator (stream mtp-lead, 2026-10-09 PT)

Owner: Claude (mtp-lead) owns MTP design end to end from 2026-10-09. Codex does routine route-and-wait only.
Sources: the five Claude MTP stream logs, MTP_AUDIT.md, REVIEW_20261008/20261009 (MR-*, MD-*, MX-1, V22/V36, J9, AB3/AC1/KV9),
the review_queue MTP files, the closure-loop job table (118 mtp*/wfc*/markov*/md6* jobs), and the records named per row.
Acceptance line (owner option B): TT setup >= 0, FF hold >= 0, DRC 0 at 833.333 ps with 60/25 ps uncertainty. SS is a sensitivity.

Legend. **Rev** = design reviewed (verdict id). **RTL/bench** = RTL plus an exact bench with a failing negative. **Phys** = best
closure-loop verdict. **Die** = instantiated in a die recipe that is ADOPTED (variant-only placements are listed as such).
**Token path** = charged in the token-path view (results/arch/token_path_20261008/*_mtp.json).

## 1. Headline

| | DS ROM (S81, 1,792 pairs) | HBM accelerator (r25, TP-96) |
|---|---|---|
| Published MTP rate | 4,351.6 tok/s HALF_PHL (composed, `physical_qualified=false`) | 3,700.3 tok/s (priced upper bound) |
| MTP blocks closed (live line) | mtp_seq, wfc_lnk, HARD wfc_tok, WFC STG tokpipe, mtp_commit | ctl_f2, accept_a0, argmax_f1, union_f3, scratch_c2, topk_f384, dswin_rd, mtp_commit, native emit queue |
| MTP blocks failing / open | WFC SOURCE (HARD partner routing), wfc_vmx (TT -19.2), P2 path (first route queued), Markov PINREG1 (ECO), MD6 lookup (electrical), seed projection / head340 / seq native binding (implementation only) | hfd_mtp die master (hold flood; x-stop + 2 HM siblings live), fence (TT -63; banked -cx live), dskv_wb_spec (synth fixed, 2 routes live), accept18 (DRC 1, fixed pins live), CP-south native master, transaction join |
| On an ADOPTED die | **No.** WFC/mtp_seq exist only as generator options (`--wfc-hard`, `--mtp-seq`, default off) | **No.** ADOPTED = R25 (no MTP master); r25m / r25i / r25imw carry an `mtp` slot only as variants |
| In the token path | Composed view only: WFC and accept dashed (closed, not integrated); DSpark stages hatched; mtp_seq / shims / P2 / Markov cycles NOT charged (step.json unpublished) | Composed view only: DSpark control dashed; hfd_mtp, fence, spec-state cycles NOT charged |
| Exactness (multi-step) | Reduced-core spec==greedy 7 runs PASS; 2-stage WFC wavefront PASS; deep order (MR-5) campaigns 14/19 PASS with ring DYN; rollback bench PASS | Connected closed control top PASS (forced / w16 / dspark) + 6 mutants FAIL; rollback bench PASS; WR 256 re-bench rerunning |

## 2. DS ROM MTP elements

| Element | Rev | RTL / bench | Phys (best live verdict) | Failing because / next | Die | Token path |
|---|---|---|---|---|---|---|
| dsfd_mtp_seq (ot_dsrom_mtp_seq: accept NSLOT 8 + draft chain + hold/release) | R1 APPROVE (adopt c) | Y: 23 benches (mtp-rom), NW 21 | **CLOSED** c67a71fe5 SS +52.37 / FF +5.76; b SS +63.55 / FF +18.83 | — | `--mtp-seq` option only; die buses re-bound to the actual wrapper ports today (MTP_SEQ_BUSES 514/650/48/36, was 64/128/128/576) | not charged (8 fwd / 8 seed / 8 per head round trip / ~52 release) |
| dsrom_mtp_seq_native_binding | Codex record | component only | none (no own block) | the die bus table did not describe the NW 21 wrapper → fixed in tools/dsrom_s81_fulldie.py (this stream); full seed/draft/verify/rollback identity composition still open | — | — |
| WFC SOURCE (ot_rom_pkg_ctrl_wfc src) | closed r24 (SS era); tokpipe never reviewed (C1); HARD partner KV9/AC1 APPROVE | Y: matched SOURCE all-10 gate PASS (8 pos / 2 mutants) 8dbc959b2 | tokpipe 9f7a7f35e TT +102.8 / FF -69.3 (NEEDS_RTL); **HARD partner 5b11f631f RUNNING** (EPYC3 route) | FF -69.3 on the old SOURCE = not repaired by rule; partner route pending | `--wfc-hard` option only | WFC charge 49 + 13 hop priced but lever not enabled |
| WFC STG (tokpipe) | Z-2/AB4 routine | Y | **CLOSED** 9f7a7f35e TT +141.65 / FF +22.80 / DRC 0 (after same-job hold ECO; SS -165.8) — published today after the record push was unblocked (3 files > 100 MB moved out of the record, hashes in heavy_manifest.json) | — | option only | as above |
| dsfd_wfc_tok HARD (e829cb457) | AB3 winner | Y: 128-entry gate + no-epoch mutant | **CLOSED** TT +8.85 / FF +22.26 / DRC 0 | adoption gated on the SOURCE partner (AA-a) | option only | +3 edges recorded |
| dsfd_wfc_tok r1/r2/r3/abutted (12 jobs: 3 FLOORPLAN_MARGIN util 62 %, 3 NEEDS_RTL SS -478, 4 harness/INVALID) | retired (I13/AB3) | — | superseded by HARD | no action (evidence kept) | — | — |
| dsfd_wfc_lnk | R4 | Y | **CLOSED** b-0cd6caa1b TT +7.75 / FF +18.60 | 7 other variants NEEDS_RTL (SS-era or LVT siblings) are superseded | option only | +3/+3 per hop recorded |
| dsfd_wfc_vmx | DR6 ~240², V14/B3 READPIPE2 | Y (o248 harness fixed B2) | o292 prd -cl r2 / intra-r2 TT -19.2 / FF -4.72 (NEEDS_RTL); lvt-r2 RUNNING; **READPIPE2 -cx intake queued today** (was approved B3, never submitted) | s2f read pointer → 46-word staging write select, 19 levels (rp→stg); READPIPE2 removes the f_vr→vm_rq decode; 9 FLOORPLAN_MARGIN jobs are the old 216² outline (util 70–85 %) = superseded by DR6 | option only | 15 start / 79 done cycles recorded |
| dsfd_drf_fan | R6 REJECT | Y | NEEDS_RTL SS -168..-178 | retired by MD-2 P2 | — | — |
| P2 transport, general 4-bank (ot_mtp_p2_ordered_rows_general4bank) | B1 REJECT topology | Y | -cl hm0 TT -166.78 / FF -39.81; 2 EARLY_FAIL_HOLD (buffer cap) | out_identity → acc_data 19 levels; topology retired, no successor | — | — |
| **P2 selected path** (PRIMARY_SHARED1 9-SRAM transport + 3-SRAM 16-lane A-prefix + native publisher) | R7/V22 APPROVE-WITH-CONDITIONS; reviewed for route today | Y: path gate PASS 5,467 cyc (1,280 values, 240→80 flits), copy-first signed-zero mutant FAIL | **first routes queued today**: mtp-p2-path-{a 500×420, b 560×460}-80ae7d954 (HM 0, 12 SRAMs on a grid) | released aligned W2 contribution fixture + primary shared-LAST consumer still open | MD-2 draft dies have no recipe | +0.2 µs/step approved, not charged |
| Draft dies + DSpark stages (MD-2: 40 dies = 5 rows × 4 ranks × A/B) | MD-2 APPROVE | element RTL composed (draft.json, 3 blocks 83.99 µs); A/B ROM images NOT regenerated | no die-level route | no draft-die recipe in tools/dsrom_s81_fulldie.py; head dies keep 12 × 85 bundles | **No** | composed (hatched) |
| dsrom_mtp_seed_projection_full15360 (5120×15360 FP8 + BF16 norm) | Codex record | QS5f K2304 two-row native PASS (285 cyc), K15360 two-row 1,688 cyc; full 15360 aligned segmentation in progress | none | native phase K13 cannot encode 15,360: segmentation + ordered reduction not finished | — | in draft term |
| Markov head (MD-6; released K = 256, not 32) | R8/V13 APPROVE-WITH-CONDITIONS | Y: PINREG1 exact + separate-add mutant FAIL | PINREG1 38f22c6d8 TT -28.62 / FF -66.87 → B4 re-judge TT +21.00, hold ECO live (PVE1) + `-kr` re-run READY (EPYC4); baseline markov256 EARLY_FAIL_HOLD; PINREG2 retired | output-port hold against the generic 250 ps budget (re-judged), FF via ECO | head dies: dsrom_mtp_head_full340_A (340 A engines / 680 ROMs) inventory only | transfer ratio only |
| MD6 released-embedding lookup pair (ot_dsrom_markov_embed_localcapture_pair) | I16/Z7/S5 | Y: 160 released beats + mutant | ctsphase TT +36.94 / FF +0.56 / DRC 0 but **30 output-slew violations** (captured_data, up to 483 ps vs 250); pgfix FF -8.63; loadfix ODB-0370 (dont_touch capture flop at CTS); f59 crash | redesign = output landing flops at the pins: outputlanding 24affff33 RUNNING (EPYC1) | — | — |
| Accept (ROM instance) | inside mtp_seq | Y | via mtp_seq | — | — | — |
| ot_mtp_commit (commit pointer n = q + 2 + a) | B1 APPROVE | Y (rollback bench) | **CLOSED** a SS +80.53 / b SS +79.12 | — | none | 1 cycle |
| Rollback rings: window ring 256 (MR-1), compressor record ring (MR-2), Engram idwin rewind (MR-3) | APPROVED | Y: rollback bench (rings) + ISA ring-8 (MR-5) | idwin in engram stream; window/record rings are HBM storage | ROM window prefetch 256 PASS in bench (prefetch r256 c1/c8) | — | +2.79 MB/user HBM, 0 cycles |
| ot_mtp_hist_ring (+ pipelined _p) | B2 REJECT (no consumer) | Y | hist_ring-b TT +10.92, -p TT +129.06 CLOSED | not integrated by decision | — | — |
| **Ring DYN (V36/J9)**: DYN25/26 for one-position ring-8 cores | J9: program first; decided today | Y: campaigns 14/19 PASS, 15/20 protocol FAIL (Codex, 3dea693b1); independent rerun running | rides the sequencer (no own block) | **Decision (mtp-lead):** the program cannot express it: a static instruction field cannot carry pos mod 8 and no NSLOT=1 DYN entry gives {pos[2:0],2'b00} / {pos[2:1],7'b0} (DYN18 is the ring-2 form); 8 program copies would cost ~8× instruction memory. Keep the RTL (the existing NSLOT>1 DYN25/26 logic enabled for NSLOT=1, 5 bits/slot, 0 cycles), default 1. Merged on claude/mtp-lead-20261009. Production full-shape compiler (ShapeLayout ratio-2 / two-record slots) still does not emit ring-8: OPEN | core copies under rtl/dsrom_sys/s81_capture_parent and rtl/w17_runtime/.../fastpp_pc21 not patched (their programs do not use ring-8 yet) | 0 |

## 3. HBM accelerator MTP elements

| Element | Rev | RTL / bench | Phys (best live verdict) | Failing because / next | Die | Token path |
|---|---|---|---|---|---|---|
| **hfd_mtp die master** (dspark_top_m: ctl FAST + accept + spec_state_f + argmax + union + topk, behind pin flops / skids) | MH, M1, MD-7 | Y: round-1 golden traces PASS (WR = W+8); connected closed top PASS; **WR 256 round 2 never finished (killed at the limit) → rerun today** | A (1c33f2dc9) and A-LVT: calibrate stuck 8 h in CTS hold repair (WNS frozen -15.0 / -12.5 at input pin flops i_rv_vals / i_lg_bias) → **cancelled today**; X 1c33/021c EARLY_FAIL_HOLD (-9.7); **x-stop 4386513e4 RUNNING (PVE1, MD-7 slot 466.56×200.88)**; **HM 0 / HM 10 siblings queued today** (EPYC4 calibrate) | hold margin 25 ps flood on die-input pin flops (real hold ≈ +10 ps); acceptance is FF >= 0 | r25m / r25i variants only (`hfd_mtp_native(_stop)` slot); ADOPTED R25 has none | not charged |
| MR-8 parameters | MR-8 | verified in 1c33f2dc9 / 021c82802 / 4386513e4: WR 256, RLOG 16'h0111, SR 10, CKMAX 2^20 | — | — | — | — |
| MD-7 ECO pins on closed views (cmdproc_s t/f_mtp 320/126, su_red 657, router 78/8, coll 64/64) | MD-7 APPROVE | no RTL ports in any wrapper | not done | owners must add ports, then route_view.sh r25m | — | — |
| spec_state (f3, inside hfd_mtp) | MX-1 APPROVE drained reset | Y: lockstep 64/64 drained, TOKEN_EDGE_FIX 128/128 | inside hfd_mtp | in-protocol exact (reset never mid-run); TOKEN_EDGE_FIX module kept as the unconditional alternative | — | +5 answer cycles |
| ot_dshbm_dspark_ctl (ctl_f2) | M | Y | **CLOSED** TT +28.49 / FF +10.88 | — | inside hfd_mtp | — |
| accept (accept_a0) | M | Y | **CLOSED** TT +113.91 / FF +21.46 | — | inside hfd_mtp | — |
| hgi_mtp_accept18 (generic-die full 18-bit endpoint) | HGI-1 item 4 | Y: positive + width / bonus mutants | 4bffda75f pd48 TT +226.06 / FF +19.78 / **DRC 1**; pd55 TT +229.99 / FF +9.55 / **DRC 1** | both DRC 1 = M5 Metal Spacing rst_n vs clk (adjacent pins in one region) → **pin-separated cfgs queued today** (pinsep-pd48/pd55-f63ddf415) | — | — |
| argmax_f1 | M | Y | **CLOSED** SS +65.99 / FF +17.62 | — | inside | +1 cycle/row |
| union_f3 | M | Y | **CLOSED** SS +13.30 / FF +20.87 | — | inside | +1 |
| scratch_c2 | M | Y | **CLOSED** 6724e9d82 SS +69.04 / FF +12.96 (c4a73b788 FLOORPLAN_MARGIN macro_edge superseded) | — | — | +1 |
| router topK (topk_f384) | MH-3 | Y | **CLOSED** TT +18.26 / FF +17.31 (LVT TT +5.42) | — | inside (X selects on the die router) | +1 |
| RF visibility fence | M3 / Z3 / E5 | Y: 4,096 exact + mutants | fence_p SS -234; p2 TT -85 / -70; p2r2 TT -63.3 (host_wr_ready → 33 skid enables, 13 levels: an unregistered ready fanning out); **banked -cx d7af9e956 intake queued today (RUNNING EPYC4)** — approved E5, never submitted | — | — | +2 (fence_p) / 0 (-cx) |
| ot_hbm_accel_dskv_wb_spec (MR-7 writer, WIN_SLOTS 256, MR-6 shadow lock) | MR-7 / B1 | Y: rollback bench | a: yosys exit 1; b: yosys hung 4.75 h at 14 GB → **cancelled; shadow rewritten as 8 slot rows with constant part selects (bit-identical, yosys 1:27); rollback bench 33/33 PASS on it; 2 routes queued** (mtprb-dskvwb_spec-{a,b}-4584c6b12) | submit lint WARN: outputs combinational (34 levels) and pos → ownership divide 62 levels: registered boundary + split S_MAP (+1 cycle/row) is the next variant if these fail | no consumer (hfd_kvwb_native not in RTL) | — |
| ot_hbm_accel_dswin_rd | MR-7 | Y | **CLOSED** a SS +265.24, b SS +280.05 | — | no consumer yet | — |
| native MTP emit queue (ot_hbm_native_mtp_emit_queue) | V23 | Y | **CLOSED** mtpemitq_rb TT +20.99 / FF +7.23 (pi-mtpemitq TT -370 superseded) | — | CP-south (pending) | — |
| native MTP transaction join | V24 (reject the external epoch increment) | Y component + mutant | none | waits for the fresh CP-south native master (hfd_cmdproc_s_mtp_native_am, 197-bit facade): no closure-loop job exists for it | — | — |
| CP-south native MTP master + 197-bit CP contract (review_hbm_token_path) | V23/V24 | gates on branch | not in the loop | needs intake | — | — |

## 4. Exactness

| Item | State |
|---|---|
| Campaign 14 (L14 ratio-2 compressor + Engram, deep order, position-1 divergence) | Root cause proved (address fault: NSLOT=1 cleared DYN25/26; element 28,320 written for 28,384; all 64 values bit-exact). Codex repair: 14 PASS 428,093 cyc, 15 protocol FAIL, 19 PASS 237,482, 20 protocol FAIL, same source 3dea693b1. **Verification:** source diff read (3 lines: DYN25/26 under `NSLOT>1 || ROLLBACK_RING_DYN`), receipts read, merged; independent rerun of all four plus the default-parameter positive, fixtures regenerated from the reduced checkpoint, running on EPYC4 (results/rtl/mtp_lead_20261009/campaigns when terminal). |
| MR-5 deep order (squashed successors in flight) | ISA: ring-8 full-γ PASS, ring-2 mutant FAIL (77cc3afae). RTL: campaigns 14 and 19 ARE the deep order on the 2-stage reduced vehicle with the closed WFC: PASS. |
| Multi-step rollback bench, both designs | Re-run today on the merged tree + the rewritten dskv_wb_spec: 33/33 OK (ROM + HBM good PASS at W128/W8 incl. spec_state_f; every mutant FAIL; prefetch r256 PASS, as-built 128 FAIL). results/rtl/mtp_lead_20261009/rollback_rerun/record.json |
| ROM multi-step spec == greedy (reduced as-built core) | 7 runs PASS, restore mutant detected; the original gate stays FAILED-preserved because the accept-extra control is inert on spread6 (accepts 5,5). |
| HBM connected closed control top | forced 598,611 / forced_w16 710,683 / dspark 1,028,459 cycles PASS; 6 mutants FAIL. hfd_mtp WR 256 round 2: rerunning. |
| τ | 4.159 software (GPU) blend; not an RTL quantity. |
| Not proven | native production full-shape program with ring-8 (ShapeLayout), released-weight multi-step on the full-shape ROM, the HBM MTP on the die (no die bench), the P2 path on released contributions. |

## 5. Failure classification (mtp*/wfc*/markov*/md6* NEEDS_RTL, FLOORPLAN_MARGIN and EARLY_FAIL jobs; counts approximate per class)

| Root cause | Jobs | Status |
|---|---|---|
| Superseded topology / outline (drf_fan ×3, general4bank ×1, wfc_tok r1/r2/abutted ×6, vmx 216² ×9, wfc_lnk older ×7, hist_ring-a, pi-mtpemitq ×2, fence_p SS-era, scratch c4a73) | 31 | no action; closed or retired successors exist |
| Harness rc=1 (tokpipe 1718d ×2, wfc_tok r3 ×2, vmx o248 ×3, vmx prd non-r2 ×2) | 9 | fixed (B2 aea8f3f06 / r2 traces); evidence only |
| Logic depth / fanout (vmx prd r2 rp→stg 19 lv; fence p2r2 ready fanout 13 lv; P2 cl 19 lv) | 4 | READPIPE2 -cx + lvt-r2 live; banked fence -cx live; P2 retired → selected path routed |
| Output electrical (MD6 slew ×2) | 2 | outputlanding live |
| Output-port hold vs generic budget (PINREG1) | 1 | re-judged TT +21; ECO live |
| Hold flood at HM 25 (hfd_mtp A/X, markov256) | 5 | HM 0/10 siblings queued (x-stop) |
| Pin-pair DRC (accept18 ×2) | 2 | pin-separated cfgs queued |
| Old SOURCE FF -69 | 1 | not repaired by rule; HARD partner routing |
| Synthesis hang (dskv_wb_spec ×2) | 2 | RTL rewrite + 2 routes queued |
