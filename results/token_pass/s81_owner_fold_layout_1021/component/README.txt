Required minimum operand-assembly proof: PASS_SOURCE_COMPONENT, epyc9 unit3705667-1792616681 exit0 (automatic unpinned spill; results copied back to gold1).

Replay from a source root containing the exact source hashes in result.json:
  python3 tools/s81_dv/owner_pair_1021/gate.py --out NEW_ABSOLUTE_OUTPUT_DIRECTORY
Optional --reuse-build PRIOR_OUTPUT_DIRECTORY first matches all RTL/physical source hashes, copies its objects, then reruns the frontend for the actual selected bench. It never mutates the prior run.

Real path:30 native line CTL commands =8 target5 component-input writes +8 localRD cfg/RDOUT pairs +6 VS11 commands. XRT/RSTOPT, actual DL4 down/up relays, production VP banked SRAM and VS adders execute every copy/add. No intermediate arithmetic result or collective output is injected. Eight final FP32 values match independent canonical ((p0+p1)+(p2+p3)); positive bad0, all rf/xf/pf/sf0. One altered odd destination fails with bad1 and all faults0, proving the numerical readback detects placement corruption. NBA guard findings0.

This is a finite synthetic rank-partial boundary-input mechanism, not an actual wo_b producer or four-rank transport replay. It qualifies both128b halves, odd source reads, overlapping odd destination writes and the canonical RB tree. Explicitly open: actual wo_b capture/output ownership, four-rank ingress, current selected die source/row leases, fixed producer-to-consumer dates, repeated fullvector tiles/result distribution, HOST/KS and full layer/token. Bench step spacing80 is a conservative test calendar, not rate credit.

Full sources/objects: gold1 and spilled epyc9 /srv/opentallas-scratch/claude/codex-tok-s81-layers/dense_driver/fold_layout_r3/{src,component_r2}. Failed predecessor remains immutable in failed_r1 and remote fold_layout_r2/component_r1. publication.json separates observed write-pin ages from source-composed SRAM commit edges.
