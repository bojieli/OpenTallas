# CODEX-S81-COLLECT2-FIT-1021 — 10-21 09:39 PT
Bounded read-only service B fit audit for S81-COLLECT2. No layout, new gate, RTL change, other-worktree mutation, or adoption.

## Result
G4 attention has concrete NT1 source and kit geometry; current G7/G8 already reserve the attention band. The old +73 mm2 proposal compares obsolete mu7 slot area against G16 attention and must not govern release. Exact full service B fit remains BLOCKED by the missing implemented current-ABI svc-only physical wrapper and NT1 functional qualification. The 1555.2-um svc height is a pin lower bound, not a hardened footprint.

## Authoritative selection and existing placement
OWNER 08:15 keeps G4 attention; OWNER 08:30 permits full 33x26 mm reticle. G7 actual plan (s81-die72-g8/results/arch/s81_die72_1021/g7/plan_unrouted_g7.json) reserves all16 rsv_* = 1728x3801.6, die32648x25952.4. G8 actual plan reserves same slots on die33000x26000, 100-um seal; service column streets129.6, service row street86.4, service-to-slice106.8. Thus mu7 1214x1344 and the owner earlier1728x3758.4 are not the actual current reservation. No margin remains for increasing the die outline itself.

## Exact G4 configuration inventory
WT /home/ubuntu/wt/s81-attn1-nt1-1020, committed HEAD edd3f4a9eba27542db0c85acd98f039af9666355 (existing tools/TB working changes are NOT adopted by this audit).
- tools/ref_tile/specs_s81dv_svc_lp/dsdv_svc_attw_n1_{main,fb}_lp.json: top dsdv_svc_attw_n1_f_lp; main1036.8x2160, fallback1123.2x2160. Four explicit children u_t0.g_g?0?..g_g?3?.u_g, each hgrp8 432x432, arranged2x2. Defines OT_ATTN_HGRP_HARD, OT_ATTN_HGRP8, OT_SVC_LAND_SRAM, OT_SVC_ATT_SRAM, OT_SVC_ATT_PINREG. Params SRAM_MACRO1, PMEM1, TLX6, TXD0, MUT0/AMUT0, DIE_ID0, ST0, ROOT0. Regional ck_c/ck_t0.
- rtl/dsrom_sys/s81_dv/svc_rs/attw/dsdv_svc_attw_n1_f.sv explicitly instantiates dsdv_svc_rs_attw TEXT1/NTP1 and ONE ot_hdc_v41x_attn_tile_s H16/TD32/NBANK5/BW3/PWORDS2/FPL4/FML6/F121.
- NT1 is one physical engine tile, FOUR physical hgrp8 groups = G4; four logical tiles time-multiplex as four sub-beats, compiled p-feed every4cycles, same intended score/PV ABI and merge order. This is not G16 and not a source-free950.4 model.
- This is source/config/kit existence only. DRIVE-S81-ATTN1 and S81-COLLECT2 report actual static PROBE runs1..3 FAIL sc160/160,pv0/0,mismatch1; run4 ongoing. No functional or mapped/clock/route qualification inferred. hgrp8 closure/submission separately owned; no new work launched here.

## Concrete geometry and the remaining blocker
Existing16slot reservation =105.1066368mm2. G4 NT1 attention alone =35.831808mm2(main) or38.817792mm2(fallback). G16 attention alone98.537472mm2 is excluded from release sizing.

With an86.4 registered crossing corridor, the conditional co-located independent-parent B stack is:
- svc1728x1555.2 +86.4 + attw<=1123.2x2160 =>1728x3801.6, exactly current reservation, no die-area addition. Attention can retain native width; no squeeze. However1555.2 is only the nonentry pin lower bound in ebcb8a9d537773648a08d4834cf5e95ef46f8198/results/arch/s81_svc_mu7_pins_1020/model.json (status MODEL_ONLY_NOT_A_DIE_PLAN_OR_CLOSURE).
- That exact model gives full literal-grid uniform/entry pin bound1728x1641.6. Using it requires1728x3888, +86.4 per slot. Uniform16 change =+2.3887872mm2; entry-only2 change =+0.2985984mm2. This is still a lower bound, not a final kit.
- Actual existing svc_rs_lp / svc_rs_entry_lp kits in specs_s81dv_svc_lp are1728x2073.6. They represent the historical different-ABI landed wrapper, explicitly NOT equivalent to current production ABI. Merely stacking these requires1728x4320, +518.4 per slot /+14.3327232mm2 uniform16, not the current-slot fit.

Fixed-layout vertical growth fails: each row already has86.4 street and the upper service row is106.8 below slices; uniform+86.4 height removes one required row street and consumes most upper street before moving anything. G8 construction has only20.4um added vertical room and full reticle. A coherent service/neighbor replan is required if implemented current-ABI svc core exceeds1555.2; no global impossibility or exact extra-die count established. Area-only free space does not prove pin/relay-channel fit.

## Next action owned by parent
Recover/repair NT1 on its exact source/params, preserving failed probes. Derive and implement current-production-ABI svc-only landed parent (including entry) and its full pin/clock/reset/native storage contract before choosing final B footprint. If it fits within the existing attention-inclusive reservation, independent hardening does not require extra die area. If it exceeds, model repack/add-die cost under owner authority; never squeeze or substitute G16. +2 crossing cycles are an authorized price target, not measured schedule/functional proof; exact pin order, landing-ring width, <=405um graph and static calendar still owe qualification.

Machine-readable captured file hashes/slot coordinates/arithmetic: /home/ubuntu/claude-takeover-20261007/artifacts/s81_collect2_fit_1021/inventory.json. No files in the inspected WTs were edited.

## 09:44 follow-up: actual NT1 static-probe failure classification (source/behavior, no fit study)
ROOT/collect2 redirected this lane to actual G4 ABI functional failure. Read original ep5 probe logs/source, preserved long sweep client404852 and original run4.
- run1 T640 P0r20/P0d20: expected160score/8PV, accepted inputs per engine1job/16q/160kv/3p, refused157p each, sc160/160,pv0/0, sc_mis0,pv_mis0, incomplete1.
- run3 P0r60/P0d60: ref42p/refused118; DUT13p/refused147, otherwise fullq/kv/score, same noPV. Reference lastscore226, DUT708, delta482.
- Therefore displayed mismatches1 is completeness failure, NOT an observed data-bit mismatch. The reference also cannot finish; equal zeroPV is correctly rejected.
- Causal source: ot_hdc_v41x_attn_s.sv p_ready_i requires p_side=act_b at ILV1; act_b becomes1 only on hand=act&&phase_pv&&!act_b after all front-job q.k issues. REPL2 skid accepts two earlypsteps, then refuses until hand. Static driver deliberately advances offeredpindex on every pulse regardless ofready. P0=20..60 is before legal p-side activation for T640 (especially NT1), so the compiled input stream is dropped and never enough completepblocks arrive for finalPV.
- Concrete correction is a legal COMPILED PO/PVO and fixedpace, NOT changing production to ready/credit flow. Need actual complete paired T640 and tailcases before rate/compiler adoption. Existing score last-edge delta482 is observed at this source/T640 only, not completePV or blanket480 price.
- Bounded existingbinary diagnostic launched ep5 unitoth-ubuntu-3090845-1792600930/session57089: ./sim +static=1 +t=640 +p0r=300 +p0d=800 +pace=4 +maxcyc=5000. ExactbinarySHAe1544d9453f71bb0f8892ac6800f6d83945aeb13f1f7846a78a7431bd0555fbd; sourceTB ead50b3ab87314f8386d4172805e9c867458ab7c71505d2fef07a48294d367d7, engineb1f0d0def70e01764895016c92556ec03ebc7254d4b469fe532971d947020dc5. Ownoutput /srv/opentallas-scratch/claude/codex-s81-probe-fix-1021/t640.log, originalbinary hardlink only, no write tobinary/source. NT1/reference pfeed fixedpulses remain unchanged.
- Three earlier dispatch attempts had no sim onselectedep9 because SCRATCH2 auto-created emptydirs; NOTRUN simulator/no design outcome (units3714092,3723748,3747497). Original binaries/longsweep untouched; ownsuccessfuldispatch uses data-localdirectory and OT_RUN_NO_SCRATCH2=1, no --hosts.

### 09:44 TERMINAL result: concrete fixed-schedule correction PASS (single case)
Existing exactbinary unit3090845-1792600930 TERMINAL0,81.2s,4546cycles. T640 /seed1 /P0ref300 /P0dut800 /dutpace4 /max5000: BOTH consumed1job/16q/160kv/160p, expected160score/8PV delivered, refused0/prog_bad0, sc_mis0/pv_mis0/incomplete0 => PASS. This confirms earlyPO was causal for the reported fail, with no RTL/ready-driven change.
Ref lastscore226, firstPV535,lastPV542. DUT lastscore708,firstPV1517,lastPV1545. Rawdifference score482 /lastPV1003 includes the explicitlydifferentPO500. Relative toPO: ref first/lastPV235/242; DUT717/745; relativefirstPV+482/lastPV+503 (8-beat burst spans7ref vs28dut). Do not publishraw1003 as intrinsicalgorithm latency or old480 as measuredwholejobdelta. For this stimulus a safe wholeburstavailableafter1545 can inform a compiled PVO candidate; actual service SRAM/p-feed/drain wrapper must proveits own schedule and calendar.
Artifact local artifacts/s81_collect2_fit_1021/nt1_static_t640_p300_p800.log + nt1_probe_sources.sha256. OneT640sourcecase only: tail/multijob/NMUT/actualSRAM/currentlandedABI qualification stillowed. Existing longprobe untouched. No furtherprobe launched after boundedresult.
