# CODEX HEAD takeover 2026-11-08 02:22 PST

Current HEAD count: 4/4 hard cores and 17/25 types (02:11 release tree). No die gate closure claimed. All route HOLDs and DO_NOT_COUNT flags retained. No merges, tags, plan-of-record changes or deletions.

| Scope | Current / running evidence | Next / owner |
|---|---|---|
| hd_lep0N vE-b | epyc5 scratch3/claude/dh85lep/kit/hd_lep0N_vE; LEC EQ, detailed placement legalizing 283249 cells at 02:24; controller intel2 ~/dh86/lep_vE_b_place.log, goal CTS | View actual place, read CTS; HEAD lead |
| hd_host vD_C | epyc6 scratch2/claude/dh86/hd_host_vD_C; fresh LEC hyp5 alive; hunt FSM no-recode class fix; goal floorplan, no PLACE before EQ | Collect EQ then one reviewed PLACE; HEAD lead |
| hd_ctl vF | epyc4 scratch3/claude/dh83/hd_ctl_vF/hd_ctl; PLACE+EQ done ~17:00 11-07; full17:06 handback recovered by child | Correction: vF reach509.868 and wcnt setup-33.71 failed review; ctl child advances existing vG WINDOW_PRE/site-packet private PLACE, not vF CTS |
| TX FOLD vH | epyc4 scratch2/claude/dh85txf/kit/ot_s81hd_sc_tx_vH_fold_a2; routed DRC0, 18 internal hold endpoints -10.30ps / port -32.15 | tx_hsplit child: image review, one eligible hold ECO, routed LEC; branch pending merge |
| HSPLIT e/w | intel2 scratch2/claude/dh85hs/kitsG; e GRT0 TT+7.91, 4 internal hold -5.14; w fixed LEC running hyp21 | tx_hsplit child collects w EQ, GRT screen; e explicit route HOLD preserved |
| hd_mesh vA/vB | intel2 scratch2/claude/dh86mesh/mesh_v1/hd_mesh_{vA,vB}; GRT congestion iteration2, live at 02:24 | mesh child actual GRT views/census; HOLD_ROUTE preserved |
| hd_spn vG_LK/end vE3_LK | intel2 scratch2/claude/dh86spn; EQ54104/40269, mutants caught, CTS/GRT units live | spn_tile child collects actual GRT/census; HOLD preserved |
| hd_tile vH7 | intel1 scratch2/claude/head-forms-2/tile_vh7/hd_tile_vH7; channel re-form and only4 relay latches retained | spn_tile child collects PLACE/CTS/GRT; explicit route HOLD |
| hd_serdes SC vJ | intel1 scratch2/claude/head-forms-2/sc_vj/hd_serdes_SC_vJ; prior GRT0 then 16GB memory failure, current48GB GRT job | spn_tile child collects; superseded vH not relaunched |
| hd_ctl_n | Already signed off, current count includes17th type; ds/dt re-sign records | No recheck; auto-resign lane handles flow updates |
| Token/cycles | LEP COL0=2 and ri+11/+10; stress release collision remains; mesh RBL+1TX edge, TX FOLD+0 | svc_token/token informed of exact current branch+kit; owns compiler/model |

## CODEX notes
- 02:24: HOST vD_C LEC alive on epyc6 (container dpkit-hd_host_vD_C-2217118); no duplication. LEP vE-b detailed placement past global-place band failure, zero placement failures/overlaps in current log; actual completion and image still owed.
- Existing stale failures remain failures: HOST vD_B OOM/no verdict; hd_host_w kitsF differs344+undecided5 = hunt FSM recode; SPN vF_U other hold2815/-53.49 and END vE2 other1195/-66.80 = cross-tap zero-logic; tile vH4/H4b NDR route capacity failure; mesh TS3 large TT/DRV/hold miss; CTL vE large setup miss; SC old16GB GRT failures = memory cap. Their structural successors above own followthrough.

- 02:29: tile vH7 GRT collected by child: TT -42.03/4, FF -7.13/4, slew0; remaining u_srl_116 lockup causes setup borrow failure, so no route. Geometry viewed; child narrows structural relay-latch correction. Mesh current async LEC pending; old lec.json is inherited, not fresh proof.

- LEP planned geometry VIEWED /tmp/codex-head-0222/lep_plan.png (epyc5 kit plan_v2.png): four pair macros face central SRAM/station band, TX banks lane-colored next to pair pins, no macro wall across whole band. Concern: projected cut demand3400 wires exceeds plotted capacity~2900 at x1180–1250 and1360–1450um in RX/landing hub area. This old estimate is advisory; actual placed density and GRT needed before any route. Demand-sizing vE-b windows fix legalizer capacity, not this bus cut. Hold route until actual check.

## 02:3x results and active followthrough
- LEP vE-b FAILED DPL-0033 with exactly2 FIRM overlaps, no CTS. Corrected initial inference: overlap already exists in3_4, not introduced by mirroring. Actual ODB image /tmp/codex-head-0222/lep_overlap.png VIEWED. Two INVx1(width.162um) were packed at.432um pitch; timing grew first to INVx8(.540um), producing.108um overlap on2rows. Existing OT_CLAND_FIT_RESERVE=resize checks family width but cland_occupy reserved original w/.4 only. Fix hub codex/head-lep-reserve-0222@3a1829140f, 17 focused testsPASS. No RTL/cycles/plan change. Actual helper probe from original3_2 staged to own intel1 scratch2/claude/codex-head-lep-0222/probe, after own E5 unstarted memory waiter3711932 cancelled. Failed vE-b retained. E5reported53GB was usable root space, actual153GB (fleet corrected), not disk free53GB.
- CTL vG active E4 scope oth-ubuntu-3733334-1794133860, fresh synth/native checks passed, FACE_GUARD4424/4424, REG_FANOUT47715/0over64. First own admission only missed lec.py preflight; fixed canonical tool staging, no P&R ran on failure. Source hub codex/head-ctl-vg-0222@4744a03c72e. PLACE only, route HOLD unchanged.
- TILE own vH8_capture PLACE-only pilot queued via ot-run40GB8T, fixes measured latch->capture reach on4 latches by moving beside capture (zero RTL/clock/cycle change). Branch codex/head-latch-capture-1108@22ecad64e85. H7 nominal0setup TT-42.03/4 remains FAIL; extra60probe is INFO per latest methodology. SPN broad CTS relay-latch setup remains open pending GRT.
- MESH both GRT overflow0/4.54% usage before repair, max-wire repair healthy. Fresh async LEC still pending; inherited old EQ is not current proof. Source class fix hub codex/head-mesh-dsrep-1108@8513f37af3e exposes independent DSREP, zero cycles; 12 testsPASS and64bit SAT lockstepPASS/bit-swap mutantFAIL. No candidate new P&R until current GRT outcomes.
- TX folded route capsule transferred to intel1 then ot-run spilling toE6 for nominal base signoff; bounded near-miss ECO pending that result. Actual density image viewed. Faceguard source fix hub codex/head-faceguard-0222@c462697287 applies exact existing skip_re to planned pins too;6testsPASS incl missing-data failure control. No shared gate bypass.
- HOST vD_C live fresh LEC onE6 progressing hyp8/rawbase11; still no verdict, no PLACE launch.
