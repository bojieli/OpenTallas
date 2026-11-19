# FABLE-FIX-S81-GLUE handoff (glue = QC die qwen_compute, design dp_glue / qfd_qc_glue_part)

Last update: 2026-11-19 01:10 PST. All kits survived the Fable limit (checked 00:57: 5 ot-run clients alive).

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

## Relay form (COORD order 01:0x: prepare in parallel, first form at GRT TT >= -42 wins)
- F  kitf  record n32 + RELAY-FORM core + mid_place.tcl + D placement keys, launched 01:08, goal grt.
  Core variant epyc9 fable-fix-s81-glue-work/lctx3_core.relay.sv (sha256 645ae0a06a54, NOT on main): row decode registers
  tt_pw_a / dh_prog_a, then tt_pw / dh_prog as a plain relay (+1 cycle on TT pw and seq_dh program rows; only the 3 valid
  bits reset, rst_bpay region stays 218). Kit-private hook gen/glue/mid_place.tcl (sourced after relay_mid in
  face_flops.tcl): the relay flops FIRM at the mid-point ROM <-> u_bout pin registers, released with ot_relay_mid.txt.
  First check: 3_3_place_gp.log line OT_MID_PLACE (a Tcl error there fails the place stage: fix the hook, relaunch).
- NOT done for the relay form: (1) latency proof: +1 cycle on tt_pw / seq_dh[186:44] program rows vs prog_busy / the receipt
  ledgers (self-timed by program_obs2, so expected benign, unproven) with the sys_face bench
  (rtl/test/qwen_split/run_sys_face_native32_protocol.sh needs the INTERMEDIATE wrappers); (2) bind / LATCHECK rows for the
  two ports; (3) obs_fault relay (the flop is in the bound wrapper, a bind / plan row for QC-PLAN-R3); (4) the mid-point
  hook as a gen_phys opt-in if F wins. Do not push the relay core before (1) and (2).
- QC-PLAN-R3 adopts the two pushed RTL files (COORD 01:0x).

## CURRENT STATE 2026-11-19 03:55 PST (rebuilt: between 01:32 and 03:45 this file was overwritten with other lanes'
## handoffs by a shared scratch file name; the sections above are the 01:01 text, this section replaces everything later)

### On main
- 8f62c2edcaad record port n32 depth 25 -> 13 (0 cycles). 92b29f6c5791 lctx3 core tcyc / pos kept-byte-carry incrementers.
- 5a45c6152e06 lctx3 core program-row relay behind define OT_QC_SF_PROG_RELAY (default off). Proof
  tools/qwen_split/sysface32/prove_relay.sh OLD_CORE GLUE_KIT_RTL_DIR: off == old core, on == old core + one-cycle relay on
  tt_pw and seq_dh[186:44]; both SAT no model. No lane K change (latency.lanes.glue__tt_pw_pw / glue__seq_dh_dh stay 9).
  Row + package: lanes/handoff/FABLE-FIX-S81-GLUE-relay/ (also the obs_fault row request). With QC-PLAN-R3 for N4.5.
- 1fd3d8bd5139 PLACE-REGION: plan key partition_types.<type>.place_regions [{name, inst_re, util 0.55, centre_um | near_re}],
  gen_phys install_place_regions, tools/die_plan/place_regions.tcl, test_place_regions.py. Default util STILL 0.55.
  Pushed --no-test (test_gen_phys_cap_budget ...explicit_cells... already fails on main; WAVE-PILOT has it).

### Glue private kits (intel2 /srv/opentallas-scratch2/claude/fable-fix-s81-glue-kit{,d,e,f}; goal grt)
- A (record only, control): post-CTS TT measure -24.02 / tns -72. D, E (timing-driven keys), F (always-on relay form +
  mid-point hook; the WINNER at placement: pre-CTS estimate -10 ps, no tt_pw / dh_prog / u_record end left): all in CTS,
  no TT read yet. Cancel D and E at their first CTS read unless it beats F (COORD).
- Cancelled: B, C (sparse exit: no gain), G. FAILED: H (two 55 % regions) at 3_5 DPL-0033 on ~34 u_record cells; regions
  were sized before the place resize. LEAF / COLL-CORE lanes warned to use util 0.35-0.40.
- The wave glue attempt_6 gen dir on epyc9 is gone: build new glue kits from an existing private kit's gen files.
- Read: postcts_gate_tt.json (parasitics global_routing = the GRT gate), tt_setup_measure.log. Probe tools:
  fable-fix-s81-glue-sta/probe/{probe.tcl,sum.py,p_any.sh}.

### tt_ctlm (QC type) private kits (intel2 fable-fix-s81-ttctlm-kit{a,b}; --priority proof; in 3_5 detailed placement)
- a = u_core fence (180,30)-(400,258) um + timing-driven keys; b = a + ABC-resynthesised u_core netlist
  (fable-fix-s81-glue-sta/ttctlm/regen/new.sv sha256 c5017230f4ed, 16 levels, abc cec equivalent to c09b67b7cc1c, all
  20,478 flop lines verbatim; tools tojson.py / abc_s8.script / regen.py / tocomb.py there, NOT in the repo).
  Zero-wire STA: base +18 ps, resynth +346..+402. Fence honoured at global placement (99.2 % inside).
- QC-PLAN-R3 (03:5x): the QC partition is 31 % utilised (my 10 % figure was std cells over the whole kit area), attempts
  5 / 7 failed the pre-route check on port-register clock latency 290-294 vs 250 ps (2,734 port registers), attempt 8 died
  in GRT exit 247. So read pinreg_mean_ps in postcts_gate_tt.json of kits a / b first; a fence does not address it.
- Winner -> main: replace rtl/qwen_dv/headprep13/corepub39/qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1.sv, pin the sha in
  tools/qwen_split/headprep_corepub_source.py CONTRACTS, add the regen tools, trailer Fixes-Items: qwen_compute/tt_ctlm*.

### Clones
Lane clone epyc9 /srv/opentallas-scratch2/claude/fable-fix-s81-glue (HEAD = my last push 1fd3d8bd5139 line). Work dir
epyc9 fable-fix-s81-glue-work (relayproof2/, kitrtl/). Local scratch files of this lane live under scratchpad/fxglue/ only.

### tt_ctlm port-register clock latency kit (COORD 04:0x): NOT launched, blocked on the plan / gen chain
- tap_resolve.py (main a3d70cd04da) refuses tt_ctlm: clock.tap_mode is 'density' (it appends only to explicit or
  grid+explicit tables). Log epyc9 fable-fix-s81-glue-work/tap_resolve.log; register dump ttctlm_regs.json (41,260 regs).
- Port-bank registers (u_bin / u_bout / u_lpad, 3,117): 1,602 on the right edge (x ~770), 827 on the bottom edge, 71 top,
  617 inside. The kit has 62 tap ports clk_t1..62; taps are kit PORTS, so new taps change the bound RTL ports, SDC and pins:
  a kit with new taps needs plan change -> bind kit-rtl -> gen.py phys (the wave chain), not a hand edit of a kit.
  No gen command is recorded in the kit or the attempt dir (logs/ empty); kit_wave.py builds it.
- Asked QC-PLAN-R3: either an explicit / grid+explicit tap table for tt_ctlm (then tap_resolve --span-um 300 runs), or the
  gen chain command for a private kit. Resynth netlist to put on top: fable-fix-s81-glue-sta/ttctlm/regen/new.sv.
