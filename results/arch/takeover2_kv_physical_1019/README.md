# KV physical pickup: ATTN source reset and critical-cone successors

Source-only candidates, default off by distinct module names. No REVIEW, submit, CTS, GRT, detailed route, timing qualification, full-token qualification, or parent binding is authorized by this packet. Original defaults and failed evidence remain unchanged.

Original `e7a88d02e` BS1/BS2 gates terminate WARN, but their source is unsafe. Exact input native `qkd_kvs_attn_safe_pr.v` SHA `f78cea8af28b15937316ca31ea473a916fe1342d8bf91255bd3023c5dfd2fc5e` has 34,576 native cells / 6,390 FF. Independent complete BUF/INV-transparent native census finds eight ASR FF QN roots driving only RESETN endpoints: 131, 89, 74, 64, 53, 48, 47, 42. Direct-only 24-load claims hid these. All native cells were parsed, with zero unresolved and multidriven nets. `check_pinreg.py` now counts transparent endpoints including ports and fails nonzero above 32.

## Reset source successor

`qkd_kvs_attn_safe_pr32.v`, SHA `8b4bec803a414206357c445865111f94292af06282dfc60e539223a0375530fb`, adds 13 real kept DFFASRHQN copies with identical D/CLK/RESETN/SETN and 13 true polarity inverters. Repartitions 292 actual RESETN pins; no serial edges, data/control assignments, ports, original FF transitions, or original pin registration change. Independent readback checks every original cell/pin, all 13 copies, exact endpoint polarity, and all unchanged assignments. Both independent native censuses report FF32/tie30/comb24/input22, zero unknown/multidriver. New source: 34,602 native cells / 6,403 FF; depth remains 18 levels.

New direct ancestor loads are charged: c12852/c12207 rise24→30; c32665/c32663 rise24→31; tied SETN roots rise24→30/28/27. This is useful state replication, not a BUF/INV fanout exemption. Source-native master reuse is not a fresh generic-to-ASAP synthesis or mapped physical signoff.

Exact library cost (real ORFS RVT NLDM, cell/library hashes in library_cost.json): +5.49666um² =13×.37908 ASR +13×.04374 INV. Added TT/FF clock load6.017687/6.540976fF, RESETN9.61727/10.437817fF, SETN14.03285/15.13798fF, D7.301827/8.104577fF. Internal power/leakage tables are retained; transition activity and placed wire/clock/reset power remain to be priced, never zero.

Fleet Verilator5.050 unchanged original miter PASS8,256 checked edges,49,857,984 retained-original FF-net checks,11 outputs/6,039 FF nets,48 original reset trials. Existing RX payload/phase/event ages and12-edge reset fixture unchanged. The first reset-endpoint MUT1 unexpectedly also PASS in that random fixture; receipt retained in pr32_m1_noncausal, and it is not a qualified causal negative.

The first Icarus monitor using `$isunknown({a,b})` failed while displaying both values1; the failed receipt is retained. The final monitor uses explicit case-equality known-value predicates (the same four-state property), without changing RTL or stimulus.

Native four-state pair proof exhausts4 independent master/copy initial binary states×2 data×16 phases:640 checks PASS, including64 deliberately opposite initial pairs, first-real-clock convergence, asynchronous assertion with stopped clock and release hold. No equality before the first real capture/assertion is assumed. Independent readback establishes all copies have the exact same transition controls.

The separate emitted-endpoint reset witness explicitly tests arbitrary victim state before reset (not a functional payload reachability claim). Common native root/copy asynchronous assertion, stopped common clock, actual emitted endpoint polarity: correct source PASS64 checks; wrong-polarity source fails RESET32_ARBITRARY_INIT_ASSERT_FAIL atphase0/seed0. It does not manufacture independent reset-family waveforms. Parent admission/POR remains an inherited contract requiring its existing real reset sequence before use; this packet does not qualify a whole parent.

## Actual TT stage failure and bounded Boolean successor

Original BS1 genuine reg→reg TT setup is−15.1502ps at833.333ps/setup60ps/hold25ps, exact original CTS placement RC. Path: c14180/QN (landed RX payload[24]) → input INV →4 OR levels → final INV atn6774 → status/enable cone → cpo216_ff/D. Launch clock370.4365ps, capture351.745ps, CPPR3.5886ps; arrival1139.9110ps/required1124.7609ps. It is not an IO-normalization path. The13-reset-copy repair alone does not repair data setup. Raw detailed reports, exact constraints/clock paths, old gate results, PNGs and source snapshot hashes are preserved. Large raw gate JSON and whitespace-bearing immutable logs are stored as lossless .gz; raw_receipt_manifest.json records their decompressed hashes. Use gzip -dc to read them.

Bounded MODEL identifies exactly old c14562/NOR27(payload[5..31]) retimed onto existing plain RX landing FFs: INV(OR27(INV(landedQN))) equals AND27(landedQN). Every old cone master, leaf state and polarity is explicitly enumerated; only this one pure cone is changed. Eight OR cells and one final INV become a balanced7AND4+2AND3+1AND2 tree. Gate levels6→3 from landed QN, +.08748um², zero FF/clock/serial-edge changes. All27 new leaf input capacitances and exact native TT/FF cell power/cap tables are charged in balanced27_priced_model.json. This is a structural Boolean model, not a routed delay prediction.

`qkd_kvs_attn_safe_pr32b27.v` SHA `ac6af21580867b0e1224c7cf7e6476309d5b036cd2ba558ad5014737fbfeddde`:34,603 native cells/6,403 FF. Independent native census remains FF32/tie30/comb24/input22, no unresolved/multidriver; first/last pin registration remains valid. Exact original/new native pure-cone four-state truth PASS8,410 vectors including216 all-basis four-state cases; wrong final AND→OR causal mutant FAIL. Full unchanged original miter for this candidate is LIVE below. No generalization to the other16 retimed cones was performed.

## Preserved original physical facts and holds

BS1:216square, zero macros (lattice N/A),3284 actual on-track accessible pins, full faces at.192um, square1:1/full-core rows. PIN-BOUND low fill9.5% (north face1080 pins requires~207um); source model standard area4185.20358um². Clock S-centre; TT/FF pin spread34.4/31.6ps; insertion408.4/331.5ps. GRT0. BS2:302.4square, fill4.8%, spread36.5/37.4ps, insertion497.1/408.3ps, GRT0; TT setup−118.1ps. Neither is submittable. Personally viewed BS1 floorplan+density PNGs; no review approval granted.

Checklist: pins/reset source first/last proof available; reach OPEN (textbookreach0 is no measurement; historical298.6um placement model is not current source physical proof); fanout original FAIL and successors source PASS only; depth Boolean model improved, actual TT/FF stage timing OPEN; storage no newly introduced SRAM/arrays; geometry pin-bound low-fill reason above, actual successor placement/reach/native PG/clock/electrical still OPEN; clock ≤80 old gate only, neighbour matching and candidate clock OPEN; static schedule0 added edges. No constant functionality, data falsepaths, MCP, clock relaxation or added waits.

Other live gates preserved diagnostic: AHUB sfa/sfb ep6 postCTS; GRP sq2/sq3 ep7 hold repair; CTL mu5/mu5b ep6 placement. Lead audit independently holds CTL max256 reset copies and128x256 macro faces9.98contacts/um, D2D sf/sfb old64x512 faces10.2contacts/um. No first-WARN submit authority survives these source/geometry blockers.

## Live pickup

Remote ep8 `/srv/opentallas-scratch/claude/takeover2-kv-physical-1019/b27m0`: unit1604802, session49161, Verilator5.050 original full-source miter for ac6af215 compiling. Do not duplicate/restart progressing GCC. All earlier own units terminal. On completion preserve sim/check/build receipts, compare unchanged original8256/6039/11 contract; then source reset/census and placed reach/model/TT+FF/native must be reviewed before any new gate.
