# ASAP7 mask-ROM versus 6T-SRAM bitcell area, and the node-transfer test

**Status:** **PASS**  
**Evidence class:** predictive open-PDK drawn-layout DRC measurement; not a foundry PDK, not TSMC N7/N6/N5, not silicon  
**PDK:** ASAP7 v1.7 (`d24f8b857ff7`), platform hashes verified against `configs/pdk/asap7_physical_lock.json`  
**DRC:** the platform's own `drc/asap7.lydrc`, run under KLayout in the pinned ORFS container `sha256:16470cea1d34...`

ASAP7 is a **predictive** research PDK. Nothing here is a TSMC N7/N6/N5 number, and nothing here may be averaged with the IHP SG13G2 result.

## Measured bitcell pitch areas

| Cell | Pitch | Area | In CPP x fin-pitch units | Ratio to 6T |
|---|---:|---:|---:|---:|
| 6T SRAM (thin cell) | 108 x 216 nm | **23328 nm2** | 16.0 | 1.000 |
| NOR mask-ROM, via-programmed | 108 x 54 nm | **5832 nm2** | 4.0 | **0.2500** |
| NOR mask-ROM, shared-S/D floor (not per-bit programmable) | 54 x 54 nm | 2916 nm2 | 2.0 | 0.1250 |

## Cross-node comparison

| Node | ROM bitcell | 6T SRAM bitcell | Ratio | 6T / ROM |
|---|---:|---:|---:|---:|
| IHP SG13G2, 130 nm planar (sibling) | 0.390150 um2 | 3.0067 um2 | **0.1298** | 7.71x |
| ASAP7, predictive 7 nm FinFET (this run) | 0.005832 um2 | 0.023328 um2 | **0.2500** | 4.00x |
| Difference | | | **+92.7%** | |

`node_stable = False`. ASAP7 ratio is HIGHER: the ROM bitcell is relatively LARGER against 6T SRAM at the 7 nm-class node than at 130 nm. This moves against the ROM side of the comparison.

## DRC cases

| Case | Expected | Violations | Rules |
|---|---|---:|---|
| `rom_shared_sd` | clean | 0 | - |
| `rom_via_programmed` | clean | 0 | - |
| `sram_6t` | clean | 0 | - |
| `probe_rom_shared_sd_tight_y` | must fail | 149 | ACTIVE.FIN.EX.1, ACTIVE.S.1, LISD.S.2, LISD.S.3-4, M1.S.6 |
| `probe_rom_via_tight_x` | must fail | 60 | ACTIVE.S.2A, GATE.S.1 |
| `probe_sram_tight_y` | must fail | 2 | WELL.S.1 |
| `rom_via_sram_rules` | clean | 0 | - |
| `probe_rom_via_sram_rules_tight_x` | must fail | 60 | ACTIVE.S.2A, GATE.S.1 |

The `probe_*` cases shrink one lattice quantum and must fail; each names the rule that pins that dimension. `rom_via_sram_rules` gives the ROM array ASAP7's SRAMDRC memory-cell rule relief and measures no shrink at all.

## Claim boundary

- This is not a TSMC N7, N6, N5 or N4 number and must never be labelled one.
- This must not be averaged, blended or combined with the IHP SG13G2 measurement.
- This does not establish ROM read margin, sensing, energy, PVT, yield or cost.
- No ASAP7 FakeRAM or synthetic memory collateral was read or used.

## Reproduction

```bash
python3 tools/asap7_bitcell_density.py
```

See `docs/ROM_DENSITY_NODE_TRANSFER.md` for the interpretation.
