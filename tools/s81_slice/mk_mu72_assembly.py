#!/usr/bin/env python3
"""Compose actual selected72 MU hierarchy; emit placement/source assembly, no view claims.

--normal-spec must be the CAP5 normal spec (3c4721d69), not an old parent view.
Normal hard descendants are flattened under u_sl; unavailable views stay visibly
unbound. This is an input for ongoing die GEN, not a new gate or validator.
"""
import argparse
import copy
import json
from pathlib import Path

CLOCKS = ["ck_S", "ck_K", "ck_L0", "ck_L1", "ck_L3", "ck_L4",
          "ck_CAP_RT", "ck_CAP_CW", "ck_CAP_CE", "ck_CAP_RN", "ck_CAP_RS"]
ROLES = {
    "u_ln0": ([1468.8,43.2], [725.76,583.2]),
    "u_ln1": ([1468.8,799.2], [725.76,583.2]),
    "u_lep": ([1468.8,1555.2], [561.6,561.6]),
    "u_land": ([1468.8,2289.6], [475.2,216.0]),
}

def assemble(normal, flavor, bindings):
    top = f"ot_s81sl_slice_{flavor}_72"
    side = "w" if flavor == "lepw_mu" else "e"
    children = []
    for child in normal["children"]:
        c = copy.deepcopy(child)
        c["inst"] = "u_sl." + c["inst"]
        c["at"] = [round(c["at"][0]+43.2,3), round(c["at"][1]+43.2,3)]
        children.append(c)
    modules = {"u_ln0":f"dsfd_coll_lane_{side}_safe8_ntf",
               "u_ln1":f"dsfd_coll_lane_{side}_safe8_ntf",
               "u_lep":"ot_s81sl_lep_mu_h" if flavor == "lepe_mu" else "ot_s81sl_lep_mu_a",
               "u_land":"dsdv_mu_land"}
    for inst,(at,envelope) in ROLES.items():
        c = dict(inst=inst, master=modules[inst], at=at, reserved_envelope_um=envelope,
                 count=1, orient="R0")
        if modules[inst] in bindings:
            c.update(copy.deepcopy(bindings[modules[inst]]))
        else:
            c["binding_state"] = "UNBOUND: preserve exact actual child view; never old-parent alias"
        children.append(c)
    return dict(schema="opentallas.s81_mu72.assembly.v1", top=top,
        source=f"rtl/dsrom_sys/s81_dv/slice/mu72/{top}.sv",
        sources=[f"rtl/dsrom_sys/s81_dv/slice/mu72/{top}.sv"]+normal["sources"]+[
            "rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv",
            "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv",
            "rtl/dsrom_sys/s81_dv/slice/dsdv_mu_land.sv"],
        defines=normal.get("defines", []),
        define_values=normal.get("define_values", {}),
        compiler_defines={"OT_S81_CAP5_C":"1"},
        normal_parameters=normal["params"],
        source_dependencies={"normal":"663783aa82568d6a8d029e2ac88f65878b004e9d",
                             "normal_spec":"3c4721d69ddab3724a65c96259143faf778fe172",
                             "original_endpoint_lp":"aefbb0ca375332e55b7983b1a4da7fe40f832960",
                             "safe8_lanes":"445e6c74c"},
        outline=dict(w=2505.6,h=6825.6,exact=True), hardened=False,
        normal_source_envelope=dict(inst="u_sl",at=[43.2,43.2],outline=[1252.8,6739.2],
            hardened=False, note="Use actual hard descendants below; normal parent closure is not required for diagnostic integration"),
        children=children, clock_ports=CLOCKS, reset_port="rst_n",
        clock_connections={"u_sl.ck_C":"ck_S",**{f"u_sl.{c}":c for c in CLOCKS if c not in ("ck_S","ck_K")},
                           **{f"{i}."+("ck" if i.startswith("u_ln") else "clk"):"ck_K" for i in ROLES}},
        transport=dict(existing_S_to_K_cycles=3,existing_K_to_S_cycles=3,
                       existing_fault_output_cycles=2,CAP5_capture_increment_vs_CAPC2=12,
                       new_K_transport_cycles=None),
        unclosed_bundles=[
            dict(ends=["u_ln0","u_lep"],nets=["l0v","l0r","l0d[552:0]","i0v","i0r","i0d[552:0]","f0[2:0]","rxv[0]"],
                 centre_distance_um=[82.08,1501.2],state="UNLANDED long K transport; ready/data/status ages must align"),
            dict(ends=["u_ln1","u_lep"],nets=["l1v","l1r","l1d[552:0]","i1v","i1r","i1d[552:0]","f1[2:0]","rxv[1]"],
                 centre_distance_um=[82.08,745.2],state="UNLANDED long K transport; ready/data/status ages must align"),
            dict(ends=["u_lep","u_land"],nets=["mwv","mwd[1103:0]","mrv","mrd[1103:0]","mf"],
                 centre_distance_um=[43.2,561.6],state="UNLANDED long K transport; write/read calendar alignment owed")],
        physical_holds=["No parent CLOSED record or SS/FF/GRT claim",
                        "K clock is an explicit diagnostic implementation root; no balanced-region closure assumption",
                        "Actual lane/endpoint/MU-land relay and regional landing geometry pending",
                        "Actual child pins, clock/reset placement and PG composition feed ongoing die flow",
                        "External ports and source widths preserved; no tied functional ports or false paths",
                        "No copy-B/AB physical release alias: this two-lane envelope is copy-A only"])

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--normal-spec",type=Path,required=True)
    ap.add_argument("--bindings",type=Path,help="module -> exact child view/receipt dictionary; no automatic aliases")
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args(); normal=json.loads(a.normal_spec.read_text())
    bindings=json.loads(a.bindings.read_text()) if a.bindings else {}
    a.out.mkdir(parents=True,exist_ok=True)
    for f in ("lepe_mu","lepe_nh_mu","lepw_mu"):
        (a.out/f"{f}.json").write_text(json.dumps(assemble(normal,f,bindings),indent=2)+"\n")
if __name__=="__main__": main()
