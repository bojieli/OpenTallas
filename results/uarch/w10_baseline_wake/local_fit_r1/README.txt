Read-only actual mapped local-capacity audit; PHYSICAL HOLD, no adoption.

Inputs: preserved d6b8f784 full mapped netlist; actual .78 worker RVT LEF
4eb73f825720d95eba4da455c7b2e7a28e444e88e9d8595d13492cf5eecfc0d1;
worker SS sequential Liberty and unchanged actual 4096x274 macro LEF/SS Liberty.
Selected actual cell LEF/SS Liberty excerpts retained alongside audit.json.
Full raw input snapshots protected under
/home/ubuntu/w10-w18-recovery/baseline_wake/local_fit_r1/.

Each capture bundle is DFFHQNx1 + AO21x1 + NOR2x1 (20+6+6 sites).
Shared BUFx2 control drivers are included in each edge reservation; the global
area union deduplicates them. 130 used west outputs and142 used east outputs
per macro, total1088 distinct capture flops. Two east outputs have no capture.
Exact global site-row alignment gives47 west and52 east rows, superseding a
nominal51-row approximation. 120site corridors overflow those pin bands.
192site/10.368um corridors support the retained named row-bin construction at
50% density. This is a constructive relative cell-site budget, not actual
placement or local signal/clock/PG routing. Repeated shared control reservations
are conservative placeholders, not requests to replicate hardware.

Cell area is already included in fullmap62705.9um2; do not add it again.
The prior617row/170.91um minimum slot model remains conditional. Moving macro
bounds inward to26.352/851.256um with these capture corridors changes neither
RTL nor the committed LEF nor the model latency. No placement file is emitted.

ICG endpoint counts are pre-CTS only. Logic gates see10108/6161/5269/67762
flop clock pins. The largest endpoint load is30213.169244fF vs46.08fF output
max capacitance. Four macro gates each see8.6838fF macroCLK capacitance. The
logic trees require buffers; their sites, slew/skew, power and SS/FF closure
are unqualified. This is not a post-CTS failure or a power/IR PASS.

Replay from the pinned edit worktree:
python tools/w10_capture_local_fit.py \
 --netlist /home/ubuntu/w10-w18-recovery/baseline_wake/fullmap_r2/1_2_yosys.v \
 --lef /home/ubuntu/w10-w18-recovery/baseline_wake/local_fit_r1/actual_worker_R.lef \
 --seq-lib /home/ubuntu/w10-w18-recovery/baseline_wake/local_fit_r1/actual_worker_SEQ_SS.lib \
 --macro-lef physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.lef \
 --output /home/ubuntu/w10-w18-recovery/baseline_wake/local_fit_r1/replay/audit.json

Focused tests:
python -m pytest -q tests/test_w10_capture_local_fit.py tests/test_w10_fullmap_slot_fit.py

Root01a0f65d retains all-port/VIA/EOL/PG escape gate. No P&R or fleet lease.
155.103.253.39 is excluded from new dispatch/reservations by explicit user hold.
