# PVFIN r16w frozen review packet — formal geometry approved

The actual gate is WARN with zero FAIL, generated 2026-10-21T16:37:34-0700; original execution ended GATE_SCRIPT_RC=0 and GATE_DONE. Gate source identity is exact_content_snapshot, commit=None retained. Gate start source commit is 2c228c39803f5a1b8a1e8ab577342e915a3a792a. The prepared source branch also preserves the source-specific bench and function proof. No route is submitted by this lane.

Geometry SHA256: **03439f436a6418ac465011c5d05cf36a669ab329328057305a62af817d1fd1ad**.
Shipping source manifest: **527d8e63bb4d9a3bba0949d8ff9b87a39e24a3ebe7aa6d9cdb479494deff7cd5**.
Shipping archive: **51696694cda35f383957acb280fb5a9d0b948b227980b6318ad401c5872153a3**.
Full canonical gate_result.json is separate from scratch_verdict_summary.json. source_match.json records all84 consumed blobs matching the frozen gate; three exact consumed helper blobs were recovered verbatim from the completed gate src, not substituted from evolving main. recovered_gate_helpers.json pins them. They are historical source preservation, not a request to deploy or regress helpers.

Original PNGs copied byte-for-byte to this packet and kit/gate_layout:
- floorplan.png SHA4b56a899c4c2981f50e084c126de99feb77d32c8209ed6891c0011c6c8c49866
- density.png SHAc26e20b0490f4f58cd27a9421fabe687a043e38df89e3244c423ea8bfcfe1488
ROOT personally viewed both original images and described four macros in2x2, broad center/perimeter channels, distributed cells and isolated east-edge hot bins. ROOT formally approved this exact geometry/source packet. The hash-bound approval transcription is FORMAL_REVIEW.json and kit/gate_layout/REVIEW.json. Final routed timing/DRC remain pending.

## Safe-design and geometry checklist

Four real32x128 SRAM macros are51.408x39.96um, placed on the existing lattice at(43.2,43.2),(129.6,43.2),(43.2,172.8),(129.6,172.8). The outline remains259.2x259.2um; no parent-slot growth. Center macro gaps are34.992um horizontally and89.64um vertically. Pin groups retain p0 south/p1 north/output west/control east. Existing RTL pin-register opt-out is unchanged: inputs participate in the same static calendar, outputs are registers; no extra data stage is permitted. Shipping reset lands2boot-only edges plus the original3-edge bounded regional release; first legal start E6 is unchanged. No new false/multicycle path, relaxed uncertainty, clock family, or88ps spread waiver.

## Eight-point cost and behavior ledger

1. **Slot/area:** gross67184.64um2,4macros8217.05um2. Actual GRT instance area42306.9um2, standard-cell area34089.9um2,256981instances/256977standard cells. Raw synthesis GATE_AREA40368.5792um2 is a separate stage/model; original floorplan std_area estimate32049um2 is not relabeled as actual. Full grt_metrics.json retained. No power estimate is invented.
2. **State/storage:** four32x128=16384mutable SRAM bits, same arithmetic/register architecture and actual read/capture/forwarding protocol. No added FIFO, calendar state, memory capacity or hidden storage.
3. **Compute:** sixteen existing FP32 add lanes and sixteen multiply lanes; ADD_LAT7/MUL_LAT6/SKEW1/MUT0. Golden rounding/arithmetic and operand ordering retained; no compute-capacity claim from physical closure.
4. **Ports/bandwidth:** same two512-bit input streams,128-bit rz face and512-bit output stream, existing beat/epoch/valid/control ports. Up to512data bits per port per eligible edge; readiness/static calendar unchanged, no new serialization or bandwidth gain claimed.
5. **Cycles:** zero data/token-age change and zero fault-latency change versus selected SRAM successor; only existing boot reset landing is present. No compiler/parent edge ledger update is silently adopted.
6. **Replication/fanout:** actual prelayout native census PASS180988roots/max32, zero role errors/violations/constant-output bits, pinned real TT/FF Liberty. This is the actual prelayout census scope, not a claim that later physical instance counts are identical.
7. **Clock/routing:** strict80ps rule, boundary2704flops TT399.5..427.2=27.7ps/FF317.4..343.1=25.7ps; all38417clock sinks TT398.5..428.4=29.9ps/FF315.1..343.9=28.8ps. All4SRAM clocks present, zero collector errors, placement-estimated4_1CTS scope. Root38020/insertion428.4TT343.9FF guidance retained. TrialGRT rc0/overflow0/M2usage45.93%,3274s; no finalDRC or extracted timing closure yet.
8. **Programme/functional price and limits:** exact zero-edge window decomposition; function SAT covers all32 inputbits including unsigned wrap, wrong-window mutant refused. Source-specific simulation passes40unstretched+48stretched commands bit-exact, NEG1–3 fault checks, five causal mutants detected, all six manifests identical. functional_source_match.json confirms all gate-shared RTL/memory manifest paths match. These bounded/source-function proofs are not universal physical cold/init or whole-die qualification. Old r15c routed TT-45.36/FF+10.09/DRC0 is retained independently.

## Actual evidence and remaining timing risk

Raw gate, complete source snapshot, clock boundary+all-clock JSON, prelayout native summary/fullgzip, original CTS/GRT logs, placement/CTS reports, grt_metrics and PNGs are local. Functional receipts are ../r16w/{bench,win_proof}; the historical qualified=false fields intentionally remain unchanged, with later gate/native evidence separate.
Raw GRT metrics report setup ws-9.61431ps and hold ws-53.6156ps in that stage's scene; these are diagnostic values, not the final routed TT/FF verdict and not a timing PASS. Hold-guard calibrated trial reached+30ps before later metric reporting. The scene, library/RC and route-vs-signoff contexts must not be conflated. Final detailed route, routed IO-reference TT/FF and DRC still decide closure. No source or child-view alias is authorized by this packet.
