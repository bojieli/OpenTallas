# Tile master dedupe, 2026-10-15 (DEDUPE)

Owner rule, 19:50 PT on 10-15 (RELAUNCH_1405.md "OWNER RULES 19:50", memory note `pin-registers-and-few-tiles-1015`):
build fewer distinct tiles. Round widths up to a few standard sizes and replicate one hardened master. Put pin
registers on every port. Do not create a new width, depth or footprint variant until the registry has been checked
for a hardened master that can be replicated or padded.

* Generator: `tools/tile_dedupe_1015.py`. It reads the fleet-viz registry (snapshot in
  `inputs/registry_rows.json`), every source listed in `results/fleet_viz/die_contracts.json` (port_bind, slots and
  instances, which give instance counts), the RTL of each master on main, and the live closure-loop jobs
  (`inputs/closure_live_jobs.txt`).
* Data: `dedupe.json` has `masters` (one row per master: function, width, footprint, state, instances, RTL file and
  RTL identity hashes), `families`, `actions` (the decision for each master, with area, extra flops and routes
  avoided) and `summary`.
* RTL identity: each module body is hashed with comments stripped and its name masked, giving an *exact* hash. A
  second *param* hash also replaces every number with `#`. Two masters with the same exact hash are the same RTL
  under different names. Two with the same param hash differ only in widths or ID constants.

## Before and after

Counts are distinct masters per die. A die count is everything the current contract or bind places on that die:
non-superseded contract members, bind-only masters, and open rows outside the contract. PHY, ROM and SRAM macros are
excluded.

| die | masters before | needing closure before | after phase 1 | needing closure after phase 1 | after full | routes avoided | area, phase 1 | area, phase 2 | extra flops (ph1 / ph2) |
|---|---|---|---|---|---|---|---|---|---|
| Qwen compute | 67 | 34 | 62 | 29 | 62 | 5 | 0 | 0 | 0 |
| Qwen KV/system | 79 | 34 | 76 (incl. +20 closed hbfd_rly) | **11** | 76 | **23** | **-2.49 mm2** | 0 | 116 k / 0 |
| S81 (DeepSeek ROM) | 434 | 73 | 361 | 67 | 296 (+46 more after the ID-register revision: ~250) | 0 now (6 on fail) | -0.009 mm2 | +0.058 mm2 | 234 k / 67 k |
| HBM accelerator | 176 | 111 | 163 | 100 | 163 | **36** (28 of them VM banks, see H-HARDEN) | 0 | 0 | 0 |
| **all (unique, 749)** | **749** | 252 | **655** | | **638** (about 590 after the S81 ID revision, about 575 with S81 relay mirroring) | **64** | **-2.50 mm2** | **+0.06 mm2** | 350 k / 67 k |

Phases:

* **Phase 0, standard.** Keep the master and replicate it.
* **Phase 1, now.** Two cases.
  * An open master whose standard is CLOSED is replaced by a replica of the standard, and its own route is not
    needed.
  * A CLOSED master is rebound by the die generator to an equal-RTL or same-footprint standard. This needs no route.
* **Phase 2, next touch.** The master is CLOSED, but rebinding it costs area or an RTL change. Its view stays until the
  die names it again (re-pin, hold or re-route). At that point the standard replaces it instead of closing the old
  master again.

Costs:

* **Cycles: 0** on every relay and station mapping. Each standard is the same single register stage, and a bus that
  is wider than the largest standard uses k copies side by side, also one stage.
* **ID registers:** merges that move an ID constant into a register cost 0 cycles in steady state. The ID is
  loaded once by the static schedule.
* **Pin registers:** the standard relays and stations already have them. The relay or station flop is both the
  input and the output pin register, so they cost no extra cycle.
* **New merged tiles:** these are VM static, port tiles and SFU control. They take the default pin registers, which
  cost 1 to 2 cycles per boundary and are absorbed by the compiler schedule.
* **Padding power:** about 1 uW per padded flop at 1.2 GHz with tied-low data, so 350 k flops cost about 0.35 W in
  total across the dies. That is well under 0.1 % of die power.
* **Area:** phase 1 is net negative. The Qwen KV relays shrink from a 52.656 x 30.2 um slot to the 21.6 x 21.6 um
  hbfd outline.

**Padding needs one tool change.** The HBM relay family already allows spare inputs tied low and spare outputs left
open at the die top (`tools/hbm_die_rly_kits.py`). The S81 and Qwen port-bind checkers must accept a declared `PAD`
bit class on standard masters (logical width recorded, spare bits tied low, outputs open). Without it they report
`input_tied`. This tool change belongs to ROOT / S-BIND.

## Families and standard sets

| family | function, depth | members | standard set (CLOSED unless noted) | decision |
|---|---|---|---|---|
| S81-HSTN `dsfd_hstn{h,v}_<W>` | common-clock station, one flop per bit, 1 stage | 55 (29 H + 26 V) | H: 20 / 85 / 128 / 514 / 761 / 1029; V: 20 / 85 / 515 / 759 / **1029 (running f8)** / 2204 | 25 rebind now (all ≤ 85 b share the 298 um2 outline; 512–515 V share 2,617 um2); 14 rebind at next touch; `hstnh_515` has a different RTL body (hend glue) and stays as it is |
| S81-STN `dsfd_stn{h,v}_<W>x<k>` | forwarded-clock link stage, 1 stage per lane | 16 | 10 / 86 / 293 / 566 / 1026 per side (`stnv_566x1` running f8, different RTL body) | 3 and 70 rebound to 10 and 86 (same outline); 70x2/x3/x4 become k x 86x1 (FILL has already retired them with `--stn70-split`); 512/514 become 566 at next touch |
| S81-RLY `dsfd_rly_<W>_<flow>` | `ot_s81_rly`, async clear, 1 stage | 37 | per flow: a ≤ 16 b class and a 17–68 b class on the smallest closed footprint, plus 283 (wide) → 27 | 10 rebind now (1→2, 54→68 / 63, 63→66, 266→283; same outline); **phase 3:** WE/EW, NS/SN and the turn flows collapse by MY/MX mirroring if pins stay on track (15.12 um = 56 rows, even) → about 12 |
| HBM-RLY `hbfd_rly_<Wc>_<flow>` | width-class relay, flops at the pins, 1 stage | 24 | 48 / 136 / 304 / 624 / 1136 x WE/EW/SN/NS | 8 → 48 (same 466.56 um2) when re-bound. **This is the cross-design standard relay library** |
| Qwen KV `qkd_rly_<W>` (20, not started, no RTL) | die-top relay | 20 | → hbfd_rly 48 / 136 / 304 / 624 / 1136 (2089 = 2 x 1136) | **20 routes avoided**, -2.49 mm2; a per-bit-direction bundle splits into one relay per direction |
| HBM v15 `hfd_stn_v15_cc2224/2248` | registered station, 1 cycle | 2 | 2 x hbfd_rly_1136 each | 2 routes avoided |
| FENCE-BANK `ot_hbm_native_fence_bank<N>` (S81 + HBM) | fence bank | 6 | 32, 128 (1..32 share 466.56 um2) | 4 rebind now |
| S81-NET lane ends | m2l/l2r/r2l | 29 in 6 exact-clone groups | one canonical per group | 22 rebind now (E0..W3 m2l_raw x8, 68x11 x8, 68x10 x4, 512x1 hco/hix/hqe, 564 E/W, r2l hcol/hsel); about +0.03 mm2 because the canonical is the largest footprint |
| other exact clones | node LLfd=LLfu, NNfd=NNfu; lkck NE/NW/SE/SW; mtp_hrow cbe=cbw; HBM vm_calendar NE=SE; smh_be eg=wg; **smh_tile eg=wg (needs redesign)**; svc_v15 SE_s0..2 = SW_s0..2 | 14 | canonical per group | smh_tile_eg: 1 route avoided |
| HBM-VMS-BANK-ID `hfd_vms_bank_identity_q*_b*` | VM bank core, BANK_ID/SLICE_ID literals, RG 5/4/6/6 | **32 RTL modules** (4 running) | 3 (RG 4 / 5 / 6) with the IDs in a pin-registered config input | **28 routes avoided**. Reverses the 10-15 "32 distinct literal masters" choice, which saved 5 identity flops per bank |
| HBM-VMS-STATIC `hfd_hgi_vms_static_NE/NW/SE/SW` | VM static slice per quadrant | 4, not started | 1 (quadrant index registered, mirrored placement) | 3 routes avoided |
| HBM-SFU-CTL 60hi / 75hi / 75lo | SFU control split | 3, need redesign | 1 programmable controller | 2 routes avoided |
| Qwen port tiles 0/1/2 (+f1) | port tile clusters | 6, not started | 2 | 4 routes avoided |
| mirror pairs | qkd_astk/_n, qkd_land/_n, qkd_hslice/_dn, qfd_xcol_e/_w | 8, not started | 4 (second copy placed MX/MY) | 4 routes avoided |
| S81 ID-constant families (closed) | VM read q/v (+_p) 32, return_bank8 8, fsr 4, hc_ctnl 4, pq_qb_bank 4, pq_bc_slice 4 | 56 | 10 after an ID-register revision | phase 2 (-46 masters), no re-route now |

## Live jobs: let them finish (none cancelled)

| job | stage | decision |
|---|---|---|
| s81fill_hstnh_4096-f6 | collect | let it finish; if it closes, the view stays (non-standard); if it fails, retire it and bind 4 x hstnh_1029 |
| s81fill_hstnv_3056-f8 | READY verdict | let it finish; otherwise use 2 x hstnv_2204 |
| s81fill_hstnv_1029-f8 | route | let it finish: **this becomes the V standard** |
| s81fill_hstnv_560-f8, hstnv_761-f8 | route | let them finish; if they fail, do not resubmit: bind hstnv_759 / hstnv_1029 |
| s81fill_stnv_566x1-f8 | route | let it finish: V standard 566 (814 instances) |
| s81net m2l_vr_68x10 E5/W5, 68x11 E4/W4 (n3/n4) | route | let them finish, but do not resubmit: the RTL is identical to the closed W0/W1, so the die binds the canonical |
| vm_identity_q0..q3_b0 | route | let them finish (representatives). Before any b1..b7 job, register BANK_ID/SLICE_ID |
| hstnv_2049 / 2164 / 2204-f8 | CLOSED 19:xx | 2204 is the V wide standard; 2049 and 2164 stand (phase 2) |

## Rules for new tiles (from now on)

1. Any new relay or station uses an existing standard: S81 hstn/stn/rly in their footprint classes, and hbfd_rly for
   HBM and Qwen. If none fits, use k copies side by side. Never create a new width.
2. Per-bank, per-quadrant or per-slice copies carry their index in a pin-registered config input loaded by the static
   schedule. They must not use a literal parameter. One RTL, one route, N replicas; mirror placement for E/W and N/S.
3. Before an element prompt launches anything new: if `tools/tile_dedupe_1015.py` (or the registry) shows an
   exact-clone or param-clone hash match, the element is a replica, not a new master.
