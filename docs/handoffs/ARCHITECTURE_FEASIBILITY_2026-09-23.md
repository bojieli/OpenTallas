# Architecture feasibility handoff — 2026-09-23 (revised end of day)

**Read [the analytical report](../ANALYTICAL_REPORT.md) first.** It is now the
project's only analytical performance report. Earlier the same day this handoff
listed about twenty analytical screens and proposals. All of them, together
with their audit scripts, tests and results, were deleted at the user's
direction and superseded by that report.

## What changed today

1. **Framework corrected.** A review found four calculation defects:
   - aggregate and energy ratios paired mismatched designs;
   - energy was charged at full pipelines;
   - the GPU was charged mixed layouts;
   - compute-in-ROM capacity was charged per bit.

   All four are fixed. Prefill, a batch sweep to 4,096, expert-parallel GPUs
   and the GB200 NVL72 domain were added. The Taalas HC1 gate now passes at
   1.45×.
2. **ROM machine redesigned** from hardware limits:
   - four-die UCIe packages, with ~10 ns die hops;
   - direct SerDes package mesh, with ~100 ns hops and no software;
   - experts striped across all ROM banks;
   - one layer per package, pipelined across packages.
3. **HBM machine kept general-purpose**, on B200 or A100 NVLink (HGX and NVL72)
   with its best layout per metric. Specialised links are a property of the
   model-specific ROM machine only (user direction).
4. **Headline at N5 against B200:**
   - DeepSeek-V4.1-Flash: 3.87× per user at batch 1, 8.52× at 64 users;
   - each side at its best: 3.18× throughput, 3.97× tokens per joule;
   - Qwen3-8B: ~19× per user at batch 1.

   Most of the large-model gain comes from specialisation. With GPU-class
   links, weights in ROM alone only tie for a single user.
5. **Deleted** as legacy analytical reports:
   - the documents listed in [the docs index](../README.md);
   - the iso-node REPORT.md files (their JSON and CSV stay, because
     implementation tools read them);
   - the `tools/audit_v41_*`, Qwen, HC1 and redesign screens, with their tests
     and results.

## Where to continue

The user's standing goal is to redesign, re-implement and simulate both
machines to best practice. The analytical phase is done; next is
implementation and simulation.

1. **The three specialisation mechanisms the report credits** are not in RTL:
   - striped expert banks (bank address map, conflict-free stream schedule);
   - package-level die-to-die and package-to-package links with bounded
     latency;
   - the layer-per-package pipeline.

   Build and simulate them in the existing ROM service RTL
   ([ROM service RTL](../ROM_SERVICE_RTL.md)) and the V4.1 plan
   ([V4.1 ROM implementation plan](../DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md)).
2. **Keep the HBM baseline at best practice** in any simulated comparison:
   expert parallelism, NVL72-class domains, native FP4/FP8.
3. **Open analytical limits** (report §8):
   - ROM read bandwidth evidence;
   - striped-bank macro qualification;
   - link latency floors;
   - ROM power (HC1 power gate 0.44×);
   - hot-expert skew;
   - cost.

## Workspace notes

- Work on `main`, and stage by explicit path: a concurrent session shares this
  checkout.
- Push with
  `git -c credential.helper= -c 'credential.helper=!gh auth git-credential' push https://github.com/bojieli/OpenTallas.git main:main`.
- `results/roofline/n5_vs_b200/analytical.json` is ~96 MB, close to GitHub's
  100 MB file limit. A larger sweep will need the artifact split or compacted.
- Regenerating the roofline studies takes ~26 minutes. The speculative layer
  must be re-run afterwards (`make speculative`), and so must
  `tools/audit_rom_iso_area_*.py`.
