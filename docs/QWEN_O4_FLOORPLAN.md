# Qwen3-8B O4 floorplan and physical composition (W5, rungs 1-5)

Workstream W5 of [the integrated physical plan](INTEGRATED_PHYSICAL_PLAN.md) for the two-reticle O4 package (TP-2, signed INT8 weights with a BF16 row scale, 6,144 lane groups a die, 4 HBM3E stacks a die). It covers both the ROM die and the HBM-weight comparator die. Every figure here comes from a source-pinned record; a figure without a record is labelled as a reservation.

**Clock.** Records use the budget clock of `results/arch/qwen3_budget.json`: 1.09864 GHz, i.e. 0.910216 ns, with 60 ps setup uncertainty. Earlier Qwen cuts ran at 0.92 ns, which is 1.07% slower. A 0.92 ns closure does not validate the model clock. The route campaign repeats two cuts at 0.92 ns, only to measure that sensitivity.

**Technology.** Geometry uses the predictive ASAP7 macro views in `physical/asap7_memory_macros` and pre-layout ASAP7 cell areas. The N6 area ledger is quoted, never substituted.

**Status: PARTIAL.** Work stopped at the root halt on 2026-09-29. The facts established so far are summarised below. The full per-component figures are in `/tmp/claude-1000/handoff_w5.md` and in the records named here.

## Rung 1: inventory = RTL

Record: `results/floorplan/qwen_o4_die_inventory.json`, from `tools/qwen_o4_die_inventory.py`. Yosys elaborates the die core at G = 8, 16 and 32, fits the counts, checks them against G = 64 held out, and evaluates them at G = 6144.

- **Datapath units.** The die RTL (`ot_hdc_core_vector_weight`, G = 6144) instantiates 98,304 `ot_hdc_bmul`, 98,304 `ot_hdc_fadd`, 98,312 `ot_hdc_qadd` and 98,304 `ot_hdc_fmul`.
- **Post-scale multipliers.** Only 1,536 of the fmuls are reachable: result-port groups 0..95 × 16 lanes, since the smallest split is S = 64.
  - The instantiated fmuls cost 50.6 mm² of pre-layout area; the reachable ones cost 0.79 mm².
  - The split-tree hold and output registers total 163.6 Mbit instantiated (47.7 mm²), of which 13.8 Mbit (4.0 mm²) is reachable.
- **Ledger rows without RTL.** These are gaps, not substitutions:
  - lane copies (m = 5);
  - an SW = 1,024 stream unit;
  - the KV/HBM service;
  - the HBM and UCIe PHYs;
  - the drafter;
  - INT8 embedding;
  - macro memories;
  - a group-offset slice of the monolithic matvec.

## Rung 2: integer ROM placement

Record: `results/floorplan/qwen_o4_rom_placement.json`.

- **Code ROM.** One per group-pair column; there are 3,072 columns.
  - Each column holds 44,480 words: 38,880 target and 5,600 drafter, with the drafter fc at S = 4096.
  - That fills 11 banks of `ot_rom_4096x266_m8`, for 33,792 macros and 259.0 mm².
  - The 8192x266 view (18,432 macros, 268.9 mm²) is rejected. Its 787 ps clk-to-q leaves 35 ps at 0.910 ns with 60 ps uncertainty.
- **Scale ROM.** 1,536 macros (11.8 mm²): each of the 96 port groups holds a whole-image replica, which is what the current RTL requires. An exact per-port subset would need 101 macros, but it needs a scale-address remap in the RTL.
- **Embedding (half vocabulary).** 2,376 macros.
- **Constants.** 133 macros of 4096x72.
- **Total.** 37,837 macros, 289.3 mm², against the N6 ledger's 253.4 mm².

## Rung 3: macro-packed floorplans

Record: `results/floorplan/qwen_o4/floorplan.json`. The DEFs are gzipped. **The tile logic area is an estimate**, because the cluster synthesis was stopped.

- **ROM die.** The die is 31.8 × 25.63 mm.
  - It carries four HBM3E PHY+controller abstracts (two on the north edge, two on the south), a west UCIe reservation and a central spine.
  - The array element is 1,536 full-goal neighbourhoods of 4 groups × 16 lanes: 22 code macros and 4 KV-slice SRAMs each.
  - **The die does not fit at the estimated logic area:**
    - as instantiated: capacity 1,225 of the 1,512 needed array tiles;
    - pruned to reachable fmuls: 1,470 of 1,512;
    - with the m = 5 copies: 882 of 1,512.
  - Every placement checks legal (lattice, halo, no overlap).
- **Wire budget.** Reach per register at 0.910 ns is 1,101.7 µm, from the routed express-link fit of 0.60 ps/µm plus 189.5 ps.
  - Distance adds about 9,200 to 10,200 cycles per token over what the RTL provides.
  - The largest terms are:
    - the x operand from the VM: 25 stages instead of 1, 5,208 cycles a token;
    - the TP exchange crossing to the UCIe edge: 1,898 cycles;
    - tree compaction for o and down: 1,440 cycles.
  - A centralised KV ring would need 4.4× the bisection capacity, so the ring slice lives in each tile.
- **HBM die.** A frame only, per the user rule of 2026-09-29. W9 owns the SM/Tensor-Core array.
  - The frame holds 4 stacks on 48 mm of shoreline and service bands of 40.1 mm², leaving 688.4 mm² for the compute array.
  - At batch 1 the HBM controller and PHY draw 293.5 W a die, 7.3 W/mm² over the 40 mm² PHY area. The die average is 0.57 W/mm².

## Rung 4: clusters (partial)

Neither cut closed or completed. Details are in `results/physical_hdc/asap7/qwen_o4_w5/README.md`.

- **ROM/MAC neighbourhood.** `rtl/physical/ot_qwen_o4_g4_rommac.sv` is cycle-identical to the flat-ROM matvec (`results/rtl/qwen_o4_g4_rommac_equivalence.json`, PASS), with zero added cycles.
  - The -1,218 ps shard path had no ROM capture register. The adopted matvec already captures ROM data in `mq_wrom` (MEM_PIPE), so the fix costs no cycle.
  - The route was stopped during synthesis.
- **8-bank VM.** Its route failed twice:
  - with ideal I/O, CTS hold repair ran out of buffers;
  - with latency-consistent I/O, setup WNS after CTS was -699 ps, on the combinational four-client conflict check driving 32 macro r_ce_in pins.

## Rung 5

Not run. `rtl/physical/ot_qwen_o4_die_row.sv` (14 tile abstracts with issue/x pipelines and a registered tree) and its placement are ready; they need the tile abstract.

