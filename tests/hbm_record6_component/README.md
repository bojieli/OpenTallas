R6 bounded component source generator

This is a separate numerical testbench. The production R-mode guard remains
unchanged. No numerical simulation, synthesis, timing or physical PASS is
claimed by this source commit.

Generate only on a fleet host under the parent's unpinned ot-run admission:

    python3 tests/hbm_record6_component/generate.py \
      --inventory record6_inventory_final.json --front-words front_words.json \
      --operands operands.npz --source-binding source_binding.json OUTPUT

Runtime imports: NumPy; tools/hbm_static/{su_arith_generate,su_arith_compile,
su_programme_compile}.py; tools/hbm_layer_vehicle/layer_images.py and its imports
su_bench, hdc_golden and the hgi_sim package. Use the frozen cached tools package;
do not replace a live runtime package. The generator checks original A SHA,
authentic R, per-bank programme row identities/128-row capacity, all 160 sectors,
24 native bank identities and exact 1280-word coverage. Second-episode input is
an exact power-of-two scaling with a separately evaluated FP32 canonical tree.

Compile generated tb.sv with exact scoped_d4g/pgslice.sv SHA32e68, the new station41
module, ROOT_OPERAND qcore opt-in, unchanged qcore dependencies, actual stree
leaf/root and directional relay masters, native q0 VM face/core/body, programme
pslice_c5, host leaf and F20 calendar, CKgen/release and functional PLL. The scoped
pgslice includes its scoped arithmetic/store dependencies; do not also compile
the generic pgslice master with the same top name.

Initial source includes two serialized episodes, actual CP programme installation,
host descriptor rearm and full OLD-sector observation. Source-stage age assertions,
reset-abort/reinstall and causal mutant coverage are still required; this initial
bench cannot qualify the complete grant. Calendar phases/latencies remain source
predictions until the fleet run measures them. Coherent RF physical storage,
clock/reach/fanout/native timing and parent transport H remain HOLD.

The next source revision adds genuine F0/X/PRE age and source-data assertions,
all active lane pin captures, root/scalar age assertions and native fill counts.
Run both the ordinary pair and +RESET_ABORT, which aborts the first prefix at
serial6100, holds reset for four serial edges, reinstalls programme/calendar and
input sectors, then runs the two full episodes. Aborted fills are reported and
excluded explicitly from the two full episodes' expected320 fills.

Runtime MUT values:5 front group held0;6 AA lifetime broken;7 root selection off;
8 missing root-valid;9 RF address corruption;10 class5 three-edge lead instead of
required two;11 full-sector mask corruption;13 omitted second descriptor rearm;
14 omitted programme reinstall (combine +RESET_ABORT). These are candidate
causal controls until actual fleet logs show the intended functional predicate.
No timeout/compile error qualifies a negative. Station-local expression ordering,
feedback and overwrite mutations remain station41's proof responsibility.

Generation also requires --station-ledger pointing to the exact station41
source_ledger.json. This derives all1281 independently evaluated canonical FP32
addition inputs/results from symbolic expression identities, verifies the two
real padding-zero subtrees, and emits adds.mem/adds.json. The bench checks and
logs each real node's OPR1 registered oa/ob and subsequent native LAT6 output,
with operation/station/episode/aborted-prefix identities. Top STATION_MUT forwards
to the genuine station RTL parameter for its three source mutation builds.

Supporting station causal source generator (separate output, no frozen changes):

    python3 tests/hbm_record6_component/station_tb_generate.py \
      --native FROZEN_GENERATED_DIRECTORY --station-ledger source_ledger.json \
      --source-binding source_binding.json NEW_SUPPORT_DIRECTORY

Compile only NEW_SUPPORT_DIRECTORY/station_tb.sv, the actual41-node station RTL
and native FP32 adder/clock dependencies. Do not compile the generated
native_reference_not_compiled.sv. This support bench supplies expected squared
words at the station input, checks actual captured held words, all1281 real
addition A/B/Y identities, fragment ownership, genuine root and two distinct
requests. It cannot replace the full512-lane/native-VM positive. Its manifest
keeps native_capture_binding PENDING until the first actual native positive
lane-pin capture checks/traces are matched to these source-pinned inputs.
