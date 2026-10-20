# HBM-XLP10 (10-20): pipelined x-load + x reuse, TOK.HDS.SMMV

Lane HBM-XLP10 (parent LEAD7-HBM). Branch `claude/hbm-xlp10-1020` (base origin/main 16f2703df). Follows HBM-SMMV9
b2ae8ec24 (model only), which projected DS 1,423.8 tok/s for a pipelined x-load and 1,445.7 with x reuse.

## Result
| census input (RATE8 main tools, `--measured --bw 98 --bridge 1`) | DS AR tok/s | Qwen tok/s |
|---|---:|---:|
| m_xl: my xl reruns, reproduces RATE8 m_all | 1341.1 | 1023.7 |
| m_xp4: pipelined x-load (SMB_XMODE xp, XAHEAD 4) | 1345.1 (+0.30 %) | 1023.7 |
| m_xr: x reuse (xlr, already exists) | 1352.6 (+0.86 %) | 1023.7 |
| **m_xpr: both** (dsA at SMB_FLAT 280, dsB at FLAT 200; each run PASS) | **1356.1 (+1.12 %)** | 1023.7 |

Measured gains are far below the SMMV9 projection. Most small dense DS records are RAW: their x is produced just before
them (x_raw in sm_runs/*.json: wq_a, wq_b, wo_a, wo_b, router, w2 head records). A RAW x-load must wait for its
producer, so pipelining cannot overlap it. On the non-RAW records the binder becomes the routed FETCH law (400 per 2-block
w1+w3 record) and the HBM residency, not the loader. XP on its own is under the 1 % adoption bar (AGENTS no-risk rule).
Qwen is unchanged because every Qwen SM record is RAW. The next DS lever is not the loader: it is RAW x latency (an op
that starts on the first landed x words) or RFETCH.

## 1. Pipelined x-load RTL (new modules; the cl2 / xql files are byte-identical, so the CLOSED ctlx views stand)
- `rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_cl2xp.sv`: `ot_hgi_sm_xload_cl2xp_ctl/_ctlw/_ctlx`.
  - x_busy falls on the LAST ISSUE EDGE, so the next command may start on that edge and the issue runs back to back.
  - The issuer `active` follows x_act (a count of loads in flight up to x_done).
  - These per-wave bits ride md / L / C / tag: bdm, the BD tpair-last bit, and the BF go marker with its 3-bit load id.
  - The per-load egress fields {bdf, la8, P, gn|gtp, xb} sit in an 8 x 23 b context ring written at start.
  - The BF emission launches from the go marker: a 5-stage go pipe gives the same edge as cl2's `tc == em_off`.
  - BD loads queue in start order and load into the ring engine when it is free or on the previous load's final tail.
  - x-store rows and the BD write/emit tpair counts run continuously.
  - Sticky faults: a command while issue is busy or its slot is live, a launch over a running emission, a full BD queue,
    or a BF/BD egress collision.
- `ot_hgi_sm_xload_static_xqlp.sv`: the xql binding with the XP ctlx.
- Compiler law: at(i+1) = at(i) + max(ISS(i), LAST(i) + 1 - FIRST(i+1)). ISS = BF 8 nb gn, BD wb gtp. At P 1 that is
  CAD x beats, and it is the XLAT model in `smb_unit.py`.
- Bench `tb_hgi_xload_xpipe.sv` / `run_xload_xpipe.sh` (Verilator 5.050). The XP xqlp runs all 24 commands from one
  calendar at the law's slots; the cl2 xql runs each command alone. RD_LAT is the BUDGET vector on NE lanes + pads.
  - Commands: 12 DS production shapes (P 1, K 512..7168, BF16/FP8/FP4 transitions) and 12 random ones (P 1..8).
  - PASS: 1888/1888 beats equal in edge, addr, grp and 2048 data bits; 24 x_done; no fault. The span is 3,780 edges
    against 5,705 serial, and 23/23 slots overlap the previous load. Seeds 11, 12 and 13 all PASS.
  - Mutants: EARLY 1 (compiler fires one edge before the law) FAIL, 92/1888 beats then fault. DMUT 8 (the egress xb
    does not ride) FAIL, 280 mismatches. Witnesses are in witness/.
- Kit `physical/ref_tile/hgi_sm_xl2_ctlxp` is a variant of the CLOSED hgi_sm_xl2_ctlx_bl (same floorplan, pins, CTS,
  RD_LAT). **Gate FAIL at the pre-gate native32 census, so it was NOT submitted.**
  - XP: 153 nets above 32 loads (max 2,158, rq_n). The same flow on the CLOSED cl2 ctlx function (scratch kit) gives
    135 nets (max 1,797). The closed view predates the 10-19 census rule. See native_census/ for traces.
  - Inherited: rq_n reset 1,797 loads; 88 kept rotation-select replicas at 118-513 loads (NR 32, 64 b x 8-way each);
    the issuer `ot_static_cmd_target_core` cfg-hit / table-write / cycle-compare nets (526, 240, 112, 96 ...); and the
    start / c_bad / bi_on / iss_on / bdm / l_rem enables.
  - XP adds about 18: em_lid (156 / 80 / 40), gp_v[4] 67, id_w compare, the bq_id / bq_rp / bq_n FIFO read, and the reset
    growth from md +5 b.
  - Hardening any ctlx change therefore needs a census-clean ctlx successor first: one-hot registered select replicas
    (NR 64 x 8 b), regional reset leaves, replicated enables, and a census-clean issuer core variant. That redesign is
    owed and not started; at +0.3 % it is not worth it for XP alone.
- Safe-design checklist (the RTL is a new ctl variant; the floorplan is the closed one):
  1. Pins: unchanged and registered (PASS).
  2. Reach: same floorplan (gate not reached).
  3. Fanout: FAIL, as listed above.
  4. Depth: unchanged except the lctx 8:1 mux (gate not reached).
  5. Storage: the ctx ring is 184 b of flops (< 2 kb, PASS).
  6. Floorplan: copied.
  7. Clock: unchanged single root.
  8. Schedule: static, faults instead of stalls (PASS); every edge is the compiler law above.

## 2. x reuse (existing compiler xlr + RTL XSLOT/OPEN_IL)
xlr already reuses x for routed w1+w3: slots 1..5 read slot 0's x on L00/L02/L14, plus wkv and wq_b. xr_dsA 17,987 /
xr_dsB 21,679 PASS bit-exact (= SMXL2). Mutant SMB_MUT=xr_any (reuse any resident x of the same footprint) FAILs
numerically: mxra_dsA 34/42 and mxra_dsB 21/24, with GO exact. It needs no RTL beyond l24 (svg XSLOT=1 OPEN_IL=1, already
handed to HBM-DIE7). The die compiler uses SMB_XMODE xlr (or xpr once the XP ctlx is bound).

## 3. SM runs (sm_runs/, tb_toksim_smhbm MC3, FETCH 200, census rows; knobs = SMXL2 xl_ds*_f200)
| run | dsA (L00, L02) | dsB (L14, head) |
|---|---:|---:|
| xl (SMXL2 repro) | 18,429 PASS | 21,941 PASS |
| xp, XAHEAD 1 (cl2-equivalent rule) | 18,429 | 21,941 |
| xp, XAHEAD 2 / 4 / 16 | 18,184 PASS | 21,757 PASS |
| xr | 17,987 PASS | 21,679 PASS |
| xpr, XAHEAD 4 | FAIL: issuer late GO at 9048 (residency model) | 21,513 PASS |
| xpr, XAHEAD 4, FLAT 280 | **17,811 PASS** | 22,014 PASS |

The compiler residency model is not monotone in FLAT. xp and xr at FLAT 280 FAIL dsA, and OP_GAP 64 / RMARGIN 40 also
pass xpr dsA. The static schedule therefore needs a per-kind knob choice until the residency model is fixed.
`smb_unit.py` adds SMB_XMODE xp/xpr (opt-in; xl/xlr byte-identical in behaviour) and SMB_XAHEAD. Under XAHEAD the x-load
of record r may start at record r-j's first command when every writer of its A precedes r-j. That is needed because at
ISSUE_AHEAD 1 two x-loads never overlap, so the loader pipelining has nothing to hide (xp = xl measured).
