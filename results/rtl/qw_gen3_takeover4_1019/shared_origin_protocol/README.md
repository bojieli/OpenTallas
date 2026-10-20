# Existing-event shared epoch/origin interface — default off, incomplete

This is a typed source/model interface, not new RTL or an adopted release protocol. `epoch_origin_inventory.py` binds eight roles and their exact clock/reset/event nets from actual compute GEN6f78e3de2 die.v (zero missing required pins). `shared_epoch_origin_guard.py` refuses absent production values. Twenty-one focused model/cone tests pass. No diagram/counter values from the laboratory cold experiment are treated as production origins.

The minimal interface uses events already in the RTL:

| Role | Existing endpoint | Clock/reset | Required origin/cost evidence |
|---|---|---|---|
| Package clock/reset | ckb_rom.pll_ck / rs | qfd_ckbump hard-macro model | Physical package/PLL clock/reset correlation; absent beyond this modeled boundary |
| Run epoch | bump_fwd_epoch.o -> sys_face.fwd_epoch, d2d_rom.fwd_epoch | qfd_sigbump hard-macro model; actual landed paths | Actual KV producer strobe and both die receive-edge receipts; the constant-zero simulation model is not a source |
| Programme identity/admission | installed host epoch/programme record in sys_face | sys_face.ck/rst_n | Immutable selected programme/image and effective context identity; installed host epoch must not stand in for every filler user's effective epoch |
| Calendar launch | sys_face.cal_start/cal_seg -> d2d_rom.cal_start/cal_seg | Actual face and D2D roots, reset trees in contract.json | Complete strobe/segment bundle age, installed-store readiness, cal_start origin relative to forwarded epoch |
| Source slots | d2d_rom.native_tx_slot/kind/beat | d2d_rom.ck; rst_n and por_n separately | Actual PR, u_txcal first image dt and source counter origin |
| Consumer context | tt_ctlm.native_cmd/layer_context_v/command_stage/native_tok/native_pos -> native59 | Actual tt_ctlm/native59 clocks and reset trees | The actual compiled instruction/context edge and its effective epoch, user and stage, plus first usable context delay |
| Landing | rly_lnk_native_tx_slot_0.a/b/en/rs/ck_s/ck | Exact native instance and reset traces | D8 four-strap replacement, pin-phase and raw-reset cases bound to source/consumer origins; present source still D4 |
| Use/fault | native59.tx_slot and context/record endpoint | Native59 pin-register stage, then actual context/codec state | First valid acceptance relation and existing sticky fault/abort path; no wait or credit |

The actual source face already states the run anchor is forwarded epoch, not reset. Its first-token counter is armed on fwd_epoch rising; first_ofs, boot_done, cal_ready and installed programme readiness must hold or the source faults. The D2D u_txcal starts its countdown on cal_start. A first table dt1 emits on the next calendar core edge. Actual qfd_d2d_static PR1 adds one input edge for cal_start and one output edge for native_tx_slot. Its cfg_recent check forbids same-edge or previous-edge configuration at start. These local semantics are priced; they do not establish the upstream anchor or final die transport.

One global compiler edge coordinate must join both sides. An origin receipt names actual counter/state pins and event occurrences, source/consumer netlist and image hashes, TT/FF phase/reset cases, and all upstream stages back to the production source. The common identity consists of the actual effective epoch/context plus selected calendar segment and native command stage. No new physical identity wire is asserted by this artifact. A missing existing-field join remains a source gap.

For a selected first event, let F be cal_start at the face, X its actual transport, Pin/Pout the proven calendar input/output register prices, and dt the image's first delta. Then source slot S=F+X+Pin+dt+Pout. Let A be the one compiled source-pin-to-consumer-pin age. Consumer first use U=S+A. In the native landing, let P/Q be actual upstream/downstream stages and N=A-P-Q the native global age. At corner c, local Lc=N+source_origin_c-receiver_origin_c. This L is DERIVED from the same A and bound origins, never independently chosen by corner. Raw phase still uses the actual pin clocks. Both reserved physical age and immutable K must agree after this coordinate change.

The default-off guard requires all of:

- Actual upstream package/PLL/run-epoch correlation and a hashed producer/consumer origin receipt.
- Common global age; derived native local edges and raw G/R0 at TT+FF; one K; 150ps/100ps reserves in the native age window. No per-corner phase wrapping or straps.
- First source word after current write-epoch activation; first receiver use after native warm-unblock; context installed with the selected native59 context-to-slot delay. The context delay is NULL here because current v3 alignment is not admitted.
- Last configuration at least two core edges before calendar start, source stores ready at start, and positive first dt. Late conditions fault; they cannot stretch the static schedule.
- Exact boot/re-admission price U minus the common epoch origin, plus all data-stage edges A. SRAM's two additional receiver edges are part of the native price. A source-clocked epoch-arm successor would also charge each actual arm/transport/release stage; no unmeasured zero-cost assumption is supplied.

Current contract.json has NULL transport/first-dt/first-valid/context/boot values and upstream correlation false; refusal.json records the exact blockers. Known local PR1 edges are the only filled local cycle prices and must be rechecked against successor parameters. No guessed327/536cycle slice total, old G21/R1596, synthetic fixed-time reset, or user-0-only identity becomes a receipt.

A concrete static hardware successor, if upstream delivery cannot provide the needed correlation, would need a source-clocked epoch-arm event and fixed registered/landed delivery to the calendar and command origins, with every accepting edge proved at all corners. This artifact defines what that successor must export and price. It does not invent such RTL, infer a PLL waveform, perform training, or use acknowledgement to choose a cycle.

SLICE6 must supply the actual current receiver-port list, exact sliced widths/bit ranges, clock/reset pin identities, complete bundle age, effective context origin and first-valid edge; K remains NULL. Historical182face rows and current183internal crossings are distinct. The new coherent channel width/area proposal is not silently substituted into this old emitted-source inventory.
