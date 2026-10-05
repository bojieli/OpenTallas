# W5 Qwen O4 route cuts (PARTIAL, stopped at the 2026-09-29 halt)

- `vm_cut_attempt1_ideal_io/physical.json`: historical failed attempt. It is the 8-skew-bank VM cut at 0.910 ns and 60 ps setup
  uncertainty, with the Codex proposal's macro coordinates and the driver's default I/O delays (0.2 T, ideal clock at the
  ports). CTS hold repair on the port-to-producer paths hit ORFS's maximum buffer count, RSZ-0060. The last reported hold
  WNS was -476 ps after 26,362 hold buffers. The inferred clock insertion delay is about 0.66 ns.
- Attempt 2 is not recorded here: the run was stopped at the halt and left no committed record. It used latency-consistent
  I/O (input delay min 0.80 / max 0.982 ns; output delay min -0.30 / max -0.118 ns), and its ORFS synth_stat area was
  171,051.8 um2 including the macros. At CTS its setup WNS was -817.7 ps before repair and -698.8 ps after, with 8,547
  violating endpoints, 1,515 hold endpoints and 3,081 hold buffers. The worst path ends at
  u_vm.banks[4].slices[2].u_mem/r_ce_in: the combinational four-client conflict check suppresses all 32 macro enables in the
  request cycle. These are scratch observations from the worker log (/tmp/claude-1000/w5scratch notes), not evidence.
- The ROM/MAC neighbourhood routes (port 26 macros, plain 22 macros, explicit placement from physical/qwen_o4_w5/*.tcl,
  0.910 ns and 0.920 ns) were stopped during ORFS synthesis. Yosys had run for more than 50 minutes on the flat G4 W16 matvec.
  No record exists.
