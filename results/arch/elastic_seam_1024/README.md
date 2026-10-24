# ELASTIC: latency-insensitive seams vs R8 landing pads, Qwen compute die — verdict: REJECT (analytical)

Owner opt-in experiment (2026-10-24 07:35 PDT). The question: should the longest die-level lanes use valid + receive
FIFO + credit seams instead of exact fixed-latency lanes plus R8 bus-coherent delay pads? AGENTS.md design method step 1
says to size this in the model before building it. The analysis below rejects it at that step, so no RTL and no P&R
were built (task 3 was conditional on some lane set winning, and none did).

Reproduce: `cal/run_cal.sh` (yosys 0.68, ASAP7 RVT SS, about 15 s), then `python3 analyze.py`, which writes `sizing.json`.
Both vehicles are read from git:
- **P5 = bound_r8**: plan `e3f313354` + `bind/bound_r8/bus_groups.json.gz`.
- **P6 = main plan**: QC-P6-R8 `1f5b9bee38`, `r8/bus_groups.json`.

Pads are recomputed with `tools/die_plan/r8.solve`:
- P5: 875,012 flops (the binder realised 870,428).
- P6: 248,360 flops, which equals the committed table.

## 1. Where the pads are (task 1)

| | P5 bound_r8 | P6 main |
|---|---|---|
| pad flops | 875,012 | 248,360 |
| pad area (0.3353 µm²/bit-stage, SS) | 0.293 mm² = **0.037 %** of the 787.5 mm² die | 0.083 mm² = **0.011 %** |
| pad flops on lanes of ≤ 6 cycles | 862,762 (98.6 %) | 245,074 (98.7 %) |
| pad flops on the longest lanes (`c_*_bf_00__rsf`: 7 hops, 514 b, 17/18 cyc) | **0** | **0** |
| pad flops from the member's own bus group | 283,907 | 11,375 |
| pad flops from the replica-set / class union | 591,105 | 236,985 |

The longest lanes carry no pad at all. Pads sit on **short** lanes. Each one waits for a slow partner: either a member of
the same as-built bus that the plan routed the long way, or a replica of the same source at a deeper slice partition.

- **P5 worst class, `tw` write bus, one class per slice (×12):** the 1024-bit `tw_data` lane `stm→ctl` is 1 hop and
  2 cycles. The 3 control bits `tw_we`/`tw_kind` arrive at depth 17 via `x_ctl_st_a`. So the data is padded 15 cycles
  (15,360 flops per slice), and `ctl→st_a` is padded 12.
- **P6 worst class:** replica pads of 2 cycles. Examples: `hw ctl→hc1/hc2` (1573 b) against `hc0/hc3`, and
  `fw→ctl` 1607 b against `fw→fe`.

Per-lane tables (hops, width, cycles, member depths, pad histogram, driver bits) are in `sizing.json` under
`longest_lanes` and `most_padded_lanes`.

## 2. Elastic sizing (task 2)

### Area

Elastic receive FIFO cost per padded member (W bits, pad p, bound depth d, duty u in words/cycle):
- **Depth:** D = max(⌈u·p⌉, ⌈u·(2d+2)⌉, 1).
  - Little's law: a word waits p cycles for its slowest partner whether it waits in a pad or in a FIFO.
  - The credit round trip needs 2d+2 entries for full rate.
- **Control:** a valid bit and a credit bit per relay stage, the FIFO pointers and count, and the sender's credit counter.

Calibrated area (`cal/cal_area.json`):

| | µm² per bit |
|---|---|
| R8 pad (ot_dp_dly stage) | 0.3353 per stage |
| elastic FIFO entry (enable + read mux) | 0.523–0.538 |

So one FIFO entry costs **1.6×** one pad stage.

Elastic area relative to pad area. The lower bound counts FIFOs only on padded members; the late members' FIFOs and
the consumer rework are not included:

| duty u | P5 elastic / pad | lanes where elastic is smaller | P6 elastic / pad | lanes where elastic is smaller |
|---|---|---|---|---|
| 1 (streaming) | 2.90× | 0 / 393 | 5.23× | 0 / 212 |
| 1/2 | 1.50× | 48 | 2.67× | 0 |
| 1/4 | 0.86× | 97 | 1.69× | 7 |
| 1/8 | 0.50× | 186 | 0.99× | 72 |
| 1/32 | 0.33× | 243 | 0.80× | 86 |

**Elastic on the longest lanes (the brief) saves 0 pad flops.** It costs 36 entries × 514 b per `rsf` lane
(2·17+2 deep), which is about 9.7k µm² per lane and **0.116 mm² for the 12 lanes**. That is more than the whole P6 pad
area (0.083 mm²).

Elastic can only come out smaller on low-duty buses. Even there the saving does not come from elasticity: a static
"sparse landing" (a valid-tagged capture register released at the scheduled cycle) gets the same rate-aware storage
without credits or relay valid bits. Even total elimination of every P6 pad is 0.011 % of die area.

### Token latency

- By construction, a pad lifts a member to its class maximum offset, which is the arrival of the partner it must join
  (same bus) or stay in lockstep with (replica set).
- An elastic consumer has to wait for the same slowest member. So the worst-case arrival does not change:
  **0 cycles gained** per crossing.
- A registered FIFO adds +1 cycle per crossing; a bypass FIFO adds a combinational enq→deq path on the 833 ps receive
  side.
- P5 and P6 both show max landed depth = max bound depth = 17: no pad raises the deepest arrival.

### Compiler and schedule

The static schedule only holds with elastic arrival if:
- the compiler still schedules at the worst-case landed depth, in which case nothing is gained; or
- every consumer leaf gets valid-gated issue.

Valid-gated issue means:
- **Rework of the as-built static leaves** (heads hc0..3, ctl, stm, st_a, su_c, sc, fe). Today they rely on exact
  relative timing; xt1 0/64 is what happens when it breaks.
- **Joins wherever replica results recombine.** Heads must stay in step, so the skew storage moves to the join and the
  token still waits for the slowest replica.
- **No stalls on calendar lanes.** The calendar collectives (`coll_regen`, LS 389; 35 `land_align_exclude` members)
  cannot stall.

That is a die-wide redesign, not an opt-in seam.

## 3. Pricing (task 4) and verdict

- **Per-user rate:** the gain is ≤ 0 % for every lane set, because worst-case arrival is unchanged. For scale, the 1 %
  threshold at the 5,237 tok/s Qwen ROM model rate (229k cycles/token at 1.2 GHz) is 2,291 cycles per token. Even if
  every P6 pad on the critical chain were removable (max pad 5), that would take 458 padded critical crossings per token.
- **Area:** elastic is larger at full duty on every padded lane: P5 2.9×, P6 5.2×. The ceiling for any pad-removal
  lever is 0.011 % of the die (P6), far from a 1 %-equivalent.
- **Closure:** elastic seams would make relay-count changes functionally safe. But the compiler still needs the
  worst-case latency, and the R8 + plan flow already handles relay changes by regenerating latency.json. No closure win
  can be priced.

**REJECT.**
- No RTL, P&R or default behaviour changed. The `cal/` netlist is a sizing calibration only and is not instantiated.
- Task 3 (RTL seam, exactness proof, 833 ps SS/FF) was not run, because no lane set wins analytically. This is
  recorded as NOT RUN, not as a pass.

## Findings handed to QC-TOK (owner of the padding reduction)

- Pads are caused by **plan splits of one as-built bus onto unequal paths** (P5) and by **replica depth spread** (P6).
  The cheap fix is plan-side, as QC plan r8b did for `tw`: route the slow narrow member alongside its wide partner, or
  equalise replica hop counts. Elastic seams do not address either cause.
- Possible residual idea, unpriced and not pursued: a rate-aware "sparse landing" for low-duty buses.
  - It needs the measured duty of each bus, plus a proof that the consumer ignores data on non-valid cycles.
  - Its ceiling is ≤ 0.011 % of die area on P6, so it is probably not worth it.
