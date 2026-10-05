Current S81 stage37 compiler candidate, source only; NOT adopted or executable whole plan.

Source API: CanonicalS81Execution.emit_current_stage_candidate(out, stage=37,
layer=20, expert_ids_by_node=ACTUAL_OWNER_IDS, context=ACTUAL_C8_CONTEXT,
calendar_pricer=dsrom_source_fragment_calendar).
The generator derives resident scopes from the canonical selected stage (19,20),
then preserves both complete source orders including actions/fences.
Current emitted choices reuse the pinned all40 schedules for layers19/20;
runtime expert IDs and accepted token/user/epoch context must still be enrolled.

candidate/parent_dispatch.json is the directly usable source binding:
263 source operations, 68 TP4 compiled FIELD groups across stages35..38;
30 FIELD fragments PER RANK on stage37, ranks0..3 / dies148..151.
Each selected group indexes the SAME offers table and actual program image:
entry/producer_pc are actual native PCs, end_pc=entry+1;
catalogue_producer_id is a separate source-publication identifier.
I7 entry0/producer0/END1; I8 entry2/producer2/END3 in each stage37 rank image.
These are newly packed current-assignment candidate PCs, not live-caller PCs.

Concrete integration fixes for Arch / Planck:
- 203 nonfield/action/fence operations have NULL physical_home/entry/PC.
  Each exact node, existing required_provider, literal source instruction,
  data reads/writes and ordered dependencies is present in source_order.
  Select actual service homes with capacity/port/clock price, then allocate
  native entries through existing emit_nonfield_run; do not assign stage37 by default.
- Every field needs the actual input lease/restore, gather/multicast ownership,
  accepted fragment/retire events and real all-copy drain. 30 is a field-subset
  coverage count, never a whole-stage completion count.
- Native physical source-owned KV/index/remote/allcopy fence visibility,
  C8 write/capture quiet, quarantine/fault and collective busy remain required.
- The actual END source nodes are L19.I114 and L20.I143, layer handoffs.
  Other unit0 instructions are control subops5/6, not END.
  Token/HEAD/global_argmax terminal is outside these scopes; terminal=NULL.
- Model calendar in parent_dispatch.json has explicit sequential dependencies;
  actual prefetch/arithmetic/publication/ACK/restore/drain service cycles are
  unknown, not zero. No composed latency/gain or physical slot fit is claimed.

No RTL, native rebuild, inference, activation inputs, proof campaign or P&R.
Source-check PASS covers pinned program bytes and all272 literal offer PCs/ENDs.
Initial sparse-source import failures are preserved in failures/; neither
attempt emitted images. Corrected source emission terminal-r3.exit is0.

Current REAL completion interface (Planck mainfbd7531ca, default-off):
rtl/rom/wavefront/completion/ot_dsrom_wf_stage_completion_join.sv;
selected parent rtl/dsrom_sys/wfc_stage_completion_parent/ot_v41_rt_die_l20_c8.sv.
Arch binds wf_join_request_v/binding_valid/identity/terminal_entry/producer_pc/end_pc
from the saved actual accepted request and true terminal. Current candidate context
and terminal are NULL, so these inputs cannot yet be enrolled.
wf_join_coverage_valid/wholeplan_complete/coverage_identity must cover this literal
complete source_order plus actual accepted/retired copy and service work; the 30
stage37 field groups alone must never assert wholeplan_complete.
wf_join_visibility_valid/fault/identity/visibility[4:0] requires real continuation,
KV, index, remote, allcopy sources. Existing join retains C8/capture/collective
qualification; no duplicate join RTL or fabricated counter is emitted here.
