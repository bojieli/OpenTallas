# Die-region detailed route pilot (2026-10-12): GRT-vs-DRT error bar

Tool: `tools/die_region_drt/region_drt.py` (pick / stage / cut / spef / compare; see its README). Windows are cut from
the die's own GRT checkpoint; instances inside a window are kept as fixed abstracts, instances crossing the edge are
*intruders* (their in-window body becomes OBS on their OBS layers, their in-window pins become fixed terminals), and the
die nets are detail-routed on the clipped die guides under the layer contract (die nets M4-M9, over a block body only
M8/M9). Runs: EPYC1tb `/srv/opentallas-scratch/claude/region-drt/{kv,s81}/<window>/`.

**Status (2026-10-12 09:30 PDT):** KV column is final (DRC 0). KV cong/relay are still iterating. KV ioedge was killed
(flat) and re-staged with the corrected intruder model. S81 cong was killed (stalled on an overflowing GRT).

## Qwen KV die (die_kvi1b GRT, overflow 0)

DRC per DRT iteration (`Number of violations`, iteration 0 first):

| window (um) | kept / intruder pins | nets (internal / boundary) | DRC by iteration | state |
|---|---|---|---|---|
| column [3500,21900,4100,22500] | 23 relays / 1,608 | 13,229 (3,189 / 10,040) | 37,472, 9,344, 5,900, 244, 20, 19, 19, **0** | **DONE, DRC 0** at iteration 7 (5.0 h) |
| cong [4650,14950,5250,15550] | 10 / 8,955 | 9,288 (1,863 / 7,425) | 22,241, 10,557, 12,093 | running (64-iteration cap) |
| relay [1107.6,5931.6,1983.6,6807.6] | 9 / 4,015 | 7,300 (4,236 / 3,064) | 30,488, 7,548, 4,505 | running; same trajectory as column |
| ioedge [7236.9,18066,8370.4,18666] | 0 / 8,158 | 4,396 (3,775 / 621) | 58,224, 18,518, 17,866, 17,738, 17,646 | killed (flat); cut artefact, see below. Re-staged as `kv/ioedge2` |

Column, measured against the die GRT of record:
- wire length DRT/GRT 0.975 (per-net p95 |rel| 10.4%); vias DRT/GRT layer changes 1.99x; layer-contract violations 0;
- net capacitance, die GRT SPEF vs RCX of the detailed route, 3,189 internal nets: total +47%, median +40%, p05 +6%,
  p95 +144%. **This is the GRT-vs-DRT parasitic error bar.** Wire length agrees within 3%, so the gap is per-unit-length
  capacitance (coupling on the routed M4-M9 stack against the GRT RC estimate). Die-level seam STA on GRT parasitics is
  optimistic by about this much on the wire part of every die-top path.
- TT/FF STA in the window is empty: the KV relay abstracts (`qkd_rly_*`) carry no clock pin in the die database (the lib
  has `ck[0]`, the LEF/odb master does not). The window STA therefore has no clocked endpoints, and the die STA cannot time
  relay hops either. Flagged to the KV die lead as a relay-abstract defect. The cap error bar above is the substitute.

### Classification of the M8 Short / Min Step class (the "systematic" reading in the interim note was wrong)
All four windows show the same iteration-1/2 profile, dominated by M8 Short + M8 Min Step. M8 is the horizontal layer
that crosses old-contract block bodies (OBS M1-M7). Column had the same profile at iteration 2 (M8 Short 1,615, Min
Step 831). It then went to 244 at iteration 3 and to 0 at iteration 7. DRT cannot remove a short against a fixed object
(die PDN strap, OBS, terminal). These shorts were therefore net-to-net rip-up congestion over the block bodies, not a
cut or abstract artefact. The counts plateau in iterations 1-2 because DRT raises its marker cost only from iteration 3
onwards. Verdict: not systematic. cong/relay keep running. Only a plateau after iteration 5 counts as non-convergence.

### ioedge: a cut artefact (fixed) on top of a genuine abstract problem
ioedge keeps no block. Six intruders (`ctrl_EN` qkd_ctrl_n with 4,350 M4 face pins in the window, `cdc_EN_15/16`
qkd_cdc_wleaf, `phy_EN` ot_hbm3e_phy, `wleaf_EN_15/16`) became one full-bbox die obstruction on every OBS layer. A die
obstruction has no same-instance exemption, so the intruders' own face pins sat inside it. The result was 17.6k DRC,
flat over iterations 1-4, on M5-M7 (eolKeepOut 6.2k, Short 3.0k) at the pin faces. Fix (`region_drt.py` cut,
claude/el1011-regiondrt): intruder bodies now use the master's own OBS boxes, placed and clipped, and are pulled back
off each face that carries in-window pins on that layer. That matches what DRT does for a kept block. The re-cut has
no-track crossings 8 -> 0 and track-blocked 3,495 -> 2,866. Genuine part: qkd_ctrl_n / qkd_cdc_wleaf are bloat
abstracts (one OBS box per layer M1-M7, covering their M4 face pins, M5 above them blocked). child_lint now refuses this,
and the M5 tile cap re-route (pins M4/M5, keepout above on M6) removes it. Any residual in `kv/ioedge2` from the M5 above
the pins is recorded as an abstract defect, not as a GRT-vs-DRT error.

### Window model under the M5 tile cap (main 7e582db75)
The cut reads each block's OBS layers from its LEF (kept: exact OBS; intruder: exact OBS, pulled back off its pins). The
layer-contract audit is also per-LEF. When the KV/S81 tiles are re-routed M5-capped, M6/M7 open over their bodies
automatically, and die straps sit on M6. The DRT layer range stays M4-M9. Old-contract tiles (OBS M1-M7) keep M8/M9 as the
only over-body layers, which is why M8 carries the rip-up load in these windows. Re-pick the windows from the die GRT
once the M5-capped abstracts are in it.

## S81 (c199b1 GRT, 458,253 overflow / 2,036 overflow gcells)

Window cong [7000,1200,7600,1800]: 19,373 nets (6,865 internal / 12,508 boundary), 2,234 no-track crossings. The
07:05 relaunch stalled in iteration 0 (10% after 12 min, then no progress for 2 h) and was killed at 09:24. A window cut
from an overflowing GRT cannot give a DRT result. Re-stage it once the S81 die GRT reaches overflow 0.

## Pass / record per window
DRC total + classes (`drt_drc.rpt`), WL DRT/GRT ratio + per-net p95, via ratio, layer_contract violations 0, STA TT
setup / FF hold on GRT SPEF vs RCX SPEF for internal nets, and `net_cap` (GRT SPEF vs RCX total net capacitance;
the wire-only error bar when the window has no clocked sinks) in `compare.json`.
