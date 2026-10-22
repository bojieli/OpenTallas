# Actual KV reset transport source

This is the requested opt-in structural implementation on `a556212a17`, which
already includes the ALL-FIRST H0 correction and production R16 integration.
It adds actual closed `qkd_rlys_1` instances, wires, and placements. It never
substitutes a geographically closer reset root.

Enable on a fresh generation:

```
export OT_KV_FINAL_RESET_STATIONS=1
export OT_KV_FINAL_RESET_PORTS=rly_pinfix_pll_lock_0__s0/en
```

Additional known lane `en` or `rs` endpoints may be comma separated. The default
is the confirmed 28,959.8 um PLL enable. Other long reset endpoints remain
explicit separate closure work; this source does not claim to repair them all.

## Implemented behavior

After forwarded lanes and the health plane have their actual placements, the
pass reads the current `die.v`, LEF, placement, and manifest. It identifies the
original scalar reset producer as an actual `qkd_rlys_1` output and retains
that exact instance, net, and source clock. It reserves two receiving captures
and transport sites in the current free space. All proposed pin spans use all
LEF rectangle centres, including original driver/receiver orientation. Origins
are anchored to the global 2.16 um lattice. Every new transport relay uses the
original source clock; the two captures use the receiving clock.

The pass generates source in an isolated working case first. Only a successful
complete plan is copied to the real case. Original source/placement files,
per-endpoint input hashes, station lists, and generated source are retained
under `final_reset_stations/`. A failed plan stops generation with the original
case intact. It does not borrow the historical coordinates or ignore an
occupied site. If the current floorplan has no path, its margins/channels must
be enlarged in the die plan; this pass does not move existing macros implicitly.

The matching forwarded-lane record is repriced using the actual new edge count:

```
reset_cal_new = reset_cal_old + source_reset_added - receiver_reset_added
cal_new       = reset_cal_new + actual_FIRST_capture
K_new         = (E + cal_new) mod 8
```

The generated netlist's actual k0/k1/k2 connections and en/rs nets are updated
with that record. E and steady-state data age E+1 remain unchanged. The existing
land-lag check runs once after the opt-in rewrite. With the option off, its
previous ordering is preserved.

## Static calendar and concrete remaining bound

The generator exports `OT_KV_FINAL_RESET_CALENDAR`. The existing static compiler
records its source hashes, exact reset producers, transport/capture counts,
clock domains, and reset G-R0 changes in `cal_deltas`. Its existing retirement
contract also budgets the added reset delay against the whole-plane release
depth, retaining the selected HOLD273 bound and its existing fit result.

The collected historical PLL plan had 87 transport stages and two captures:
89 added reset edges, with a 360.636 um maximum span. Its conditional region-live
release moves 110 -> 199, and the downstream regional path moves 28 -> 117.
The current implementation recomputes these counts; it does not assume 89.
Using the existing PROG17 requirement of 325, that historical count gives a
conservative HOLD requirement of 414, **141 edges beyond HOLD273**. If the
current existing whole-plane requirement is larger than 325, the compiler adds
the generated delay to that larger requirement instead.

Per-source absolute boot dates, POR/IGNORE behavior, clock phase bounds, and
first-use margins are still missing. Every affected first-use margin must
accommodate its actual added reset release delay; no cold-boot PASS is inferred
from a protocol proof. The generated ledger remains explicitly structural and
unqualified for release. Increasing a requested environment HOLD does not
change the actual closed h273b cell. A matching root implementation and actual
production scheduling decision remain necessary.

## Existing evidence and execution status

The implementation reuses the collected site planner and closed relay cells.
Existing ALL-FIRST protocol evidence (`3abf491a6`) passes 2,400 checks across
NF1/2/5/15/40 with 89 real reset relays and catches stale K, missing capture,
and historical NF1-only H0. The original failures and old geometry evidence
remain preserved in their original packets.

Per the owner's instruction to stop new validation campaigns, this new source
pass has not been run in a fresh die generation and no new checks, simulations,
gates, or audits were launched. The live original `a556` chain is untouched.
Use this implementation as the opt-in source for a fresh actual closure chain;
do not treat the historical coordinates or protocol receipt as current geometry
or cold-boot qualification.

## K.RST 10-21 (ELEM-KRST, S81-ELEM): root cause and structural fix -- the PLL path needs NO reset transport

The 28,959.8 um `rrs_n_rst_die_t1__m_0__g1_s188/b -> rly_pinfix_pll_lock_0__s0/en` pair is not a reset-distribution
gap. `rly_pinfix_pll_lock_0__s0` is the pin relay of the PLL lock output, placed 107 um from `rly_pll_lock_0__s0`, at the
PLL in region **c** (every neighbour within 700 um is on `n_clk_core_c`). `kv_pin_repair.relay_trunk` matched a trunk
when the instance was ANY endpoint, and the PLL is the driver of every `clk_core_*` trunk, so the relay took the first
one in bus order, `clk_core_WS`. `kv_fwd_lanes` then laned a c -> c hop as WS -> c (`qkd_landsh0_1`), with
`en = fallback_rst(WS)` (the most common reset net on tree WS: a die-reset leaf 29 mm away) and a die-reset `rs`.
Besides the wire, that gated the PLL lock with a released die reset while the HOST releases every die reset only
after `pll_locked` (`por_n && pll_locked` in qkd_host_*): a boot deadlock.

Fix (structural, generator source):
- `kv_pin_repair.relay_trunk`: trunk membership = the trunk's loads (`b[3][1:]`), never its driver (kv_die's main
  planner already skips `eps[0]`). The PLL lock pin relay joins the sink's trunk (host, `clk_core_c`): a plain
  `qkd_rlys_1` c -> c hop, no lane, no `en` / `rs`, no added reset edge, no boot dependency. Only PLL-launched relays change.
- `kv_fwd_lanes.form`: fail closed if a lane launches from a clock generator (an instance driving >1 core trunk).
- `kv_final_reset_stations`: no default endpoint (the PLL en no longer exists); the stale constant 325 is removed.
- `kv_static_programme.die_retirement_contract`: opt-in stations add `max_added_reset_edges` to THIS die plane's own
  computed need, never `max(.., 325 + extra)`.

HOLD 414 vs 273, resolved from existing evidence (the existing `kv_retirement_contract.build`, no new campaign):
325 was the PROG17 d22hl2 plane (leaf DMAX 179) and +89 was the mis-clocked PLL wire. On the five current selected
`0ae42aa9c` sqk2 generations (ep5 `kvs14r-0ae42aa9c-sqk2{c432,c216,nl,c108,c324}`), using each run's own
`health_successor.json` + GEN7 candidate + `rst_regional.json` max_total_depth 88 for the uncovered sources (+ the
diagnostic 64-edge cross-root skew), the whole-plane need is 262 / 267 / 264 / 267 / 269 <= HOLD273 (margin 4-11).
With the fix the PLL path adds 0, so the h273b cell stands; no HOLD growth or re-closure is required.

Still open (not claimed): the 64-edge cross-root skew is unmeasured (die STA), and the general lane `en`/`rs`
selection (`fallback_rst` = most common net of the tree, not nearest) leaves ~282 en / ~172 rs pins > 405 um on
sqk2c432 (Manhattan driver->pin; ~150 have a same-tree net within 405 um). Those need a post-lane regional landing
(lane en/rs loads re-planned by the regional tree, depth priced into K and the HOLD need), not this PLL transport.
