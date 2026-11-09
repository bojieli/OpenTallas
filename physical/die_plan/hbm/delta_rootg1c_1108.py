#!/usr/bin/env python3
"""HBM plan event ROOTG1C-1108 (DIE-HBM-92-OPEN/ROOTG1C 11-08, DIE-HBM-92 ruling (c)).

Hard core ot_wbq_root_g1 (216 x 129.6, 4 lane payloads of 128 words x 256 bits).  The 91.8-um payload master
ot_sram_1r1w_128x256_m1_r0c0_g256 has no routable orientation in this slot for g1:
  * R0/MY tower (vG3): one port edge faces away from its logic, 1024 bits cross the tower, GRT overflow 9887 (M6 157 %);
  * R90 (vR90, vR90b): every M4 edge pin lands on one M4 row under the M4 OBS, DRT-0073 (never rotate ot_sram_1r1w_*);
  * a facing 2 x 2 at 128x256 needs 259.2 um, the slot cannot grow (g0 abuts W, u_mu_fused_* 17.28 um E).
Form (c): each lane payload is two ot_sram_1r1w_128x128_m1_r0c0_g128 halves (53.16 x 27.576; RTL ot_wbq_root_payload_ps in
rtl/hbm_accel/cores_split/reform_1105b/ot_wbq_split.sv, lo = bits 127:0, hi = bits 255:128), in two facing 4-row towers:
  left  R0 at x 30.252 (write edge E), right MY at x 113.388 (write edge W): a 29.976-um write channel over the S wd window;
  rows y 14.892 / 42.492 / 70.092 / 97.692 (pitch 27.6), lane i = row i; read edges face the W / E strips.
Every origin is on 0.012 mod 0.048, so every M4 edge pin (master y = 0.012 mod 0.048) sits on an M4 track.

Changes (nothing else):
  1. core_macros.json: cores["ot_wbq_root_g1"].macros -> the 8 halves above (status KNOWN, outline unchanged 216 x 129.6,
     channel_rule_um unchanged), basis note.
  2. SHA256SUMS: the core_macros.json row (if listed) and a row for the receipt.
  3. receipt rootg1c_1108_event.json.
die_plan.json, pins tables, clock, stations, buses: untouched.  PIN CYCLES 0, pin changes 0, outline unchanged.
ot_wbq_root_g0 (the same 4 x 128x256 2 x 2 entry) is untouched.

usage: delta_rootg1c_1108.py BASE_PLAN_DIR OUT_DIR
OUT_DIR is made by hard-linking every file of BASE_PLAN_DIR; a changed file is unlinked first and written new (a hard-linked
base file is never written through).  Re-runnable: an OUT_DIR that holds this event's receipt is rebuilt from scratch;
any other existing OUT_DIR is refused."""
import copy
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

EVENT = "ROOTG1C-1108"
MOD = "ot_wbq_root_g1"
OUTLINE = [216.0, 129.6]
CORE_BOX = [4.32, 4.32, 211.68, 125.28]
OLD_MASTER = "ot_sram_1r1w_128x256_m1_r0c0_g256"
NEW_MASTER = "ot_sram_1r1w_128x128_m1_r0c0_g128"
MW, MH = 53.16, 27.576
XL, XR = 30.252, 113.388
YS = [14.892, 42.492, 70.092, 97.692]
PITCH_M4 = 0.048
RESIDUE = 0.012
CHANNEL_RULE = 10.8
RECEIPT = "rootg1c_1108_event.json"
TAG = (f"DIE-HBM-92-OPEN/ROOTG1C {EVENT} (DIE-HBM-92 ruling (c)): {MOD} payload width split, 4 x {OLD_MASTER} -> "
       f"8 x {NEW_MASTER} in two facing 4-row towers (left R0 x {XL}, right MY x {XR}, 29.976-um write channel), "
       f"outline/pins unchanged, 0 pin cycles")


def r4(v):
    return round(float(v) + 0.0, 4)


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def new_macros():
    out = []
    for i, y in enumerate(YS):
        for half, x, o in (("lo", XL, "R0"), ("hi", XR, "MY")):
            out.append(dict(name=f"u_fcore.u_grp.g_lane[{i}].u_payload.u_{half}", master=NEW_MASTER, orient=o,
                            rect_um=[r4(x), r4(y), r4(x + MW), r4(y + MH)]))
    return out


def check_geometry(macros):
    """legal: inside the core box, no overlap, channel >= the 10.8 rule, every origin on the M4 track residue, no 90-deg."""
    for m in macros:
        x0, y0, x1, y1 = m["rect_um"]
        if m["orient"] not in ("R0", "MX", "MY", "R180"):
            raise SystemExit(f"{EVENT}: {m['name']} orient {m['orient']} (ot_sram_1r1w_* must not rotate 90 deg)")
        if not (CORE_BOX[0] - 1e-6 <= x0 and x1 <= CORE_BOX[2] + 1e-6 and CORE_BOX[1] - 1e-6 <= y0 and y1 <= CORE_BOX[3] + 1e-6):
            raise SystemExit(f"{EVENT}: {m['name']} {m['rect_um']} leaves the core box {CORE_BOX}")
        for v in (x0, y0):
            res = round((v - RESIDUE) / PITCH_M4, 6)
            if abs(res - round(res)) > 1e-6:
                raise SystemExit(f"{EVENT}: {m['name']} origin {v} not on {RESIDUE} mod {PITCH_M4}")
    for a in range(len(macros)):
        for b in range(a + 1, len(macros)):
            p, q = macros[a]["rect_um"], macros[b]["rect_um"]
            if p[0] < q[2] - 1e-6 and q[0] < p[2] - 1e-6 and p[1] < q[3] - 1e-6 and q[1] < p[3] - 1e-6:
                raise SystemExit(f"{EVENT}: {macros[a]['name']} overlaps {macros[b]['name']}")
    channel = r4(XR - (XL + MW))
    if channel < CHANNEL_RULE:
        raise SystemExit(f"{EVENT}: channel {channel} < {CHANNEL_RULE}")
    return channel


def apply_core_macros(CM):
    C = copy.deepcopy(CM)
    e = C.get("cores", {}).get(MOD)
    if e is None:
        raise SystemExit(f"{EVENT}: core_macros has no {MOD}")
    if [r4(v) for v in e.get("outline_um", [])] != OUTLINE:
        raise SystemExit(f"{EVENT}: {MOD} outline {e.get('outline_um')} != {OUTLINE}")
    old = e.get("macros") or []
    masters = sorted({m.get("master") for m in old})
    if len(old) != 4 or masters != [OLD_MASTER]:
        raise SystemExit(f"{EVENT}: {MOD} base macros are not 4 x {OLD_MASTER}: {len(old)} {masters}")
    new = new_macros()
    channel = check_geometry(new)
    e["macros"] = new
    e["status"] = "KNOWN"
    e["basis"] = TAG
    e["channel_rule_um"] = e.get("channel_rule_um", CHANNEL_RULE)
    C["note"] = (C.get("note") or "") + " | " + TAG
    return C, old, new, channel


def hardlink_tree(src, dst):
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        od = dst if rel == "." else dst / rel
        od.mkdir(parents=True, exist_ok=True)
        for f in files:
            os.link(os.path.join(root, f), od / f)


def write_new(p, text):
    if p.exists() or p.is_symlink():
        p.unlink()
    p.write_text(text)


def run(base, out):
    base, out = Path(base).resolve(), Path(out).resolve()
    if not (base / "core_macros.json").is_file() or not (base / "die_plan.json").is_file():
        raise SystemExit(f"{EVENT}: {base} is not a plan dir (core_macros.json / die_plan.json)")
    if out.exists():
        if not (out / RECEIPT).is_file():
            raise SystemExit(f"{EVENT}: {out} exists and is not an output of this event")
        shutil.rmtree(out)
    hardlink_tree(base, out)
    CM = json.loads((base / "core_macros.json").read_text())
    C, old, new, channel = apply_core_macros(CM)
    write_new(out / "core_macros.json", json.dumps(C, indent=1) + "\n")
    P = json.loads((base / "die_plan.json").read_text())
    rows = [(tk, hc["inst"]) for tk, t in P["partition_types"].items() for hc in t.get("hard_cores") or []
            if hc.get("module") == MOD]
    rc = dict(schema="opentallas.hbm_plan_event.v1", event=EVENT, tag=TAG, base_dir=str(base),
              base_sha256={"die_plan.json": sha_file(base / "die_plan.json"),
                           "core_macros.json": sha_file(base / "core_macros.json")},
              out_sha256={"die_plan.json": sha_file(out / "die_plan.json"),
                          "core_macros.json": sha_file(out / "core_macros.json")},
              module=MOD, plan_rows=len(rows), plan_types=sorted({t for t, _ in rows}), old_macros=old, new_macros=new,
              channel_um=channel, pin_changes=0, pin_cycles=0, outline_um=OUTLINE, die_plan_changed=False,
              rtl="rtl/hbm_accel/cores_split/reform_1105b/ot_wbq_split.sv: ot_wbq_root_g1 -> ot_wbq_root_grp_ps "
                  "(ot_wbq_root_payload_ps = 2 x " + NEW_MASTER + ")",
              macro_views="physical/asap7_memory_macros_v2/" + NEW_MASTER + " (tools/mem_compiler/build_hbm_rootg1c_1108.py)")
    write_new(out / RECEIPT, json.dumps(rc, indent=1) + "\n")
    sums = out / "SHA256SUMS"
    lines = sums.read_text().splitlines() if sums.is_file() else []
    keep = [l for l in lines if l.split()[-1:] not in (["core_macros.json"], [RECEIPT])]
    listed = any(l.split()[-1:] == ["core_macros.json"] for l in lines)
    if listed:
        keep.append(f"{sha_file(out / 'core_macros.json')}  core_macros.json")
    keep.append(f"{sha_file(out / RECEIPT)}  {RECEIPT}")
    write_new(sums, "\n".join(keep) + "\n")
    if out.joinpath("die_plan.json").stat().st_ino != base.joinpath("die_plan.json").stat().st_ino:
        raise SystemExit(f"{EVENT}: die_plan.json is not the base hard link")
    return rc


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    rc = run(argv[1], argv[2])
    print(json.dumps(dict(event=EVENT, out=argv[2], plan_rows=rc["plan_rows"], plan_types=rc["plan_types"],
                          channel_um=rc["channel_um"], macros=len(rc["new_macros"]),
                          core_macros=rc["out_sha256"]["core_macros.json"])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
