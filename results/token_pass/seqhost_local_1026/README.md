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

`native_boot.py` now supplies an isolated native mux boot bridge. The caller must supply slot gaps, return latency, KIT issue, all eight HWIN event rows with every slot's attributes, and actual KS/reset pin dates. It emits only the required CSR 0x15/0x16 words; it does not invent calendar rows or descriptors. The emission records the selected local receipt and source closure. The return latency uses KS input sampling, hence `KIT issue + measured pin offset - 1`. The KS pin dates must satisfy the measured issuer phase relative to actual reset release and the supplied slot gaps. The helper also checks event bounds, periodic endpoint collisions and outstanding-slot wrap.

The committed `native_boot_fixture.json` is explicit diagnostic programme data for the existing six-row calendar. Its 35 generated words (`native_mux_boot.memh`) replay through the current real mux with exactly the same complete `SEQ_` trace as hand-encoded boot: two jobs, four north words, two south words, two CW and two KIT returns, zero errors. A one-bit return-latency mutation produces 253 errors and a sticky fault. Actual run: `nativeboot1`, localhost unit `oth-ubuntu-1795877-1793010388`, ot-run exit 0 after checking both expected verdicts. Config mutations for wrong phase, RL, missing event, endpoint collision and wrong gap are rejected. This adds no production RTL stages or cycles.

For the same diagnostic fixture, prepare a fresh seqhost source directory with `prepare.py`, generate its `mux_boot.memh` with `native_boot.py --config native_boot_fixture.json --local-receipt control_local.json --out FRESH`, and copy that file into the prepared directory. Run `replay_native_fixture.sh` there through ot-run. The replay's fixed KS dates and calendar are the committed fixture only; production callers must use their actual bookings.
