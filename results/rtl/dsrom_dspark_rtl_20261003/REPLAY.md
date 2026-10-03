# DSpark MTP in RTL on the V4.1 decode core (reduced vehicle)

Branch `claude/dsrom-dspark-rtl-20261003`. Owner decision 2026-09-29: the V4.1 ROM design runs MTP with m = 1,
**time-multiplexed** on the existing element array (no lane copies). Every result here is functional RTL simulation
under Verilator on the reduced DeepSeek-V4.1-Flash vehicle (`build/models/deepseek-v4.1-flash-reduced-v2`:
40 layers, dim 160, window 128, DSpark block 5, 3 draft stages over target layers 37-39, 4 experts top-3 in the
draft MoE). The DSpark weights of the reduced vehicle are seeded random, so its acceptance (always 0) is a
functional check only. The `forced` drafter (golden continuation, one draft corrupted per step) exercises nonzero
accept lengths. No clock rate is claimed.

## Inventory (what existed, what this branch adds)

| Piece | Where | State before | This branch |
|---|---|---|---|
| DSpark golden (draft, `generate_spec`, layer-major `forward_positions`, rollback by truncation) | `tools/hdc_golden_v41.py` | bit-exact vs non-speculative greedy (328b5fff) | reused |
| ISA: slots (`dslot`), DYN banks, CTL TOKX / AMAX / DYN / ACCEPT | `tools/hdc_isa_v41.py`, `rtl/hdc/v41/ot_hdc_isa_v41.svh` | done | reused |
| Programs: STEP (prefill + DSpark row seeding) and ITER (draft, DYN, verify of gamma+1 slots, ACCEPT) | `tools/hdc_program_v41.py build_mtp` | ISA bit-exact | reused, m = 1 |
| Draft pass RTL: 3 DSpark stages (window attention over the seeded rows, top-3 MoE), Markov head, one SELECT per draft, TOKX | program on the core's existing ME / SU / QE / XU / HE | written 93bd43b5, never simulated to completion | **simulated bit-exact** |
| 6-position verify (slots merged op-major, issued one slot after another: m = 1) | core sequencer slots, per-slot DYN banks | same | **simulated bit-exact** |
| Accept / rollback | `rtl/hdc/ot_hdc_accept.sv` (default) or Codex's protected leaf `rtl/experimental/ds_mtp_accept_20261003/ot_hdc_mtp_accept_guarded.sv` via the new `rtl/hdc/ot_hdc_mtp_accept_caller.sv` (`ACC_GUARD = 1`) | leaf standalone only | **leaf wired into the core**, default-off |
| KV commit / rollback | dead-row invariant: rejected slots' KV, compressor-ring and index-key rows are never read before the committed position rewrites them; Engram hash history restored to slot a's snapshot (XU) | same | checked: final KV SRAM incl. dead rows equals the ISA model's; restore mutant detected |
| Expert union | not needed at m = 1: each verify slot runs its own top-k experts on its own issue (ROM experts are stationary; the union saves no bytes) | - | - |
| Re-specified core (`ot_hdc_core_v41x`) MTP bench | `rtl/test/tb_hdc_core_v41x_mtp.sv`, `tools/rtl_hdc_dspark_v41x_campaign.py` | none | new |
| Integration point in the V4.1 ROM program | ITER program at `entry` of the same image; `start` with `entry != 0` runs one speculative step; `acc_n` / `acc_tok` / `next_token` are the step's output; host advances pos by `acc_n` | - | - |

## Replay

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
