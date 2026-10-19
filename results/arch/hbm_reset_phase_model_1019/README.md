# HBM reset phase feasibility — finite native MODEL, fixed age REFUSED

The exact two-positive-edge station has **no established fixed release age**. Native tables plus the proposed forwarded-clock topology do not establish its asynchronous removal contract, and a zero-delay source bench cannot establish it. The alternative below is a concrete source proposal only. Neither alternative has measured TT/FF phase, routed RC, legal rows, PG connectivity, or a compiler release age.

This packet consumes the compressed final 154ae602c tree (2,263 transport stations, 494 face pairs, 810 forest pins, maximum depth179). It does not reuse the rejected3,685-home prototype_model.json counts. The source PLL/hb_ckgen ancestry, downstream2,983 contracted row children (3,793 total HBM reset pins), row lag/head offsets, and global first-use ownership remain part of closure.

## Native evidence and domains

`native_tables.json` records every actual timing arc, conditional `when`, table axis and finite min/max for BUFx12f, DFFASRHQNx1, INVx1, INVx6 and TIEHIx1 at TT/FF, with exact Liberty hashes. Units are ps/fF. `inputs/setRC.tcl` is an immutable copy from the existing native platform-input snapshot; it gives M6 R=.0118796kohm/um,C=.187426fF/um; M7 .0125096/.162979. Historical calibrated .014/.105 is shown separately and is not substituted as this corridor's measured RC.

Native DFF equations remain QN=IQN, next_state=!D, preset=!RESETN, clear=!SETN, clocked_on=CLK. Both async controls retain their actual constraints; SETN is tied high. RESETN recovery grid extrema TT[-69.8242,-13.5105]ps / FF[-53.1152,-9.72729]; removal TT[23.6533,88.9908] / FF[17.4588,67.5064]. RESETN low-pulse bound reaches321.045ps at both corners. CLK high/low minimum pulse bounds also reach321.045ps. These are finite *grid bounds*, not values measured at an actual station load/slew.

The CQ grid is clock slew5..320ps and output load.72..46.08fF. FF1 QN driving INV1 has only.619928fF TT/.683716fF FF intrinsic input load, below .72 absent actual wire. Clock INV1 driving one native FF clock has .462899/.503152fF, also below .72 absent wire. No min-CQ or clock-inverter delay is inferred by extrapolating below those domains. SC2 nominal CQ is not used. Large-grid transition maxima exceed320ps for some combinations, so table membership alone does not prove composable slew. Restricting the actual operating envelope remains required.

## Exact existing station and finite refusal

Current station is BUFx12f(A=clock_in,Y=clock_out), FF1.D=1, FF2.D=INV1(FF1.QN), FF1/FF2.RESETN=upstream_reset_n, output=INV1(FF2.QN); both FF clocks are clock_out. Every RESETN deassertion must be checked against *both* FF clocks. A forwarded clock reaching a child after its reset can allow the same numbered source edge to capture release. A digital simulation that reports a different edge is not evidence for this physical contract.

Let Dmin/max be genuine launch-clock→release delays including CQ, output driver and reset wire. Let g be the time from launch edge to the intended next capture edge, with actual unwrapped edge identity. For every relevant FF and corner the sufficient aperture is:

`Dmax + recovery + 60 <= g <= 1024 + Dmin - removal - 25`.

There are also data setup/hold, pulse-width and slew/domain constraints. The existing two-positive-edge scheme intending to exclude the same forwarded edge sets g=1024+delta. Across the entire native grid, even before wire, CQfall+INV1rise grid minima are59.22345ps TT /41.67046ps FF; combining the conservative removal maxima requires delta<=-54.76735ps TT /-50.83594ps FF. This broad-grid sufficient contract cannot certify a positive-delay forwarded clock. It does **not** prove every narrower operating point impossible. Actual min-CQ, wire minimum and correlated phase extrema are NULL, so fixed-age admission is REFUSED.

## Real RC inventory changes the proposed source sizing

`trunk_rc_model.json` contains all2,263 stations ×2 corners for each RC scenario. It sums recorded child polylines plus3um contact allowance per child rather than applying only the longest wire. Maximum summed trunk branches are708um. Candidate M6 capacitance reaches135.909244fF; M7 reaches118.600768fF. Existing INV1 max cap46.08 is exceeded in2,503 M6 and2,386 M7 corner-station rows; the historical .105 model still has176. These are candidate branch-wire MODEL violations, not measurements of existing routed metal. Local face→810 sink routing is not included, so these are not a complete supply/signal qualification.

INV6 max cap368.64 covers all modeled trunk totals without pretending it solves timing. The conservative lumped RC upper bounds reach585.056ps M6 /539.434ps M7, before CQ/driver delay. This deliberately bounds all branches as one line; it is not per-pin Elmore and cannot be treated as actual arrival or a minimum-delay bound. Exact branched RC and clock/reset common-path correlation could narrow it; no ideal matching credit is taken. Using the entire native delay grids with these pessimistic RC bounds gives no useful guaranteed half-cycle aperture. A stronger buffer alone therefore does not admit the design.

## Genuine half-cycle candidate with stage-owned release

A candidate station would retain native BUFx12f clock_out, then:

- FF1 uses INV1(clock_out).Y, a genuine negative-edge source capture; FF1.D=1, FF1.RESETN=upstream_reset_n.
- release1=INV1(FF1.QN); FF2 uses positive clock_out, **FF2.RESETN=release1**, FF2.D=1.
- output=INV6(FF2.QN); all SETN pins remain tied high.

Simply inverting FF1 while retaining raw upstream RESETN on FF2 is refused: FF2 still receives a positive-edge asynchronous reset release. The candidate deliberately changes the release equation. Stopped-clock assertion propagates upstream low→FF1 preset→release1 low→FF2 preset→output low, with real async arc and wire delays. Release1→FF2 RESETN is a local negative→positive half-cycle check; output→child FF1 RESETN is a positive→negative check across the trunk. Every face pair needs the same explicit treatment, including its downstream native polarity/clock and frozen row offsets. FF2.D is constant, so an unreset data path is not substituted for owned reset release.

If h is the actual source high fraction, source positive→negative separation is1024h plus clockINV delay and native branch phase; negative→positive is1024(1-h) minus that inversion delay, with local buffer/clock pin differences included. Use each separation as g in the aperture above. Native min pulse requirements must hold after inverter rise/fall asymmetry and duty distortion. No50% waveform, zero skew, zero clock delay or borrowed serial/stream phase is assumed. The source PLL's additional native BUFx12f input is2.34288fF TT/2.60175fF FF before actual wire; its PLL phase/drive contract is absent.

Even this topology cannot assign a deterministic source-relative age to arbitrary-phase raw POR deassertion at the root FF1. Root POR must have a genuine specified release aperture, or remain an explicitly asynchronous synchronizer with variable latency and no fixed compiler age. Per-station half-cycle labels also do not remove accumulated forwarded clock insertion: the complete179-depth clock ancestry must be unwrapped to source edge identities. Thus the old conditional362-edge price is not replaced by an invented181-edge compiler price.

## Cost and smallest next prototype

Applying the candidate to all2,757 transport+face pairs retains5,514 ASR FF,2,263 clockBUF and2,263 tie cells; it adds2,757 clockINV1 and replaces2,757 outputINV1 withINV6. Counts become5,514 INV1 +2,757 INV6; total native area3,345.89130um2, delta321.57648um2, new PG term bindings36,622 (delta5,514). This excludes any further driver, clock, hold or row growth discovered later. The largest two-pair coupon adds.23328um2 versus the compressed reservation, equivalent to.864um summed one-row cell width; the prior8.424um body has no automatic fit approval. No placement or PG binding is claimed.

Native FF clock capacitance remains2552.425086fF TT/2774.380128fF FF (the exact machine-readable cost is authoritative). ClockBUF outputs replace one FF1 clock load per pair with INV1 input: +432.928953fF TT/+497.814948fF FF across all pairs, while every FF clock load is still paid on inverter outputs. Adding actual clockINV input pins to the sibling exact-current clock-pin inventory gives9,563.504022fF TT/10,547.145390fF FF total new primitive clock-input capacitance before wire. The tie source now drives FF1.D,FF2.D and two SETN per pair; maximum local two-pair tie fanout8. Reset output changes from two RESETN per child to one child FF1 RESETN, with FF2 reset separately owned by release1. Full native transparent all-driver census, all clock pins, actual wire/cap domain and mapped tie loads remain required.

Minimum NEXT proposal for separate ROOT review: one real source station, two transport stations and one face pair with both exact-current and candidate equations as distinct default-off vehicles; preserve production bytes and frozen graph ownership. Prove stopped-clock assert/cold unknown/reassertion/min pulse/phase aperture and causal wrong-polarity/missing-INV/raw-FF2-reset/same-edge/ownership/fanout/reach controls. The sibling currently implements only the already-authorized exact-current functional bench. The candidate has no RTL grant here. Future physical prototype must first replace NULL load/clock phase/rows/PG/OBS with exact native evidence. No synthesis, OpenROAD, placement, clock forest or production Liberty change was run.

Finite extraction/model ran unpinned via ot-run,2GB/1thread, ep8 unit oth-ubuntu-2262848-1792448965, exit0. The table outputs and source remain immutable. Result: SOURCE MODEL/refusal with a priced alternative, **physical HOLD / compiler age NULL**.

Checklist before any future engine: native face capture SOURCE MODEL; <=405um reach inherited conditional geometry; <=32 transparent fanout requires revised mapped census; logic/slew/native timing HOLD; no indexed payload storage introduced; actual rows/one band/PG HOLD; real clock duty/spread/boundary HOLD; compiler startup age NULL. None is an engine grant.
