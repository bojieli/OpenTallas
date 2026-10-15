# Actual payload completion, 2026-10-14

The real `ot_s81_svc_job` embedded in `dsfd_svcio_job` previously marked an
END source complete at its result header. A job could therefore report done
while its terminal payload was still leaving the actual service output pins.
The corrected parser retains END/tag/source until the last valid payload beat.
Zero-length terminal frames complete at their header. No data-ready signal,
credit, retry, or variable-time scheduling was introduced.

The small actual physical job leaf gate passes two jobs with concurrent source
frames, fixed payload gaps, and a zero-length terminal frame (`d0.log`).
Restoring the authentic old header behavior fails early (`d7.log`); completing
at the first source also fails (`d5.log`).

The four-slab actual physical IO integration passes 40 jobs and 644 frames
(`physical4.log`). The long terminal-frame case passes 40 jobs and all 620
frames in 4,329 cycles (`long64.log`). Its authentic old-behavior mutant still
passes every frame comparison, but reports done at cycle 78 before the final
payload at cycle 129 (`long64_header_mut.log`). This is the concrete reason a
numerical or frame-count gate could miss the completion defect.

The existing full-slab bench also counted END at the header and then counted
its own legitimate payload as after-end traffic. Its source is corrected to
record final payload and to reject early job done. Existing immutable live F/H
builds retain their old checker and are not silently relabeled.

The unified completion model prices 48 retained metadata FF, no new ports,
memory ports, or clock roots. `../completion_model.json` records the exact
static calendar and one completion-observation edge. Output-pin completion
still requires compiler accounting for downstream SRAM write visibility.

`source_scope.json` proves the `dsfd_svc_join` body unchanged from 204913992;
only the changed physical job leaf needs a successor route. The candidate
scalar-clock v20 pin file preserves explicitly assigned legacy geometry but
is not equivalent to the separately CLOSED scalar-clock view. New TT setup,
FF hold, DRC0 and clock/reset/pin qualification are required.


S-DIE confirmed at 20:23 PDT: select the explicit v20 legacy q/q_o
rectangles as the new payload-correct job target, with scalar ck/rst; preserve
the current scalar CLOSED view as a separate predecessor. The successor kit
is `s81_svc_payload_job_ref`. This is a new routed result, not a view alias.


## Final timing structure: fixed event stage

The first payload-correct version's placement CTS test measured TT setup
-33.4ps on the completion cone. `pre_route_gate.json` preserves that result.
The final structure registers decoded terminal events before queue bookkeeping.
This adds 48 event bits (96 total new metadata bits), one fixed completion
observer edge, no q/result transport stage and no new memory/clock/IO ports.
The physical tile now reports done two edges after accepting the final output
pin tap; a zero-length END follows the same fixed two-edge observer path.
The compiler must price that extra edge plus downstream VM write visibility.

Final source unit evidence is in `event2/`: two jobs PASS with exact fixed done
cycles; authentic header and first-source mutants FAIL. Four-slab long64
integration passes40 jobs,620 frames,0early/0fault in4,315cycles. That harness
uses a historical credit issuer and behavioural arithmetic stimuli, so its
elapsed cycles are safety evidence only, not production static token throughput.
The actual job and IO RTL is instantiated. The fixed unit calendar has no
credit issuer or output-dependent scheduling. The complete job safety suite also passes seven positive and nine expected-negative cases (`event2/suite.log`). Final assigned-pin CTS now passes with TT setup +75.2ps and hold +27.2ps; max TT insertion231.1ps/spread36.9ps across1,571sinks. Logic depth falls from~652ps to~538ps. Synth std area887um2. The exact assigned slot utilization warning remains; new route TT/FF/DRC0 remains required. See `pre_route_event2.json`.
