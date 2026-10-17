# Die clock method: neighbour-relative clocking (owner decision 2026-10-16)

Binding for all three dies: S81, HBM, and Qwen (compute and KV/system).

The compile-time schedule is fixed. So the die clock does NOT need global zero skew. It needs:

1. **Regional delivery.** One physical tree per region (a region root), with matched insertion inside the region.
2. **A neighbour budget.** Every pair of tiles that exchange data synchronously must be within **80 ps flop-arrival
   skew at TT setup AND FF hold**. Flop arrival = die pin arrival + the tile's in-arc insertion R.
   There is no die-wide spread criterion.
3. **Fixed-latency links between regions** that are not neighbour-matched: forwarded-clock relays (form F1 below),
   re-timed once at the sink region. Each such edge is in the static schedule (+1 cycle at the sink). There are no
   credits, no backpressure and no runtime handshakes.

Async families keep their CDCs / FIFOs and are listed, never judged. Examples: HBM PHY clocks, host, ingest, the PHY
(SerDes/UCIe/d2d), and meso cfifos.

## 1. Regions and roots (per die)

- A region is a compact area (a few mm on a side) whose sinks share one regional tree.
- The trees of all roots of one synchronous family that have sinks in a region form one `balance_group` (the region).
  Example on the Qwen KV die: pll_c plus the stack root inside one band.
- Neighbour regions = region pairs with at least one communicating tile pair, from the die netlist (data nets joining
  2..8 block instances, `die_clock_geom_dump.py --pairs`) or from the generator's crossing-edge list. Diagonal
  neighbours count.
- Root sites: at the region centroid, about 60 x 60 um kept free in the floorplan. Until the floorplans reserve them,
  the builder roots every regional tree at the PLL pin and adds a root buffer beside it.
- Starting sizes:

  | Die | Regions |
  |---|---|
  | Qwen KV | 2 columns x 4 bands of ~6.3 mm |
  | Qwen compute (q2o4) | 68 regions from Q-DIEPLAN3: AW/AE array groups, port stacks, CORE (one region; split VM/SU/TT if its FF spread is above 80), IO, KV |
  | HBM | C band plus NE/NW/SE/SW quadrants, per family (serial, stream, hbm), split further where a region's FF spread is above 80 |
  | S81 | hub (serial + stream hub/sfar), per-column cfifo trees, scfifo; seams below |

## 2. Delivery inside a region and between neighbours (tools/die_clock/build.py)

- **Trees.** Each regional tree is an R-aware DME merge on obstacle-aware routes. Every cell is a real ASAP7 buffer on a
  legal site.
- **Trim.** Two corners in one STA (TT late, FF early). Two delay elements: P (stacked BUFx12f) and W (a BUFx24
  local/far pair 180 um apart, measured in context). The trim is hierarchical: an offset that a whole subtree needs is
  placed once at the subtree's input.
- **Targets.** Spec `"neighbours": [[regionA, regionB], ...], "neighbour_budget_ps": 60`. Each region's target rises
  only as far as its neighbours require, through difference-constraint relaxation. There is no die-wide target.
  - The 60 ps tree budget leaves 20 ps for the in-region spread inside the 80 ps neighbour gate.
  - Regions that talk to no one keep their natural insertion.
- **Partial runs.** `"unclaimed": "disconnect_diagnostic"` builds a partial clock (for example macro trees before the
  relay stations are legal). It is labelled DIAGNOSTIC and is never a die result.
- **R per master pin.** Taken from routed views' `insertion.json` (`view_targets.py`, or the die's own clocks.json).
  Any master without one gets an explicit `SYNTH_IDEAL_R0` label, and a result containing such masters is diagnostic
  for those masters.

## 3. Forwarded-clock relay standard, F1 (HBM, Qwen and S81 die links)

```
hbfd_rly_<W>_<dir>_fc / qkd_rlys_*_fc ( clk_in, rs, i[W], o[W], clk_out )
```

- **Register.** Clocked by `clk_in`.
- **Data output.** `o` = register Q, then ONE output buffer of the same cell and drive as the clock buffer.
- **Clock output.** `clk_out` = `clk_in`, then one in-tile clock buffer.
- **Pins.** `o` and `clk_out` sit side by side on the downstream face, on the same layer, so the data and clock wires
  run in parallel.
- **Per-hop hold.** About clk2q - t_hold at FF, independent of hop length.
- **Per-hop setup.** Gains the clock wire delay.
- **Chains.**
  - The first station's `clk_in` = the SOURCE regional root (the root of the driver flop).
  - Station k+1's `clk_in` = station k's `clk_out`. Data and clock travel together.
  - Branches: up to 4 children per `clk_out`. Above 600 um of total branch wire, use a second buffer.
- **Sink end.** Applies to every inter-region bus whose regions are not neighbour-matched.
  - The last stage takes `clk_in` from the SINK regional root: a 1-stage re-time, +1 cycle, priced in the ledger.
  - The die STA times it with propagated clocks. Both clocks come from one PLL, so they are related and the latency is
    fixed.
  - DIE-CLOCK trims the phase with pads on the sink-root branch, until it meets TT setup and FF hold.
- **Intra-region buses and neighbour-matched crossings.** No forwarding and no added cycle. Stations use the root of
  the region they sit in.
- **Equal-age pads.** At the sink, on the sink root.
- **`rs`.** The domain reset (a reset-forest leaf), unchanged.
- **Contract.** Every `clk_in` / `clk_out` is bound explicitly. Strict port-bind refuses any implicit clock.
- **Bench.** Lockstep against the old tile, plus mutants (clk_out tied; o taken from i). The tile's `insertion.json`
  carries clk_in->clk_out and clk_in->CK (R) at ss/ff/tt.

## 4. Die STA

- Propagated clocks on the physical regional trees: `clock.odb` from build.py. Or `set_clock_latency` per tile clock
  pin from the measured `arrivals_<corner>.tsv`. No ideal `phi - R` sink clocks at sign-off.
- All roots of one family form one related clock.
- Forwarded-clock links are timed hop by hop on the forwarded clock: launch `clk_in[k]`, capture `clk_in[k+1]`. The
  sink re-time stage is timed as a related-clock crossing with its compiled fixed latency. No global-skew pessimism is
  applied to these links, and none is waived.
- Fixed-ratio seams (S81 serial:stream 3:4, VM x34/x43, capture x8x incl. ckvb):
  - related clocks, `set_max_delay 1388.889` / `set_min_delay -1111.111` from the other root, latencies included
    (`tools/s81/die_sta.py seam_constraints`);
  - resets released on the common epoch edge;
  - never `set_clock_groups -asynchronous` for a scheduled seam.
- Async families: `set_clock_groups -asynchronous` only between true async families, with their CDC cells.

## 5. Check (tools/die_clock_check.py) on every die trial

```
die_clock_geom_dump.py --odb DIE.odb --out G --roots <roots> --pairs          # communicating tile pairs (P rows)
build.py ... --write-odb ; build.py --measure ... --corner ff                  # TT + FF arrivals
to_dump.py manifest.json arrivals_tt.tsv dump_tt.tsv --pairs-from G/pairs_u.tsv  (same for ff)
die_clock_check.py report dump_tt.tsv --ff-dump dump_ff.tsv --targets targets.json \
    --budget-ps 80 --region-map spec.json --families families.json --out die_clock_check.json
```

- The report gives per region: insertion, flop-arrival spread, and intra-region pair skew.
- `neighbour_check` gives per pair class (`intra:<region>`, `neighbour:<A>|<B>`, `async:<f1>|<f2>`): pairs, TT max,
  FF max, and the number over budget.
- The verdict is PASS only when every judged pair is within 80 ps at TT AND FF. Without an FF dump the verdict is
  INCOMPLETE.
- Look at the clock images (`plot.py`) of the whole die and of the worst regions on every trial.
