# KV CTL mu4 SAFE review packet

Source: codex/kv-ctl-mu4-safe-1019, isolated successor of claude/mu-kv-ctl3-1019. No route submission is authorized by this packet.

1. Pins FIXED: all input/output pins registered; rst_n/por_n two-stage face landing. Final reset stages contain 40/16 KEPT copies. PREOPT load counts must confirm ceil(loads/256) <= copies; ot_rst_copies.tsv is mandatory evidence. Counts are deliberately conservative until measured.
2. Reach REVIEW PENDING: unchanged square 475.2 um outline, pin registration and center entry; inspect synthesized/placed maximum stage wire, must be <=405 um. No claim before gate.
3. Fanout FIXED / CHECK PENDING: registered bad and four KEPT halt copies partition enter, leave, deadline, control bank enables. Gate must prove copies survive and critical loads comply (~32). Reset split maximum 256 per copy under the reset audit exception.
4. Depth FIXED / CHECK PENDING: guard forecast root-2, bad registered, root offsets captured at boot; no combinational pin feedthrough. Gate must report stage depth.
5. Storage PASS inherited: no new data storage arrays; scalar guard registers only. MU programme storage unchanged from mu3; gate checks implementation inventory.
6. Floorplan REVIEW PENDING: no macros, lattice N/A. One full-width standard-cell region; W/E 2524 bits /475.2 um =5.31/um; N 1647/475.2=3.47/um. Square aspect1.0. Actual synthesis area/util and layout PNG require owner review.
7. Clock FIXED / MEASUREMENT PENDING: ck constrained to S center x236..239; --cts required; TT/FF spread <=80 ps and neighbor boundary check remain acceptance conditions. io_hold_margin=0.03 ns.
8. Schedule FIXED: all mu3 crossing/boot latencies retained. Ownership drain/host/upstream guards sampled one additional clock earlier vs mu3 (two earlier vs PIPE0). Native enter/leave/deadline and MU re-arm ages unchanged on valid static execution. Config/go/group-fault abort observation +1 ck. No credits/backpressure. Compiler/die coordinator must price extra quiet clock and fault age before binding.

Gate JSON, layout PNGs, OT_RST_COPIES preopt table, and measured clock data are pending. No REVIEW.json is written here. Existing failed evidence remains untouched.

## Gate verdict (KV-GRP-CTL 10-19 ~12:30, recovered: local client PID 942518 died; remote run completed GATE_DONE)
Run ot-epyc5 /srv/opentallas-scratch/claude/ref_gate/qkd_kvs_ctl_mu4_safe-20261019-080131; recovered with
tools/ref_tile/recover_gate_result.py (--route-commit e00f75155) -> gate_result.json; PNGs gate_layout/{floorplan,density}.png
(inspected by KV-GRP-CTL). PRE_ROUTE_GATE: FAIL (clock_rule; source_binding = stale branch tool overlay, not design).
Checklist result (measured):
1 Pins PASS: 22 in / 20 out ports pin-registered; rst_n/por_n land 2 stages, port nets 1 sink each.
2 Reach PASS: textbook reach 0.2 um/stage (pin flops at faces); GRT overflow 0 (M2 20.9 %).
3 Fanout FAIL (partial fix): landed rst_n 2150 PREOPT loads over 40 copies (max 54) PASS; but RTL-internal reset regs
  u_fanr.rs_q (qkd_kv_es_fan_root2_b) 756 loads and u_wprg.reset_pin_n (qkd_kv_native_programme) 409 loads > 256.
4 Depth FAIL: u_lprg.g_mu r_ctrl/r_end -> ctx_t/stage ~675 ps, 17 lv (c_age == r_X-1 subtract+compare, 4-user priority,
  metadata mux in one stage); TT placement reg2reg -152.5 ps at u_lprg.epoch[8].
5 Storage FAIL (missed by mu3/mu4 audits): u_lprg (qkd_static_kv_layer_programme_mu MU=1) holds t_ctrl..t_end 9x36x32 +
  t_gap 144x32 + shadow = ~15.2 kb of runtime-indexed flop tables (> 2 kb -> SRAM rule).
6 Floorplan FAIL/WAIVE: util 10.5 % (std 23,150 um2 in 475.2 sq); pin-bound by W/E 2524 bits (>= 421 um face at 6/um),
  so the tile cannot shrink much below 432 tall; logic sits in 3 central blobs, corners empty. Die frame 1123x172.8 cannot
  host this view (MU-DIE-KV slot decision).
7 Clock FAIL: TritonCTS one root 38,249 sinks from S-centre ck: pin-flop spread TT 182.5 / FF 159.0 ps (boundary
  505-688 TT); N-face pin flops (top-left) are 470 um from the S pin.
8 Schedule: +1 ck QUIET (host/upstream/drain) before enter/leave and +1 ck config/go/group-fault abort observation vs
  mu3 -> handed to the die schedule (lanes/KV-GEN8.md INBOX 10-19).
NEXT (structural successor mu5, not a tweak): lprg tables -> SRAM row fetch (row+next-gap per (user,stage), read issued
on the edge c_load is set, 0 added cycles) and boot-time precomputed r_X-1 compares (MU-KV-BOOT RTL); N kept copies of
rs_q/reset_pin_n through reset_relay_split; symmetric centre-fed spine (OT_SPINE_SYM=1) instead of TritonCTS; outline
pin-bound ~432 tall after the die slot decision. No REVIEW.json, no submit for mu4.
