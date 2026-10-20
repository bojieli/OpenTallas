# qkd_pv_ctl_tbf1 — PV pair END FLOOR control (KV-FLOOR1 10-20)

Top `ot_qwen_tp8_pv_wide_ctl_tbf` (`rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_ctl_tbf.sv`), END_FLOOR=1, bound in the KV die
under `OT_KV_PVFIN_FLOOR=1` (needs `OT_KV_BOOT_AGES=1`, `OT_KV_PV_T=1`) as `u_ctl` of the generated frame
`qkd_pvw_die_tbf` (`rtl/qwen_sys/split_20261014/qkd_pvw_die_t_bf.sv`, `kv_bootage.py --pvw ... --floor`).

What changes against the CLOSED `qkd_pv_ctl_tb1` (`ot_qwen_tp8_pv_wide_ctl_tb`): one 16-b `nq_end` register (pair 0's
issue count for both pair straps) and the FEED-end compare / `out_age` on `nq_end`. Same ports, outline
43.2 x 43.2, pin faces, layer cap, recipe and hooks (the generated kit differs from tb1 only in `PARAMS`). The
pair-1 control stays in FEED for `nq_end - nq` extra edges with no row in flight, so both pairs publish at P0 and
`qkd_pv_fin_s |P0 - P1| = 0` at every context (KV_STATIC_PARAMS ATTN_CALENDAR PVFIN_PAIR_SKEW was 32/16 on 4096 of
8192 contexts). Token cost 0 (the pvfin join already waited for max(P0, P1) = P0), no stall, no handshake.

Bench: `tools/qwen_kv_die/pv_floor_bench.sh` — `results/arch/kv_floor1_1020/pv_floor_bench_full_307565e07.log`:
FLOOR=1 bit-exact both pairs, out_age P0 == P1 at T = 1 .. 8192 classes incl 4097 / 8192; FLOOR=0 reproduces the
shipping skew 32 / 16 / 0.

## PINBOUND decision (notice 10-20 09:25)

`ot_qwen_tp8_pv_wide_ctl_tb` W face: 248 b (in_valid 8 + in_t 112 + in_epoch 128) on 43.2 um = 5.74 pins/um.
- Merge into the pvw parent: NOT possible as a hardened absorb. `qkd_pvw_die_t*` is a wires-only frame flattened onto
  the die by `kv_expand` (the die is its parent); u_ctl is a die-placed hard leaf at the fixed `pv_trunk_gen` strip
  slot (`kv_die.py` pl['u_ctl'], 43.2 x 43.2).
- Re-shaped kit (e.g. 43.2 x 86.4, W 2.9 pins/um): needs a `pv_trunk_gen` strip re-plan, i.e. a new
  `qkd_pvw_die_t.sv` and every pin keyed on it (kv_pvw_padding / residual roles / profiles) — a die re-plan, not a
  floor fix.
- Decision: same-outline drop-in. 5.74 <= 6 pins/um; the same face CLOSED in tb1 (gate overflow 0, M2-M5 <= 24%).
  RULE FREEZE (owner 10-20 09:35): die GRT/STA decide. Re-shape only if the die GRT names the u_ctl W face.

## Safe-design checklist (owner 10-19, binding; RULE FREEZE 10-20: tile rules are guidance)

1. Pins: PASS (unchanged from tb1). Every data input `*_r` and every output is an RTL flop; pin_regs flow off with
   reason (a flow stage would add a cycle the calendar lacks). Reset lands in 2 registered stages (reset_landing).
2. Reach: PASS. 43.2 x 43.2 tile, no wire > 405 um.
3. Fanout: WAIVED (same as closed tb1): reset `rst_q` drives ~272 flops (gate WARN, > 32 native-census guidance).
   Reason: drop-in for the closed tb1 structure; changing the reset tree changes the boot reset-release edges
   and the LEC profile. Tile-local, 43.2 um, FF/TT closed in tb1. Re-structure only if this gate or the route fails.
4. Depth: WAIVED (same as tb1): age -> reduce_left ~740 ps / 18 levels estimated (gate WARN); tb1 routed and closed
   at 0.77 ns. The added `nq_end` compare replaces the `nq` compare (same width): no new depth expected; check the
   gate's worst path.
5. Storage: PASS. No storage > 2 kb (control state only).
6. Floorplan: PASS / waived util. No macros; one full std-cell band; pins on full faces <= 5.74/um; square; util
   ~33% (below 40-60%; same outline as tb1 so the die slot stays).
7. Clock: PASS expected (tb1: 688 sinks, TT 109.5 / FF 83.4 ps insertion, spread 5.9 / 5.8 ps). io_hold_margin 0.03.
8. Schedule: PASS. Static: P1 = P0 handed to the compiler (`kv_static_programme.attention_calendar` pv_floor,
   `OT_KV_PVFIN_FLOOR=1`); 0 added token cycles.

Native census (pre-gate rule 10-19 23:45): taken from this gate's synthesized-netlist textbook lint (remote gate
`--cts`); record the numbers here when the gate result lands. Owed before submit_exact: a mutant bench
(MUT=1 k_qc slot) with its committed fail witness, and the standard LEC receipt after the route closes (strict-bind
profile for `ot_qwen_tp8_pv_wide_ctl_tbf`).
