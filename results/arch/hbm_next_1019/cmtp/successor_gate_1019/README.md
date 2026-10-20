# P3 CMTP successor admission, 2026-10-19

The whole-token image gate now rejects native FUSED phase/operand violations
before claiming an executable P3 calendar. All six original P3 images remain
byte-identical. The old I1–I6 gate returned zero violations for each image;
the integrated I7 gate finds 363 violations in AR/users N1 and 403 in MTP N6
and users N2/N3/N4. These are counts of rule violations, not distinct records.
The first is the real HC_PRE_NORM gain B residing in HBM while the lane reads VM.

This imports the existing source-owned `fused_phase_check.py` from
`claude/hbm-next-units-fushub-1019`, and invokes its F1–F4 rules from
`image_check.check_image`. The former image mutants now require their own I2/I3/I4/I5
failure: an existing FUSED rejection cannot falsely witness an unrelated mutant.
Existing I1–I6 results and loop summaries remain exact in the comparison.

GQ s3 launch-to-fire is 4 edges, copied exactly from
`claude/hnx-gq-s3-1019@7a7f7112a` (formerly 3). Issue-relative bank/read/write
calendars are unchanged. The model's opt-in `gq_s3` measurement key charges
COLL.ROW_GATHER one cycle per descriptor, including AR, without changing further-row
II. It is deliberately absent from historical/default measurement sets. Other
COLL lowering and native descriptor execution remain unbound. No new token-rate
headline is justified by this partial cost hook.

## Verification

Unpinned ot-run selected ot-epyc8, unit `oth-ubuntu-287256-1792456695`, exit 0.
Admission: 1 thread, 4 GB RAM, 2 GB scratch for a Python-only image/source regression;
all six inputs total 3.7 MB. No HDL/native build or physical engine ran.
`run.log`, `successor_result.json` and `RUN_SOURCES.sha256` preserve the exact run.
The final source adds only the descriptive `MEAS['gq_s3']` metadata after this run;
the tested implementation and final implementation are otherwise identical.

- Eleven encoded FUSED cases: legal PRE phase0 and POST phase0/5 pass; eight real
  phase/space/alignment/stride/gain violations fail their expected rule.
- Six whole images: non-I7 violations and loop summaries equal the frozen parent
  checker; I7 matches the independent per-record F1–F4 enumeration exactly.
- Five image mutants per applicable image require their named invariant.
- GQ fire-relative calendars compare exactly over all quadrants and three shapes;
  launch epoch advances one edge. The model defaults remain unchanged; row and
  non-row gather each gain exactly one cycle; TOPK merge is unchanged.

## Next structural work and qualification limits

These images cannot enter a healthy layer replay or physical dispatcher gate.
Fix the allocator against the existing native FUSED contract: PRE A/B/O must
share phase0, every row stride must preserve it, gain must be installed by a real
DMA.LOAD before first use, and POST C must have a genuinely aligned producer
(the old HC_MIX O+4 interior pointer cannot be renamed into alignment). Preserve
the golden reduction and exact payload dependencies, re-run I1–I7 and native
value-front replay on the emitted addresses, then charge DMA, padded allocation,
GQ descriptor launch and actual relay hops in the static SU/MU calendar.

The factored-cardinality proposal is still uninstalled: descriptor lowering,
all-layer resident kernel/metadata stores, boot installation, native unit ports,
TT/FF timing, SRAM access, and actual prefix preparation remain open. Prior
3370.44 MTP / 1035.72 per-user numbers are conditional historical estimates;
this packet establishes no numerical token PASS, dispatcher route, or adoption.

The original die chain f4c_t9p3r and both GQ s3 gates continue progressing without
restarts. This bounded compiler repair neither changes nor duplicates those jobs.
