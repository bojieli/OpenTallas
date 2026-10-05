# HA2 direct die-to-die all-reduce, measured in RTL (2026-10-04)

Accelerator (ours). Successor to Codex's HA2 snapshot attempt (`results/rtl/hbm_accel_ha2_20261003/`, REJECTED
snapshot gather, reducer build exit 95). Nothing there is overwritten.

## What was built

- `rtl/hbm_accel/ha2_ar/ot_ha2_ar_endpoint.sv` (ENABLE = 0 by default: all outputs tied off). One die's
  cut-through collective endpoint, placed at the fabric-SerDes edge of the V4.1 HBM die. 20 ports: 15 local
  (all lanes of a 16-die group) and 5 global (the same lane in the 5 other groups).
  - Reduce-scatter: each o-group contributor sends slice s of its 1,024 FP32 partials straight to owner s.
    Injection is slice-interleaved, 2 flits a cycle.
  - Reduction: each owner reduces a flit as soon as all 8 operands are slotted. It uses the golden tree
    `((p0+p1)+(p2+p3))+((p4+p5)+(p6+p7))` in rank order with `ot_hdc_fp32_add_lat #(7)` (LAT 7 closes SS at
    1.2 GHz standalone, w11_fp_latency_sweep nm_fadd7), followed by the golden `to_bf16`.
  - Multicast: each result flit goes out on all 20 ports. A die that receives a flit on a global port delivers it
    and relays it on its 15 local ports.
  - Delivery: results reach the hub at 4 flits (2,048 bits) a cycle. Credits are per port, 32 flits each.
- `rtl/hbm_accel/ha2_ar/ot_ha2_link.sv`: one direction of a link.
  - Wire stages: 14 between the endpoint and the SerDes on each side.
  - TX clock-domain crossing: `ot_link_afifo` (Gray code, 2 flops).
  - Serializer pacing: 2 lanes x 112 Gb/s x RS(272,257) = 211.65 bits/ns. A 551-bit flit leaves every 2.6 ns.
  - PHY/FEC latency: the light-FEC hop of 130 ns adopted in w15_collectives board_112g, which is an ESTIMATE.
    Global links add 8 ns of cable flight (ASSUMED). A per-link static draw of 0-3 ns is added on top.
  - RX clock-domain crossing into the receiver's own core clock, then 14 wire stages.
  - The credit return travels over the reverse latency.
- `ot_ha2_prims.sv`: delay lines, a variable PHY delay (simulation channel element) and a FIFO.
- `tb_ha2_ar.sv`: all N dies, each with its own core clock and PHY clock at random phases per seed, fully wired
  in both directions.
  - Every die checks every committed result flit against the golden image.
  - Latency is measured from the earliest issue on any die to the last result committed at the hub of the
    slowest die (the W15 rule).
- Floorplan stages are taken from `results/floorplan/hbm_gpu/v41_hbm_die.json` at 430 um a stage:
  - hub root to fabric-SerDes column: 14,713 um = 35 stages;
  - column centre to farthest port: 6,000 um = 14 stages.
- Golden: `tools/ha2_ar_fixture.py` uses `hdc_golden.add` (pairwise tree) and `to_bf16`, the W19 executor's
  `op_reduce`. The operands are a stress fixture with these cases:
  - whole-tree cancellations to +0;
  - subnormal sums;
  - exact BF16 ties.

## Shapes

| config | what |
|---|---|
| ds | DS-V4.1 TP-96 o-group all-reduce: 8 groups x 8 contributors x 1,024 FP32, BF16 out, multicast to all 96 dies |
| dsgather / dsgather512 | the same endpoint as a 96-rank all-gather (NC = 1) at 128 B and 512 B a rank (sensitivity) |
| qwen | Qwen3-8B TP-2 all-reduce over the in-package UCIe pair (W15 q256 width, 4,096 FP32, one-shot). UCIe-A PHY+adapter 2 ns (normative), FDI 0.4 ns clock, 37 hub stages (qwen_hbm_die tp_root_to_ucie 15,495 um) |

## Replay

The campaign ran on ot-agidock128 (EPYC admissions were frozen), from `~/claude-ha2ar` with copies of the sources
listed in `runs/input_sha256.txt`. Builds use Verilator 5.050 `--hierarchical`, with the shape set by
`+define+HA2_*` so that the endpoint and the link are compiled once.

    python3 tools/ha2_ar_fixture.py fx/<shape> --shape <shape>        # ds dsgather dsgather512 qwen
    campaign.sh   (copy in this directory)                             # 4 builds, 10 seeds each, ds PHY 114/170
    python3 tools/ha2_ar_campaign.py runs --out measured.json
    python3 tools/ha2_ar_compose.py --measured measured.json --out composition.json

The first Qwen build attempt hit a parallel-make PCH race (`build_qwen_attempt1.log`, exit 2). It was rebuilt
with make -j 1 (`qwen_retry.sh`), with the RTL unchanged.

The earlier flat (`-G` parameter override) DS build was OOM-killed at 128 GB on ot-pve1. That is why the build
moved to parameter-free hierarchical wrappers.

`codex_reducer_lzc_fix/` re-runs Codex's standalone reducer bench with the missing `ot_hdc_fastfp.sv`.
