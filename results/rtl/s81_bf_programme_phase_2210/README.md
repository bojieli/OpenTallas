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
Their absence is preserved in `current_phase106_inputs.json`; no hashes or
proof records are rewritten. The profile's full source-hash guard therefore
cannot honestly claim current production qualification there. After the XS
selector source event, that profile also needs explicit correspondence for
the changed simulation selector source; the old hash must not be relabeled.
A coherent source/manifest/schedule staging event is the next concrete step.

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
