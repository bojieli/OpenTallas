# DSpark MTP in RTL on the V4.1 decode core (reduced vehicle)

Branch `claude/dsrom-dspark-rtl-20261003`. Owner decision 2026-09-29: the V4.1 ROM design runs MTP with m = 1,
**time-multiplexed** on the existing element array (no lane copies). Every result here is functional RTL simulation
under Verilator on the reduced DeepSeek-V4.1-Flash vehicle (`build/models/deepseek-v4.1-flash-reduced-v2`:
40 layers, dim 160, window 128, DSpark block 5, 3 draft stages over target layers 37-39, 4 experts top-3 in the
draft MoE). The DSpark weights of the reduced vehicle are seeded random, so its acceptance (always 0) is a
functional check only. The `forced` drafter (golden continuation, one draft corrupted per step) exercises nonzero
accept lengths. No clock rate is claimed.

Runnable additive export: branch `codex/dsrom-dspark-runnable-export-20261003`,
based on main `585f8e09e76ecba06ceedbda496cc5b8ee32136b`. The export supplies the
missing source files from `2f20d5161` and `e694ceec5` together with the final
`1f94c92b8` / `77280a0a3` implementation. The MTP core is an exact copy of
`2f20d5161:rtl/hdc/v41x/ot_hdc_core_v41x.sv` at the new path
`rtl/hdc/v41x/dspark/ot_hdc_core_v41x.sv`; its only difference from the current
main core is that commit's default-off ACC_GUARD delta. The DSpark campaign
selects this same-module source in place of the shared core. The shared core,
shared decode campaign and all other existing main paths stay byte-identical.
This export does not change the live wave-1 or cached-run source pins.

## Inventory (what existed, what this branch adds)

| Piece | Where | State before | This branch |
|---|---|---|---|
| DSpark golden (draft, `generate_spec`, layer-major `forward_positions`, rollback by truncation) | `tools/hdc_golden_v41.py` | bit-exact vs non-speculative greedy (328b5fff) | reused |
| ISA: slots (`dslot`), DYN banks, CTL TOKX / AMAX / DYN / ACCEPT | `tools/hdc_isa_v41.py`, `rtl/hdc/v41/ot_hdc_isa_v41.svh` | done | reused |
| Programs: STEP (prefill + DSpark row seeding) and ITER (draft, DYN, verify of gamma+1 slots, ACCEPT) | `tools/hdc_program_v41.py build_mtp` | ISA bit-exact | reused, m = 1 |
| Draft pass RTL: 3 DSpark stages (window attention over the seeded rows, top-3 MoE), Markov head, one SELECT per draft, TOKX | program on the core's existing ME / SU / QE / XU / HE | written 93bd43b5, never simulated to completion | actual RTL campaign running; terminal exactness pending |
| 6-position verify (slots merged op-major, issued one slot after another: m = 1) | core sequencer slots, per-slot DYN banks | same | actual RTL campaign running; terminal exactness pending |
| Accept / rollback | `rtl/hdc/ot_hdc_accept.sv` (default) or Codex's protected leaf `rtl/experimental/ds_mtp_accept_20261003/ot_hdc_mtp_accept_guarded.sv` via the new `rtl/hdc/ot_hdc_mtp_accept_caller.sv` (`ACC_GUARD = 1`) | leaf standalone only | **leaf wired into the core**, default-off |
| KV commit / rollback | dead-row invariant: rejected slots' KV, compressor-ring and index-key rows are never read before the committed position rewrites them; Engram hash history restored to slot a's snapshot (XU) | same | final KV including dead rows and restore mutation are checked by the running campaign; terminal verdict pending |
| Expert union | not needed at m = 1: each verify slot runs its own top-k experts on its own issue (ROM experts are stationary; the union saves no bytes) | - | - |
| Re-specified core (`ot_hdc_core_v41x`) MTP bench | `rtl/test/tb_hdc_core_v41x_mtp.sv`, `tools/rtl_hdc_dspark_v41x_campaign.py` | none | new |
| Integration point in the V4.1 ROM program | ITER program at `entry` of the same image; `start` with `entry != 0` runs one speculative step; `acc_n` / `acc_tok` / `next_token` are the step's output; host advances pos by `acc_n` | - | - |

## Replay

The historical image-generation commands below call the NumPy golden. They must
not be launched on CPU hosts under the current GPU-only policy. Gamma sweeps,
longer guard images and plain baseline generation remain held until Claude provides
the exact local GPU golden path. Existing wave-1 RTL simulations keep running.

From a checkout of the branch with `build/models/deepseek-v4.1-flash-reduced-v2` and
`results/abi3/deepseek_v41_reduced_v2_reference_oracle_fp8.json` present (Python needs numpy and tokenizers):

```
export OT_SCRATCH=/scratch/dir
# as-built core (ot_hdc_core_v41, NSLOT 8, MP 1)
python3 tools/rtl_hdc_v41_mtp_campaign.py --part rom_m1_g5_gold4 --gamma 5 --ngen 12 --prompts gold4 --mutate --isa-checks --output parts/rom_m1_g5_gold4.json
python3 tools/rtl_hdc_v41_mtp_campaign.py --part rom_m1_g5_o8s6 --gamma 5 --ngen 12 --prompts oracle8,spread6 --output parts/rom_m1_g5_o8s6.json
python3 tools/rtl_hdc_v41_mtp_campaign.py --plain --part rom_m1_plain --ngen 12 --prompts gold4,oracle8 --output parts/rom_m1_plain.json
# re-specified core (ot_hdc_core_v41x, he,me re-specified units), ot_hdc_accept / protected leaf
python3 tools/rtl_hdc_dspark_v41x_campaign.py --part x_heme --units he,me --mutate --gamma 5 --ngen 12 --prompts gold4,oracle8,spread6 --output parts/x_heme.json
python3 tools/rtl_hdc_dspark_v41x_campaign.py --part x_heme_guard --units he,me --acc-guard --mutate --gamma 5 --ngen 12 --prompts gold4,oracle8,spread6 --output parts/x_heme_guard.json
# gamma sweep, longer run, six re-specified units
python3 tools/rtl_hdc_dspark_v41x_campaign.py --part x_heme_g3 --units he,me --gamma 3 --ngen 12 --prompts gold4,oracle8 --output parts/x_heme_g3.json
python3 tools/rtl_hdc_dspark_v41x_campaign.py --part x_heme_g1 --units he,me --gamma 1 --ngen 8 --prompts gold4 --output parts/x_heme_g1.json
python3 tools/rtl_hdc_dspark_v41x_campaign.py --part x_all6 --units he,me,att,sel,eg,su --gamma 5 --ngen 12 --prompts gold4 --output parts/x_all6.json
# caller unit bench (seconds)
python3 -m pytest -q -o addopts='' tests/test_hdc_mtp_accept_caller.py
# summary
python3 tools/dsrom_dspark_rtl_record.py
```

Each part record carries `input_sha256` of every RTL source, bench and tool it used.
Runs were executed on ot-epyc1tb (`/srv/opentallas-scratch/claude/dsrom-dspark`, rsync of the branch).

For the queued all-six DPI campaign, use the successor runner with the two existing
`wd/i_gold4_{dspark,forced}_g5_n12_attheidxmesu` images, without inference:

```
python3 tools/dsrom_dspark_cached_rtl.py --part x_all6dpi --fp dpi \
  --image /srv/opentallas-scratch/claude/dsrom-dspark/wd/i_gold4_dspark_g5_n12_attheidxmesu \
  --image /srv/opentallas-scratch/claude/dsrom-dspark/wd/i_gold4_forced_g5_n12_attheidxmesu \
  --run-dir /scratch/new-unique-run --jobs 16
```

Its `part.json` records active PID and becomes terminal only when all runs finish;
each `runN.log` is distinct, line-buffered and retained with the C++ build objects.
The source and image hashes travel with the terminal record. A crash, fault,
missing summary or mismatch cannot pass. No new SS/FF or full-system claim is made.
The summary requires all ten original parts and returns 2 for incomplete campaigns;
use a new `--output` path on each collection to retain earlier failed verdicts.
