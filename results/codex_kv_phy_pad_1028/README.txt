KV PHY receive pad closure fix

Source bb4cf8b22; baseline main 6132842ff. The previous routed PHY pad
74f971cce9b8 failed TT setup -73.87 ps on 101 endpoints, FF hold -2.65 ps
on 4 endpoints. Diagnosis from KV-KITS-16: padding_ok's 496-bit reduce
(~240 ps) then queue-bank write-enable fanout (~380 ps).

The new form captures 31 16-bit zero flags beside the unchanged dq capture.
The second stage reduces those 31 flags. A registered onehot write pointer
and per-bank pending valid decode replace the binary bank write decode.
put_q predicts wp_hot AFTER the current take: at the next edge it is
exactly vq AND the current onehot write address. It is not an extra delay
on take. Fault/pop/count/credits and output timing remain unchanged.
No clock or interface change. Added cycles=0; latency/model price unchanged.
Resource estimate and timing expectation are in estimate.txt; physical
closure remains NOT RUN and this source alone is not a SIGNED claim.

Smallest mechanism test via ot-run --mem4 --threads4 on intel2, unit
oth-ubuntu-1094531-1793256254: exit0. Nominal old/new lockstep PASS334
edges, 48 ordered full-width payloads, initial5 source credits/downstream4,
queue5/full longstall, padding-invalid, ghost-credit, overflow and reset.
MUT1 payload flip caught by old/new data comparison (mutant.log). Reference
is the exact pre-change file, renamed only at the module declaration.
Run command: bash results/codex_kv_phy_pad_1028/run.sh.

Next physical step: regenerate qkd_hr_phy_pad from the existing KV-KITS-15
release recipe, replacing qkd_host_rx_pad5.sv with this source before
synthesis; preserve plan pins/outline, seven-stage trunk, seam25/25,
cts-setup-only and two-mode-grt. Run kit LEC, place, render+VIEW and record
GEOM verdict; enqueue fresh kit via autopilot only after review.
