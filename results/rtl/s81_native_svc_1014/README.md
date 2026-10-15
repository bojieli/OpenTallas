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
