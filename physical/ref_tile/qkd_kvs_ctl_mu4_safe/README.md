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
