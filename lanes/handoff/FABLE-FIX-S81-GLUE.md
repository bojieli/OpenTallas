# FABLE-FIX-S81-GLUE handoff (glue = QC die qwen_compute, design dp_glue / qfd_qc_glue_part)

Last update: 2026-11-19 01:00 PST. All kits survived the Fable limit (checked 00:57: 5 ot-run clients alive).

## State in one paragraph
Gate read of wave glue attempt_6 (s29q103S4Q9N3): TT -130.39 / 648 ends at GRT. 385 ends = u_record logic depth: FIXED and on
main. 263 ends are register placement / distance, NOT fixed yet: 5 private kits are testing placement keys. Nothing is adopted
in the QC wave tree yet; no wave row was touched.

## Done (main)
- 8f62c2edcaad: rtl/qwen_split/qfd_sys_face_record_port_n32.sv regenerated (sha256 919f726936a6), depth 25 -> 13 levels,
  0 cycles, identical ports (36 source copies, 54 reset leaves), so NO bind / LATCHECK change. Readable source
  qfd_sys_face_record_port_bal.sv; generator command `bash tools/qwen_split/record32/regen_n32.sh --install`.
  Proof: one-edge transition + output SAT of the EMITTED graph vs the original source (2018 comparisons, PASS; 3 gate mutants
  refuted), Verilator lockstep 53,803 checks incl 48 protocol episodes PASS, 3 mutants FAIL. Evidence
  results/arch/qw_record32_bal_1119.
- 92b29f6c5791: qfd_sys_face_lctx3_core.sv tcyc + 1 / pos + 1 with kept byte carries (sha256 8fc1850d23f9), proven equal
  (tools/qwen_split/sysface32/prove_inc_bytes.sh); kept nets survive kit synth (kit C 1_2_yosys.v).
- Brief corrections: the kit binds the n32 file, not _opt; the digest round is 2 XOR levels, the depth was wide zero checks
  and 64/80-bit compares in front of priority muxes.

## Open classes (wave attempt_6 GRT DB, exact gate frame; intel2 /srv/opentallas-scratch2/claude/fable-fix-s81-glue-sta/out)
Every one of the 263 flops has +295..+760 ps on its Q side (balance.txt): placement, not logic.
- (a) rom_qr -> tt_pw / dh_prog, 68 ends, -130: ROM at y 450, pin registers at y 1463, tt_pw / dh_prog sit next to the pin
  registers, one 1.1 mm hop.
- (b) u_embed_prov.g_rope rope FF memory: mem 104 at -52, rq 38 at -82 (3 HB4 hold buffers on the setup path), u_bout
  embed_code_q 35 at -50.
- (c) sys_face obs_fault -116 (1 mm hop). (d) tcyc -92, pos -24 (fixed by 92b29f6c5791). (e) ctx_x 7 at -16,
  emb_word_data 3 at -13.
- The wave kit's GRT-basis TT repair died with RSZ-0074 (tt_setup_repair.tcl line 136) at -105.9, so the gate read the
  unrepaired DB.

## Running: private kits, intel2, goal grt, ot-run 64 GB / 16 thr, started 00:20-00:45
Base = wave glue attempt_6 gen copy (epyc9 kw43-wave-1109n/.../items/glue/attempt_6/gen). Dirs
/srv/opentallas-scratch2/claude/fable-fix-s81-glue-kit{,b,c,d,e}/gen/glue, log run_grt.log, README.txt in each.
- A  kit   record n32 only
- B  kitb  + OT_GPL_SPARSE_OVERFLOW=0.25
- C  kitc  B + core incrementers
- D  kitd  record + incrementers + GLOBAL_PLACEMENT_ARGS reweight {79 64 49 29 21 15}, net weight max 8
- E  kite  record + incrementers + sparse exit 0.25 + reweight {79 64 49 40 32}, weight max 8
Wave timing for reference: place ~1 h after synth, CTS TT read ~3 h, GRT ~6-7 h. Expect GRT TT 07:00-08:00.
Read: postcts_gate_tt.json (setup_wns_est_ps, parasitics global_routing = the GRT gate), tt_setup_measure.log.
Probe tools: fable-fix-s81-glue-sta/probe/{run.sh,probe.tcl,sum.py} (class table + register positions of any stage ODB);
keep33.sh keeps each kit's 3_3_place_gp.odb there; balance.tcl = prototype that moves a failing flop toward its source by
(sQ - sD)/2 (mechanics tested only, numbers not yet meaningful).

## Next
1. Per kit at 3_3 / CTS / GRT: class table + where tt_pw / dh_prog / obs_fault landed (probe/run.sh KIT STAGE_ODB RCMODE).
2. Post GRT TT per kit. Adopt the winning keys for glue with kit_wave_edit item_env (candidates OT_GPL_SPARSE_OVERFLOW,
   GLOBAL_PLACEMENT_ARGS).
3. Adoption of the two RTL files in the QC live tree is the die owner's step (DIE-QC-103): src_manifest delta-make to
   92b29f6c5791 or later -> live_tree.py apply --die qwen_compute; files rtl/qwen_split/qfd_sys_face_record_port_n32.sv and
   qfd_sys_face_lctx3_core.sv. Then glue retry (kit_wave_edit). Sign-off export is automatic (auto_export.py).
4. If (a) / (c) stay after D / E: a placement rule (register between a macro-side source and a FIRM pin register goes to the
   mid-point; relay_mid.tcl cannot do it, the D side is logic) or one relay stage; (b) needs the hold pads off the common
   tail of the rope read mux.

## Clones / paths
Lane clone epyc9 /srv/opentallas-scratch2/claude/fable-fix-s81-glue (HEAD = main 92b29f6c5791, clean except bench/).
Work files epyc9 /srv/opentallas-scratch2/claude/fable-fix-s81-glue-work. Posts lanes/posts/FABLE-FIX-S81-GLUE.md.
