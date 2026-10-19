# Abutted-joint bit-order audit, 4 current dies (ROOT-PINORDER-AUDIT 2026-10-19)

Tool `tools/hier_contract/abutted_joint_audit.py` (generalises `hc_ring_joints.py`); per-die data `<die>.json`, hand-off lists `handoff_<die>.md` (owner = die lead).  Joint = two placed hard children whose faces abut or face each other across <= 5 um with net bits on both facing faces; judged when > 32 b.  Pin model: routed LEF for CLOSED views, else the kit route plan (pin_ranges / dictionary order / pin_order_desc), else the die's stand-in LEF (order undefined).  Audit, not a gate.

| die | source case | joints | > 32 b | bits > 32 b | order-undefined | reversed | mirrored | scrambled | misaligned | ok | complete |
|---|---|---|---|---|---|---|---|---|---|---|---|
| s81 | S81 p4l3 real-view case case_p4l3_rv2 (bind_hbm900, plan p4l_lkcol rev1) | 249 | 95 | 25651 | 95 | 0 | 0 | 79 | 16 | 0 | True |
| qwen_compute | Qwen compute dv2f14bn chain/case_r22k (die_sources current; dv2f16 GEN running) | 34 | 10 | 52924 | 10 | 0 | 0 | 0 | 0 | 0 | True |
| qwen_kv | Qwen KV kvs14r-131a7af2c-base case_kv (GEN source claude/die-kv-lead-1019; prep FAILED at kv_lane_stations -> placement as last written) | 275 | 195 | 87770 | 195 | 0 | 0 | 193 | 0 | 0 | True |
| hbm | HBM d4g GEN2 case_a (relay-free placement case, 23:28; GEN2 'case' + GEN2c chains running) | 28 | 22 | 13832 | 10 | 0 | 3 | 21 | 0 | 1 | True |

## What needs work (counts = > 32 b joint sides)

- **s81** (owner DIE-S81-LEAD): CLOSED views with scrambled own order (re-kit route.pin_balance + re-route): {'s81dv_land_276': 56, 's81dv_land_70': 16, 's81dv_land_276l': 10, 's81dv_land_562': 9, 's81dv_land_512': 4}; kits to add route.pin_balance: none; modules with no kit (die stand-ins; their kits must be created with pin_balance + ranges facing the neighbour): {'ot_s81sl_slice': 63, 'ot_s81sl_slice_lepw': 11, 'dsdv_svc_rs_entry': 5, 'dsdv_svc_rs': 4, 'ot_s81sl_slice_lepe': 4, 'ot_s81sl_slice_lepe_nh': 4, 'ot_pdie_serdes': 4}; same-master joints whose crossing is the die netlist's bit mapping: 0.
- **qwen_compute** (owner DIE-QWEN-GEN16): CLOSED views with scrambled own order (re-kit route.pin_balance + re-route): none; kits to add route.pin_balance: none; modules with no kit (die stand-ins; their kits must be created with pin_balance + ranges facing the neighbour): {'qfd_dv_slice2_e': 10, 'qfd_dv_slice2_w': 10}; same-master joints whose crossing is the die netlist's bit mapping: 0.
- **qwen_kv** (owner DIE-KV-LEAD): CLOSED views with scrambled own order (re-kit route.pin_balance + re-route): none; kits to add route.pin_balance: {'qkd_rlys_296': 128, 'qkd_rlys_36': 4}; modules with no kit (die stand-ins; their kits must be created with pin_balance + ranges facing the neighbour): {'qkd_hbm3e_phy_pc': 128, 'qkd_kvs_pc': 124, 'qkd_kvs_pc_h': 4, 'qkd_d2ds': 1, 'ot_qkvd_ucie_x64_phy': 1}; same-master joints whose crossing is the die netlist's bit mapping: 64.
- **hbm** (owner DIE-HBM-LEAD): CLOSED views with scrambled own order (re-kit route.pin_balance + re-route): {'hbfd_rly_624_we': 16, 'hbfd_rly_624_ew': 12, 'hbfd_rly_624_sn': 4}; kits to add route.pin_balance: none; modules with no kit (die stand-ins; their kits must be created with pin_balance + ranges facing the neighbour): {'ot_hgi_sfu_core_split3': 10}; same-master joints whose crossing is the die netlist's bit mapping: 11.

## Findings

- Only 1 of the 322 > 32 b joints on the four dies is clean (HBM).  Every other one has a side without a defined bit order (kit or closed view without route.pin_balance: PPL 32-b chunks; or a module with no kit yet: die stand-in pins), or, on HBM, both sides are CLOSED hbfd_rly_624 views whose measured order is chunk-scrambled (11 relay-relay joints).
- Same-master joints (KV qkd_rlys_296 x64, HBM hbfd_rly_624 x11): part of the crossing is the die netlist wiring permuted bus slices into the relays; that is a die-generator fix (bit k to facing bit k), not a kit range.
- No full reversal found at die level (the R0->R180 reversals HBM-HCRING fixed are inside the HC ring cluster). Mirrored > 32 b joints exist only on HBM (rly_624 relays against R180 / MX ot_hgi_sfu_core_split3); they need pin_order_desc + mirrored range on the sfu side once it is kitted (prescription in hbm.json after the relay order is defined).
- CLOSED relay / landing views are chunk-scrambled in their own bit order (S81 dsfd_dvland_*, HBM hbfd_rly_624_*): a neighbour cannot match them with a range; they need a pin_balance re-kit and re-route before the parent kits are planned.
- Re-run after kits change: the prescriptions (pin_range in the re-kit side's face coordinates, pin_order_desc) appear once the partner side's order is defined.

