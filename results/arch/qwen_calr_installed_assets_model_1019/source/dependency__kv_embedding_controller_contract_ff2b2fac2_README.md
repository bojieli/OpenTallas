# Selected embedding controller: M2 source contract

Read-only extraction of frozen **5f2ce19bc**, selected pre-expansion die SHA **00a3de7cd445198b147af744e5dd3c00f824a3222767b3fb4c8274392dd8b36e**. The25 bodies and exact SHA/lengths are in source_manifest.json. No RTL, compile, simulator, programme, boot image, physical binding, profile or calendar changes. No production date or native/PHY qualification follows. This completes the bounded source diagnosis, while M2's native return inputs remain open.

The material correction to af18/945's simplified description is **RETIME=1 in the actual selected endpoint**. Its reserved return is a latest allowed edge, with one early controller word retained. The source does not require the raw er pulse to equal the reserved return edge. The historical standalone qkd_embedding_static_pc exact-arrival module is not the selected strap implementation.

## Actual selection and parameters

| Selected hierarchy / body | Actual contract |
|---|---|
| qkd_kvs_pc and qkd_kvs_pc_h.u_pc | qkd_static_kv_pc_path_fan_nc_b MU=1; all five controller HBM clock pins, cal/front/return_hck use local hck; core and return_ck use local ck; hrst=hrst_n, rsi=rst_n |
| _fan_nc_b.u_chain | qkd_kv_pc_chain_station_b MUT=0; full780-bit hop; eight16-bit ISS/RET/CAP/TRN/SISS/SRET/SCAP/STRN registers defaultffff |
| _fan_nc_b.u_pce | qkd_static_kv_pc_path_emb_nc_b MU=1 |
| _emb_nc_b.u_esm | qkd_static_kv_pc_es_merge_b defaults ROW0=24427, MUT=0, **RETIME=1**; selected u_emb is qkd_embedding_static_pc_strap with the same values |
| _emb_nc_b.u_path | qkd_static_kv_pc_path_nc MU=1 |
| u_path.u_ctrl | qkd_ctrl_pc_host_static_nc ROW0=64, CVL=2, HOFF=3, WDONE=17, LATE=4096, PROFILE=0, EVMUT=0, MUT=0, **ELASTIC=1, RAW_WD=256, TQD=64**; remaining STRAP_CDC=0, DRAIN_PIPE=0, CONTEXT_DESC=0, STATIC_REFRESH=0 defaults |
| u_ctrl.u_sched.u_ctl | ot_qkd_static_ctrl_pc_emb ENABLE=1, PC=0, PHASE=0, PROFILE=0, CONTEXT_DESC=0, STATIC_REFRESH=0; SQD=4, S_STARVE=8, TWIN=0, TWIN_ROFF=0, PULLIN=0 |
| u_ctl.core | ot_qkd_static_kv_timing SROW=1, READY_CUT=1, REF_MODE=1, WR_EN=1, WQ=4, AQ_RD=0; same preceding SQD/starvation/twin/profile parameters; PC=0 and REF_PHASE=0 **inside** each controller, compensated by external strap-delayed hgo |
| timing constants, HBM edges | RCD19, RP16, RAS28, RTP6, CCDL3, RRDS3, RRDL4, FAW15, RFC342, RFCPB196, REFI3808, REFIPB118, RREFD8; RTW10, WTR14, WRR28, RCDW10; all source defaults, not a measured DRAM return receipt |
| u_ctrl.u_port.u_port | port child RQD=64, MUT=0; ot_qfd_emb_pcport_nkw RQD=64, WQD=4, MUT=0; ordered class queue, static/embedding read class, real4xSECDED72/64 decode |
| u_ctrl.u_cdc.u_ecdc | ot_qkd_static_emb_cdc ENABLE=1, DEPTH=8; down FIFO349bits, up FIFO258bits, credit FIFO1bit; each ot_async_fifo EXT_RST=0 default, separate resets/online rendezvous |
| u_path.u_calendar | qkd_controller_hbm_calendar N=16, ROW0=64, MUT=0;32 accepted64-bit half-writes, low/high coverage and seal required before go; event capacities/finite offsets are real |
| u_calendar.raw_calendar | qkd_static_kv_return_calendar defaults PHYSICAL_CMD_EDGES=4, HBM_RL=23, CORRECTED_EDGES=5; raw shift27, corrected shift32. These are **nominal source calendar constants**, not native response bounds |
| selected embedding SRAM | rowtx ot_sram_1r1w_64x512_m1_r2c2, same ck, synchronous r_ce/address and512-bit masked write; no memory reset; rr/cr disabled in this source. Actual macro view/read aperture/PG receipt is a separate missing input |

ROW0=64 belongs to ordinary KV descriptors. Embedding ROW0=24427 is in the separate embedding address mapper; do not substitute one for the other. MU1 here is the source's selected PC row mapping; it does not qualify integrated HOST MU4.

Selected preexp PHY instances are phy_WS/WN/ES/EN, each qkd_hbm3e_phy_pc with local n_clk_hbm_STACK and32 po328/pi289 faces plus fh/rh data clock ports. selected_phy_connections.txt retains the four complete instance lines. kv_die.py describes SPLIT_PHY as a licensed PHY-only abstract; it does not implement po-to-pi read data. HBM lead explicitly confirms no matching selected qkd return/phase receipt is held there; their n64/HBM45 successor is unselected and cannot supply this contract. This does not prove no such receipt exists anywhere.

## Controller read/return recurrence

Use **sampling edges**: a register reads pre-edge values; a produced value is usable by another register on a later edge. C_s[k] is one selected stack's core edge, H_s[j] its HBM edge. There is no common numerical C/H origin in this packet. Equal source hck expressions do not establish native insertion/phase equality.

1. Let I be the core edge where selected strap samples emb_issue_v. It stores complete token/word/half/scale/epoch, sets pending, and produces ees. The merge samples ees at C[I+1] and produces es. Controller cdc child samples es at C[I+2] into es_v_q/es_d_q. Its down FIFO accepts the pulse at C[I+3] only if wr_ready; otherwise sticky fault_core records loss. No retry or invented credit/wait is permitted. This relation assumes each intervening selected reset is released and no conflicting writer/boot source.
2. Keep the actual down FIFO recurrence rather than rounding a clock ratio: on H edges wr_gray_r1<=wr_gray, wr_gray_r2<=wr_gray_r1, rd_empty<=(rd_bin_next==wr_gray_r2), with rd_valid gated by conditioned reset and synchronized writer-online. c_v_w=rd_valid; c_v output capture, u_ctl.s_v_q capture, then core static-queue push are distinct H edges. Other accepted descriptors ahead of this read contribute real occupancy. Reset reconditions and rendezvous can reject a pulse; a fixed phase-free +N is invalid.
3. Static queue accepts only s_v && s_r (four-entry capacity). s_go is legal_static && reserved_static_col in selected PROFILE0. legal_static requires matching open bank/row, RCD/CCDL and turnaround eligibility, no refresh block, plus source priority (starvation8 or background availability). A reserved column without legal_static faults; it is never postponed. Exact boot writes, acquisition reads/writes, bank state and refresh phase are inputs to legality. A no-conflict inequality must be solved against that real state, not a constant read latency.
4. u_ctl registers its actual column, then u_sched registers po containing column/row/data. The class queue launch is aligned independently through dv and port pin captures (CVL2, LW3). PHY must supply in-order pi valid and actual288-bit code. The actual command-to-return edge is **NULL**. HBM_RL23 feeds the nominal raw expectation only.
5. For a physical pi sampled by port child at H[P], rv_q and rd_q are captured together. At H[P+1] the real port captures c1, syndrome y1 and v1 for an embedding/static read class; at H[P+2] it produces em_v/em_d with corrected256-bit data/CE/UE. CDC child captures that at H[P+3], and its up FIFO accepts it at H[P+4] if online/not full. These exact source captures do not bound P.
6. Up FIFO repeats the actual Gray-pointer/reset/online recurrence in C. The cdc child's er_v/er_d capture is a further real C edge after up_valid is visible. It exports {er_f,er_cr,UE,CE,data,valid}; the selected merge only steers it away while own=boot. No ordinary KV u_ecc or block_front latency belongs in this embedding er path: those serve kv_v, whereas static/embedding em_v traverses u_cdc directly.
7. Let A be the core edge at which strap samples er[0] for this pending read, and R its compiled return_slot sampling edge. With RETIME1, a legal read requires **I < A <= R**, exactly one response, pending true, er_f=0, returned UE=0 and no conflicting held/new word. If A<R, h_d holds the real data until R; if A=R it passes through. beat_v/data/identity become visible after R. An early unsolicited word, second held word, held+new word at R, missing/late response, or return with no pending read faults. issue cannot overlap a pre-existing pending read, even on its return edge. Therefore next same-PC issue must sample strictly after R.

The elastic raw watchdog is not a per-request worst-case bound. It tracks nominal outstanding count, resets raw_age on **any** rv_q, and faults after256 no-data edges while debt remains. A stream of responses can keep resetting that age. In-order class/finite queue checks help diagnose validity but do not turn this into a proven fixed controller latency. A finite return deadline requires the actual PHY/service and admitted traffic contract, not RAW_WD arithmetic.

## PC calendar and strict header inequalities

Let S_s,p be the edge where chain_station_b samples the **local ss hop register** (not direct RESULT or shared fan root). That edge loads act=1,cnt=0 and token/epoch. With offset x, the player emits its registered event after S+x+1; the downstream endpoint/return pin samples it at S+x+2. Accordingly:

- I=S+ISS+2 and R=S+RET+2; scale I'=S+SISS+2, R'=S+SRET+2 only for the mapper-selected home PC.
- Actual controller er must satisfy I<A<=R. Scale issue I'>R, scale arrival I'<A'<=R'. Every offset is0..65534; ffff disables. All eight r words must have been accepted while inactive before ss. No boot-time guessed wait supplies acceptance.
- Return-hop capture_slot must coincide with the endpoint's registered beat_v at its pin. Therefore CAP=RET+1 and SCAP=SRET+1 in this source. Hop records capture_slot/data at one edge and retains them one edge later. Its transfer must act on pre-existing occupied data, so TRN>CAP and STRN>SCAP; a simultaneous capture/transfer faults. Scale cannot overwrite a retained code beat before its transfer clears occupancy.
- Each return station has two actual sampled edges for upstream forwarding. Its local transfer and upstream valid may not coincide. The four complete train routes and later HROOT/die captures must be composed per stack; no suffix63/18/76/26 is treated as a certified age.
- Let J be the edge where join4_cal samples direct start. It stores ss at J, starts act at J+1, produces a slot for offset o after J+2+o, and join4's slot pin samples that at J+3+o. The selected train record must be valid at that **same join4 pin sampling edge**. join4 captures it then; inner join consumes it on the next C edge; word_v/code or selected scale appear after that inner-join edge. rowtx captures them on the following C edge. Direct J and delayed fan S are separate source events and reset epochs.
- Let F be rowtx's real FILL sampling edge, W_i each of64 code write sampling edges, W_scale scale capture, and H_0 the header reservation sampling edge. Require **F < min(W_i,W_scale)** and **max(W_i,W_scale) < H_0**, matching token/epoch, exactly one of each word/scale, with n=0 while writing. Equality at the last write/header is illegal because residency uses pre-edge coverage.
- Exactly65 ordered header/word slot samples H_0..H_64 are required. Header issues SRAM word0 prefetch, slot H_k consumes the previous prefetch and requests the next word when applicable. Distinct consumer edges and the real macro clk-to-q/read access aperture must support H_(k+1); no array preload is allowed. Last H_64 clears armed; a66th slot faults. Keep row identity until the consumer's actual final scale/read/result use (M6), whose date remains NULL.

The original kvjc3_pc_chain.py is a useful eight-register/two-segment equation template. Its common root/join origin and ctrl_lat default92/exact-L description are not the selected die contract. A correct constructor must take separate J,S_s,p, real maximum er deadline, every return route and reset/phase witness, then emit accepted boot words and actual link/E reservations. No +2 scalar e1 adjustment is used: frozen selected core has no e1 input/output boundary wrapper.

## Missing inputs and minimal next source proposal

M2.NATIVE: selected qkd_hbm3e_phy_pc po→pi source/model plus real DRAM read/service maximum, ordered-return guarantee, data/ECC association and command/data aperture; selected native per-stack C/H/reset phase/clock continuity. HBM_RL23 is only nominal calendar policy.

M2.TRAFFIC: actual accepted/sealed16-descriptor controller images and all PC/player/join boot words, actual go/hgo ancestry, bank/refresh initial state and competing host/write/ordinary KV reservations. hgo delay uses dtab[pc]=floor(pc*118/32)+parity correction after the hr_q reset pin; PC/dsel must be stable before use. Pinning that formula supplies no global cycle origin. STATIC_REFRESH0 retains the original dynamic refresh-bank selector, not a static-RR phase assumption.

M3/M4: source-backed J vs four delayed fan start routes,128 local S events, all return HROOT/die capture chains, reset-first-valid proofs and macro read contracts. These are independent of controller body equality. Actual e1 boundary source remains absent.

M1/M5/M6: real first seed/next RESULT identity, executable65 link reservations and Qwen independent E/FILL expectations, original preload/provider/native65 reads and final ownership. Qwen confirms neither frozen787345 nor selectedb8e812 event version has executable E installed. No R5 fixture date is transferred.

Next bounded source step: one immutable event ledger accepting these missing inputs, deriving reservations from the recurrences/inequalities above, encoding then decoding the **real** boot/player/controller/join and link/E words, rejecting finite-field overflow/collisions/reset crossing. This packet does not grant a synthetic responder, waiting schedule, new credit, unconditional RESULT, programme edit or compile. Qualification remains HOLD until actual input authorities and ROOT's source/sim grant exist.
