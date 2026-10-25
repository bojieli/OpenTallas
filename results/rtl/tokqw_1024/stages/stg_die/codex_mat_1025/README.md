# Bound S8 matrix schedule repair, 2026-10-25

QKV and OD scheduling repairs qualified on the production-K layer-0 cuts; one-round LM merge qualified. GU full readback remains in flight. Source parent: claude/tok-qk-s8a-1024@8b3d9f511.

The bound west-row L9 pair heads W5/W3/W1 have no neighbour input.
The old slice2 ownership table tried to finish their L9 reductions there,
so only east-row QKV receivers produced results (384/768 exact words).
Bound receivers are chain positions 1,3,5,6,8,10; sender = receiver xor 1.
The block and arithmetic tree order stay unchanged. Slice2 ownership stays unchanged.

The bound station rejects configuration while either near/far words arrive.
Near words precede far by 14 edges; arm 20 edges before the first producer far
word, including all running-K prefixes. The previous six-edge arm landed among
the running words. The ctl own_ch and fdn ch_dn_o are outgoing registers: the
measured far-to-AR latency includes two edges after local station r_v.
The inter-round reconfiguration guard therefore uses measured latency minus
two, keeping the previous result complete before loading the next config.
This is a scheduling correction; no RTL or arithmetic latency changes.
The first producer delivery remains at the requested matvec edge; STN commands
move 14 edges earlier. Final composition must account for any preceding-op conflicts.

Tests reuse the compiled fixed-RTL 12-slice FACE3 binary on intel2.
Run root: /srv/opentallas-scratch2/claude/codex-s8-mat-1025.
Production K: QKV 8, GU 32, o 2, down 6.
OD positive PASS 515/515 with strict status clean, both framed 256-word AR messages, zero collisions, span1555. QKV PASS769/769,48/48 VM writes, zero missing, span445 and strict status clean. Drop-last-K negative control FAIL1/769 (768 value mismatches plus busy status), as required. GU remains in flight.

Failed diagnostic: od_v3, pre-arm17, zero extra guard: value/edge/framing
checks 515/515 exact, but strict station status FAIL. Preserved separately.
od_v4, pre-arm20 and far-to-AR guard: refused one edge before simulating
(land1306 < previous-results1307). Local-result guard candidate is od_v5.

Additional compiler repairs: the vector role assertion and calibration probe
follow actual bound Q receivers (first probe1, formerly2). LM only clears
actual receivers and emits root0 only if it has a candidate. Bound root0
is a sender, so all6 candidates arrive remotely, with root AMNB6 unchanged.
Clearing nonparticipant senders would leave their MU state open forever,
faulting the next token clear. The source scalar core counts local and
remote candidates uniformly. One-round, six-receiver LM probe and AMNB5
negative control are running; the full25-round head has not been rerun.

To reproduce the minimum LM probe, copy lm_minimum.py to the run root beside tree/, then run with DV2_S8DIE=1 and argument lm_min or lm_min_mut; each work dir reuses the fixed-RTL obj_n12 binary.
