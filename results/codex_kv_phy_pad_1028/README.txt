CURRENT SOURCE: 67522c5e4, registered onehot speculative-bank form.
The old partial-predicate candidate bb4cf8b22/e24b3122f is superseded.
The intermediate pending-valid candidate adec2c6fc was functionally exact
but failed physical preflight: raw in_v had6 loads. Final source uses only
the original vq input capture and registered wp_hot[k] for each bank.
Failures remain in their original run directories; no gate was waived.

Current fix keeps raw1024 capture and the original496-bit padding test.
Queue DATA bank enables are vq AND onehot write address. Validation governs
queue pointer/count COMMIT. A rejected speculative write cannot become a
future valid output: padding/full rejection asserts sticky fault on the
same edge; simultaneous pop sees pre-edge contents; reset clears valid
occupancy. Clock, ports, sampling and output cycles remain unchanged.

Smallest old/new lockstep PASS8766 edges, including all496 padding-bit
positions, rejection during pop, fault/reset and valid post-reset words;
MUT1 payload flip caught. Original48word legal longstall/credit/overflow
cases also pass. Logs nominal_spec.log/mutant_spec.log cover the same
speculative mechanism; final valid-input capture fix reran identically.
An initial extended bench hit the old100us watchdog; the200us bench bound
accommodates the known496 extra cases (no RTL fix for that harness issue).

Fresh normal hr_face_ports: post rc0, mutant rc1, emitted_v rc0;
0 logic/dropped/feedthrough/multi-input paths. Actual CORE_PREFLIGHT PASS
both1_2_yosys.v and1_synth_odb.v:1577/1577 ports,0 errors. Final kit
hashd243d1cfeca8bf5e:4776 clock sinks (+2 versus old), same centre-entry
sevenstage trunk, same seam25/25, outline86.4x95.04, M5 ceiling.
Place+kitLEC IN PROGRESS, phy_pad timing/signoff NOT RUN.

Estimate: late validation logic + data enable fanout (~380ps in old path)
removed from2640 queue DATA write enables. Raw496bit validation remains
on small control cones. Expected gain exceeds TT73.87ps deficit; actual
routed timing still required. Extra effective state2FF (onehot5 vs binary3),
no additional storage, no throughput/latency cost, added cycles0.

HISTORICAL FIRST CANDIDATE (retained receipts follow):

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
