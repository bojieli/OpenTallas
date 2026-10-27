# CODEX HBM coverage 2026-10-26 20:03 PDT

Working branch codex/hbm-2001; no source mutations in paused worktrees.

- PATH-HBM: CODEX took over: R13 planS2 clock/plan repair on codex/hbm-2001. Collected planS2 DS lower/mid/upper loss 0.89/0.60/4.19%; R12 GRT50 signal overflow0 but KIT rc1 stale u_sfup_Q clock tap. Cause: R9-R13 replicate/place hard cores without regenerating clock.taps. Repair now yields NW104/104 + NE102/102 centre entries (old81/80); native core pin and die tree rebuild still required. No freeze/signoff claim.

- HBM-ARCH: CODEX owns current R13 lane multicast/census followup via PATH-HBM. R12 missing21k wire finding handled by R13 direction/multicast model, but unknown RTL direction4354/11750 pin bits, in-surplus2282/1133 and soft-glue2154/hub remain model assumptions: native bit binding still required before freeze. No old 1:1 transport adoption.

- HBM-CORE-LAT: CODEX collected latest: PGS03 source LEC67599 EQ (prior collected), geometry remains FAIL SRAM across strip. All140 reach types require structured rebuild (58-first lower bound). Waiting qualified QC shared-generator/slices; no broad unqualified rebuild. Current hub clock postpass repairs stale placement/replica tap names only; 250/202.5 contract retained.

- HBM-MU-AUDIT: CODEX collected taller fixed-bound MU probes: H4320 NW x0.567/y0.433 segment max0.577; NE x0.410/y0.480 segment max0.590, both pack PASS MODEL. H4665.6/5184 also MODEL PASS; 4043.52 output not finished at20:03. This supersedes interim claim no tested height closes; R13 multicast not included and area/timing remain inferred. No MU scope decision made.

- HBM-PG: CODEX reviewed latest result: PG model/real parity and domains cause diagnosed; PDN-ONE merged main resolves shared emission contract, so HBM clock must rebuild against corrected PG. Historical PHY isolatedIR5/5 PASS20.993..28.842mV is not current-die freeze evidence. No superseded PG/clock route adopted.

- HBM-CORES: CODEX consolidated active work under PATH-HBM/HBM-CORE-LAT; retained ROOT actual comparison13213/13213EQ and Q3EQ83261/83261. Old clock/F6/face failures require current master-plan slices; no routing waived. SM cluster and SFU distributed-interface exactness candidates remain not physically qualified.

- HBM-KITS: CODEX consolidated under PATH-HBM: original EDGEkit8139pins/8122FSFF PRE_CTSHOLD; canonical oneclock source5views/7slots candidate needs native recipe/interface integration. TKM V6 CTS historical and explicit noGRT conditions retained; no stale kit requeue. Actual current plan slices + native clocks required.

- ELEM-HBM: CODEX consolidated under PATH-HBM/HBM-CORE-LAT: legacy idx/xp/hc/bankq/gq geometry failures retained. Not launching old near-miss kits because current B1/R13 interfaces+clock/master-plan unresolved. ROOT actual LEC closure retained; new physical work proceeds on current hub plan.

- TRIAL-HBM: CODEX collected R12 die signalGRT50 ovf0 KIT rc1, stale replicated-core clock taps root cause now repaired in optin postpass (PATH-HBM). Last partial-M5 root-only FAIL1437784 vs bank-only1196448, allM5=0: both core families needM5. Prior isolatedPHYIR passes remain historical until corrected currentPG+clock. No full-die rerun before geometry review.

## CODEX notes 2026-10-26 20:58 PDT: native MU architecture model
Pushed codex/hbm-2001@a810b810f. Canonical model: results/hbm_mu_2001/buddy/NW and NE/candidate_type.json; reviewed image results/geom_review/codex_hbm_2001/buddy_final.png.
32 native four-macro VM banks,32 FUSED lanes,28 external golden tree nodes,L4 delivery (L5 optional excluded). Single central FUSED hub0.11944mm2 reserved but unplaced,888bits/hub. Atomic624.24x518.4 bank/FUSED buddies unpack to separate real cores; named endpoints and balanced eight-bank groups preserve logical IDs.
H4320,bound3957.12: NW whole0.548/0.414 maxsegment0.553;k3. NE whole0.463/0.520 maxsegment0.588;k5. Independent96nativeVMlinks18/282/257 allparallel,32pairs gap8.64 maxdirect65.88um,0coreoverlaps. Final directgap removes111NW/75NE relay cycles, all listed for latency/compiler rebinding. NEup271 period4 protectedk5->k4(+13wires),allnewMUtreehops<=405. All hard cores explicitlyM5.
Architecture model PASS-COND ONLY; NOT ROUTE READY. New native pins/clock/PG/reset and FUSED W/E repin/rekit required; root placement, real native static calendar/token, existing SU transport pricing and TT/FF die STA remain. Old R11 face stations have reach gaps because pin spreading follows routing; NE4 old routes also failed. Retained and diagnosed, no waiver or die freeze.
Conditional die area526.571mm2 withoutSMrowgrowth /529.979 with120umSMrow assumption, vs503.997SU. No unchangedSUlatency or FUSED81/103II claim. Source native zero-cycle adapter is FLOW-KITS-owned. Old diagnostic proxies remain live: mu_r13 H4043NE447905,mu32_r13 H4320NE1201563/H4665NW1202180; they do not block current native candidate.
