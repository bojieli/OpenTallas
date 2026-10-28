# DIE-S81-14 (S81 die owner): go13 intra hold re-timed with the CLK-INV-CAL-1 inverter model, and the ESTIMATE for the next inverter build

Data: intel2 /srv/opentallas-scratch2/claude/die-s81-14/t1.
- The go13 proof is /srv/opentallas-scratch2/claude/die-s81-13/proof (rise-only, plan plan_s10).
- Tools:
  - main = origin/main 7bccfa99f1 tools/ (git archive).
  - cal = origin/claude/clk-inv-cal-1-1028@8795df0cf. This is the CLK-INV-CAL-1 rework on FLOW-ONEMODEL-1, with the clock cell declared. It is not re-approved yet, but its inverter rows (Ainv/Ainv2 + SPICE_CLOCK_CAL_INV) are the same as in the approved @fccbe1df43.
- The die_sta_related options are the same as the go13 sta_intra run: table AOCV, shared droop, --cppr-lca, spice cal, FF core latency 202.5, no hold buffers.
- Scripts are in scripts/. Numbers are in data/intra_hold_retime.json.

## 1. go13 intra hold, before and after the calibrated inverter model (CHECKED, own runs)

| run | clock model | TT setup | FF hold | FF kit-contract W180 (neg pairs) |
|---|---|---|---|---|
| go13 log (go13 code) | BUF (auto) | -657.5 | -1183.9 | -952.9 (24822) |
| main 7bccfa99f1 | BUF (auto) | -657.5 | -1183.93 | -952.93 (reproduced exactly) |
| cal 8795df0cf, --clock-cell inv2 | inv, Ainv, spice 0.9324/0.938 | -508.57 | **-1049.05** | -827.09 (22847) |
| WHAT-IF: cal + early:=late (nominal pin cap) | same | -492.07 | -1033.53 | -811.05 (20232) |
| WHAT-IF: cal + early core taps credited with their declared core insertion | same | -147.34 | **-754.29** | -522.24 (1599); damage p99 177 / p99.9 224 |

The worst pair is the same in every row: bk_sel clk_c3 (early core tap) -> clk_t2 (plain tap).

## Root cause: the S81-13 diagnosis is wrong

### The 13.4 % spread is not variation
- The 13.4 % late/early spread comes from the Liberty pin-capacitance range.
  - CKINVDCx16 pin A is 9.54 fF, with rise_capacitance_range (6.68, 9.54). That is -30 %.
  - BUFx24 is 1.76-2.35 fF, which is small next to the wire load.
- OpenSTA uses the minimum cap on the early path. So every inverter stage is about 13 % faster on the early path (first stage: 16.3 vs 13.9 ps).
- combo.tcl has no set_timing_derate (CHECKED). die_sta_related already documents this as CLOCK-MESH-2.
- Its effect on FF hold is only 15.5 ps (-1049.05 -> -1033.53), because CPPR and the common prefix absorb most of it.

### What sets intra hold
Intra hold is set by the late-only skew of 991-1007 ps between early core taps and plain taps. That skew has two parts.

(a) GATE MODEL
- The declared-budget block model puts the common latency (202.5 FF) on BOTH sides of a pair.
- An early core tap is early BY DESIGN: its core insertion is 510-829 TT / 402-665 FF. The gate charges all of that planned earliness as damage.
- Crediting the declared insertion (schema.core_tap_early_ps) moves FF hold from -1049 to -754. Kit-contract negative pairs drop from 22847 to 1599.
- The real-view path (--core-view) would apply this credit, but S81 has no signed views for these cores.
- This is a measured failure. It is reported to COORD; no tool was edited here.

(b) STRUCTURE (hangs deliver at the wrong time)
- With the credit applied, each core clock pin is compared with the median plain tap of its partition. Core pins arrive too early: p50 -36 ps TT / -52 ps FF.
  - Cause: the build used QC's ratio 1.48/1.28, but the S81-measured ratio is 1.78/1.53.
- The tail is 16 TT / 19 FF taps that arrive more than 180 ps early (data/core_tap_overshoot.txt):
  - bk_sel c3: -669 TT / -624 FF.
  - The fW*_p1/p4_b1/b2 c3-c5 taps: about -200.

### Dropping early delivery fails by construction
- Without early delivery, each core pin arrives late by e = insertion - common latency. From the plan:
  - 1358/1696 taps have e over 180 at TT, and 1327/1696 at FF.
  - The maximum is 579 TT / 463 FF.
- So making the core taps plain DME sinks (no hangs) FAILS the kit contract by construction.
- The declared-budget gate would not catch this. It would report about 0 damage for those taps.

## 2. Next inverter build: ESTIMATE from the go13 measured edges

Counts come from data/edge_stats_go13.txt (CHECKED). The effects are estimates (UNCHECKED).

### (b) No upper-node hangs
- Keep early delivery, but as a DME sink delay. Per partition, the core-tap cluster merges with the plain subtree at its zero-skew point. Merges are binary (fanout 2), with a snake on the fast side only, so no node carries a star.
- Today, 901 hang-parent nodes each carry 1-5 hang legs; 130 of them carry 4.
- Delivery uses the S81-measured ratio TT 1.78 / FF 1.53, not QC's ratio.
- Estimate:
  - The FF p50 bias goes from -52 to about 0.
  - The tail is then set by the per-tap ratio spread (+-0.4), about |60| ps at p90 for e = 230.

### (i) Slew
- 197 of the 204 TT cells with slew > 320 ps are the first repeaters of hang legs (S81-13). Removing the star hangs removes them.
- About 7 remain, in the feed and phy band. They get branched legs with repeaters at <= 450 um (rep 250 today). No upsizing.

### (ii) DME level split
- Edges over 350 ps TT that are NOT hangs:
  - dme 80, feed 37;
  - of those, over 450 ps: dme 7, feed 16.
- Width fit from the S81-13 data (211 ps at 420, 244 ps at 480) is about 0.55 ps of width per ps of level. So a level of <= 350 ps gives a width of about 173, against the 208 limit.
- Split each such edge at its middle repeater into a tree node: +117 nodes, about 0 extra cells (each new node sits on an existing repeater).
- The 181 hang edges over 350 ps disappear with (b).

### Hold estimate after (b), with the credit
- Worst case = plain in-region spread (max 211 FF, S81-13) + the |off| tail (about 60). That gives kit-contract about -90 (UNCHECKED).
- The plain in-region balance (fW2/fE2 H-tree halves) is still needed to meet W180.

### F1 and tool needs
- The F1 GEOM-44 placement (the S81-13 apply estimate) goes into the same build.
- Shared tool needs (opt-in, default byte-identical):
  - die_trial --region-dme-early-mode merge;
  - die_trial --tree-opt dme_node_pitch_ps=350;
  - in the die STA block model, a declared per-tap core insertion for early core taps (FLOW-ONEMODEL owner).
- No build in this slice: building no-hang now would give a gate-blind result.
