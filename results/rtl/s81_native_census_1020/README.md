# Binding native fanout census, 2026-10-20

Existing jobs preserved. These are mapped-netlist diagnostics, not release approval. Source script uses the main textbook parser and buffer/inverter collapse with all high-fanout thresholds set to 32; clocks excluded, resets included. Physical geometry was not provided to this pass. Every JSON retains the full refusing high_fanout list and SHA256 of its exact mapped netlist.

- qgate: 238553 cells, 53216 flops; 1093 nets over32, reset max 307, nonreset max 5410. 61ad474a2d0674f2da6d2f7666ef0bfb9f98f4483b7f6aa80b89647268da5db5.
- bfgate: 294317 cells, 53495 flops; 1306 nets over32, reset max 552, nonreset max 4272. 8d4821aa101b31a7803402748ee25d879e07932cf34dce40eff1c87aace6d8e3.
- lpk4: 111466 cells, 25535 flops; 101 nets over32, reset max 0, nonreset max 2187. a06d0277e1dc90e97d7544b48abfdcd37f491be13aaff7a827ed70a4e53cffab.

The earlier native frame report incorrectly called BF outputs unregistered. PINREG4 routed-netlist proof supersedes that statement: registered output flops feed ten hold buffers; T-OUT targets overpadding. That pin fix does not address this mapped fanout refusal.

Next structural choice: compose compact199 FOREP + RSTPART from c199-fanout lineage with T-OUT, then reduce residual >32 loads in actual mapped census. CPR qxpq requires register-copy/partition restructuring, rather than more pin or sizing-only changes. SerDes lpk4 also needs kept landing counter/decode/control copies; regional clock partition alone does not fix data fanout.

No gate, route, submit, or cancellation was launched by this census task. Runtime: ot-epyc6 unit oth-ubuntu-2431337-1792481802, terminal exit0.
