# Gather S8 evidence, 2026-10-13

Design B uses eight open row slots per root. The production binding is
`half_dedicated_ksplit`, SHA256 recorded in prod_golden.json (d9f84be9...).
All 40 layers, golden routed experts, rank 0, one position: static and stream
maxima are four on layers 2, 8, 14, 20 and two elsewhere. The all-expert
upper check remains live on PVE1; this is not proof for arbitrary expert
orders or concurrent positions. Overflow remains sticky and observed.

S16 failed the actual route floorplan margin at 0.716 > 0.60; S8 fits
the same slot provisionally, with CTS gates in flight. No routed closure
or production tok/s qualification is claimed here.

cluster_verdicts.log is the full 128-root / 32 four-root-leaf hierarchy
compared to the flat 128-entry reference at commit 7584088df. Its root
queue remains 128 deep. L2 returns 37,440 rows and L20 returns 37,312
with zero row/control/status mismatches. Stress, sticky overflow and
coverage refusal pass; lane, chain, no-forward, xgo and overflow mutants
fail. Source hashes accompany the verdict. root_verdicts.log contains
271 root lockstep cases including the real order and all root mutants.

Physical clock mode (`S81PH_GTH_DIE_CLOCKS`) adds ck_l[31:0], index
4*column+row, one clock pin per leaf. Existing ck and ckv clock the control
leaf. The die must deliver compensated phi-R at each pin; the compatibility
mode ties leaf clocks for behavioural use only. This does not supply routed
clock insertion evidence. Cluster control relays and assigned v18 bundle
pins remain owed.
