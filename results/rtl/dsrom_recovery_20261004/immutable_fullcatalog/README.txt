CURRENT S81 all-occupied-stage immutable field control catalog (opt-in)

Source compiler: tools/dsrom_s81_target_field_controls.py::emit_native_catalog,
using the existing emit_native_stage_tables byte-identical body linker and
v41_die_images_w17w10 codec. Canonical source pins are in manifest.json.
The current authoritative matrix_map has 46671 phases across stages0..73;
stages74..80 contain no field matrices. No inferred assignment/repartition.

Generate NEW images (not needed to consume committed images):
python3 tools/dsrom_s81_target_field_controls.py --owner . --layer 20 --rank 0 \
  --stage-tables all \
  --reuse-stage-images results/rtl/dsrom_recovery_20261004/immutable_stage_controls \
  --out NEW_OUT
The accepted stage37/38 images are referenced unchanged, without repeating
phase/body checks or copying them. Other occupied stages use the SAME existing
per-phase byte equality and actual packed PHROM decode checks. No inference,
checkpoint read, emitted activation, RTL/native build, observer, or P&R.

Consumer API: read manifest.json; require complete=true AND
all_occupied_stages_ready=true for a whole-system static-provider source claim.
Each stages[] record has the actual image_path (repository-relative), binding
file/hash, hex hashes, PHW/SAW capacities, canonical phase count, exact unique
body/word counts, original unshared count, and rank/die/valid-key counts.
Resolve image_path relative to the repository root. A blocked record has
image_path=null plus exact failure arguments; its remaining phase checks are
explicitly incomplete. Never substitute another stage or a zero image.

New images: binding.json.gz is deterministic compressed JSON with the SAME
per-phase source/template/key/CFG/descriptor/rank-slice witnesses as binding.json.
read_stage_binding(image_dir) accepts exactly one binding.json or binding.json.gz.
linked_native_stream and emit_native_phase_controls(stage_image=image_dir)
retain the existing local control-bundle interface. Provider image inputs are
spine_phase.hex (2048x64), spine_stream.hex (16384x48), and the physical rank's
spine_keys.rankR.hex (1024x32); all full depths and inactive zeros are explicit.
CFG remains the existing source-bound namespace at25*canonicalphase; this
catalog never emits a new CFG mapping. PHROM remains2*canonicalphase/+1;
only PHROM SBASE is relocated. All actual resident expert alternatives are
covered, with source output rounding preserved, not one selected token tuple.
The original generic descriptor text's 'all384' applies to resident MoE
alternatives, not a requirement that every stage contain384 expert phases.

Only complete48-bit bodies that compare byte-identically share an offset,
within EACH stage. No across-stage sharing or shape-only equivalence. Source
input/output bases, selectors, and batch position remain existing GO controls;
source-driven shape/rounding conflicts are refused. No phase/key/order/CFG or
arithmetic change. No global port-width, clock, die-class, or hardware change.

Existing RAM/per-actor programming remains the default. Source-image readiness
does not remove host writes or adopt a hardware provider. Epicurus owns actual
provider read/capture/write-path integration and physical timing; Maxwell owns
per-stage provider counts and SAME-provider baseline+47FF composed pricing.
Active-word counts do not shrink the declared ROM depths or erase storage cost.
The full declared extent remains priced by the provider/physical owners.

Terminal source-only generation EXIT0, implementation76114050f.
Counts: {"artifact_files": 506, "manifest_sha256": "eaaa0b429c6bfaae03a2d0053e66af3af8e4bb505c2ab4aebde7314acada31f5", "max_stage_phases": 642, "maximum_stage_stream_words": 1336, "new_phase_checks": 45421, "new_stages": 72, "phases": 46671, "rank_providers": 296, "stages": 74, "unique_bodies": 354, "unique_stream_words": 57008, "unshared_words": 7851904}
Source phase/body/decode checks new45421; accepted1250 checks reused unchanged.
No descriptor conflicts or capacity failures; whole catalog ready.
Existing native command admission guards remain authoritative: static descriptor readiness does not waive a refused ME rounding command.
