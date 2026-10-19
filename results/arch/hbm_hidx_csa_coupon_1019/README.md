# Bounded HIDX CSA coupon: exact native ownership and TT electrical PASS

Source b8da0b2b6 descends from immutable failure c34a0e781 and structural model
c07103474. This is an opt-in component proof. Production source5af00a1ab,
compiler/clock policy, physical helpers and original failed artifacts remain
unchanged. No whole HIDX resynthesis, placement, CTS, route or gate ran.
Whole-tile reset, SRAM, registered IO, floorplan, SS/FF and parent admission
remain HOLD; this result qualifies only the bounded source/native mechanism.

## Actual structure and ownership

Each of the six pc8 and twelve pc16 operand cohorts retains its original
same-age mask FF and all24 actual selector FF per count bit. TWO complete
useful Wallace networks per cohort each serve12 of those selector D sinks.
Native hierarchical JSON retains36 complete trees,312 genuine FA and132 HA
arithmetic leaves, each with actual useful sum/carry outputs. Unique IDs and
existing keep_hierarchy prevented cross-leaf reshaping; final flat actual
cells and both SAT proofs, rather than attributes alone, establish the result.
No BUF/INV distribution tree, added pin/mask FF, delay stage or output alias
substitutes for these producers. `csa_audit.json` records every arithmetic
leaf, all168 actual count-bit roots and each of their12 real FF D sinks.

Canonical flow is unchanged: existing keep-reg hook, normal synth -flatten
-noabc respecting useful hierarchy, native SEQ dfflibmap, merged exact native
comb-Lib ABC, then representation-only flatten with no optimization. The
pinned image is in image.txt. Native DFFHQN polarity is included in mapped SAT.
507 no-pin scopeinfo records remain metadata; no native pin/cell is excluded.

| Measured bounded quantity | Original coupon | CSA coupon |
| --- | ---: | ---: |
| Native cells |7410|8265|
| Standard area um2 |1086.25374|1151.49924|
| FF / FF area um2 |2616 /762.82560|2616 /762.82560|
| Native FF clock cap fF |1241.909376|1241.909376|
| Nontransparent roots |4957|5837|
| Maximum FF / comb / input loads |14 /25 /27|14 /12 /27|
| Native levels to selector D |11|11|
| Worst count TT arrival ps |707.328003|434.309937|
| That path launch / body ps |54.819 /652.509|44.483383 /389.826554|
| Count setup slack ps |+16.280422|+308.779266|
| Worst native slew ps / limit |474.66 /320|126.87 /320|

The measured source change costs +855 cells / +65.24550um2; FF, actual clock
contacts/capacitance, reset endpoints and count input/output ages are unchanged.
Actual mask operands312 plus payload288 plus selectors2016 =2616 FF. All FF
are the exact native DFFHQNx1. Clock contacts2616 are explicitly counted by
Liberty clock role, with no clock-name exemption. There are no literal or
unknown drivers in this coupon. Physical PG terminals are absent from this
logical graph: this is no PG coverage claim, and no tie repair was needed.

All-driver BUF/INV-transparent native census includes every FF, combinational
and input root and every real endpoint. Independently unchanged strict oracle
counts8570 drivers /19671 logical endpoints, maximum27 and zero violations.
The separately reported288 non-FF gc outputs are the existing internal
combinational boundary before external S1 capture. All2016 selector outputs
are actual FF. The coupon cannot qualify a hardened registered-output ABI.

Each raw first-byte lane mask drives27 real pin FF D (9 compaction+6 pair+12
quad); second byte12. Existing canonical/S1 consumer is explicitly outside the
coupon. Whole-source eb201d9df budgets group loads28/22/16/10 repeated, total
1216 valid FF operands. Duplicating arithmetic inside the existing operand
cohorts adds no raw-mask consumer. Whole-source native integration is still
required; this component proof does not certify the unchanged unsafe parent.

## Actual timing and electrical limits

Native ideal-wire TT STA uses original833ps / setup60ps / hold25ps, with no
clock tree or wire estimate. Count FF endpoint paths are explicitly reported
in sta_all.log, rather than hidden by a faster/global output-path report.
Worst count path body is389.826554ps at full actual12 D load6.705864fF; its
last useful XOR2xp5 contributes69.702438ps, output slew121.782097ps. Whole
worst slew126.87ps is below320. No slew or capacitance violations occur;
worst cap-check slack is+16.33fF (6.71 against23.04fF limit).

`direct_caps.json.gz` records every immediate real native input-pin contact,
including BUF/INV and clock pins, with exact Liberty capacitance. Maximum
native-cell driven ideal-wire cap is7.571468fF. Raw lane input maximum15.088194
fF is a real upstream burden, not a qualified physical driver. These direct
caps differ from the transparent logical endpoint sums in native.json.gz;
for example maximum logical FF burden8.073190fF is not its immediate net cap.
Clock pins stay in the ledger and are removed only by native role for the
nonclock comparison. No native input, output or transparent pin is omitted.

Global worst reported arrival480.846313ps is at UNLOADED internal gc output;
its +292.153687ps slack does not qualify external S1 capture. There is no
FF-hold/SS/minimum-CQ/neighbor-clock/physical reach or maximum-frequency claim.
Actual source-stage edges remain input capture then selector capture; no
pipeline or single-user token-cycle increment is introduced by this coupon.
Full compiler/parent latency and area/clock fit remain NULL, not zero-cost.

## Exactness and causal controls

Fleet Icarus PASS:65536 mask pairs;256 compaction masks with zero plus every
288-bit payload basis; all nine disjoint payload slices,144 pair and288 quad
selector copies:28,451,072 checks. Stable-append reference independently
checks original lane order, exclusive prefix and zero padding. Independent
source SAT proves arbitrary payload/masks, and full native mapped SAT proves
all2304 output bits including all kept FF and QN polarity. Both contain
`SAT proof finished - no model found: SUCCESS!`. No sampled-trace substitution.

Six committed causal witnesses fail semantically: inclusive prefix; reverse
order; adjacent-payload merge; slice8 drop; only selector23 corruption; wrong
CSA carry. The latter fails PAIR_COUNT_COPY_FAIL at mask0000, owner0, count2
vs0. No timeout/tool exception is used as a negative witness. Original full
production3072-record miter and mutant7/8 remain historical, not rerun here.

## Fleet reproduction and limits

All sims/synthesis/native STA ran remotely with unpinned ot-run. The actual
source/map/formal/oracle chain unit oth-ubuntu-1875302-1792443968 on ep8,
16GB/two threads, returned exit0. Actual post audit/TT unit1931966 returned0.
Direct-cap final unit1933959 returned0; final collector ID/log is recorded in
final_run.log. Data-locality directory for post work is the existing out dir,
not a pinned host. Inputs were staged ep6/ep8; no progressing job was restarted.
The first cap-only analysis used a name for reporting; final version uses
actual Liberty clock roles. Both client logs are kept; neither changed source,
synthesis or STA. Exact final all-file hashes are CSA_FINAL_SHA256SUMS.

Native netlist, merged actual Liberty, hierarchical JSON and full raw ledgers
remain on ep8:/srv/opentallas-scratch/claude/hidx-csa-coupon-1019/out, hashed in
the final manifest. Compressed complete native and independent census plus
retained-leaf/source/endpoints are committed here. Local readable artifacts
are /home/ubuntu/artifacts/hidx-csa-coupon-1019/out. No source adoption or
physical-gate permission follows. Next dependency is ROOT review of this
bounded coupon plus the remaining whole-ownership/model coupons, storage,
reset, native clock and registered-boundary closure before any whole build.
