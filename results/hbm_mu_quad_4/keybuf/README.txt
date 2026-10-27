HBM-MU-QUAD-4 task 4: keybuf time-serialisation (hnx_idxn_keybuf, 4 instances u_mu_keybuf_0__q0/q1 in q_hub_nw/ne, 324x324)
Date 2026-10-27. Host epyc2. Numbers: CHECKED = recomputed from the named log/artifact here; UNCHECKED = analytic/estimate.

SOURCE  ot_hnx_idxn_keybuf from claude/hbm-next-units-idxn-1019@1228d93d6 (copied byte-identical to
        rtl/hbm_next/idxn/ot_hnx_idxn_keybuf.sv and ref_ot_hnx_idxn_keybuf.sv; SRAM model ref_sram_256x256.v from the same sha).
        Ports: key_in 8792 + key_out 8792 + 31 control = 17615 bits (CHECKED, RTL). key_out = replay_v ? regenerated : key_in.
        The scorer consumes one 8792-bit line per edge for 171 back-to-back key beats per row (row II 232, idxn README).

DESIGN  rtl/hbm_next/idxn/ot_hnx_idxn_keybuf_ser.sv (new; the original module is unchanged and instantiated inside):
  ot_hnx_idxn_keybuf_ser #(NB)  hard core: key buses cross the boundary as NB beats of W = ceil(8792/NB); every input pin
                                lands in a flop, every output pin is driven by a flop (fault too).
  ot_hnx_idxn_kb_tx  #(NB)      producer shim (partner partition, beside the IDXN calendar/key-line service): registers
                                control, serialises key_in, FAULTS when two key events are < NB edges apart.
  ot_hnx_idxn_kb_rx  #(NB)      consumer shim (scorer side): registers beats, assembles the line, delays beat_v/index by K.
  Static schedule: no valid/ready, no credits, no beat counters: always-shifting serialiser/assembler chains, so beat j
  is on the wire exactly j edges after beat 0 by construction. Inner keybuf sees the ORIGINAL control sequence delayed
  by L = NB+1 every cycle (pre_v stays one edge ahead of replay_v).

CHOSEN NB = 3 (opt-in; NB is a parameter):
  NB  W     core port bits  pins/um (1296 um perimeter)  track ratio (4 faces x 324/0.048 = 27000)
  1   8792  17615           13.59                        0.652   (original)
  2   4396  8823            6.81  (> 6 limit)            0.327
  3   2931  5893            4.55                         0.218   <- chosen (0.437 if only 2 faces used)
  4   2198  4427            3.42                         0.164
  (arithmetic CHECKED; NB=3 widths CHECKED in sim RESULT line W=2931)

LATENCY / CYCLE COST (for the latency package):
  K = 2 NB + 2 = 8 edges per key transfer (line producer edge -> scorer edge), CHECKED (sim offset + formal P1-P3).
  fault visibility +NB+2 = 5 edges (CHECKED, sim/formal P4).
  THROUGHPUT: key events must be >= NB = 3 edges apart -> the 171 key beats of a row take 513 edges instead of 171.
  Row II (binding unit = scorer array: 32 head emits + 5 gap + key beats + 23 reload gap): 232 -> 32+5+513+23 = 573,
  i.e. +341 per added row; record N=1: 1297 -> ~1297+342+8 = ~1647 (UNCHECKED analytic, calendar not recompiled).
  The IDXN calendar programme must be recompiled with key-beat pitch 3 (kb_tx faults otherwise).
  This is a LARGE cost on IDX.INDEX (MTP/MU rows). Zero-cycle structural alternative (NOT built here; recommend pricing
  it against NB=3): split the keybuf spatially by key line into 8 identical slices (one type x8 per scorer stream:
  1099 in + 1099 out + 31 ctl = 2229 bits, 4.25 of the 34 macros -> 5 macros, ~1/8 of 324^2 ~ 115x115 um, perimeter
  ~460 um -> ~4.9 pins/um), each placed beside the score hcol cores that consume its line: no serialisation, 0 added
  cycles, pins registered the same way (+1/+2 edges of pin flops only). UNCHECKED (analytic).

EQUIVALENCE
  1. Random simulation, full 8792-bit width, real ot_hnx_idxn_keybuf + 34 SRAM models, iverilog 12.0 (epyc2):
     tb_keybuf_ser.sv: old keybuf vs kb_tx -> keybuf_ser -> kb_rx on the same stimulus; 6 records (171 live beats, 3
     replay rows each, PRE one edge ahead), records 4-5 inject schedule faults (bad PRE index, replay of a wrong index,
     stray PRE). Check A: every key event e: rx line(e+K) == old key_out(e), all 8792 bits; scorer beat fields delayed
     by K equal. Check B: core fault pin(t+NB+2) == old fault(t), every cycle.
     NB=3 seed 1: events 2620, data_err 0, fault_err 0, fault cycles 3124 (faults exercised), PASS  -- sim_nb3_s1.log
     NB=3 seed 7: events 2816, 0/0, PASS (sim_nb3_s7.log); NB=2 (K=6): 1596 events 0/0 PASS; NB=4 (K=10): 2796 events 0/0 PASS.
     Spacing mutant (events NB-1 apart): kb_tx fault raised -- sp_nb{2,3,4}.log all FAIL-as-expected (fault raised).
  2. Formal, unbounded (SBY + abc pdr, yosys 0.67, openroad/orfs:asap7lock docker): formal/fv_top.sv, fv_nb{2,3,4}.sby.
     The inner keybuf is CUT (OT_KB_FORMAL: free key_out/fault, inner inputs observed) so the proof holds for ANY inner
     behaviour: P1 inner control(t) == original control(t-L) every cycle; P2 live event e: inner line(e+L) == key_in(e);
     P3 rx line(c+NB+1) == inner key_out(c) at every inner event c; P4 fault pin(t+1) == inner fault(t); P5 no spacing
     fault; assumption: key events >= NB edges apart. Width reduced to DW = 10/11/12 for NB = 2/3/4 (same residue
     8792 mod NB, so the padded last beat is covered); the wrapper is bit-sliced (each bit an independent shift chain
     generated by the same loop), so the reduced-width proof covers the 8792-bit instance structurally (argument, not a
     full-width run: a full-width PDR run did not finish in 9 min and was stopped).
     Result: NB=2 PASS, NB=3 PASS, NB=4 PASS (formal/fv_nb*.log). Non-vacuity: mutant control delay NB instead of
     NB-1 -> engine FAIL (formal/mut_delay/mut.log; the trace replay step errors only because no SMT solver is installed).
  Together: end to end (tx+core+rx) == original keybuf delayed by K = 2NB+2 on every consumer-sampled edge.

CELLS (yosys generic synth, inner keybuf blackboxed; synth_*.log; NOT ASAP7-mapped -> UNCHECKED area):
  core wrapper +23536 generic cells (17670 flops = boundary + assembler + serialiser regs; 2NB*W + 28NB ~= 1 flop per
  original port bit), producer shim 14688, consumer shim 8867 (8865 flops). The core keeps its 34 macros + original logic.
  Area fit of +17.7k flops inside 324x324 next to 34 macros: UNCHECKED (needs a kit/place).

FILES  rtl/hbm_next/idxn/{ot_hnx_idxn_keybuf.sv (pinned copy), ot_hnx_idxn_keybuf_ser.sv}
       results/hbm_mu_quad_4/keybuf/{README.txt, tb_keybuf_ser.sv, tb_spacing.sv, run_sim.sh, run_formal.sh, synth.sh,
       sim_*.log, sp_*.log, synth_*.log, formal/}
