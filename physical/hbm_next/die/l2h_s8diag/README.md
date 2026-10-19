# f4c_t9p3 S8 diagnosis (LEAD2-HBM/L2H-P3, 10-19)

These notes are about the P=3 next-release HBM die, case `hnx_case_f4c_t9p3_land`. It uses stand-ins and is diagnostic only. It is not a closure claim.

## What failed

- S8 run.log: OpenROAD SIGSEGV inside the die-repeater `repair_design`. It happened at iteration 0, with 18,695,977 nets still remaining.
  - Wall time was 56 min and RSS was 75 GB, below the 160 GB docker limit.
  - GRT never started.
- Span census: `span_hist.py` computes the driver-to-farthest-load span per net family; the output is `span_hist_f4c_t9p3_land.json`.
  - The case has about 18 M nets: 10.26 M lane-hop to lane-hop and 5.23 M relay to relay.
  - About 80% of the hop nets are 405 um or shorter.
  - About 4.7 M are over 405 um. Most of those are 405-600 um: lane rows end up 'slid along/across/row nearest' (15,417 of 42,435 are 'row nearest').
  - The longest are HC bank tiles. `hcb_*` (32 x 548x549 um) has no plan or grant slot, so it is placed by a peer-centroid "home" AFTER the lane rows. That moves it 1-30 mm: hcb_SW7 and hcb_SE6 went to y=30078 at the top edge, and hcb_SE* went to the SW corner.
  - The hcb_SW6->SW7 link is 2,351 b direct and 30.9 mm long.
  - The plan's hce_Q slots (1598^2) now hold sfup/sfr, and the 8 banks per quadrant would not fit there anyway.
- Reset: 31,148 POR sinks have no regional tree. Almost all of them are the `rs` pins of relay and lane-hop stations; the relay layer says "rs = domain reset leaf; never forwarded".

## Diagnostic S8 variants (same GEN, placement and netlist; only run.tcl differs)

- `_rs150`: `die_repeaters.tcl` gets `skip_short_um 150`. Nets whose pin-bbox HPWL is under 150 um are marked do-not-touch, because they need no repeater. With fewer nets for `repair_design` to walk, this variant tests whether the crash comes from the scale of the run.
- `_norep`: the repeater step is removed, so GRT runs on the unrepeated die. This localises the SIGSEGV and gives the congestion of the die as placed.

## Structural repair (separate sub-lane)

1. Give hcb_Q0..7 grant slots: a 2x4 racetrack per quadrant corner (SW corner free x 2160-4450 / y 345-1490 in the pre-relay case; SE above hc_eng; NW and NE top corners), placed in step 1 BEFORE the lane rows. Re-run S3..S8 so stations are planned on the final positions.
2. Plan stations at about 360 um, so that the lane-row legalisation slack stays at 405 um or less.
3. Relay reset: forward `rs` per hop (one registered reset bit travelling with the lane, like the forwarded clock). Alternatively, make data relays reset-free, flushed by the source pin registers. Either way only hop-0, the landings and the tiles stay on the regional forest (the same H.RST blocker as the release d4g die).
4. Price the added hops and edges for CMTP.
