# Token exactness on the current structure (stream token-exact, 2026-10-09)

Source under test: main 54268eb16 + the harness fixes of this stream (4dc3e0062). Runs on ot-epyc1tb
`/srv/opentallas-scratch/claude/token-exact/runs/4dc3e0062` (Verilator 5.050), exactness harness runs on
`/srv/opentallas-scratch/claude/exactness/runs/4dc3e0062780`. Method: the minimum-component rule. Each mechanism is
proven on the smallest vehicle that contains it, and the layer and token verdicts are composed from those proofs.
Each component boundary is checked at the transaction level: data, order and faults must be exact, while latency
may change.

Legend: **exact** = bit-exact against the golden, with the negative controls failing as required. **mismatch** = an
RTL result differs from the golden. **not run** = no measurement (the reason is given). **blocked** = the vehicle
exists but a fixture or host is missing.

## Verdicts at target context

| Target | Layer verdict (RTL, current structure) | Token composition |
|---|---|---|
| Qwen3-8B ROM (TP4 ROM die + KV die), P8191 | **exact.** Three chained layers L0-L2 on the split partition (sequencer / tree top / SU across the die-master boundary, DCU=DUC=2 stations, split compensation, SU lane ML 7): 12/12 layer X and 12/12 current-K/V writes bit-exact, write-back drained. The LM head on the same split core is exact (token and winning logit on all 4 ranks, all 4 normalised head inputs). Every new mechanism outside that vehicle is exact on its own bench. | L0 + 35 x the L1 layer + the head, all measured: **201,041 cycles** (see Composition). |
| HBM generic die: Qwen TP4 INT8 + DS | **exact in the simulator** (HGI-1 records on r25: Qwen full token at P8191, DS full 1M token). **RTL:** exact on the main-line vehicles (Qwen TP2 L0, DS SM PQ/XMAP joint P1+P6). Exact on the fork block benches, with DS / legacy lockstep against the pre-fork RTL. | No r25 RTL layer bench exists yet: the forks are not on main and the R25G die is not assembled. |
| DS-V4.1 ROM (S81), P1,048,575 | **exact.** L20 (ratio-1 + compressor + indexer layer): 24 field phases x 2,864 region runs in RTL, 26 field ops / 34,880 rows chained through the VM, the chain VM equal to the golden after all 143 ops, final VM 450,479 words equal, the selector exact on the 1M golden scores. The mutant is detected. BF, coll_core and Engram are exact on their own benches. | The 117 non-field ops are golden-composed: their inputs are proven bit-identical at every op boundary. |

## Matrix (component x target)

### (a) Qwen3-8B ROM: TP4 ROM die + KV die, P8191

| Component | Verdict | Evidence |
|---|---|---|
| Base die (harness STREAM4 plain AR, same tree), L0-L2 chain | exact (16,617 cycles; L0 6,044 / L1 5,282 / L2 5,282 = the published per-layer cycles) | `qwen_rom/L3_base.json`, `L3_base_stages.txt` |
| Split partition + latency compensation (DCU=DUC=2, COMP=1) + SU lane ML 7 (bv SU master: VM answers + far constant ROM), **current** | exact (17,120 cycles; L0 6,151 / L1 5,480 / L2 5,480; +198 cycles per layer vs base) | `qwen_rom/L3_s22ml7.json`, `STN_s22ml7.json` |
| Same with ML 4 (the rtl-finish point) | exact (17,000; L1 5,432) | `qwen_rom/L3_s22ml4.json` |
| Negative: stations without compensation (COMP=0, ML 7) | FAIL as required (49,152 X words + 6,046 K/V codes differ) | `qwen_rom/L3_s22ml7neg.json` |
| Banked VM (128 macros, bv ports, NRB64/SW64) | exact: vm_ports s5/s9/big PASS; mut/xmut FAIL | `qwen_comp/STATUS.txt` |
| SU replica copies on the banked VM (su_vm_bv, IS/OS 1 and 2) | exact: su_vm_exact / su_vm_s2 PASS; mut/vmut FAIL. The qwen-system "pre-existing FAIL" was Verilator 5.032; under the pinned 5.050 it passes | `qwen_comp/STATUS.txt` |
| ME result path (band serializer + 6:1 merge + landed tree top) | exact: res_ports_s3, landed_exact PASS; smut FAIL | `qwen_comp/STATUS.txt` |
| Band lanes (levels 8-10, 16 lanes, LNK 0/2) | exact: band_exact_nl16 / lnk2 PASS; mut_order / mut_upper FAIL | `qwen_comp/STATUS.txt` |
| Split spine end to end (BANDF slab ports, LNK1/CLNK2, die geometry GT 6,144, splits 7-11) | exact: sb_exact / sb_link / sb_qwen PASS; 4 mutants FAIL | `qwen_comp/STATUS.txt` |
| Q / new-K / V -> KV die -> attention result crossing, **with the KV4 write-then-read fence** (kv-die 224d19c30, STACK d) | exact: 14/14 base runs (7 vectors incl. ctx 8192 normal/peaky, 8191, 4097, 2048, 129, 1; stall 0/1) at best / typical / worst PHY latency (8192 layer step 1,827 / 1,829 / 1,841 cycles); mutants 1-5 and 7 FAIL; base-RTL controls 6 (TIGHT) and 8 (fence stall 400) exact. Measured by the kv-die stream (run11), harvested here | `kv_die/run11_results.jsonl.txt` |
| Embedding from HBM (boot load, gateway, PC strip, far bus, SU landing) | exact: base_kv0/1/2 + twin_kv1/2 PASS (mean fill latency 459-488 cycles); mut_row / mut_scale / mut_ecc / mut_gate FAIL; 160-token image | `qwen_comp/emb_hbm_run.json` |
| Head (LM head + argmax) on the split core (s22ml7), head alone with the CPU gold's L35 output as its input | exact: token 24 / logit 0x41962749 on all 4 ranks, 4/4 head Xnorm digests; 3,048 stage cycles (base die: 2,999, also exact) | `heads/qwen_rom_head_s22ml7.json`, `heads/qwen_rom_head_base.json` |
| Collective tags at full shape (one stage program per start: tags repeat across the 36 layer stages) | exact (fixed, reviewed 2026-10-09): `ot_qwen_tp_seq_w12_fs` (instantiated by `ot_qfd_sp_constants_sequencer_sys`) tags `{gen, stage, pos[12:0], token[7:0], seg[2:0]}`; bench with two AR segments a stage, 38 stages x P 5/261/517/8191: 0 collisions (base 28,576); stage / pos8 / seg collision mutants FAIL | `results/rtl/qwen_system_20261008/tag/review_20261009/`, `physical/sys_takeover/seq_tag_bench.sh` |

### (b) HBM generic die

| Component | Qwen TP4 INT8 | DS-V4.1 | Evidence |
|---|---|---|---|
| HGI-1 simulator vs golden (released weights) | exact: full token at P8191 (embedding 4/4, 144/144 layer, head 4/4, argmax; token 119419); L0 16 families | exact: full 1M token in native HGI unit ops on 96 dies (token 21946, logits digest), TP-96 round trip 40L+head | `results/arch/hgi_sim_20261009/qwen_token_P8191.json` (collected here), `qwen_L0_P8191.json`, `ds_native_1M_token.json` |
| Main-line RTL layer vehicle | exact: hbm_qwen_L0 (TP2 w160, P8191) 6,399 cycles = expected, X byte-equal | exact: hbm_ds_joint_p1 (SM PQ/XMAP, 4 P1 + 4 P6 fixtures) 4,048 cycles = expected; FP4 negative refused | exactness.log rows 2026-10-09 08:16 PT (4dc3e0062780) |
| Fork: cmdproc + config path (CF-0 20 cases, CF-1 300-job lockstep vs ot_hfd_cmdproc20_m) | exact | exact (lockstep) | `hbm_forks/STATUS_27237d9c6.txt`; MUT_CRC / RANGE / SETTLE FAIL |
| Fork: record sequencer ot_hgi_seq (36 cases) | exact | exact | same; MUT_WAIT / MUT_LOOP FAIL |
| Fork: collective group sizes (ot_hbm_accel_tu_endpoint_psg) | exact: n = 2/4/8 | exact: legacy CF-1 set (62 runs) | `hbm_forks/STATUS_fa2b6fdb2.txt`; 4 pad negatives caught |
| Fork: attention half tile with the ldk strap | exact: ldk 1 | exact: CF-1 roles 0-4 lockstep, ldk 0 | same; LDK mutant FAIL |
| r25 Qwen TP4 INT8 RTL layer / token bench | not run: no bench exists until the forks land and R25G is assembled (hbm-forks, Codex die integration) | not run (same) | - |
| HBM-Qwen LM head (TP2 w224 head bench) on the CPU TP2 gold | exact: token 24, logit 0x416f3349 = gold, 4,641 cycles (= the harness's expected head cycles) | - | `heads/hbm_qwen_head_token_result.json` |

### (c) DS-V4.1 ROM (S81), P1,048,575

| Component | Verdict | Evidence |
|---|---|---|
| L20 one-layer token bench (field vehicle q element QX 10, 1,792 HALF-dedicated + router K-split binding sha-checked; every phase x region in RTL; VM chain to the golden layer output) | exact; RTL-row bit-flip mutant detected (chain_ok false, 1 final word) | `s81/token_bench.json`, `s81/token_bench_mutant.json` |
| Selector (ot_hdc_v41x_sel Q4/W16/IW20/K512, the dsfd_bk_selector core) on the 1,048,576 golden index scores | exact (16,491 cycles) | `s81/select.json` |
| BF element, every candidate variant (the decision is due 21:30 PT) | exact at the transaction level: full-rate RECUT 2 QZE=1 (mutants dp / recut / ze / z detected), CG=0, RECUT 2 plain; HALF_PHL. The BF sources are unchanged on main since those runs (only `ot_dsrom_head_bundle.sv` moved, opt-in) | `results/rtl/s81_bf_icg_20261008/exact_gate_recovered/`, `results/rtl/s81_bf_native_20261008/safe_s81_b1/{halfphl,recut2}/terminal.json` |
| coll_core OQPIPE with the (* keep *) push replicas (54e3f8f9c, attribute only) | exact: TB_S81PH_COLL_SYS PASS (4-die TP4 group vs four C8 engines); MUT_OQPIPE_SLICE and MUT_NOREORDER FAIL | `coll/markers.txt`, `coll/STATUS.txt` |
| Engram from HBM (home-die HBM tables) | exact on the Codex engram stream's gates (HBM backend, row-stripe read, canonical read, prefetch macro, lead): all `status: pass` | `results/rtl/engram_*_gate_20261009.json` |

## Harness fixes made by this stream (4dc3e0062)

- `tools/exactness/qwen_rom_fulltoken.py` gains a mode `L3`: a 3-layer chain at P8191 with current-K/V checks. The host gains `--stop-after S`, which drains the posted write-back and reads back K/V for stages 0..S. The gold falls back to the realmem-ctx8k P8191 gold, verified file by file against the committed oracle digests (`qwen_rom/fixture_manifest.json`). An IndexError on an empty head result is fixed.
- `tools/qwen_hbmacc_rt_token_w12.py`: the oracle record is now looked up one level up, and layer-only runs need none. The 10-08 hbm_qwen_L0 "FAIL" was this lookup, not the RTL.
- `tools/s81/token_bench_l20.py`: `--jobs` is passed as a string. The 10-08 run had died before the field runs.

## Composition (pathfinding)

On the split, the Qwen ROM token is measured as 6,151 cycles for L0, 5,480 for each later layer and 3,048 for the head. That is +107, +198 and +49 cycles against the base die measured on the same tree (6,044 / 5,282 / 2,999, the published per-stage cycles). Composed: 193,955 + 107 + 35 x 198 + 49 = **201,041 cycles**, +3.65 % per token from the split stations, the compensation and the SU ML 7. The KV-die crossing adds the kv-die stream's own +8 cycles a layer for the fence (CONTRACT v1.1). That stream prices it; it is not composed here.


## 36-layer golds regenerated on CPU (owner decision 2026-10-09: no GPU reset)

- **Tool.** `tools/qwen_hbmacc_position_oracle_gpu.py --device cpu` runs the same torch golden: the r21/split TP4 and the TP2 summation orders, chunked K-split, rank-order fold, and the chunked running argmax head. It runs on ot-epyc1tb in a uv venv (torch 2.14 + numpy 2.5.3, 32 threads). The primitive self-test passed bit for bit against `hdc_golden` before use.
- **History seeding.** `--kv-history` seeds every layer's K/V store and decodes only position 8191. measure-at-target-context allows a format-valid synthetic history, because a layer is a pure function of its inputs. L0-L2 use the real prompt history (the committed pin). L3-L35 reuse L0's history. The RTL runs used the same history files.
- **Cross-check of the CPU path.** The CPU gold reproduces the committed real-prompt digests for every L0-L2 layer X, kv_pre and kv_at_P, and for the x preload. This holds for TP4 against the committed oracle and for TP2 against the verified tp2_l3 gold (`heads/STATUS_HEADS.txt`).
- **Records.** `heads/cpu_gold_{tp4,tp2}_oracle.json`: next token 24, TP4 logit 0x41962749, TP2 logit 0x416f3349. Each gold took 17-18 min wall time and 12-13 GB RSS.
- **Why not the full real-prompt prefill.** On CPU it costs 1,016 s per position for 36 layers plus the head. That is about 96 days for 8,192 positions, so it is not feasible. The committed real-prompt digests remain the reference for L0-L2.
- **Restored HBM-Qwen head images.** The TP2 W12 stage images (`hbm-accel-qwen-token/w12`) were swept from scratch-overflow on 10-09. The head images were rebuilt from the pinned prep npz with `tools/exactness/w12_head_restore.py`. All three files per die are sha256-equal to the pins, so they are byte-identical restorations. The head program and segments came from `w12_head_stage.py` + `qwen_rom_program_sw.py`; the identical procedure reproduces the surviving TP4 head program and segments byte for byte. The 72 layer images (L0-L35 x 2 dies) were then restored the same way by `tools/exactness/w12_layer_restore.py`. It replays the emitter with the npz matrices, and takes the program and segments verbatim from the prep's recorded words. All 5 files of every image are sha256-equal to the pins (`heads/w12_tp2_layer_restore.jsonl`). On the restored images, hbm_qwen_L0 is again exact: 6,399 cycles, the expected count, with layer X equal on both dies (exactness.log, run d39293f56cbd).

## Fixture protection

Every exactness fixture tree now carries a `.keep` marker, placed by `tools/exactness/keep_fixtures.sh` on ot-epyc1tb, ot-epyc2 and ot-epyc3. Three cleaners honour it:
- the 48 h sweep (`gaps/dir48.sh`) skips a root that holds a `.keep` anywhere within depth 4;
- `tools/fleet/sweep.py` treats a `.keep` the way it treats a `STATUS.md`;
- the closure-loop deep release skips a run root that holds a `.keep` and hard-protects every `.keep` subtree. The triage stream redeploys the daemon (drive-0849.log).
