# Tree16 wrapper verdict repair and physical-gate reuse request

Both original daemon jobs NEEDS_RTL because the mutant wrapper printed only six MISMATCH lines and its final grep-PASS returned1. The daemon correctly refused: its committed fail_regex was absent from wrapper stdout. Original raw mutant QTREE16 FAIL MUT=4 bad=9134 checks=19986. No RTL, threshold, expected-failure rule, physical kit or frozen gate artifact changed.

The wrapper now prints the terminal QTREE16 verdict independently and then up to six mismatch details. Replay against actual original positive/mutant logs returns0/1 with both committed pass/fail regexes present. Original raw failure is retained. This branch is a wrapper-only projection onto source146012ea1; the separate64c9feeb0 helper-refresh branch is not used for this reuse request. No P&R or new route was launched.

Exact 624-file consumed-snapshot checks for each gate show the ONLY changed consumed file is run_qtree16.sh. Frozen original gate JSON/manifests are byte-identical. Current source_binding policy rejects that gate-consumed wrapper delta; ROOT must review an explicit compatible reuse path. gate_reuse_request.json is an audit/request, not a substitute gate receipt or automatic waiver. Do not submit until that path is approved and verified.
