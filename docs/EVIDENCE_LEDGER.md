# Evidence ledger: every load-bearing number, and whether anything still produces it

**Audited at commit `a782530` (2026-08-30 13:16 UTC).** The working tree was
moving during the audit — five agents and a workflow are editing this
repository — so `results/rtl/abi3_campaign.json`,
`spec/abi3/numeric_contract_union.json`, `compiler/`, `runtime/` and two ABI 3.0
documents were uncommitted-modified when their numbers were read. Rows that
depend on those files are marked **(tree)**.

This ledger exists because of a specific failure mode. Tonight the headline
moved from 54.2× to 8.6× across five independent corrections. Each was applied
to the code and to the generated artifacts. **Prose is not regenerated**, and
`docs/` holds 47 hand-written markdown files carrying roughly 1,100 unit-bearing
numeric tokens. Exactly one file in `docs/` is generated
(`PROGRAM_STATUS.md`, by `tools/build_program_status.py`) and it has not rerun
in 108 commits. Nothing anywhere checks a number in prose against the artifact
that produces it.

**2026-09-02 reconciliation.** The paragraph above is retained as the discovery
state, not a current status claim. `PROGRAM_STATUS.md` has since been generated;
its current retained snapshot binds clean W6.6 closure commit `0a5bc1f…`,
records 83/10/1, and carries `worktree_dirty: false`. The follow-on publication
commit changes only the companion files and these identity pointers.
`tools/check_prose_figures.py` now
checks hundreds of explicit provenance annotations, but unannotated figures
remain outside its visibility, which is why W11.3 is still partial.

`tools/audit_prose_figure_coverage.py` now records the complete Markdown census
under schema v2 and applies the separate, reviewable
`configs/evidence/prose_figure_triage.json` policy.  A rule identifies an exact
document, section, literal, and optional source-line context; it carries a
disposition and rationale, declares how many candidates it must match, and the
audit refuses stale or overlapping rules.  The first deliberately small pass
classifies **8** candidates as ABI norms or examples. <!-- figure: 8 src="results/abi3/prose_figure_coverage.json#totals.unbound_triage.normative_or_example" name="explicitly triaged normative/example prose candidates" -->
It leaves **3,414** explicitly untriaged. <!-- figure: 3414 src="results/abi3/prose_figure_coverage.json#totals.unbound_triage.untriaged" name="prose candidates still awaiting triage" -->
No document-wide default is allowed, and neither the new classification nor a
snapshot entry is evidence that a result is correct.  Produced figures still
need resolving `figure:` annotations; external values need named sources; and
load-bearing calculations without artifacts remain `missing_producer` work.

The storage-equivalence rows in §3a are also reconciled beyond the discovery
snapshot: the overwritten artifacts now use the explicit v2
storage-and-placement schema and current neutral graphs. Their current numbers
are recorded there as resolved, while the separate cross-product-backend gap
remains OI-19.

## How to read this

**"What produces it"** is a runnable command plus a named artifact field, or it
is the finding. `make roofline` = `python3 tools/run_roofline_studies.py --force`;
`make iso-node` = `python3 tools/build_iso_node_studies.py --write && python3 tools/run_iso_node_studies.py`.

**Grade** uses the vocabulary defined in `configs/hardware/technology.json`
(`grade_definitions`) and enforced by `tools/check_evidence_grades.py`:

| grade | means |
|---|---|
| `measured` | fabricated silicon reported in a peer-reviewed venue |
| `published` | stated by a vendor or standards body for a shipping part |
| `executed` | obtained by running something in this repository, with the artifact committed |
| `derived` | computed from published/measured entries by a stated formula |
| `assumed` | a stated judgement that must be swept |
| **`prose`** | *added by this ledger*: asserted in text only; no artifact, no command, no test |

**Current?** was checked against the regenerated artifact in every case, never
assumed. Where a number appears in prose and in an artifact, both are quoted.

---

# 1. Stale load-bearing claims, ranked by consequence

Ranked by how much of the project's argument rests on the number. Rank 1–5 are
headline claims: a reader who lifts one of them lifts a retracted figure.

## Rank 1 — `docs/WAFER_VERSUS_ARRAY_LATENCY.md` §3: the retracted on-wafer ceiling, unmarked, as the document's sharpest conclusion

This is the worst finding in the repository. The document is the *origin* of the
retracted `116,278` and `81,966 tok/s` figures — they are the reciprocals of its
own §3 numbers (1/8.6 µs = 116,279; 1/12.2 µs = 81,967) — and it carries no
retraction marker anywhere. Its §3 conclusion is stated as
*"**This is the sharpest argument for wafer-scale**"*.

The defect is nameable and isolated: §3 charges an on-wafer all-reduce **one**
hop traversal. The corrected model charges ~1.1 × the mesh diameter, which for a
57-region span is **15.4** traversals. The 100 ns hop input is unchanged; only
the traversal count moved.

| number | where it is stated | what produces it | grade | current? |
|---|---|---|---|---|
| `7.2 µs` on-wafer TP, Qwen3-8B | `docs/WAFER_VERSUS_ARRAY_LATENCY.md:52` | `make roofline` → `results/roofline/n5_vs_b200/REPORT.md:460`, topology row `Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1` = **110.88 µs** (`72 x all_reduce span 57 on on_wafer (traversals 15.4)`) | `derived` | **NO — 15.4× low** |
| `8.6 µs` on-wafer TP, Flash | `docs/WAFER_VERSUS_ARRAY_LATENCY.md:53` | same, `:503` = **132.44 µs** | `derived` | **NO — 15.4× low** |
| `12.2 µs` on-wafer TP, Pro | `docs/WAFER_VERSUS_ARRAY_LATENCY.md:54` | same, `:550` on-wafer term = **187.88 µs** | `derived` | **NO — 15.4× low** |
| "on-wafer costs 7.2–12.2 µs, or **12–21% of the budget, and fits**" | `docs/WAFER_VERSUS_ARRAY_LATENCY.md:58` | against the doc's own 58.8 µs budget (`:18`), 110.88 µs is **189%** of it | `prose` | **NO — inverts the conclusion** |
| "**Wafer** — **15× the latency headroom**, tensor parallelism available" | `docs/WAFER_VERSUS_ARRAY_LATENCY.md:92` | `results/roofline/n5_vs_b200/REPORT.md:19` finding 8: *"the wafer is **at least 2.0x** cheaper"*; per-model 2.0×/8.3×/8.9× | `prose` | **NO — 15× → 2.0–8.9×** |
| implied per-user ceilings `116,278` / `81,966 tok/s` (= 1/8.6 µs, 1/12.2 µs) | `docs/WAFER_VERSUS_ARRAY_LATENCY.md:52–54` (as reciprocals) | `results/roofline/n5_vs_b200/REPORT.md` aggregate column: Qwen `:460` = **9,018.8**, Flash `:503` = **7,550.6**, Pro `:552` (hybrid) = **5,182.0**. Pro under *pure* tensor spans two wafers and falls to **701.6** (`:550`), because the inter-wafer link is charged too. The replacement band is **5,000–9,000** | `derived` | **NO — RETRACTED** |

The corrected claim is pinned by a test:
`tests/test_roofline.py:844 test_on_wafer_tensor_parallelism_no_longer_reaches_taalas_rates`.
The document predates it and does not know it exists.

## Rank 2 — `docs/FIRST_PRINCIPLES_MEMORY_DESIGN.md`: the whole document, including the figure it nominates as the project's headline

The document's own framing is *"This should be stated as the headline of any
write-up, because it is counter-intuitive and it is the project's actual
finding"* (`:123–125`). The figure so nominated is 3.1× too high. Every
DeepSeek row descends from the retracted `entry_bytes 583` / `index_entry_bytes
68` constants. **The three Qwen rows are unaffected and correct** — Qwen's KV
constants never moved.

Recomputed under the current model. There is no command in the repository that
emits this table, so here is one that does — it is the closest thing to a
producer this document has:

```sh
PYTHONPATH=src python3 -c '
from opentallas import workload as W
from opentallas.schema import ModelProfile
for name, ctxs in [("deepseek-v4-flash-0731",[200000,1000000]),
                   ("deepseek-v4-pro-0813",[200000,1000000]),
                   ("qwen3-8b",[1024,8192,32768])]:
    m = ModelProfile.load(f"configs/models/{name}.json")
    wt = W.weight_traffic(m, 1); wb = wt.dense_bytes + wt.routed_bytes
    for c in ctxs:
        kv = W.kv_traffic(m, c)
        print(f"{name:24} ctx={c:>9,} W={wb/1e9:7.3f} GB KVread={kv.read_bytes/1e9:6.3f} GB "
              f"KV/user={kv.storage_bytes_per_user/1e9:6.3f} GB W:KV={wb/kv.read_bytes:6.1f}")'
```


| number | where it is stated | what produces it | grade | current? |
|---|---|---|---|---|
| **260:1** W:KV, Pro @200K — *"the project's actual finding"* | `docs/FIRST_PRINCIPLES_MEMORY_DESIGN.md:32,118` | `opentallas.workload.kv_traffic` on `configs/models/deepseek-v4-pro-0813.json` = **83.8** | `derived` | **NO — 3.10× high** |
| **113** W:KV, Flash @200K | `:30` | `make roofline` → `results/roofline/n5_vs_b200/REPORT.md:162` col `W:KV at B=1` = **35.3**; and `executed` at `results/abi3/deepseek_v4_reference_oracle_context_ladder.json` → `context_ladder_summary.rungs[4].weight_to_kv_read_ratio_at_this_context` = **35.34** | `executed` | **NO — RETRACTED (113.2:1)** |
| **59** W:KV, Pro @1M | `:33` | `results/roofline/n5_vs_b200/REPORT.md:163` = **18.0** | `derived` (Pro is *not* executed — see §5) | **NO — RETRACTED (58.9:1)** |
| **24.5** W:KV, Flash @1M | `:31` | `opentallas.workload` = **7.4** | `derived` | **NO — 3.31× high** |
| `0.099 GB` KV read/token, Flash @200K | `:30` | `results/roofline/n5_vs_b200/REPORT.md:162` col `KV read/token` = **0.317 GB**; executed **317,435,904 B** at ladder rung 200,000 | `executed` | **NO — 3.20× low** |
| `0.674 GB` KV read/token, Pro @1M | `:33` | `results/roofline/n5_vs_b200/REPORT.md:163` = **2.207 GB** | `derived` | **NO — 3.27× low** |
| `0.70 GB` KV/user, Flash @200K | `:54` | `results/roofline/n5_vs_b200/REPORT.md:162` col `KV/user` = **1.382 GB** | `derived` | **NO — 1.97× low** |
| `5.03 GB` KV/user, Pro @1M | `:55` | `:163` = **9.856 GB** | `derived` | **NO — 1.96× low** |
| die counts `226 mm² / 2 / 18 / 2 / 16 / 126 dies` | `:54–55` | derived from the KV/user above; all ~2× low | `derived` | **NO** |
| `0.65 TB/s` KV BW, Flash @200K @6,600 tok/s | `:66` | 0.317 GB × 6,600 = **2.09 TB/s** (1.7 stacks, not 0.5) | `derived` | **NO — 3.2× low** |
| `2.02 TB/s` KV BW, Pro @1M @3,000 tok/s | `:67` | 2.207 GB × 3,000 = **6.62 TB/s** (5.5 stacks, not 1.7) | `derived` | **NO — 3.3× low** |
| `45 GB` / `322 GB` KV capacity at B=64 | `:66–67` | **88.4 GB** / **631 GB** | `derived` | **NO — ~2× low** |
| Qwen rows `100 / 12.5 / 3.1` and `0.15 / 1.21 / 4.83 GB` | `:27–29`, `:51–53` | `opentallas.workload` = **100.2 / 12.5 / 3.1**; storage **0.151 / 1.208 / 4.832 GB** | `derived` | **YES** |

§4's qualitative conclusion (*"Dense Qwen is KV-bandwidth-bound; sparse DeepSeek
is KV-capacity-bound"*) survives, but its margin narrows from 3.8× to 2.2×.
§5's ROM-area table (`:86–91`) is weight-side only and is unaffected.

## Rank 3 — `docs/OVERVIEW.md`: the front-door document, stale in both its headline derivations

`README.md:71–73` sends every new reader here. Two whole sections are
pre-correction, and one of them is a step-by-step derivation — which is worse
than a bare number, because a reader can check the arithmetic and it will be
self-consistent while being wrong.

### 3a. The `113.2×` traffic table — the retracted figure stated live, twice, plus once in a rendered figure

| number | where it is stated | what produces it | grade | current? |
|---|---|---|---|---|
| **113.2×** Weight/KV-read ratio | `docs/OVERVIEW.md:86` (table) and `:92` (twice in one sentence) | `make model-traffic` → `results/model-traffic/sweep.csv`, `weight_to_kv_read_ratio` = **35.3358** | `executed` | **NO — RETRACTED** |
| `99.1018 MB` KV read/token | `docs/OVERVIEW.md:85` | same file, `kv_read_bytes` = **317,456,384** | `executed` | **NO — 3.20× low** |
| `11.2176 GB` weight read/token | `docs/OVERVIEW.md:84` | same file = `11,217,572,060` B | `executed` | **YES** |
| **113.2×** and `99.10 MB / token` as rendered labels | `docs/assets/why-rom.svg`, embedded at `docs/OVERVIEW.md:76` | `python3 tools/render_public_assets.py`; last built commit `a1eb32e` **2026-08-28** | `executed`, stale | **NO** |

`docs/OVERVIEW.md:88–91` says *"Those values come directly from
`results/model-traffic/sweep.csv`"*. Two of the three rows no longer match the
file they cite, so this is a mis-citation as well as a stale number.

### 3b. The `9,399 tokens/s` derivation and the `8.67×` iso-node ratio

The retracted **8.67×** does not appear as a token anywhere — the document states
it **decomposed**, as `14,436 / 1,666`. A grep for `8.67` finds nothing; that is
why it survived.

| number | where it is stated | what produces it | grade | current? |
|---|---|---|---|---|
| `13.106 µs` HBM KV service | `docs/OVERVIEW.md:194` | `make iso-node` → `results/iso-node/n7_architecture_attribution/analytical.json`, `kv_beachfront_C8` = **41.979 µs** | `derived` | **NO — 3.20× low (same KV correction)** |
| `106.392 µs` interval | `docs/OVERVIEW.md:204–205` | recomputing the doc's own formula with the corrected max: **124.222 µs** | `derived` | **NO** |
| **`9,399 tok/s`** N7 central, Flash @200K B=1 | `docs/OVERVIEW.md:184` (heading), `:209`, `:226`, `:242`; pointed at by `README.md:73` | `results/iso-node/n7_architecture_attribution/REPORT.md:74`, `ROM user tok/s` = **8,050.1** | `derived` | **NO** |
| `618 tok/s` A100 same-batch | `docs/OVERVIEW.md:226`, `:242` | same row, `GPU user tok/s` = **614.4** | `derived` | **NO** |
| implied N7 ratio `15.2×` | `docs/OVERVIEW.md:226`; rendered as `B=1  15.2×` in `docs/assets/throughput-at-200k.svg` | same row, `Same-B ratio` = **13.10×** | `derived` | **NO** |
| **`14,436 tok/s`** N4-class central | `docs/OVERVIEW.md:228`, `:243` | `results/iso-node/leading_node_market/REPORT.md:58`, `ROM user tok/s` = **12,629.3** | `derived` | **NO** |
| `1,666 tok/s` B300 same-batch | `docs/OVERVIEW.md:228`, `:243` | same row, `GPU user tok/s` = **1,650.7** | `derived` | **NO** |
| implied N4 ratio **`8.67×`** (14,436/1,666 = 8.665) | `docs/OVERVIEW.md:228`, `:243`; rendered as `B=1  8.7×` in `docs/assets/throughput-at-200k.svg` | same row, `Same-B ratio` = **7.65×** | `derived` | **NO — RETRACTED** |
| band `1,299–35,829 tok/s` | `docs/OVERVIEW.md:242` | `results/iso-node/n7_architecture_attribution/REPORT.md:186` = **1,287.0–23,767.7** | `derived` | **NO** |
| band `1,666–56,884 tok/s` | `docs/OVERVIEW.md:243` | `results/iso-node/leading_node_market/REPORT.md:190` = **1,637.9–42,373.7** | `derived` | **NO** |
| the same bands, plotted | `docs/assets/uncertainty-at-200k.svg`, embedded `docs/OVERVIEW.md:250` | `tools/render_public_assets.py`, last built 2026-08-28 | `executed`, stale | **NO** |

`docs/OVERVIEW.md:218–219` — *"The binding term is the collective floor—not the
ROM read"* — is still true by the artifact's `binding_constraint` label, but the
`max()` term inside the derivation has silently changed identity from **compute**
to **KV beachfront**. The explanation no longer matches its own arithmetic.

## Rank 4 — `docs/PER_REGION_COMPUTE_IN_ROM_DESIGN.md`: every row of the results table, in a document that opens by promising it did not hand-compute

`:3–5` states *"Every figure below is emitted by `src/opentallas/roofline.py` and
read out of `results/roofline/n6_vs_a100/REPORT.md` and `analytical.json`.
Nothing is recomputed in prose — the previous version of this document said the
same thing and did not do it, and section 1 is the retraction that resulted."*
It has done it again.

Ground truth is `make roofline` → `results/roofline/n6_vs_a100/REPORT.md:687–730`,
column `Per-region over broadcast`.

| number | where it is stated | what produces it | grade | current? |
|---|---|---|---|---|
| **10.65×** per-region over broadcast, Flash @200K b64 sram | `docs/PER_REGION_COMPUTE_IN_ROM_DESIGN.md:252` | `n6_vs_a100/REPORT.md:711` = **3.57×** (aggregate 138,631 → **46,493.0**) | `derived` | **NO — RETRACTED** |
| `15.20×` at b256 | `:253` | `:712` = **7.20×** (198,349 → **94,029.5**) | `derived` | **NO** |
| `3.51×` at b8 | `:251` | `:708` = **2.01×** | `derived` | **NO** |
| `3.68×` at b64 rom | `:254` | `:719` = **2.01×** | `derived` | **NO** |
| `6.84×` Pro @1M b64 sram | `:255` | `:727` = **2.34×** | `derived` | **NO** |
| `12.01×` Pro @1M b256 | `:256` | `:728` = **4.72×** | `derived` | **NO** |
| Qwen `11,364 / 12,310 / 44,017` and Flash b1 `10,890` | `:247–250` | `:689,695,703,705` = `12,312.6 / 73,121.2 / 133,002.4 / 13,021.5` | `derived` | **NO** (the `1.00×` ratios are right; the magnitudes are not) |
| floorplan-sweep table: `87,122.5 / 213,473.6 / 1.885 / 1.155` etc. | `:82–85` | `n6_vs_a100/REPORT.md:831–836` — different designs, different rates, different binding terms | `derived` | **NO — every cell** |
| `43 of 48 operating points` lost | `:274` | `n6_vs_a100/REPORT.md:23` finding 12 | `derived` | **YES** |
| §1 floorplan table `481.6 / 521.6 / 186.7 / 146.7 mm²`, `2.23×`, `34.47 µs`, and compute-in-ROM capacity **67.7%** | `docs/PER_REGION_COMPUTE_IN_ROM_DESIGN.md` §1 | `n6_vs_a100/REPORT.md` → “The two ROM floorplans on one die” | `derived` | **YES** |
| region sizing `126.1 / 469.5 mm²`, `18.0%`, `36,600 / 195,796 mm²` | `docs/PER_REGION_COMPUTE_IN_ROM_DESIGN.md` §3 | `n6_vs_a100/REPORT.md` → “Sizing one expert region” | `derived` | **YES** |
| `253.91` A100 gate, capacity-infeasible `0.00×` HC1 gate, `1.0000` KV validation ratio | `:8–14` | `n6_vs_a100/REPORT.md` → validation gates; `results/roofline/qwen3_execution_validation.json` → `lanes[*].kv.byte_ratio = 1.0` | `executed` | **YES** |

## Rank 5 — retracted claims still live in `src/` and in the one config the grade checker enforces

These matter more than a stale document, because the code is what the next
regeneration reads, and `configs/hardware/technology.json` is the *only* file
`tools/check_evidence_grades.py` guards — and it passes while carrying retracted
constants in its prose notes.

| number | where it is stated | what produces it | grade | current? |
|---|---|---|---|---|
| *"**Measured, not assumed**: the released DeepSeek implementation reads no index at 1,001 or **8,001** tokens (251 and 2,001 compressed entries)"* | `src/opentallas/schema.py:53–58` (docstring of `index_scan_min_compressed_entries`) | `configs/models/deepseek-v4-{flash-0731,pro-0813}.json` now set the field to **0**, with a full retraction record at `deepseek-v4-pro-0813.json:373–378`; `tools/check_evidence_grades.py:14–15` names it *"an instrumentation artifact"* | claims `measured`, evidence supports **none** | **NO — RETRACTED, and over-graded** |
| *"charging the scan there **overstates** KV traffic — **by 1.60x at 8,001 tokens** on DeepSeek-V4-Flash"* | `src/opentallas/workload.py:139–144` | `configs/models/deepseek-v4-flash-0731.json:23`: *"With the threshold at 8,001 the profile **under**-predicted the measured rungs by 1.12x at 1,000 tokens and 1.60x at 8,000"* | `prose` | **NO — retracted, and the sign is inverted** |
| *"**72%** of the KV read is a scan of 50,000 index entries of **68 bytes** each"* | `src/opentallas/roofline.py:1072` | recomputed at the current `index_entry_bytes = 256`: 21 × 50,000 × 256 = 268,800,000 B of 317,435,904 B = **84.7%** | `derived` | **NO** |
| *"each index entry sits beside the **583-byte** payload entry … **96 of 68** useful bytes at a 32-byte HBM granule, **128** at a 128-byte SRAM row"* | `src/opentallas/roofline.py:1081–1085` | current config is `entry_bytes 1024`, `index_entry_bytes 256`. **256/32 = 8 exactly; 256/128 = 2 exactly** — zero granule waste | `derived` | **NO** |
| *"the two layouts **differ by more than 1.6x**"* | `src/opentallas/roofline.py:1074–1075` **and** `configs/hardware/technology.json` → `kv.index_layout.note` | `make roofline` → `results/roofline/n5_vs_b200/REPORT.md:1254–1259`, `Inflation` column = **1.00x on all six rows** | `assumed` (grade passes; the note is false) | **NO — the layout choice is now a no-op** |
| *"A **68-byte** index entry therefore costs **96 bytes**"* | `configs/hardware/technology.json` → `kv.access_granularity_bytes.hbm.note` | same — a 256 B entry costs 256 B | `assumed` | **NO** |
| *"a narrower 64-byte macro halves the waste on a **68-byte** entry"* | `configs/hardware/technology.json` → `kv.access_granularity_bytes.sram.note` | same | `assumed` | **NO** |
| `81,218 mm²` / `45,316 mm²` ROM array, and every weight-side figure | `docs/FIRST_PRINCIPLES_MEMORY_DESIGN.md:86–91` | weight-side only; untouched by the KV corrections | `derived` | **YES** |

`tools/check_evidence_grades.py` reports *"every graded entry names a defined
grade and a source it can support"* across 151 entries. It is right, and it is
not enough: it checks grade vocabulary and citation resolvability, never whether
the note's arithmetic still holds.

---

# 2. Corrections that themselves went stale

The most dangerous category, because a retraction notice is the form a reader
trusts most. Each of these correctly retracts a number and then names a
replacement that has since been superseded.

| number | where it is stated | what produces it | grade | current? |
|---|---|---|---|---|
| *"**RETRACTED**: '27× over a global broadcast at batch 64.' The model now says **10.65×**"* | `docs/PER_REGION_COMPUTE_IN_ROM_DESIGN.md:258–259` | `results/roofline/n6_vs_a100/REPORT.md:711` = **3.57×**. `10.65×` is an intermediate value | `derived` | **NO — the correction is two generations behind** |
| *"'per-region beats a global broadcast by up to 27× at batch 64' is retracted. At a matched floorplan the model said **10.65×**, and … it now says **7.44×**"* | `docs/TECHNICAL_DIRECTION_RECOMMENDATION.md:115–117` | same, = **3.57×**. The **same document** states 3.57× correctly at `:865–866`, 750 lines later | `derived` | **NO — and the file now states two different current values for one quantity** |
| *"**RETRACTED**: 54.2× … The model now says **35.4×**, with a band of **24.5–42.5×**"* | `docs/TECHNICAL_DIRECTION_RECOMMENDATION.md:263–264` | `results/roofline/n6_vs_a100/REPORT.md:203` = **8.63×**, band **4.46–11.82×** (`:317`) | `derived` | **NO** — rescued only at `:372`, 108 lines later |
| *"**The headline iso-area ratio at 554,700 mm² spans 24.5–42.5×**"* | `docs/TECHNICAL_DIRECTION_RECOMMENDATION.md:1058–1059` | same: **4.46–11.82×** (n6) / **2.62–6.60×** (n5) | `derived` | **NO — a live, bolded, unmarked headline; §0.12's correction never reached §3** |
| a table column headed literally **`ratio now`** carrying `35.4×` | `docs/TECHNICAL_DIRECTION_RECOMMENDATION.md:316,324` and `docs/ISO_AREA_COMPARISON_AND_THE_TAALAS_ANCHOR.md:135,143` | `n6_vs_a100/REPORT.md:203` = **8.63×** | `derived` | **NO** — both files banner the section (TDR `:372`, ISO `:96–98`), but the column header still says "now" |
| *"OI-38 **Closed** … the marker moved to `cases=50 … views=391`, checks from 3,017 to **3,282**"* | `docs/UNIFIED_EXECUTION_CHECKLIST.md:1298–1300` | `results/rtl/abi3_campaign.json` **(tree)**: `cases=63 headers=63 programs=51 issues=177 views=451 traps=11 checks=4331` | `executed` | **NO — a closed correction that is itself stale** |

There is a coincidence worth knowing before anyone bulk-edits: `docs/ISO_AREA_…:138`
and `docs/TECHNICAL_DIRECTION_…:319` contain a **`8.6×`** that is *not* the
headline — it is the ratio at the 79,870 mm² rung of the superseded table. And
`tools/run_roofline_studies.py:3508` contains a `54.2` that is a **watt**, not
the retracted iso-area ratio.

---

# 3. Stale supporting numbers

Lower consequence individually; they matter because they are the evidence
attached to `[x]` checklist items, which is what a reader checks when they doubt
a headline.

## 3a. `docs/UNIFIED_EXECUTION_CHECKLIST.md` — `[x]` items whose evidence no longer holds

| number | where it is stated | what produces it | grade | current? |
|---|---|---|---|---|
| `[x]` W8.6 *"41 cases, 135 issue events, 354 resolved tensor views, 11 traps, 2,903 checks"* | `:103` | `make abi3-rtl` → `results/rtl/abi3_campaign.json` **(tree)** = **63 / 177 / 451 / 11 / 4,331** | `executed` | **NO** |
| OI-16 *"compares 354 resolved views"* | `:528` | same = **451** | `executed` | **NO** |
| `[x]` W2.4 *"691 kernels, 1127 tensors … graph_id `65eb209f`"* | `:40` | `make abi3-ir` → `build/ir-v3/qwen3-8b/kernel_ir.v3.json` = **728 kernels, 1165 tensors, graph_id `88496d70b772`** (399 bindings and 16,381,470,720 B are correct) | `executed` | **NO** |
| `[x]` W2.5 *"3003 kernels, 71278 tensors"* | `:41` | `build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json` = **3976 kernels, 7066 tensors** (229 states and 156,015,698,140 B correct) | `executed` | **NO — tensors off ~10×** |
| `[x]` W2.6 *"union published … (71 contracts)"* | `:42` | `spec/abi3/numeric_contract_union.json` **(tree)** → `contract_count` = **68** | `executed` | **NO** |
| `[x]` W4.3 *"Qwen 69 instructions from 691 kernels"* | `:64` | admitted Qwen records all carry `instruction_count` **75** | `executed` | **NO** |
| `[x]` W5.2 current static-proof figures: Qwen **75 instructions / 239 descriptors** on both generated sides | checklist W5.2 | `make abi3-equivalence` → `results/abi3/storage_class_equivalence_qwen3.json`, schema v2; the retained ROM execution record independently carries the same 75/239 counts, but the proof's comparison-HBM member is not the shipped 75/218 HBM product deployment <!-- figure: 75 src="results/abi3/storage_class_equivalence_qwen3.json#instruction_count.rom" name="Qwen v2 instructions, ledger reconciliation" --> <!-- figure: 239 src="results/abi3/storage_class_equivalence_qwen3.json#descriptor_count.rom" name="Qwen v2 descriptors, ledger reconciliation" --> | `executed`, static build proof | **YES — old 29/31/210 drift resolved; semantics kept distinct** |
| `[x]` W6.2 current static-proof figures: **18** Qwen descriptors differ, all `MEMORY_OBJECT` and ROM→HBM; **16** placed→unplaced plus **2** already-unplaced, zero residual violations | checklist W6.2 | same v2 file → `differing_descriptor_count`, `placement_transitions`, `differences_beyond_permitted_transition`, `admitted` and `holds`; this does not refresh the retained 24-token execution <!-- figure: 18 src="results/abi3/storage_class_equivalence_qwen3.json#differing_descriptor_count" name="Qwen v2 differing descriptors, ledger reconciliation" --> <!-- figure: 16 src="results/abi3/storage_class_equivalence_qwen3.json#placement_transitions.rom_placement_to_hbm_unplaced" name="Qwen v2 placed transitions, ledger reconciliation" --> <!-- figure: 2 src="results/abi3/storage_class_equivalence_qwen3.json#placement_transitions.already_unplaced_to_hbm_unplaced" name="Qwen v2 already-unplaced transitions, ledger reconciliation" --> | `executed`, static build proof | **YES — old v1 artifact superseded** |
| Current DeepSeek v2 static proof: **1,171 instructions / 3,403 descriptors** on both generated sides; **318** permitted transitions = **312** placed→unplaced + **6** already-unplaced | OI-19 / OI-51 | `make abi3-equivalence` → `results/abi3/storage_class_equivalence_deepseek_v4.json`; both generated builds admit, `holds: true`, and the residual list is empty <!-- figure: 1171 src="results/abi3/storage_class_equivalence_deepseek_v4.json#instruction_count.rom" name="DeepSeek v2 instructions, ledger" --> <!-- figure: 3403 src="results/abi3/storage_class_equivalence_deepseek_v4.json#descriptor_count.rom" name="DeepSeek v2 descriptors, ledger" --> <!-- figure: 318 src="results/abi3/storage_class_equivalence_deepseek_v4.json#permitted_transition_count" name="DeepSeek v2 transitions, ledger" --> <!-- figure: 312 src="results/abi3/storage_class_equivalence_deepseek_v4.json#placement_transitions.rom_placement_to_hbm_unplaced" name="DeepSeek v2 placed transitions, ledger" --> <!-- figure: 6 src="results/abi3/storage_class_equivalence_deepseek_v4.json#placement_transitions.already_unplaced_to_hbm_unplaced" name="DeepSeek v2 already-unplaced transitions, ledger" --> | `executed`, static build proof | **YES — current v2; not a product-HBM execution** |
| `94 counters` / `115-counter registry` / `115 counters` | `:29`, `:57`, `:417` | `PYTHONPATH=. python3 -c "from runtime.sim.counters import COUNTERS; print(len(COUNTERS))"` = **121** | `executed` | **NO — three mutually inconsistent figures, none matching the registry** |
| `[x]` W10.5 *"largest context **actually executed is 8,000 tokens**; 32K/128K/200K exhaust GPU memory"* | `:120`, restated in OI-39 at `:199–200` | `results/abi3/deepseek_v4_reference_oracle_context_ladder.json` → `largest_natural_context_executed` = **200000**; `context_ladder_summary.executed = [1000, 8000, 32000, 128000, 200000]` | `executed` | **NO — all five rungs ran** |
| `[ ]` W13.5 *"the recorded runs are 23 and 24 tokens, which is not a reasoning task"* | `:137–138` | `results/abi3/qwen3_hbm_ta-qw-reason-1_execution.json` = **512 tokens, status pass, `reference_agreement: true`** | `executed` | **NO — an open box whose blocking rationale is refuted by a committed artifact** |
| `[ ]` W13.6 *"A tool call that is never executed is not an agentic task"* | `:139–141` | `results/abi3/qwen3_hbm_ta-qw-agent-1_episode.json` → `executed_command_count: 1`, `answer: "239"` = `expected_total` | `executed` | **NO — the loop is closed** |
| `[ ]` W6.3 *"12,100 instructions, 25,129 descriptors, work 50,339,327"* | `:82` | `results/abi3/deepseek_v4_hbm_ta-ds-chat-1_execution.json` = **11,049 / 23,297 / 6,177,966** | `executed` | **NO** |
| `[ ]` W6.4 *"retires 5,883 instructions (2,974 issued) … the residual-add wall **is gone**"* | `:83` | `results/abi3/deepseek_v4_rom_ta-ds-chat-1_execution.json` = **5,789 / 2,952**, failure = *"the residual add contract is BF16 in and BF16 out"* — **the wall it says is gone** | `executed` | **NO** |
| OI-26 / OI-28 *"reduction output view 413"* | `:842–844`, `:930` | artifact says **view 2327** | `executed` | **NO — stale view id** |
| W12 correction table, all six rows | `:266–273` | 54.2→35.4→**8.6×**; 113.2→**35.3**; 58.9→**18.0**; 116,278→**5,000–9,000**; 27.3→**4.62×**; 27→**3.57×** | `derived` | **YES — the only place in the repository where all five corrections land correctly** |
| `[~]` W11.1, the 24-vs-192 token horizon | `docs/UNIFIED_EXECUTION_CHECKLIST.md` W11.1 | `results/abi3/comparison_qwen_rom_vs_hbm.json` → `token_agreement {identical: true, common_prefix_length: 24}`; `results/abi3/qwen3_hbm_ta-qw-8k-1_execution_192.json` → `status: "diverged"`, `notes.first_divergence_index: 137`, `reference_agreement: false` | `executed` | **YES — the model entry in the file** |

## 3b. Token-identity claims that are true but unscoped

The retraction is *"the two lanes produce identical tokens" — true at 24 tokens,
false at 192*. `docs/UNIFIED_EXECUTION_CHECKLIST.md` W11.1 states the rule:
*"A token-identity claim between two backends has a horizon and the horizon must
be stated."* Three summary-level claims state the identity without the horizon.

| number | where it is stated | what produces it | grade | current? |
|---|---|---|---|---|
| *"**The Qwen3-8B accelerator produces output token-identical to an independent reference** over the pinned chat workload"* | `README.md:9` (research-status banner) | true for `TA-QW-CHAT-1` (24 tokens). At 192 tokens on `TA-QW-8K-1` the HBM lane diverges from the oracle at index **137** (`results/abi3/qwen3_hbm_ta-qw-8k-1_execution_192.json`) | `executed` | **narrowly YES; the scope qualifier is load-bearing and the horizon is not stated** |
| `[x]` W13.2 *"24 tokens, oracle-identical, and identical to the HBM lane position for position"*, under a heading *"stated plainly"* | `docs/UNIFIED_EXECUTION_CHECKLIST.md` W13.2 | same | `executed` | **YES at 24; should carry W11.1's "false at 192"** |
| `[x]` W6.2 *"The 24 tokens are identical … which is the claim this item makes"* | `docs/UNIFIED_EXECUTION_CHECKLIST.md` W6.2 | same | `executed` | **YES — correctly scoped, but carries no pointer to the horizon** |
| historical checklist wording: *"the horizon must be stated: 137 tokens here, **286 on the agentic workload**"* | `docs/UNIFIED_EXECUTION_CHECKLIST.md` W11.1 before the 2026-09-02 reconciliation | `results/abi3/qwen3_hbm_ta-qw-agent-2_episode.json` → `oracle_comparison.first_generated_divergence_index: 286` — an **accelerator-vs-oracle** divergence on an **HBM-only** episode. There is no ROM agentic record, so it is not a two-backend horizon | `executed` | **CORRECTED — W11.1 now distinguishes the 137-token ROM/HBM horizon from the HBM-only 286-token oracle divergence** |
| *"the weight side comes in at **1.007–1.008×** of prediction on those lanes"* | `docs/TECHNICAL_DIRECTION_RECOMMENDATION.md:56–58` | `results/roofline/qwen3_execution_validation.json` (24 tokens) = 1.00829 / 1.00709 ✓. The newer `results/roofline/qwen3_8k_execution_validation.json` (192 tokens) reports **1.0235 (ROM)** and **1.1059 (HBM, `status: diverged`)**, and is cited nowhere in the document | `executed` | **YES at 24; the 192-token artifact is uncited** |

## 3c. `docs/ISO_AREA_COMPARISON_AND_THE_TAALAS_ANCHOR.md` §2e — a table labelled "after" that predates §2d of the same file

| number | where it is stated | what produces it | grade | current? |
|---|---|---|---|---|
| `27.1× / 26.0× / 10.1× / 4.0×` under a column headed **`ratio after`** | `:381–386` | `results/roofline/n6_vs_a100/REPORT.md:260,264,266,268` = **12.61× / 21.60× / 26.69× / 36.52×** | `derived` | **NO** |
| *"Pro's aggregate ratio at batch 256 falls from 5.2x to **3.0x**"* | `:388–389` | `n6_vs_a100/REPORT.md:284` = **17.33×** | `derived` | **NO** |
| *"the aggregate comparison at serving batch is **halved**"* | `:378–379` | the corrected model says the ratio **rises** with batch for both sparse models — which `:322–330` of the same file states | `prose` | **NO — the direction is inverted, and the file contradicts itself** |
| *"GPU rising 449 → 526 → **642** tok/s"* | `:149–156` | `n6_vs_a100/REPORT.md:203` corrected GPU at 554,700 = **236.7** | `derived` | **NO** |
| §2d ladder, all 20 cells | `:263–282` | `n6_vs_a100/REPORT.md:299–331` | `derived` | **YES — cell for cell** |
| §2f watts (`54.21 W`, `27.04 W`, `85.3 W`), stated only as evidence the power model is broken, with *"every watt … is unpublishable"* at `:429` | `:411–447` | `results/roofline/n5_vs_b200/REPORT.md:1438–1447` | `assumed`, disclosed | **YES — correct handling** |
| `5,000–9,000 tok/s` on-wafer replacement | `:191–196` | `results/roofline/n5_vs_b200/REPORT.md:460,503,552` aggregate column | `derived` | **YES** |

## 3d. `docs/TECHNICAL_DIRECTION_RECOMMENDATION.md` — one live figure outside its own coverage note

| number | where it is stated | what produces it | grade | current? |
|---|---|---|---|---|
| *"ratio from **27.1×** to 27.1×"* | `:405` — above the *"(Both tables below predate section 0.12…)"* disclaimer at `:411–412`, which scopes itself to *the tables below* | `n6_vs_a100/REPORT.md:197` corrected Flash @200K per-user ratio at 554,700 = **9.50×** | `derived` | **NO** — the claim's *point* (the KV correction is invariant at batch 1) survives; the number does not |
| `84.7% for Flash and 87.0% for Pro, up from 72%` (index share of KV read) | `:188` | I recomputed it: 21 × 50,000 × 256 = 268,800,000 B of 317,435,904 B = **84.7%** ✓ | `derived` — but **prose-only**, see §5 | **YES, and nothing emits it** |
| `4.62×` N5-vs-B200 for Pro, `13.1× against 27.3×`, `8.63×`, `35.3:1`, `18.0:1`, the whole latency-separation ladder at `:628–649` | `:330–332`, `:399–401`, `:628–649` | `n5_vs_b200/REPORT.md:203,315`; `n6_vs_a100/REPORT.md:184–203`; `n5_vs_b200/REPORT.md:162–163` | `derived` | **YES** |

---

# 4. Generated artifacts: which generator actually reran

`results/**/REPORT.md` is generated and therefore current *by construction only
if the generator ran after the correction*. Two did not.

| artifact | produced by | last regenerated | current? |
|---|---|---|---|
| `results/roofline/n5_vs_b200/REPORT.md` | `make roofline` | `fc9b7b1` 2026-08-30 10:13 — the fifth correction itself | **YES.** No commit touches `src/opentallas/roofline.py` after `fc9b7b1` |
| `results/roofline/n6_vs_a100/REPORT.md` | `make roofline` | `fc9b7b1` 2026-08-30 10:13 | **YES** |
| `results/iso-node/leading_node_market/REPORT.md` | `make iso-node` | `a782530` 2026-08-30 13:16 — HEAD, *"regenerate against tonight's corrected model"* | **YES** |
| `results/iso-node/n7_architecture_attribution/REPORT.md` | `make iso-node` | `a782530` | **YES** |
| `results/model-traffic/REPORT.md` + `sweep.csv` | `make model-traffic` | `de5c34c` 2026-08-30 09:23 | **YES** |
| `results/abi3/*` (30 artifacts) | the ABI 3.0 targets | up to `2dff29d` 2026-08-30 11:30 | **YES** |
| **`docs/PROGRAM_STATUS.md`** | `make abi3-status` → `tools/build_program_status.py` | `ca0c36d` **2026-08-29 17:50** | **NO — 108 commits and 19.5 hours stale** |
| **`docs/assets/why-rom.svg`, `throughput-at-200k.svg`, `uncertainty-at-200k.svg`** | `python3 tools/render_public_assets.py` | `a1eb32e` **2026-08-28 11:01** | **NO — see Rank 3** |
| `results/standard/`, `results/sensitivity/` | `make legacy-sim`, `make sensitivity` | 2026-08-28 | **stale but honestly bannered** *"Legacy/superseded"* in both REPORTs, in `README.md:160` and `SOURCES.md:238` |
| `results/spice/*`, `results/asap7_physical/`, `results/gpu/*`, `results/noc/` | `make spice-pdk`, `make noc`, … | 2026-08-27/28 | **YES — circuit- and fabric-level, untouched by tonight's model corrections** |

### `docs/PROGRAM_STATUS.md` in detail

It is the only generated file in `docs/`, and it is the file `README.md:17`
points to for *"generated status"*. It states `**Commit:** 3abe9cd3f15e`.

| number | where it is stated | what produces it | grade | current? |
|---|---|---|---|---|
| *"58 done, 7 in progress, 13 not started"* | `docs/PROGRAM_STATUS.md:8` | `tools/build_program_status.py:195–197` counts `- [x] ` / `- [~] ` / `- [ ] ` in `docs/UNIFIED_EXECUTION_CHECKLIST.md`. Run today: **71 / 11 / 10** | `executed` | **NO** |
| deepseek-v4-flash IR row `3003 \| 71278 \| 229 \| 572431f15e65` | `:21` | `build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json` = **3976 / 7066 / 229 / `e9b960ffcb19`** | `executed` | **NO** |
| qwen3-8b IR row `728 \| 1165 \| 36 \| 88496d70b772` | `:20` | `build/ir-v3/qwen3-8b/kernel_ir.v3.json` | `executed` | **YES** |
| *"30 cases, 24 programs executed, 99 engine-issue events and 12 traps"* | `:58` | `results/rtl/abi3_campaign.json` **(tree)** = **63 cases, 51 programs, 177 issues, 11 traps** | `executed` | **NO** |
| oracle table, `TA-DS-CTX-8K-1 \| 8 \| max_new_tokens` as the deepest DeepSeek rung | `:29–30` | `results/abi3/deepseek_v4_reference_oracle_context_ladder.json` now runs to **200,000** | `executed` | **NO — the table has no 32K/128K/200K rows** |
| `failclosed_campaign \| None \| None \| None` | `:69` | `results/abi3/failclosed_campaign.json` exists | `executed` | **NO — reported absent while present** |

`make abi3-status` regenerates it in one command. Nothing runs it.

**Update 2026-08-31.** It has now been run, and the regeneration confirms every
row above and adds one the audit did not reach. The RTL line moved from *"63
cases, 51 programs"* to **64 cases, 52 programs, 182 issue events**; the
checklist counters moved to the live values; and the DeepSeek IR row moved
again, to **3,956 / 7,047 / 229 / `fa785d3fd7e3`**, because the exporter changed
after this audit was written. That third one is worth naming: `build/` is
`.gitignore`d, so `results/abi3/program_status.json` is the **only committed
record** of the neutral IR, and both `README.md` and checklist W2.5 were still
quoting the previous `3,976 / 7,066 / e9b960ffcb19`. The stale value had
migrated out of the generated file and into two hand-written ones, where nothing
regenerates it. A later phase-extent correction preserved the 3,956 / 7,047 /
229 census but moved the graph identity again, to `9ef6c3248d23`; the README's
figure annotation now binds that summary to the generated status artifact.

**Update 2026-09-02.** After W6.6 closed, `make abi3-status` ran from clean
commit `0a5bc1f284af`. The retained Markdown and JSON now report **83 complete,
10 in progress, 1 not started, 0 blocked**, branch `main`, and
`worktree_dirty: false`. The generated files are committed in the follow-on
status publication commit; their embedded identity deliberately remains the
clean closure commit whose artifacts and checklist they summarize. The older
table above is retained as the original stale-status finding, not as current
status.

The Physical table gained **ten rows it had simply been missing** — 14 rows
before, 24 after: `asap7/ot_ta_matmul_bf16_sram_engine`, and on `sky130hd` the
ABI 3.0 datapath and numeric-probe blocks (`ot_a3_dma_index_mover`,
`ot_a3_mac_lane`, `ot_a3_selection_argmax`, `ot_a3_vector_add` and the four
`ot_a3_probe_*` runs), all of which post-date the last regeneration. Two of the
ten do **not** meet timing (`ot_a3_mac_lane/prelayout` at -27.099 ns and
`ot_a3_probe_fp32_add` at -29.573 ns), so a generated status file was reporting
a clean physical lane while ten runs, two of them failing, were invisible to it.
A generated file does not only go stale by stating a wrong number; it goes stale
by **omitting a row**, and an omitted row reads as "not applicable" when it
means "not counted".

---

# 5. Numbers nothing produces

**This is the most durable part of the audit.** A stale number can be corrected;
a number with no producer will go stale again the next time the model moves, and
nothing will notice. The correlation is exact and worth stating plainly:

> Of the priority documents, `PER_REGION` and `TECHNICAL_DIRECTION` cite
> artifacts — and their errors were *caught and retracted*. `FIRST_PRINCIPLES`,
> `WAFER_VERSUS_ARRAY` and `COMPUTE_IN_ROM_MECHANISM` cite **nothing** — and
> their errors are still live and unmarked. Provenance is what made the
> difference, not care.

Measured over the priority documents (`grep -c` for `results/`, `tools/|make |python3 `, `src/opentallas`):

| document | numeric tokens | `results/` refs | command refs | `src/` refs |
|---|---:|---:|---:|---:|
| `docs/TECHNICAL_DIRECTION_RECOMMENDATION.md` | 421 | 4 | 2 | 2 |
| `docs/ISO_AREA_COMPARISON_AND_THE_TAALAS_ANCHOR.md` | 262 | 2 | 2 | 1 |
| `docs/PER_REGION_COMPUTE_IN_ROM_DESIGN.md` | 73 | 2 | 0 | 1 |
| `docs/OVERVIEW.md` | 17 | 7 | 9 | 0 |
| `docs/ASSUMPTIONS.md` | 63 | 1 | 0 | 1 |
| **`docs/FIRST_PRINCIPLES_MEMORY_DESIGN.md`** | **56** | **0** | **0** | **0** |
| **`docs/WAFER_VERSUS_ARRAY_LATENCY.md`** | **58** | **0** | **0** | **0** |
| **`docs/COMPUTE_IN_ROM_MECHANISM.md`** | **16** | **0** | **0** | **0** |
| **`docs/METHODOLOGY.md`** | **9** | **0** | **0** | **0** |

## 5a. Whole documents nothing produces

| number(s) | where | what produces it | grade |
|---|---|---|---|
| all 58 figures in `docs/WAFER_VERSUS_ARRAY_LATENCY.md` — the hop-latency budget table, the pipeline-cost table, the tensor-parallel table, the per-model crossover rates (`7,400` / `1,280 tok/s`) | whole file | **nothing.** No script, no artifact, no test. The roofline study now models all of it and disagrees | `prose` |
| all 56 figures in `docs/FIRST_PRINCIPLES_MEMORY_DESIGN.md` | whole file | **nothing.** `:5–6` claims *"Every figure comes from `configs/models/*.json` through `opentallas.workload`"* — but `src/opentallas/workload.py` has **no `main`, no CLI and no argparse**, and no artifact writes this table. The claim names a module, not a command | `prose` |
| all 16 figures in `docs/COMPUTE_IN_ROM_MECHANISM.md` — including `66.8×` per-user, `~2.2×` aggregate, `~7,771 tok/s (40% MFU)`, and the closing *"the per-user and aggregate ratios differ by **30×**"* | whole file | **nothing.** The roofline study now quantifies the same fork at *"up to **28.5x** of aggregate throughput"* (`results/roofline/n5_vs_b200/REPORT.md:22`), from a different derivation. The `40% MFU` assumption appears in no config | `prose` |
| `docs/METHODOLOGY.md` in full | whole file | nothing; it is a normative contract, and `:13` still says *"The repository maintains **two** independent studies"* when there are now four — the roofline pair, where tonight's headline lives, is not governed by it | `prose` |
| SHA-256 known-answer digests and element counts across the **16** `docs/DEEPSEEK_V4_*_EVIDENCE.md` files | whole family | 14 of 16 cite no `results/` path, and **none names a reproduction command**. Hash-anchored, so they cannot silently drift numerically — but nothing regenerates or verifies them either | `prose` |

## 5b. Individual figures nothing emits

| number | where it is stated | what produces it | grade |
|---|---|---|---|
| `16,960 tok/s` Taalas HC1 per user — **the validation gate for the entire model** | `docs/COMPUTE_IN_ROM_MECHANISM.md:117`, `docs/TECHNICAL_DIRECTION_RECOMMENDATION.md:16`, the roofline gate table, and `configs/hardware/technology.json` | the *gate* is produced (`n6_vs_a100/REPORT.md:78`). The *anchor* is cited to three secondary press reports in `docs/ISO_AREA_…:15–34`, and **`docs/SOURCES.md` contains zero occurrences of "Taalas" or "HC1"** — while `SOURCES.md:26–27` forbids secondary press for a value | claims `published`, **not in the source register** |
| `46,225 mm²` WSE-2 wafer area — the numerator of the N7 compute roof | `docs/SOURCES.md:169` (`SRC-CEREBRAS-WSE2`), used at `docs/ASSUMPTIONS.md:185` | cited as *"Cerebras WSE-2 public product disclosures"* — **no URL, no document, no date, no hash**. Its sibling `SRC-CEREBRAS-WSE3` carries a URL, a byte size and a SHA-256 | claims `published`, **unresolvable** |
| `823 mm²` GC200 die and `47.5 TB/s` — the denominator of the same roof | `docs/SOURCES.md:170` (`SRC-GC200`), second sentence | *"Public GC200 architecture disclosures"* — **no URL**. The first sentence of the same cell *is* backed by the linked product page | claims `published`, **unresolvable** |
| `60 GB/s/mm²` ROM read-bandwidth density (YOLoC) and `20.7 MB/mm²` (3D-METRO) — the two most load-bearing ROM constants | `docs/SOURCES.md:200–201`, used at `docs/ASSUMPTIONS.md:159–164` | DOIs present, but `SOURCES.md:36–40` discloses that both resolvers returned **HTTP 403** and *"this run does not claim fresh access to or content validation of the ACM papers"* | correctly graded non-fabricated; **unverified** |
| `84.7%` / `87.0%` index share of the KV read | `docs/TECHNICAL_DIRECTION_RECOMMENDATION.md:188` | I recomputed it by hand and it is **right**. It appears in no artifact | `prose` |
| `290.4 ns` per compressed-sparse layer, and the fixed-latency share table `55.4 / 38.7 / 34.7 / 6.6 / 2.0 / 0.9%` | `docs/TECHNICAL_DIRECTION_RECOMMENDATION.md:141–157` | nothing | `prose` |
| `11,747 feasible points`, and the uniform-multiplier table `0.181 / 0.851 / 1.340 / 1.684 W/mm²`, `339 / 581 / 987` | `docs/TECHNICAL_DIRECTION_RECOMMENDATION.md:496,508,515–518` | nothing; `11,747` is a cross-study sum with no stated derivation | `prose` |
| corrections `1.02× to 3.14×` over `125 GPU points`; `3.69 devices engaged, 2.53 effective, 1.46×` | `docs/TECHNICAL_DIRECTION_RECOMMENDATION.md:127–130` | nothing | `prose` |
| the entire per-user results table `216 / 229 / 4,022 / 1,143 / 1,857 / 1,056 / 17 / 41 / 779 / 264 …` | `docs/TECHNICAL_DIRECTION_RECOMMENDATION.md:749–763` | sourced to *"`The batch-amortisation fork` and the points behind it"* — that table (`n6_vs_a100/REPORT.md:687–736`) carries **aggregate only**. None of these values is in it | `prose` |
| *"a 4,000-trial Monte Carlo … agreement within 3% at every batch"* | `docs/TECHNICAL_DIRECTION_RECOMMENDATION.md:100` | the test **does** exist — `tests/test_roofline.py:1631 test_expected_max_region_load_matches_a_monte_carlo_of_the_routing`, `trials=4000`, `rel=0.03` — but the document names no test, no file and no artifact | `executed`, **uncited** |
| *"the measured speed-of-light all-reduce floor on GB200"*, `1.4 µs` | `docs/TECHNICAL_DIRECTION_RECOMMENDATION.md:300`, `:1051` | nothing. Conspicuous next to `:301–302` (Rocki SC20) and `:1054–1056` (De Sensi SC24), which *are* cited | claims `measured`, **no source** |
| `100.4 mm² of an 815 mm² die at N6` | `docs/UNIFIED_EXECUTION_CHECKLIST.md:376` | nothing — `grep -rn "100.4 mm" results/` is empty. The byte figure beside it (`1,207,959,552 B`) *is* produced | `prose` |
| *"all **27 distinct prefill kernels** diffed kernel-by-kernel through the `on_issue` hook: bit-identical"* | `docs/UNIFIED_EXECUTION_CHECKLIST.md:81` | nothing — no artifact path, no tool named, not reproducible from the repository | claims `executed`, **no artifact** |
| the wafer is `8.3×` cheaper on Flash and `8.9×` on Pro | `docs/ISO_AREA_COMPARISON_AND_THE_TAALAS_ANCHOR.md:200` | the artifact states only *"**at least** 2.0x cheaper"*; the per-model values appear in neither study report | `prose` |
| `26 dies against 18`, `138 against 93` | `docs/PER_REGION_COMPUTE_IN_ROM_DESIGN.md:218–219` | no die-count table in either report carries these | `prose` |
| `299 mm²` MAC-array area recovered; `0.41×` feed fraction; *"the mean understates the sweep by **1.6x to 2.7x**"* | `src/opentallas/roofline.py:1341`, `:1364`, `:373` | nothing computes or prints them. The last sits directly under the per-region argument whose headline moved 27× → 3.57× | `prose` |
| `46,225 mm²` wafer; `681 reticle fields`; `1.4x`; the watts `54.2 W / 27.0 W / 85.3 W` | `tools/run_roofline_studies.py:3539`, `:3680`, `:3654`, `:3508–3511` | **hard-coded strings inside otherwise fully f-string findings.** The watts sit under `## Interpretation boundary` and are a disclosure, not a claim — but if the power model moves, the disclosure will quote stale evidence for a true conclusion | `prose` |
| *"A 681-region all-reduce is **5.72 microseconds**, not **0.20**"* | `tools/check_evidence_grades.py:12–13` | nothing recomputes it. Consistent in direction with the retraction | `prose` |
| `17,000 tok/s` vs `16,960 tok/s` | `tools/run_roofline_studies.py:2724` and `:2402` vs `:3298`; `src/opentallas/roofline.py:3168,3173` | the config value is **16,960** (`configs/hardware/technology.json`). One file quotes both | `published`, inconsistently rounded |
| `results/roofline/*` and `results/abi3/*` | — | **no `GEN-*` row in `docs/SOURCES.md`.** Its 23 `GEN-*` rows index `results/standard`, `routing`, `noc`, `model-traffic`, `model-execution`, `sensitivity`, `spice`, `rtl` and `configs/hardware` — but not the two newest and most-cited result families, which is where every number in §1 of this ledger is produced | — |

---

# 6. What enforces what

| mechanism | scope | gap |
|---|---|---|
| `tools/check_evidence_grades.py` | **`configs/hardware/technology.json` only** — 151 graded entries. Invoked only by `tests/test_evidence_grades.py::test_the_checked_in_technology_passes`; it has **no `make` target** | Does not read `configs/models/*.json` (3 graded entries, unchecked) unless `--also` is passed, which nothing does. Checks grade vocabulary and citation resolvability, **never whether a note's arithmetic still holds** — which is why Rank 5's retracted `583`/`68` constants sit inside the one file it guards, and it passes |
| `tests/test_roofline.py` | pins the corrected model: the mesh-diameter collective (`:824`), the retracted on-wafer rates (`:844`), the layer cap (`:715`), the pipeline rule (`:1002`) | pins the **model**, never the **prose**. No test reads a `docs/*.md` number |
| `tools/build_program_status.py` | the only generator writing into `docs/` | must be run by hand; nothing runs it; 108 commits stale |
| `tools/render_public_assets.py` | the only generator writing `docs/assets/` | same; 2 days stale, and 3 of its SVGs carry retracted figures into the two most-read documents |
| `docs/SOURCES.md` | 23 `GEN-*` rows + external citations | no row for `results/roofline/` or `results/abi3/`; zero mentions of the Taalas anchor |
| **nothing** | **`docs/*.md` prose** | 47 files, ~1,100 unit-bearing numbers, no linter, no test, no generator |

**The one durable fix.** Every stale number in §1 and §2 would have been caught
by a checker that reads a fenced provenance annotation next to each load-bearing
figure — `<!-- from: results/roofline/n6_vs_a100/REPORT.md#L711 col="Per-region over broadcast" -->` —
re-reads the artifact and diffs. That is roughly what
`tools/check_evidence_grades.py` does for `technology.json`, applied to prose.
Until something like it exists, the documents in §5a will go stale again on the
next correction, silently, exactly as they did on this one.

---

## Counts

Reconcilable with the tables above; every figure here is a row count.

| | |
|---|---:|
| Load-bearing figures carrying an explicit **current?** verdict (§1–§4) | **108** |
|  of which **stale** | **80** |
|  of which **verified current** | **26** |
|  of which qualified (narrowly true / misattributed) | 2 |
| Entries in §5 naming a figure **nothing produces** | **25** |
|  whole-document groups (§5a), covering 4 documents ≈ 139 numeric tokens + the 16-file `DEEPSEEK_V4_*_EVIDENCE` family | 5 |
|  individual figures (§5b) | 20 |

Breaking the 80 stale down by kind:

| kind | count | where |
|---|---:|---|
| retracted figures, or their direct descendants, stated as **live** claims | **47** | §1 |
| **corrections whose own replacement has been superseded** | **6** | §2 |
| supporting figures contradicted by a regenerated artifact | 20 | §3 |
| generated artifacts whose generator did not rerun | 7 | §4 |

The swept universe was larger than the ledger: roughly **1,100 unit-bearing
numeric tokens** across the 13 priority documents (measured by `grep -oE` for a
number followed by `× x :1 tok/s mm² µs GB TB/s W %`), plus
`src/opentallas/*.py`, the audited `tools/*.py`, `configs/`, the 21 generated
`REPORT.md` files and `docs/assets/`. Figures that merely repeat a value already
in the table, and worked-example arithmetic that carries no claim, were not given
their own row.

Every "current?" verdict was checked against the artifact that produces it, or
recomputed from `configs/` through `opentallas.workload`. None was assumed.

---

# 7. Additions of 2026-08-31

Two claims landed after this audit closed. Both are recorded here on the
audit's own terms — what produces it, what grade it can support, and what it may
not be used for — rather than left to prose.

## 7a. The ABI 3.0 RTL against the shipped deployment images

| number / claim | where it is stated | what produces it | grade | current? |
|---|---|---|---|---|
| the ABI 3.0 sequencer RTL reproduces `runtime.sim.device.Device` exactly on the **Qwen3-8B ROM and HBM single-chip deployments, the DeepSeek-V4-Flash ROM wafer deployment, and the DeepSeek-V4-Flash HBM 32-node cluster deployment**, both entrypoints, at whole-transaction depth — 2,105 instructions / 693 issues / 2,143 views per Qwen case; 18,491 / 11,714 instructions on DeepSeek ROM prefill / decode; and 18,607 / 11,229 instructions on DeepSeek HBM prefill / decode | `docs/UNIFIED_EXECUTION_CHECKLIST.md` W8.8, `rtl/RTL_INVENTORY.md` A3-SEQ-001, `docs/ABI3_PROGRAM_REPORT.md` §2.7 | `make abi3-rtl-deployment` → `results/rtl/abi3_deployment_campaign.json` → `what_ran.depth_reached[]`, `correlated_cases` | `executed` | **YES** |
| the authoritative list of **which** shipped deployments that campaign covers | prose summaries defer to this field | `results/rtl/abi3_deployment_campaign.json` → `correlated_cases` | `executed` | **by construction** |

The second row is the point. The first run of this campaign refused the
DeepSeek-V4-Flash ROM wafer deployment after eight retirements, on
`A3_STATE_SLOTS`; a repair to that bound changes the verdict, and every document
that had transcribed the verdict would have gone stale in the same silent way
this ledger was written to catch. So the documents state the **rule** — a claim
resting on this RTL may name exactly the deployments `correlated_cases` records
and no others — and point at the field for the list. A rule survives a rerun; a
transcript of a verdict does not.

**What the campaign does not establish, and no document above may imply.**
Engine arithmetic: every dispatchable operation is a recording no-op on both
sides, so the instruction stream is verified and the computation is not, and the
datapaths `results/rtl/abi3_engine_campaign.json` correlates are not wired to
this sequencer. No checkpoint byte is read. One request shape per entrypoint, a
sixteen-token prefill and a one-token decode at position sixteen. Descriptor
record CRC32C and the header's SHA-256 are unchecked in RTL. And **no area,
timing or power quantity whatever** — no block of the ABI 3.0 control plane has
been synthesised or routed at all.

**The finding underneath it, which outlives any rerun.** `A3_STATE_SLOTS` was a
hardware bound that **nothing expressed at admission**: no capability field
named a state-slot count and `runtime.abi3.verifier` had no such check, so a
shipped deployment passed every admission gate this program has and was then
refused in hardware. That is the failure signature the fail-closed design exists
to prevent, and it was invisible until the RTL was asked to run a real program
rather than a generated one.

## 7b. Governed source-current token captures

| number / claim | where it is stated | what produces it | grade | current? |
|---|---|---|---|---|
| Qwen3-8B ROM (`925351…`) and HBM (`8e1185…`) both emit `[1654, 525, 2661, 1447]`, identical to the independent oracle and to each other over the governed four-token horizon | `results/abi3/accelerator_tokens/README.md`, checklist freshness boundary, `docs/ABI3_PROGRAM_REPORT.md` §2.1 | `tools/run_accelerator_tokens.py`, the two governed `qwen3_8b_{rom,hbm}_chat1.json` captures, and their byte-matched oracle input | **`executed`**, functional-simulator and external-comparator evidence only | **YES** |
| DeepSeek-V4-Flash-0731 HBM (`294319…`, post-A28) and ROM both emit `[13806, 345, 7472, 55560]`, identical to the independent oracle and to each other over the governed four-token horizon | `results/abi3/accelerator_tokens/README.md`, checklist W6.3/W6.4 and W13.3/W13.4, `docs/ABI3_PROGRAM_REPORT.md` §3 | `tools/run_accelerator_tokens.py`, the two governed `deepseek_v4_flash_{hbm,rom}_p32.json` captures, `deepseek_v4_reference_oracle_prefix.json`, and `comparison_deepseek_rom_vs_hbm.json` | **`executed`**, functional-simulator and external-comparator evidence only | **YES** |

`executed` in this repository's vocabulary means *obtained by running something
in this repository, with the artifact committed*. The governed tool lowers the
pinned graph, admits the deployment, executes prefill and decode, checks token
legitimacy, and compares only against the byte-matched external oracle. The old
`deepseek_v4_flash_rom_p32_raw.json` remains as historical evidence but no
current claim depends on it. The longer Qwen 24/192-token, EOS, reasoning and
agentic records likewise remain historical: they predate the current deployment
identities and hardened source maps, so no source-current claim beyond four
tokens depends on them. Execution does not promote any capture or pairwise
report to cycle, RTL, physical or silicon evidence, and the four-token horizon
does not establish token 5 or a long-context threshold.

**A correction this milestone forces on existing prose.** The 104-token
`TA-DS-CHAT-1` run has been described as the real gate for DeepSeek execution.
It is not a gate for sparse selection, and neither is the 32-token prefix:
`window_size` is 128, `index_topk` is 512, and the 20 `compress_ratio=128`
layers hold zero compressed positions below 128 tokens, so **neither prompt
reaches any of the three thresholds**. The only structural difference between
them is compressed positions in the 21 `compress_ratio=4` layers, 8 against 26.
Sparse attention under pressure is the `TA-DS-CTX-*` ladder's job, and the
ROM-versus-HBM story at 200K and 1M context rests on exactly the regime neither
prompt touches.

**And it is not an RTL claim.** This is the golden-model/simulator path. Whether
the RTL runs the DeepSeek wafer deployment is §7a's question, answered by a
different artifact. A reader must not come away thinking a validated token means
the RTL runs that design.

## 7c. One line of §6 is now out of date, in the good direction

§6 records that **nothing** enforces `docs/*.md` prose. Since the audit,
`tools/check_prose_figures.py` does: it reads a machine-resolvable provenance
annotation beside a figure, re-reads the artifact and fails on disagreement,
over several hundred annotated figures. Its non-regression map now pins every
release document that currently publishes checked annotations, and
`tests/test_prose_figures.py` proves that removing a whole document's coverage
fails the gate. That is the "one durable fix" §6 names, built. It remains silent
about every figure nobody annotated, which is why W11.3 remains partial and §5
is still the most durable part of this ledger.

---

# 8. Additions of 2026-09-01

## 8a. Four-target ABI 3.0 checkpoint/restart exactness

| number / claim | where it is stated | what produces it | grade | current? |
|---|---|---|---|---|
| Qwen3-8B HBM and ROM plus DeepSeek-V4-Flash-0731 ROM and HBM P32 each reproduce a three-token uninterrupted baseline exactly when stopped after token two, checkpointed, and resumed for token three in a fresh process | checklist W6.6 and `results/abi3/restart_exactness_{qwen3_hbm,qwen3_rom,deepseek_rom_p32,deepseek_hbm_p32}.json` | the four target-specific `make abi3-restart-*` recipes → `tools/run_abi3_restart_exactness.py` → `runtime/sim/checkpoint.py` | **`executed`**, source-current within the recorded 288-file governed Python scope; functional-simulator evidence only | **YES for all four lanes** |
| DeepSeek HBM restores all 32 node arenas and ends with the same aggregate counter set and all 32 per-node counter sets, including sticky-overflow state | `results/abi3/restart_exactness_deepseek_hbm_p32.json` and checklist W6.6 | the serialized governed HBM P32 restart recipe above | **`executed`** against current deployment `294319…`; baseline and fresh resume both produce `[13806, 345, 7472]`, the STATE-erased control diverges at index 2 with `[13806, 345, 7249]`, and the reported-only state-only control matches. The artifact carries 8,992 writable objects across all 32 nodes, passes 27/27 guards, and passed an independent source/deployment/five-PID/token/work/counter/control audit plus the four-artifact retained-evidence regression | **YES — final source-current artifact retained** |

The four current equalities are guarded rather than inferred from two short
lists. Baseline, interrupted, resumed, negative-control and state-only-control
processes are distinct. Each records the same deployment digest,
implementation identity, node count, and complete per-file source map: 288
Python files under `compiler/`, `runtime/`, plus the restart driver, aggregate
digest `ee08b43d87bf6edbcd7b241e7c15a2c4c1a9cb180992dd2eeeee337902a18faf`.
All 27 guards pass in each current artifact. The interrupted prefix is non-empty
and matches the baseline; the fresh process skips prefill and performs real
decode work; and token length, retired work, aggregate counters and all per-node
counters match. W6.6 is closed because the same facts are now retained and
independently validated for current DeepSeek HBM rather than inferred from the
other lanes.

The checkpoint evidence is deliberately complete over the simulator's mutable
boundary. Schema v2 enumerates every writable zero-source object for every
node, verifies that exact node/object set before restoring any bytes, and
retains aggregate counters, every per-node counter set, device/session
bookkeeping, and sparse object digests. The current DeepSeek ROM capture covers
438 images representing 1,078,248,644,744 logical mutable bytes in 143,255,560
logical stored payload bytes. These are sparse-encoding quantities, not physical
disk usage. The corresponding 32-node HBM artifact covers 8,992 objects
representing 2,447,390,804,224 logical mutable bytes in 5,136,187,520 logical
stored payload bytes; it records a 24.53-second write and 99.724-second normal
restore. Those are likewise sparse simulator quantities, not disk footprint or
performance claims.

The controls establish sensitivity. In every lane, a normal resume exits
successfully and reproduces the baseline; a second successful resume with every
STATE-class image erased changes the first resumed token. A complementary
STATE-only run erases HBM/HOST/SRAM scratch and still reproduces the baseline in
all four captures. The negative control gates `pass`; the STATE-only result is
reported as an architectural observation rather than made a validity gate.

**What this does not establish.** The Qwen request is 93 prompt tokens and the
DeepSeek request is the governed 32-token prefix; both produce three tokens
split 2+1. No capture reaches a long-context sparse-attention threshold. This
is functional NumPy execution, not cycle, RTL, physical or silicon evidence,
and it makes no latency or throughput claim. Finally, [OI-23] still applies:
the HBM backend executes from and checkpoints its prepared state image. These
captures prove exact restart from that complete simulator image; they do not
silently upgrade the backend's known committed-image layout defect into a
durability proof.

## 8b. Independent immutable-ROM schedule certificates

| number / claim | where it is stated | what produces it | grade | current? |
|---|---|---|---|---|
| The shipped Qwen ROM deployment passes **63** independent semantic schedule checks over **74** instructions and **14** schedule descriptors <!-- figure: 63 src="results/abi3/rom_schedule_checks.json#cases[case=qwen3-rom-single-chip].passed_check_count" name="Qwen ROM independent schedule checks, ledger" --> <!-- figure: 74 src="results/abi3/rom_schedule_checks.json#cases[case=qwen3-rom-single-chip].actual.instructions" name="Qwen ROM independent schedule instructions, ledger" --> <!-- figure: 14 src="results/abi3/rom_schedule_checks.json#cases[case=qwen3-rom-single-chip].actual.schedules" name="Qwen ROM independent schedules, ledger" --> | checklist W5.5 and `results/abi3/rom_schedule_checks.json` | `make abi3-rom-schedule-check` → `tools/check_rom_schedules.py` → `compiler/backends/rom/common/check.py` | **`executed`**, static artifact-semantic proof | **YES** |
| The shipped DeepSeek ROM wafer deployment passes **129** independent checks over **1,323** instructions, **108** schedules, **609** reconstructed direct dependency edges, and **18** communication descriptors <!-- figure: 129 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-wafer].passed_check_count" name="DeepSeek ROM independent schedule checks, ledger" --> <!-- figure: 1323 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-wafer].actual.instructions" name="DeepSeek ROM independent schedule instructions, ledger" --> <!-- figure: 108 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-wafer].actual.schedules" name="DeepSeek ROM independent schedules, ledger" --> <!-- figure: 609 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-wafer].expected.dependency_edges" name="DeepSeek ROM reconstructed dependencies, ledger" --> <!-- figure: 18 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-wafer].actual.communications" name="DeepSeek ROM checked communications, ledger" --> | checklist W5.5, the implementation-plan §6.3 status note, and the same campaign artifact | the parallel DeepSeek campaign case, reading the shipped graph, capability, deployment manifest, descriptor table, program, and embedded ROM plan | **`executed`**, static artifact-semantic proof | **YES** |

This evidence is independent in the source-code sense the plan requires. An
AST gate rejects any checker import of the ROM program generator, image planner,
or either product backend. The checker instead consumes frozen graph/ABI
contracts and emitted bytes. It separately factors the layer signature stream,
maps representative kernels to frozen engine operations, expands nested loop
intervals, traces producer events, reconstructs ROM shards and resource masks,
checks mutable ports and queue capacity, binds the wafer coordinate table back
to its topology digest, validates collective participant arrays and flow-control
bounds, and closes every live-buffer producer/consumer dependency. The campaign runs the Qwen and
DeepSeek cases in separate worker processes and records the input and checker
digests in the result.

The mutation controls distinguish this proof from another call to the generic
ABI verifier. Tests restamp each altered descriptor table into an internally
consistent deployment; the generic verifier admits the wrong-but-wire-valid
queue, bank, tile width, earlier event, and link-credit cases, while the ROM
checker refuses each at its reconstructed semantic invariant. Running the
campaign twice without a source or input change produces byte-identical JSON.

**Boundary.** `counter_bounds` contains maximum-trip descriptor-derived work,
memory-byte, flit, queue-pressure and potential-port-contention bounds. They are
not measured functional or cycle counters. The route proof binds and checks the
complete emitted shard-coordinate table and its slots; it does not claim that a
physical wire meets timing, power, signal-integrity, or congestion targets.
Those remain W8/W9 evidence, and this static certificate must not be cited as
RTL or silicon execution.

## 8c. Shared HBM/SRAM deployment certificates

| number / claim | where it is stated | what produces it | grade | current? |
|---|---|---|---|---|
| The shipped one-node Qwen HBM deployment passes **21/21** certificate checks, spans **18,526,449,668** of 103,079,215,104 HBM bytes per node across its emitted live-buffer address map, and places **399** authenticated checkpoint ranges exactly once <!-- figure: 21 src="results/abi3/hbm_qwen_deployment_certificate.json#cases[case=qwen3-hbm-single-chip].passed_check_count" name="Qwen HBM deployment certificate checks, ledger" --> <!-- figure: 18526449668 src="results/abi3/hbm_qwen_deployment_certificate.json#cases[case=qwen3-hbm-single-chip].actual.hbm_bytes_per_node" name="Qwen HBM resident bytes, ledger" --> <!-- figure: 399 src="results/abi3/hbm_qwen_deployment_certificate.json#cases[case=qwen3-hbm-single-chip].actual.weight_segments" name="Qwen HBM authenticated ranges, ledger" --> | checklist W4.6 and TA-HBM-3.0 §4.4 | `make abi3-hbm-qwen-deployment` → two clean `lower_with_plan` builds, comparison with the shipped program/table/manifest, emitted-address inventory, `compiler/backends/hbm_sram/check.py`, and the frozen verifier | **`executed`**, deterministic static deployment certificate | **YES** |
| The shipped exact-32-node DeepSeek HBM deployment passes **36/36** certificate checks; its 38 communications cover all five ordered route classes, and its replica-aware capacity proof includes **13,445,013,724** weight bytes plus **805,306,368** bytes of shared communication scratch inside **88,080,248,832** of 103,079,215,104 HBM bytes per node <!-- figure: 36 src="results/abi3/hbm_deepseek_deployment_certificate.json#cases[case=deepseek-v4-flash-hbm-cluster].passed_check_count" name="DeepSeek HBM deployment certificate checks, ledger" --> <!-- figure: 38 src="results/abi3/hbm_deepseek_deployment_certificate.json#cases[case=deepseek-v4-flash-hbm-cluster].actual.communications" name="DeepSeek HBM communications, ledger" --> <!-- figure: 13445013724 src="results/abi3/hbm_deepseek_deployment_certificate.json#cases[case=deepseek-v4-flash-hbm-cluster].actual.weight_bytes_per_node" name="DeepSeek HBM weight bytes per node, ledger" --> <!-- figure: 805306368 src="results/abi3/hbm_deepseek_deployment_certificate.json#cases[case=deepseek-v4-flash-hbm-cluster].actual.communication_scratch_bytes" name="DeepSeek HBM communication scratch, ledger" --> <!-- figure: 88080248832 src="results/abi3/hbm_deepseek_deployment_certificate.json#cases[case=deepseek-v4-flash-hbm-cluster].actual.hbm_bytes_per_node" name="DeepSeek HBM required bytes, ledger" --> | checklist W4.7 and TA-HBM-3.0 §4.4 | `make abi3-hbm-deepseek-deployment` → two clean builds compared byte-for-byte with the shipped bundle, the frozen verifier, the independent checker, causal producer/receive/consumer reconstruction, independently reconstructed replica/shard ownership and generated-constant/alignment accounting, serialized scratch proof, plus digest-restamped wrong-stride, unreachable-decoy, source-map and schedule mutations | **`executed`**, deterministic static deployment certificate | **YES** |

The Qwen certificate does not infer deployment quality from token output. It
rebuilds the physical plan and ABI bundle twice, requires both to equal the
shipped bytes, checks graph/capability/plan bindings, proves HBM and SRAM
capacity, and invokes an independent checker that now accounts for block-scale
companion groups. A raw diff of the single-chip and cluster capabilities allows
only topology class, node count, peers, route groups and bisection-link count to
differ; engines, features, memory and numeric contracts remain identical, so
the one-node profile has not silently removed the shared chip's endpoint.

The DeepSeek certificate closes placement independently of token output. Its
hybrid plan keeps output-column sharding where scale tiles permit it and assigns
each routed bank's consecutive expert slices to node-local views. The causal
checker does not accept a route-class label alone: each data-bearing link must
wait for a producer DMA into its endpoint object, and its completion must reach
a DMA that writes an object read by a waiting non-DMA consumer. Route classes
zero through three satisfy that chain; route class four remains the final
cluster barrier, and every state commit waits for it. The shared exchange object
is included in the HBM capacity result rather than appearing only after the
planner's proof. The capacity checker also reconstructs the residency of each
weight tensor from its node-selected views, conservatively charges any tensor
with a replicated use, includes generated constants and 4 KiB alignment, and
compares that independent packing with the planner's result. This is
deterministic static deployment evidence, not cycle, RTL, physical or
long-context numeric evidence.

---

# 9. Additions of 2026-09-02

## 9a. Governed DeepSeek HBM real-deployment cycle reconciliation

| number / claim | where it is stated | what produces it | grade | current? |
|---|---|---|---|---|
| One 32-token prefill over shipped DeepSeek HBM deployment `294319…` exits `SUCCESS` / `NONE`; an independent functional rerun agrees on all **66** compared architectural counters with no differences <!-- figure: 66 src="results/abi3/deepseek_v4_flash_hbm_p32_prefill_cycle.json#functional_agreement.counters_compared" name="DeepSeek HBM cycle counters reconciled, ledger" --> | checklist W7.5 and `docs/ABI3_PROGRAM_REPORT.md` | `PYTHONPATH=. python3 tools/run_abi3_cycle.py --deployment build/abi3/deepseek-v4-flash-hbm-tokens --capability configs/hardware/abi3_capability/hbm_sram_cluster_32.json --cost-table configs/hardware/abi3_cost_cluster32_v2.json --entrypoint 0 --transactions 1 --symbol SPAN_TOKENS=32 --symbol POSITION_START=0 --symbol POSITION_END=32 --symbol CONTEXT_LENGTH=32 --symbol PHASE=0 --symbol GENERATION_INDEX=0 --symbol MAX_NEW_TOKENS=16 --symbol BATCH=1 --symbol SPAN_LAST_INDEX=31 --check-functional-agreement --out results/abi3/deepseek_v4_flash_hbm_p32_prefill_cycle.json` | **`executed`**, current-tree functional/cycle counter reconciliation | **QUALIFIED YES** — exact deployment, capability and cost-table digests are bound; the artifact carries no full Python source map |
| The schedule audit is complete over **447** operators with no findings or contract gaps <!-- figure: 447 src="results/abi3/deepseek_v4_flash_hbm_p32_prefill_cycle.json#schedule_audit.operators_checked" name="DeepSeek HBM cycle operators audited, ledger" --> | the same artifact → `schedule_audit` and `gaps` | the same governed command; strict schedule admission is the default | **`executed`**, schedule-contract evidence | **YES for the bound deployment/request** |
| The model reports **244,691,019,251** cycles <!-- figure: 244,691,019,251 src="results/abi3/deepseek_v4_flash_hbm_p32_prefill_cycle.json#timing.total_cycles" name="DeepSeek HBM modeled prefill cycles, ledger" --> from **124** assumed and **5** characterized parameters <!-- figure: 124 src="results/abi3/deepseek_v4_flash_hbm_p32_prefill_cycle.json#provenance.counts.assumed" name="DeepSeek HBM assumed cycle parameters, ledger" --> <!-- figure: 5 src="results/abi3/deepseek_v4_flash_hbm_p32_prefill_cycle.json#provenance.counts.characterized" name="DeepSeek HBM characterized cycle parameters, ledger" --> | the same artifact → `timing.total_cycles` and `provenance` | the cycle model plus `configs/hardware/abi3_cost_cluster32_v2.json` | **`assumed`**, not measured or characterized performance | **CURRENT INPUTS, NOT A PERFORMANCE CLAIM** |

This is the first retained governed cycle result over a shipped real-model
deployment rather than a fixture. It exercises the admitted 32-node program,
node-indexed communication, queues, barriers, schedule descriptors and memory
traffic, then runs a separate functional device for the counter comparison.
The result has an empty `differences` map, a complete schedule audit, and an
empty `gaps` list.

**Boundary.** The artifact's own provenance class is `assumed` and
`depends_on_assumed_values` is true. Its modeled 244.691 seconds is therefore
not latency, throughput, projection, or silicon evidence. The input record
binds the deployment, capability, cost table and request symbols, but not a
workload/prompt artifact or a full Python source map. `functional_agreement`
compares architectural counters; it does not compare the `produced_tokens`
field with the external oracle. Token correctness remains the job of the
hardened four-token capture, and RTL remains the separately bounded W8.8
control-plane campaign.

## 9b. Oasis causal-state and MiniMax-H3 ROM attribution

| number / claim | where it is stated | what produces it | grade | current? |
|---|---|---|---|---|
| At the central W32 envelope, the proposed Oasis causal cache is a **25.618×** algorithmic change <!-- figure: 25.618 src="results/world-model/analytical.json#findings.central_oasis_w32_cache_algorithmic_speedup" name="Oasis W32 causal-cache algorithmic speedup, ledger" -->; with whole-call weight reuse and local temporal state, immutable ROM contributes **2.225×** over same-compute HBM <!-- figure: 2.225 src="results/world-model/analytical.json#findings.central_oasis_w32_cached_rom_storage_speedup_local_cache" name="Oasis W32 local-cache ROM attribution, ledger" -->, falling to **1.128×** when all cache bytes cross the modeled global cut <!-- figure: 1.128 src="results/world-model/analytical.json#findings.central_oasis_w32_cached_rom_storage_speedup_remote_cache" name="Oasis W32 remote-cache ROM attribution, ledger" --> and **1.086×** under the one-row service proxy <!-- figure: 1.086 src="results/world-model/analytical.json#findings.central_oasis_w32_cached_rom_storage_speedup_per_stream_proxy" name="Oasis W32 per-stream ROM attribution, ledger" --> | `results/world-model/REPORT.md` | `make world-model` from hash-locked source inventories, the existing leading-node hardware envelope, explicit cache-placement/NoC/reuse sweeps, and a same-compute HBM counterfactual | **`simulated/derived`** | **YES, analytical only** |
| Across the baseline dense and deliberately favorable four-call/sparse MiniMax-H3 controls, ROM storage attribution is **1.000×–1.000×** <!-- figure: 1.000 src="results/world-model/analytical.json#findings.h3_rom_storage_speedup_min" name="H3 ROM attribution minimum, ledger" --> <!-- figure: 1.000 src="results/world-model/analytical.json#findings.h3_rom_storage_speedup_max" name="H3 ROM attribution maximum, ledger" --> because modeled full-clip compute/NoC hides both ROM and HBM weight service | the same report, H3 control section | pinned public H3 config/checkpoint headers/Diffusers graph, with official AdaLN precomputation credited and both QKV HBM service and precomputed AdaLN output-table service omitted favorably | **`simulated/derived`** | **YES, analytical only** |

**Boundary.** The Oasis cache is a source-derived transformation, not released or
executed behavior; exactness through dynamic noising and sliding-window rollover
is open. MiniMax-H3 was not executed. OpenTallas has no video ABI, compiler,
diffusion scheduler, causal frame-state backend, RTL, cycle model, physical
implementation, or silicon result. The integer ROM row-reuse law is a
service-byte sensitivity rather than validated compute-in-ROM timing. None of
these figures is a video throughput or implementation claim.

## 9c. Recent world-model decode-shape ROM screen

| number / claim | where it is stated | what produces it | grade | current? |
|---|---|---|---|---|
| In the central same-compute envelope, the BF16 and matched-FP8 HBM weight/compute ridge is **373.272 fresh rows per dominant matrix call** <!-- figure: 373.272 src="results/world-model-landscape/analytical.json#hardware_formats[label=BF16].same_compute_hbm_ridge_rows" name="Recent world-model central HBM row ridge, ledger" -->; the B300 BF16 control ridge is **174.194 rows** <!-- figure: 174.194 src="results/world-model-landscape/analytical.json#hardware_formats[label=BF16].gpu_hbm_ridge_rows" name="Recent world-model B300 HBM row ridge, ledger" --> | `results/world-model-landscape/REPORT.md`, hardware-ridge section | `make world-model-landscape`, using the existing leading-node compute and storage envelopes and the closed-form dominant-linear row roofline | **`simulated/derived`** | **YES, analytical only** |
| Four source-derived open paths plus EVOKE's explicitly assumed temporal window carry **1,560–8,800 fresh current rows** before favorable exclusions and therefore each has **1.000×** standard roofline ROM attribution. Even a deliberately impossible, fully serial endpoint with all ROM weight service set to zero gives dominant-linear ceilings of only **1.239×** for WorldPlay, **1.183×** for AlayaWorld, **1.080×** for LingBot, **1.043×** for EVOKE, and **1.042×** for Matrix-Game 3.0 <!-- figure: 1.080 src="results/world-model-landscape/analytical.json#model_screens[model=LingBot-World-Infinity 14B causal-fast].zero_cost_rom_additive_upper_bound" name="LingBot dominant-linear zero-ROM-cost ceiling, ledger" --> | the same report, row sweep and model-by-model screen | Commit-pinned official repositories/configurations determine four current-query geometries; EVOKE's spatial factors are pinned but its nine-latent-frame current window is an explicit favorable assumption. A one-billion-active-matrix-parameter normalization demonstrates that parameter count and denoiser-call count cancel from the weight/compute balance | **source-derived/assumed geometry plus `simulated/derived` roofline** | **YES, as a favorable screen—not a whole-model bound** |
| Atlas and RTFM are structurally more promising than full-clip H3 because they expose autoregressive elements and reusable history, but their public material does not disclose enough latent geometry, denoiser calls, active matrices/dtypes, cache bytes, or measured latency/hardware to assign a numerical OpenTallas speedup. Cosmos 3 separately shows a narrow causal next-token Reasoner path and a broad full-attention diffusion Generator path, so the family label alone is insufficient. | the same report, Atlas/RTFM and Cosmos sections | Primary World Labs launch posts and pinned NVIDIA report/repository; missing numerical inputs are retained as null rather than imputed | **source audit / conditional inference** | **YES** |

**Boundary.** Fresh-row counts are lower bounds for the dominant high-resolution
linear path, not full execution traces. Four surveyed row geometries are
source-derived; EVOKE's nine-latent-frame temporal factor is an explicit
favorable assumption, and MiniMax-H3's 512 text rows are also assumed. The
zero-ROM-cost values are ceilings only for that isolated dominant-linear path;
unmodeled narrow-row branches could have a larger ROM-attributable fraction,
while attention, cache construction, KV traffic, collectives, VAE work, and
runtime overhead can alter the end-to-end result. Atlas and RTFM rely on mutable
dated pages and have no numerical result. No surveyed model was run on
OpenTallas, and OpenTallas still has no video ABI, compiler, diffusion
scheduler, causal-frame backend, RTL, physical implementation, or silicon
result.
