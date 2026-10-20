# QW-COLL regional split of the Qwen TP8 collective core (2026-10-19)

Branch `claude/qw-coll-split-1019` (base `codex/coll-b4-bank64-1019` 9a92ac53f). Source `rtl/rom/ot_coll_tp8_split.sv`.

## Why

Both whole-core gates of the monolithic B4 core failed the clock rule on ONE glue root spread over 734x1037 um:
TT pin-flop spread 451.7 ps (lattice) and 277.3 ps (R0 all-grid), 6628 of 10196 sinks
(`results/rtl/qwen_coll_safe_1019/core_*_gate_failure`). One failed route = structural redesign, not knobs.

## Structure

The core datapath is already bit-sliced in four 128-bit slices (one package fold + one cross fold per slice). It is
rebuilt as five hardened LEAF tiles, each with its own small local CTS root:

| tile | count | contents | outline |
|---|---:|---|---|
| `qfd_coll_split_q` (`ot_coll_split_q`) | 4 (one master) | 128 data bits of every record: pin regs, P/R ring data (2+2 x `ot_sram_1r1w2c_128x64_m1`), S-ring data (4 x `ot_sram_1r1w2c_256x64_m1`, 512 rows), both fold slices as soft logic, all data muxes | 302.4 x 302.4 |
| `qfd_coll_split_c` (`ot_coll_split_c`) | 1 | sequencer, every token/valid/metadata/check/fault, P meta ring (1 x 128x64), S meta (2 x 256x64), R err/last 256-bit flop ring, 168 per-Q token output registers | 190.08 x 181.44 |

`qfd_io_collective_split` composes C + 4 Q with no glue logic; it is port-compatible with `qfd_io_collective_static`
except the clock entries (clk = C, clk_q0..3 = Q). B4 capacity (128 words) sits in ONE 128-row native column per 64 bits:
no bank-select mux. Every SRAM face is <= 3.81 contacts/um (old 512x128 S macro 7.4/um, 32x64 5.95/um).

## Crossings and paid cycles

- C -> Q: schedule tokens only (42 pins per Q, one landing flop per pin). The schedule is static, so C reads each
  token TWO edges early (early taps of its stationary token rings; S-meta read at offset LS-1) and sends it through a
  kept C output register and the Q input register: each Q select lands at its ORIGINAL cycle. 0 data edges.
- Q -> C: fold error bits. pe (package fold) only feeds the sticky fault: +2 diagnostic edges.
  xe (cross fold) is the R-record err bit (ur_rec[513], R ring, out_err): the reduce E stage moves EX = 2 edges later
  (Q delays xr two more edges in a stationary ring; C lands xe in two registers). Gather, LU and LS unchanged.
- {fault, fault_code} leave C registered together: +1 diagnostic edge. Completion/drain must wait 3 more edges for
  the last fault observation.
- Compiler: `tools/qwen_coll_tp8_static_bench.py --split` (word_events: reduce out = c + 2LU + 2SL + LS + 12 + EX + w).
  Token price (72 AR + 1 argmax): +2 x 72 = +144 cycles on top of the chosen LU/LS. With the bank-command audit
  candidate LU66/LS391 (+2834 vs current LU53/LS378): +2978 cycles = +1.19 % of 249577 (throughput -1.18 % at equal
  frequency). With the ROOT model LU65/LS390: +2760.

## SAFE-DESIGN checklist (owner 10-19)

1. Pins: PASS. Every input lands in exactly one flop at the face (Q: ir/dp/dr/sr/c_tok/straps; C: cmd/in/meta/valid/
   q_pe/q_xe); every output leaves its own flop (C drives each Q landing flop from its own kept output register).
   Reset lands in two stages per tile (`ot_coll_rst_leaf`, rst_n 2 sinks). Waived: C `cmd_free` stays the
   combinational 6-level diagnostic predictor (never gates issue); registering it needs the issuer-side +1 diagnostic
   age (ROOT model 70461c678). C kit uses hold_budget tile for it.
2. Reach: PASS by construction inside each leaf (Q 302 um, C 190 um); gate measures actual wire per stage. Parent:
   C <-> Q and pin legs are registered hops; the parent/die placement must keep each leg <= 405 um or add relays.
3. Fanout: PASS candidate. Replicated kept copies: tbv x8 (32 loads), tcv/gd/tfv/tfo x4, gsel x4, die strap x8, rank
   select x16, S bank select per 32 bits; token rings chunked to <= 10 bits per pointer. Mapped census at gate.
4. Depth: PASS candidate. All wide selects are AND-OR one-hot with registered selects; token ring read = one-hot
   AND-OR; fold slices unchanged (closed tile TT +231 ps). Gate path classes pending.
5. Storage: PASS. > 2 kb in SRAM natives (P/R/S data, P/S meta); every delay >= 3 deep is a stationary ring
   (`ot_coll_tok_ring`, <= 840 bits each); no flop->flop shift chains; xr delay is a 3-slot ring.
6. Floorplan: macros on the 43.2 lattice, 51.8 um x / >= 45 um y channels, >= 43 um from every pin face, halo 10.8 um,
   faces <= 3.81 contacts/um; Q full-width standard-cell band y 257.4..300; aspect 1:1. Outline from the synthesis
   area of the first gate (spec estimate std 36000 / 6000 um2).
7. Clock: one local CTS root per leaf; parent supplies one regional entry per leaf with a neighbour-matched C <-> Q
   boundary (TT and FF <= 80 ps); io_hold_margin 0.03. Spread measured at the --cts gate.
8. Schedule: static, no credits/backpressure. E stage +2, fault +2/+1 diagnostic, priced above.

## Evidence

- `run_one.sh` / `run_bench.sh`: Verilator 5.050 fleet benches (production 4 + unit 13 at LU66/LS391, production at
  LU65/LS390) and negative controls LEAD, EX, RERR, SBANK, RANK, RLAT, GATHER. Results `bench/` (fleet ot-epyc7,
  source = 0613be211 split RTL before token-ring chunking/fold-clock port removal; functionally identical rerun on
  exact HEAD is v4, pending): unit 13/13 PASS, production 4/4 PASS at LU66/LS391 (AR256 span 838, argmax 472, 2xAR
  1094) and at LU65/LS390 (835/470/1091 = B4 model +2 per AR, gather +0). Every mutant caught: LEAD 16 mismatches,
  EX 1024, RANK 704, RLAT 512, GATHER 2112, SBANK all-die faults/0 outputs, RERR out_err 4 of 8 dies. Witnesses in
  `witness/` (fail regex `COLL_TP8S FAIL mutant=<define>`).
- Kits: `physical/ref_tile/qfd_coll_split_q`, `physical/ref_tile/qfd_coll_split_c` (specs in tools/ref_tile/specs).

## Q slice safe3 (QW-CLUSTER3, 2026-10-19 16:50 PT) -- kit physical/ref_tile/qfd_coll_split_q3

Why: q2 --cts gate (ot-epyc7 ref_gate/qfd_coll_split_q2-20261019-122644) ended CTS with OT_HOLD_STALL NEEDS_RTL:
FF hold -30.6 ps/1,091 endpoints -> -7.8 ps/46 R2R after 3 h repair; top classes fold skew delay-line `dl` flop->flop
chains (u_xf and u_pf) and adder pipeline data-reset flops; textbook: one fold reset leaf drove 5,138 flops; 23,402
flops on one root (SS boundary spread 59 ps, placement RC). One failed gate = structural redesign:

1. Pins: unchanged (every pin lands in one flop / leaves a flop). PASS.
2. Reach: tile 302.4x259.2, local; no single-cycle wire beyond ~300 um. PASS.
3. Fanout: rst_n lands in ONE 2-flop face leaf (u_rs; port 2 sinks); rs feeds only registered relay copies
   u_rsg (rings' address counters, cc, q_pe/q_xe), u_rst0/u_rst1 (21-bit halves of the token landing), u_rsx (u_xr
   pointers) -- release one edge after the leaf, the same pattern as C's u_rsq/u_rsp/u_rss/u_rsr -- and each fold's own
   2-flop leaves (seam+rings, one per fold stage: 4 adders' valid bits + 7-bit error line, adder data reset off).
   Every relay/leaf <= ~32 sinks (first q3 attempt with 3 port-fed leaves was refused by textbook reset_landing: rst_n
   6 sinks; gate stopped). Fixed.
4. Depth: unchanged datapath (q2 setup SS +103 ps after CTS). PASS.
5. Storage: the u_xf skew delay lines (D = 7 and 14 edges x 128 b = 2,688 flops) are SRAM rings (ot_coll_nring,
   4 x ot_sram_1r1w2c_128x64_m1, rd valid exactly D edges after wd, same as the shift line); u_pf's constant-zero
   sources g >= 2 are tied to 0 (their lines only ever held 0; adders kept, so fold latency and rounding unchanged).
   Fixed.
6. Floorplan: 12 natives in three N-S stacks at x = 43.2 / 129.6 / 216 (43.2 lattice), 51.8 um channels, one
   full-width std band above y ~ 209 and between stacks; outline from q2 synthesis (25.7k um2 std minus removed
   flops ~ 23.5k) at ~0.5 util, aspect 1.17. PASS (gate checks).
7. Clock: one local root over a 0.3 mm tile; judged by pin-flop spread <= 80 TT+FF at the gate; io_hold 0.03. Gate.
8. Schedule: zero added cycles (ring age = shift age; tie-offs and reset split change no data edge). PASS.
Negative control for the new mechanism: OT_COLL_FOLD_MUT_DR (ring one edge short) must FAIL reduce_8w_x16.

### Q safe3 tied always-zero inputs: per-input verdict (QW-COLL4 10-19, coordinator 18:34 rule)

Rule: a tied input is allowed only if architecturally constant in every Qwen config (compiler proof cited); else it is a
forbidden tied functional port and is restored + benched. The Q tile's own ports (`ot_coll_split_q`) carry no tie: every
port is driven by the parent / C and lands in a pin flop. Tied connections inside the tile:

| input (instance.port) | value | verdict | constant proof (file:line) |
|---|---|---|---|
| `u_pf.src[383:256]` (package fold source g=2) | 0 | CONSTANT (allowed) | A Qwen TP8 package has exactly 2 dies, so the package sum has exactly 2 live sources: compiler golden `tools/qwen_coll_tp8_static_bench.py:127` `pk = [G.add(f[2 * p], f[2 * p + 1]) for p in range(4)]` (ND = 8, `:30`); spec `results/arch/qwen_tp8_1012/SPEC.md:199` "8 dies in 4 B200-class packages (2 dies per package)" and `:205` "both fold p = d0 + d1"; the die-in-package strap is 1 bit (`rtl/rom/ot_coll_tp8_split.sv:158` `die_ps`), so no config can feed a 3rd/4th source. The original monolithic core already fed `{0, 0, hi, lo}` (`rtl/rom/ot_coll_tp8_die.sv:9,225`): ((lo + hi) + 0) + 0 = lo + hi bit for bit. |
| `u_pf.src[511:384]` (package fold source g=3) | 0 | CONSTANT (allowed) | same proof as g=2. |
| `u_pf` skew-line sources g >= NLIVE=2 (`rtl/rom/ot_coll_fold_slice.sv:51`, `pg = 0`) | 0 | CONSTANT (allowed) | these delay lines are fed only by the constant g=2/3 sources above (they could only ever hold 0); adders kept, fold latency and rounding unchanged; unit/prod benches 8f42f133d PASS. |
| `u_rsg/u_rst0/u_rst1/u_rsx.d` (reset relay data) | 1 | CONSTANT (allowed) | reset synchroniser data input: release value by construction (async assert from rs, sync release); not a functional port. |
| `ot_csp_rep_reg` strap / rank-select copies `.rst_n` with `RST(0)` | 1 | CONSTANT (allowed) | `RST(0)` copies have no reset; the port is unused by construction (static strap copies of pk_q/di_q). |

No input RESTORED (none was a functional port).

## Q slice safe4 / safe4w (QW-COLL4, 2026-10-19 21:50 PT) -- kits qfd_coll_split_q4 / qfd_coll_split_q4w

Same RTL as safe3 (577229357; benches unit 13/13, prod 4/4 LU66+LU65, mutants dr/lead/ex/rerr/sbank FAIL, witnesses
8f42f133d). Why: q3/q3w gates (ot-epyc4 ref_gate/qfd_coll_split_q3{,w}-20261019-164832) FAIL fill 28% / 25% (macros 13159 +
synthesized std 8838 in 78382 / 89580 um2; outline from the 23.5k std ESTIMATE, synthesis gave 12669 (8838 placed)) with all
1376 heavy data pins on W (560) + E (816); q3w also TT spread 83.1 ps > 80 (345.6 wide). One failed gate = re-floorplan:

1. Pins: unchanged RTL pin flops. PASS.
2. Reach: tile <= 260 um. PASS.
3. Fanout: unchanged (safe3). PASS.
4. Depth: unchanged (q3 TT setup +97.6 ps pre-CTS). PASS.
5. Storage: unchanged (safe3 SRAM rings). PASS.
6. Floorplan (fixed): outline from SYNTHESIS area: q4 220.32 x 259.2 (aspect 1.18) = 45 % fill with synth std 12669
   (38 % with placed 8838; gate WARN band, > 35 %), q4w 233.28 x 259.2 (43 % / 36 %; placeable density INFO 56 %).
   Pins re-faceted over all four faces: N clk/rst/straps/in/out (261), W SerDes 1/2 (512), E UCIe P/R up/dp/ur/dr (512),
   S SerDes 0 + C tokens + errors (~300): <= 2.0 pins/um averaged on every face (q3 E 5.5/um over 57 %).
   12 natives in two abutted N-S stacks on the 43.2 lattice: x 43.2 = 4 S-data 256x64 + P bank 1; x 129.6 (q4) / 172.8
   (q4w) = xf skew rings g3/g2, R ring, P bank 0 (P banks both at the N in_data face); every macro >= 20 um from each
   pin face; centre std channel 51.8 um (q4) / 95 um (q4w), full-width std bands at S (43 um) and N (21 um). PASS (gate).
7. Clock: one local root over <= 233 x 259 um (q3 at 302 x 259 measured TT/FF spread 59.6/56.3; q3w's fail was the 345.6
   width); io_hold 0.03. Gate --cts measures TT+FF spread <= 80.
8. Schedule: zero added cycles. PASS.
