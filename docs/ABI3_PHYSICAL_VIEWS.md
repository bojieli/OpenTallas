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

| Corner | V | T | Min period | Fmax |
|---|---|---|---|---|
| `ff` | 1.95 V | −40 °C | 9.624 ns | 103.91 MHz |
| `tt` | 1.80 V | 25 °C | 17.520 ns | 57.08 MHz |
| `ss` | 1.60 V | 100 °C | 37.383 ns | 26.75 MHz |
| `ss_lv` | 1.28 V | −40 °C | 149.403 ns | 6.69 MHz |

This spread is available only in the mature view; the local ASAP7 copy has a
single TT corner.

### 5.3 Place-and-route

<!-- PNR_RESULTS -->

---

## 6. Reproducibility of the archived ASAP7 results

`results/asap7_physical/` holds a three-case ORFS campaign
(`numeric_e1_l16_tc`, `numeric_e4_l16_tc`, `reduction_s8_g2_tc`) produced by
`tools/run_asap7_physical.py` and locked by
`configs/pdk/asap7_physical_lock.json`.

**These results are reproducible now.** The ORFS image pulled for this work has
image ID `sha256:af971398d91e…`, which is exactly the `image_id` recorded in
`configs/pdk/asap7_physical_lock.json`. The ASAP7 platform files inside it
still hash to the values that lock records — verified for all five RVT TT NLDM
liberty objects during extraction, all matching.

Two qualifications, stated precisely:

1. **The recorded amd64 manifest digest was not re-verified.** The lock records
   `openroad/orfs@sha256:16470cea1d346bfa…` as the amd64 digest. The pull
   resolved the `latest` tag to manifest-list digest
   `sha256:d995618be9f2bcdf…`. These are different digest types; the config
   digest (image ID) matches exactly, which is the identity that determines
   tool behaviour. The tag `latest` is mutable, so a future pull may not yield
   this image — the image ID, not the tag, is what must be checked.
2. **The archived campaign itself was not re-executed.** This work established
   a new flow and proved it on `ot_reduction_endpoint` and
   `ot_ta_add_bf16_sram_engine`; it did not re-run
   `tools/run_asap7_physical.py` over its three cases. The claim above is that
   the toolchain and PDK inputs are byte-identical, not that a re-run was
   performed and compared.

Note that `results/asap7_physical/reduction_s8_g2_tc` and the `asap7`
`reduction_s8_g2` results here are the **same RTL block at the same target
period (2.25 ns)** but are *not* the same experiment: the archived campaign ran
formal equivalence checking and an unconstrained-endpoint audit that this flow
does not, and the two use different synthesis front ends (ORFS's own Yosys
versus the pinned host Yosys) for the synthesis/STA lane.

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

SKY130 corner sweep:

```
for c in tt ss ff ss_lv; do
  python3 tools/run_abi3_physical.py --view sky130hd --block reduction_s8_g2 \
      --corner $c --clock-period-ns 20 --stages synth,sta --fmax-search \
      --output results/physical_abi3/sky130hd/reduction_s8_g2/corner_$c.json
done
```

Full place-and-route:

```
python3 tools/run_abi3_physical.py --view sky130hd --block reduction_s8_g2 \
    --clock-period-ns 20 --stages pnr \
    --output results/physical_abi3/sky130hd/reduction_s8_g2/pnr.json

python3 tools/run_abi3_physical.py --view asap7 --block reduction_s8_g2 \
    --clock-period-ns 2.25 --stages pnr \
    --output results/physical_abi3/asap7/reduction_s8_g2/pnr.json
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
