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

**Open.** 119 pad-junction hops exceed 500 µm (maximum about 1,030 µm), where the corridors near the node are full. The fix is for it2: reserve the pad sites before the bulk relays are placed.

## Iterations

| It | Source | Views | Run | GRT overflow | TT setup | FF hold (after pads) | Clock plan | State |
|---|---|---|---|---|---|---|---|---|
| it1 | tp8a (see `it1.log`) | Closed: `qfd_cst` (n/s), `qfd_crom_g_a`, `qfd_su_cbuf_g_b`, `qfd_d2d_rom_b`, `qfd_io_serdes_rxd512`. Contract budget (0.2 T): everything else, including `qfd_tile_nk` (GT 3,072 re-synthesis pending) and `tt_up4` (NB 3) | EPYC1 `/srv/opentallas-scratch/claude/qwen-tp8-die/it1` | pending | pending | pending | pending | running |

**Pass criteria:** GRT overflow 0, TT ≥ 0, FF ≥ 0 after pads, clock plan with 0 intra and 0 inter violations, die_audit hops_over 0.

**Script:** `scripts/it1.sh`. Its stages are:

1. Localhost generation and lint.
2. Contract re-derivation and tree-pad check.
3. Assumed libraries, r21b ETMs and `die_views` (`bind_it1.json`).
4. Clock plan: htop + hreg `--shards 12` on EPYC1, then record and balance.
5. EPYC1 `die_chain` followed by `pad_chain`.
