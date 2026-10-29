# S81 continuation 2026-10-28 23:40 PDT

Candidate plan_s13 repairs the shared serdes__t1 reset entry at its source and recomposes the existing S81 observer/monitor network. Base DIE-S81-19 f3bac9b5e9, plan_s12f804dcbe81c51. No RTL/data-lane-cycle changes.

reset_site.py uncomposes the existing landing cohorts, moves the t1 entry from E y1074.016 to E y460.576, then calls the unchanged shared composer. The original macro-pushed parent reset output sits near W y460.960. All current instances of the shared type use the same new entry. Wavefront trial: unreachable1->0; lk_WN1 reset hop630.3->215.0um, release90->89; lk_ES0 release83->84; maxrelease101 unchanged. The recomposed monitor uses those new release dates.

Output intel2:/srv/opentallas-scratch2/claude/codex-s81-2340/plan_s13.json sha2560c3ab20b31c59124bd2bd12d09351b2bd499b34f92b40c7d2c8d95a382841d08. Manifest physical/die_plan/s81/bind/asbuilt_b178_coll_s13.json (s12 semantics except new sidecar path). 204 types vs205,2306ports,1700infraedges. Bootready500vs502;18bandfailures unchanged;maxmonitorhop378.048um. Data lanes identical873,sum11948. G0C after staging the plan-relative source sidecars:20errors (was24),12cuts+6PGdomain+2unsigned>400ktypes. All4reset/monitor reach errors removed. Full plan render personally viewed; no route/freeze/signoff claim.

Inherited go16 physical collection epyc2:/srv/opentallas-scratch2/claude/die-s81-18/go16: GRT0TT/FF; spice_edge declaredTTsetup334.97/FFhold-288.93,view18.66/-570.61. W180kitwindow needs239.20,residualFF-59.20/68pairs. Duty94/8501FFoutside45-55%,max56.31%,noMPW;26topology-edge delays>450ps (not physical lengths). Stagecal refit RMS7.49TT/6.73FF. CA postprocess still livePID1797403 at23:48; no duplicate job. Root causes remaining: local tree/window mismatch, unqualified core-view insertions, duty and long physical legs.

Correction: edge_stats.py subtracts OpenSTA node arrivals; thresholds are ps, not um. Independent GEOM actual parent_of/sites census finds8 bufferlegs>450um (7x457.38feed,1x653.4local),0taplegs. No route or repeater decision used the mistaken delay interpretation.

## Actual reach17 trial

Reviewed geometry19ab10cb5/510ac51ec, runner799654bb3: TT+FFGRT50 completed00:07:37 PDT on epyc2 unitoth-ubuntu-2747230-1793257465. GRT0both;actualphysicalmax403.272um,0>405. FFduty94->4/8501,max55.135953%;TT0,max52.153624%;MPW0,minpulse373.7175ps>libtablemax321.05ps (independent GEOM rawcheck). All8501sinkpolarities preserved;22inverters on10edges;1588tappaths+even2/4clockstages;0data/tokencycles.

Timing remainsFAIL: FFkitwindow180needs316.93 (go16needed239.20); viewTTsetup-100.64/FFhold-680.05 with1696missingcoreviews. The localbk_sel653umspan'sA*bypass+4inverters was inserted AFTER DMEbalance, so delay is not priced by localbalancing. SharedFLOWclock_tools owns one coherentphysicallegobject used byDMEcost+exactexport; smallbk_selcouponfirst. No adoption/freeze.

Four remaining duty misses share r105_2's351/48.06um inverterpair, forced by a350um-highhardcore; midpointlegalchannel is41.6um sideways. reach18 geometry-only cap350 candidate fixes all26remaining>350edges with52eveninverters andglobalmax349.812um. No route: timing-awarelocalrebalance first. Three candidatepanelPNGs retained, NOT fullyreviewed/eligible.

Cut allocation estimate (no plan adoption): explicitFTshare0.25->0.5 on23affectedtypes removes12visible plus13shadowed cut failures at unchanged0.6 limit;worst1.023->.5957. This is only a track-allocation estimate. Actual reservedM4-M7tracks plus remainingcore-link/glue demand must be proven before adopting; no budget/capacity waiver.
