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
