# KV relay corridor candidate, 2026-10-20

Status: geometry preflight PASS for two variants, NOT a strict die result.
Source branch codex/kv-relay-plan-2210; geometry evaluated at c6c649db6
(018abccda placement change); a95cb0efc adds endpoint-priority allocation.
Read-only preflight stops before `_relays`; it does not omit any check from a
qualifying chain. Strict bind, real relay ages, GEN safety, PG/M8 GRT trial,
TT/FF STA, clock and die IR remain mandatory.

The d23p1/2/3 failures are preserved in the original KV-D2D3 run directories.
The failures respectively expose sink-greedy placement of 39 PV.start pads,
exhausted D2D payload endpoint approaches, and K.tx_record above the immutable
K22 image. No image, cycle count, pin model or reach constraint is relaxed.

## Two concrete variants

Both set OT_KV_ATTN_WEST_HOST=1 OT_KV_EQ_ROW_BANK=1
OT_KV_D2D_ENDPOINT_FIRST=1 and unset OT_KV_ATTN_DXY/OT_KV_ATTN_AT_D2D.
Other strict integration flags stay with the die owner.

| Variant | OT_KV_D2D_APRON_UM | HOST/D2D free channel | Wide relay rows | Legal row sites | Die height |
|---|---:|---:|---:|---:|---:|
| A | 216 | 347.784 um | 3 | 62 | 28432.08 um |
| B | 302.4 | 434.184 um | 4 | 83 | 28518.48 um |

The 548/549/552-bit words use 45.36 x 82.08 um relay frames. Row pitch and
placement use the actual GX/GY lattice, 21.6 um block halos and 4.32 um relay
gaps. Rows align from the D2D S face so endpoint reach is not spent on an unused
bottom margin. The committed JSON gives each actual site and a simultaneous
nonoverlapping assignment for all five wide words (rx_payload, rec_rx, rec_tx,
att_tx_payload, emb_tx_payload), checking every realized D2D view bit against
340 um. These are available sites, not an allocation claim after all other
chains have been built; the new priority gives those constrained words first
access before control/boot chains.

Attention moves from the old p1 home (5741.712,25261.2) to
(5917.536,27002.16) for A. Its E side has a 129.6 um approach to HOST; its N
side is 43.2 um below D2D. Exact K22 padding remains fail-closed when natural
stages exceed the image. S-going PV/control words get freshly derived/priced
ages. All added equalizer cells remain real one-cycle relays; the row bank
reserves its complete rectangle before placing a serpentine R0/MY chain.
Every intercell and endpoint hop is measured from actual cell pins.

The die width remains 13476.672 um. Relative to d23p1 height28302.48, A adds
1.747 mm2 and B adds 2.911 mm2, both below 28600 um in height. No token-rate
claim is made until the actual relay ledger and compiler have been exported.

## Future CTL slot, not enabled

The 345.6 x 475.2 portrait slot legally fits (6565.536,25961.04) in either
variant with normal halos. Legacy CTL source stays exact. C32 source/native
repair is another lane; its +2 drain and +2 boot edges must be priced before
C32 is enabled. Geometry alone does not qualify that binding.

## Fleet validation

`bank_tests.log`: 3/3 PASS (39 real row cells, lattice, orientation, per-hop
reach, no overlaps; occupied region and unreachable endpoint negatives).
`corridor_proof.log`: both geometry variants PASS, unit
oth-ubuntu-15477-1792560095 on ot-epyc6, admitted through unpinned ot-run.
The script and full site/endpoint packets are retained alongside this note.

## Integrated strict trials, 22:27 PT

Integrated source c641da67d = die-owner743e0575d (ROOT14/LAND/scalar
bind alias/GENfacts plus plan) + strict-launch and actual M8 routing fix.
The original router used M4-M9 even when the repeater RC knob selected M8;
this source sends M8 into the Docker GRT process and routes signals M4-M8,
reserving M9 for clocks/PG. `OT_KV_STRICT_CHAIN_ONLY=1` suppresses automatic
diagnostic continuation after marker/bind failure. No diagnostic bypass is
set. `launch_strict_trial.sh A|B` captures the exact flags and commit.

Both admitted unpinned through ot-run with 250 GB, matching the established
KV chain admission (GRT140GB plus concurrent clock stages). Five congestion
iterations form the early GRT trial; TT/FF and IR still run on every build.
This is an iteration count, not a wall-time limit. Full physical and schedule
qualification remains pending. LAND=1 is an opt-in candidate with standard
LEC EQUIVALENT already present; independent d22hl2 bind is still pending.
AHUB a7 adoption is conditional on its independently running positive LEC.

- A: ep6 unit oth-ubuntu-69163-1792560404, session3766;
  `/srv/opentallas-scratch/claude/qwen-kvsys/kvs14r-c641da67d-codexcpA`.
- B: ep6 unit oth-ubuntu-69436-1792560405, session34650;
  same path with suffix `codexcpB`.

Initial bash-stdin wrappers exited0 without executing the source because the
fleet admission process did not retain stdin. No result directory or job was
created. The actual launches above carry the script as a quoted bash argument;
worktree creation and running source were verified. No failed design verdict
was overwritten or rerun by this setup correction.

## Resumed 22:40 takeover: A/B failures and concrete corrections

Both original c641da67d trials are terminal PREP FAIL, preserved unchanged.
A ultimately failed attention TX payload relay stage2 with460um remaining;
its first failed placement attempt is captured in A_endpoint_failure.json
(stage3,380um remaining). B failed the final actual pin-hop check:
`rly_ks_pvst__f0_3.b -> pvw_1.st` spans12945um, before equalization.
No GRT, timing, IR or strict-die PASS resulted from either run.

The A snapshot demonstrates genuine legal sites between the existing HOST
record relay frames, around x6627..6633 and y27227..27238. The existing fine
fallback perturbs Y alone, so its X grid misses the narrow gap. Source5465e3357
adds default-off OT_KV_RLY_FINE_XY=1; all GX/GY, halo, predecessor and farthest
bit checks remain active. endpoint_xy_regression.py executes the source's
actual nested _spot AST and actual refinement AST on the captured occupancy:
legacyY-only refuses; XY accepts6630.336,27239.76 with185.770um predecessor
and287.256um farthest-view-bit distance. Moving the predecessor out of reach
still refuses. Original snapshot and log are committed.

Sourcee0dc985f1 additionally adds default-off OT_KV_PV_CONTROL_PIN=1.
The PV control inputs use canonical N-face positions from the existing PV
plan, transformed by the actual instance orientation before first-pass
routing. pvw_1 is MX, putting st on its SOUTH end; the previous first pass
aimed at the nearest frame edge and left the12.945mm terminal wire when
later full replans failed elsewhere. No drawn pin, port, leaf RTL or reach
check changes. Actual resulting relay stages must be recompiled and priced.

mechanism_check_final.log (ep6unit809610-1792561918, session10135):
- PV st hints match actual masters()/pin_xy() positions: pvw_0 R0
  (6575.136,12065.736), pvw_1 MX(6575.136,13171.680). The projection explicitly
  supplies the two existing start-fork endpoint edges because this hook runs
  before the relay pass has installed its fork buses in m['buses'].
- With both optional fixes enabled, the actual A relay planner completes the
  attention TX chain in3stages, last output6675.696,27280.8 and farthest
  realized D2D view bit287.286um (<=340). It stops immediately after that
  chain; this is a mechanism proof, not a full-plan or strict-bind PASS.

No duplicate full chain was launched while paused d24pa/b/c and CTL11 portrait
preps progressed. The next integrated source must take the die owner's
actual source-direction/clock qualification fixes before another strict trial.
Unbound dual-clock PC roots and other GEN failures remain explicit HOLDs.

## Revised analytical A/B models in progress (22:56 PT)

`plan_fixed.py` runs K.build() only at immutable sourcee0dc985f1, with the
original A/B kv_flags.env plus OT_KV_RLY_FINE_XY=1 and OT_KV_PV_CONTROL_PIN=1.
It saves the final actual pin-reach and relay/bundle-age ledger if build()
returns. It performs no GEN qualification hook, P&R, or diagnostic bypass.
Both original full chains and d24pa/b/c + CTL11 preps are now terminal FAIL.
Future strict trials must additionally integrate the die owner's real source
port-direction adapter/clock evidence; old unknown roots remain HOLD.

- A: apron216; ep6unit2124570-1792562212, session7669,
  `/srv/opentallas-scratch/claude/codex-kv-relay-plan-2210/fixed_plan_A.json`;
  local log `/home/ubuntu/scratch/codex-kv-relay-plan-2210/fixed_plan_A.log`.
- B: apron302.4; ep6unit2124796-1792562213, session86019;
  same result/log names with suffix B.

Initial allocation completed with728/736 actual pin-hop violations before the
normal drawn-pin replan/repair. Both replan attempts encountered the existing
WS group/PC narrow channel (`slg_WS_0.o_pc1 -> kvpc_WS_9.i_grp`, remaining697um).
This is intermediate progress, not a final verdict. Preserve progressing jobs.
