# Qwen TP8 track-A ROM die: die iterations

Stream `qwen-tp8`, die agent `[qwen-tp8/die]`. Branch `claude/el1011-qwen-tp8-die`. Log: `/home/ubuntu/claude-takeover-20261007/el1011-qwen-tp8.log`.

- **Spec:** `results/arch/qwen_tp8_1012/SPEC.md`, sections 1, 2, 3 and 5.
- **Generator:** `tools/qwen_rom_fulldie_b3r2.py --recipe tp8a`. The recipe is defined in `tools/die_top_lint.py` as `QWEN_TP8A`: it is r22ko4 plus a `tp8` config.
- **Contract:** `results/arch/hier_contract_1012/qwen_rom_tp8.json` (die `qwen_rom_tp8`, v1). It is derived by `tools/hier_contract/derive_tp8.py` from the qwen_rom v5 templates and the tp8a case.

## Floorplan (tp8a)

| Item | Value |
|---|---|
| Die | 25,039.6 × 23,004.0 µm (576.0 mm²) |
| Tiles | 768 `qfd_tile_nk` (TP4 master, unchanged), 64 columns × 12 rows; 768 `qfd_cst`, 64 heads |
| Bands | 3 × 4 rows: `port_tiles_{0,1,2}` + `_f1`, `band_lanes` ×3, `res_ser` ×3, `tt_up4` + 3 × `tt_up4_g` |
| Routing channels | 518.4 µm row gap between tile rows; link channels before rows 2 and 10 |
| Spine | TP4 columns at 777.6 µm (closed d2d_rom / su64 / slab views fit), VM square, ctlm, seq_su |
| IO band (N) | `io_collective` 3,453.6 × 1,563.8 (1.5× TP4), `io_xfifo` 700 µm, `io_ucie`, 3 × `io_serdes` (`io_serdes` E of UCIe; `io_serdes_1` / `_2` W of the collective, MY) |
| S edge | `ot_qkvd_ucie_x64_phy` + `qfd_d2d_rom` to the paired KV die (unchanged) |
| Slot share / channels | 55.8 % / 44.2 % (rule: ≤ 60 % / ≥ 35 %) |
| Die-top relays | 9,822, including 2,024 tree-leg pads |

**Tree balance.** `tools/qwen_die_seam/tree_pads.py` runs the array bench's arrival model on the unpadded netlist: 704 of 720 nodes were misaligned. The resulting pads are in `results/arch/hier_contract_1012/qwen_rom_tp8_tree_pads.json`. The generator places them as relays at the sink end of each early leg. As placed, 0 of 720 nodes are misaligned.

**Open.** `die_audit` counts 1,232 nets over the 504 µm reach:

- 1,226 are tree-pad chain hops (500 to 1,250 µm). The corridors near the nodes are full, so the pads land in the row gaps, up to 880 µm from the W-face tree pins.
- 6 are hops on the W-SerDes words, which cross the collective.

The v2 fix: place pads on the leg's own row-gap crossing (between two frames that are within reach), or reserve corridor pad sites before the bulk relays are placed. Route the W-SerDes words S of the collective.

## Seam benches (agidock128 `/srv/opentallas-scratch/claude/qwen-tp8-seam`)

These run on the tp8a contract and netlist with `QS_CONTRACT=…/qwen_rom_tp8.json` and `QS_GEN_ARGS=--tile-subset`. The tile subset maps the 768 die tiles onto the first 768 tile streams of the L3 TP4 recording.

| Bench | Verdict |
|---|---|
| `array_placed` (corridor + tree, **no `--deskew`**) | **PASS**: 0 / 720 misaligned nodes, 0 pad relays needed |
| `p2p` | **PASS** |
| `array_mut_drop_tree` (drop `n_tree_0_1_0b` relay 1) | FAIL, as required |
| `credit` (15 lanes: 8 cbuf, 3 rs, collective) | **PASS**; mutant `cr:+1` FAILs as required |

## Iterations

| It | Source | Views | Run | GRT overflow | TT setup | FF hold (after pads) | Clock plan | State |
|---|---|---|---|---|---|---|---|---|
| it1 | tp8a (see `it1.log`) | Closed views through `die_views`: `qfd_crom_g_a`, `qfd_su_cbuf_g_b`, `qfd_d2d_rom_b`, `qfd_io_serdes_rxd512` (all 3 SerDes). ETM-bound through `qwen_die_etm_map`: station ETMs on `qfd_cst_n` / `_s` and `qfd_chead`, and slab port-group ETMs. Contract budget (0.2 T): everything else, including `qfd_tile_nk` (GT 3,072 re-synthesis pending) and `tt_up4` (NB 3) | EPYC1 `/srv/opentallas-scratch/claude/qwen-tp8-die/it1` | pending | pending | pending | 0 intra / 0 inter (max inter 135.4 ps; balance left 262 late views) | running. **CONGESTION PROBE ONLY**: 267 µm tile slot, superseded by the coordinator's v2 tile slot of 311.04 × 1,296 |

**Pass criteria:** GRT overflow 0, TT ≥ 0, FF ≥ 0 after pads, clock plan with 0 intra and 0 inter violations, die_audit hops_over 0.

**Script:** `scripts/it1.sh`. Its stages are:

1. Localhost generation and lint.
2. Contract re-derivation and tree-pad check.
3. Assumed libraries, r21b ETMs and `die_views` (`bind_it1.json`).
4. Clock plan: htop + hreg `--shards 12` on EPYC1, then record and balance.
5. EPYC1 `die_chain` followed by `pad_chain`.

## it1 result (EPYC1 `/srv/opentallas-scratch/claude/qwen-tp8-die/it1`)

**FAIL at the real case, before GRT.** There is no GRT overflow or hotspot data. `ot_mts::place` found no legal origin for `crom_g_0` because the constant-ROM row `crom_g_0..3` overlaps `sp_port_tiles_0_f1`. A local overlap check of the it1 case finds the same 4 overlaps. The chain stopped at 04:20, so the congestion probe on the 267 µm slot produced no data.

## Contract v2 probe (tp8a at the 311.04 × 1296 slot; local generation only, not launched)

This probe was superseded at 07:34. The owner chose track B and the spec picked floorplan F2. tp8a v2 is kept only as a probe and as tooling for tp8b.

- **Geometry:** the die is 25,999.5 × 24,719.0 µm. Row gap 669.6 µm. The spine is three 777.6 µm sub-columns plus two 171.9 µm edge relay channels (`_tp8_spine`). The VM square spans all three sub-columns. Overlaps: 0 (the it1 overlap is gone).
- **Root spread (`root_spread`, `_root_spread`):** each block's tree is re-hosted with its local row XOR (block column mod 4). XOR is a tree automorphism, so every leg keeps its length and the reduction order is unchanged. Block roots now sit 4 per row on all 12 rows; before, they were all on local row 1.
- **Reserved pad columns:** each padded leg gets one contiguous corridor column next to its sink, reserved before the bulk relays. The bulk relays end at the column's far end. Tree-leg hops over reach went from 117 to 1.
- **Open item 1, balance:** the reservations change the bulk relay counts of 127 *unpadded* legs (for example, 5 relays become 7 or 10). As placed, 294 of 720 nodes are misaligned. Fix: compute the pads inside the generator *after* the bulk relays, using the arrival model of `gen_bench.tree_pads`. The reservation then only reserves space, and the trim/extend step uses the final counts.
- **Open item 2, non-tree hops over reach:** 59, all in the spine and IO: `pword` ×6, `tt_*` ×31, `o4_cb_*`/`cf_*` ×13, `rst_seq_ctlm` ×3, SerDes rx/tx ×4 (up to 3,496 µm).
- **Fixes:** `su_vm_abut` allows VM S-face groups outside the SU span. The SU E-face `si` clamp is now 80 µm (seq_su sits below the SU).
