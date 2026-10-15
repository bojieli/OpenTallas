# S81 service native probability boundary, 2026-10-14

Actual RTL: `ot_s81_svc_probability_pack` and `ot_s81_svc_probability_frame`.
The opt-in `dsfd_svc_c.NATIVE_FP32_PV=1` instantiates this converter immediately
before the actual job/IO path. Type 14 carries one natural attention row of
16 FP32 head values per payload. It becomes type 5, with BF16 RNE and two
natural rows packed per service word. Each header is rewritten to ceil(T/2)
payload words. An odd final row pads the high half with zero. No readiness,
credit, or runtime scheduling port exists. Dedicated input and output face registers enclose the conversion stage.
The fixed accepting-edge latency is three (capture, convert, output); the
compiler must budget all three. Pair outputs correspond to second/final rows;
conversion replaces host rounding in this path. Payload flops have no reset;
reset valid/control owns visibility.

Production shapes T=640 and T=133 passed 387 pack output words and 391 frame
output/header checks. RNE-removal and swapped-half mutants fail observably.
The pack bench also checks an invalid row faults without waiting or rescheduling;
the frame bench checks immediate next-header passage after a final payload.
Reproduce on an admitted fleet host from repository root:

```
bash rtl/dsrom_sys/s81_ph/svc/test/run_probability_pack.sh OUT
```

Recorded final admission: ot-epyc4 `oth-ubuntu-1424220-1792032172`, exit 0.
Only the current `probability_*` logs establish this final source's result.
Earlier p0/p1/p2 logs are historical development receipts.

`tb_dsfd_svc_c` can capture actual score/PV words and pin-cycle transfers with
`+trace=DIR`; `tools/s81_ftok/svc_capture.py` rejects missing, duplicate,
nonmonotonic, malformed, or hardware-fault output words. It writes component
handoff arrays and input-trace hashes. The compiler-assigned input schedule
mode requires `+static_inputs=1 +pv_cycle=N +expected_end=M`; score completion
is checked at N and cannot delay input issue. Legacy random-delay mode remains
component safety evidence. Static mode itself has not yet been simulated.

The service bench supports actual SU probabilities via `+e_file=FILE` with
`NATIVE_FP32_PV=1`, and explicitly refuses a missing file. `native_e.hex` holds
one 512-bit FP32 row (head h in bits 32h+:32). Existing expected score/PV arrays
remain checker-only. `SRAM_MACRO=1` is now forwarded from the slab top into the
quad, attention staging, and selfetch paths. Its full-slab lint is currently
live; this record does not establish mapped-memory numerical qualification.

## Remaining scope

This is not a fully native layer/token result. Real SU output binding and full
SVC/SU iteration, the real controller and peer network, mapped-memory numerical
proof, compiler service timeline, and physical area/CTS/pin qualification remain
required. The historical full-slab builds inject reference probabilities and
peer rows and use the PC controller model. Their arithmetic/component results
must not be presented as native token qualification. The new converter is a real child but has no CLOSED physical view yet.
The die lead assigned its 129.6 x 86.4 slot and exact v20 pins in
`physical/s81_die_pins/v20_svc_native/ingress_layout.json` (d69e94ef3),
with job/IO orientation MX and two short native joins. Assigned-pin CTS pre-route gate completed with zero failures. It measures
2,363 sinks, TT maximum insertion 171.4 ps and spread 20.7 ps, placement
setup +185.5 ps and hold +26.9 ps. Reset-conditioned payload-enable fanout
was removed; remaining warnings concern the assigned slot's 13% utilization
(1,291 um2 logic). Full native top composition/reset/clock remains open.
Exact gate source binding is `physical/ref_tile/s81_svc_probability_native_ref/gate_result.json`;
TT/FF routed pin qualification and DRC remain required.

The unified sizing entry point is `tools/uarch_model.s81_probability_ingress_model`.
`component_model.json` prices the raw FP32 candidate explicitly: T640 sends
643 input words versus 322 legacy BF16 words, adding 321 transport cycles
plus the three-stage flight if exposed. T133 adds 66 transport cycles plus
the pipeline. No overlap, token-rate loss, or free transpose is assumed.
Real source-side BF16 packing is an alternative to evaluate before adoption.
Input accepted on edge C yields q_o after C+2; an upstream registered launch
just after edge L yields q_o just after L+3, then downstream capture L+4.


## Routed probability leaf, 20:13 PDT

The exact assigned-pin probability successor is CLOSED in job
`s81_svc_probability_native_ref-native2-eb1c52d15`: TT setup +157.00 ps,
FF hold +22.16 ps, DRC 0. SS sensitivity is -136.30 ps. Published record
b29719b17, main merge 6fccf1992; local record cherry-pick 45da9bf8e.
Actual routed clock boundary insertion is TT 136.3..152.7 ps (mean145.0),
FF110.5..126.0 ps; all-sink TTmax157.2 ps. No reset/clock waiver.

`routed_pins.json` separately checks the exact requested Tcl center coordinates.
All 1,033 signal names and layers are present; all 1,030 q/q_o data centers
match exactly. Three scalar side pins were quantized by the pin placer:
clk/rst_n/fault rectangle centers are 0.012um higher than the supplied center.
Their actual boundary rectangles must be consumed by the parent pin contract;
the exact-center audit intentionally records this discrepancy and does not
relabel it as an exact match. Full parent clock/reset/raw input seams remain
OPEN. The payload-completion fix and its successor are detailed in
`payload_done/README.md`; those changes do not modify the probability leaf.
