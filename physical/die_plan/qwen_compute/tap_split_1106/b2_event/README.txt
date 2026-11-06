Conservative B2 affinity shared support, source f87028ff0c, default OFF.
No plan/POR/RTL/SDC window change, no new stages or source budget relaxation.

The source keeps each already same-tap consecutive register run indivisible.
It joins only complete runs within max128 members, existing200um radius and
existing1200sink capacity. A run that cannot fit stays unchanged. Thus B2 may
remove boundaries relative to the provided A density assignment, never add one.
Exact scalar/matrix delay bits and terminal q remain supported. The narrow
literal vm8q CROM relay pairs crh1->crh2,crl1->crl2,twl1->twl2,twh1->twh2 are
individual-bit groups. Source RTL qfd_dv_s8_vm8q_rp1.sv141-153 wires each stage2
fromstage1; actual FF worst crh87 data path is retained east_event/actual_worst_ff.rpt.
No whole vector or source wildcard group. Actual captured register clock pins
must remain positive DFFs, same instance/master, on the same original direct
root source family. Hard pins and gate/mux/inverter clock descendants excluded.
Data/reset/ICG/test-CE/master/placement/netlist semantics untouched.

Seventeen focused Tcl/plan checks PASS, including indivisible-run refusal,
literal per-bit paired-register positive/negative identities, scalar/matrix
terminal q, gated-gap refusal, cap/radius and changed source/master/identity.

CBN actual retained3_place, measured A97 baseline -> B2:
E5 /srv/opentallas-scratch2/claude/codex-qc-tapsplit-1106/canary_cbn_f870
8GB/2T unit oth-ubuntu-4175404-1793978406 exit0;5313joinedsegments,
15400CLKmoves;348544instance/master/pose and1288523otherpin/netrecords unchanged.
Maxload1049->1200;maxjoinedreach199.988um;27776adjacentdelayedges,
cross-tap13496->3403,10093removed,ZEROnew boundaries vs measuredA97.
Separate ORIGINAL28PORTS cap1200 control -> A97:crossings5899->13496,
1229removed/8826introduced byA. These A changes are not credited toB2.
This28port control is an assignment experiment, not the original CTS timing map.

EAST SUc actual retained3_place, own measured A81 baseline -> B2:
Intel2 /srv/opentallas-scratch2/claude/codex-qc-tapsplit-east-1106/canary_f870
8GB/2T unit oth-ubuntu-3121046-1793978494 exit0;547joinedsegments,
2932CLKmoves;359875instance/master/pose and1416036otherpin/netrecords unchanged.
Maxload1134->1172;maxjoinedreach199.720um;6139adjacentdelayedges,
cross-tap1336->319,1017removed,ZEROnew boundaries vs measuredA81.
Actual worst crh87 stage1 andstage2 already share proto_clk27 underA81 and
stay there underB2. Its structural assignment improves with density A; B2 is
not falsely credited for that particular move.

Exact per-register instance/master/source/stage/tap/xy groups are retained in
each output ot_tap_chain_groups.tsv. All A/B full snapshots retained there.
Reproduction/audit scripts included; no keep-or-source semantics weakened.

Both actual affinity_geometry.png renders viewed PASS-COND: current original
macro channels, assigned groups within existing radius/capacity, no newA-relative
boundary. Lines are assignments, not wires. No CTS, PG, route, hold, parent/native
or sign-off credit. Remaining319/3403 boundaries require ordinary physical gates.
Coherent current parent/reset/START/provider/native integration still precedes
physical adoption; hardened CBN currentgeometry requires its own fresh inventory.
