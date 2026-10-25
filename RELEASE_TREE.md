# OpenTallas release tree (refreshed 2026-10-25 03:27 PDT by CODEX)

Snapshot: 2026-10-25 03:27 PDT. Published main = a8512b6d2; integration candidate = codex/integrate-1025@d2630948f (not yet main). Lane results and correction candidates below are ahead of main. No target has a complete G4 + G5 release pass. QC has two distinct signed cores (SU8 and CRH), KV four known signed cores; legacy /api/elements CLOSED counts are not current SIGNED evidence.

Gates: G0 plan, G1 geometry review, G2 prototype, G3 signed physical partitions/cores, G4 assembled die timing, G5 token pass. Current signoff is TT setup / FF hold, 60/25 ps uncertainty, 833 ps; related-pair CPPR skew <=80 ps. Plans that pass G0 still need actual per-bit station geometry, routed timing and the bound reset/start contract.

## EDIT · rules
- Tick a line only with committed evidence (sha). Failed verdicts stay, struck through only when superseded.
- Status words: RUNNING WAITS TODO NEW COORD OWNER FAIL PASS DONE BLOCKED.

## DIE seam · Clock, reset and seam method (all dies)
- [ ] SEAM.CLOCK Industry MSCTS spine + pair-skew/CPPR die STA (owner dec. 5) · CLOCK · RUNNING · Signed-source measurement bug fixed b0613e9d9; elemB TT63.68/62.02 and FF59.39/57.26 ps pair damage. Real die hold closure still open; HBM PHY/PG clock corridors being repaired
  - [ ] SEAM.CLOCK.STA2 Die STA and clock reruns on current plans · CLOCK · RUNNING · Retain old failures; use corrected pair metric, actual signed views and native per-corner clock contracts
  - [ ] SEAM.CLOCK.HEAD S81 head seam with corrected related-pair metric · CLOCK · WAITS · Older 81.9 ps spread-era figure is historical; real assembled seam gate remains open → SEAM.CLOCK
- [ ] SEAM.REPLAN Batched M7 / reach405 / wavefront re-plan · S81 / QC / KV / HBM · RUNNING · Candidate batch747fa737a not main; exact pin-bit audits found failures hidden by bundle centres; corrective per-bit plans in progress
  - [ ] SEAM.PROTO2 Fresh prototypes only after actual-bit geometry clears · COORD · RUNNING · QC baseline su_l0 overflow131719, CBN168, FTC0 but all fail reach; corrected QC candidate53/53 geometry PASS; CBN/FTC prototypes CLEAN, SU_l0 GRT still live → batch merge
- [ ] SEAM.RESET Wavefront reset tools and synchronous-input RTL · RESET · RUNNING · SYNC_INPUT opt-in dacd148ba ready; QC preflight377 parts/max core release129 clocks. Bound reset fanout/start adoption still required on all dies
  - [ ] SEAM.RESET.ADOPT All die/tile binds adopt wavefront control-only reset + explicit start · S81 / QC / KV / HBM · RUNNING · QC token bind still directly fans rst_n to377 partitions; no whole-die token release qualification until actual wavefront/start is bound → SEAM.RESET
- [ ] SEAM.CP1 CP1 seam method and wavefront proof kits · RESET · RUNNING · Earlier seam TT+434.5/FF+104.9 remains component evidence; new wavefront pair placed probes, owned warm repairs; full current pair signoff pending

## DIE s81 · S81 (DeepSeek-V4.1 ROM layer die) + 4 head dies
- [ ] S81.G3 S81 frame partitions · S81 · WAITS · Core/FT geometry correction precedes re-kits; earlier frame FAILs remain. New reset/clock pins must avoid PG before route → SEAM.CLOCK, SEAM.RESET
  - [ ] S81.G3.CORES S81 hard cores and explicit FT cell packing · S81 · RUNNING · Known vq/hrow/LLd/l5f/cfg7 closures retained; split ve_m/ve_s/vn_a/vn_b reviewed. Independent corrected core+FT geometry94/94 types PASS, zero explicit cell/core/overlap violations; parent prototypes and full signoff still owed
  - [ ] S81.G3.ST405 Station405 kits and reset-pin access · S81 · RUNNING · Known signed station views retained; t30 reset-pin/PG DRC diagnosed, source181eaa1e0 ready; regenerate and review moved pin coordinates before new route
- [ ] S81.HEAD Head die elements and tile transport · S81 · RUNNING · Warm element repairs active; FF-reference correction gives elemB c9 -8.13ps/53 residual hold endpoints, TT2 slew violations. Tile transport/fences and final signoff remain open
- [ ] S81.XDIE Pair-B endpoints + PHY/ESD/bump composition · S81 · RUNNING · DEC12R model PHY geometry PASS-COND only; actual PHY footprint, WS3 bump escape and ES0/ES1 offshore physical disposition remain open
- [ ] S81.IR PHY/core supply split and IR · S81 · RUNNING · Split-supply tool ready; selected PHY power and actual bump contract still needed for final IR, explicit stand-in diagnostics only
- [ ] S81.G4 Abutted die · S81 · WAITS · → S81.G3, SEAM.CLOCK
- [ ] S81.G5 DeepSeek token pass · TOK-DS · RUNNING · Entry/control components pass; L14 Engram reconstruction exact + mutant caught. Norm/quant schedule and full bound data exactness remain open → TOK.DS.COMP
  - [ ] S81.HW Exactness hardware and bound data paths · S81 / TOK-DS · RUNNING · IDX/runtime row-read/end-slice paths and norm partial deskew must be integrated with real compiler schedules
  - [ ] S81.MTP Measured composed MTP schedule · TOK-DS · RUNNING · Owner six-position pipeline law is rate-of-record; measured overlap and recoveries toward3000 tok/s remain open, no final rate claim

## DIE qwen_compute · Qwen compute
- [ ] QC.CAP Accepted capacity plan and current re-plan · QC · RUNNING · Capacity plan on main; current meth2/per-bit candidate ahead of main,18 changed types/251 lanes with +1..3 cycles; geometry and token rebind owed
- [ ] QC.SU Bound SU program alignment · QC · RUNNING · Fix af1bbef0c adopted in branch bind (+3 start edges), fixed-SU bind0 errors; reaches release through meth2, not a completed die gate
- [ ] QC.G3.A0 A0/core clock closure · QC · RUNNING · Two distinct signed QC cores SU8/CRH; rp1 clock and SU-lane cores in progress. Selected NK probe retained; rejected variants stay failed
- [ ] QC.G3.FTC coll_ftc actual-bit stations · QC · RUNNING · Baseline GRT0 but actual tl_st_wi hop483.7um violates405; corrected candidate now prototype CLEAN: overflow0, TT+108.93/FF-2.07ps (minor station hold only); full logic kit/signoff remains open
- [ ] QC.G3.TYPES Current-plan soft-type re-kits · QC · WAITS · Independent actual-bit audit/GRT and full waveform reset/start must clear before new kits → QC.CAP
- [ ] QC.G4 Abutted die · QC · WAITS · → QC.G3.A0, SEAM.CLOCK
- [ ] QC.G5 Qwen compute bound token pass · TOK-QK · RUNNING · Meth bind xt1 near64/64+far64/64 and tp8/xdie/ovl4u PASS with mutants caught; AR+1296 cycles. Wavefront reset/start missing, so whole-die G5 remains open → QC.CAP

## DIE qwen_kvsys · Qwen KV
- [ ] KV.BIND Native KV45 rebind · KV · RUNNING · B/C/D integration plus833ps single-clock controller candidate ready; native bind/reset/start and final boot integration remain open
- [ ] KV.G3.HUB hub_Ei and current wavefront kit · KV · RUNNING · Earlier vK GRT0/pair68.0/62.2 evidence retained; new per-bit geometry and bound reset/start must be adopted before final closure
- [ ] KV.G3.CORES KV hard-core closure · KV · RUNNING · Four known signed cores retained; even-head boundary fix98c25c4a8 exact + mutant caught and face_guard1344/1344. ectlk/astk/ahub/PV physical failures still being repaired
- [ ] KV.XING Channel/station correction and crossing cost · KV · RUNNING · Candidate all47 soft types clears planned geometry: max404.808um, zero in-core station centres; physical per-bit packing/GRT and per-lane cycle adoption still owed
- [ ] KV.DFI 833ps synchronous controller/PHY contract · KV · RUNNING · Native833ps controller/compiler opt-in6b0ac47a0 component PASS with independent physical JEDEC and timing mutants; adoption into KV45/boot still owed
- [ ] KV.G4 Abutted die · KV · WAITS · → KV.G3.HUB, SEAM.CLOCK
- [ ] KV.G5 KV boot + token · TOK-QK · RUNNING · Compiler pacing and native controller fixes ready; prior boot528/7161 failure retained. Final integrated wavefront/start boot/token pass not achieved

## DIE hbm · HBM B2n/B2o successor (DeepSeek + Qwen)
- [ ] HBM.B2M B2o physical successor and clock/PHY corridors · HBM · RUNNING · B2n actual-bit scan31/44 types fail (worst620.144um); B2o NPC2/pin/packing/clock/PG/reset integration and FT repair in progress, not main
- [ ] HBM.NATIVE Native B2 one-clock bind · HBM · RUNNING · Logical cut/width/newFAIL0 smoke and967 clockports PASS; historical strict-bind straps/PHY models, reset/start, per-cut SU mapping and W128 HC physical views remain blocked
- [ ] HBM.G3.CORES HBM boundary/core physical closure · HBM · RUNNING · 266/268 generated face-guard views PASS plus exact shell benches; no complete HBM physical signoff set. gq_land corner-reference repair and W128 HC sizing active; generation failures individually diagnosed
- [ ] HBM.G4 Abutted die · HBM · WAITS · → HBM.B2M, SEAM.CLOCK
- [ ] HBM.G5 HBM token integration · TOK-HBM · RUNNING · Native one-clock SU ALAT4 lane1984 outputs/3968 checks PASS + mutants; full native token still open on HC transport/L74 beats/FACE latency. Model-only rates exclude pending deltas

## TOKEN · token-pass gate per design
- [ ] TOK.DS DeepSeek token · TOK-DS · RUNNING
  - [ ] TOK.DS.COMP DeepSeek norm/quant/compiler integration · TOK-DS · RUNNING · Norm partial deskew/compiler data cuts and quant finisher collision-free release calendar remain active; L14 true-checkpoint H reconstruction PASS
- [ ] TOK.QW Qwen component and bound token evidence · TOK-QK · RUNNING · Stage527/527 and meth-bound xt1/link components PASS; real reset/start wavefront + KV boot integration owed before whole-design G5
- [ ] TOK.FREEZE Final evidence run at RTL freeze · COORD · WAITS · → S81.G5, QC.G5, KV.G5, HBM.G5
- [ ] MU.CURVE Latency-throughput curve vs A100 80GB · COORD · WAITS · → TOK.FREEZE

## INFRA · fleet and coordination
- [ ] INFRA.SIGNOFF Current-plan signoff coverage · S81 / QC / KV / HBM · RUNNING · 138 lost-DB historical closures are not SIGNED; track only matching current signoff records. Source-local SELRANGE waivers and fail-closed common runner integrated in candidate batch
- [ ] INFRA.DISK Fleet admission and scratch headroom · COORD · RUNNING · 05:25 rtx-pro root 91%, epyc2 scratch2 94%, epyc1 92% -> INFRA-DISK lane pruning (target root <=85%, scratch >=15% free)

## WAITS · who
### Waiting on the owner
- Actual S81 PHY dimensions, PHY power and final signal/PG bump contract remain OWNER? in CODEX-LOG.md. Technical reset/start and station corrections continue without waiting.

## HISTORY · retained failed evidence
- Earlier trial die FF hold failures (-46..-417ps), old head81.9ps seam figure, prior KV boot528/7161 and rejected HBM/leaf floorplans remain historical failed records. Corrected tool measurements do not erase them or sign off the successor.
- Geometry audit baseline b58fc0f16: QC15/53 soft types fail, KV24/47, S8188/175, head0/16, HBM31/44. Correction candidates are tracked separately; planned geometry PASS does not establish G3/G4/G5.
