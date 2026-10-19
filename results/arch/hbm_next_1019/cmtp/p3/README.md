# HBM-NEXT P3-CMTP: compiler images, goldens and price at P = 3 (owner decision 0le, 10-19)

Lane HBM-NEXT-P3-CMTP, 2026-10-19. The next-release HBM die is P = 3 position lanes with a shared 3-lane x store (P3+(a)), replacing P = 4. Tools: `tools/hbm_next/` at claude/hbm-next-cmtp-1019 @1e9ef4076 (step 6: one VM map, image_check), plus this step's changes:
- `static_check.py --P`;
- the `fused_tree` and `sm3` re-time keys;
- the defaults moved to P = 3: `isa_rows.P_LANES`, `emitter --P` and `static_check --P`. The isa_rows selftest still runs its P = 4 rpl vectors and PASSes. Fleet tree: ot-epyc7 `/srv/opentallas-scratch/claude/hnx-cmtp4/optp3` (= opt6 + those two edits).

## 1. Images at P = 3 (`emitter/`) -- VEH input

`emitter.py --P 3`. Whole-token images (`emitter/whole/<mode>_N<n>/`), 40 layers + head, one VM map. CANDM (the layer-20 carried value) is pinned as in step 6. Every image has 0 failed records and 0 emit errors.

| image | records | bytes | VM need (2^19 = 524,288) | sha256 | vs P = 4 image |
|---|---|---|---|---|---|
| ar_N1 | 3,954 | 470,976 | 99,200 | 09b394e917ba | identical (AR is P-free) |
| mtp_N6 (2 full passes of 3) | 3,715 | 516,304 | 506,112 | fc4429481250 | differs (no remainder split; rpl 0) |
| mu_N1 | 3,955 | 471,056 | 99,232 | ae4ef0c90c26 | identical |
| mu_N2 | 3,595 | 498,928 | 187,040 | c8c3c44d2955 | differs (no rpl) |
| mu_N3 | 3,595 | 498,928 | 264,256 | e807cb37a0f7 | identical (1 pass at both P) |
| mu_N4 (4 users on 3 lanes = passes 3 + 1) | 3,715 | 516,336 | 351,712 | d4bb66ec494b | differs (2 ATT plan passes: 3,595 -> 3,715 records) |

The per-layer images are L0/1/2/3/14 (`emitter/{ar,mtp,mu}/`). They have 0 failed records. Peak VM need is MTP 481.5k, users N = 4 335.3k and AR 95.1k, all within 2^19.

**Checks**
- **Image check** (`image_check.json`, `image_check.log`; the P is read from emitter.json and equals 3): I1-I6 PASS on all 6 images. U_max is 36 for MTP and 12 / 18 / 24 for users N = 2 / 3 / 4. Every KVUNION has budget 128 and NL <= 3. The 5 mutants fail as witnesses: wrong count word, KV budget 256, wrong rtab, lost END and VM past 2^19.
- **Compiled-programme check** (`static/`, `static_check.py --P 3`): 123 / 123 segments PASS on C1 unit collision, C2 RAW/WAW/WAR, C3 rows and C5 ring for MTP, users N = 4 and AR. The unit_double_book, raw_early and ring128 mutants fail as witnesses (AR has no ring).

## 2. Goldens: none depend on P (`../goldens/p_dependence.json`)

The goldens use hdc_golden_v41 chunk8, whose reduction order is fixed by the golden. Every committed array is a per-position or per-user, per-layer activation, with no lane dimension. At P = 3 each lane computes whole position rows: MTP N = 6 runs as 3 + 3, draft N = 5 as 3 + 2 (rpl 0), and users as 3 + 1. So `ar_mtp_g5`, `mtp_all5` and `mu4` stay as committed: no regeneration and no fleet run.

## 3. Price at P = 3 (`retime/rp_P3a_u{4,3}_{mean,ub}.json`)

The price uses `plane_compiler.py meas --step5 [--union-bound]` with ALL measured v2:
- IDXN 1,297 + 232(N-1);
- SU.VOP 28 / 56;
- ARGMAX 22;
- FUSED 81 / 103;
- HC 250;
- IDX.TOPK / UNION;
- KVWB;
- COLL rows / ARGMAX_MERGE;
- ATT4;
- SM4 skew;
- VM 2^19.

"Frames" adds the measured first-row costs: IDX 1,297 and FUSED c1 404 / 196. "Die tree" adds `fused_tree` from P3-DIE f4c_t9p3: +37 cycles on the first row of every FUSED record. "SM P3 tile" adds `sm3` from P3-SM hnx_rp3lp3x @217fff8b6: +4 cycles on every SM.MATVEC record and x1.008 on N-row SM records (the worse, K4 throughput figure). The die is P3-DIE f4c_t9p3 at **767.41 mm2**.

P3-UNITS (@712500e6e) found that only ATT4 depends on P among the non-SM units. The ATT4 row form at NL 3 is unchanged (fixed ~113-127 + 7.8 per union row), so the compiled ATT price stands. The `att4` key keeps -40 a PV pass. Every other row II is N-only.

| case (P3+(a), DS, 1.2 GHz, 1M ctx) | AR | MTP mean union -> **reserved 6N** | 4 users agg / per user, mean -> reserved | 3 users agg / per user |
|---|---|---|---|---|
| ALL measured v2 | 1,949.7 | 3,390.1 -> 3,180.2 | 4,251.2 / 1,062.8 -> 4,191.8 / 1,048.0 | 3,855.8 / 1,285.3 |
| + die FUSED tree | 1,931.0 | 3,375.6 -> 3,167.4 | 4,228.9 / 1,057.2 -> 4,170.1 / 1,042.5 | 3,831.3 / 1,277.1 |
| + frames | 1,997.5 | 3,427.5 -> 3,213.1 | 4,224.7 / 1,056.2 -> 4,166.0 / 1,041.5 | 3,856.5 / 1,285.5 |
| + frames + die FUSED tree | 1,977.9 | 3,412.6 -> 3,200.0 | 4,202.6 / 1,050.7 -> 4,144.6 / 1,036.1 | 3,832.0 / 1,277.3 |
| **+ frames + die FUSED tree + SM P3 tile (P = 3 of record)** | **1,967.8** | **3,377.5 -> 3,161.2** | **4,159.5 / 1,039.9 -> 4,100.4 / 1,025.1** | 3,793.0 / 1,264.3 |
| targets | 1,905 | ~3,364 | ~4,365 agg / >= 1,000 per user | |

**Reading**
- AR and the per-user floor are met in every row.
- At the mean union, MTP is +0.4% over target (3,377.5).
- If the static calendar reserves the union bound U = 6N, MTP falls to 3,161.2, which is 6.0% under target. This is the open owner / PROG decision from step 6 (README sec. 10 item 3). Options: (a) accept the 6N reservation; (b) a union budget below 6N plus an E_RANGE fault and an AR fallback; (c) the CP issues records after the loop.
- The 4-user aggregate is 4.7% under the ~4,365 study figure (4,159.5). That figure was the P = 4 target; the owner accepted P = 3 on the basis of 4,251.
- The die FUSED tree costs 0.4-1.0%. The SM P3 tile costs 0.5% AR, 1.0% MTP and 1.0% 4-user.
