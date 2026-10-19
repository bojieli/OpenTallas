# Qwen A0 structural continuation

There is no selected qualified native A0 view. These results qualify individual
source changes and preserve the failures that require a structural successor.
The original gate-writing worktree was not changed. No REVIEW or submit occurred.

`failures/nk_c1r9f.json` is the immutable DPL-0033 failure with no GRT table;
`failures/nl_c1r9f.json` rejects before remote execution because its reset landing
clock was missing. Source baseline is `985e49d6e` plus `c980cbe47`.

The recovered source samples reset once in `qfd_tile_nk_rp2_45.reset_q`.
Per-child reset relays do not establish the required two face stages or bound
that common reset driver. The historical opt-out therefore cannot qualify reset.

`nk_c1r9f_census.json.gz` contains every signal driver and endpoint from the
actual immutable `1_synth.odb`, with an independently recorded ODB SHA256. The
audit counts all cell input pins, including combinational and hard-child pins;
its second count traverses physical buffers/inverters/hold cells. Clock and tie
drivers remain in the inventory. Nine register outputs exceed 32 terminal loads:
split[1:0,2,3] 383/325/260/232, round147, reset104, active89, wsrc89,
k_last60. There are 99 nonclock driver records above32, including buffers and
tie cells. The full inventory is compressed, not filtered to the passing cones.

`REGROOT_MODE=4` is opt-in; both NK/NL wrappers default to the existing3.
The operand change owns each select and its decode in a two-lane chunk. Original
half selects had only1–2 immediate decode loads, but their NAND decode outputs
drove256 loads. The new actual ORFS mapped result retains64 local control FFs,
adds58 FF, bounds the common upstream wsrc at32 and group masks at9, and removes
the 256-load decoded operand controls. All nonclock above32 records fall99→74.
Nine other register roots remain above32. `source_binding.json` proves the
22 other source inputs match the immutable historical run byte for byte.

`copies_v1` records the actual64-MAC, ten4096x266 ROM, all-eight-LSL and node
numerical comparison:6399 checks,2560 nonzero outputs, same output edges.
Mutants28/29 clear a W/E local group-mask bank; mutant26 holds a real ROM reset
relay. All three fail the comparison. The first fixture uses round0; it does not
qualify the rounding-mode control. Its build digest and exact logs are retained.

The `copies_v2` followup copies the S2 round selector per sixteen output
bits (+7 FF, zero logical edges; +65 FF combined). It enables round on alternating
operations and uses nontrivial low mantissa bits. Native6399 checks/2560 nonzero
outputs PASS; bank28/29, reset26, and round-off30 all fail (round30 gives2400
mismatches). Actual mapped round control loads are22 maximum, operand control
loads1, common wsrc32. Eight other register roots still exceed32; all nonclock
above32 inventory records are70. V2 source is `9d9a7140b`.

`REGROOT_MODE=5` implements the owner-authorized output landing:512 data FF on
the eight existing `ck_tx0..7` roots (64 FF each), and one valid FF. The complete
tile data/valid return advances exactly one edge; node n_a/n_b→n_y stays on its
existing edge. No new clock port, backpressure, data mask, or timing exception is
introduced. `outland` records6399 native comparisons/2560 nonzero outputs PASS
with exact+1 data/valid matching; missing-relay31 fails6250 comparisons and real
reset-relay26 fails1200. Actual mapped state increases by513 relative toV2;
all512 new data FF drive exactly one actual node t_d input. This source is
`0bfed5970`. The source and clock-owner inventory qualify logical structure;
physical landing coordinates and native pair closure remain OPEN.

The geometric model has a1209.6×648 outline, aspect1.867, all19 child origins on
43.2, at least20µm between bodies and boundary, and a continuous12.96µm parent
standard-cell band. The new actual synthesized standard area6283.16352µm² plus
actual hard bodies322971.4944µm² fills42.006% of the outline. Standard-cell mass
fills40.08% of that band; the earlier8756µm² reserve would fill55.85%. These are
separate raw and placement-band measurements; white space is reserved for
routing. This is a prebuild model, not placement, channel capacity, PG,
pin-access, native-clock, parent-fit, or route evidence.

The additional ROM return/reset landing depths and full-token cost remain
unbound; no zero-cost or implicit-phase claim is made. Eight broad control/reset
registers and73 nonclock driver records remain above32 after the new landing.
The source common reset remains one face stage; no reset qualification is claimed.

| Safe checklist | Current evidence / required continuation |
|---|---|
| 1 Pins/reset | Existing data pin registers; two face reset stages and bounded tree OPEN. |
| 2 Reach | Old unlanded paths failed; exact new endpoint/relay ledger OPEN. |
| 3 Fanout | Operand cone mapped bounded; split, reset, issue controls and ties still FAIL. |
| 4 Depth | Historical448.4ps only; new mapped/native cone depth and pin audit OPEN. |
| 5 Storage | Runtime arrays and ≥3 delay lines require source inventory before gate. |
| 6 Floorplan | Lattice/aspect/body-gap/area model PASS; actual rows, pins, tracks, PG/escape OPEN. |
| 7 Clock | Native pair TT/FF, <=80ps spread and >=.03ns route repair margin OPEN. |
| 8 Schedule | Operand/round copies0 edges; node+1 source/native component proved; reset/ROM/full composition OPEN. |

No critical gate may start until the failed/open checklist items have actual
source and model proof. A final native A0 source/LEF/clock-pin packet goes to
the CB16 owner only after actual closure;121 parent occurrences remain unqualified.
