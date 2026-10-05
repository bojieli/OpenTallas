# DS-V4.1 HBM accelerator at 1M with every critical-path term measured (2026-10-04)

**Result.** One decode token at position 1,048,575, TP-96, composed on the executed program's fixed serial order
(`tools/dshbm_1m_allmeasured.py`, `composition.json`). Base: the adopted measured accelerator rate of
`dshbm_local_chains_20261004` (2,313.0 AR), reproduced exactly before any term is replaced.

| | base (partial) | fully measured | at the clocks the blocks close today |
|---|---:|---:|---:|
| AR token | 432.33 us | **460.05 us** | 603.75 us |
| AR rate | 2,313.0 tok/s | **2,173.7 tok/s** | **1,656.3 tok/s** |
| MTP (DSpark block 5, verify P=6 + measured draft), tau 4.159 (owner 6-class blend, adopted 2026-10-05) | 5,225.8 | **4,683.2** | 3,675.7 |
| MTP sensitivity at the published V4.1 tau 3.8879 (range 3.43-4.32) | | 4,377.9 (3,862.3-4,861.6) | 3,436.1 |

The fully measured AR is 6.0 % slower than the base. Measured share of the AR token: **91.4 %** counting the labelled
Tomahawk vendor budget as measured-path (the DS-ROM convention), **66.3 %** without it.

**Notice is the default for the index-key scans and the window rows (owner >= 90 % bandwidth rule, 2026-10-04).**
As built (descriptor at the query, no notice) the scans reached 0.617 (L20) / 0.506 (L2) and the window 0.198 of peak
steady at the worst of 64 refresh phases. The program is static, so the stream PC's existing `notice` input is driven
ahead of every scan and window descriptor (the R5a mechanism; no new logic). Re-run with the independent per-PC DRAM
checker `rtl/test/ot_hbm_pc_dram_check.sv` bound into every PC (`tools/dshbm_1m_hbm.py run --chk`, 1,280 runs x 32 PCs,
0 violations, every sector exact, negative controls FAIL; `notice_default/runs_pcchk.json.gz`): scans 1.000 / 1.000,
window 1.000 of peak steady at the worst phase (complete 225.6 / 132.4 / 57.7 ns). HBM term 13.68 -> 10.76 us; AR
2,156.0 -> 2,173.7 tok/s (+0.82 %). Token-dependent loads (CKV gather, embedding) stay as built; notice on every load
is the `hbm_loads_with_notice` sensitivity, and the old default is `hbm_loads_as_built_no_notice`.

**What replaced the model (all bit-exact where data-dependent).**

| term | base | measured | record |
|---|---:|---:|---|
| collectives (265 on path) | 199.17 us TU model | 167.26 us endpoint RTL + labelled budget, + 39.75 us striping tail (model) | `collectives.json`: new default-off `rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint.sv` (HA2 hub/reducer/primitives, 8 striped switch ports), one die in RTL against a labelled TU stub (PHY 100 + switch 250 + cable 27.6 ns a crossing), 184 runs exact |
| FP8/FP4 quantisers | 6.53 us (40.6 ns node) | 19.19 us | `local.json`: `ot_hdc_actquant` 173 cycles per 5,120 values, q + kv-row QDQ 53 + 29 (one instance) |
| DU steps (index q/scores, selects, candidates, Engram mix, router top-6) | 7.01 us | 9.58 us | `local.json`: real operands of L1/L2/L20/L24 (executor `--exec-layers`), selects charged by their tail after the last score (the DS-ROM convention) |
| HBM loads | 5.32 us (fetch model) | 10.76 us | `hbm_streams.json`: stream PC (notice on scans + window), worst of 64 refresh phases, corrected REFpb: window 131 ns x 40, index keys 223 / 340 ns (bind over the array's ingest), CKV source rows (golden worst stack, 2 / 7-row cases), embedding 317 ns, routed fetch 130 ns |
| hc_mixes | 0 (off-path by assumption) | 0 exposed | HCP `spec_w256` 328 cycles (K 20,480) + SU pre/post + Sinkhorn 0.693 us = 0.97 us beside every sublayer body (body 4.39-11.53 us, 80 sublayers) |

SM matvecs (70.12 us), the barrier (22.30), SU chains (93.61), the attention tile (19.67), SwiGLU and the 96 x 512
select were already RTL-measured and are unchanged. The SM weight stream never stalls the SMs in steady decode
(HBM fork: demand 2.0-2.7 TB/s per layer type against 3.85 sustained).

**Still not RTL (listed in `still_modelled_ar` / `still_modelled_other`).**
- Tomahawk-Ultra PHY + switch + cable: 115.17 us of the AR token, labelled VENDOR BUDGET.
- Striping tail 0.15 us per collective (39.75 us): the RTL stripes over 8 equal-latency ports, so inter-chip skew is
  not captured.
- MTP: routed-expert union increments (+47.74 SM / +28.45 fetch us, W19 composer), LOCAL_REPEAT issue fraction,
  the DSpark draft record (its collectives are the TU model), seed commit; tau is the owner 6-class workload blend 4.159 (owner decision 2026-10-05; the published 3.8879 is the sensitivity in `tau_sensitivity`).
- HBM path constants inside the stream bench (PHY cmd 5, rsp 10, NoC 5 ns); the CKV stack mapping (i // 8 // 96) % 4.

**Sensitivities.** Notice on every HBM load (adds CKV gather + embedding): 2,183.8 tok/s; no notice anywhere (the superseded default): 2,156.0 tok/s. Port-matched endpoint hub
(8 in / 10 out flits a cycle): 2,225.5 tok/s.

**Clocks today** (`at_closing_clocks.clocks`): SM element 1,030.9 MHz (issue output ports -136.7 ps; tc_col, stack
and tc16 also miss; the whole SM element was never routed), SU 638.6 MHz (light-lane screen), attention tile 881 MHz
(fastfp multiplier), collective endpoint clk_sm 394.5 MHz (baseline endpoint in context, SS -1.70 ns on RX CDC ->
asmb), router top-6 621.5 MHz, HBM stream PC 1,209.6 MHz (closes). The new TU endpoint has no area, route or STA:
its 394.5 MHz is the as-built endpoint's, not a measurement of the new one.

**N2048 lanes option: REJECT.** Measured with the wire stages it really needs (BCAST 6 / RET 6 from the
`uarch_model.wire_cycles` rule that gives N1024's 4/5; `su_n2048/wire_stages.json`), 38 + 38 chains exact. AR
2,146.9 tok/s (-0.42 %: the extra stages cost more than the wider lanes save at P = 1); MTP 4,434.4 (+1.72 %). Not
adopted: AR regresses, and the wider array has no area, route or SS/FF evidence.

**Replay.**
```
python3 tools/dshbm_1m_coll.py fixtures|campaign|record DIR          # collectives.json (ot-agidock128)
python3 tools/dshbm_1m_hbm.py ...                                    # hbm_streams.json (ot-agidock128)
HDC_V41_ARITH=chunk8 python3 tools/dshbm_baseline_measure.py execute --exec-layers 1,2,20,24 --out DIR   # operands
python3 tools/dshbm_1m_local.py select|idx|quant|su-prep|record ...  # local.json
python3 tools/dshbm_1m_allmeasured.py                                # composition.json
```
