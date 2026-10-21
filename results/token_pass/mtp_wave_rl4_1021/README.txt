MTP wave RL4 producer repair, 2026-10-21

Source fix 735d2e8e7 on codex/mtp-overflow-1021 changes only the bench.
The actual dsfd_vm_p2_ep landing queue remains RL=4,D=10. Its input is
ready-latency, so every valid beat is captured regardless of current ready.
The old integrated producer and linked P2 twin used same-cycle ready to
advance payload and held valid while blocked. This exceeds reserved slots
and repeats words when ready falls. Both now qualify emission with ready
sampled four clock edges earlier and advance on every emitted beat. The
unlinked twin drives the core directly and retains valid/ready handshakes.

Original failed smoke+wave records are retained at
results/token_pass/tokfunc_s81_1021/head_mtp_run/wave and remote
ot-gold1:/srv/opentallas-scratch/claude/tokfunc-s81-headmtp/run_1021_0906.
New remote run: ot-gold1:/srv/opentallas-scratch/claude/codex-mtp-overflow-1021/run2
Unpinned ot-run32GB/8threads, Verilator5.050, unit oth-ubuntu-1546441-1792600768.
run1 is a preserved packaging failure (missing ot_secded_cols.svh), not an
RTL verdict. run2 ships that existing include without source changes.

run2 SMOKE PASS: production payload/lanes/station counts; short core busy
parameters as tools/mtp_wave_bench.py SMOKE. 15steps,61emitted,42P2
transactions,267hidden-row parts,191763cycles,zeroerrors. Production
busy-time wave and matched mut_p2l_seg remain LIVE in that same unit.
No throughput qualification claimed from this functional smoke.
