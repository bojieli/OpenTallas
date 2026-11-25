# FIX-TRACE-1720: ALLFIX rows not marked IN-BASE, IN-COMPOSE or IN (11-24 17:3x PST, read-only audit)

Scope: every row in lanes/ALLFIX-S81.tsv, ALLFIX-QC.tsv and ALLFIX-KV.tsv whose status does not start with IN-BASE, IN-COMPOSE or IN. That is 118 rows: S81 40, QC 38, KV 40 (one KV row is the A4d header). Row numbers are tsv line numbers.

Verdicts:
- (a) in a later bound plan;
- (b) in a composed but unbound plan;
- (c) not in any plan;
- (d) superseded, withdrawn, or not a plan row.

## Bound plans used
- **S81 c8 = 9b25d6714339** (j9tail_c8/p6w_sg).
  - The c8 bind on rt 69de had errors. It was re-bound as c8s on rt 52c1, streaming per type.
  - The c8s full bind was OOM-killed at 15:06 PST (epyc9 bind_c8s.otrun.log, exit 137). At 15:00, 211 of 403 records were final.
  - Kits launched per type: 210 spec dirs in intel2 ~/tmp/s81int/c8s.
  - c8 is therefore only partly bound.
  - Evidence: epyc9 s81-allfix-int/tmp/applied_census_c8.json. Each step is old-checked against 9b25d6714339 (present/changes).
- **S81 c9 = 048fa468f0a2** (G0 PASS) and **c9s = 99f7d3042489**: the gate restarted 12:56 and is still in elab/strict, so not bound. c8r acded6da9daf was composed but no strict PASS was found. c10 exists only as rows.
- **QC**:
  - C1h 894e6f21991f, C1i 3e46ebd69a97 and C1j 7fbc73d3f7cf (strict PASS 11:55) are bound.
  - C1k (strict PASS 14:29, E7) is bound.
  - C1l 4f372c56ced8 failed PRE at 17:26 and is re-binding. C1m is composing.
  - Evidence: QC-ALLFIX posts 02:41 (C1h), 04:42 (ROW-APPLIED audit), 05:16 (C1i), and 16:11 COMPOSE-GUARD, which diffs C1k against C1g, C1h and C1j key by key.
- **KV**:
  - A5t5 669cbe6e39bd is bound: published-tree strict PASS 13:01 (93/93 types, 0 errors), wave event since 13:31.
  - A5t6 a498941539fd is composed; gate try 4 is running on E10.
  - Row lists: epyc11 kv-allfix/grow/a5t2.list, a5t3.list, a5t4.list; epyc9 grow/a5t5.list.
  - Key checks: A3g grow/A3g/plan.json against pub/kv_a5t5_tree/.../plan_allfix_A5t5.json, on epyc10.

## S81 (40): a 20, b 10, c 4, d 6
| line | item | verdict | evidence |
|---|---|---|---|
| 12 | rc25 LOSTART | a c8 | census step rc25_svc_lostart 416/416 present |
| 35 | rc67 | a c8 | rc67_hopsite_1 2/2 |
| 46 | x1 | a c8 (base B1) | in ALLFIX base B1 ae3101241d6b; census class UNCHECKED (no ops file) |
| 47 | hg-S81-CLOCK-SKEW | a c8 | tgr5_leaf_regen_1 686/704 (9 re-set by RSTREACH) |
| 48 | hg-S81-CLOCK-TAP | a c8 | tgr5_leaf_regen_1 |
| 53 | hg-S81-LOGIC-DEPTH | a c8 | rc37_lp_profile_1b 1/1 (OPEN-DEMAND outcome) |
| 56 | hg-S81-REACH | a c8 | base + tgr5_leaf_regen_1 |
| 57 | hg-S81-REPAIR-CAP | b c9 | closed by measurement; lepe_mu_LP t2 RTL row = c9 (unbound) |
| 60 | hop-S81-svc | a c8 | svc_frame_g0_v3 7452/7884 (432 ft sites ruled to HOPFIX) |
| 72 | B2-R3 | a c8 | svc_frame_g0_v3 |
| 75 | KVLEAF-VNB-HARD-1 | a c8 | kvleaf_vnb_hard_1_v2 358/358 + kvleaf_sta_unbury_1 219/231 |
| 76 | B1-G0-SVCFRAME-46 | a c8 | svc_frame_g0_v3 |
| 78 | SVC-CUT-FACE | a c8 | svc_frame_g0_v3 |
| 81 | ABI-RESTORE | c | abi_restore.json is not a c8 census step and is in no c9 post. Owner S81-ALLFIX-INT (alive, 17:28) |
| 84 | SERDES-RING-ONEGROUP | d | WITHDRAWN 04:50 (probe t2 hold -226 -> -645); in c8 22/22 but the 11 serdes types are HELD |
| 87 | KVLEAF-T2-HARD-1 | c | census: "accepted, never in any plan". The t2 D3 re-floor exists only as the provisional c9s-D3 row i027e 23f7e1c701d5 (not composed). Owner S81-KVLEAF-T2-ARCH (alive 17:13); R2 last posted 07:31 |
| 89 | SERDES-t13-FSTART0 | d | own row never delivered; the class is covered by tail_fstart 87/87 in c8 |
| 90 | FSTART-DEPTH-CLASS | a c8 | tail_fstart 87/87 |
| 92 | LEAF-LANDCAP-C7A | a c8 | 8f2a6b3cedb4 = leafband_resite_1 99/99 |
| 93 | LEAF-HOP-C4 | a c8 | pt_rthops_p1/p2 (hops 0) |
| 94 | LEAF-ANCHORDRY-7 | d | REASONED same-edge rename, no row; ANCHORDRY accepted in PRE |
| 95 | T2-AB-SPLIT | c | no A/B cut (INT ruling 21:54); the t2 contents row is in no plan (census planned-NONE). Owner S81-KVLEAF-T2-ARCH |
| 98 | RSTREACH-C8 | a c8 | pt_rstreach 499/499 |
| 99 | OVERHARD-FW0-C8 | b c8r | only in c8r acded6da9daf; c8s binds c8, not c8r |
| 100 | TYPEDEF-SELREP-C8 | a c8 (likely) | pt_defs_drop 75/75 (COORD default: remove on 10 types) |
| 101 | RTHOPS-98 | a c8 | pt_rthops_p1/p2 |
| 102 | RTHOPS-PERBIT-14 | b c9 | BITS row d3d6e6e041df -> c9 |
| 103 | GATE-C8-DEFINES | d | count gate condition, not a plan row |
| 104 | LKES0-AB | b c9 | c9 row |
| 105 | RSTHOLD-COUNTER | b c9 | in-die counter on c9; interim host rst_n contract on c8 |
| 106 | KIT-LAUNCH-C8 | d | not a fix; c8s kits launched 14:26 onward |
| 107 | C8R-GATE | b c8r | fix2 c8r, no strict PASS found |
| 108 | TAPOFF-SITE-C8 | b c9 | probe-only on c8; rekey goes in the c9 tail |
| 109 | LATDEF-C8 | d | count rule, not a plan row |
| 110 | SITEGRID-T31-C8 | a c8 | pt_t31_sitegrid 710/710 |
| 111 | LP-CORETAP-C9 | b c9 | 2ef1a5f50c30 line-append 80/80 on c9 |
| 112 | BKSEL-ETM-C9 | b c9s | lib swap into c9seal_tree 09:19, re-seal fa9585697566 |
| 113 | EXPORT-REPICK-C9 | c | dry run only (44 UNMEASURED); not composed. Owner S81-ALLFIX-INT (alive) |
| 114 | LEP-RIP-ROW-C9 | b c9 | composed with LP-CORETAP-C9 |
| 115 | FF-LIB-RESIGN-C8 | a (launch) | re-sign rides the fresh c8s kits; not a plan row |

## QC (38): a 27, b 0, c 1, d 10
The lineage evidence comes from posts. The C1k contents are confirmed by COMPOSE-GUARD 16:11: 9 adopted rows are present in C1k. The losses it found are r10 (restored in C1l) and three deliberate drops: HC1-CLKENTRY, the sle_ctl re-key 1d3b, and the coll_core reset re-solve.

| line | item | verdict | evidence |
|---|---|---|---|
| 2 | b25 successor | a C1h..C1k | compose A f418c1b290f3 lineage |
| 3 | x12 tapoff | a | in compose A |
| 4 | rc99 cb NK lockup | a | C4 row in cA; the cb probe is owned by QC-CB-PROBE/QC-CB-C1L |
| 5 | rc101 cb landing piles | a | as above |
| 6 | rc107/rc109 | a | in cA |
| 7 | coll_core 80 reset copies | d | coll_core reset re-solve dropped deliberately from C1k (COMPOSE-GUARD 16:11) |
| 8 | SLE CTL B_TW | a | in cA |
| 9 | SLE CTL clock entry (ctlclk) | a | C1-noSU 12b66c0e4829 carries ctlclk (04:42 audit) |
| 10 | rc105 su_c street | a | SU2R db537389cc92: 24 of 30 types byte-equal in C1h, 6 carry it plus later rows (04:42 audit) |
| 11 | SU-2 | a | as above |
| 12 | RED +2 | a | ov_red2 installed in the C1h overlay (02:41) |
| 13 | rc103 | a | in cA |
| 14 | hg-QC-HOLD-SKEW / RESET-ASYNC | a | B2 lineage |
| 15 | RSN FLT | d | kit rt fix, not a plan row |
| 16 | F16 | a | C1h F16 tie row; T20 core in C1j |
| 17 | TTC-NECK | a | B1 NECK lineage; tt_ctlm core in C1j |
| 18 | rc97 BT_LAT=2 | c | QC-ALLFIX 10:28: "never started"; no bt2 master in C1k, C1l or C1m. Owner QC-ALLFIX (alive) + FAM-QC-HCST-R3 |
| 19 | rc94/rc98 | a | in cA |
| 20 | x5 DPL-0033 | d | kit, not a row |
| 21 | CBN-RSF-SEAT | a | in C1-noSU (04:42 audit) |
| 22 | SUC-Q0 | a | in C1h (04:42 audit) |
| 23 | C1-noSU compose | a | lineage base |
| 24 | SU2R-FIX3 | d | superseded by FIX3v2 + FIX4 (in C1g/C1h) |
| 25 | SUL1-UNBURY | a | C1g/C1h |
| 26 | C1d | d | withdrawn |
| 27 | HC1-CLKENTRY | d | deliberately not adopted; superseded by the SEAT-MATCH re-key (04:42, 16:11) |
| 28 | C1e | d | withdrawn |
| 31 | C1d2 | d | superseded by C1g |
| 32 | C1g | a | base of C1h |
| 33 | DEADIN | a | C1h apply_deadin 20d75259cfb5 |
| 34 | sle_st_b_v2 ride | d | kit, not a row |
| 36 | C1h compose | a | bound |
| 37 | FWDCLK-REPOINT | a C1j | 05:16: late for C1i, so C1j |
| 38 | QC-SC-FARRST | a C1i | 1dfd9d3d7464 (C1i compose 05:16) |
| 39 | sle_ctl re-key 1d3b | d | in C1i, deliberately dropped from C1k (COMPOSE-GUARD) |
| 40 | sle_sc_v3 stations | a C1j | QC-OPEN-SU e1254b6b9eb4 -> C1j; also signed on the QC-OPEN-SU private plan |
| 41 | QC-RSTCNT | a C1j | 9cb276998d14 -> C1j |
| 42 | FWCPL-2 | a C1i | 02ddf1a18df7 (9 fw) |

## KV (40, of which line 34 is the A4d header): a 27, b 0, c 8, d 4
| line | item | verdict | evidence |
|---|---|---|---|
| 3 | SYSC-D2DOUT | a A5t5 | in A3g lineage (RECON 22:49); 4 S3 bits still REASONED-pending |
| 5 | PCGUTKEEP | a | A1 -> A3g |
| 6 | G2 pcc seam | a | PCGROWDIE in A3g |
| 10 | PCPO3 | a | A1 |
| 14 | rc127 HGFORM | a | K3g base 324af451f9be -> A5t5; hg holds lifted 13:31 (74033e14); probe still owed |
| 16 | hg_v1p2 | a | same |
| 22 | x10 tap offsets | a | A1 |
| 24 | TAPGRID pv_v3e | a | A1 |
| 25 | TAPGRID pv_v1n | a | A1 |
| 26 | HUBC-E2 | a | A3g |
| 27 | H2 RSTCL / H3 SEQE | a | A3g |
| 28 | R8 type split | a | R8SPLIT in A3g |
| 29 | PCGROW | a | PCGROWDIE 84141a5187ca |
| 30 | D38BR | a | A3g |
| 32 | PCGROWDIE | a | A3g |
| 33 | ADV-PORT-PIN | c | no row in any list (only hub_Wi via PORTPIN). Owner KV-ALLFIX (alive) |
| 34 | (A4d header) | - | - |
| 48 | KV-HG-CAP r2 | a | SPLICE-HG2 92c630137c96 in a5t3.list |
| 51 | RCOLL | d | superseded by RINS |
| 56 | EARLYTAP/ASTKTAP | d | superseded by AE1 e06290feabeb (which is in A5t5) |
| 58 | PORTPIN-HUBWI | a | d628d562a06d in a5t2/a5t3; hub_Wi reset_spine_pins 142 (A3g) -> 156 (A5t5) |
| 59 | TAPSPLIT | a | TAPSPLIT-RD 8f1f158a5632 (re-derive of 874a8f84c7ee) + TAPSPLIT-HGPV 6d4807c970f2 in a5t5.list |
| 60 | FTLOCKUP | c | in no list a5t2..a5t5 or A5t6; clock.ft_hop_lockup byte-equal A3g vs A5t5 (types [kv3_io_ft_v1] only). Owner KV-ALLFIX (alive) |
| 61 | RREACH v2 | a | e28ef6cafd32 + RREACH-EXCL + ISTSITES in a5t3 |
| 62 | STREETSTN | a | ae8fb066997c in a5t5 (C2T2); "street" key count 574 -> 698 |
| 63 | HUBCTAP | c | in no list incl. A5t6. Owner KV-ALLFIX, which owns hub_C (alive) |
| 64 | DLYAP R1 | a | fee13023181e in a5t3; dly_alt_pol keys 0 -> 31 |
| 65 | KV-RSTREACH leftovers | c | A5t5 PRE still has 21 RSTREACH findings; no row in A5t5 or A5t6. Owner KV-OWN-RSTREACH (alive 17:24); KV-RSTREACH last posted 07:30 |
| 66 | RING-RSTFAN | c | no row. Owner KV-OWN-PV-R2 (alive 14:40) |
| 67 | KV-OPEN-INCORE | a | INCORE-R2 67e32f55dcee in A5t5; "incore" keys 0 -> 4 |
| 68 | KV-DIE-SEAMHOLD | a | dddecdff1714 in a5t2/a5t3; ring_hold.sender_ps_types 4 -> 90 types |
| 69 | KV-HUB-EPZO | c | ROW NONE. Owner KV-HUB-EPZO, last post 11-23 21:29 (DEAD); KV-HUB-HOLD 22:55 (DEAD) |
| 70 | HUBA1 | d | pulled |
| 71 | STRIPRAW | d | dropped, replaced by RSTNAME-REMAP (SPLICE-R1) |
| 72 | KV-PV-RSTRELAY-v3 | c | rows/ROWS_KV-PV-RSTRELAY.py exists on epyc10 but is in no list or A5t6. Owner KV-PV-RSTRELAY, last post 11-23 22:59 (DEAD) |
| 73 | KV-DIE-SEAMHOLD (A6 dup) | a | already in A5t5 (line 68) |
| 74 | FTLOCKUP (A6 dup) | c | as line 60 |
| 75 | STREETSTN (A6 dup) | a | as line 62 |
| 76 | TAPSPLIT-HGPV | a | 6d4807c970f2 in a5t5.list |
| 77 | INCORE-R2-B1 | a (likely) | INCORE-R2 67e32f55dcee in A5t5; the B1 variant was not separately checked |

## (c) rows: 13
- **S81**: ABI-RESTORE, KVLEAF-T2-HARD-1, T2-AB-SPLIT, EXPORT-REPICK-C9.
- **QC**: rc97 BT_LAT=2.
- **KV**: ADV-PORT-PIN, FTLOCKUP (twice), HUBCTAP, RSTREACH leftovers, RING-RSTFAN, HUB-EPZO, PV-RSTRELAY-v3.
- **Dead owners**: KV-HUB-EPZO, KV-PV-RSTRELAY.
