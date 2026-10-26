#!/usr/bin/env python3
"""Candidate slot pins for the gather parent dsfd_sp_gather_c on the ACTUAL closed leaf heights (v21 transverse RE).

The die lead's v19 rule (tools/s81/v19_pins_1014.py gather()) is applied unchanged to the taller slot:
  * every data / clock port of the current v19 slot file keeps its face, layer and centre measured from the S / W end
    (t_capture / f_cd on S do not move; W / E pins keep their y, the slot grows only northwards);
  * ck_q[47:0] are re-assigned, one compensated entry per lane / result relay at the slot face nearest its ck pin,
    for the relay positions of gather_parent_spec.relay_children(geometry(actual leaf heights)).
This is a CANDIDATE for die-lead adoption (the die contract still carries 1728 x 803.52); it moves no closed view.
"""
import argparse, importlib.util, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gather_parent_spec as gps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot", default="physical/s81_die_pins/v19/dsfd_sp_gather_c.json")
    ap.add_argument("--out", default="physical/s81_die_pins/v21_gather_transverse_candidate")
    a = ap.parse_args()
    spec = importlib.util.spec_from_file_location("v19p", ROOT / "tools/s81/v19_pins_1014.py")
    v19p = importlib.util.module_from_spec(spec); spec.loader.exec_module(v19p)
    cur = json.loads((ROOT / a.slot).read_text())
    leaf_h = gps.leaf_heights()
    geo = gps.geometry(leaf_h)
    W, H = cur["outline_um"][0], geo["outline_h"]
    relays = gps.relay_children(geo)
    RV = {m: v19p.lef_bits(f"physical/ref_tile/s81_rly_{m[9:].lower()}/views/{m}/{m}.lef") for m in
          ("dsfd_rly_276_WE", "dsfd_rly_276_EW", "dsfd_rly_214_NS")}
    slot = {p: [list(b) for b in v["per_bit"]] for p, v in cur["ports"].items() if p != "ck_q"}
    P = v19p.P
    occ = {}
    for v in slot.values():
        for b in v:
            occ.setdefault((b[0], b[1]), set()).add(round(b[2] / P))
    ckq, ent = [], []
    for r in relays:
        (_, _), rp = RV[r["master"]]
        f, ly, cx, cy = rp["ck"][0]
        px, py = r["at"][0] + cx, r["at"][1] + cy
        d = {"W": px, "E": W - px, "S": py, "N": H - py}
        face = min(d, key=d.get)
        c = py if face in "WE" else px
        lay = "M4" if face in "WE" else "M5"
        s = occ.setdefault((face, lay), set())
        k = round(c / P)
        while any(abs(k - o) < 2 for o in s):
            k += 1
        s.add(k)
        ckq.append([face, lay, round(k * P, 3), 0.192])
        ent.append(dict(port=r["clock"], child=f"{r['inst']} ({r['master']}).ck", parent_face=face,
                        entry_wire_manhattan_um=round(d[face] + abs(k * P - c), 1)))
    slot["ck_q"] = ckq
    extra = {k: cur[k] for k in ("clock_entries", "unchanged_from_v18", "removed") if k in cur}
    extra.update(ck_q_entries=ent, source_slot_file=a.slot, leaf_h_um=leaf_h, row_y_um=geo["row_y"],
                 relay_plan="tools/s81_ph/gather_parent_spec.relay_children(geometry(actual leaf heights))",
                 status="CANDIDATE for S81 die-lead adoption: slot grows N by %.2f um; die contract still 803.52" % (H - cur["outline_um"][1]))
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    fn = v19p.write(out, "dsfd_sp_gather_c", [W, H], slot, "ck", "v19 die-lead slot rule on the actual leaf heights: all v19 slot "
                    "pins unchanged from the S / W end, ck_q[47:0] at the face nearest each relay ck pin", "v21_gather_transverse", extra)
    rec = json.loads(fn.read_text())
    rec["source"] = "tools/s81_ph/gather_v21_slot_pins.py (v19 die-lead rule, gather owner candidate)"
    fn.write_text(json.dumps(rec, indent=1) + "\n")
    # Die-level placement list (parent frame) for the flattened option: the parent is wires-only, so under the
    # owner's two-level rule its 214 hard children can be placed by the die directly (no parent route).
    plan = json.loads((ROOT / "physical/s81_ph_views/gather/v21/strip_plan.json").read_text())
    kids = {f"u_l_{g}_{k}": dict(master="dsfd_gth_rw" if g < 4 else "dsfd_gth_re", at=[gps.LEAF_X[g], geo["row_y"][k]],
                                 clock=f"ck_l[{4 * g + k}]") for g in range(8) for k in range(4)}
    kids["u_ctl"] = dict(master="dsfd_gth_ctl", at=[1598.4, 8.64], clock="ck")
    kids.update({r["inst"]: dict(master=r["master"], at=r["at"], clock=r["clock"]) for r in relays})
    kids.update({r["instance"]: dict(master=r["master"], at=r["origin_um"], clock=r["clock_entry"]["port"]) for r in plan["relay_children"]})
    (out / "layout_gather.json").write_text(json.dumps(dict(
        schema="opentallas.s81.subslots.v1", parent=f"dsfd_sp_gather_c (gather v4 direct, transverse RE) {W} x {H}",
        case="v21_gather_transverse", owner="S-GATHER candidate for the S81 die lead", leaf_h_um=leaf_h,
        row_y_um=geo["row_y"], children=kids, n_children=len(kids)), indent=1) + "\n")
    print(f"GATHER_V21_SLOT outline [{W}, {H}] ck_q max entry {max(e['entry_wire_manhattan_um'] for e in ent)} um -> {fn}")


if __name__ == "__main__":
    main()
