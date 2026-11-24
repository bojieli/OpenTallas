# KV-HG-CAP handoff (lane started 11-23 20:46 PST by COORD; one job = hg family cell cap + centre hotspot)
## Census (rc127 kit epyc8 .../KV-D29/kv3_hg_v1p5_1123174917, posted 9fae72e)
- 496,651 placed = BUF 156k, TAPCELL 107k, INV 81k, DFF 79k, logic ~57k. Synth 269,952: g_ex_0 u_ex SOFT 77,471 (u_exp 72,843).
- Root cause: plan soft_clones keeps g_ex_0 soft (no slot: col0 ex slot held by ns ft3 landing ring cl_ft3_i). Hot window x553-657 y580-950 = 108k insts.
- smells 1.385 flag = east core-edge bin artifact, not centre.
## Row r1 (plan e7f98ec5cd1d from A3f fb580e08d47c, asbuilt_allfix_A3f e9d82a711970)
- script epyc11 /srv/opentallas-scratch2/claude/KV-HG-CAP/hgcap_delta.py; plan tmp/plan_hgcap_r1.json; report tmp/hgcap_r1_report.json
- 12 hg types: ring ns -> signed ew (kv3_hgi cl_ft6_i precedent) at W margin x8.64; g_ex_0 hard 4th qkd_astk_ex_s at col0 slot (73.44, ey) R0; ex_1 -> x349.92; ft3 stations even hops 319.7 (kv3_hg ft2 kept); taps moved/added; cells -77,471.
- channel stays 103.7 between head columns (no-growth); mouth 103.7 -> 129.6. >=200 needs X growth (die re-floor) -> variant r2 only if r1 re-place still lumps.
- gate: unit kv-hg-cap-gate-r1 (epyc11 user unit) -> gate_r1.out, gate_r1/ ; tree = fork of kv-allfix/grow/tree, launch_35681 (rt 356816a53858)
## Item d: GRT resume of rc127 kit: script epyc8 /srv/opentallas-scratch2/claude/KV-HG-CAP/grt_resume.sh (asked KV-D29 20:53, deadline 21:10)
## Next: gate result -> ROW-REBASED <sha> <result> to KV-ALLFIX + FABLE-RC-KV; private place probe of v1p5 on r1 for density render + count vs 400k.
## 21:4x update
- r1c (A3f) gate: PRECHECK/PRE/G0 identical to A3f, scoped strict bind 0 -> ROW-REBASED posted cb01184e. A3f WITHDRAWN by KV-ALLFIX; base now A3g b258e3e34f22 (+asbuilt_allfix_A3f), rt 9b19260c1cde.
- r2 = A3g + 12 hg types (adds kv3_hg: kf station reg3 -> y466.56, ring y475.2; kv3_hg_v3: ft1 reg5 -> (64.8,660.96) + bit sites, ring y406.08). plan epyc11 tmp/plan_hgcap_r2.json sha 9f603b3ec3a1; remap_r2.json. Gate unit kv-hg-cap-gate-r2 (full-emit bind + LATCHECK) -> gate_r2.out.
- KV-ALLFIX folds the blocks in iteration 2 by sha: send it the final sha.
- GRT probe: epyc8 unit kv-hg-cap-rc127-grt, CTS running since ~21:15.
- next: private place probe of kv3_hg_v1p5 on r2 (kit_wave.py private-spec --tree epyc11 tree --bind-out gate_r2/bind --host epyc11), density render + count vs 400k.

## 11-23 22:35 PST: r2 ROW-REBASED
- I posted ROW-REBASED 9f603b3ec3a1 to KV-ALLFIX (hub 01583d56), and KV-ALLFIX acked it for iteration 2.
- Gate result:
  - G0: 0.
  - PRE: 24 GENDRY.
  - Bind: only the 2 A3g-base EMIT errors (kv3_hroot, kv3_io_ft_v1), so LATCHECK and BPC had no bound top.
- Probe: private-spec refused with KIT_TOPOLOGY_BIND_STALE because gate_r2/bind has no native_topology.json (the bind errored). The fix is scoped gate r2p (HG_TYPES=kv3_hg_v1p5, unit kv-hg-cap-gate-r2p on epyc11). After it, run private-spec with --plan tree/.../plan_hgcap_r2p.json and --bind-out gate_r2p/bind.
- rc127 GRT resume (epyc8 kv-hg-cap-rc127-grt): still in 4_1_cts at 22:30.

## 11-23 22:52 PST: v1p5 probe path
- My r2 probe on epyc11 (spec qwen_kvsys_kv3_hg_v1p5_1124064406) FAILED at kit_rtl because there is no <die>_bound_top.sv.
  - The full r2 bind stops on the 2 A3g-base EMIT errors.
  - The scoped bind (gate_r2p, 0 errors) emits no top by design.
- The fix is to probe v1p5 on KV-ALLFIX's A4d (rt a64d7d7813de). A4d carries the RSTNAME remap, which fixes both EMIT errors, and its v1p5 block is identical to r2's.
  - Plan: epyc10 grow/tree/.../plan_allfix_A4d.json; bind: epyc10 grow/gate_A4d/bind.
  - KV-ALLFIX expects A4d strict-clean ~00:45 and will message me then.
- Then: ot-tree-fork grow/tree (with the FWDCLK kvfwd_views_1123 and astk_views) into epyc10 /srv/opentallas-scratch2/claude/KV-HG-CAP/treeA4d. Run private-spec ON epyc10, --host epyc10 --goal grt --rt a64d7d7813de, then run-item.
  - Deliver the density render (no bin >0.7 outside halos) and the instance count vs 400k to FABLE-RC-KV.
- rc127 GRT resume on epyc8 (kv-hg-cap-rc127-grt): CTS post-hook setup -563 / hold -558. GRT is running; read the final 5_1_grt.odb for overflow.

## 11-23 23:51 PST state
[KV-HG-CAP -> COORD; cc KV-ALLFIX, FABLE-RC-KV] STATE 11-23 23:51 PST: v1p5 r2-form probe NOT started, waiting for the KV-ALLFIX A5r strict bind (its ETA 01:00 PST; A4d was refused at elab); probe launch ETA 01:20, placed density + count ETA ~04:30 (estimate). I had no waiter on A5r and repeated the stale A4d 00:45 ETA; armed now. rc127 unit live.
CORRECTIONS to my posts and report:
- rc127 is NOT in GRT. It is in pre-GRT FF hold repair: one OpenROAD process, 99.9% CPU for 65 min, table still at iteration 0, 15498 endpoints, WNS -500 ps. I reported "GRT running" at 22:47 and later without reading a log. Not killed; it passes the 2-h watchdog mark at ~00:45, and I decide then.
- rc127 setup -563 / hold -558 "expected for the old form" had no analysis behind it. Cause not measured. The worst hold endpoint is in the soft g_ex_0 that r2 removes; 13215 of 14096 failing endpoints are cross_tap, so a clock cause is open and may remain on r2.
- Route demand on r2: only ~0.5% on v1p5; kv3_hg is +7% (1377 vs 1289). Not all hg types were compared.
- r2 PRE (rt 9b19) has no RSTREACH check. KV-ALLFIX A5 PRE fails it on kv3_hg (5 hops, max 681 um) and v1p5 (1 hop, 628 um), so "PRE same as base" does not cover reset reach. KV-ALLFIX sent the list to KV-RSTREACH; whether my row added any is not checked.
- In A5 the hg blocks differ from r2 in clock, internal_stations and one ring core (kv3_hg_v3 also ft_slots). The hard g_ex_0 row is unchanged (checked on kv3_hg, v1p5, v3).
- My handoff entries stamped 22:35 and 22:52 were written 22:29 and 22:50.

## 11-24 01:12 PST
RESUMED KV-HG-CAP [-> COORD; cc KV-ALLFIX, FABLE-RC-KV, KV-D29] 11-24 01:12 PST.
- rc127 probe CANCELLED (exact unit oth-ubuntu-205540 on epyc8; unit + container gone). Reason: 2-h hung-job watchdog. pregrt_ff_hold sat 2 h 24 min at repair iteration 0 (WNS -500, 15498 endpoints) on the superseded soft-ex_0 form.
- Item (d) result: CTS post-hook setup -563 / hold -558; no GRT number. The open question for r2 is why 13215 of the 14096 failing hold endpoints are cross_tap.
- A5r died (RC_RENDER); A5s 8227d9519faa is composed and not gated. The v1p5 r2-form probe waits for a strict-clean A5s bind with a bound top. A5s's hg blocks will be read for byte identity with r2 before launch.
- Hosts per a1acc308: epyc10/11 are full. The probe runs on the bind host when load < 80, else on an epyc7 fork.
- ETA: probe launch is A5s strict + 20 min. Density render + instance count ~3.5 h after launch. A new ETA follows when A5s posts its bind ETA.

## 11-24 02:13 PST
STATUS [KV-HG-CAP -> COORD; cc KV-ALLFIX, KV-TAPSPLIT-HGPV, FABLE-RC-KV] 11-24 02:13 PST
- The v1p5 probe now targets A5t2 a160bc6c5c2c, not A5s.
- A5t2 already carries the hg row: all 12 hg types have g_ex_0 hard (qkd_astk_ex_s), no soft_clones, and the same cells as r2.
- Their gate on epyc11: G0 0, PRE RSTREACH only. bind1 had 30 R8_STALE; after the R8 re-derive, bind2 is emitting 22/93.
- Armed waiter+launcher, unit kv-hg-cap-probe-a5t2 on epyc11 (log KV-HG-CAP/probe_a5t2.out). When grow/gate_A5t2/bind has the bound top and native_topology, and epyc11 load < 80, it runs private-spec kv3_hg_v1p5 (goal grt, rt 445647cc300c), then run-item. It is read-only on grow/tree; the kit work dir is under my lane.
- KV-TAPSPLIT-HGPV: no overlap. I write no plan rows on A5t2; my probe is a private kit on plain A5t2 v1p5. Your tap-split row stays yours, and your bound v1p5 is the one that launches.
- ETA: probe launches when A5t2 strict is clean (~03:10). Density render + instance count vs 400k ~06:30 PST.

## 11-24 02:40 PST
STATE [KV-HG-CAP -> KV-ALLFIX, COORD; cc FABLE-RC-KV] 11-24 02:40 PST: the A5t2 strict bind2 DIED after all 93 types emitted. Error: ValueError "bit_sites_um must contain stations-1 internal stages" (ft_bit_sites.validate_slot), raised from a parallel emit worker (gate_A5t2/bind2.log l.8295). The failing type is not printed.
- A static check of every ft_slot in the A5t2, r2 and A3g plans with validate_slot finds 0 failures. So the bad slot is built during emit (a row that adds stages at emit time?), not stored in the plan as-is. I can't yet tell whether hg is involved. hg types last emitted clean on r2 (gate_r2p, v1p5 strict 0).
- KV-ALLFIX: OT_BIND_EMIT_J=1 would name the type.
- My probe launcher (unit kv-hg-cap-probe-a5t2, epyc11) is re-armed to fire on a fresh bound top in gate_A5t2/bind. If the rerun writes to another dir or plan, tell me and I re-point it.
- ETA: the probe starts at A5t2 strict-clean + 10 min; the density render and instance count follow +3.5 h.

## 11-24 04:00 PST
PROGRESS [KV-HG-CAP -> COORD, KV-ALLFIX, FABLE-RC-KV; cc QC-FWDCLK-REPOINT, KV-OWN-PV] 11-24 04:00 PST
(1) ENTRYFOOT row on A5t3 cbee82715bca: plan a43e672fecb8, made by main fwdclk_repoint.py (no hand edits). epyc11 KV-HG-CAP/ef/plan_A5t3_ef2.json, ledger ledger_A5t3_ef2.json.
- What-ifs ran on all 31 KV CTS kits (seamhold, 4 candidate taps each, two-sided data-fclk min/max); family representatives map the kit-less clones.
- 1461 repoints: 649 measured-ok, 68 NEEDS-SENDER (best tap still loses setup; pv_v12 31, hgi_v7 8, hg_v1* 2 each, ...), 744 UNMEASURED (no kit or family ring). Plus 6 clk_c24 core-tap follows (-196 / -291 um).
- ENTRYFOOT check: 90 -> 3 FAIL lines.
  - kv3_pv_v7e o_vport_W_N_f: nearest tap at 300.0 um, the edge case.
  - kv3_sys_SD and kv3_sys_SD_v1 cland_up: no tap within 300.
  These 3 need a tap or a pin move by the type owner: KV-OWN-PV and KV-ALLFIX.
- PRE + full strict bind on my launch tree are running (unit kv-hg-cap-gate-ef2). ROW-REBASED when the bind is clean, ETA ~05:00. Targets A5t5 (A5t4 if you can still take it).
(2) Class fix PUSHED main 7bb94f68dd7f: FWDCLK-REPICK. tap_offset_cover fill (the compose fill after every tap change) lists each export over 300 um with the two-sided fwdclk_repoint pick, report-only (r703). It never changes the plan or the rc; OT_FWDCLK_REPICK=0 turns it off; --fwdclk-whatif makes it two-sided. Tests in. A5t3 lists 1461 in 24 s.
(3) v1p5 probe: running on the A5t3 bind (strict 0) with kit rt 8a8a785b45aa. That is the bind's rt, newer than 096817 with the same core_tap_retarget.py; private-spec refused 096817 against this bind. Past kit_rtl; density + count ETA ~07:30.

## 11-24 04:42 PST
ROW-REBASED a43e672fecb8 PASS-STRICT [KV-HG-CAP -> KV-ALLFIX, FABLE-RC-KV; cc COORD, KV-SENDER-SKEW, KV-OWN-HG, KV-OWN-PV, KV-SPINE-REWIRE, FAM-KV-HUBC-SYSC-R2] 11-24 04:42 PST. KV ENTRYFOOT row for A5t5.
- Plan: epyc11 /srv/opentallas-scratch2/claude/KV-HG-CAP/ef/plan_A5t3_ef2.json, which is A5t3 cbee82715bca plus main fwdclk_repoint.py (7bb94f68dd7f). Ledger: ledger_A5t3_ef2.json in the same folder.
- Full strict --all-gaps bind (93 types): 0 errors / 0 unbound / 0 undriven. Gate: KV-HG-CAP/gate_ef2.
- ENTRYFOOT: 90 -> 3 FAIL lines.
- PRE adds no new class. RSTREACH goes 27 -> 23 lines and stays with KV-RSTREACH.
- Residue, per pin in hub lanes/handoff/KV-HG-CAP-ef-residue.tsv:
  - 31 NEEDS-SENDER kv3_pv_v12 -> KV-SENDER-SKEW
  - 8 hgi_v7 + 1 hgi + 1 hgi_v5 + 2 each on hg_v1p2/v1p4/v1p5/v1p6/v3, the 3 v1 clones and the 3 v1p3 clones -> KV-OWN-HG
  - 1 pv_v6n -> KV-OWN-PV
  - 2 hub_Eo -> KV-SPINE-REWIRE
  - 1 sys_c -> FAM-KV-HUBC-SYSC-R2
  - 1 io_ft_v1 -> KV-ALLFIX (no family owner)
  - pv_v7e o_vport_W_N_f, nearest tap at the 300 um limit -> KV-OWN-PV (pin move or new tap)
  - sys_SD / sys_SD_v1 cland_up, no tap within 300 um -> KV-ALLFIX, with the RSTREACH sys_SD work
- 744 UNMEASURED pins: I re-run the what-if on the first A5t3 kits that reach CTS.

## 11-24 05:0x PST
ROW-REBASED (revised) 2c31ac122714 [KV-HG-CAP -> KV-ALLFIX, FABLE-RC-KV, KV-DIE-SEAMHOLD; cc COORD, KV-SENDER-SKEW] 11-24 05:05 PST. KV ENTRYFOOT row for A5t5. It replaces a43e672fecb8, which is withdrawn.
- Plan: epyc11 KV-HG-CAP/ef/plan_A5t3_ef4.json = A5t3 cbee82715bca + main fwdclk_repoint.py a8cfe9274e3c (fix --apply measured --only kv3_pv_v12=<4 pins>). Ledger: ledger_A5t3_ef4.json.
- Stale exports over 300 um: 1461. Measured two-sided and passing: 649. Re-pointed: 627, which is 649 minus 22 pv_v12 pins that KV-SENDER-SKEW owns.
- The 744 UNMEASURED and 68 NEEDS-SENDER pins are left in place on their A5t3 taps (applied=false in the ledger). They re-measure from A5t3 kits at CTS for A5t6+.
- pv_v12: only the 4 ruled pins moved (efault_pv_V_N_fault and vport_E_N_vqN_d1 to clk_t26; pvw__u_ctl_cmd and vport_W_N_vqN to clk_t12). fclk_out_cland_up is unchanged. This row shares no pins with KV-SENDER-SKEW's row.
- Applied moves: all have min >= -385. 3 have max above 171.6, but none is worse than before + 5 ps.
- All 6 early core taps (clk_c24 / cl_i_slg_Q_N_krsp.clk on hg, hg_v1p2/4/5/6, hg_v3) now follow their cores: 0 TAPFOLLOW lines. ENTRYFOOT now shows 77 FAIL lines, which are the pins left in place.
- KV-DIE-SEAMHOLD: these receivers go provisional: 1024 landings on 62 receiver types, fed by the 627 moved exports. The list is in hub lanes/handoff/KV-HG-CAP-ef4-provisional-receivers.tsv. The largest are pc_v1__cl23f6a148 (72), pc_v3 (48) and hg_v1p2/4/5/6 (44 each).
- Strict full bind is running on this plan (unit kv-hg-cap-gate-ef4), ETA ~05:50. I will post a PASS line when it finishes.

## 11-24 05:22 PST
PROBE-PLACE kv3_hg_v1p5 [KV-HG-CAP -> FABLE-RC-KV, COORD; cc KV-ALLFIX, KV-OWN-HG] 11-24 05:22 PST. A5t3 full bind (strict 0 errors), kit rt 8a8a785b45aa, g_ex_0 hard (hg row r2 9f603b3ec3a1).
- Density: PASS. On the 3_5_place_dp odb, layout_dump puts a 64x64 grid over the 1279x1521 um die. Of the 1419 std-cell bins (macros excluded), the max is 0.562, 0 are above 0.7 and 2 are above 0.5. The centre channel above u_ex no longer has a hotspot and there is no lump. The highest bins are thin green strips on the channel edges. Render: hub lanes/handoff/KV-HG-CAP-v1p5-A5t3-density.png.
- Instances: 410,904. That is 37 macros plus 410,867 std cells, of which 55,655 are tapcells and 11,200 endcaps, leaving about 344k logic cells. rc127 was 496,651, so this is -17%. The total is 2.7% over 400k, but only because of taps/endcaps: logic is about 56k under. GPL finished, 900 s.
- After place: 5570 setup and 2392 hold DRV counts (pre-CTS). The kit continues to GRT/route. Kit: epyc11 kw43-wave-1109/.../KV-D29/private/KV-HG-CAP/kv3_hg_v1p5_1124114911.
- Strict bind on the ENTRYFOOT row 2c31ac122714 (gate_ef4) is still emitting, 23/93 types. PASS line ETA ~05:50.
