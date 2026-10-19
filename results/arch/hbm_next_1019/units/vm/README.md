# VM growth on the P = 4 die: unit-side spec (HBM-NEXT-UNITS, 2026-10-19)

**Decision (PROG 10-19 01:35):** the VM grows to at least 412k words (2^18 + 5 x 30k). The as-built VM (2^18) cannot run an N = 6 MTP programme. CMTP measured 326.7k words for a normal layer and 469.8k / 486.0k for the Engram layers 1 / 14 (`cmtp/README.md` section 6).

**Unit-side answer:** add one data macro per bank. That gives **2^19 = 524,288 words** in the quadrant-sliced region. 2^19 is the smallest size the macro granularity allows above 412k, and it also covers the Engram peak (486.0k, +38k margin). **Engram row groups are therefore not needed.** CMTP can drop that option, unless DIE refuses the area.

Status (UNITS-VM 10-19): **RTL + bench DONE** (rtl/hbm_next/vm, section "hnx RTL as built" below); kit hnx_vms_bank gated (see Gate).

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


## hnx RTL as built (HBM-NEXT-UNITS-VM, 2026-10-19, branch claude/hbm-next-units-vm-1019)

d4g die master forked: **all 32 d4g banks bind `hfd_vms_bank_native_q0_faces`** (results/rtl/hbm_b_rtl1_1017/vm_quadrant_map.json;
SW/NW/SE/NE identical master, RG 5 / WG 2, EG_WIDE 1), kit `vm_native_q0_faces_g313c` (270 x 313.2 um, 3 SRAMs).
`ot_vms_bank_static` / `q1_core_pr` are NOT on the d4g die and were not forked.

| file (rtl/hbm_next/vm/) | from (d4g) | delta |
|---|---|---|
| `hnx_vms_bank_q0_faces.sv` | `faces_q0/hfd_vms_bank_native_q0_faces.sv` | widths +1, `clk_macro3`, bench-only `MUT` |
| `ot_hnx_vms_bank_q0_core.sv` | `faces_q0/ot_vms_bank_q0_faces_core.sv` | widths +1, `clk_macro3` |
| `ot_hnx_vms_bank_q0_body.sv` | `faces_q0/ot_vms_bank_q0_faces_body.sv` | sector17 decode, A0/A1 select on row[10], B field [167:112], 3:1 capture, 4th SRAM `u_a1` |
| `ot_hnx_vms_ce_counter_pipe.sv` | `ot_vms_ce_counter_pipe.sv` | rename only |

Records: rq 18 {v, s17}; wq/dq/kq 282 {v, s17, data256, mask8}; xq/xq2/eg 277 {v, row12, data, mask}; pq 286 {v, wr, row12, data,
mask, tag}; pr 266 and status 18 unchanged. row12 = {mirror, row11}; a mirror sector with row[10] = 1 faults (sticky FAULT).
Pipeline unchanged: read n+6 (+1 pin register = 7 edges measured), commit n+3, egress n+1; 1 R + 1 W per bank per cycle.

### Bench (fleet, Verilator 5.050, ot-epyc5, bundle d6bd0f0aa; `tools/hbm_next/hnx_vm_bench.sh OUT all`)

`rtl/hbm_next/vm/tb/tb_hnx_vm_bank.sv`, 2 banks (bid 2, 5; sid 1), real SRAM models:
- **Phase A lockstep vs d4g** (same schedule to `hfd_vms_bank_native_q0_faces` and the hnx bank; random owners 0..5 / 0..6 every
  cycle, lower 2^18 + mirror, partial masks, mirror egress): every output bit-identical every edge.
  SEED 1: 4,000 cycles, 8,024 compared edges, 4,701 reads, 5,012 writes, 413 mirror egress, 1,647 packet responses.
  SEED 2: 6,000 cycles, 12,024 edges, 6,969 reads, 7,263 writes. **PASS**.
- **Phase B 2^19 scoreboard** (hnx alone): all 2,048 quadrant rows (A0 + A1) + 1,024 mirror rows per bank written back-to-back
  (all 7 write sources), 512 partial-mask rewrites (A1-heavy), all 3,072 rows read back-to-back (all 6 read owners, permuted):
  6,144 reads, 2,048 upper (A1), constant latency 7 edges, status 0 (no CE/UE/FAULT). **PASS**.
- **Phase C**: mirror sector with row[10] = 1 -> FAULT. **PASS**.
- Lint of the kit sources (-DSYNTHESIS, SRAM black box): 0 errors.
- Mutants (each FAILS, witness committed in `witness/`):
  - MUT 5 = A1 read select dropped (capture mux reads A0): `TB_HNX_VM FAIL MUT=5 ... DATA` (`witness/m5.log`);
  - MUT 6 = sector wrap (row[10] decoded as 0: 2^19 wraps onto 2^18): `TB_HNX_VM FAIL MUT=6 ... DATA` (`witness/m6.log`);
  - MUT 7 = A1 check field never written: `TB_HNX_VM FAIL MUT=7 ... DATA` (SECDED mis-corrects, `witness/m7.log`).
  All three pass phase A (lockstep) and fail in phase B: the new mechanisms only.
Logs: `bench/verdict_all.txt`, `bench/m0s1.log`, `bench/m0s2.log`, `bench/lint.log`.

### VM clients whose address width changes (for CMTP / DIE): +1 bit per record, no schedule change

Bank port map (d4g, every quadrant; vm_quadrant_map.json):

| bank port | d4g -> hnx | client (instance / master) |
|---|---|---|
| rq0 / wq0 | 17 -> 18 / 281 -> 282 | SU LG pair taps `su_<q><s>` (ot_hbm_vm_lg_static_tap / _split / lg_pair_tap); HC residual / result VM bases (`ot_hnx_hc_q`, base 16 -> 17 b) ride these |
| rq1 | 17 -> 18 | DMA write-back `hb_dbk_<q>` |
| rq2 | 17 -> 18 | x-load control `xl_<q>_ctl` (SM_X) |
| rq3 | 17 -> 18 | COLL `hb_coll_<q>` (SW/SE/NE); quantiser `hb_quant_NW` (NW) |
| rq4 | 17 -> 18 | quadrant IDX ctl/query (SW/SE/NE); `hb_coll_NW` (NW) |
| wq1 | 281 -> 282 | SM writer `smw_<q>` (ot_hbm_sm_vm_wr_q_t_lanes4; calendar payload base10 -> base11) ; NW via merge `vmm_NW<b>` |
| dq | 281 -> 282 | delivery lanes `vmdel_<q><b>` (ot_hbm_svc_vmdel_lane_n NPC 2; aperture base field +1 b) |
| kq | 281 -> 282 | COLL `hb_coll_<q>.vm_kq` |
| pq / pr / xq / xq2 / eg | 285 -> 286 / 266 / 276 -> 277 | quadrant hub `hb_vms_<q>` (hfd_hgi_vms_static_<q>b_glue): packet row 11 -> 12 b; CW/CCW ring lanes (2,224 b) +1 b per bank record (+8 b per lane) |
| rslot / wslot / bid / sid | unchanged | calendar `calendar_<q>` |

Compiler: `static_check` VM_WORDS 2^18 -> 2^19; every sector field 16 -> 17 b (isa_rows.py / plane_compiler).

### Kit and area (for DIE)

Kit `physical/ref_tile/hnx_vms_bank` (top `hnx_vms_bank_q0_faces`), d4g g313c floorplan + `u_a1` on top of the abutted SRAM stack
(same 90.624 um pitch, direct clock entry `clk_macro3` at its clk pin): **outline 270 x 403.92 um = 0.1091 mm²** (d4g 270 x 313.2 =
0.0846): **+90.72 um bank height, +0.0245 mm² per bank, +0.78 mm² over 32 banks** (macros +0.394 mm²). DIE f4c_t6c reserved
+86.4 um per bank for 412k (5 macros) and +151.2 um for 524k: the built 2^19 bank needs only +90.72 um (4 macros; the check
macro B holds all three fields). Pins: `tools/hbm_next/hnx_vm_pins.py` (exact plan, 3,933 pins: N 592 / S 1,111 M5 on the d4g
slots; W 1,116 / E 1,114 M4 at 7 tracks on the taller faces).
