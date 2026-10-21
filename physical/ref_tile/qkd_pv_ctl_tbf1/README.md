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

## r2 structural safe rebuild (KV-FLOOR2 10-20)

Gate 1 (below) failed the native census on the r1 = tb1 structure. r2 rebuilds `ot_qwen_tp8_pv_wide_ctl_tbf` in place
(same module, ports, parameters; same token / data edges, END_FLOOR=0 still = ctl_tb edge for edge):
- Reset: control / valid bits only (state, flt, nodes, ti, start copies, one-hot IDLE copies, iv/cv/cf flags, req_valid,
  fault, busy, cmd, out_age, out_epoch, ep, nq_end, pa counters, walker active). Datapath unreset (lim, nq, drain_left,
  reduce_left, wage, walker q/nq/lim, pin data words). Reset tree: pin flop `rst_q` (RESET_PIN) ->
  `ot_rst_relay_bounded32 #(16)` (rtl/lib) -> 16 kept leaves, each <= 18 asynchronous clears.
  BOOT-ONLY edge change: reset release reaches the control flops 3 edges later than r1 (relay root / second / leaf);
  assertion stays asynchronous; the first start follows boot by >= 200 edges (bench) -- no scheduled edge moves.
- Kept registered copies (keep + dont_touch; gate flop count 769 vs r1 688 = copies NOT merged): `start_k[9]`,
  `pid_k[4]`, `fbad_k[6]`, `idle_k[8]` (= state_n == IDLE, registered one-hot IDLE decode). One (start, idle, fia_bad)
  triple per load group (ep, nq_end, lim, nq, pa_c, pa_n; walker active/q, lim, nq) replaces the r1 79/33 decode nets.
- `age` -> two kept counters `pa_c` (check side) / `pa_n` (next / cmd side), both = r1 age + 1 every edge.
- `cv_r != {32{cv_r[0]}}` as and/or trees (cv_r[0] no longer drives 32 compares).
- Request walker: local copy `ot_qwen_tp8_pv_wide_ctl_tbf_vrow` (= ot_qwen_tp8_vrow_wide edge for edge; its unconnected
  fault flop dropped) so the shared closed module stays untouched.
- MUT 3 (new bench negative control): the kept pa_n copy loads 2 at start (replica divergence).

## Safe-design checklist (owner 10-19, binding; RULE FREEZE 10-20: tile rules are guidance) -- r2

1. Pins: PASS. Every data input `*_r` and every output is an RTL flop (pin_regs flow off with reason: a flow stage
   would add a cycle the calendar lacks). Reset lands in 2 registered stages (reset_landing: rst_n 1 sink).
2. Reach: PASS. 43.2 x 43.2 tile, gate reach 0.3 um; no wire > 405 um.
3. Fanout: PASS (fixed in r2). Pre-gate native census on the mapped netlist (gate 2): limit 32 PASS, max 32 loads
   (r1: 6 violations, max 277). Kept copies survive synthesis (769 flops).
4. Depth: WARN (guidance). Gate estimate 642 ps / 16 levels (pa_c -> cbad -> abort -> drain_left) vs r1 ~740 ps /
   18 levels; tb1 (same logic class) routed and closed at the 770 ps flow clock / 833 ps sign-off.
5. Storage: PASS. No storage > 2 kb (control state only).
6. Floorplan: PASS / util waived. No macros; one full std-cell band; pins on full faces <= 5.74/um; square; util 34%
   (outline fixed by the die-placed u_ctl slot of the pv_trunk_gen strip, same as closed tb1). Trial GRT overflow 0,
   worst M3 27.7%.
7. Clock: PASS. 769 sinks, TT insertion 99.1-105.5 ps (spread 6.4), FF 74.3-80.8 ps (spread 6.5); pin-flop spread
   4.2 ps TT/FF. io_hold_margin 0.03.
8. Schedule: PASS. Static, no handshake; P1 = P0 handed to the compiler (kv_static_programme pv_floor,
   OT_KV_PVFIN_FLOOR=1); 0 added token cycles; boot-only reset release +3 edges recorded above.

Native census (pre-gate rule 10-19 23:45): r2 gate 2 PASS, limit 32, max 32 (gate_result.json).
Benches: pv_floor (FLOOR=1 skew 0 bit-exact both pairs; FLOOR=0 shows the shipping skew), mutants pv_floor_m1 (k_qc
slot) and pv_floor_m3 (pa_n replica divergence) with committed fail witnesses in results/arch/kv_floor2_1020/.

## Gate 1 (10-20 13:32, pre_route_gate --remote auto --cts, ot-pve1): FAIL — native census refused at floorplan

Mapped-netlist census (limit 32 loads, 3119 roots): 6 violations, max 277 — the CLOSED tb1 structure fails today's census
(tb1 predates it): reset `g_reset_pin.rst_q` 277 RESETN loads; `start_r` 70; comb `_3968_` 79 + `_5112_` 33 (state /
FEED-end decode); `pid` 36; `age[1]` 33. No waiver exists (tools/ref_tile/native_census.py), so the same-outline drop-in
cannot be gated. Structural rebuild owed (r2, same ports / same scheduled edges): datapath unreset (owner 10-20 09:05:
reset control/valid bits only) + ot_rst_relay kept leaves <= 32; kept replicated copies of start_r / pid / age (check
Yosys did not merge: paramod names); registered one-hot state/phase decode copies feeding <= 32 loads each. Then
pv_floor_bench (bit-exact, P0 == P1) + a mutant witness, re-gate. Until then the die runs DIAGNOSTIC with
OT_KV_PVFIN_FLOOR_STANDIN=1 (closed tb1 view renamed).

## Gate 2 (10-20 13:54, r2, pre_route_gate --remote auto --cts, ot-epyc5): WARN (0 fail, 3 warn)

native census PASS (limit 32, max 32); util 34% (slot-fixed outline); logic depth 642 ps / 16 levels (guidance);
CTS TT spread 6.4 ps, FF 6.5 ps; trial GRT overflow 0. PNG review (gate_layout/floorplan.png, density.png): no
macros, one std-cell region, pins on the four full faces as planned, clock entry on S, cells pulled toward the
W (in_*) and N (cmd / col_*) faces, no empty channel on a link path.

