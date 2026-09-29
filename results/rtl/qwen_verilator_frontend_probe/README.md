# Qwen O4 Verilator front-end probe (2026-09-28)

These source-pinned records measure **Verilator 5.050 front-end resource use** for
the frozen real-layer0 source set on `ot-pve2`. They do not build a full-shape
simulation, run a token, establish throughput, or validate physical timing.
The hierarchy control file selects only `ot_hdc_fmul` and `ot_hdc_qadd` as
compilation boundaries; it makes no RTL arithmetic change.

| Probe | Front-end result | Wall time | Child maximum RSS |
| --- | ---: | ---: | ---: |
| G64 matvec, flat, high unroll, `--cc` | exit 0 | 379.798 s | 11,909,380 KiB |
| G64 matvec, leaf hierarchy, high unroll, `--cc` | exit 0 | 91.936 s | 1,456,628 KiB |
| G512 matvec, leaf hierarchy, high unroll, `--cc` | exit 0 | 951.141 s | 19,593,280 KiB |
| G64 matvec, flat, low unroll, `--lint-only` | exit 0 | 307.357 s | 11,646,656 KiB |
| G64 core, flat, low unroll, `--lint-only` | cgroup exit 137 | 97.998 s | 12,547,016 KiB |
| G64 full layer0 top, flat, low unroll, `--lint-only` | cgroup exit 137 | 283.670 s | 12,541,096 KiB |

The matched G64 `--cc` source hashes, Verilator version and non-hierarchy
flags agree. Leaf hierarchy cut front-end wall time by 4.13 times and peak RSS
by 8.18 times at this size. G512 uses 13.45 times the G64 hierarchical peak
RSS for eight times as many groups. Thus these results do not establish that
a G6144 elaboration will fit any available host. The exit-137 probes were
under separate 12 GiB memory caps; their maximum RSS is close to the cap.

The JSON files contain exact commands, tool versions, source hashes, stable
source checks and log hashes. The runner is
`tools/qwen_verilator_frontend_probe.py`; hierarchy is selected by
`tools/qwen_verilator_leaf_hierarchy.vlt`.

## Reduced exact hierarchy replay

`reduced-hier-8561-exact.json` records a separate compiled reduced G4 TP-2
replay. It used all 27 matching RTL/harness/ISA source hashes from the earlier
passing `8561a033` campaign and all 21 identical image hashes. The six
original campaign generator/quality-tool pins are outside this compiled
replay's source list; its frozen images preserve their generated values.
Verilator 5.050 with the leaf hierarchy compiled the design and replayed all
18 checked steps: generated tokens 1073, 382, 93; zero token, logit, KV and VM
mismatches; 317,329 cycles, identical to the original flat reduced record.
The first remote simulation lacked copied die image subdirectories and was
discarded. The `--reuse-build --adopt-sim-log` mode pins the corrected binary
and successful replay log; its 0.002-second `wall_seconds` is only the record
adoption time, not compilation or simulation runtime. This proves reduced
arithmetic equivalence of the hierarchy setting, not real G6144 layer0
exactness or a full-model result.

`reduced-flat-current.json` and `reduced-hier-current.json` are the matched
comparison on the later frozen comparator source. Their 27 compiled source
hashes, all 21 input image hashes and Verilator version match. Both builds
replayed the same 18 steps and 317,329 cycles with zero token, logit, KV or VM
mismatches. The hierarchical current-source binary was also first simulated
before the remote die image subdirectories finished copying; that invalid
attempt produced mismatches and was discarded. These records pin only the
corrected replays and their binaries. Their `wall_seconds` values likewise
measure record adoption after completed compilation and simulation.

## Experimental group and reduction bank cuts

The unmerged `ot_hdc_matvec_mac_group` cut keeps all logical W16 lanes and
reuses a compiled 16-lane group. Its G4 reduced exact gate passed with the
same 18 steps and 317,329 cycles. At G512, its front-end used 18,755,092 KiB
and 907.850 s, versus 19,593,280 KiB and 951.141 s for the leaf-only cut:
only 4.3% less peak RSS and 4.6% less wall time.

The following experimental `ot_hdc_matvec_reduce_bank` cut keeps every
pairwise FP32 add in the same order, the same valid/select controls and the
same three-cycle held path plus one output register. At G6144/W16, the
proposed geometry has 96 banks of 64 groups per level, 13 levels, 1,248 bank
instances, 98,272 qadd lanes and a still-flat 3,145,728-bit parent level
bus. Each bank has a 32,768-bit held/output bus and up to two 32,768-bit pair
inputs. Non-power-of-two G6144 pair counts are exact: levels 6 and 7 have
partial banks of 32 and 48 active groups; level 13 has no add groups.

This banked version passed the G4 reduced 18-step gate and an independent
pre-refactor versus candidate G4 complete-matvec split sweep. G64 front-end
finished at 108.524 s / 1,582,936 KiB, worse than the group-only cut at that
size. G512 compilation exceeded its separate 12 GiB cap: the hierarchical
Verilator child received signal 9 after 293.859 s, with 12,497,484 KiB child
maximum RSS. The preset <8 GiB acceptance target was missed. The banked
cut remains experimental and does not support a G6144 compilation claim.
The independent G64 W16 cycle-by-cycle split sweep was still running when
this negative resource result was recorded; no G64 equivalence pass is
claimed here.

Integration note (claude/w0-codex-reconcile): the group/bank hierarchy refactor
of `rtl/hdc/ot_hdc_matvec.sv` from Codex commit `a80d6a30` is NOT applied to
production RTL. Its source is preserved verbatim as
`results/rtl/qwen_matvec_bank_equivalence/ot_hdc_matvec_hier_experiment.sv.txt`
for replay; the records above are historical (G4 exact, G512 Verilator above
12 GiB). `tools/rtl_hdc_matvec_bank_equiv.py` expects that variant in place of
the production module.
