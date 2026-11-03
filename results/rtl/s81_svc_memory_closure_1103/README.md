# S81 svc memory closure, class port of the T7 source event 12605dc2 (DIE-S81-51/MEM, CLOSURE S81-066)

**Why.** 15 S81 svc types fail kit GEN_LINT `memory_bits` (kit wave b1a2125433d0): svc_hi_dsdv_svc_rs__t1..t6, svc_lo_dsdv_svc_rs__t1..t6, svc_lo_dsdv_svc_rs_w__t1, svc_hi_dsdv_svc_pvso_entry__t1/t2. Every one carries the same nine over-limit memories as T7 canary2, with the same content-hashed helpers. The required form is generated memory macros, which is the adopted T7 memory-closure source event (COORD 11-03 00:33). A raised SYNTH_MEMORY_MAX_BITS is not the form.

**Inventory (per type, identical in all 15).** All helpers are async-read flop arrays.

| memory | words x width | bits | form after |
|---|---|---|---|
| pmem `ot_bind_native_193c9` | 512 x 512 | 262,144 | 4 x `ot_sram_1r1w_256x256_m2_r2c2` (PMEM cut) |
| land `ot_bind_native_4c805` (4R/7W) | 640 x 256 | 163,840 | 12 x 256x256 (LAND cut) |
| pvq `ot_bind_native_9c281` | 8 x 2120 | 16,960 | 34 x `ot_sram_1r1w_32x64_m1` (PVQ cut) |
| `ot_hdc_v41x_attn_staging` | 2 inst x 4 lanes x 160 x 265 | 169,600 | 16 x 256x256 (`SRAM_MACRO=1`, existing module form) |
| exp table `ot_hdc_v41x_exp` | 256 x 64 | 16,384 | declared logic, already on main (rom_declared_logic elab_width 64) |
| u_att.sw `ot_bind_native_bfac5` | 32 x 512 | 16,384 | declared flop FIFO, already on main (DECLARED_FLOP_MEMORIES) |

- Macros added: +32 256x256 and +34 32x64 per type. Their LEF/lib views already exist in `physical/asap7_memory_macros_v2`.
- Cycles: 0 added. Each macro's registered read replaces the old capture or output register.
- Reset loads: 0 added.

**Method.** `tools/die_plan/s81_svc_memory_closure.py` runs the four reference transforms (`s81_T7_pmem_bound_cut_0900`, `s81_T7_pvq_bound_cut_1040`, `s81_T7_LAND_bound_cut_1102`, `s81_T7_STAGE_macro_gate_1102/stage_flip.py`). Their proof logic is unchanged. Only three things are re-targeted:
- the svc head, `u_rsv_14_` -> `u_rsv_NN_` (or `u_rsv_NN_u_` for the pvso_entry wrapper level);
- bind-numbered `procmux_N` nets, through a structural name map (`name_map`: a recursive driver signature plus the source location, unique in both files). Plain `N_Y` nets must map to the same number, or the tool refuses;
- the T7 preimage hash locks, which are replaced by the self-check below.

**Self-check.** On the T7 original 61c902f1, the ported chain reproduces every approved hash byte-exactly: 04a55430 (PMEM), then 43dc924c (LAND joint), then 12605dc2 (stage flip). The run is recorded in `closure.json` `self_check`.

**Result.** 15/15 types CLOSED (`closure.json`; closed bounds in `closed/*.sv.gz`). Every structural obligation of the four transforms held for every type:
- port and capture identity;
- the 2158-bit struct field list and its exactly three readers;
- per-lane RD_ADDR = 4*(rc-1)+j, with valid/win/need/scale on the same row;
- removal counts 18 / 23;
- the top header is unchanged, and every other line is identical and in the same order.

**EQ/sim basis.**
- The helpers (same content hash) and the children (3d7ab5aa / 80367218 / 64e23cf3) are byte-identical to T7's.
- The component native gates of the T7 packets therefore cover every type.
- The bound integration is proved by the same structural obligations, re-checked per type.

**Application to a kit.** `--kit-rtl <rtl dir>...` (optionally `--closed-dir` with this packet's `closure.json` and bounds) swaps `s81p_<type>_bound.sv` for its closure. It adds the three children after the bound in kit_rtl.f, kit_rtl_sim.f and kit_rtl.json `files`, and writes `memory_closure.json`. A bound without the helper set is NOT_APPLICABLE.

**Held.**
- Plan placement of the +66 macros and the 25 pre-existing glue macros is not done. All 15 types share T7's 1442.88 x 2453.76 form, which does not fit (DIE-S81-50/t7 ESTIMATE). That work is DIE-S81-51/PLAN's, under S81-RF1.
- 833 ps timing of the 256x256 read cone is unchecked (clk->Q 405-441 ps TT).

**Pilots** (`pilot.sh` = the T7 canary3 recipe: gen phys plan_h2_2249 + kit_gen_lint + kit_preflight with main 08542fa9d7d tools; evidence in `pilot/`):
- svc rs class: svc_hi_dsdv_svc_rs__t1 with its closed bound = GEN_LINT PASS, 5/5 checks with memory_bits 9 -> 0; KIT_PREFLIGHT PASS. SYNTH_MEMORY_MAX_BITS 16384 is the declared exp/sw size, not a raise for the macro memories.
- kv_leaf class: ot_s81sl_kv_leaf__t2 with no source change = GEN_LINT PASS and KIT_PREFLIGHT PASS. Its two exp tables are declared logic on main.
