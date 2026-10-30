Entry replay status and concrete current compiler repair,2026-10-30

The old handoff blocker is stale. Main0e75647078 fixed RX held-KS harness;
6/6nativeentry jobs PASS_CUT_COMPONENT,4×817+2×460 strict checks,zero faults/
mismatches, meaningful calendarbit33 corruption caught204 mismatches. The old
nullbit13 missed control remains history. Native jobs already have real515b
HOST words. The later split-layer adapter49f7915d5a/ab386d3e5 handles actual
prog/jobN/host_boot.memh; canonicalBKsink record tokds_bk_sink_canon_1024/
canon_layers.json passes all8control jobs acrossL0/L2/L14/L20 with mutants.
This does NOT qualify current physical clocks or a full token; no rerun made.

Actual remaining software gap: current BoundBoot write-only input emitted
CTL templates but no native PW rows, while legacy entry_boot.compile_jobs
requires legacy Die/ctl_path geometry. New entry_write_calendar.py consumes
actual entry_input_rows, retains every source payload/order/die identity,
and lowers job-local command calendars plus real515b CSR/PW/template words.
Pages contain at most126commands, reserving2rows for eventual actualKIT/END.
Caller supplies explicit issuer-relative first_issue/stride (stride>=2).
Native V ACK remains5edges; it is NOT treated as store-commit/readiness.
No BEGIN,SEAL,KIT,END,KSdescriptor or globalSTART is invented.

BoundControl now omits norm-spacing checks only for commands whose actual
encoded target5 payload agrees with TARGET5 classification. A missing or
mislabeled payload cannot hide a NORM cohort; partial NORMR/GO groups still
block, and existing wrong partial alignment still fails. This enables the
new target5 pages through the existing --native-entry-program source path.

Meaningful narrow validation:13focusedtests PASS, including all3920real
committed input writes unchanged across32pages and15712concreteHOSTwords;
actual emitted template-payload corruption is caught by existing bound_boot
native decoder. Unsafe cadence/rowcapacity/datewidth/identity/duplicate-row
controls refused; norm guard regressions remain blocked. The demonstrated
fixture's original die hash is retained, not relabelled as a current physical
bind. New pages are candidate software artifacts, NOT source-view adoption.
No RTL changed; no new replay or physical job was launched.

Usage with actual same-die entry rows:
 python3 tools/s81_dv/layer_prog/entry_write_calendar.py \
   --entry-rows CURRENT_ENTRY_ROWS.json --first-issue RELATIVE_ISSUE \
   --issue-stride SOURCE_CADENCE --out FRESH_DIRECTORY
Pass jobNNN.json to the existing --bound-control-only --native-entry-program
compiler WITHOUT --retime-native-entry (that switch is for NORM cohorts).
Current bound inventory, selected source timing, host CSR cadence and real
reset/KS receipts remain required before the boot compiler can qualify paths.
All source identity checks remain active. Omitted stage/phase yields no BEGIN.

Known encoded cost:15712HOSTwords,78560localpin-event reservation edges IF
loaded serially at verified5-edge CSR spacing. This is explicit entry boot
work, not a steady-state token-price delta against the old nonexecuting
3920template-only words. Actual source/transport dates,MUconfiguration,
HLOAD/GAIN/store completion,KIT/END/retirement and interpage reload authority
are still missing and are not priced as zero. No hardware cycle changed.

Existing local VP proof reused, not resimulated:
The real prior VP gate's11source/dependency files, including real r0c0 SRAM
and bench, are byte-identical to the selected source. Binder file/preference
selection picks those VP/SRAM implementations;80actual destinations retain
unoverridden measured defaults. No activated conditional guard is accepted.
Intake compares the exact bound transport/inventory identities, preserves the
old proof's distinct die/asbuilt identity, and annotates only local body facts:
VPtarget5pin->itsstorecommit2edges, HLOADlastVP_HWoutput20, GAINlastVP_WL12.
Six negative controls reject missingpayloadmutant, dirtysource, wronginventory,
parameterdrift, incoherentstorefieldage and activatedmemory-faultvariant.

This advances the previouslyNone local VP commit stage. It deliberately does
NOT label last VP output as VN capture/store readiness. Existing HLOAD/GAIN
readiness placeholders remainNone; physical clock/reset phase, XRtarget5
decode, actualper-commandarrival, VNstore and programme retire remainheld.
No old proof was relabelled as a new whole-die proof; compact vp_intake.json
retains both identities and exact stage ranges. The compiler CLI is
 tools/s81_dv/layer_prog/vp_local_intake.py --transport ACTUAL_BOUND_ENTRY \
 --inventory SAME_SOURCE_INVENTORY --proof VP_GATE --source-root SOURCE \
 --manifest EXACT_ASBUILT_MANIFEST --out FRESH_OUTPUT
No RTL cycles added; these are existing formerlyomitted stages, not zero
latency. Scratch fulloutput remains beside sourceinputs for the next compiler
step. A preliminarycomparison against stale remote~/OpenTallas was discarded;
qualification uses actual explicitselectedsource root, where all11match.

Current target5 decode and concrete compiler arrival composition (1030 05:xx)
-------------------------------------------------------------------------
The old compound entry_mechanism source differs, so its decode age was not
reused. tools/s81_dv/xrt_target5_1030 measures selected current XRT1/XRT3
FACE_LAND1/FOREG0/PDSK01234/QDELAYS0, all16SID*5leaf*3DLports. 240writes,
480full payload/row/mask/leaf/date comparisons PASS at833ps. E/W/V ages3
for both wrappers. Real input payload corruption catches2errors; wrong age
catches480errors. Original base/payload/age logs retained. Intel1 unit3796997
terminal0. No RTL changes. xrt_target5.json records exact source hashes.

layer_prog.target5_arrivals consumes matching actual control/VP transport/
inventory identities and this measured stage. It checks selected XRT source,
parameters and conditionals, then computes per-target source-relative VP
store dates and optional TARGET5 command arrivals. Actual80 destinations
from functional c09217/062ef0 retain identity; seqhost-output→VP-commit
range69..221edges. Six unsafe-source/control/payload controls refused.
The explicit synthetic one-command arithmetic control tests lowering only;
actual programme commands lowered0. Existing old86dd input data was never
retagged current. Native jobs remain UNSEALED: current-source entry data,
residency/reload, VN capture, actual root phase and start remain holds.
