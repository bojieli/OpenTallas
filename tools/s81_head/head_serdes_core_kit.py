#!/usr/bin/env python3
"""Build the existing KP4 Chien/Forney child without changing link latency.

HEAD's 422,040-cell SerDes contains one digital KP4 link. Its six analog
lanes are not six identical digital links. Harden the existing registered
``u_phy.u_link.u_dec.u_chn`` boundary first; 55 inverse tables alone account
for 128.8k cells. This is a die-local driver of the shared core generator,
with no new face registers and no claim that historical views are SIGNED.
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
MODULE = "ot_s81_kp4_dchn"
OUTLINE = [216.0, 194.4]
PORTS = {
    "W": [("k_v", 4), ("k_lo", 310), ("k_L", 5), ("k_any", 1)],
    "N": [("cw_q", 544), ("apply", 8), ("o_unc", 1), ("o_ne", 5), ("fs", 1)],
    "S": [("n_corr", 32), ("n_unc", 32)],
}
FILES = [f"rtl/dsrom_sys/s81_link/{f}" for f in
         ("ot_s81_kp4_common.sv", "ot_s81_kp4_dchn.sv", "ot_s81_gf1024.svh")]


def pins():
    """Regular face bands and centre clock/reset entries, on the plan lattice."""
    w, h = OUTLINE
    out = []
    for face, buses in PORTS.items():
        count = sum(n for _, n in buses)
        span = h if face in "WE" else w
        # 0.288 is six M4/M5 tracks; all coordinates use the 0.024 phase.
        step = 0.288
        start = round(((span - step * (count - 1)) / 2 - 0.024) / 0.048) * 0.048 + 0.024
        k = 0
        for bus, width in buses:
            for bit in range(width):
                pos = round(start + step * k, 4)
                x, y = (0, pos) if face == "W" else (pos, h if face == "N" else 0)
                out.append(dict(name=bus if width == 1 else f"{bus}[{bit}]",
                                x=x, y=y, layer="M4" if face in "WE" else "M5"))
                k += 1
    for name, delta in (("rst_n", 0), ("clk", 0.096)):
        x = round((w / 2 - 0.024) / 0.048) * 0.048 + 0.024 + delta
        out.append(dict(name=name, x=round(x, 4), y=h / 2, layer="M5"))
    return out


def interior_io(orig, G):
    def emit(pinlist, w, h, tag):
        inner = [p for p in pinlist if p["name"] in ("clk", "rst_n")]
        text, rows = orig([p for p in pinlist if p not in inner], w, h, tag)
        for p in inner:
            size = [0.048, 0.48] if p["name"] == "clk" else [0.024, 0.192]
            text += (f"place_pin -pin_name {{{p['name']}}} -layer M5 "
                     f"-location {{{p['x']:.4f} {p['y']:.4f}}} "
                     f"-pin_size {{{size[0]} {size[1]}}}\n")
            rows.append(dict(bus=p["name"], bit=None, x=p["x"], y=p["y"],
                             layer="M5", face="interior", size=size, clock=p["name"] == "clk"))
        return text, rows
    return emit


def inputs(plan, work):
    work.mkdir(parents=True, exist_ok=True)
    if plan.resolve().is_relative_to(ROOT):
        # A release-capable source profile must read its original pin table
        # from the pinned repository, not a generated /srv input path.
        pinfile = ROOT / "tools/s81_head/data/kp4_dchn_pins.json"
        if json.loads(pinfile.read_text()) != pins():
            raise SystemExit("tracked KP4 Chien pin table differs from the declared core shape")
    else:
        pinfile = work / "dchn_pins.json"
        pinfile.write_text(json.dumps(pins(), indent=1) + "\n")
    views = dict(plan=str(plan.resolve()), view_list=[dict(
        view=f"{MODULE}@head", module=MODULE, outline_um=OUTLINE,
        pins_file=str(pinfile.resolve()), pins_sha256=hashlib.sha256(pinfile.read_bytes()).hexdigest(),
        instances=["u_phy.u_link.u_dec.u_chn"], placed=1, recipe_keys=[MODULE])])
    vf = work / "views.json"
    vf.write_text(json.dumps(views, indent=1) + "\n")
    return vf


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("rest", nargs="*")
    a = ap.parse_args()
    out = Path(a.out).resolve()
    vf = inputs(Path(a.plan), out / "_inputs")
    spec = importlib.util.spec_from_file_location(
        "head_core_shared", ROOT / "physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py")
    G = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(G)
    G.io_tcl = interior_io(G.io_tcl, G)
    sys.argv = ["gen_core_kit_hbm", "--views", str(vf), "--view", f"{MODULE}@head",
                "--out", str(out), "--recipe-key", MODULE, "--face-shell", "off",
                "--core-insertion", "none", "--sigmax", "M5"] + a.rest
    commit = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    recipe = dict(top=MODULE, files=FILES, params={}, macros=[], source_commit=commit, read_at_commit=True,
                  synth_memory_max_bits=10240,
                  source="HEAD SerDes existing KP4 Chien/Forney child; no latency change")
    profile = dict(source_commit=commit, family="HEAD_KP4_DCHN_NATIVE", added_face_cycles=0,
                   qualification="UNROUTED_CANDIDATE", clock_ports=["clk"], reset_ports=["rst_n"],
                   endpoint_contract=dict(kind="INTERNAL_CORE", partition_rule="R2_INTERNAL_TIMED_IN_PARTITION",
                                          parent_partition="hd_serdes", instance="u_phy.u_link.u_dec.u_chn",
                                          source="rtl/dsrom_sys/s81_link/ot_s81_kp4_dchn.sv"))
    if not Path(a.plan).resolve().is_relative_to(ROOT):
        profile["diagnostic_inputs"] = True
    G.main(recipe_overrides={MODULE: recipe}, source_profile=profile)
    kd = out / re.sub(r"[^A-Za-z0-9_.-]", "_", f"{MODULE}@head")
    # The shared pin auditor supports interior entry ports; its old HBM
    # sibling projects them onto a face. Keep actual plan coordinates.
    import shutil
    shutil.copyfile(G.TOOL / "pin_audit.py", kd / "pin_audit_core.py")
    ppfile = kd / "plan_pins.json"
    if ppfile.exists():
        pp = json.loads(ppfile.read_text())
    else:
        # Source-profile kits retain their original table instead of emitting
        # the legacy canonical table. Publish the actual placed pin centres,
        # including the interior entries, for this driver as well.
        pp = dict(schema="opentallas.hbm_arch.core_plan_pins.v1", module=MODULE,
                  rule="actual io.tcl centres; centre clock/reset preserved", pins=[])
        for row in json.loads((kd / "pins.json").read_text()):
            name = row["bus"] if row["bit"] is None else f"{row['bus']}[{row['bit']}]"
            x, y = row["x"], row["y"]
            if row["face"] in ("W", "E"):
                x += G.PIN_LEN_UM / 2 if row["face"] == "W" else -G.PIN_LEN_UM / 2
            elif row["face"] in ("N", "S"):
                y += G.PIN_LEN_UM / 2 if row["face"] == "S" else -G.PIN_LEN_UM / 2
            pp["pins"].append(dict(name=name, layer=row["layer"], x=round(x, 4), y=round(y, 4)))
    byname = {p["name"]: p for p in pins()}
    for p in pp["pins"]:
        if p["name"] in ("clk", "rst_n"):
            p.update({k: byname[p["name"]][k] for k in ("x", "y")})
    body = json.dumps(pp, indent=1) + "\n"
    ppfile.write_text(body)
    fz = json.loads((kd / "freeze.json").read_text())
    fz["plan_pins_source"] = fz["pins_file"]
    fz["plan_pins_source_sha256"] = fz["pins_sha256"]
    fz["pins_file"] = "plan_pins.json"
    fz["pins_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    fz["pins_canon_sha256"] = G.plan_pins_canon_sha256(dict(pins=pp["pins"]), OUTLINE)
    fz["head_driver"] = dict(instance="u_phy.u_link.u_dec.u_chn", added_cycles=0,
                             kind="existing RTL hierarchy, same default MUT=0")
    fz["kit_hash"] = G.kit_hash(kd)
    (kd / "freeze.json").write_text(json.dumps(fz, indent=1) + "\n")
    print(json.dumps(dict(kit=str(kd), added_cycles=0, status="GENERATED_NOT_SIGNED")))


if __name__ == "__main__":
    main()
