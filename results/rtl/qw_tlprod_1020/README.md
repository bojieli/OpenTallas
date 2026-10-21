# QW-TLPROD ctlm9d: per-layer slice-table load PRODUCER in the CTLM calendar (Q.STA.TTC.4 release blocker), 10-20

## Blocker (QW-CALR ctlm9c)
CALR=1 gives the CTLM a table-ROM request lane (LOCAL4 -> table_req {valid, stage, user} -> slice qfd_dv_slice_tload),
but nothing issued the 36 per-layer loads for user 0: the CALR10 capsule only has 36 caller-selected one-entry preload
ranges (868..1008); the face's dh stage start carries no range and the OPSEG leaf refuses user-0 entries (and its
op-start list carries no table loads for fillers either). Layers 2..36 would run with stale norm gains / post-scales.
Owner check: no existing producer is designed for it (sys_face T calendar: stage starts only; MU ctx: context record only;
TLOAD kind 3: refused under CALR; finite_calendar_body: "ordinary stage starts do not infer a table installation").

## Fix (static schedule, no handshake)
- RTL `rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv` TABLE_REL (under TABLE_ROM): a LOCAL4 entry with bit 10 = 1 is stage-relative:
  table_stage = the stage its playhead was started on (`pst`, 6 b per playhead, loaded on the accepted start: dh face start
  for user 0, OPSEG leaf start for fillers). Field [9:4] must be 0, stage 1..36 else fault_code[4]. Bit 10 = 0: unchanged.
  MUT 35 (bench) drops the stage-17 REL load. `qfd_tt_ctlm_dv_lpf(_parts)`: bench-only CAL_MUT parameter (default 0).
- Compiler `tools/qwen_layerbench/calr_table_producer.py`: inserts ONE REL LOCAL4 as the first decode-descriptor entry
  (T=8 = T0_MIN), moves the first original entry (SU issue, first possible table consumer) 26 -> 102 (CONSUMER_GAP 94 =
  tload face 1 + loader sample 1 + first-read bound 92; table_req rides beside cmd, so die lane / row hops cancel; GEN must
  give table_req the cmd-lane latency). Decode 406 -> 407 entries, head still at 476, nent 1009/1023. Exact round trip of
  the source image through the packer. Images: images/calr10 (rel), calr10n (none = blocker), calr10a (abs stage 1).
- Price: +76 edges per layer, serial at the layer start (ledger claude/qw-tlprod-ledger-1020 replaces the QW-CALR
  124-cycle bound). Overlap with the previous layer (0 cycles) needs the per-user table-bank lifetime certificate
  (table_load_windows.validate: previous layer's last table read) from the layer compiler: owed, not assumed.

## Evidence (Verilator 5.050, ep6 /srv/opentallas-scratch/claude/qw-tlprod-1020, ot-run oth-ubuntu-2146458-1792562367)
- Bounded netlist rtl/qwen_dv/lp9d_np (same chain as ctlm9c): construct 67,558 -> 68,742 cells (+115 vs lp9c_np), 13
  macros; native census PASS max 32; textbook WARN (ck_core 11,928 FF + 12 macro pins, +24 = pst); depth 718.5 ps / 24 lv
  (unchanged); reset 1 sink; in->out 0.
- Landed lockstep tb_np10 (flat RTL vs lp9d_np): ctlm9c regression rnd_mut0 PASS / mut1, mut2 FAIL, calr_mut0 PASS,
  calr_rommut FAIL; **tok_rel PASS**: real produced image installed through dh, user 0 plays stages 0..37 from the face:
  36 table_req on BOTH flat and netlist outputs, user 0, stages 1..36 in layer order, fixed latency 11 from each stage
  start, image_ready 1 throughout; tok_rel_rnd (random starts on the new image) PASS. Mutants: tok_norel (old image) FAIL
  0 loads; tok_abs1 FAIL 35 wrong-stage loads (netlist too); tok_drop17 (flat CAL_MUT 35) FAIL 35 loads.
- Unit calr_rel (NU 4, user 0 descriptor + users 1..3 explicit decode range = OPSEG filler starts): m0 PASS 144 loads
  (36/user, right stage+user, latency 9, no fault); m35 FAIL 140; none FAIL 0; abs1 FAIL 140 bad. calr_port regression
  (vs F16 reference, old image): m0 PASS, m34 / m2 FAIL.
- Capacity: calr_capacity.py --require-producer PASS on calr10 (safe8u / safe8bu fills unchanged), FAIL on the old image.
- Not covered here: slice-side content (stage -> PROG/BTAB/CROM rows) is the closed qfd_dv_slice_tload/f16_tload bench.

## SAFE checklist (ctlm9d vs ctlm9c): 1 pins unchanged; 2 reach unchanged; 3 fanout native max 32 PASS; 4 depth 718.5 ps
/24 lv unchanged; 5 storage +24 flops (pst) PASS; 6 floorplan unchanged (same macros/slots); 7 clock: +24 FF on ck_core;
8 schedule: +76 edges/layer priced (ledger).
## NEXT
Kit safe9c (+_b) = TTC8 winner + **lp9d_np** (not lp9c_np) + 2 ROM266 (calendar_m0/m1 = images/calr10) + wtn child;
die GEN: table_req lane latency == cmd lane; mu_opcal: fillers' first op group must start at the decode first entry
(REL entry inside it); layer compiler: lifetime certificate -> overlap (76 -> 0); toksim with the ledger.
