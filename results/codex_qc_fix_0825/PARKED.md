# QC takeover parked on explicit Claude reset, 2026-10-29 09:04 PDT

No engineering, P&R or new jobs after the reset. All inherited jobs remain untouched.

## Branch and coordination

Own sparse WT `/srv/opentallas-scratch/claude/wt/codex-qc-fix-0825`, branch `codex/qc-fix-0825`.
Base `claude/qc-fix-2-1029@c45ab5e297`; this unpublished base also includes shared macro-pin read-only-anchor opt-in
`0e115b17c`. Do not accidentally merge those shared changes as part of a results-only merge. Own earlier result
commits: `8fa2d2a3a`, `b63b2a2e2`, `9110fe6ed`, `e037ebcb9`; final park commit follows this file.
Untracked native dumps/diagnostic plots remain safely in this own WT; no other agent WT was edited.

## BTAB inherited jobs: both still LIVE

intel1 `/srv/opentallas-scratch2/claude/qc-fix-2-1029/kits/qfd_dv_s8x_btab_f3b`, unit `oth-ubuntu-1217062-1793286545`.
Check `tail -20 KIT/run_route.log` and `KIT/run/logs/asap7/kq_qfd_dv_s8x_btab_f3b/base/5_2_route.tmp.log`.
At reset DRT iter~20+, latest progress14 violations (previous23), not a terminal verdict.

F3r same root `qfd_dv_s8x_btab_f3r`, unit `oth-ubuntu-1270172-1793286849`.
FF GRT repair completed (margin15, ~1300 buffers, final measured hold positive); now DRT iter1,6866 violations early.
Check its `run_route.log`. Intel2 original clients: `~/qcfix3/f3{b,r}_route.otrun.log`.
No duplicate route launched. Existing run_kit.sh can return2 on do-gds-merged because SRAM GDS is absent; if6_final
survives, run standalone signoff on an own copy, then routed LEC. Do not call a route exit0 a sign-off.
Required: TT setup/FF hold, 0DRC/DRV, actual insertion and calibrated BUF gates. All missing BUF factors are now
measured on root main (flow_clock `acedd3ef7+947dd4bf1`, BUF8 `9023...`); no proxy is needed.
F2 retained NOT SIGNED: TT+305.76/FF-1.68, DRC1, slew88/45, insertion285.82/227.85. Root causes documented in QC-FIX.

## PROG: stale signed cache was genuinely invalid

The native h800 plan uses OLD s8b fallback259.2x354.24, S clock(35.292,.042), signed-pin file. Its archive is
intel2 `/srv/opentallas-scratch2/claude/autopilot/closed/qwen_compute/qfd_dv_s8x_prog__s8b__6aa7f1fc4d`.
Coverage/support invalidated its releasecache row via existing RETIRED_SIGNOFFS policy. The original signoff lacks
PG check; native census found108 protected clock buffers/216 missing supplies. Original archive stayed untouched.
Own PG-only repaired6_final is intel2 `/srv/opentallas-scratch2/claude/codex-qc-prog-pg-0830/repaired/6_final.odb`.
Unit2066468 terminal. Native census0/408482 open; exact cells/signal connectivity/COMPONENTS/NETS/PG metal unchanged
(`pg_only_receipt.json`). Do not mistake this for current sign-off: independent native image found89 register arcs
>405,max446.364, pin-registerp9032.74. No new STA was run on this FAIL geometry.

### Wide structural alternative: GRT0, but not the selected native interface

Current-wide prototype (354.24x259.2) has a47-hour DRT failure on epyc2 `codex-qc-cores-0815/prog_l2h3_route2`.
Do not kill it. 93% of an899-marker saved report clusters x270..280/y120..140, outside SRAM E pin-column keep-off.
Own native geometry showed528 cells there (104FF+376 combinational INV/NAND/OA). The spread candidate moves only
those376 combinational cells into open E street285..320,max21.87um, leaves allFF/macros/clock/pins unchanged.
Own and independent G1 PASS-COND admitted ONE GRT-only probe: native placement clean, GRT50 configured,0 overflow,
15009nets,434766um WL. Data epyc2 `/srv/opentallas-scratch2/claude/codex-qc-prog-corner-0835/`:
`spread.odb`, `spread_grt.odb`, `spread.guide`, `grt.log`; unit/client2504777 terminal.
Native reach354.73/0over405,pin-registerp9023.11/max27.73, actual own clock driver44.5um. Typed actual ft declaration
verifies0 unregistered pins (legacy ot_isl_ckft/ot_isl_rstft).
No DRT/STA launched. Actual prototype clock is center(177.132,134.46); main-wide plan says S(177.132,.042), while
selected native fallback says S(35.292,.042). Cannot silently swap it into native plan.
A0 helper fit report71b2104 shows wide outline fits hard cores but overlaps15 provider bodies per12SU instances
(180 actual bodies), plus clock reservation windows. Needs one batched outline/pins/provider/clock re-home event.

### Native-contract-preserving alternative: two placement preparations, no P&R

Own intel2 root `/srv/opentallas-scratch2/claude/codex-qc-prog-native-0858/`, source archive5_2_route.odb.
First candidate `native_reach.odb`, unit2847339 terminal:89FF homes moved, register reach446.36->404.51 and89->0,
but p_re was moved too far from its E pin (max155.96), so this candidate remains FAIL; original record preserved.
Second candidate `native_pin_reach.odb`, unit3676935 terminal at reset:354FF moved,max98.766um; no other cells,
RTL, ports, outline or cycles changed. Corrects p_re target to21.6um south (not150um) and places265 south input
FFs within explicit29.5um pin-distance lenses. Source targets/scripts and moves committed in final park packet.
The SECOND candidate has NOT been dumped/rendered/reach-censused or reviewed. Next is native geom dump on that
candidate, full reach + pin distances + check_placement, render/view, then review. Original5_2 has old PG issue:
apply the existing protected-instance PG hook only after appropriate review, before any new physical continuation.
Clock sink locations move here; old leaf routes are NOT valid timing evidence. It needs real local clock routing
and TT/FF timing, not unchanged SPEF. No route/STA has been admitted. Candidate pin density remains the native
old-interface issue, not a waived rule.

## Parallel children and functional integration

`/root/qc/a0` owns `codex/qc-a0-0830`: source fix68204ac61dc moves clock wire declarations ahead of generate.
Native old ICG2 synth had1ICG/0hopFF/0ROM (8RF retained; NKnode retained); corrected NL34ICG/66hopFF/10ROM+8RF,
NK36ICG/64hopFF/10ROM+8RF+node. Source proof `/root/qc_proof` still live, see own packet; no source merge solely
on the old FP1 coupon. NK one V1L placement finished FAIL532captures>405,max657.45,7collapsed relays, reset261.76;
main-gate enable548.53 and NODE408.81. NL original placement still live. Root authorized ONE repaired NK placement
only after a concrete graph-homes analytic+visual PASS-COND plan; it was NOT launched before reset. No CTS/GRT.

`/root/qc/import` owns `codex/qc-import-0824`, latest453353f304b plus parent3c286/2f83. Actual native provider
48,259 cells applied; two first reset FFs moved79.92um, complete actual32514arc reachmax403.698/0over405,
0undriven, native44967cells/44906routes unchanged. Mixed PG185698/185698contacts constructed,0unresolved,
9local groups/20contacts changed. These are own measured numbers, independent NUMBER-CHECK still pending.
Actual PG materialization and provider FF clock access still open; `/root/qc_provider_clock` owns the latter.
Read children's final reset packets for exact running units/checkcommands.

`/root/tokens/qwen` owns current QC functional assembly/bind. Old native abstract import was NOT a functional
asbuilt for d2d_rom/native59/sys_face/tt_ctlm. It is preparing one coherent source event with234/2525 actualnative
CA age differences (aggregate-168portcycles, not an end-to-end price), current3266START, profile3+INNERWIT8/TXD18,
R8 regeneration. Fresh ELAB passed; binder count_strap ABI fixed on three types, bind3live. No physical adoption.

All other QC historical lanes are covered by these successors; no stale waves rerouted. VMR versioning belongs
FLOW. Independent QC A3 vK NUMBER-CHECK completed53bb5b582:43.330/40.581rise,44.463/41.899fall, selected-net mesh
shorts0; old root-cause was an actual M9 short, not coupling. Keep strap_keepout_um0.32 in current native mesh event.
OWNER?: none added. Native/wide PROG and CA consistency remain coordinator event choices, not silent rule changes.
