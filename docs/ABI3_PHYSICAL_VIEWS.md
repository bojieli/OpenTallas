# ABI 3.0 physical implementation views

Factual record of the physical-implementation flows established for the
OpenTallas ABI 3.0 program: which technology views exist on this machine, what
each one can actually do, the exact tool and PDK identities behind every
number, and what cannot be reproduced offline.

Everything in this document was produced by running the tools described here.
No number is estimated, scaled, or carried over from another node.

Driver: `tools/run_abi3_physical.py`
Results: `results/physical_abi3/`
Environment test: `tests/test_abi3_physical_env.py`

> **Which design these numbers are about.** A routed area, period, slack or
> power figure is a measurement of a netlist, and the netlist only means
> something once its function is established against something. For the ABI 3.0
> blocks that reference is `runtime.sim.device.Device`, and the campaign that
> establishes it against the programs this repository actually ships is
> checklist W8.8, `results/rtl/abi3_deployment_campaign.json`.
>
> **The rule.** A number in this document may be cited as the implementation
> cost of a design that provably runs exactly the deployments that campaign's
> `correlated_cases` field records — and **none of them may be cited, scaled or
> aggregated as the cost of anything that runs a deployment it does not
> record.** Read that field rather than a sentence: it moves whenever a
> sequencer bound is raised and the campaign is re-run. As recorded at commit
> `518260f` it named the two Qwen3-8B deployments, the ROM single chip and the
> HBM single chip, and not the DeepSeek-V4-Flash ROM wafer one, which the RTL
> trapped after eight retirements on a bound nothing expressed at admission.
>
> Nothing here is retracted by that. The co-simulation is a functional result
> and says nothing whatever about area, timing or power; it bounds which machine
> a number is allowed to describe, not what the number is.
>
> Two further limits, already true and easy to lose. **No block of the ABI 3.0
> control plane appears below at all** — the routed blocks are the ABI 2.5
> engines, the four W8.3 ABI 3.0 datapaths and the numeric probes, and the
> reason the microsequencer is absent is [OI-43] in
> `docs/UNIFIED_EXECUTION_CHECKLIST.md`. That sentence has one exception since
> OI-43 closed: `results/physical_abi3/asap7/a3_microsequencer/pnr.json` routes
> `ot_a3_microsequencer` at `STATE_COMPAT = 0` alone at asap7 — fetch/decode,
> loop stack, event scoreboard and one view-resolver lane; no descriptor
> store, no dependence table, no engine, no memory macro — which is the
> control plane's front-end block, not the control plane, and its numbers are
> read from that record and its `notes`, not from this document. And no
> frequency, area or energy from a
> 130 nm or predictive-7 nm open PDK may be scaled to N6/N5/N7/N4
> (`docs/METHODOLOGY.md` §9).

## Summary answer: which flows do full place-and-route?

**Both chosen views do full place-and-route. Neither is synthesis+STA only.**

| View | Synthesis | Static timing | Full place-and-route | Proven by |
|---|---|---|---|---|
| `sky130hd` (130 nm, mature) | yes | yes, 4 corners | **yes** — ORFS `sky130hd` | routed, DRC 0, antenna 0 |
| `asap7` (7 nm, predictive) | yes | yes, 1 corner | **yes** — ORFS `asap7` | routed, DRC 0, antenna 0 |
| `ihp-sg13g2` (130 nm) | available | available | available (ORFS platform ships) | **not run** |
| `nangate45` (45 nm) | available | available | available (ORFS platform ships) | **not run** |

ASAP7 did not need replacing. It place-and-routes, and it reproduced the
archived ASAP7 campaign bit-for-bit (§6). The rows marked *not run* are
genuinely available in the same container but were not exercised by this work;
they are capability statements about the tooling, not results.

---

## 1. The two chosen views

| | Mature implementation view | Predictive view |
|---|---|---|
| Name | `sky130hd` | `asap7` |
| Process | SkyWater SKY130, 130 nm | ASAP7, 7 nm predictive FinFET |
| Cell library | `sky130_fd_sc_hd` | `asap7sc7p5t` RVT |
| Evidence class | Open **manufacturable** foundry PDK | **Predictive academic** PDK, not manufacturable |
| Synthesis + STA | yes, local pinned tools | yes, local pinned tools |
| Place-and-route | yes, via pinned ORFS container | yes, via pinned ORFS container |
| Corners available locally | 18 liberty corners (4 registered) | 1 (RVT TT) |
| Real SRAM macros in PDK | yes (`sky130_sram_macros`) | no |

### Why these two

The brief asked for a mature implementation view and a predictive view, clearly
separated. Four candidates were assessed against what actually works after the
downloads landed:

* **SKY130 HD — chosen as the mature view.** The full PDK download succeeded, so
  `sky130_fd_sc_hd` now has liberty at 18 process/voltage/temperature corners,
  LEF, tech LEF, GDS, and Verilog models locally. It is a real, manufacturable
  foundry process. ORFS also ships a `sky130hd` platform, so the same view
  supports full place-and-route. It is the most widely taped-out open PDK.
* **ASAP7 — chosen as the predictive view.** It is the only 7 nm-class option
  available, it exercises a genuinely different technology generation from the
  mature view, and the pinned ORFS image that contains it is byte-identical to
  the image behind the archived `results/asap7_physical/` campaign (see §6).
* **IHP SG13G2 — available, not chosen.** The local tree is complete and
  includes real SRAM macros, and ORFS ships an `ihp-sg13g2` platform, so this
  view could be added cheaply. It was not chosen because it is also a 130 nm
  process: pairing it with SKY130 would give two views at the same node rather
  than the required separation. It remains the natural second mature view and
  is already locked by `configs/pdk/ihp_sg13g2_physical_lock.json`.
* **Nangate45 — available, not chosen.** Typical-corner liberty and LEF only,
  and it is a generic educational library rather than a foundry process, so it
  is the weakest evidence class of the four. ORFS does ship a `nangate45`
  platform, so it could do place-and-route if ever needed.

---

## 2. Exact tool identities

All binaries are hard-pathed. The system-provided Yosys (0.9), Verilator
(4.038) and Magic (8.3.105) are too old, and the system `netgen` is a mesh
generator, not the LVS tool; none of them are on any path this flow uses.
`tests/test_abi3_physical_env.py` asserts the pinned versions.

| Tool | Version | Path | sha256 |
|---|---|---|---|
| Yosys | 0.68 (git sha1 38e001a6f) | `~/.local/opentallas-tools/yosys-0.68/bin/yosys` | `44eda4ce93270e581abfb8dd28ab77489bf9e7c43aadbf906faf30f2fffc2e50` |
| ABC | bundled with Yosys 0.68 | `~/.local/opentallas-tools/yosys-0.68/bin/yosys-abc` | `da898a762b6c3d0f4e76d3a4c142fea05dd14d98916e315e942ea9227e4e87ce` |
| OpenSTA | 3.1.0 (be771a0116) | `~/.local/opentallas-tools/opensta-be771a0/bin/sta` | `ecf87c20ca592279f330aeb5681610616b16df810e4f308b855af04605a09a88` |

Place-and-route container:

| Item | Value |
|---|---|
| Image | `openroad/orfs:latest` |
| Image ID | `sha256:af971398d91e5d154ec40d3df26554efd8790107268a4c7f1e6bb8f222979d34` |
| Manifest-list digest as pulled | `sha256:d995618be9f2bcdfa5538b885123463070dfbf178bea1818716d4652fe0fa380` |
| OpenROAD | `26Q3-1510-g6cb3f2b704` |
| Yosys inside image | `0.68+post` |

The image ID is the authoritative identity and is recorded in every
place-and-route result. It is checked against the archived ASAP7 campaign by
`tests/test_abi3_physical_env.py`.

---

## 3. Exact PDK identities

### 3.1 SKY130 full PDK — new root, new lock

Installed at `~/.local/opentallas-pdk-full` by `ciel` 2.6.1, open_pdks release
`f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7`. Libraries: `sky130_fd_io`,
`sky130_fd_pr`, `sky130_fd_sc_hd`, `sky130_fd_sc_hvl`, `sky130_ml_xx_hd`,
`sky130_sram_macros`. Installed tree: 8374 files, 1 114 549 811 bytes,
manifest sha256 `d92f7dbb964318953d1a6f2e0c3a50aa3780d68a42e265d1e6e8cbad12d65f21`.

Recorded in **`configs/pdk/sky130_full_physical_lock.json`** (new file).

> **The pre-existing locks were not modified.** `sky130_physical_lock.json`
> covers a *different* root, `~/.local/opentallas-pdk`, which holds
> `sky130_fd_pr` device models only and whose tree hash backs the retained
> SPICE evidence. That root was not touched by this installation; its
> `libs.ref` still contains exactly `sky130_fd_pr`, and
> `tests/test_abi3_physical_env.py` asserts this. `ihp_sg13g2_physical_lock.json`
> was likewise not modified.

Registered corners (liberty time unit 1 ns, capacitance unit 1 pF):

| Corner | Liberty | V | T |
|---|---|---|---|
| `tt` (default) | `sky130_fd_sc_hd__tt_025C_1v80.lib` | 1.80 V | 25 °C |
| `ss` | `sky130_fd_sc_hd__ss_100C_1v60.lib` | 1.60 V | 100 °C |
| `ff` | `sky130_fd_sc_hd__ff_n40C_1v95.lib` | 1.95 V | −40 °C |
| `ss_lv` | `sky130_fd_sc_hd__ss_n40C_1v28.lib` | 1.28 V | −40 °C |

`tt` liberty sha256 `8e78e14442062dba34d414fca6490b2f6b96038d4510d1438ca44fee31487135`.

### 3.2 ASAP7 local liberty — new root, new lock

ASAP7 ships only inside the ORFS container. To let the *pinned host* Yosys and
OpenSTA characterise the predictive view, the five RVT TT NLDM liberty objects
were copied out of the pinned image to `~/.local/opentallas-pdk-asap7` and the
four gzip-compressed ones were decompressed. Content is otherwise unmodified.

Every container source object's sha256 was compared against the corresponding
entry in the pre-existing `configs/pdk/asap7_physical_lock.json` and **all five
matched**, so the local copy provably descends from the archived ASAP7
identities. `tests/test_abi3_physical_env.py` re-checks this.

Recorded in **`configs/pdk/asap7_local_liberty_lock.json`** (new file).

Liberty time unit is **1 ps** and capacitance unit **1 fF** — a thousand-fold
difference from SKY130. The driver carries a per-view `time_unit_ns` and
converts, and the environment test asserts the declared unit against the
liberty header, because a mismatch would silently scale every reported Fmax by
1000x.

ASAP7 LEF, GDS and DRC decks were **not** mirrored locally; the
place-and-route lane reads them from the container.

### 3.3 A real caveat: the P&R lane does not read the local liberty

For `sky130hd`, the local synthesis/STA lane reads
`sky130_fd_sc_hd__tt_025C_1v80.lib` from the full PDK
(`8e78e144…`), while the ORFS place-and-route lane reads the container's own
copy of a file with the same name (`ec0e1067…`). **These are different files
from different open_pdks builds.** Both identities are recorded in every result
record (`corner.liberty[].sha256` and
`place_and_route.platform_file_sha256`). Local pre-layout STA and container
post-route STA for this view are therefore not guaranteed to be
library-identical, and small differences between the two lanes should be
attributed to that before anything else.

---

## 4. What each flow can and cannot do

| View | Synthesis | Pre-layout STA | Full P&R | Post-route parasitic STA | DRC / antenna |
|---|---|---|---|---|---|
| `sky130hd` | pinned Yosys 0.68 + ABC | pinned OpenSTA 3.1.0 | ORFS `sky130hd` | inside ORFS (SPEF) | ORFS detailed route |
| `asap7` | pinned Yosys 0.68 + ABC | pinned OpenSTA 3.1.0 | ORFS `asap7` | inside ORFS (SPEF) | ORFS detailed route |

Both chosen views support **full place-and-route**. Neither is
synthesis-and-STA-only. Nangate45 and IHP SG13G2 are registered nowhere in the
driver today; adding them is a config-table edit, not new code.

Two flow details worth recording:

* **`signed` port declarations.** Yosys writes `input signed [31:0] x;` for
  signed RTL ports, and OpenSTA's Verilog reader rejects it (`syntax error`),
  both on the host and inside OpenROAD. The driver strips the `signed`
  attribute from declarations in the mapped gate netlist. This is a
  declaration-attribute-only edit: no cell, net, port or connectivity change.
  Both the raw and normalised netlist sha256 are recorded.
* **Two-phase ORFS run.** Because of the above, place-and-route runs ORFS
  synthesis first, normalises the mapped netlist on the host, then resumes the
  flow through `finish metadata-generate`. This mirrors the method already used
  by `tools/run_asap7_physical.py`.

---

## 5. Measured results

Blocks are existing RTL already in the tree. Both map to standard cells only —
`ot_ta_add_bf16_sram_engine` presents SRAM as an external interface and
instantiates no macros, so `macro_count` is 0 in every run below and no macro
placement was exercised.

### 5.0 How to read `status` in these artifacts

Every record carries two separate fields, and they mean different things:

* **`flow_completed`** — did the script run to completion without erroring.
* **`status`** — the **engineering** result. `pass` only when every
  timing-bearing stage that ran met setup *and* hold with zero violating paths,
  and, for place-and-route, zero DRC and zero antenna violations. Otherwise
  `not_met`. `not_evaluated` when nothing timing-bearing ran (synthesis alone),
  and `error` when the flow itself failed.

A run that did not close timing is emitted as `not_met`, never as `pass`. The
`acceptance` block records the criterion and the per-stage checks that produced
the verdict. Records also carry `purpose`: `signoff_target` means the target
period is the intended operating point, `characterization` means it is a probe.
`expected_not_met` documents that a corner was deliberately swept past its
closing point; it annotates intent and does **not** soften `status`.

`tests/test_abi3_physical_env.py` walks every emitted artifact and fails if any
of them claims `pass` while carrying unmet timing, DRC or antenna violations.

### 5.1 Synthesis + pre-layout STA

Typical corner, pinned Yosys + pinned OpenSTA, ideal clock.
`Fmax` is from bisection on the SDC clock period with the mapped netlist held
fixed — the smallest period with setup WNS ≥ 0.

| View | Block | Cells | Cell area (µm²) | Sequential area (µm²) | Macros | Target period | WNS (ns) | Fmax |
|---|---|---|---|---|---|---|---|---|
| `sky130hd` tt | `ot_reduction_endpoint` | 3 374 | 39 148.33 | 18 100.00 | 0 | 20 ns | +2.4873 | **57.08 MHz** |
| `sky130hd` tt | `ot_ta_add_bf16_sram_engine` | 12 774 | 106 312.27 | 38 267.08 | 0 | 28 ns | +1.2104 | **37.74 MHz** |
| `asap7` TT | `ot_reduction_endpoint` | 5 072 | 679.94 | 190.24 | 0 | 2.25 ns | +0.2730 | **505.68 MHz** |
| `asap7` TT | `ot_ta_add_bf16_sram_engine` | 12 549 | 1 785.79 | 578.48 | 0 | 4.4 ns | +0.1746 | **239.06 MHz** |

All four meet timing at their target period.

The critical path of `ot_reduction_endpoint` is a 32-bit ripple-carry chain
(a run of `maj3` carry cells) into the accumulator register; that structure,
not the library, is what sets its frequency.

### 5.2 SKY130 corner spread

`ot_reduction_endpoint`, same mapped netlist, four corners:

All four runs use a 20 ns target period, so the two slow corners are being
swept past their closing point deliberately. Their `status` is `not_met`, and
that is the correct and useful engineering result: **`ot_reduction_endpoint`
does not close at 20 ns at either SKY130 slow corner.**

| Corner | V | T | Setup WNS @ 20 ns | Violating paths | Meets 20 ns? | Min period | Fmax |
|---|---|---|---|---|---|---|---|
| `ff` | 1.95 V | −40 °C | +10.3787 ns | 0 | **yes** (`pass`) | 9.624 ns | 103.91 MHz |
| `tt` | 1.80 V | 25 °C | +2.4873 ns | 0 | **yes** (`pass`) | 17.520 ns | 57.08 MHz |
| `ss` | 1.60 V | 100 °C | −17.3770 ns | 21 | **no** (`not_met`) | 37.383 ns | 26.75 MHz |
| `ss_lv` | 1.28 V | −40 °C | −129.3212 ns | 618 | **no** (`not_met`) | 149.403 ns | 6.69 MHz |

The block closes at 20 ns at `tt` and `ff` only. To close at the conventional
slow corner `ss` it would need a target period of at least 37.4 ns, i.e. a
26.75 MHz operating point; at the extreme low-voltage corner `ss_lv`
(1.28 V, −40 °C) it needs 149.4 ns. A design intended to run at 20 ns across
PVT would therefore have to be re-pipelined — the 32-bit ripple-carry chain in
the reduction path is the limiter.

This corner spread is available only in the mature view; the local ASAP7 copy
has a single TT corner, so the predictive view carries no slow-corner evidence
at all.

### 5.3 Place-and-route

Full RTL-to-routed-layout through the pinned ORFS container. All four runs
completed and **all four met timing with zero DRC errors and zero antenna
violations** (`status: pass`).

Placement and routing quality:

| View | Block | Target | Std cells | Macros | Std-cell area (µm²) | Sequential area (µm²) | Die area (µm²) | Utilisation |
|---|---|---|---|---|---|---|---|---|
| `sky130hd` | `ot_reduction_endpoint` | 20 ns | 7 035 | 0 | 54 459.7 | 18 077.3 | 140 993.0 | 0.397 |
| `sky130hd` | `ot_ta_add_bf16_sram_engine` | 28 ns | 16 523 | 0 | 134 763.0 | 38 227.9 | 330 366.0 | 0.416 |
| `asap7` | `ot_reduction_endpoint` | 2.25 ns | 7 507 | 0 | 845.5 | 190.2 | 2 651.2 | 0.377 |
| `asap7` | `ot_ta_add_bf16_sram_engine` | 4.4 ns | 17 617 | 0 | 2 008.3 | 578.5 | 5 844.0 | 0.385 |

Routing, post-route timing and violations:

| View | Block | Routed wire length | Vias | Routed nets | DRC | Antenna nets | Antenna pins | Setup WNS | Hold WNS | Fmax | Power | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `sky130hd` | `ot_reduction_endpoint` | 174 411 µm | 39 744 | 5 678 | **0** | **0** | **0** | +5.0836 ns | +0.4595 ns | 67.04 MHz | 22.9 mW | `pass` |
| `sky130hd` | `ot_ta_add_bf16_sram_engine` | 479 089 µm | 89 091 | 13 956 | **0** | **0** | **0** | +2.2315 ns | +0.4743 ns | 38.81 MHz | 46.3 mW | `pass` |
| `asap7` | `ot_reduction_endpoint` | 22 184 µm | 61 473 | 7 546 | **0** | **0** | **0** | +0.0535 ns | +0.0558 ns | 455.26 MHz | 25.8 mW | `pass` |
| `asap7` | `ot_ta_add_bf16_sram_engine` | 64 571 µm | 139 656 | 18 698 | **0** | **0** | **0** | +0.2175 ns | +0.0565 ns | 239.09 MHz | 31.2 mW | `pass` |

Post-route Fmax is *higher* than the pre-layout figure in §5.1 for the SKY130
runs (67.04 vs 57.08 MHz for the reduction endpoint; 38.81 vs 37.74 MHz for the
bf16 engine). That is not an inconsistency: ORFS performs timing-driven
resizing, buffering and clock-tree synthesis that the plain local
Yosys/ABC mapping does not, and it reads a different liberty file (§3.3).
The local synthesis+STA lane is the cheaper screen; the ORFS lane is the
stronger result.

ORFS reports slack in the SDC's own time unit — nanoseconds for `sky130hd` but
**picoseconds** for `asap7`. The driver converts to nanoseconds and retains the
raw values under `metrics.raw_timing_library_units`.

**DRC counts here come from the detailed router's own rule checks, not from a
foundry signoff deck.** Zero DRC in this table means the router believes it
routed legally; it is not a signoff DRC clean.

Retained artifacts per run are in `<output>_artifacts/` next to each
`pnr.json`: `config.mk`, `constraint.sdc`, `metadata.json`, `1_2_yosys.v`,
`6_final.v`, `6_finish.rpt`, `5_route_drc.rpt`. The heavy outputs
(`6_final.def`, `.gds`, `.odb`, `.spef`) are hashed and recorded but not
retained by default; `--keep-heavy-artifacts` retains them.

---

## 6. Reproducibility of the archived ASAP7 results

`results/asap7_physical/` holds a three-case ORFS campaign
(`numeric_e1_l16_tc`, `numeric_e4_l16_tc`, `reduction_s8_g2_tc`) produced by
`tools/run_asap7_physical.py` and locked by
`configs/pdk/asap7_physical_lock.json`.

**These results are reproducible now, and one of the three cases was actually
reproduced bit-for-bit.**

The ORFS image pulled for this work has image ID `sha256:af971398d91e…`, which
is exactly the `image_id` recorded in `configs/pdk/asap7_physical_lock.json`.
The ASAP7 platform files inside it still hash to the values that lock records —
verified for all five RVT TT NLDM liberty objects during extraction, all
matching.

Beyond that identity argument, the `asap7` / `reduction_s8_g2` place-and-route
run performed here — driven by the *new* `tools/run_abi3_physical.py`, with its
own config and SDC — landed on **numerically identical** results to the
archived `reduction_s8_g2_tc` case:

| Metric | This flow | Archived campaign |
|---|---|---|
| Routed wire length | 22 184 µm | 22 184 µm |
| Vias | 61 473 | 61 473 |
| DRC errors | 0 | 0 |
| Antenna violating nets / pins | 0 / 0 | 0 / 0 |
| Fmax | 455 262 000 Hz | 455 262 000 Hz |
| Setup WNS | 53.4617 ps | 53.4617 ps |
| Core / die area | 2 240.22 / 2 651.22 µm² | 2 240.22 / 2 651.22 µm² |
| Standard-cell area | 845.509 µm² | 845.509 µm² |
| Utilisation | 0.377423 | 0.377423 |
| **`6_final.v` sha256** | `ed82979b637ef255…` | `ed82979b637ef255…` |

The final routed netlist is **byte-identical**. The archived ASAP7 campaign is
therefore not merely reproducible in principle; its routed result was
regenerated exactly on this machine.

Two qualifications, stated precisely:

1. **The recorded amd64 manifest digest was not re-verified.** The lock records
   `openroad/orfs@sha256:16470cea1d346bfa…` as the amd64 digest. The pull
   resolved the `latest` tag to manifest-list digest
   `sha256:d995618be9f2bcdf…`. These are different digest types; the config
   digest (image ID) matches exactly, which is the identity that determines
   tool behaviour. The tag `latest` is mutable, so a future pull may not yield
   this image — the image ID, not the tag, is what must be checked.
2. **Only one of the three archived cases was reproduced.**
   `reduction_s8_g2_tc` was matched byte-for-byte as shown above. The other two
   cases, `numeric_e1_l16_tc` and `numeric_e4_l16_tc`, were **not run**.
   `tools/run_asap7_physical.py` itself was not re-executed, so the archived
   campaign's formal equivalence checking and unconstrained-endpoint audit were
   not re-run either — this flow does not perform those checks at all.

The two are the same RTL block at the same target period (2.25 ns) and, for the
place-and-route lane, the same computation — hence the identical netlist hash.
They are still not the same *campaign*: the archived one additionally ran formal
equivalence checking and an unconstrained-endpoint audit that this flow does
not. The separate synthesis+STA lane here also uses a different front end (the
pinned host Yosys rather than ORFS's own), which is why §5.1's pre-layout
numbers differ from §5.3's post-route numbers.

---

## 7. What is not reproducible offline

* **Everything requiring a fresh network fetch.** The ORFS image
  (4.65 GB) and the full SKY130 PDK (2.2 GB installed) are already on this
  machine. On a clean machine both must be downloaded; `latest` is a mutable
  tag, so an ORFS pull is not guaranteed to reproduce the pinned image ID.
* **ASAP7 without the container.** ASAP7 is not separately packaged here. The
  local liberty copy is sufficient for synthesis and STA, but ASAP7
  place-and-route requires the container's LEF, GDS and tech files, which were
  not mirrored.
* **Foundry signoff of any kind.** No view here is a signoff flow. There is no
  foundry DRC/LVS signoff deck run, no sign-off timing with OCV/AOCV, no IR-drop
  signoff, and no library characterisation. ORFS DRC counts come from the
  detailed router's own rule checks, not from a foundry deck.
* **Any target-node inference.** SKY130 is 130 nm and ASAP7 is a 7 nm
  *predictive academic* PDK. Neither supports claims about a target foundry
  node's density, delay, energy, leakage, yield or cost. Both lock files carry
  an explicit `forbidden_inferences` list.
* **Macro-bearing implementation.** Both blocks proved here contain zero
  macros. SRAM macro placement has not been exercised in either view, although
  the SKY130 full PDK does now contain real `sky130_sram_macros` (and IHP
  SG13G2 contains `sg13g2_sram`) should the program need it.

---

## 8. Reproducing this

From the repository root.

Environment check:

```
python3 -m pytest tests/test_abi3_physical_env.py -q
```

Synthesis + STA, both views, both blocks:

```
python3 tools/run_abi3_physical.py --view sky130hd --block reduction_s8_g2 \
    --clock-period-ns 20 --stages synth,sta --fmax-search \
    --output results/physical_abi3/sky130hd/reduction_s8_g2/synth_sta.json

python3 tools/run_abi3_physical.py --view sky130hd --block add_bf16_sram_engine \
    --clock-period-ns 28 --stages synth,sta --fmax-search \
    --output results/physical_abi3/sky130hd/add_bf16_sram_engine/synth_sta.json

python3 tools/run_abi3_physical.py --view asap7 --block reduction_s8_g2 \
    --clock-period-ns 2.25 --stages synth,sta --fmax-search \
    --output results/physical_abi3/asap7/reduction_s8_g2/synth_sta.json

python3 tools/run_abi3_physical.py --view asap7 --block add_bf16_sram_engine \
    --clock-period-ns 4.4 --stages synth,sta --fmax-search \
    --output results/physical_abi3/asap7/add_bf16_sram_engine/synth_sta.json
```

(The four commands above each add `--purpose signoff_target`, since their target
period is the intended operating point.)

SKY130 corner sweep. The two slow corners are known not to close at 20 ns and
are marked as deliberate characterisation:

```
for c in tt ff; do
  python3 tools/run_abi3_physical.py --view sky130hd --block reduction_s8_g2 \
      --corner $c --clock-period-ns 20 --stages synth,sta --fmax-search \
      --purpose characterization \
      --output results/physical_abi3/sky130hd/reduction_s8_g2/corner_$c.json
done

for c in ss ss_lv; do
  python3 tools/run_abi3_physical.py --view sky130hd --block reduction_s8_g2 \
      --corner $c --clock-period-ns 20 --stages synth,sta --fmax-search \
      --purpose characterization --expected-not-met \
      --output results/physical_abi3/sky130hd/reduction_s8_g2/corner_$c.json
done
```

Full place-and-route, all four runs (each takes roughly 5-15 minutes):

```
python3 tools/run_abi3_physical.py --view sky130hd --block reduction_s8_g2 \
    --clock-period-ns 20 --stages pnr --purpose signoff_target \
    --output results/physical_abi3/sky130hd/reduction_s8_g2/pnr.json

python3 tools/run_abi3_physical.py --view sky130hd --block add_bf16_sram_engine \
    --clock-period-ns 28 --stages pnr --purpose signoff_target \
    --output results/physical_abi3/sky130hd/add_bf16_sram_engine/pnr.json

python3 tools/run_abi3_physical.py --view asap7 --block reduction_s8_g2 \
    --clock-period-ns 2.25 --stages pnr --purpose signoff_target \
    --output results/physical_abi3/asap7/reduction_s8_g2/pnr.json

python3 tools/run_abi3_physical.py --view asap7 --block add_bf16_sram_engine \
    --clock-period-ns 4.4 --stages pnr --purpose signoff_target \
    --output results/physical_abi3/asap7/add_bf16_sram_engine/pnr.json
```

An RTL top not in the built-in registry — for the ABI 3.0 blocks landing in
`rtl/abi3/` — is driven directly:

```
python3 tools/run_abi3_physical.py --view sky130hd \
    --top ot_abi3_some_block --source rtl/abi3/ot_abi3_some_block.sv \
    --clock-period-ns 20 --stages synth,sta --fmax-search \
    --false-path-from rst_n \
    --output results/physical_abi3/sky130hd/some_block/synth_sta.json
```

The driver refuses to overwrite an existing output unless `--force` is given.

If the PDK roots are installed elsewhere, override
`OPENTALLAS_TOOLS_ROOT`, `OPENTALLAS_PDK_FULL_ROOT`,
`OPENTALLAS_PDK_ASAP7_ROOT` or `OPENTALLAS_ORFS_IMAGE`.

Installing the two new roots from scratch:

```
ciel enable --pdk-root ~/.local/opentallas-pdk-full \
    f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7

docker pull openroad/orfs:latest
mkdir -p ~/.local/opentallas-pdk-asap7/lib/NLDM
docker run --rm -v ~/.local/opentallas-pdk-asap7:/out openroad/orfs:latest bash -lc '
  cd /OpenROAD-flow-scripts/flow/platforms/asap7 &&
  cp lib/NLDM/asap7sc7p5t_{AO,INVBUF,OA,SIMPLE}_RVT_TT_nldm_*.lib.gz \
     lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib /out/lib/NLDM/ &&
  chmod -R a+rwX /out'
gunzip -f ~/.local/opentallas-pdk-asap7/lib/NLDM/*.gz
```
