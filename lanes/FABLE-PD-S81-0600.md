# FABLE-PD-S81-0600: S81 SerDes face / AM path review (serdes__t13 pilot)

2026-11-17 06:00 PST. Technical PD only. Gate: R-MINIMAL (routed TT >= -42 ps, internal FF hold >= 0, DRC 0), 833 ps.
To: S81-TYPES-R3, COORD.

## Verdict

Every TT failure in the last seven forms is a clock failure on `io_pma_rck`, not a data placement or cycle budget failure.
The recovered clock is one tree, 63 buffer stages and 2.18 ns deep, and 205 repeaters added after CTS put 837 of its
25,112 register sinks up to 390 ps later than the rest. Each failing class is a path between one of those late groups
and the balanced bulk, or a half-cycle path that loses 148 to 224 ps to duty distortion on the same deep tree.

With the late groups brought to the common depth, the H5 global-route snapshot reads TT -30.5 ps with 0 endpoints
below -42 (modelled from measured arrivals; it reads -64.25 with 3 below -42 today). No retime and no pin move is needed
for that. The form to build is H5's placement with the rck tree depth equalised (section 3).

## 1. Root cause, measured

Source: H5 `5_1_grt.odb` (sha 886605288fe7, density 0.30), TT, global-route RC, the same frame as the kit TT gate.
Probe: epyc8 `/srv/opentallas-scratch2/claude/fable-fix-s81-serdes/probes_fable_pd_0600/` (`probe.tcl`,
`rck_sinks.tsv` = every rck clock buffer and sink with its position and clock arrival, `paths400.rpt` = 438 paths
under +60 ps). ot-run unit oth-ubuntu-3860324-1794923531, exit 0, WNS -64.25 reproduced.

Geometry:

| item | value |
|---|---|
| rck pad pin | (332.7, 1063.8) M7, the west end of the PMA strip |
| PMA RX macro | x 319 to 2566, y 926 to 1055 (2246 um wide) |
| rck register sinks | 25,112, x 319 to 2550 |
| sinks in x 800 to 1800 (decoder, rate-match memory) | 23,787 (94.7 %) |
| CTS root buffer | (1448, 675) |
| trunk, pin to root | 20 stages, about 1505 um, about 800 ps |
| H-tree, root to leaf | 42 stages, about 1370 ps; CTS reports average sink wire 1618 um |

Depth and arrival:

| group | sinks | stages | rise insertion (ps) |
|---|---|---|---|
| bulk | 24,275 (96.7 %) | 63 | 2149 to 2256, p10 to p90 = 2165 to 2195 |
| late groups | 837 (3.3 %) | 64 to 75 | up to 2565 |

The CTS H-tree is balanced: the launch and capture branches of the worst path agree to 2 ps at level 7 (1976 vs 1974).
The late groups come from the 205 post-CTS repeaters (118 `clkleafrep_*` from the leaf-repeat hook, 87 `wire*`
max-wire buffers). 20 of them are the common trunk; the rest sit on the sparse branches that reach the face ends and the
outlying transport bits, and nothing re-balances the rck tree after them (the tap balance only handles `clk_t*`).

Late groups by place: x 1927 to 2062 at 72 to 73 stages, 2520 to 2565 ps (x0 and rck_transport bits); x 2415 to 2550 at
67 to 68 stages, 2326 to 2394 ps (east face `u_rxf_q[532..543]` and all nine `u_face_am3.parts`).

Duty distortion: fall minus rise arrival is 148 ps at the median sink and 191 ps at the deepest (2.35 ps per stage, all
stages are same-polarity BUF). The H10 CTS snapshot read 224 ps over 68 stages. The falling-edge `u_rxf_q` to
rising-edge `u_face_am3.parts` path therefore has 192 to 268 ps instead of 416.5 ps, for 318 ps of data over 19 um
(clock-to-Q 79, eight placement buffers 157, three logic cells 82).

Failing classes against that picture:

| form, stage | class | slack (ps) | clock cause |
|---|---|---|---|
| H5 GRT | `u_syn.x0` -> `u_syn.x_q` (707 um) | -64.25 | launch 72 stages, capture 63: 415 ps adverse, 9 extra repeaters |
| H5 GRT | `u_rxf_q` (fall) -> `u_face_am3.parts` | -15.0 | half cycle, 234 ps fall-rise difference |
| H5 CTS | same AM class | -87.9 | same |
| H7 CTS | boot release | -116.3 | 201 ps adverse |
| H7 CTS | AM class | -102.2 | 261 ps (duty + leaf) |
| H7 CTS | `u_lpl_*_r.o` -> `u_out.bsrc` | -97.3 | 344 ps adverse |
| H7 CTS | `u_bm.gm` -> `u_bm.d` | -90.4 | 292 ps adverse |
| H10 | AM class, all 21 FF on one leaf | -62.57 | 224 ps duty distortion alone |
| H5 CTS, FF | `u_rck_transport` r -> q hold | -257.8 | capture 326 ps later than launch |

Each re-place moves the late groups to different sinks, which is why each form produced a new worst class.

## 2. The form most likely to close: H12 = H5 placement + rck depth equalised

Keep: H5 RTL (bound sha e55e8d12), H5 `3_place.odb`, density 0.30, SDC f364d75, all cycles. Change only the rck clock
build in the CTS step:

1. After the leaf-repeat hook, balance the `io_pma_rck[0]_regs` tree bottom-up: at each branch node, pad every child
   branch to the latest sibling (tolerance 20 ps). Pads are inverter pairs, so they add no duty distortion.
   Size: about 25 late leaf groups, at most 12 levels each, so at most about 300 pad points and of the order of 1,000
   to 3,000 cells (0.3 to 0.8 % of 385k). Bulk insertion rises from 2177 to about 2565 ps; rck is asynchronous to
   `clk` (max-delay crossing), so absolute insertion is free.
2. Acceptance before GRT: rck sink rise insertion span <= 110 ps over all 25,112 sinks (the bulk is 107 ps today).

Expected numbers (each of the 438 paths re-timed with both end arrivals taken from `rck_sinks.tsv`):

| class | H5 GRT now | H12 model |
|---|---|---|
| `x0` -> `x_q` | -64.25, 3 below -42 | +288.6 |
| `am_ok` -> `xs` (843 ps of data, both ends in the bulk) | -30.5 | -30.5 |
| `u_rxf_q` -> `u_face_am3.parts` | -15.0 | -12.3 |
| `u_lpl_0_r.rc` -> `.o` | -3.2 | -3.2 |
| whole block | -64.25 | -30.5, 0 below -42, 32 below 0 |

This is a model on global-route RC, not a routed result, and the margin to the gate is 11.5 ps. The limiter becomes
`am_ok` -> `xs`, a data path; if the routed read lands under -42, that one class gets a duplicated `am_ok` register
(+0 cycles), not another whole-form change. Internal FF hold gets easier: the -257.8 transport class is the same
late-capture skew. DRC 0 rests on H5's own detailed route (first pass at 80 %, 70.8k violations, against 176k for H3p
at density 0.5); H12 does not change the placement, so H5's DRT verdict carries.

Optional second lever, as a plan change for the five shore-band types only if the AM class is short after routing:
move the rck pad pin (and the PMA model's `pma_rck` pin) from x 332.7 to x 1448, same y. The trunk goes from about
1505 um / 20 stages to about 390 um / 5 stages: -15 stages, about -590 ps insertion, -35 ps duty distortion at
global-route RC, which lifts the AM class from -15 to about +20.

## 3. Stop list

- More data-side fixes on the AM path: same-leaf cohorts (H10), buffer prunes (H10b; the one pruned path gained 79.8 ps
  but seven ends stay at -58.8 to -45.1), cone moves, and the falling-edge face flop swap (554 flops, 234 hops over
  100 um on a half cycle of at most 268 ps).
- Density variants: 0.50 fails DRT-0255, 0.20 reads TT -532 on 402 ends, pad 2 failed. 0.30 is settled.
- Frozen-CTS global-route resumes and more TT repair (H9, -102.2 to -47): repair cannot buy back 350 to 415 ps of
  clock.
- Per-class localisers as a whole-form route (BOOT path 8f05 is fine as a source fix; H7 still read -102.2 on the
  other classes).
- xface retime (H11, branch bc62574bc34) as the closure form: its target class reads +288.6 once the clock is
  equalised, so the 1,088 flops and the delay change are not needed, and a resynth re-rolls the late groups. Keep the
  synth result; no place and route unless `x0` -> `x_q` is still short after H12.
- H4 (density 0.5) and H6 / H8: superseded brackets.

## Not checked

- No H12 build exists; the -30.5 is a re-timing of measured arrivals, not an STA of an edited database.
- The pad count is an estimate from the group count, not from a constructed tree.
- H9's own TT read was still in global route at 05:35; H5 and H7 detailed routes had not finished.
- The four G / J class types and t3 / t12 were not opened; they are blocked on their floorplans, not on this clock.
- FF corner arrivals were not dumped; the hold statement rests on the H5 CTS FF census class.

Housekeeping: my probe left a 1.4 GB copy of the H5 snapshot at `probes_fable_pd_0600/in/input.odb` on intel1 and
epyc8 (scratch2 is 99 % full on both); both copies can go. Two of my own probe waiters (epyc2, intel1) were cancelled
before they started.
