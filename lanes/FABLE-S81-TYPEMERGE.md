# FABLE-S81-TYPEMERGE (Fable PD review, 2026-11-15 07:4x PST) -- analysis only, no plan change, no launch

Question (OWNER): how many S81 types could share one physical design?
Plan read: epyc7 /srv/opentallas-scratch2/claude/s81-b3-clk/ev/B6gslcf.json (B6gsl + count-aligned), 395 types / 398 partitions.
Scripts: epyc7 /tmp/fable_tm_a*.py, /tmp/fable_tm_b*.py (python3 -I, read-only on the plan).

## Answer
- 395 types hold 187 different physical problems (RTL + outline + pins + ft geometry + hard-core sites). The other 208 are names, ROM images and CA/clock-landing bookkeeping.
- Three low-risk rules take 395 -> 193 builds (col 216 -> 14). All of the gain is in the frame columns.
- The 179 non-col types (leaf, station, serdes, slice, svc, misc) stay 179 under these rules: each tile carries its own set of die feedthroughs and bus positions. Merging them is a slice-region re-pin, not a delta.
- "S81 no re-type" (10-27) still holds for the non-col families. For col the merge is not a re-type: the layouts are already equal.

## 1. Groups by RTL module + parameters
| family | types | RTL (module+params) | +outline | +pin names/widths | +pin positions | +hard-core sites |
|---|---|---|---|---|---|---|
| col_h9 | 180 | 4 | 6 | 8 | 8 | 9 |
| col_h10 | 36 | 3 | 4 | 4 | 4 | 4 |
| ot_s81sl_leaf | 75 | 1 | 3 | 67 | 68 | 74 |
| slice_station | 46 | 1 (no logic) | 3 | 34 | 44 | 44 |
| serdes | 11 | 1 | 1 | 4 | 9 | 9 |
| dsdv_slice | 20 | 12 | 12 | 19 | 20 | 20 |
| svc | 16 | 5 | 6 | 16 | 16 | 16 |
| kv_leaf | 5 | 2 | 3 | 5 | 5 | 5 |
| misc (phy, eng, gunit, iqf, seqhost, bk_sel) | 6 | 6 | 6 | 6 | 6 | 6 |

## 2. What differs inside each group
| difference | where | class | evidence |
|---|---|---|---|
| ROM image (`P_*_INSTANCE`, 43 per type: 35 `ot_rom_4096x72_m8` + 8 elem halves) | col, 216 -> 43 | (c) cosmetic for P&R | every such parameter ends on a hard core with one LEF + one lib. Bound RTL of two siblings (h9_r1 cl49d7a23e pv47efee8f vs pvbb600efe): 216 of 5,376 lines differ, all ROM instance strings plus 4 port comments |
| type name copied into `landing_contract.base_type`, `collector_tree.type`, `collector_children`; notes | all | (c) | hash equal after removal |
| CA count strap width 6 vs 7 bits (`strap_ca_k_*`) | col r0, 43 -> 33 | (b) | bands, ring width (1152 / 128) and reserves are equal across siblings; only the K port width follows the instance K value |
| reverse-monitor entry (`fclk_in_cland_dn_k`, `monitor_k` band, pins) and the reset collector tree built from it | col, 33 -> 20 | (b) | 1 to 3 entry sites per family (W 463/481/801, N 182, S 182), set by which neighbour is the monitor child |
| plain form vs collector form (no landing contract vs relayed reset + monitor) | col r1/r2, 20 -> 16 | (b), reset timing changes | r1: 52 plain / 8 collector; r2: 45 / 15; h10_r1 10 / 2; h10_r2 8 / 4 |
| clock tap xy off by 1.6 to 17 um (taps, added_taps) | col h9_r2, h9_r0_p3, 16 -> 14 | (b) | tap sites derived from an older core origin (578.88 vs 586.44 in the note); hard-core origins are equal |
| CA band present or not on a lane (lane landed or not) | col h10_r0_p1, h9_r0_p2 (14 -> 12), serdes t1/t15 | (a) today | making a lane landed adds ring cycles |
| feedthrough set (count, width, faces, stations) | leaf, station, serdes, slice, svc | (a) under this floorplan | 0 to 20 ft slots per tile, 0 to 7,786 ft bits; a tile is a die routing channel |
| own-bus position and face (leafdn/leafup N or S at 6..1307 um) | leaf, c1x_C, svc | (b), but moves the neighbour pins | 9 c1x_C types = 1 RTL with 9 pinouts |
| orientation | all | already used | exact match up to MX/MY/R180 gives 0 further merges (TYPE-DEDUP did it) |
| outline | leaf 3, station 3, col 2 per family | (a) | svc-band growth rows |

## 3. Type count after normalizing (b) and (c), CA in place
| family | now | R1 ROM image + names | R2 strap width | R3a monitor sites | R3b one reset form | R4 taps | floor |
|---|---|---|---|---|---|---|---|
| col_h9 | 180 | 30 | 22 | 13 | 11 | 9 | 9 |
| col_h10 | 36 | 13 | 11 | 7 | 5 | 5 | 4 |
| leaf | 75 | 75 | 75 | 75 | 75 | 75 | 74 |
| station | 46 | 46 | 46 | 46 | 46 | 45 | 44 |
| serdes | 11 | 11 | 11 | 11 | 11 | 11 | 9 |
| slice + svc + kv + misc | 47 | 47 | 47 | 47 | 47 | 47 | 47 |
| total | 395 | 222 | 212 | 199 | 195 | 192 to 193 | 187 |

Cost of each rule:
| rule | latency | area per tile | timing risk |
|---|---|---|---|
| R1 one build per equal layout, ROM-image siblings inherit | 0 | 0 | none: same netlist, same LEF/lib |
| R2 strap width = max over the sibling group (7 bits) | 0, K values unchanged | 1 tied pin + 1 counter bit per strap, under 10 um2 | none |
| R3a every sibling carries the union of monitor entry sites (max 3), unused inputs tied | 0 data cycles; boot path only | up to 3 bands x 396.6 um2 = 1,190 um2 (0.07 %), about 1,000 flops | low; monitor is a 2-bit boot-only ring |
| R3b plain tiles take the collector form | 0 data; reset release moves by tree depth 6 to 8 cycles on 115 tiles | about 230 relay/pad flops | medium: reset wavefront re-proof (bind_reset); inside the 64-clk rst_n hold |
| R4 re-derive tap sites from the current core origin | 0 | 0 | none |

Non-col options, not for the next delta:
| option | leaf | station | serdes | cost and risk |
|---|---|---|---|---|
| superset at exact pin positions (unused ft slots tied, mirror allowed) | 75 -> 61 | 46 -> 33 | 11 -> 6 | 0 cycles, neighbours untouched; unused station flops; saves 32; CA band set of the superset must cover the members |
| re-pin ft slots to a common grid, then superset | 43 | 27 | 2 | saves 60 (corrected from 81); neighbour pins move, signed leaf/station types rebuild, stations and K values change |
| one universal template | 3 | 3 | 1 | not feasible: union is 19,036 ft bits against a median of 2,628; N face needs 12,136 ft pins against 5,194 allowed (1,442.88 um x 6 x 0.6) |

## 4. Top 3 rules
1. **R1: sign-off key = layout hash, not type name.** Hash the type without module, notes, param_set and self-name fields; one build per hash, siblings inherit. 395 -> 222 (-173). This is S81-COL-INHERIT (OWNER-approved 11-14 for r1/r2, 144 identities -> 13) extended to r0 and to the CA plan. No plan change.
2. **R2 + R4: CA strap width = group max, tap sites re-derived.** 222 -> about 210 (-12). CA composition only; K values, bands and latency unchanged.
3. **R3a: union of monitor entry sites per col family.** About 210 -> 197 (-13). R3b adds -4 but moves reset release on 115 tiles; take it only if bind_reset passes without other changes.

Next S81 delta: yes for all three. They do not touch CA lanes, K values, ring depths or data latency, and they change only the col types, which are regenerated at adoption anyway (350 delta types are under PENDING-PLAN). CA matters in one way: in B6gslcf the r0 siblings differ by strap width and collector tree, so without R2 and R3a the r0 inheritance that held before CA is lost (col r0 = 28 builds instead of 9).

Not checked: which of the 36 signed types are col r0 types (they would re-sign after R2/R3a); how the ROM image reaches the macro GDS per instance at die assembly.

## 5. Addendum 11-15: R3a minimal form, and R1 without R3a (plan TYM1, IMPL hash `col_typemerge.layout_hash`)
Script: epyc7 /tmp/fable_tm_c2.py, c3.py (read-only on ev/TYM1.json).

### 5.1 What the 76 hashes are made of
| step | col hashes | what changes |
|---|---|---|
| TYM1, IMPL hash | 76 | - |
| drop `landing_contract.collector_children[].part` from the hash | 33 | nothing in the design: `part` is the die instance name of the child (fE0_p3_b0), not layout. Dropping `placement` alone changes nothing (76) |
| R3a (below) | 19 | reset-tree outs of 76 of the 89 collector-form types |
| R3b (plain tiles take the collector form) | 15 | 127 plain tiles |

The 19 after R3a: 12 families + 4 plain/collector splits (h9_r1, h9_r2, h10_r1, h10_r2) + h10_r0_p1 (lane landed or not) + h9_r0_p2 (hard-core origins differ, 5 vs 5 types) + h9_r2 plain (43 vs 2 types, tap and sink sites still differ after R4).

### 5.2 R1 without R3a
R1 still works. With the IMPL hash as is: 216 -> 76 col builds (-140), S81 total 255. With the instance name removed from the hash: 216 -> 33 (-183), total 212. R3a then adds -14 (total 198). The first step is a hash fix, not a design change, and is worth three times R3a.

### 5.3 R3a minimal form
Correction to section 3: the entry sites are the `outs` of the partition reset tree (`collector_tree.outs`, node `rst_n_t<n_consumers+k>`), not a band option.
Facts from TYM1:
- Every tap and out is padded to the tree depth. Depth is one value per family in every variant (6, 7 or 8) with 0, 1, 2 or 3 outs (h9_r2 has a 3-out type at depth 6).
- Outs without a monitored child already exist: h9_r0_p5 (12 types, 1 out, 0 children), h9_r2 (2 outs, 1 child). The tree hash is equal for two h9_r2 types that use different outs (ct 3c121d).
- The remaining spread is the out set plus the tap index shift it causes (`core_resets[].tap` +1/+2).

Rule: per (family, collector form), `outs` = union of the sibling out sites in one fixed order; `mask.children`, the `cland_dn_*_k` pins and the `monitor_k` band exist at site k if any sibling monitors a child there. Per instance, an unused out is left open at the parent and its monitor inputs are tied and excluded from the ready/fault aggregate (1 strap bit per site, tied at the parent).

| family | union outs | types changed | outs added |
|---|---|---|---|
| h10_r0_p1 | 2 | 4 of 6 | 4 |
| h10_r0_p4 | 2 | 6 of 6 | 6 |
| h10_r1 | 2 | 1 of 2 | 1 |
| h10_r2 | 2 | 3 of 4 | 3 |
| h9_r0_p1 | 1 | 0 of 6 | 0 |
| h9_r0_p2 | 2 | 12 of 12 | 17 |
| h9_r0_p3 | 3 | 12 of 12 | 27 |
| h9_r0_p4 | 2 | 4 of 6 | 4 |
| h9_r0_p5 | 2 | 12 of 12 | 12 |
| h9_r1 | 2 | 8 of 8 | 8 |
| h9_r2 | 3 | 14 of 15 | 14 |
| total | - | 76 of 89 | 96 |

Cost: each added out is one pad chain of 6 to 8 flops (about 700 flops over the die); a monitor band (320 flops, 396.6 um2) where a site gains one. Data cycles 0. Reset release 0 cycles if the depth holds; +1 cycle on a family if the union tree goes one level deeper (inside the 64-clk rst_n hold).

Proof needed:
1. Compose: `collector_tree.depth` per family equal to TYM1; clock_landing sum 2992 and cycles sum 14021 unchanged.
2. bind_reset: per-instance release depth equal to TYM1 for every consumer and every used child out (diff of bind_reset.json = 0 rows).
3. LATCHECK: unchanged; no lane row is touched, run once as a regression.
4. bind_declared_ties / tie audit: the open outs and tied monitor inputs listed, nothing else new.

Not checked: that the monitor aggregate can ignore a child whose return clock is tied (the monitor ring is written on the child clock, so tying ready/fault alone is not enough; this is the strap bit above). h9_r0_p3 with 3 outs has no existing example; its depth is the one to watch.
