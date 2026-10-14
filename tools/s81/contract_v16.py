#!/usr/bin/env python3
"""S81 hierarchy contract v15 -> v16 (one-shot, idempotent).  Folds the slot requests posted to el1011-s81die.log on
2026-10-13 07:26..09:35 PT and the coordinator decisions of 07:55 (hrow) / 12:25 (q element, VM8 clock):

  hrow     four die-placed leaf slots (ing, hub, cbe, cbw) under rep/hrow, die relays, measured insertions
  ces      dsfd_coll_ces0 x1 + dsfd_coll_cesn x3 (wires-only parent over hardened leaves) under sp_collective
  capture  sp_capture 1727.976 x 129.576 -> 1727.976 x 561.6, cluster over the closed capt_g2 / capt_x / capt_ctl
  q elem   real view + libs + bound PQ1 bench; legacy M7 pockets
  pq_root  131.76 x 211.68 (ref_tile lattice), ports N 68 / S 71
  bgq28    345.6 x 501.12 -> 345.6 x 622.08 (8 one-bank leaves of 77.76; 592.5 = 8 x 74.06 is off the 2.16 lattice)
  vm_fe    new slot sp_vm/u_fe 1520.064 x 695.52 (dsfd_vm_fe_h, leaves frozen at 693940a56); sp_vm grows N
  wfc      priced kit pins (RD2 1: t_srd 31, f_srq 1026; t_ft 4; t_hep 36 on L37/38/39)
  SU       kv0/kv1 -> kvt x4 + kvq x16 + kve/kvp/kvr; qb0-3 -> qbt + qbe x8; sw0-7 -> swt (reserve) + swe x128 + qbe x8
  HC       W face: wq_d / y_d on the VM / collective lanes at 2-track pitch (--lane-pins 2)
  gather   pending (storage redesign step B fits the slot; capacity answer owed)
  clock    seam_rules.clock = the die clock delivery rule (insertion-compensated entry, tap levels)

Slab pins: `--pins-from ELEMENTS.lef` re-reads every hub slab row's pins (face, layer, centre offset, span) from the
generator's LEF of the v16 case, so the contract carries the pins the die was generated with.

Usage: contract_v16.py [--check] [--pins-from ELEMENTS.lef]
"""
from __future__ import annotations
import argparse, copy, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "results/arch/hier_contract_1011/s81.json"
RT = "physical/ref_tile"

# measured TT boundary-mean clock insertion (views/<cell>/insertion.json), the die clock delivery reference R
def _ins(kit, cell):
    p = ROOT / RT / kit / "views" / cell / "insertion.json"
    if not p.exists():
        return None
    j = json.loads(p.read_text())
    b = (j.get("tt") or j)["boundary"]
    return dict(R_tt_ps=b["mean"], spread_ps=round(b["max"] - b["min"], 1), sinks=b["n"])


def _lef_size(kit, cell):
    p = ROOT / RT / kit / "views" / cell / f"{cell}.lef"
    if not p.exists():
        return None
    m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", p.read_text())
    return (float(m.group(1)), float(m.group(2)))


def _row(tmpl, **kw):
    r = {k: copy.deepcopy(v) for k, v in tmpl.items() if k in ("io_budget", "clock_entry")}
    r.update(version=16, pg_layer="M5", strap_layer="M6", signal_max_layer="M5", layer_cap="M5", layer_rule="tile_m5")
    r.update(kw)
    return r


def _clock(r, kit, cell):
    i = _ins(kit, cell)
    if i:
        r["target_insertion_ps"] = i["R_tt_ps"]
        r["clock_delivery"] = dict(i, level="common (R <= 300)" if i["R_tt_ps"] <= 300 else
                                   f"early tap, R - 300 = {i['R_tt_ps'] - 300:.1f} ps before the common level; its hops at SKEW 150",
                                   spread_ok=i["spread_ps"] <= 80.0, source=f"{RT}/{kit}/views/{cell}/insertion.json")
    return r


def lef_pins(path):
    """{macro: (w, h, {bus: [(face, layer, coord along the face)]})} for the hub slab masters of a generated LEF"""
    out, m, pin, layer = {}, None, None, None
    for line in Path(path).read_text().splitlines():
        s = line.split()
        if not s:
            continue
        if s[0] == "MACRO":
            m = s[1]; out[m] = [0.0, 0.0, {}]
        elif m is None:
            continue
        elif s[0] == "SIZE":
            out[m][0], out[m][1] = float(s[1]), float(s[3])
        elif s[0] == "PIN":
            pin, layer = s[1], None
        elif s[0] == "LAYER" and pin:
            layer = s[1]
        elif s[0] == "RECT" and pin and layer:
            x0, y0, x1, y1 = map(float, s[1:5]); w, h = out[m][0], out[m][1]
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            d = dict(W=cx, E=w - cx, S=cy, N=h - cy); f = min(d, key=d.get)
            b = re.sub(r"\[\d+\]$", "", pin)
            out[m][2].setdefault(b, []).append((f, layer, cy if f in "WE" else cx))
            pin = None
        elif s[0] == "END" and len(s) > 1 and s[1] == m:
            m = None
    return out


def refresh_pins(c, lef):
    lp = lef_pins(lef); n = 0; changed = []
    for s in c["slots"]:
        if s.get("parent") != "s81_layer1" or "pins" not in s or s["cell"] not in lp:
            continue
        w, h, buses = lp[s["cell"]]
        if abs(w - s["outline"]["w"]) > 0.05 or abs(h - s["outline"]["h"]) > 0.05:
            raise SystemExit(f"{s['name']}: LEF {w} x {h} != contract outline {s['outline']}")
        pins = []
        for b, v in sorted(buses.items()):
            if b in ("VDD", "VSS"):
                continue
            faces = {f for f, _, _ in v}; lays = {l for _, l, _ in v}
            f = sorted(faces, key=lambda f_: -sum(1 for x in v if x[0] == f_))[0]
            cs = [x[2] for x in v if x[0] == f]
            pins.append(dict(name=b if len(v) == 1 else f"{b}[{len(v) - 1}:0]", face=f, layer=sorted(lays)[0],
                             offset=round((min(cs) + max(cs)) / 2, 3), width=round(max(cs) - min(cs) + 0.024, 3),
                             **({"faces": sorted(faces)} if len(faces) > 1 else {})))
        if pins != s["pins"]:
            changed.append(s["name"])
        s["pins"] = pins; s["pins_source"] = "generator LEF of the v16 case (tools/s81/contract_v16.py --pins-from)"; n += 1
    return n, changed


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); ap.add_argument("--pins-from")
    a = ap.parse_args()
    c = json.loads(CON.read_text())
    if c["version"] >= 16:
        if a.pins_from:
            n, ch = refresh_pins(c, a.pins_from)
            if not a.check:
                CON.write_text(json.dumps(c, indent=1) + "\n")
            print(f"v16 pins refreshed on {n} slab rows; changed: {ch}")
        else:
            print("already v16")
        return 0
    assert c["version"] == 15, c["version"]
    by = {s["name"]: s for s in c["slots"]}
    tile = by["sp_collective/cb_f"]
    new = []          # (after row name, row)

    # ---- hrow (coordinator 07:55): rev 5 as DIE-PLACED tiles with die relays, four leaf slots, no cluster job
    h = by["rep/hrow"]; h.update(kind="container", assembly="tiles_direct", version=16)
    h["notes"] = ("v16 (coordinator 2026-10-13 07:55): rev 5 kept as DIE-PLACED tiles with die relays; four leaf slots below, no "
                  "parent / cluster job. Chain relays per hop CQ 3 / P 2 / WD 0 (dsfd_mtp_hrow_tc); the U-turn hop (336..509 um, "
                  "2,079 b) takes one more die relay so every hop <= 500 um; cbe / cbw pin jogs (34 / 153 um) are absorbed by the "
                  "die relays. Functional gate: mtp_hrow_gate --tiles on the mixed r8a / r8b pair. Present on the stage dies "
                  "that carry the hidden row (--hrow-tx / L37..39), not on layer1.")
    for cell, kit, n, wh in (("dsfd_mtp_hrow_ing", "hrow5_ing", 3, (129.6, 129.6)), ("dsfd_mtp_hrow_hub", "hrow5_hub", 1, (216.0, 216.0)),
                             ("dsfd_mtp_hrow_cbe", "hrow5_cbe_cx", 15, (475.2, 216.0)), ("dsfd_mtp_hrow_cbw", "hrow5_cbw_cx", 15, (475.2, 216.0))):
        sz = _lef_size(kit, cell); assert sz == wh, (cell, sz, wh)
        r = _row(tile, name=f"rep/hrow/{cell}", cell=cell, kind="tile", parent="s81_layer1", parent_master="rep/hrow",
                 outline={"w": wh[0], "h": wh[1]}, origin={"x": 0, "y": 0}, kit=kit, assembly="tiles_direct", owner="el1013-ds-mtp",
                 replicated={"count": n, "placement": "die plan (generator --hrow-tx), inside the rep/hrow region 2998.08 x 1769.04"},
                 view_status=f"CLOSED on main, view {RT}/{kit}/views/{cell} (LEF {wh[0]} x {wh[1]}, 3 libs, insertion.json)",
                 notes="v16 leaf slot of the MTP hidden row (die-placed, die relays)")
        new.append(("rep/hrow", _clock(r, kit, cell)))

    # ---- collective engine lane-slices (s81-cesn 07:37)
    assert _lef_size("dscoll_ces0_cxsp", "dsfd_coll_ces0") == (302.4, 341.28)
    for k, (x, y) in enumerate(((604.8, 1017.36), (950.4, 1017.36), (604.8, 1401.84), (950.4, 1401.84))):
        cell = "dsfd_coll_ces0" if k == 0 else "dsfd_coll_cesn"
        r = _row(tile, name=f"sp_collective/ce_s{k}", cell=cell, kind="tile" if k == 0 else "parent", parent="sp_collective",
                 outline={"w": 302.4, "h": 341.28}, origin={"x": x, "y": y, "orient": "R0"}, owner="el1013-s81-cesn",
                 notes="v16 engine lane-slice %d: 2 x 2 block (pitch 345.6 x 384.48, 43.2 channels) centred in the core band "
                       "between the cb row (top 381.24) and ct (2381.376), 172.8 um E of the lane column. Lane -> slice hops "
                       "inside the cluster are up to ~1,020 um in y: the collective owner plans registered lane relays "
                       "(<= 500 um a stage)." % k)
        if k == 0:
            r.update(kit="dscoll_ces0_cxsp", view_status="CLOSED cxsp d8b0f7a0e, view physical/ref_tile/dscoll_ces0_cxsp/views/dsfd_coll_ces0")
            _clock(r, "dscoll_ces0_cxsp", "dsfd_coll_ces0")
        else:
            r.update(assembly="cluster", view_status="NOT BUILT: the flat cesn (22.6k sinks on one root) is refused by the clock rule; "
                     "wires-only parent on this outline over hardened leaves cesl / cesx / ceso / cespn / cescn (own roots; "
                     "kits physical/ref_tile/dscoll_ces{l,x,o,pn,cn}); child slots follow the leaf verdicts")
        new.append(("sp_collective/ct", r))

    # ---- capture cluster (s81-spwfc/sp3 option A)
    cp = by["sp_capture"]; assert (cp["outline"]["w"], cp["outline"]["h"]) == (1727.976, 129.576)
    cp["outline"]["h"] = 561.6; cp["version"] = 16; cp["assembly"] = "cluster"
    cp["notes"] = ("v16: 1727.976 x 561.6 cluster over CLOSED M5 views, children MX (inputs N, outputs S): 8 x dsfd_capt_g2 at y 345.6, "
                   "8 x dsfd_capt_x at y 43.2 (x 129.6, 302.4, 475.2, 648.0 | 950.4, 1123.2, 1296.0, 1468.8), dsfd_capt_ctl at "
                   "(820.8, 172.8); cluster logic = 872 station flops + t_cd. 0.439 mm2 of closed leaf outline cannot fit 129.6 um "
                   "in any partition. Clocks: ck N (17 child pins), ckv S (8 child pins): ckv / rsv are NEW die pins. Spec "
                   "tools/ref_tile/specs_s81sp/s81sp_capc_cl.json (branch s81-spwfc-1013).")
    cp["pin_request"] = {"f_gather[53*16*g +: 848]": "8 bundles on N centred at x 189, 361.8, 534.6, 707.4, 1009.8, 1182.6, 1355.4, 1528.2",
                         "f_gather[6946:6784]": "163 b on N over the ctl, x 864", "t_vm[1664*g +: 1664]": "S under the x columns",
                         "t_vm[13375:13312]": "S under column 3, x 707.4", "t_cd": "N near x 707", "ckv, rsv": "S",
                         "status": "OPEN in the generator: v16 GEN still lays f_gather / t_vm as one centred group each "
                                   "(pins below = the generated ones); the bundle split is a generator change owed before the cluster routes"}
    c.setdefault("sub_layouts", {})["dsfd_sp_capture_c"] = {
        "outline": {"w": 1727.976, "h": 561.6}, "owner": "s81-spwfc", "orient": "MX children",
        "rows": [{"tile": f"g2[{g}]", "cell": "dsfd_capt_g2", "x": x, "y": 345.6} for g, x in enumerate((129.6, 302.4, 475.2, 648.0, 950.4, 1123.2, 1296.0, 1468.8))]
              + [{"tile": f"x[{g}]", "cell": "dsfd_capt_x", "x": x, "y": 43.2} for g, x in enumerate((129.6, 302.4, 475.2, 648.0, 950.4, 1123.2, 1296.0, 1468.8))]
              + [{"tile": "ctl", "cell": "dsfd_capt_ctl", "x": 820.8, "y": 172.8}]}

    # ---- q element: real view + libs on main; PQ1 bench bound by Codex at 9a645eab1
    q = by["rep/q_elem/ot_v41_rom_elem_q_qxpq_w10"]; q["version"] = 16
    q["view"] = "physical/s81_die_views/q_elem_qs5f_efs"
    q["view_status"] = ("REAL view on main cd4790dd9: LEF 510.84 x 221.4 (= the LEF every die case placed) + TT / FF / SS libs = verdict "
                        "replay of the CLOSED route dsrom-qelem-qs5f-efs-7fb23b7ff-tc-hm10-cl (TT +98.72 / FF +12.04, DRC 0); exact PQ=1 "
                        "bench + mutant bound at 9a645eab1 (3648/3648, mutant fails). Legacy layers: signals and pockets up to M7 "
                        "(view_cap M7). Coordinator 12:25: the view is KEPT; a strict M7 pocket check is owed only by a parent that "
                        "routes M7 over it (the die keeps M7 off the element frames: field-frame die routes use M8/M9 and the "
                        "column relays' M4/M5 in the relay sites).")

    # ---- PQ root (s81-pqroot 07:36)
    p = by["rep/pqc/dsfd_pq_root"]; p["outline"] = {"w": 131.76, "h": 211.68}; p["version"] = 16
    p.update(pg_layer="M5", strap_layer="M6", signal_max_layer="M5", layer_cap="M5", layer_rule="tile_m5", kit="s81pq_root_ref",
             real_cell="ot_s81_pq_ret_root_cam_p (D128 QD128 PAR0 ASPLIT0)")
    p["ports"] = {"N": "tree word in: i_v, i_t[32], i_d[32], i_e, i_p, up_fault = 68 b (M5)",
                  "S": "root word out: r_v, r_row[16], r_pos[3], r_fp32[32], r_bf16[16], r_e, r_p, fault = 71 b (M5)", "W": "clk, rst_n (M4)"}
    p["notes"] = ("v16: 131.76 x 211.68 (2.16 lattice; 0.432 um narrower than the reserved 132.192 frame, placed at the frame's W "
                  "edge, no neighbour moves). Ports 68 / 71 ADOPTED. Cost to neighbours: the die buses are pqt 66 and pqo / pqc 68 "
                  "(generator PQ_TI / PQ_RO): +2 b on pqt (i_p, up_fault: tied at PAR 0 by the N return station) and +3 b on pqo "
                  "and on the column return into the cfifo `ri` (68 -> 71); dsfd_cfifo is a CLOSED view, so the +3 b (r_e, r_p, "
                  "fault) ride a separate 3-b status relay to the column fault collector instead of widening `ri`. OPEN in the "
                  "generator (PQ_TI / PQ_RO unchanged in the v16 case: the root is still the generated 66 / 68 placeholder).")
    for n_ in ("rep/pqc/dsfd_rstg_pq66", "rep/pqc/dsfd_rstg_pq68"):
        by[n_]["notes"] += " v16: stays 132.168 wide (0.408 um overhang past the 131.76 root on E, inside the frame); width follows the pq_root port decision (68 / 71)."

    # ---- VM slab: bank tile 345.6 x 622.08, FE slot, slab grows N
    vm = by["sp_vm"]; assert vm["outline"]["h"] == 2730.216
    BG_H, BG_Y0 = 622.08, 136.08
    for s in c["slots"]:
        mm = re.match(r"sp_vm/g_h\[(\d)\]\.g_t\[(\d)\]\.u_bg$", s["name"])
        if mm:
            t = int(mm.group(2)); assert s["outline"]["h"] == 501.12
            s["outline"]["h"] = BG_H; s["origin"]["y"] = round(BG_Y0 + (3 - t) * BG_H, 3); s["version"] = 16; s["kind"] = "parent"
            s["clock_entry"] = {"pin": "ck", "face": "W", "layer": "M4"}
            s["view_status"] = "NOT BUILT: wires-only parent over 8 x dsfd_vm_bgl28 (345.6 x 77.76, one bank each, hardened once; kit physical/ref_tile/dsfd_vm_bgl28_a on claude/s81-bgq28-1013 @d415c687f)"
            s["notes"] = ("v16 (s81-bgq28 07:58, coordinator: slot grows, shared gate not overridden): 345.6 x 622.08 = 8 x 77.76 "
                          "leaves (the SRAM stays >= 20 um from the N / S pin faces: 74.06 um minimum, 77.76 on the 2.16 lattice; "
                          "the coordinator's 592.5 = 8 x 74.06 is off the lattice). Width, N / S pin x and layers, W pins ck / rs / grp, "
                          "M5 cap unchanged; the flat 63,416-sink tile is retired. Tile hop 6 -> 16 cycles (timing only, o_* -> f_* "
                          "skew unchanged). Clock spine buffers + 3 tie cells a leaf inside the existing 43.2 um W channel. | v15 and "
                          "earlier: " + s.get("notes", "")[:400])
    fe_y = round(BG_Y0 + 4 * BG_H + 21.6, 3)                 # 2646.0
    FE = (1520.064, 695.52)
    new.append(("sp_vm/u_be.g_s[3].u_sl", _row(tile, name="sp_vm/u_fe", cell="dsfd_vm_fe_h", kind="parent", parent="sp_vm",
               outline={"w": FE[0], "h": FE[1]}, origin={"x": 0.0, "y": fe_y, "orient": "R0"}, assembly="cluster", owner="el1013-s81-vmfe",
               view_status="NOT BUILT: hierarchy RTL + all leaves frozen and proven @ 693940a56 (claude/el1013-s81-vmfe: lockstep 9/9, "
                           "FRL 6, KD 2, LGL / LDL / LAL 3); leaf kits and the plan are owed by the physical agent",
               notes="v16 FE envelope 1,520.064 x 695.52 (the request: up to 1,520.064 x ~694; 695.52 = 322 x 2.16): room for one "
                     "lane row under the clt plateau (option (a) of el1013-s81-vmfe B3). Includes clt, fsr, flt, fcn / fcc / fcw, "
                     "frg / fra / frr mid relays (the 02:51 clt / fsr slot request is answered by this envelope: FE-internal "
                     "sub-slots are the FE owner's sub_layout). Cycles: read +4, write landing +4 (+7 on the landing lanes), "
                     "slot done +1 (el1013-rom-layer-tput-s81.log).")))
    vm_h_old = vm["outline"]["h"]; vm["outline"]["h"] = 3343.656; vm["version"] = 16
    vm["notes"] = (vm.get("notes", "") + f" v16: slab height {vm_h_old} -> 3343.656 (+613.44 N): 4 x bgq28 at 622.08 (+483.84) and the FE "
                   "envelope 695.52 at y 2646.0 (+~108 + lattice); be_sl row and the 136.08 BE band unchanged. The hub stack above "
                   "(capture, gather, pq, wfc, collective) moves N with it (generator re-stack).")

    # ---- WFC stage kit: priced pins
    w = by["sp_wfc"]; w["version"] = 16
    w["kit_of_record"] = "dsfd_wfc_stg #(.VM_LINK(1), .VMRQ(64), .WOUTW(8), .POSTED(1), .RD2(1), .HEP(layer in 37/38/39)) = the PRICED kit (tb_mtp_wave_dies.sv:96)"
    w["pin_changes_v16"] = {"t_srd": "15 -> 31 b ({v1, a1[14:0], a0[14:0]}); group t_sw_sr 544 -> 560",
                            "f_srq": "513 -> 1026 b ({rv1, rq1[511:0], rv, rq[511:0]}); group f_sw_sr 516 -> 1029",
                            "t_ft[3:0]": "NEW: kit fault flags to the die fault collector (host f_wfc_ft); was a tied-off functional port",
                            "t_hep[35:0]": "NEW on the layer 37 / 38 / 39 stage dies only (HEP 1), to ot_dsrom_mtp_hrow_tx",
                            "generator": "--wfc-priced (tools/dsrom_s81_fulldie.py): WFC_FIELD_SPLIT + wfc_kit_buses at RD2 1"}
    w["view_status"] = ("no cluster: the three closed children (tokpipe_stg 190.41 sq, lnk 216 x 151.2, vmx 291.6 x 280.8) route M1..M7 "
                        "and vmx is closed only at the DEFAULT pins; vmx at the priced parameters is being rebuilt split <= 15k sinks "
                        "per root. Die M6 / M7 treat the three child footprints (698 um at the E end) as blocked; no hot die window "
                        "over the slot (c5: hub W face 0.022, E face 0.128), so no M5 re-route is asked.")

    # ---- SU slab (s81su 03:40 + 07:41): legacy kv / qb / sw lane tiles -> taps + engines
    su_old = [n for n in by if re.match(r"sp_su_s/(kv[01]|qb[0-3]|sw[0-7])$", n)]
    assert len(su_old) == 14, su_old
    reg = {"kv": [by[n] for n in su_old if "/kv" in n], "qb": [by[n] for n in su_old if "/qb" in n], "sw": [by[n] for n in su_old if "/sw" in n]}
    def region(rows):
        return [dict(x=r["origin"]["x"], y=r["origin"]["y"], w=r["outline"]["w"], h=r["outline"]["h"]) for r in rows]
    SU = [("kv", "dsfd_su_t_kvt", "s81su_kvt_ref", 4, (36.72, 453.6), "CLOSED +63.22 / +25.87; pins BIT-ordered (e_d[128 j + b] of all 32 positions in band b): the tap -> engine fan-out is 4,096 wires, ~2,050 across the mid-height cut on M7 (SU-internal)"),
          ("kv", "dsfd_su_t_kvq", "s81su_kvq_ref", 16, (259.2, 259.2), "CLOSED s81su_kvq_ref-v4-ebdb80f0e (closure-loop record on main)"),
          ("kv", "dsfd_su_t_kve", "s81su_kve_ref", 1, (124.2, 124.2), "CLOSED +56.64 / +3.23"),
          ("kv", "dsfd_su_t_kvp", "s81su_kvp_ref", 1, (151.2, 151.2), "CLOSED +60.82 / +1.87"),
          ("kv", "dsfd_su_t_kvr", "s81su_kvr_ref", 1, (140.4, 140.4), "CLOSED +84.25 / +1.95"),
          ("qb", "dsfd_su_t_qbt", "s81su_qbt_ref", 1, (572.4, 453.6), "CLOSED +101.46 / +11.81; DEFECTS open: 26 input endpoints 4 levels from dn_st (pin register), boundary spread > 80 ps"),
          ("qb", "dsfd_su_t_qbe", "s81su_qbe_sp8_ref", 8, (259.2, 259.2), "CLOSED +62.49 / +17.68"),
          ("sw", "dsfd_su_t_swt", "s81su_swt_ref", 1, (572.4, 453.6), "NOT CLOSED (DRT 5,067 violations, 434 unregistered input endpoints): RESERVE ONLY; becomes two half-tap columns dl / dh (36.72 x 453.6 each, own clock root); final outline follows the split RTL"),
          ("sw", "dsfd_su_t_swe", "s81su_swe_sp8_ref", 128, (216.0, 216.0), "CLOSED +128.43 / +15.08"),
          ("sw", "dsfd_su_t_qbe", "s81su_qbe_sp8_ref", 8, (259.2, 259.2), "CLOSED (SW quantiser = the qbe master)")]
    su_rows = []
    for grp, cell, kit, n, wh, st in SU:
        sz = _lef_size(kit, cell)
        posted = wh
        if sz and sz != wh:      # the closed LEF is the outline of record (the owner's 07:41 list was rounded / pre-lattice)
            wh = sz
        r = _row(tile, name=f"sp_su_s/{grp}/{cell}", cell=cell, kind="tile", parent="sp_su_s", outline={"w": wh[0], "h": wh[1]},
                 origin={"x": 0, "y": 0}, kit=kit, owner="el1013-s81su",
                 replicated={"count": n, "placement": "SU owner's sub_layout inside the reserved region(s) (origins not posted yet)"},
                 region_um=region(reg[grp]), view_status=st + ("" if sz else " | no view LEF on main")
                 + (f" | outline = closed LEF {wh[0]} x {wh[1]} (posted {posted[0]} x {posted[1]})" if wh != posted else ""),
                 notes=f"v16: replaces the legacy sp_su_s/{grp}* lane tiles; the legacy slot rectangles stay reserved as region_um. "
                       "Bench binding pending the tile-top gate s81su_tiles: not qualified yet.")
        su_rows.append(_clock(r, kit, cell))
    area = {g: sum(r["outline"]["w"] * r["outline"]["h"] * r["replicated"]["count"] for r in su_rows if r["name"].split("/")[1] == g) for g in reg}
    have = {g: sum(r["outline"]["w"] * r["outline"]["h"] for r in reg[g]) for g in reg}
    c["sub_layouts"]["sp_su_s_v16_fit"] = {g: dict(tiles_mm2=round(area[g] / 1e6, 4), region_mm2=round(have[g] / 1e6, 4),
                                                   fill=round(area[g] / have[g], 3)) for g in reg}
    su_short = {g: round((area[g] / 0.60 - have[g]) / 1e6, 3) for g in reg if area[g] / 0.60 > have[g]}   # 0.60 fill incl. channels
    c["sub_layouts"]["sp_su_s_v16_fit"]["short_mm2_at_0p60_fill"] = su_short
    c["sub_layouts"]["sp_su_s_v16_fit"]["verdict"] = (
        "MEASURED from the closed outlines x the posted counts: the kv and sw tile sets do NOT fit the legacy regions "
        "(fill > 1); sp_su_s (1,890 x 10,022.4) is NOT grown in v16 because no sub_layout was posted and the growth "
        "direction (N into the hub stack / corridor, or the --su-e E column) is a floorplan decision that needs it. "
        "The rows are reservations by master; the slab outline change is owed with the SU owner's sub_layout (v17).")

    # ---- HC W face (v15 relays-2 slot change, sent to el1013-s81hc.log)
    hc = by["sp_hc_s"]; hc["version"] = 16
    hc["w_face_v16"] = ("--lane-pins 2: wq_d[4095:0] and the 8 y_d slices (one 8,192-b port) stand on their straight VCH station lanes at "
                        "2-track pitch (M4), on both slabs; master frame (v15 run 4): wq_d y 1018.416..1411.536; y_d slice k at "
                        "4811.136 + 98.304 k .. +98.208; every other lane port of the W face moved with them (take the LEF; pins "
                        "below are refreshed from the v16 generator LEF). Cost: the HC root row (cpin / crooty / crootr) must take "
                        "wq_d / y_d at those y: HC owner's cluster relays; cut at the face 4,096 b / 393 um = 10.4 b/um on M4 "
                        "2-track = 0.50 of the M4 tracks under the pins (0.25 with M2+M4).")

    # ---- gather: pending
    g = by["sp_gather"]; g["version"] = 16
    g["view_status"] = ("PENDING (s81-gather): the slot 1727.976 x 803.496 cannot hold the flat cell (2,907,531 flops, 1.61 mm2 of std cells). "
                        "Storage redesign: step A (queue / pairing data in per-root 1r1w macros) needs 1727.976 x ~1,230 (+~430 N); step B "
                        "(pairing store indexed by {open-row slot, tree node}) fits THIS slot (~1.15 mm2) if <= 8 rows are open per root. "
                        "Measured on the die-layer vehicle: queue peak 10 of 128, pairing buffer peak 5 of 128 (synthetic field order). "
                        "DIE LEAD: slot UNCHANGED in v16 (step B is the design to build; capacity fault stays sticky / fail-closed); "
                        "if the real field order shows > 8 open rows, step A needs +430 um N and the hub column has NO such room after v16 "
                        "(v16 GEN: VM top 16,757, capture .. host stacked to y 22,746.9 of the 22,749.1 N strip; only the five ~172-um "
                        "station pockets between the slabs remain): it would cost the SU / VM stack or the pockets. "
                        "Pins: t_capture as 8 bundles on S at the capture's f_gather x centres (generator change owed with "
                        "the capture bundle split).")

    # ---- insert the new rows, drop the legacy SU rows
    out = []
    for s in c["slots"]:
        if s["name"] in su_old:
            if s["name"] == su_old[0]:
                out.extend(su_rows)
            continue
        out.append(s)
        out.extend(r for after, r in new if after == s["name"])
    assert len(out) == len(c["slots"]) - 14 + len(su_rows) + len(new), (len(out), len(c["slots"]))
    c["slots"] = out
    names = [s["name"] for s in c["slots"]]; assert len(names) == len(set(names))

    # ---- die clock delivery rule (el1013-pinreg-audit.log 09:07)
    c["seam_rules"]["clock"] = ("v16 DIE CLOCK DELIVERY RULE: the die delivers the clock at tile X's clock pin at phi - R_X (R = "
                                "views/<cell>/insertion.json <corner>.boundary.mean, the sign-off reference), never a common phase at "
                                "the pins; tiles with R <= 300 ps share one level, a tile with R > 300 takes the trunk earlier by "
                                "R - 300 on its own tap and its hops are budgeted at SKEW 150 (623.3 ps) instead of 90 (683.3 ps); "
                                "boundary spread <= 80 ps is inside o + s and not compensatable; every bound view needs insertion.json "
                                "(tools/s81/die_sta.py kit: clock_delivery record; tools/hier_contract/pinreg_audit.py)")
    c["seam_rules"]["hop_budget_ps"] = {"setup": "o_A + 0.76 ps/um x L + s_B <= 833.3 - 60 - SKEW", "same_level": 683.3, "across_levels": 623.3,
                                        "hold": "l_A - h_B >= 100 ps at FF"}
    drop = ("v15 SU slot change", "v15 no closed slot-shaped view by name")
    c["open_items"] = [o for o in c.get("open_items", []) if not (isinstance(o, str) and o.startswith(drop))] + [
        "v16 capture / gather bundle pins (f_gather, t_capture as 8 bundles at the g2 column centres; t_vm under the x columns): generator change owed.",
        "v16 pq_root ports 68 / 71: generator PQ_TI / PQ_RO still 66 / 68; +3 b status relay to the column fault collector owed.",
        "v16 SU sub_layout origins (kvt / kvq / kve / kvp / kvr, qbt / qbe, swt / swe) owed by the SU owner; swt not closed (two half-tap split); qbt spread / pin-register defects. "
        "MISFIT: " + json.dumps(c["sub_layouts"]["sp_su_s_v16_fit"], sort_keys=True)[:600],
        "v16 sp_collective ce_s1..3 (cesn) child leaf slots follow the leaf verdicts; lane -> slice relays inside the cluster owed.",
        "v16 sp_gather: step B capacity answer (rows open per root on the real field order) owed; else +430 um N in v17.",
        "v16 dsfd_bf (s81-bf 07:39): tiles_direct request (2 x bf_col 450.144 + bf_front 100.224 in the same frame, two 1.188 um seam channels) NOT folded: LEF / lib exports and the compact199 compose STA are owed first.",
        "v16 no closed slot-shaped view by name for dsfd_bf, dsfd_pq_root, dsfd_sp_pq."]
    c["version"] = 16; c["updated"] = "2026-10-13 PT"
    c["changelog"].append({"version": 16, "when": "2026-10-13 PT", "change":
        "s81-die: (1) hrow: 4 die-placed leaf slots ing 129.6 sq x3 / hub 216 sq x1 / cbe, cbw 475.2 x 216 x15 each (coordinator 07:55), rep/hrow = "
        "container. (2) sp_collective: ce_s0 (ces0, closed) + ce_s1..3 (cesn parent) 302.4 x 341.28 as a 2 x 2 block. (3) sp_capture 129.576 -> "
        "561.6 tall cluster (+432.024). (4) q element row: real view + libs + bound PQ1 bench; M7 pockets kept. (5) pq_root 131.76 x 211.68, "
        "ports 68 / 71. (6) bgq28 501.12 -> 622.08 (16 slots re-stacked), new FE slot 1520.064 x 695.52, sp_vm 2730.216 -> 3343.656 (+613.44 N). "
        "(7) sp_wfc priced-kit pins t_srd 31 / f_srq 1026 / t_ft 4 / t_hep 36. (8) SU: 14 legacy kv / qb / sw lane-tile slots -> 10 per-master "
        "rows (kvt, kvq, kve, kvp, kvr, qbt, qbe, swt reserve, swe) inside the same regions. (9) HC W face on the VM / collective lanes "
        "(--lane-pins 2). (10) gather pending, slot unchanged. (11) seam_rules.clock = die clock delivery rule (insertion-compensated entry, "
        "tap levels at 300 ps, SKEW 150 on deep-tile hops). NEIGHBOUR COST: the hub column stack above the VM moves N by +613.44 (VM) and the "
        "stack above the capture by a further +432.024 (total +1,045.464 for gather / pq / wfc / collective): taken from the free band of the "
        "hub column, which is now FULL (v16 GEN: host top y 22,746.9 of 22,749.1; station pockets of ~172 um between pq / wfc / sseq / collective / host kept), die 33 x 26 mm unchanged; the hc_s <-> vm / collective straight lanes move with their slabs (GEN v16: hop gate 500 um, "
        "0 overlaps). No price changed; no closed tile re-shaped."})
    if a.pins_from:
        refresh_pins(c, a.pins_from)
    if a.check:
        print("ok (check only)", len(c["slots"]), "slots"); return 0
    CON.write_text(json.dumps(c, indent=1) + "\n"); print("v16 written", len(c["slots"]), "slots"); return 0


if __name__ == "__main__":
    sys.exit(main())
