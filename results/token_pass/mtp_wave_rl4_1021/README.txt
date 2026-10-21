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
busy-time wave subsequently passed; matched mut_p2l_seg remains LIVE.
No throughput qualification claimed from this functional smoke.

Production-busy wave PASS: 15steps,61emitted,42P2transactions,70Markov,
59seedrows,89/89/89hidden-rowparts,2558056cycles,zeroerrors. Full raw
positive logs and builds are committed. Exact remote source closure hashes
cover all66shipped files including headers, generators and released gold.

Matched segmentation mutant: unchanged SMOKE parameters, single define
OT_P2L_MUT_SEG. Existing heartbeat at200000cycles shows emitted0,P2tx0;
matched positive finished61tokens at191763cycles. bounded_progress.py reads
these original logs and independently fails completion at the first fixed
heartbeat deadline after the control completes (200000cycles). Its exit1
and bounded_fail_witness.json are a bounded noncompletion witness. Later
400000/600000 heartbeats remain0/0, consistent with the corrupted high
identity being blocked by the existing P2 transaction identity gate.
There is NO terminal WAVE FAIL claim. The original20M-cycle watchdog and
run2 remain running under unit oth-ubuntu-1546441-1792600768. Final runner
summary/exit remain pending. This bounded negative is not its terminal
simulator verdict. Production RTL and its overflow guard are unchanged.

An additional earlydone case launch crossed the parent no-extra-build
instruction and was stopped immediately: local client3200056, exact own
remote subtree1770879/1770915/1770918/1770921. Partial run3 and stopped client
log are retained; it supplies no qualification. Original run2 was untouched.
No physical actions, main actions or throughput qualification occurred.
