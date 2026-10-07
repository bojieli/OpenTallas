# Top-down timing budgets and the planned die clock (CLAUDE BUDGETS, 2026-10-06)

Owner-approved: chip-firm practice for the two open targets, the DeepSeek-V4.1 ROM S81 dies (case r9m215_v4) and the
HBM accelerator die (round r16j). Tools: `tools/budgets/` (README in `/tmp/claude-review-20261003/BUDGETS_README.md`).
Inputs and their source commits: `inputs/provenance.json`.

## 1. Die clock plan (`clock_plan/<die>.json.gz`, validated by clock-only CTS on EPYC3)

The plan follows option C of `results/uarch/rom_die_clocking_decision_20261003` (mesochronous regions with forwarded
link clocks):

- Root: the PLL outputs on the collective block.
- Trunk: one buffered H-tree per domain on M8/M9, from the PLL to every clock-region root.
- Regions:
  - S81: the 128 field columns, each a tree on M6/M7 from its column FIFO `co`.
  - Hub, spine, band and service sinks are grouped into regions of at most 4 mm, then merged along their synchronous
    nets up to 5.25 mm, the measured 60 ps H-tree extent.
  - HBM: the `clock_regions` of `hbm_accel_die_fp`, cut and merged the same way.
- Pads: every region root of a tree is padded up to that tree's slowest region tree.
- Forwarded links (S81 `fclk`, HBM r15 fwd segments) carry their own clocks and are not CTS trees.

Validation: one OpenROAD `clock_tree_synthesis` per die. Each partition clock pin is a sink (a DFF stand-in at the
generator pin). The run uses placement-estimated RC (M8/M9 trunk, M6/M7 regions) and SS/FF NLDM. Skew bounds are
CRPR-style: |nominal| + 5 % OCV on the non-shared insertion of both sinks, for every synchronous die net. Every case
fit in 0.33-0.74 GB, and CTS took 6-15 s.

| die | trunk insertion SS / FF (ps) | regions (trunk + field) | region intra bound (ps), max | inter-region pairs > 150 ps | meso wander (5 % x 2 x insertion) |
|---|---|---|---:|---:|---|
| HBM r16j | stream 2,689-2,695 / 1,426-1,429; hbm 2,192 / 1,163; link 1,281-1,285 / 679-681; serial 853-857 / 452-454 | 34 | 56.7 (budget 29-90) | 4 region pairs (6 sink pairs) | 270 ps < 417 ps (depth-4 FIFO) OK |
| S81 scan (layer) | stream 3,853-3,858 / 2,044-2,046; serial 977-981 / 518-519; hbm 1,627 / 863 | 54 + 128 columns | 45.2 trunk; 37.9 columns (column budget 59-63) | 7 (9 sink pairs) | 386 ps < 417 ps OK (tight) |
| S81 layer1 | stream 3,836-3,842; serial 960-964 | 47 + 128 | 50.0; 37.9 | 2 | 384 ps OK |
| S81 head | stream 3,859-3,863; serial 960-963 | 51 + 128 | 48.2; 35.4 | 6 | 386 ps OK |

Field column trees: 351-388 ps SS / 185-204 ps FF at the element pins (head 284-366 / 149-192).

**Plan targets.**
- Per region: the planned arrival at each partition pin (`regions.*.target_entry_insertion_ss_ps`, tolerance ±
  half-spread) and the region skew budget `intra_budget_ps`. The budget is the measured bound + 25 ps, capped at the
  owner's 90 ps, so every column and trunk region is tighter than 90.
- Inter-region: 150 ps.
- Per block (budget sheet `clock.entry_target_*`): region flop target minus the block's own internal insertion. The die
  tree compensates early or late entry; `die_pad_ss_ps` is the delay it adds over the CTS arrival.

**Flat versus hierarchical.** One flat balanced H-tree per domain (`clock_plan/<die>_flat.json.gz`) has about 2 ps
nominal skew. Adjacent sinks that split near the root still diverge by 5 % of about 3.9 ns, giving up to 401 ps
(S81) and 308 ps (HBM). That makes 56 / 39 / 44 / 144 intra-region violations. The hierarchical plan removes all of
them, and what remains are the crossings below.

**Synchronous crossings the plan cannot hold to 150 ps.** These need a forwarded clock, a meso FIFO or a region re-cut
(an architecture change).

| die | pair (bus class) | bound |
|---|---|---|
| HBM | `hb_vm` <-> `hb_index_{NE,SE,SW}_b5` (hub) | 198-268 ps |
| HBM | `hb_router` <-> `hb_vm` (hub) | 197 ps |
| HBM | `hb_cmdproc` <-> `hb_router` / `hb_loader` (hub) | 197 ps |
| S81 | `bk_selector` <-> `hix_{SE,NE,SW}` (local) | 382-385 ps |
| S81 | `bk_collector` <-> `hco_{SW,NW}` (local) | 383-384 ps |
| S81 | hub station pair `f_hb_gather_capture_7/8` at the spine region cut | 280 ps |
| S81 | `ctrl_*`/cks <-> `svc_*` (hbm_read) | 185-191 ps |

The `ctrl`/`svc` pair is resolved inside the 8.5 mm slabs by the S81-PH tiles: each `dsfd_ctrl_pc[p]` and
`dsfd_svc_pc[p]` abut on one leaf. The die model sees each slab as a single clock pin.

## 2. Budget sheets (`sheets/<master>.json`, `summary.json`, `SUMMARY.md`)

The sheets cover 257 hardened masters:

- **HBM:** 74 masters, all 71 masters of `physical/hbm_accel_die_views/index.json` plus the PHY / SerDes / host black
  boxes.
- **S81:** 165 die masters over the scan, layer1 and head dies.
- **S81-PH:** 18 placeholder tiles (selector, collector, capture, collective, ctrl, svc, VM, gather).

Each interface entry gives:

- length to the nearest register;
- skew class and term;
- SS input and output delay, with the fraction of T and the internal budget left;
- FF min delays: clk->Q 32.2 + 0.112 ps/um, and hold 15 - 0.112 ps/um;
- stages needed against planned (reach 412 um intra, 359 um inter, 491 um forwarded);
- pin registration;
- die fanout.

Each sheet also carries the block clock: the entry targets, and the internal insertion as a TARGET plus the value the
die compensates.

- Insertion **target** = min(430 + 0.865 sqrt(w h), 900) ps. The model is fitted to the closure-loop calibrations
  and Z20c, and is capped where a block's own OCV would use the 90 ps intra budget.
- Measured calibrations override the compensated value. Six blocks are over target:
  - `hfd_index_q_b0` / `b1` / `b2` / `b3` / `b5`, measured 1,132-1,324 ps;
  - `hfd_svc_SE_s0`.

**154 interfaces on 57 masters are infeasible as planned.** They need stations or architecture; `SUMMARY.md` lists
every one.

- **HBM: hub nets without planned wire stages** (1 planned):
  - `vm` <-> `index_q_b5` (i*, t_vm): 5.1-5.3 mm, 13 stages needed.
  - `index_q_b2` / `b3` / `b5` <-> `attn_tile` root/chain: 1.7-4.5 mm, 5-11 stages needed.
- **HBM: one stage short of the planned ceil(L / 430.56) wire stages.** The region-crossing hop sits at the 150 ps
  reach:
  - `su` <-> `router` / `cmdproc` / `vm` / `coll` / `index` (cross-domain serial <-> stream): 2.1-6.7 mm, 6-17 stages
    needed against 5-16 planned.
  - `vm` <-> `router`: 3.8 mm, 10 against 9.
  - SM control leaf (`cdist_r15` <-> `sm`): 3.9 mm, 10 against 9.
  - result leaf (`gath_r9` / `r24` <-> `sm`): 1.7 mm, 5 against 4.
  - x leaf (`mcast_r5` <-> `sm`): 1.3 mm, 4 against 3.
  - control leaf (`cdist_r14` <-> `sm`): 1.3 mm, 4 against 3.
- **S81 link lanes.**
  - Hub end blocks `dsfd_m2l_vr_68x10/11` and `svc` / `ot_pdie_serdes` / `ucie` to their first lane station: 558-980 um
    on a single hop. 52 ports on the scan die, 13 on layer1.
- **S81 field.**
  - Return leaf / relay / qbank hops of 450-864 um: `rly_63`, `rly_266`, `qbank_N`, `node_LL*`, `bf`.
  - `cfifo` <-> `rly_66` column return: 699 um.
  - Status relays: 451-562 um.
- **S81 head die.**
  - `go` relays to `ot_dsrom_head_elem_A/B`: 0.76-1.13 mm, 3 stages needed against 1 planned.
  - hbglue <-> head element x / root / res / ctl: 461-744 um.
- **S81 hub.** `dsfd_sp_vm` <-> hub end blocks `ha_*` / `hcol` (cross-domain serial <-> stream): 392-632 um, with no
  station (head and layer1 dies).
- **S81-PH tiles.**
  - Capture ctl <-> group: 562 um with no station.
  - svc IO hub <-> die lane station: 611 um.
  - The svc quadrant station chains (430 um) fit the slab's measured region budget.

## Update 2026-10-06 ~23:40 PT (CLAUDE HBM-ABSTRACTS coordinator): HBM re-planned on generator r18
- HBM die model / clock plan regenerated on r18 (claude/hbm-abstracts-20261006): budget stage plan (common-clock staged
  segments 1 + ceil((L - 359) / 412) hops), forwarded-clock hub chains (index b5 -> VM, VM -> router), regions HUB-SP /
  HUB-V, barrier beside the cmdproc, svc bands SE_s0 / SE_s3 / SW_s0 / SW_s1 / SW_s7 with their ck at the band centre
  (M7 area pin).  Clock-only CTS (EPYC2): 34 regions, max intra 56.7 ps, max inter 141.4 ps, 0 crossings > 150 ps.
  HBM interfaces infeasible as planned: 23 -> 0.  S81 sheets unchanged.
- `--insertion-override inputs/insertion_override.json`: index_q b0 / b1 / b2 / b3 / b5 keep their edge ck (R0 and
  x-mirrored copies of one master cannot both carry an on-track centre M7 pin); their internal insertion TARGET is
  re-planned to the measured SS max (1,154-1,402 ps), the die entry target follows (the tree delivers earlier by the
  excess), and the extra OCV of the deeper tree, 0.05 x (target - 900), is added to the skew term of each of their
  synchronous interfaces (+12.7..+25.1 ps).  The die skew budget (<= 56.7 ps) is unchanged.
- 2026-10-07 ~00:10 PT: HBM on generator r19 (VM split into 4 quadrant tiles hfd_vm_{sw,se,nw,ne}, ~700 x 1,000 um,
  registered cross buses; sheets for the four tiles), svc SE_s3 re-planned to 919 ps (centre ck measured; die pad 138 ps).
  HBM infeasible as planned: 0; clock plan 0 crossings > 150 ps.
- 2026-10-07 (CLAUDE HBM-ABSTRACTS): HBM on r19b: every attention root bus (tile row -> index band a0..a3) and index-key chain end (-> b0 k) ends in a die station abutting the receiving pin (budget PIN_LAST_UM 100 um, +1 hop): index b5 a3 internal input budget 113.6 -> 428.1 ps; all index-band interfaces >= 387.8 ps.
- 2026-10-07 (CLAUDE HBM-ABSTRACTS): HBM on r20 (VM quadrant tiles with the centre M7 ck). Clock plan unchanged in outcome (34 regions, max inter 141.4, 0 > 150).
- 2026-10-07 (CLAUDE HBM-ABSTRACTS): HBM on r21: a station opposite each index b5 t_vm pin run (87.7 um): b5 t_vm internal output budget 247.7 -> 501.1 ps. Clock plan 36 regions, max inter 141.4, 0 > 150.
- 2026-10-07 (CLAUDE HBM-ABSTRACTS, OWNER three rules): HBM on r22: a relay station abuts every hardened-block pin of every
  die interface whose pin segment exceeds 100 um (500 relay ends, list relay_ends_hbm.json; last segment <= 100 um,
  +1 hop each). HBM hardened blocks with an interface internal budget < 300 ps: 17 -> 1 (ot_pdie_serdes black box, 465 ps
  after the link relay; hfd_su a at 339.7 ps). Clock plan unchanged (relays are not clock-tree instances).
- 2026-10-07 (CLAUDE HBM-ABSTRACTS, OWNER 2x hub): HBM on r23: SU / SFU / HC quarters x2 area (1406 / 797 / 551 um x 5530 um), die W 24.40 -> 27.16 mm; hub quarter E/W ports in <= 500 um windows. Clock plan: stream trunk 2.69 -> 2.88 ns SS, 7 SE-group w/e crossings at 150.5-150.9 ps (<= 0.9 ps over the 150 ps term: next plan pads them). HBM infeasible 0.
- 2026-10-07 (CLAUDE HBM-ABSTRACTS): HBM on r23 (die 30.59 x 24.62 mm): 2x hub (SU / SFU / HC quarters 1406 / 797 / 551 um wide,
  ports clustered in <= 500 um windows), attention tile 1778.5 x 1350.0 um (~54 % util, option-B power), mcast_r6 split into
  hfd_mcast_r6a / r6b (half bus each), svc SE_s7 split into SE_s7 + SE_s8, SE_s1 centre ck. Clock plan method update: sibling
  regions (SM group halves, scan-quadrant cuts, HUB-C cuts) share ONE trunk sink at their family root, and forwarded-clock
  segments are not tree pairs: 37 regions, max intra 56.7 ps, max inter 58.5 ps (the wider die had 54 crossings at
  150-160 ps with per-region trunk sinks). Stale sheet hfd_vm removed (split into hfd_vm_{sw,se,nw,ne} since r19).
  HBM infeasible as planned: 0.
- 2026-10-07 (CLAUDE HBM-ABSTRACTS): VM early clock branch: HUB-V taps the stream trunk 300 ps early (the rest of the tree lifts 84.4 ps), the region flop instant is kept, so the four VM tiles have 300 ps die pad for deeper tile trees; svc SE_s5 centre ck.
- 2026-10-07 (CLAUDE HBM-ABSTRACTS): index_q b1 FF IO model from its routed boundary leaf (ff_min 540, kout hold); sheets_r23v/: the 8 VM sub-tile sheets of the r23v fallback (flag default off; VM early branch: 300 ps die pad each).
