# S81 / HEAD / ROOT child park on explicit Claude reset, 2026-10-26

Root ordered PARK after the explicit usage reset. No new launches or source edits
followed that order. Existing QX source/tests were committed as a WIP checkpoint;
the already-running positive/mutant jobs both completed while collecting status.
No owned jobs remain running. Inherited S81 signal-only GRT was left untouched.

## QX final proof and source checkpoint

Main-based WIP `codex/qx-stateproof-0733@cebcdd878` pushed, based on maincb95b36e0.
Two files: tools/dsrom_qelem_cl/qxpq_cgr_lec.py and test_qxpq_state_points.py.
The specialized CGR helper itself was absent from main, so this is a full386-line
new-helper/test range, not a small patch to an existing main helper. Root must
review that range before adopting it. The inherited baseline helper is from
6bc91ebc92; actualCGR8 source is the inherited s81clr2-qx tree. Do not blanket-merge
the old QX branch or assume this proof adopts its physical clock plan/gb master.

Original terminal UNPROVEN40917 remains intact at epyc1:
/srv/opentallas-scratch2/claude/codex-head0733/qx_alias/{equiv.log,lec_cgr.json}.
It is a solver/point-recipe failure, not an RTL counterexample. Read-only exact
structural analysis of those CGE models found a complete unambiguous60122-bit
FF bijection, zero structurally different next-state/control/reset functions,
identical primary/ROM outputs, and302633 interned operator nodes.

Cause/fix: the legacy bounded equiv_simple flow retained arbitrary/dead/internal
combination aliases and `equiv_struct` omitted `-icells` (thus ignored internal
RTL cells). `--merge-enables` also skipped induction. New state normalization
keeps EVERY60122FFbit and all44true primary/ROM ports (1891bits), compares defined
initial values, clock connections/edge polarity/reset/enable parameters, changes
only formal netnames, then uses `equiv_struct -icells -fwd; equiv_induct -seq2`.
The existing ICG-to-enable and ROM-CE abstraction remains explicit; enablecopies
are structurally identical CLK/ARST/D/parameters. Actual point has asynchronous
reset value1 for the enablecopies, fixed PARAMS/RSTP1. This is the existing
registered-enable clock-gate abstraction, not a new physical clock assertion.

Exact FINAL source-helper normalization, without re-elaboration/cold sourceproof:
- epyc1:/srv/opentallas-scratch2/claude/codex-qxnext-0733/source_normalized/
- positive unit oth-ubuntu-452408-1793037645 COMPLETEexit0.
- positive.log:57041/57041 remaining equiv classes PROVED,0unproven,151.22s,
  peak2803MB,Yosys0.68/38e001a6f.60122original statebits retained before dedup.
- meaningful mutant inverted registered gate-enable next-state D (u_ze_r0).
  Unit oth-ubuntu-452423-1793037645 COMPLETEexit1, CAUGHT54910unproven.
- scope.json records allscope/clock/initial checks and exact mutated cell.
- 7focused fail-closed helper tests PASS: complete-state/ports retained,
  mismatched interface/unpaired/ambiguous state/initial/clock edge/clock source
  rejected. No broad new simulation was run.
- Existing minimum actual bench remains1,773,914/1,806,452/1,849,282active edges,
  zero mismatches; regional-enable mutant377mismatches first85. Retain this
  active-window/clock-gate evidence with the specialized formal proof.

Earlier probes are preserved: root qxnext positive.log (normalized bounded-simple)
and induct.log were intentionally stopped before final method; icells.log is
terminal FAIL54909 without induction; icells_induct.log is earlier PASS57041.
Final authoritative result is source_normalized/positive.log and mutant.log.

Old ownWT /home/ubuntu/wt/codex-qx-0733 still has the documented4-line uncommitted
netname-alias rewrite experiment; it did NOT close40917 and is not a merge source.
New main-based checkpoint WT /home/ubuntu/wt/codex-qx-stateproof-0733 is clean.
No new native source/physical kit was built. CGR+0data edges proof does not price
or adopt qxpq_gb boundary +1GO,737pins; that remains in the combined B2 event.

## ROOT and clock-entry work already merged by root

Maincb95b36e0 includes complete ROOT ordinary driver, compact proof/KEEP receipt,
and native clock-entry check (root independently counted both proof dictionaries).
Functional ROOT:1340/1340joint untrusted hints plus13213/13213actual comparisons,
0different/undecided, no current-state or SRAM/buffer format assumptions; memory
black-box outputs/read-buffer data remain free. Original KEEP3572/3572present,
missing0. Source/tool/AIG/map/hyp/keep fingerprints and read-only paths are in
results/hbm_root_0733/receipt.json with compressed raw joint/actual/hints.
Source branch codex/root-history-0733 final e68031681; driver final2e63f9b13.
Canonical kit lec.json was not overwritten; no cold --reuse/correspondence run.
This is source-specific functional equivalence+retention evidence, not timing.

Clock-entry helper source codex/clock-entry-0733@6d0bddff3 is merged. Unique actual
.ck/.clk/explicit-native-port taps resolve; ambiguous taps/pins and missing pin
metadata fail closed. Native->proposed,tap->native,tap->proposed are all checked,
including orient+trackoffset.28master tests PASS. ActualHEAD five native points
remain realFAIL: A0/A1tap-native30.24um,A2/A3/B6.48um; proposed-centre/native
291.53A/257.538B. No full HEAD analysis was repeated after this helper fix.

## HEAD / B2 physical planning holds

ONE HEAD master static packet pushed codex/head-master-0733@99a84a86a, source
mainb723 tools and heldc923 plan,16types/326parts,actual trackedA/Bpintables.
Results/geom_review/codex_head_master_0733 includes reviewed render/analysis,
rawgates/roads/master and UNFROZEN slices.362paths,198326bits,372roads,468bays,
maxreachgap401.742um,0gaps,bay49.6%,M4/M5peak37.9/49.8%,lotfitPASS in CENTROID
MODEL ONLY. Mesh/IR etcNOTRUN. Earlycore offsets+165.627A/+128.756B, centre reach
319.68/278.824>200, hd_serdes tapinsidePHY remain structural failures. One common
clock-entry/internal-tree/island event is needed. No clock padding/new P&R.
Prior HEAD c3q GRT structuralFAIL/nextpredictorFAIL_NO_BUILD remains as0918packet;
source codex/s81head-0733@9c664aa42. No owned HEAD jobs remain.

S81 B2D3 final source remains codex/s81b2-0733@12a0c04f0 (candidate, noadoption).
Full plan physical/die_plan/s81/b2d3_0733/die_plan_b2d3.json.gz plus event/neighbor
FTledgers. Combined deltas +4bk_sel->s_4S_C,+1reverse,+1seqhost->bk_sel,+4tp
bk_sel->s_7S_LP; +2egress stages/276payload+epoch. Token price remains OPEN per
last authoritative lane state; flow_tokens notified, no summed457-140 claim.
Actual M5/M7+PG/via capacity, epoch source,7coreface failures/native rebuilds,
Gb+1GO and masterclock/commonfactory gates still required before route/freeze.
BF narrow source codex/bf-ready-0733@7bd7b9b3b remains source/bench-ready, notphysical
closure. TXV1 structuralFAIL12137/189936pairs>405,max1015.5; V2readhub insufficient;
V3per-bank RDL/WDL+midspine distribution/placement with pricedcycles remainsnext.

Inherited S81 signal-only GRT is still NOT a real-clock die gate. Last read at
park: epyc1:/srv/opentallas-scratch2/claude/path-s81-taps-1026/die_g0fix_i50/grt/grt.log
extra36/50,mtime10:46:49PDT; noOT_DONE/terminalreceipt.0clocknets, nofreeze. It was
not stopped/rerun. The earlier requested epyc2unit name is LoadState=not-found,
which must not be misreported as a terminal PASS.
