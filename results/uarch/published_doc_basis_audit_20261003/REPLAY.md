# Published-document basis audit replay

Base: `dcba5c0ab0a61485b8e4a2fd59e591151e8f9f3d`. Branch: `codex/ds-hbm-doc-basis-review-20261003`. TASKS active queue also transfers streaming KV model ownership to Claude, keeps Ampere/Euclid physical/source ownership and Russell publication-only, and prepares future native DS PC11 alongside actual R58 PC0–4 scope. The parent calibration reference is `c5ae2f69d`: full wire overrides, with current collective/service calibration unknown. No engine/model/calendar changes, model regeneration, hardware builds or job restarts. Parent owns merge and push.

Run from the repository root at this milestone commit:

```sh
python3 results/uarch/published_doc_basis_audit_20261003/verify.py
python3 tools/audit_prose_figure_coverage.py --check
make check-figures
git diff --check
```

`proof-r1.json` pins the final documents/census, twelve unchanged records/source declarations and thirty-one exact JSON assertions. The verifier compares each unchanged source with the base Git object as well as SHA256. `edits-r1.json` records thirty-six scoped before/after edits and their individual record bases. Additional status prose and Atlas/figure labels are reviewable in the commit diff. No global numeric substitution is performed.

Selected DS row: `hbm_gpu.json#rows[design=v41_hbm_gpu_groupslot]`, 2,801.8 tok/s / 356.9 µs, 73.7 µs matvec, 24.8 µs barrier. The modeled 1.0339 GHz and 78-cycle boundary are explicit. Companion speculation, saturation, energy and adaptive cells bind their own records. The independent `fabric.json` 0.668 µs sweep remains 2,919.7, rounded to 2,920, and is expressly distinguished. This verifies existing published record basis, not current-source model recomputation or product-rate qualification.

QROM: budget `die_split.kind` explicitly TP-2; historical AR 10,873.6 and DFlash 18,719.9 remain numerically unchanged. Current `QWEN_ROM_PRODUCT` declares TP-4, AR without a drafter. TP-4 terminal replay is exact at position zero and SU64 runtime scope with `adoption=false`. The existing seven-fill successor remains G0 FAIL with no measured sustained PHY bandwidth or hardware admission. No replacement TP-4 rate is asserted.

`HEADLINE_BUNDLE.md` and its JSON remain byte-exact. The generator's byte-exact check forbids editing its descriptions by hand; the new `docs/HEADLINE_BUNDLE_SCOPE.md` supplies historical/nonadopted configuration scope, linked from Atlas lead/current state/conclusion and the microarchitecture document. The generator itself is unchanged. Retained Atlas anchors remain inside visibly historical rows so all existing numeric/source bindings continue to resolve.

Census regeneration:

```sh
python3 tools/audit_prose_figure_coverage.py
```

The regenerated census has 4,013 untriaged candidates. Both visible count annotations in `docs/EVIDENCE_LEDGER.md` and `docs/UNIFIED_EXECUTION_CHECKLIST.md` are synchronized, followed by a second census generation. The TASKS update changes the existing active rows/paragraphs rather than appending an integration diary. `check-figures-r2-tasks.log` preserves the intermediate FAIL after TASKS added seven census candidates and before its two annotations were resynchronized. `check-figures-r3-final.log` records the final full gate; `census-r4-final.log` retains the final regeneration. All logs are retained. `headline-anchor-FAIL-r1.log` records the first label edit's literal-anchor failure; the subsequent correction restores those anchors without changing any numerical record. `check-figures-r1.log` records PASS, including the existing unavailable build-product reference and pre-existing historical stale-pin counts. This audit does not claim to clear those unrelated findings or any G0–G5 gate.
