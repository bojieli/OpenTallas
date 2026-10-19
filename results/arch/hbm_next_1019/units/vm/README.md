# VM growth on the P = 4 die: unit-side spec (HBM-NEXT-UNITS, 2026-10-19)

**Decision (PROG 10-19 01:35):** the VM grows to at least 412k words (2^18 + 5 x 30k). The as-built VM (2^18) cannot run an N = 6 MTP programme. CMTP measured 326.7k words for a normal layer and 469.8k / 486.0k for the Engram layers 1 / 14 (`cmtp/README.md` section 6).

**Unit-side answer:** add one data macro per bank. That gives **2^19 = 524,288 words** in the quadrant-sliced region. 2^19 is the smallest size the macro granularity allows above 412k, and it also covers the Engram peak (486.0k, +38k margin). **Engram row groups are therefore not needed.** CMTP can drop that option, unless DIE refuses the area.

Status: SPEC and ESTIMATE only. No RTL or gate exists yet. The fork is listed under "next" below.

## d4g VM as built (source: `rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv`, d4g frame)

- 4 quadrant slices x 8 banks = 32 banks (`vmb_<q><0..7>`). Each bank does 1 read + 1 write per cycle, slotted by the compiler.
- Each bank has 3 macros of `ot_sram_1r1w_1024x256_m2_r2c2` (12,317 um² each):
  - **A:** the quadrant-local data, 1,024 rows x 8 FP32 words.
  - **C:** the mirror region, 1,024 rows, the same address in every quadrant.
  - **B:** the SECDED check bits: 7 b x 8 words for A plus the same for C = 112 of 256 b.
- Sector address, 16 b: `s[15]` = mirror, `s[14:13]` = quadrant (must be 0 when mirror), `s[12:3]` = row, `s[2:0]` = bank.
- Capacity:
  - quadrant region 32 x 8,192 = **262,144 words** (= `static_check.VM_WORDS`);
  - mirror region 8 x 8,192 = 65,536 words, one copy per quadrant.
- Bank outlines (d4g frame `d4g_phy.compact.P.json`):

  | banks | outline (um) | area (mm²) | macro fill with 3 macros |
  |---|---|---:|---:|
  | SW / SE | 812.8 x 365.0 | 0.297 | 12.5 % |
  | NW / NE | 849.5 x 339.1 | 0.288 | 12.8 % |

## hnx VM (`hnx_vms_bank`, spec)

| item | d4g | hnx |
|---|---|---|
| data macros per bank | A (1,024 rows) | **A0 + A1 (2,048 rows)** |
| mirror macro | C | C (unchanged) |
| check macro B | 112 / 256 b used | 168 / 256 b used (A0, A1, C fields); still one macro |
| macros per bank / die | 3 / 96 | **4 / 128** |
| quadrant region | 262,144 words | **524,288 words** |
| mirror region | 65,536 (x4 copies) | unchanged |
| sector address | 16 b | **17 b**: `s[16]` mirror, `s[15:14]` quadrant, `s[13:3]` row (11 b; row[10] = 0 when mirror), `s[2:0]` bank |
| request records | rq 17 b {v, sector16}, wq 281 b | rq **18 b**, wq **282 b** (+1 bit on every rq / wq / dq / kq / xq / pq record) |
| bank bandwidth | 1 R + 1 W per cycle | unchanged |
| read latency | n+6 | n+6 expected; the capture mux grows from 2:1 (A/C) to 3:1 (A0/A1/C). The gate must confirm |

Why exactly 2^19:
- 412k needs 12,880 words per bank, which is 1,610 rows.
- A 512-row macro on top of the 1,024-row one gives 1,536 rows, which is 393k: too small.
- So the next step at macro granularity is 2,048 rows, which is 2^19.

## Area estimate for DIE

- **Macros:** +32 x 12,317 um² = **+0.394 mm²**.
- **Outline:** today's banks are not filled by macros: they are 12.5 % macro, and the 4th macro takes that to 16.6 / 17.1 %. The expected outline growth is **0** (the extra mux and decode are a few hundred cells).
- **Upper bound:** each bank grows by one macro row (~75.5 um high x bank width). That is **+2.0 mm²** over the die, well inside the 59 mm² f4c_t5 reserve.
- **For DIE:** reserve +0.4 mm² placed and +2.0 mm² outline worst case. The ~490k "Engram option" costs nothing extra, because it is the same 2^19 VM.
- **Correction:** the `hbm_plane_model.py` placeholder (1.5 mm² / 256k words) prices the +150k at 0.86 mm². It should be replaced by the figures above.

## Ripple to the other units (+1 sector bit)

Every VM client that forms a sector address widens its address field by one bit:
- SU / SFU (lg_tap rq/wq);
- HC: `ot_hnx_hc_q` residual/result base. The row strides are already 16-b sector counts, so the bases need 17 b;
- IDX (`rq4` read group);
- DMA (`rq1`, `dq`);
- x-load (`rq2`, `xq`, `xq2`);
- COLL (`kq`, VM write roots);
- quantiser `wq2` and SM writer `wq1`;
- the packet port `pq`;
- the VM ring records (`VM_RING` 17,792 b class: +1 b per record lane).

This is wiring only, with no schedule change. The cut figures rise by well under 1 %.

## Next (to do: RTL + gate, not a release gate)

1. Fork `ot_vms_bank_static` and the native wrappers (`ot_vms_bank_native_physical`, `hfd_vms_bank_native_q0_faces`, `..._q1_core_pr`) to `rtl/hbm_next/vm/` (`ot_hnx_vms_*`): sector17 decode, A0/A1 select on row[10], B field 112..167 for A1, 3:1 read mux.
2. Bench on fleet Verilator 5.050:
   - bit-exact vs the d4g bank for all rows < 1,024 (N = 1 identity);
   - A1 rows written and read back with SECDED;
   - mutants: A1 check field not written / row[10] ignored. Both must FAIL.
3. Kit `hnx_vms_bank` (d4g outline, 4 macros on the 43.2 um lattice): gate, then submit.
4. CMTP: set `static_check` `vm_capacity` to 2^19 and drop the Engram row-group pricing.
5. DIE: no area change unless the gate grows the outline.

Machine-readable form: `vm_spec.json`.
