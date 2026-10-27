# HEAD-RTL-4 2026-10-26 (s81_head mesh CRC span, copy-B burst FIFO, die_port_bind STUB rule)

Branch claude/head-rtl4-1026 (HEAD-RTL-3 fe797a6b46 rebased on main 278c7c4e85). Tools run on epyc1 (ot-run), Verilator 5.050.

## (1) CRC coverage of beat bits 300-339: NO gap (proof from RTL, then bench) -- CHECKED
- Beat format (ot_s81ph_link_gbx_safe3, BW 512): [2:0] control, [55:3] reverse frame (own CRC-32), [511:56] gpay (G 456).
  Slots S = 596 = {flit 595, slot valid}, 3 slots in 4 beats, K1 = 140.  Beat bits 300..339 = gpay i = 244..283:
  - phase 0 (t0): slot bits 244..283 = flit 243..282;   phase 1 (t1): slot 104..143 = flit 103..142;
  - phase 2: i 244..279 (r2, rem) = slot 560..595 = flit 559..594, i 280..283 (t2) = slot 0..3 = slot VALID + flit 0..2;
  - phase 3 (r3, rem): slot 420..459 = flit 419..458.
- Flit (ot_s81ph_link_ep_safe4): [31:0] CRC, [594:32] = FPW 563 payload {seq, last, data}.  TX CRC = crc(t_pay[HB-1:0]) ^
  crc(t_pay[FPW-1:HB]) ^ crc(0) over the WHOLE payload; RX checks q_f[32 +: HB] and q_f[FFW-1:32+HB] (contiguous, = all of
  [594:32]) against q_f[31:0].  ot_link_crc32: bit b's mask e_b = step^b(POLY) is never 0 (step is invertible, POLY[0]=1),
  so every flit bit is in the span.  The one non-CRC bit (slot valid, beat bit 336 in phase 2) is framing: a flip drops a
  flit (sequence gap -> NAK/replay) or makes a phantom flit (fails CRC).  No CRC span fix is needed.
- Why HEAD-RTL-3 saw X crc_err 0: its imp[1] window (cycles 5000-5200) lay AFTER the record traffic (400 records at
  >= 7-cycle spacing end near cycle 3,300); idle / empty-slot beats carry no flit to check.  Bench now puts both windows
  inside traffic (imp[0] 1000-1200 bits 96..143, imp[1] 2000-2200 bits 300..339): crc_err_b X=7 Y=5, replays X=5 Y=4,
  retx flits 40/21, lane a 0/0.  The existing link mutant OT_DSROM_LINK_MUT_NOCRC must FAIL (mutant 6).
  No new span mutant was added because there is no span to narrow.

## (2) copy-B burst FIFO in ot_s81hd_mesh_ep_core (closed lsc_r0m untouched) -- CHECKED
- Mechanism: after a lane-b replay the link delivers the held records back to back (lsc_r0m li_r = li_v registered,
  gearbox 3 flits / 4 edges); the shared word port drains 1 word / 2 edges, copy A first.
- Bound (tools/s81_head/mesh_bq_bound.py, cycle model of the RTL decision / count / landing registers): replay window
  N = floor(S/T) + 1 records (all records whose copy-B landing falls inside the stall S), delivered at 3/4 per edge
  while copy B drains at 1/2 - 1/T (copy A, priority, takes one 2-edge slot per T); worst over all copy-A phases.
  Bench point: T = 7 (gap >= 6), S = max copy-B latency 121 - nominal 42 (NOREPLAY run 40/42) = 79 -> N = 12 -> BQ = 7.
  Measured peak (records held + landing in flight) with BQ 32: copy B 7, copy A 1 = model.  BQ = 7 (default parameter).
  Production: position period T >= 8,357 edges > any NAK stall (~80) or ACK-timeout stall (ATOB 1,481 at CH_BOARD 700)
  -> N = 1, so BQ 7 has margin there; S is the measured worst stall of this error model (UNCHECKED for other error
  patterns: repeated corruption of replays lengthens S; an overflow then drops the record and sets sticky ep_fault[10]).
- RTL: per copy BQ x 97-b flop FIFO, one-hot pointers, same 3 edges as the old slot (landing reg, write+count, decision ->
  word register); a landing into a full FIFO is dropped (order kept) and flagged.  Cost ~2 x 7 x 97 = 1,358 data flops per
  endpoint (3 replicas) UNCHECKED area (no synth in this lane).
- Bench mesh_fifo_bq7/ (tools/s81_head/mesh_ep_bench.sh, both directions forced CRC): MESH_EP_BENCH rc=0.
  production PASS: 400/401 records x 2 copies exact, errors 0, no phase-1 fault, Y epf 000 (no sticky fault), peak copy B 7.
  mutants all FAIL as required: 1 copy id stuck, 2 copy-B bit flip (801 err), 3 lane b silent, 4 fault not carried,
  5 NOREPLAY (copy B 122/253), 6 NOCRC (143 err), 7 BQ-1 = 6 (copy B 399/401 lost, Y ep_fault[10] set).

## (3) die_port_bind STUB rule (tools/die_port_bind.py, tests in tools/test_die_port_bind.py) -- CHECKED (unit + wrappers)
- A master that instantiates its own name without a parameter override (unbounded recursion = can never elaborate) is
  STUB, stub_reason self_instance (parameterised recursion stays real; unit test).  Always on.
- A master whose only behaviour is wiring assigns (nets / selects / concats, no operator, always or child) is STUB
  (logic_free_wiring) with --logic-free-stub.  OPT-IN because tools/tests/test_die_bind_unread_manifest.py's toy producer
  (pure fanout) and possibly pure-feedthrough masters on other dies were 'real' so far; head_die_portbind.py passes it.
  Making it default needs a census of the other dies' binds (ASK).
- Tests: tools/test_die_port_bind.py + tools/tests/test_die_bind_unread_manifest.py 38 passed.
- Generated wrappers, kind(): canonical ot_s81hd_ctl / ot_s81hd_host_ep / ot_s81hd_mesh_ep = STUB self_instance (3);
  canonical lep0N wrapper stays real (its content "dsdv_slice_lepw_mu.LP" is a dotted path to a real module, which only the
  module check catches; head_die_portbind still requires module check 0 missing).  Candidate: all 4 real.
- Full head_die_portbind runs (canonical expected FAIL, candidate expected PASS) were still running at lane stop:
  results/arch/head_rtl4_1026/{canon,cand}.otrun.log on epyc1 wt/head-rtl4-1026 (not committed; collect: verdict lines
  HEAD_DIE_PORTBIND / DIE_PORT_BIND).

