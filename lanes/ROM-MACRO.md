# ROM-MACRO lane (started 2026-10-25 19:58 PDT; OWNER 2026-10-25 ~20:40: every ROM is a GENERATED memory macro)
Branch claude/rom-macro-1025 (wt localhost /home/ubuntu/scratch/rom-macro-1025, sparse). Base origin/main 190ebb428.

## STEP 1 REPORT -- how ROMs are built today (origin/main 190ebb428, plans physical/die_plan/*/die_plan.json)
The generator already exists: tools/mem_compiler/rom_gen.py (v1.0, docs/MEMORY_COMPILERS_AND_BIST.md section 2).
- It builds a via-programmed NOR mask ROM: ASAP7 DRC-clean ROM cell 108 x 54 nm, row decoder + WL drivers, column mux, single-ended sense amps, output latch.
- Liberty TT/SS/FF is characterised with every via present, so one view set serves every content.
- `personalise` writes the per-instance `<inst>.viamap.hex` (the via/bit layer), its SHA-256, the CRC-32 BIST signature and the die content signature.
- tests/test_mem_compiler.py proves two contents leave every view byte-identical.
- The v2 aligned views are in physical/asap7_memory_macros_v2/ (build_aligned_v2.py).

| die | content ROMs | how implemented | instances | designs only because of content |
|---|---|---|---|---|
| S81 | weights + cfg ROMs ot_rom_4096x72_m8 (64+8 SECDED) | GENERATED MACRO (bb + LEF/lib v2) in 12 col_h9/h10 types (35-42 per region); ot_s81_cfg7_seq: 7 cfg ROMs per pair; pq calendar ROMs (VIAMAP param) | 7644 placed (434 plan entries) | 0. The col types split into 53 bind variants (type_splits), but from the LK latency param (asb_record lk_asbuilt), not from content. The INSTANCE param of the col frames is unused. Sims load content by hierarchical $readmemh of the via maps (tb_s81_die_layer.sv:508). |
| S81 head | none | -- | -- | 0 |
| QC (Qwen compute = Qwen ROM die) | weights ot_rom_4096x266_m8 | GENERATED MACRO: 10 per A0 tile (rtl/physical/qfd_tile_nk_rp2_45.sv), placed directly in the tile | 36 tiles (35 nk + 1 nl) = 360 | 0. ROM_TILE is only a sim identity assertion; one tile design. BTAB/PROG/CROM are writable SRAM macros, not ROMs. |
| KV/sys | none for weights (embedding comes from HBM) | -- | -- | 0 |
| HBM | none for weights (SRAM programme stores) | -- | -- | 0 |

Function tables synthesised into std-cell logic (Yosys proc_rom / memory_bmux2rom, then memory_map). This is what the new gate catches.
- Every instance has the same content, so none of these forces an extra design.
- The fleet scan (`rom_infer_gate.py --mem-json` over 758 ORFS mem.json files from the last 7 days on epyc1) found 20 FAIL runs, 64 ROM cells >= 1 kbit, 26 smaller INFO decodes and 0 RAM problems.

| table | RTL | shape | where | std-cell area (yosys+abc ASAP7 RVT TT, unplaced) | as generated macro | macro cost |
|---|---|---|---|---|---|---|
| Sinkhorn recip seed c0/c1/c2 | rtl/hdc/v41/ot_hdc_sk_recip_rom.sv | 512x65(69) | HBM hc_root_static tail{0,1}_sk_{step0,steady}, 4 per core = 16 | 229 um2 | 512x65 m8 464 um2, clk->q 315 TT / 254 FF ps | 2.0x area, +1 read cycle |
| Sinkhorn sq | same file | 512x14 | same, 16 | 31 um2 | 512x14 m8 161 um2, 289 ps | 5.2x area, +1 cycle |
| GF(1024) inverse (KP4 FEC) | rtl/dsrom_sys/s81_link/ot_s81_gf1024.svh (gf_inv) | 1024x10 | ot_pdie_serdes, about 55 per serdes; S81 has 14 serdes partitions (agent count, also on HBM) | 113 um2 | 1024x10 m8 213 um2, 319 ps | 1.9x area, +1 cycle |
| exp ln2_nk range table | rtl/hdc/v41x/ot_hdc_v41x_sfu.sv:62 + copies | 256x61(64) | S81 ot_s81sl_vsw (68) / ot_s81sl_eg (16); HBM SU lanes (several hundred, not counted exactly) | n/m | 256x61 m4 249 um2, 296 ps | +1 cycle per exp |
| exp table (rxsf) | dsfd_su_t_rxsf u_exp | 128x49 | S81 dsfd_su_t_rxsf (68) | n/m | 128x49 m2 140 um2, 269 ps | +1 cycle |
| bmux constant | qfd_qc_glue_part (memory_bmux2rom) | 64x32 x2 | QC glue | n/m | 64x32 m2 81 um2 | +1 cycle |
| D2D cal images | rtl/qwen_sys/d2d_static_20261015/qkd_d2d_cal_seq_bc4.sv (packed localparam) | 2 x 32x32 | KV kv3_sys_c.dcal (1) | n/m | 32x32 m2 64 um2 | +1 cycle. Variants differ only by the include. qkd_d2d_cal_seq_ovl_* already use ot_rom_4096x72_m8 VIAMAP, but no bind.f includes them. |

Std-cell vs macro, honestly:
- For CONTENT ROMs (weights), the macro is the only sane form: 123-153 Mb/mm2 at 0.72-0.90 array efficiency, and it is already used.
- For smooth FUNCTION tables the std-cell form is 2-5x smaller than the smallest generated macro, and it is combinational. The macro adds a synchronous read: 290-320 ps clk->q TT, one pipeline stage.
- The bit density of small shapes falls fast: 32x32 is 0.016 Mb/mm2 periphery-bound.

Other step-1 findings:
- Yosys flows: ORFS synth.tcl runs proc_rom and memory_bmux2rom by default, then memory_map flattens any memory <= SYNTH_MEMORY_MAX_BITS. Our kit configs set 131072-262144 (S81) and 16384-33280 (HBM), so nothing stopped inference.
- tools/ref_tile/pre_route_gate.py MEMORY-FF LINT only reports register folding into ROM reads.
- autopilot/OWNERS.tsv listed the generated macros as hard cores to kit, NEEDS-KIT and UNOWNED: ot_rom_4096x72_m8 with 7644 replicas (owner PATH-S81) and ot_sram_1r1w_512x128_m4_r2c2 with 150. Fixed on the branch (state GENERATED, owner ROM-MACRO).

## STEP 2 STATUS -- generator + checks (claude/rom-macro-1025@f2b828e9a)
- Generator: tools/mem_compiler/rom_gen.py. It is content-independent per shape (bit array + decoder + sense/output); content only sets the per-bit drain via (viamap.hex = the via layer: physical row a//mux, column b*mux + a%mux). Shapes are characterised once (LEF + TT/SS/FF Liberty + bb + behavioural). No change was needed.
- NEW `rom_gen.py verify --manifest <prefix>.personalisation.json [--image W]` is the per-content functional/LEC check against the weight file. It checks the via-map SHA, compares read-back on the behavioural model's read path to the image tile by tile, checks that SECDED decodes clean, and checks the BIST CRC and the content signature. PASS on a 5000-word SECDED image; a one-via flip is caught by the hash, and with a forged hash it is caught by word diff + CRC.
- NEW gate tools/mem_compiler/rom_infer_gate.py. It FAILs a netlist with any read-only memory >= 1 kbit (proc_rom / bmux2rom / initialised read-only array); smaller ones are INFO and initialised RAMs are WARN.
  - Inputs: `--mem-json` (ORFS RESULTS_DIR/mem.json, post hoc) or `--rtl ... --top` (Yosys synth -run :fine, the same stage ORFS dumps; needs Yosys >= 0.10, e.g. the openroad/orfs:asap7lock docker).
  - Validated on a synthetic 1024x64 $readmemh table (FAIL) + a 16x8 case decode (INFO).
- Bind audits: content is not in any netlist (the macro bb has no content port or parameter in synthesis; VIAMAP/INSTANCE are sim-only), so there are no tie-offs to declare. The per-bit constants live only in viamap.hex + the personalisation manifest.
- OWNERS fix: tools/autopilot/ownership.py kind 'macro' -> GENERATED.
- Tests: tests/test_rom_macro_gate.py 7 pass; tools/autopilot tests 83 pass (test_draw fails on main too, missing module). In tests/test_mem_compiler.py 22/23 pass; the read_slang test fails locally (yosys 0.9).
- Cost ledger: no row. The content ROMs are already macros, so the swap costs 0 cycles.
- NOT done yet:
  - wiring the gate into the kit flow / autopilot classify (rule 3: flow change -> flow release); proposed in the PLAN-DELTA below;
  - per-die personalisation manifests from the real weight files (needs the S81/QC weight image paths per die; next lane).

## STEP 3 PROPOSAL (PLAN-DELTA, needs COORD/OWNER)
- D-ROM-0 (no plan change): adopt the GENERATED state for the generated macros in OWNERS; gate available.
- D-ROM-1 (flow, at the next flow tag after the canary): run rom_infer_gate on every kit mem.json. It is a WARN until D-ROM-2/3 are decided, then a FAIL.
- D-ROM-2 (OWNER?): function tables. Recommendation (a): treat fixed math function tables as logic. They are identical in every instance, generated by a checked-in script, and verified by LEC against the generator. Allow them through a declared list in the gate. 8 tables, 0 cycles.
  Alternative (b): move them to generated macros, at +1 read cycle per lookup on the exp / Sinkhorn / KP4 paths and 2-5x area. This touches S81 ot_s81sl_vsw / eg, dsfd_su_t_rxsf, ot_pdie_serdes, HBM sk / SU lanes and QC glue: PATH types, so a PATH-lead re-plan.
- D-ROM-3: KV dcal. Swap the packed-localparam images for the ROM macro (the ovl template exists). This merges the variants that differ only by the include, which TYPE-REDUCE-2 wants anyway.
- No plan delta is needed for the S81 or QC weight ROMs: they are already generated macros, one view per shape.
2026-10-25 20:25 PDT ROM-MACRO: step 1 + step 2 core done, branch claude/rom-macro-1025@f2b828e9a pushed. Weight ROMs on S81 (7644 x ot_rom_4096x72_m8) and QC (360 x ot_rom_4096x266_m8) are already generated macros; designs only because of content = 0. Gate scan: 20/758 runs FAIL on synthesised function tables (8 distinct tables). OWNER? D-ROM-2 (a) vs (b).
2026-10-25 20:25 PDT ROM-MACRO: rom_infer_gate --rtl on the real rtl/hdc/v41/ot_hdc_sk_recip_rom.sv (orfs:asap7lock yosys 0.67): FAIL 512x65 proc_rom table, as expected.
## PARKED 2026-10-25 20:25 PDT
Branch claude/rom-macro-1025@f2b828e9a pushed, READY in COORD-REVIEW-QUEUE. Worktree localhost /home/ubuntu/scratch/rom-macro-1025 (sparse; remove after merge). No live jobs. Scan artefacts: epyc1:/tmp/romgate_t/scan.json (758 mem.json verdicts), scan.txt.
NEXT:
(1) COORD: merge READY; D-ROM-0 takes effect at the next autopilot tick (OWNERS GENERATED rows).
(2) OWNER: decide D-ROM-2 (a) declared function tables stay logic vs (b) macro, +1 cycle; then D-ROM-1 wires the gate (FAIL) into the kit flow at a flow tag.
(3) KV lead: D-ROM-3 dcal images -> a small generated shape (32x32 m2, 64 um2; the ovl variants use 4096x72, which is oversized).
(4) Content tools: the per-die viamap writers (tools/s81_ftok/hcx_rank_images.py, dsrom_markov_*, engram_*, ...) write via maps ad hoc with no personalisation manifest. Route them through rom_gen.py personalise so 'rom_gen.py verify' runs per content per die.
2026-10-25 20:54 PDT ROM-MACRO follow-up (OWNER D-ROM-2 = (a); COORD approved D-ROM-0/1/3):
- (1) DONE claude/rom-macro-1025@211186de1: declared-logic allowlist tools/mem_compiler/rom_declared_logic.json (7 entries: module + table + SHA-256 of the Yosys INIT bit string + shape + src + reason): sk_recip_seed 512x65, sk_sq_seed 512x14, exp_ln2_nk 256x61, exp_s_rxsf 128x49, kp4_gf1024_inv 1024x10, qc_d2d_cal_tx / qc_d2d_cal_rx 64x32. Match = shape + content hash (+ src file when the cell has one); anything else >= 1 kbit FAILs; --no-allowlist = raw check. rom_gen.py verify --macro for shapes outside physical/. Tests 9 pass.
- Rescan (epyc1 .../rom-macro-1025/gate/scan2.json, 758 mem.json): 754 PASS, 4 runs deleted since the first scan (were PASS), 0 FAIL. The 20 former FAIL runs are all declared tables (exp_ln2_nk 9 runs, sk seeds 6, qc_d2d_cal 2, exp_s_rxsf 2, kp4 1). REAL FINDINGS: none -> nothing to route.
- NOTE for COORD: the 'QC 64x32 constant table' is the QC-side D2D calendar TX/RX image (ot_qwen_d2d_cal_seq.sv:119, glue u_cseq.u_seq.u_seq), a compiled schedule, not a math function. It is declared per owner D-ROM-2; a recompiled calendar changes its hash and the gate will FAIL until re-declared (or the QC side gets the D-ROM-3b treatment).
- (2) D-ROM-3: KV images are DEAD on the KV die (boot target 11 loads them; bc4 suppresses the inner init writes) -> no macro; variants also differ by START/PERIOD/SEG2. Bench 1.5M edges 0 mismatch. Proposal D-ROM-3b in lanes/PLAN-DELTA.md (KV batch). Scratch: epyc1 /srv/opentallas-scratch2/claude/rom-macro-1025/dcal (tb.sv, noimg.sv, b95.sh BMC), localhost /home/ubuntu/scratch/rom-macro-dcal (32x32 m2 shape + manifests, verify PASS).
- (3) D-ROM-1: claude/rom-gate-flow-1025@0b6be8e6d (stacked): pre_route_gate.py runs rom_infer_gate on $B/mem.json -> GATE_ROMGATE, check_rom_gate FAIL on undeclared ROM, INFO otherwise; tests/test_rom_gate_flow.py 2 pass. For the next flow tag via FLOW-CANARY (0 FAIL on the current fleet, so it refuses no current kit).
2026-10-25 21:09 PDT ROM-MACRO: D-ROM-3 BMC PASS: yosys 0.67 miter gold(bc4, main images) vs gate(images=0), reset held edges 1-2, all inputs free, 95 edges (covers the full 66-write init stream + the reset landing): "SAT proof finished - no model found: SUCCESS" (1430 s, 27 GB, epyc1 .../rom-macro-1025/dcal/bmc95.log). Together with the 1.5M-edge random bench (reloads included): the KV dcal images never reach an output.
## PARKED 2026-10-25 21:09 PDT
Branches: claude/rom-macro-1025@211186de1 (READY, allowlist), claude/rom-gate-flow-1025@0b6be8e6d (READY-AT-FLOW-TAG, D-ROM-1 hook). Worktree localhost /home/ubuntu/scratch/rom-macro-1025 (sparse; remove after merge). No live jobs. Scratch: epyc1 /srv/opentallas-scratch2/claude/rom-macro-1025/{gate,dcal}, localhost /home/ubuntu/scratch/rom-macro-dcal.
NEXT: (1) COORD merge allowlist READY; FLOW-CANARY carries the gate hook in the next flow tag. (2) PATH-KV/TYPE-REDUCE-2 pick D-ROM-3b (drop dead dcal images; START/PERIOD/SEG to a 64x32 generated ROM or boot words) -> one dcal design. (3) COORD: QC-side calendar images are declared logic per D-ROM-2 but are compiled schedule content; consider D-ROM-3b for QC too. (4) content tools -> rom_gen personalise manifests (from step 1 NEXT 4).
