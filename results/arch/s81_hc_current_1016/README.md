HC current source and compact hub residuals

This is an additive candidate, not a production adoption or a stand-in retirement.
The current die uses ot_s81_hc_comb with its historical credit-driven CSEQ and defaults CCF_BP=0. The fourteen-child dsfd_sp_hc_comb_native is older than the current seven-leaf CCF successor. Neither is a source-current static production composition.

The two new parents join the actual main arithmetic without rewriting it:

- dsfd_sp_hc_comb_roots20 uses the current CCF_BP=3/PINREG bankpipe, current forward pad trim3, and all twenty independent serial child roots. It retains historical dynamic CSEQ only as a diagnostic reference, requiring a twenty-first controller root.
- dsfd_sp_hc_comb_calendar20 replaces that sequencer with the existing, source-pinned 20d249948 compiler-calendar CSEQ candidate. It exposes actual row/tag and command completion/scalar ages and does not use operand readiness to select production issue times. It has twenty serial roots. Commands and the added 165 tag/calendar input bits must arrive already in the sequencer serial clock domain. No controller-clock CDC bridge has been invented or qualified.
- ot_s81_hc_pad_roots20 contains additive copies of the current wires-only pad/CCR assemblies with independent child clock inputs. Arithmetic and existing hard leaves remain untouched.

`source_join.json` lists the exact generated files, input hashes and all twenty physical clock paths. `prebuild.json` records the actual target shape, boundary widths, source and unqualified geometry before this build. The generator regenerates these source files from current source bytes plus the pinned existing calendar controller, rather than copying the stale fourteen-child parent.

Verified on EPYC4 through ot-run: both full native arithmetic graphs pass Verilator lint with no black-box substitution. The actual current pad composition passes 500-cycle delay equivalence including reset and four stopped-real-clock mutants fail. This does not prove full HC numerical equivalence, all-kind static cycle timing or physical delivery; these remain open. One failed packaging invocation ran no design test and is recorded in proof_receipt.json.

Real routed views, independently audited now:

- CCF north: TT +306.32 ps / FF +20.00 / DRC0, native launch206.5/capture171.1/spread51.2 ps PASS.
- CCF south: TT +304.98 / FF +15.88 / DRC0, native launch194.1/capture173.2/spread64.6 PASS.
- CCR pr3: TT +82.40 / FF +0.26 / DRC0, native FAIL launch279.7 on501outputs and capture257.1 on716inputs. This view cannot qualify the joined parent. It also has16006 real clocked registers; this already CLOSED leaf is retained as evidence, not silently treated as a newly partitioned root.
- CCF bank: NEEDS_RTL, TT -34.99 / FF +14.99 / DRC2, preserved PVE1 run. No unchanged retry.
- CSEQ pr3: progressing hold ECO on EPYC4, latest measured TT+30.22 / FF-21.52 / DRC0. Preserve this job. Its legacy controller proof cannot qualify the new static controller.

The old whole20 tallpack_v3 proposal is575.992x943.52, not a grant. Its `u_f5r1(f3r1)` reservation is stale: PINREG+3 and trim3 require DEPTH2, not historical DEPTH5 or the earlier trim2 DEPTH3. Existing hard pad views are not interchangeable with this actual source. The static CSEQ has extra165 input bits and a changed clock interface; its legacy190.08 square outline and measured insertion cannot be inherited.

HC folded64-group geometry from the SU/HC home stream excludes these residuals intentionally. Its primary8x8 arrangement is4916.16x6989.76 with real leaf origins; crootY, crootR, comb and controller still require source-current homes, actual clocks and all incident pin joins. The production crootY FIFO emits on fixed pop events but has no independent current all-root composition proof here. Collect its existing leaves rather than aliasing its parent. Die owner assigns coherent new residual origins and all pin windows before kits. Owner reviews the Explorer candidate before adoption.

Next engineering steps: classify the actual bank internal TT and DRC paths and repair structurally; split CCR capture/launch ownership against actual failing pins without adding unpriced stages; collect preserved CSEQ ECO; join canonical all-six-kind static programs to actual VM/collective, validate tags and exact command/output/completion edges, then measure per-root state/clock/area, actual all-incident cuts<=0.60 and TT/FF/native timing. No new physical job, external cost acceptance or production selection is made by this receipt.
