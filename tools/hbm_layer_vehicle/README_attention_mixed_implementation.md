# Mixed attention context implementation packet

This increment provides isolated opt-in components and compiler support. Shared feed/group, banked apps and the canonical issuer are not edited. Integration remains held for explicit coordinator/root acceptance; this is not a physical qualification.

## Exact issuer clone and layout

`ot_hbm_svc_sm_issuer_rel_class` clones exact825607a54. The frozen reference SHA256 is `6acb3e9d66d70ceb211c86a317868e10bb15716787fdf9b3815a08b57d407d07`; it is also the source at main944bbb859. Clone SHA256 is `33e042c922bcf3a9cef389ef2031c9ef012325b4232a96ac23f3cd1199cfbce3`.

The baseline context is range[45:0], width46; bit46 was outside that port. The clone is range[46:0], width47. There is no bit47. Descriptor197 enters the new top bit110 of each111-bit S/G queue, then context bit46. The old lower46 mapping is unchanged: row_off45:34, tag33:24, epoch23:8, bank7, lstep6:3, fl2, mode1:0. A/P remain200 bits; reserved descriptor[231:200] remains zero. The source layout audit checks every slice for overlap/gaps and reverses only the declared module/port/class changes to reproduce the exact canonical source bytes. All cohort logic is consequently identical.

The clone retains ID_COHORT's default for source compatibility; strict use must instantiate ID_COHORT=1 and wire ids_cohort16. The new module's selection is the semantic opt-in; it does not replace the canonical source. Its negative controls CLASS_MUT1/2 drop the class or incorrectly select the live A-stage class.

The actual-SRAM component bench compares all original status/handshakes and valid reserve/start/programme payloads, including low46 context, against the frozen reference. It independently checks the new class against the test descriptor mode table. Verilator5.050 PASS:994 comparison cycles,17 GO events, two complete eight-descriptor runs on the same layer with distinct fresh token cohorts, zero low46/class mismatches. Stale prior cohort, wrong layer, duplicate IDs and absent IDs at a fixed routed deadline are rejected. Both class mutants fail the independent oracle. Receipts are under `results/rtl/hbm_ds_layer_tput_1018/attention_issuer_class_1019/`; the layout audit is under `attention_mixed_guard_1019/issuer_layout_audit.json`.

The clone deliberately inherits the known native frontend control/reset failures, including the414-load cone. No mapped fanout, reset, reach, clock or timing claim is made.

## Class checker and common integration ownership

The standalone `ot_hbm_svc_command_class_guard` is off by default and checks each actual A2 command for context validity, decoder-invalid mode3 and descriptor-class disagreement with actual mode[2]. It does not gate its examination away when metadata-valid is false. Mode7 is a legal DeepSeek PV4 mode; the guard must not reject all attention modes whose low bits are3. Qwen h128-specific illegal configurations remain the actual frontend's responsibility.

Guard component positive PASS covers12 offers including modes0/1/2/4/5/6/7, mode3 rejection, missing context, reset recovery and disabled defaults. Descriptor/command class-flip controls both fail. The actual retained HBM+SVG+XC+SM frontend also rejects a mode3 command at cycle1855; its frontend source hash matches main944bbb859. These are separate proofs; they do not claim that the guard is already integrated into the shared frontend.

The agreed integration names are `command_class_observe` and `command_context_valid_observe`. Both join the actual R/C command token, select R for PREL0 and C for PREL1, and join native d1/d2. Format injection overrides the C class/valid with the current word's context, even if the preceding C slot was empty. Extension-only magic words require valid metadata even when SVG low83 are zero.

The robust SVG envelope is85 bits: command83+class+valid. XC's existing context5 already contains full descriptor mode[4:2], hence class at bit4. XC compares only after mrel rewriting, R/C selection and command alignment. Its command envelope111 plus KV_DESC64 is a full175-bit aligned record. The banked-app owner implements local inline fault registration equivalent to the guard; parent owns final feed/group integration and the final assembled-command check. A local XC fault does not replace checking SVG's class against the final assembled192-bit command. Total proposed additional source state with explicit validity and both guards is89 FF bits; mapped accounting remains open.

## Compiler support and validation

`compile_attention(..., mixed_context=True)` writes descriptor modes4/6/7 but preserves literal programme words, HBM contents, X writes, GO timing and outputs. The metadata-only audit confirms exactly32 descriptor rows change only mode195:197 for a full64-row KV8 run. The ordinary default event image hashes still match the original KV8 proof byte for byte. No probability-store pread or observational req_lead field is changed.

Native timing arguments are `native_padding`, `command_extra`, `calendar_extra` and `programme_done_extra`, all zero by default. Read admission stays7. Compiler/API profiles prove command9/READ6 and command11/READ8 with historical padding19, done0/2 and residual tail2. These profiles do not select actual native RTL. Parent has since selected a newer leaf8/metadata8 path with prefetch22; callers must supply that actual source-bound padding, not assume the historical19 profile is current. The low-level compiler already accepts22. The old storage-only64-row proofs remain unchanged.

The audit enumerates440 actual DeepSeek fixture programmes across L02/L14, subruns0/8/32, covering164,532 magic words, all attention class1. An independent source proof audits every cal.set and mode-fill branch in the actual DS and Qwen compilers: DS emits modes4/6/7 and Qwen emits modes4/6, independent of operands, row count or result calibration. The compiler/frontend hashes match main944bbb859. Qwen's coordinator reports no currently source-qualified selected HBM fixture/calibration; selected-production Qwen binding coverage therefore remains OPEN. Historical q_land54 and ROM fixtures are not substituted.

A legal programme may change class. `attention_mode_contract.analyse` exposes explicit segment ranges and GO split cost rather than silently declaring it unsupported. The three-word mode-only dense→attention→dense example requires two additional descriptors, four installation ingress rows, and at least20 extra idle stream edges under banked-native timing. Conservatively reloading a64-line block per split adds17,408 physical HBM bytes. Existing literal commands need not change; retire/reopen and fresh epoch are scheduled per segment. Any live-state boundary must be recompiled and certified drained; a split plan is not evidence that an unscheduled mixed programme executed.

Before adoption: explicitly accept the audited clone, complete banked/common integration with source-bound timing, prove alternating dense/attention/dense on the actual assembled frontend with mismatch mutants, qualify the selected Qwen service binding, and complete physical, writer, descriptor and throughput gates.
