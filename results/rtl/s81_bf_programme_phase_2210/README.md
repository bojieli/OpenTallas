# Disabled current CAP-safe H10 BF phase programme

This prepares only u_f_0L01 phase106 (attn.wo_a, six actual rows,
segment0/4, pairs1/5/10) as a source image overlay. The current field is
`intel1:/srv/opentallas-scratch2/claude/codex-ds-compiler-1101/down_cap_safe_fields_1131/u_f_0L01`.
The base field, active ROM aliases, cohort, canonical manifest, RTL and
all production defaults remain untouched. This is not a whole-token result.

The cause of all1800 empty BF phase records is the intentional measured-profile
gate: `xs_bf.load_meas()` defaults to historical
`results/rtl/s81_layer_tput_1018/compiler/bench_xsb/measure.json`.
`meas_for` requires the exact as-built `col_h10_asb_x|E2|bseg1024` (or H9)
key and refuses shifted/older-variant borrowing. With no matching key,
`bf_plan` returns `calendar_unmeasured`, no descriptors and no return calendar.
`compile_bf` consequently adds nothing to `field.bf_desc`; `write_images`
only inserts descriptors that actually exist. This is not a BF image
namespace failure. The opt-in inputs are `OT_XS_BF_MEAS` plus
`OT_S81_SELECTED_SOURCE_ROOT`; the selected as-built manifest and schedule
must also match (`OT_S81_SELECTED_ASBUILT_MANIFEST`, `OT_XS_ASB_SCHEDULE_DIR`).
No switch is turned on here.

The retained source programme is the real compiler output
`epyc2:/srv/opentallas-scratch2/claude/codex-ds-bf-1131/full0_bf_programmed_scoped`.
It used the H10 three-class static replay profile in
`results/rtl/s81_bf_asbuilt_1101/shape_domain/h10x_candidate.json`.
The current phase's identity, actual rows/segment/stream base, assignment,
golden partials and three actual ROM starts all match that retained phase;
only the measured descriptor/return fields differ. Each pair's 82-bit
programme is the measured OFF4/PER1/N64 descriptor with current actual ROM
base0. OFF is already advanced for the measured front input register;
calling the historical `boundary_descriptor(c10_nlock)` again would be
incorrect and its old source hash is deliberately not bypassed.

The native programme ABI is the 38-bit `f_prog` input: issue[0],
addr[14:1], operand[29:15], segment[32:30], half[33], chain[37:34]. The
82-bit descriptor rides spare [71:48] of CFG words0..3, logical bank
`word%7`, address `4*phase + word//7`. The physical 512-row image interleaves
8 logical addresses per bit column. The adapter uses the existing
`bf_programme_compile.pack/word`; it changes only these actual phase rows
and checks every original lower48 data/control bit and other logical row.
It emits actual go-relative issue words and retained return words, not
invented global source epochs. No RTL stage or clock is added.

The selected native source matches98 of the100 retained H10 profile hashes,
with **zero changed files**. The historical qualification manifest and the
original source schedule JSON are absent in that sparse native worktree.
Their absence from that native worktree is preserved in
`current_phase106_inputs.json`; no hashes or proof records are rewritten. A
private complete retained closure is now staged (all100 exact hashes pass),
and the production-default qualifier rejects its unqualified native GB
provider, as detailed below. After the XS selector source event, the profile
also needs explicit correspondence for the changed simulation selector
source; the old hash must not be relabeled.

The retained replay scope is BF-active/Q-idle with its measured reset/family
profile. Actual activation residency and source epochs, BF row tags,
concurrent Q/BF return use, global mission calendar, physical timing and
production reset/source correspondence remain unqualified. This overlay
neither enables all25 frame phases nor closes any of those contracts.

Actual adapter run passed Intel1 unit oth-ubuntu-553965-1793598947,
exit0: three descriptors, twelve changed mask images, zero RTL cycles.
Fresh actual images are in
`intel1:/srv/opentallas-scratch2/claude/codex-ds-bf-selectors-2200/programme_phase106_overlay1`.
`physical_row_overlay.json` retains all12 exact changed physical rows and
base/candidate hashes; applying it requires the exact original base hashes.
`overlay.json` contains all192 actual issue records plus retained returns.
This is an image-generation check, not a new BF arithmetic/reset simulation.

The two missing retained files have now been faithfully staged privately with
the98 unchanged native files. All100 qualification hashes pass. The exact
qualifier with production-default flags then **fails closed** at the real
remaining guard: `GB frame requires its qualified one-edge-early GO/TAG
provider: col_h10_l4_lp_asb_x` (unit638180-1793599299, exit1).
This is more precise than the initial missing-file diagnosis. The old BF
recompiler used the explicit bench-only `OT_XS_GB_PROVIDER_UNDER_TEST=1`
and `OT_XS_Q_CPR=1`; those flags exercise an unqualified provider and never
set `native_provider_qualified=true`. They can admit the retained experimental
scope, but cannot qualify production. That refusal is retained separately.

A second independently observed open contract is BF return row identity:
`field_rank_images.tag_plan` deliberately skips BF. Actual current phase110
owns rows6..11 but its CFG labels are0..5; tail122 owns24..28 and labels0..4.
Phase106 owns0..5 and therefore happens to coincide. The packet records the
actual extracted labels without editing them or asserting a production
capture failure (the complete consuming mission contract is still absent).

Exact source-profile admission in that original explicit bench-only scope
passed unit677080-1793599463, exit0, `measured_bf_active_idle_q`.
The default production refusal remains unchanged. The private complete
retained source root is
`intel1:/srv/opentallas-scratch2/claude/codex-ds-bf-selectors-2200/source_closure_candidate1`.
No source proof is transferred to the newly proposed selector manifest.
