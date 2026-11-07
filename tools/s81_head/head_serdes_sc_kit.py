#!/usr/bin/env python3
"""DIE-HEAD-76-SERDESRF: child kits of the hd_serdes SC form (rtl/dsrom_sys/s81_head/ot_s81hd_serdes_sc_cores.sv).

Two hard sub-core types inside the hd_serdes slot, next to the signed u_chn child (head_serdes_core_kit.py):
  tx   ot_s81hd_sc_tx   u_phy.u_link.u_tx                      ~115k cells, all IO on the S face (tx | e_flt | pma_tx)
  bmq  ot_s81hd_sc_bmq  u_phy.u_link.u_dec.u_syn.u_bm0..2      ~28k cells, inputs W face, outputs E face
Every face is a register in the RTL (no face shell); clock / reset are centre entries (METHODOLOGY 12.8a), as on u_chn.
Outlines fit the 150-um digital shore strip under the VDDPHY region (phy_pg.json y >= 150).
"""
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
L, T, H = "rtl/dsrom_sys/s81_link", "rtl/dsrom_sys/s81_head", "rtl/hbm_accel/cores_split/reform_1104b"
CHILD = {
    "tx": dict(module="ot_s81hd_sc_tx", outline=[388.8, 120.96], inst=["u_phy.u_link.u_tx"],
               ports={"S": [("tx", 512), ("e_flt", 1), ("pma_tx", 544)]}, clk="clk", rst="rst",
               files=[f"{T}/ot_s81hd_serdes_sc_cores.sv", f"{H}/ot_s81_kp4_enc_la.sv", f"{L}/ot_s81_kp4_common.sv",
                      f"{L}/ot_pdie_serdes.sv", f"{L}/ot_s81_gf1024.svh", f"{L}/ot_s81_kp4_enc_mat.svh",
                      f"{H}/ot_s81_kp4_enc_ff_mat.svh", f"{H}/ot_s81_kp4_enc_la2_mat.svh"],
               note="ot_s81_kp4_enc_la LA 2 FF 1 (HBM serdes_tx form) + pma_bm; pma_tx +2 ck edges"),
    "bmq": dict(module="ot_s81hd_sc_bmq", outline=[95.04, 103.68],
                inst=[f"u_phy.u_link.u_dec.u_syn.u_bm{i}" for i in range(3)],
                ports={"W": [("ld_i", 4), ("S_i", 300)],
                       "E": [("lam", 160), ("om", 150), ("L", 5), ("any", 1), ("done", 4)]}, clk="clk", rst="rs_n",
                files=[f"{T}/ot_s81hd_serdes_sc_cores.sv", f"{L}/ot_s81_kp4_bm.sv", f"{L}/ot_s81_kp4_common.sv",
                       f"{L}/ot_s81_gf1024.svh"],
                note="RXQ ldq/S_b relay + one RiBM unit (THC 1); 0 added cycles"),
}


def pins(c):
    """Regular face bands (0.288 = six M4/M5 tracks, 0.024 phase) and centre clock/reset entries."""
    w, h = c["outline"]
    out = []
    for face, buses in c["ports"].items():
        count = sum(n for _, n in buses)
        span = h if face in "WE" else w
        step = 0.288
        if step * (count - 1) > span - 2.0:
            raise SystemExit(f"{c['module']}: {count} pins do not fit the {face} face ({span} um)")
        start = round(((span - step * (count - 1)) / 2 - 0.024) / 0.048) * 0.048 + 0.024
        k = 0
        for bus, width in buses:
            for bit in range(width):
                pos = round(start + step * k, 4)
                x, y = {"W": (0, pos), "E": (w, pos), "N": (pos, h), "S": (pos, 0)}[face]
                out.append(dict(name=bus if width == 1 else f"{bus}[{bit}]", x=x, y=y,
                                layer="M4" if face in "WE" else "M5"))
                k += 1
    for name, delta in ((c["rst"], 0), (c["clk"], 0.096)):
        x = round((w / 2 - 0.024) / 0.048) * 0.048 + 0.024 + delta
        out.append(dict(name=name, x=round(x, 4), y=round(h / 2, 4), layer="M5"))
    return out


def interior_io(orig, c):
    def emit(pinlist, w, h, tag, *args, **kw):
        inner = [p for p in pinlist if p["name"] in (c["clk"], c["rst"])]
        text, rows = orig([p for p in pinlist if p not in inner], w, h, tag, *args, **kw)
        for p in inner:
            size = [0.048, 0.48] if p["name"] == c["clk"] else [0.024, 0.192]
            text += (f"place_pin -pin_name {{{p['name']}}} -layer M5 "
                     f"-location {{{p['x']:.4f} {p['y']:.4f}}} "
                     f"-pin_size {{{size[0]} {size[1]}}}\n")
            rows.append(dict(bus=p["name"], bit=None, x=p["x"], y=p["y"],
                             layer="M5", face="interior", size=size, clock=p["name"] == c["clk"]))
        return text, rows
    return emit


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--child", required=True, choices=sorted(CHILD))
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("rest", nargs="*")
    a = ap.parse_args()
    c = CHILD[a.child]
    M = c["module"]
    out = Path(a.out).resolve()
    work = out / "_inputs"
    work.mkdir(parents=True, exist_ok=True)
    pinfile = work / f"{a.child}_pins.json"
    pinfile.write_text(json.dumps(pins(c), indent=1) + "\n")
    vf = work / "views.json"
    vf.write_text(json.dumps(dict(plan=str(Path(a.plan).resolve()), view_list=[dict(
        view=f"{M}@head", module=M, outline_um=c["outline"], pins_file=str(pinfile),
        pins_sha256=hashlib.sha256(pinfile.read_bytes()).hexdigest(), instances=c["inst"], placed=len(c["inst"]),
        recipe_keys=[M])]), indent=1) + "\n")
    sys.path.insert(0, str(ROOT / "physical/die_plan/hbm_arch_cores"))   # generator sibling modules (static_id_contracts)
    spec = importlib.util.spec_from_file_location(
        "head_core_shared", ROOT / "physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py")
    G = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(G)
    G.io_tcl = interior_io(G.io_tcl, c)
    sys.argv = ["gen_core_kit_hbm", "--views", str(vf), "--view", f"{M}@head", "--out", str(out),
                "--recipe-key", M, "--face-shell", "off", "--core-insertion", "none", "--sigmax", "M5"] + a.rest
    commit = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    recipe = dict(top=M, files=c["files"], params={}, macros=[], source_commit=commit, read_at_commit=True,
                  synth_memory_max_bits=10240, source=f"HEAD SerDes SC form child: {c['note']}")
    profile = dict(source_commit=commit, family="HEAD_SERDES_SC", added_face_cycles=0,
                   qualification="UNROUTED_CANDIDATE", clock_ports=[c["clk"]], reset_ports=[c["rst"]],
                   endpoint_contract=dict(kind="INTERNAL_CORE", partition_rule="R2_INTERNAL_TIMED_IN_PARTITION",
                                          parent_partition="hd_serdes", instance=c["inst"][0],
                                          source=c["files"][0]))
    if not Path(a.plan).resolve().is_relative_to(ROOT):
        profile["diagnostic_inputs"] = True
    G.main(recipe_overrides={M: recipe}, source_profile=profile)
    kd = out / re.sub(r"[^A-Za-z0-9_.-]", "_", f"{M}@head")
    import shutil
    shutil.copyfile(G.TOOL / "pin_audit.py", kd / "pin_audit_core.py")
    ppfile = kd / "plan_pins.json"
    if ppfile.exists():
        pp = json.loads(ppfile.read_text())
    else:
        pp = dict(schema="opentallas.hbm_arch.core_plan_pins.v1", module=M,
                  rule="actual io.tcl centres; centre clock/reset preserved", pins=[])
        for row in json.loads((kd / "pins.json").read_text()):
            name = row["bus"] if row["bit"] is None else f"{row['bus']}[{row['bit']}]"
            x, y = row["x"], row["y"]
            if row["face"] in ("W", "E"):
                x += G.PIN_LEN_UM / 2 if row["face"] == "W" else -G.PIN_LEN_UM / 2
            elif row["face"] in ("N", "S"):
                y += G.PIN_LEN_UM / 2 if row["face"] == "S" else -G.PIN_LEN_UM / 2
            pp["pins"].append(dict(name=name, layer=row["layer"], x=round(x, 4), y=round(y, 4)))
    byname = {p["name"]: p for p in pins(c)}
    for p in pp["pins"]:
        if p["name"] in (c["clk"], c["rst"]):
            p.update({k: byname[p["name"]][k] for k in ("x", "y")})
    body = json.dumps(pp, indent=1) + "\n"
    ppfile.write_text(body)
    fz = json.loads((kd / "freeze.json").read_text())
    fz["plan_pins_source"] = fz["pins_file"]
    fz["plan_pins_source_sha256"] = fz["pins_sha256"]
    fz["pins_file"] = "plan_pins.json"
    fz["pins_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    fz["pins_canon_sha256"] = G.plan_pins_canon_sha256(dict(pins=pp["pins"]), c["outline"])
    fz["head_driver"] = dict(instance=c["inst"], added_cycles=0 if a.child == "bmq" else "pma_tx +2 ck edges",
                             kind="DIE-HEAD-76-SERDESRF SC form child")
    fz["kit_hash"] = G.kit_hash(kd)
    (kd / "freeze.json").write_text(json.dumps(fz, indent=1) + "\n")
    print(json.dumps(dict(kit=str(kd), child=a.child, status="GENERATED_NOT_SIGNED")))


if __name__ == "__main__":
    main()
