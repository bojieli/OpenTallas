BF A current routed failure diagnosis / bounded next step, 2026-11-01 21:40 PST

PASS-COND one bounded route-retaining ECO iteration after independent review.
Personally viewed actual_failure_paths.png from actual current ck12A6_finalODB,
native read-only geometry dump unit4105866-1793596370 exit0. Macrofree116.64x198.72,
103034nonfillcells / actual66.78%fill, no collapsed placement or macro wall.
Current connected Manhattanr2r239.81um/19779captures/0>405/0loops. The highlighted
setup path is a local20-cell decode/arithmetic cone, not a long unstationed hop.
The hold path is a short north-face input chain already clustered near capture.
All clock wires and original pin/clock/reset/outline contracts remain frozen.

Actual existing nominal0/25ps833ps signoff: TT−0.84/3, FF−24.25/372, slew8/8,
DRC0/ANT0. Thus a current051 re-sign cannot be assumed to remove the failure by
policy. TTfam_kr0→g_e27n.g_wq0[15].tb2[1]: XOR/OR/NOR→HA/FA→AND tail,
finalAND3x1 drives19loads with~90psdelay. Targeted setup10/DRV repair is a normal
data-only candidate; no broad clock trim or RTL arithmetic/pipeline change.
FFworst xb_data561→r_xb_d561 input is short against propagatedclk_io_w;
qy0→bk_fault0 also−13.92. These external-input hold cones differ from the internal
TT critical cone. Normal hold12 padding can therefore be tried without a blanket
constraint tradeoff. Exact fresh TT/FF/DRV/DRC/antenna/current051 routedEQ decide.

Concrete prepared own runtime Intel2 codex-s81-bfA-2112, untouched original
source s81ck10/kits/dsfd_bf_front_roots_ck12A. Current source clone has only its
signoff/LEC tools staged from exact051; all RTL/pins/params/clock data unchanged.
Gated sequencer f25e09975a82 (nowmerged), single-mode TTt12 (setup10+DRV)→FFb12,
max1iteration, clockwirefreeze blocking, route-keeping onlydirtynets, no full
rebuild, OT_PRD_TARGETED1/HOLD_ALLOW_SETUP0. Source actual oldh routed signoff
is supplied as eligibility input, never a fake GRT record. Existing B_E live,
A_E retired17:17, SS20 launched no duplicate. This is at most one A alternative
alongside B_E; preserve every failure. No new cycles or source adoption.

PREPARED ONLY pending independent review / ROOT dispatch selection. No BF CAD
launched by Codex. Original generation identity remains unknown where absent;
no source-publication/count authority is inferred. Exact command is in
COMMAND_PREPARED.txt. Current L2/VEs/VSW closure work continues independently.
