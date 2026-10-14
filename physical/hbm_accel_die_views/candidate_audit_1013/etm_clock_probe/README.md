# Real ETM clock-reference experiment

Admitted through ot-run (4 GB, 2 threads) on ot-agidock128; all four STA commands
exited 0. The source ETM is copied byte-for-byte from the published hbfd_rly8 WE
TT view. Its explicit ck min/max tree rise values are 44.16697/45.71592 ps.
`real_stripped_tt.lib` removes only those two tree timing groups.

`real_raw.log`, `real_stripped.log` and `real_final.log` are byte-identical.
All retain -210 ps inter-clock uncertainty in both crossing directions and
physical clock source latency 150 ps. OpenSTA therefore does not subtract these
tree values from propagated-source-clock I/O timing in this HBM flow. The final
production constraint generator preserves physical phi-R and treats explicit
ETM tree paths as diagnostic metadata.

The superseded add-back run `real_corrected.log` shifts launch source latency to
195.71592 ps and capture to 194.16697 ps, decreasing each setup slack by 1.54895 ps
on equal views. On the controlled synthetic model with tree values 40/60 only
at b, the same add-back decreases b-to-d slack by 60 ps and increases a-to-b
slack by 40 ps. These changes are spurious reference offsets, not a routing fix.
The raw/corrected synthetic sources and logs are retained as counterevidence.

Do not generalize this result to S81's network-latency constraints, ideal clocks,
or a different OpenSTA version without an equivalent numerical experiment.
The original four-cell probe remains separately preserved and limited in scope.
Remote scratch was deleted after preserving source, logs and SDCs.
