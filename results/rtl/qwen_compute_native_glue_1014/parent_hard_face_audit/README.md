# Exact NK hard-face contract classification

This test package reproduces the original `OT_IOFLOP: no pin flop found` on the immutable 85b373696 physical ODB, then tests a source-bound audit on that same ODB. It does not change the parent RTL, any CLOSED child, placement, timing budget, or original artifact. The original failed gate is retained compressed alongside the proof.

The exhaustive audit checks all 2,667 nonpower BTerms: 2,580 exact payload bits, reset_n into sixteen real reset_root data inputs, 83 independent hard clock entries, one own standard-cell clock root, and two actual constant outputs. The hard faces must match exact instance, master, direction and bit, with no additional residual/comb endpoint. The binding rehashes twelve registered leaf source/view files. Actual own standard-cell FFs are never claimed as hard faces; their only exposed port is the ck root. Their internal data/clock timing remains for actual CTS/STA.

All eleven cases pass: the unchanged default reproduces the original refusal; an ordinary actual standard-cell FF output still anchors successfully without the opt-in; the real hard-face inventory passes; missing endpoint, extra residual D sink, wrong bit, unexpected port, changed source binding, changed view binding, changed actual LEF bytes, and own clock feeding combinational logic each reject with their intended diagnostic. Negative ODB changes exist only in disposable tool memory; the altered LEF is mounted from a test copy.

The shared hook candidate is reviewed/published separately by the shared flow owner. Do not enable the kit until that exact hook is published. No OT_OFLOP_ALLOW_NONE is used. An audited hard endpoint is not a channel, wire-reach, PG or timing waiver. Existing held-only dense channel status remains.

Reproduction on ot-epyc4: copy `hard_face_audit.tcl`, `hard_face_binding.tcl`, and the reviewed `io_flop_at_pins.tcl` to /tmp; copy the first two into /tmp/qce-face-audit-mount. Copy `test_hard_face_contract_remote.py` to /tmp/qce-face-contract-tests.py. Run with ot-run --mem 4 --threads 1 --dir the receipt run_dir, using python3 /tmp/qce-face-contract-tests.py. The runner deliberately names the exact immutable ODB rather than accepting a fabricated fixture. Results/logs go to /tmp/qce-face-contract-results.

The authoritative mapped ODB census is 954 actual DFF instances, all on ck. Earlier 2278 is the pre-ABC source bit count; textbook 2308 is an estimate. A proposed source cleanup to943 pre-ABC FFs therefore has no measured physical area/clock benefit until mapped comparison.
