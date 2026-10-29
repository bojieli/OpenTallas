# S81 continuation 2026-10-28 23:40 PDT

Candidate plan_s13 repairs the shared serdes__t1 reset entry at its source and recomposes the existing S81 observer/monitor network. Base DIE-S81-19 f3bac9b5e9, plan_s12f804dcbe81c51. No RTL/data-lane-cycle changes.

reset_site.py uncomposes the existing landing cohorts, moves the t1 entry from E y1074.016 to E y460.576, then calls the unchanged shared composer. The original macro-pushed parent reset output sits near W y460.960. All current instances of the shared type use the same new entry. Wavefront trial: unreachable1->0; lk_WN1 reset hop630.3->215.0um, release90->89; lk_ES0 release83->84; maxrelease101 unchanged. The recomposed monitor uses those new release dates.

Output intel2:/srv/opentallas-scratch2/claude/codex-s81-2340/plan_s13.json sha2560c3ab20b31c59124bd2bd12d09351b2bd499b34f92b40c7d2c8d95a382841d08. Manifest physical/die_plan/s81/bind/asbuilt_b178_coll_s13.json (s12 semantics except new sidecar path). 204 types vs205,2306ports,1700infraedges. Bootready500vs502;18bandfailures unchanged;maxmonitorhop378.048um. Data lanes identical873,sum11948. G0C/review in progress; no route/freeze/signoff claim.

Inherited go16 physical collection epyc2:/srv/opentallas-scratch2/claude/die-s81-18/go16: GRT0TT/FF; spice_edge declaredTTsetup334.97/FFhold-288.93,view18.66/-570.61. W180kitwindow needs239.20,residualFF-59.20/68pairs. Duty94/8501FFoutside45-55%,max56.31%,noMPW;26topology-edge delays>450ps (not physical lengths). Stagecal refit RMS7.49TT/6.73FF. CA postprocess still livePID1797403 at23:48; no duplicate job. Root causes remaining: local tree/window mismatch, unqualified core-view insertions, duty and long physical legs.

Correction: edge_stats.py subtracts OpenSTA node arrivals; thresholds are ps, not um. Independent GEOM actual parent_of/sites census finds8 bufferlegs>450um (7x457.38feed,1x653.4local),0taplegs. No route or repeater decision used the mistaken delay interpretation.
