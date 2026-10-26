# Current atomic seqhost and BK control timing

The real canonical `dsdv_hostb_seqhost_mux(HOSTB_ENABLE=0,STATIC_KS6=0)` and preferred `dsdv_bk_sel_vmtx(TX_SRAM=1)` implementations were simulated under the exact as-built defines. Current bind_names maps them to one atomic leaf each (seqhost, bk_sel); no bound inter-partition transport is replaced by these local measurements. Source closure selects manifest preferences, explicit blackboxed implementation children and actual functional memory views. The receipt pins48 production dependency hashes, parameters and straps.

Primary edge convention: a pin event is valid **after** its posedge; an input register samples it on the next edge. Raw sampling observations remain in logs.

| Path | Pin-event edges |
|---|---:|
| seqhost f_ks -> issuer acceptance |4|
| seqhost f_ks -> calendar age0 command register |5|
| command register -> vo_n |7|
| command register -> vo_s |8|
| command register -> CW |3|
| f_ks -> KIT pin, minus programmed KIT issue age |8|
| BK vi_n -> vo_s |3|

Seqhost: two real jobs, four north words, two south words, two CW and two KIT words; every payload exact, zero fault. The input-sampling deltas are KS->accept3, KS->age0command4, KITage72->return79. Input phase0 passes; phase1/2/3 controls fail. Both payload and +1-edge timing-receipt mutants are caught. The receipt records the measured phase relative to reset release; a native compiler must use the actual delivered reset phase.

BK:32 nonzero276-bit CTL words pass exactly, no fault. Input sampling->output is2 edges, hence3 from the preceding pin event. Payload and +1-edge timing mutants are caught.

The actual seqhost mux always instantiates the47-slot tracker and8-row window engine, including single-user operation. Valid0x15 gap/RL and0x16 window boot is mandatory; omitting it raises a status fault even when commands issue. This bench configures gap152/RL79 and8 benign windows for its KITage72 calendar. These are this bench's programme data, not default compiler prices.

Failure diagnosis retained in scratch: v1 omitted a hidden functional SRAM view; v2 deliberately wrong launch phase; v3 omitted MU boot; v4 lacked valid window event rows; v5 mispacked CTL arguments (template index belongs in low7 bits, context in bits7..8). Corrected v7 is fault-free; no production RTL changed. The BK first build lacked its hidden1024x256 SRAM implementation view; v2 is complete.

Actual runs via ot-run: seqhost localhost unit1450615, BK localhost unit1242407, phase controls unit1380135 (plus final-binary controls). Scratch directories seqhost-timing-1026/v7 and bk-timing-1026/v2 under actualhub scratch2. Use tools/s81_dv/seqhost_timing_1026/run.sh under ot-run to reproduce from a clean repository.

These are local control components only: no routed clock, reset-release, bound transport, physical sign-off or whole-token claim. No RTL cycles were added.
