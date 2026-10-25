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

CLOCKS = ["ck_S", "ck_K", "ck_ML", "ck_L0", "ck_L1", "ck_L3", "ck_L4",
          "ck_CAP_RT", "ck_CAP_CW", "ck_CAP_CE", "ck_CAP_RN", "ck_CAP_RS"]
ROLES = {
    "u_ln0": ([1468.8,43.2], [725.76,583.2]),
    "u_ln1": ([1468.8,799.2], [725.76,583.2]),
    "u_lep": ([1468.8,1555.2], [561.6,561.6]),
    "u_land": ([1468.8,2289.6], [475.2,216.0]),
}
# G3 (LEAD-S81-G3 10-21, FAM-S81-LEPENH): E-end tops (lepe_mu / lepe_nh_mu) place the lep MY at the slice ri_e/ro_e
# height (k8a pin_ranges ri_e 2309.6..2788.6 + ro_e ..3267.6, +43.2 parent offset -> centre 2829.6) so ro/ri face u_sl,
# and both lanes beside the lep (E of it, W faces abutting the lep lane face; ln0 below / ln1 above the lep centre),
# MU land N of the lep with the 172.8 ring corridor.  Outline 2505.6 -> 2851.2 wide (no squeeze).  lepw keeps ROLES.
ROLES_E = {
    "u_ln0": ([2073.6,2203.2], [725.76,583.2], "R0"),
    "u_ln1": ([2073.6,2894.4], [725.76,583.2], "R0"),
    "u_lep": ([1468.8,2548.8], [561.6,561.6], "MY"),
    "u_land": ([1468.8,3283.2], [475.2,216.0], "R0"),
}
# S81-LINK5 (owner 10-21 06:00, 5th lane pair): lepw_mab_mu = s_0N copy-A/B end (ot_s81sl_lep_mu_ab, 4 lanes), the W-end
# mirror of ROLES_E: u_sl at the E side (its E face = parent E face: ring ri_e/ro_e to s_7N), the lep R0 W of u_sl with its
# E face (ro/ri) facing the slice ri_w/ro_w pins across the 172.8 landing-bank corridor, all four lanes R0 in one W column
# (tx/rx on the lane W faces = parent W face toward the die-W SerDes; lo/li on the lane E faces abutting the lep W face,
# 51.84 gap).  Four 583.2 lanes cannot abut a 691.2 lep face, so the lep reservation is TALL (561.6 x 1987.2 = kit
# outline 475.2 x 1900.8 + 43.2 halo; pair A AND pair B lane pins on the lep W face, ~2.3 pins/um): the s81sl_lepmu kit
# (475.2 x 691.2, pair B on S) must be re-floorplanned to this shape before its gate (enlarge, no squeeze).  Lanes stacked
# 626.4 pitch centred on the lep; outer lanes overlap the lep face 345.6.  MU land N of the lep with the 172.8 corridor.
ROLES_WAB = {
    "u_ln0": ([43.2,1490.4], [725.76,583.2], "R0"),
    "u_ln1": ([43.2,2116.8], [725.76,583.2], "R0"),
    "u_ln2": ([43.2,2743.2], [725.76,583.2], "R0"),
    "u_ln3": ([43.2,3369.6], [725.76,583.2], "R0"),
    "u_lep": ([820.8,1728.0], [561.6,1987.2], "R0"),
    "u_land": ([820.8,3888.0], [475.2,216.0], "R0"),
}
OUTLINE = {"lepw_mu": 2505.6, "lepe_mu": 2851.2, "lepe_nh_mu": 2851.2, "lepw_mab_mu": 2851.2}
SL_AT = {"lepw_mab_mu": [1555.2, 43.2]}
G3_SOURCES = ["rtl/dsrom_sys/s81_dv/slice/landed/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_lp.sv",
              "rtl/dsrom_sys/s81_dv/slice/landed/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_lp_e6.sv",   # PORTFIX-DEAD D-CAPEND
              "rtl/dsrom_sys/s81_dv/slice/lp/ot_s81sl_capc5r.sv",
              "rtl/dsrom_sys/s81_dv/slice/lp/ot_s81sl_capc5r_e6.sv",
              "rtl/common/landed_parent/ot_pl_land_rst_copy.sv"]

def assemble(normal, flavor, bindings):
    top = f"ot_s81sl_slice_{flavor}_72"
    side = "w" if flavor.startswith("lepw") else "e"
    mab = flavor == "lepw_mab_mu"
    slx, sly = SL_AT.get(flavor, [43.2, 43.2])
    children = []
    for child in normal["children"]:
        c = copy.deepcopy(child)
        c["inst"] = "u_sl." + c["inst"]
        c["at"] = [round(c["at"][0]+slx,3), round(c["at"][1]+sly,3)]
        if c["inst"] == "u_sl.u_xg":
            # S81-RTLGAP/head 589110357: the cap5r_lp end slice instantiates u_xg as ot_s81sl_xg_xo (head XB egress, no
            # port/net/strap/cycle change). The old ot_s81sl_xg stand-in view is NOT this master -> UNBOUND until the
            # xg_xo view gates (never alias the old xg view onto the changed successor).
            c.pop("view", None)
            c.update(master="ot_s81sl_xg_xo",
                     binding_state="UNBOUND: ot_s81sl_xg_xo view to gate (S81-RTLGAP/head); never old ot_s81sl_xg alias")
        if c["inst"] == "u_sl.u_xr":
            # S81-LINK5B G7: S81-RTLGAP/ffn 59a8155d3 -- the cap5r_lp end slice instantiates u_xr as ot_s81sl_xrt1 (FFN row-pair
            # V transport, same ports). The old ot_s81sl_xr1 (xr1f) view is NOT this master -> UNBOUND until an xrt1 view closes.
            c.pop("view", None)
            c.update(master="ot_s81sl_xrt1",
                     binding_state="UNBOUND: ot_s81sl_xrt1 view owed (S81-RTLGAP/ffn); never old ot_s81sl_xr1 alias")
        if c["inst"] == "u_sl.u_cap":
            # S81-LINK5B G6: the cap5r_lp end slice instantiates u_cap as ot_s81sl_capc5r (region-landed reset ports).
            # The normal spec's capc5c view is NOT this master: bind the CLOSED capc5r view only via --bindings
            # (exact source), else UNBOUND (never alias the old capc5c view onto the successor).
            # S81/PORTFIX-DEAD D-CAPEND (10-25): the lep tops are 6-frame row ends: u_sl = c1x_k8_cap5r_lp_e6 -> u_cap =
            # ot_s81sl_capc5r_e6 (rt_e 140 b; lanes 6 / 7 had no frame).  Its own kit; never alias the capc5r view.
            c.pop("view", None)
            c["master"] = "ot_s81sl_capc5r_e6"
            if "ot_s81sl_capc5r_e6" in bindings:
                c.update(copy.deepcopy(bindings["ot_s81sl_capc5r_e6"]))
            else:
                c["binding_state"] = "UNBOUND: ot_s81sl_capc5r_e6 view (PORTFIX-DEAD D-CAPEND); never ot_s81sl_capc5r alias"
        children.append(c)
    modules = {"u_ln0":f"dsfd_coll_lane_{side}_safe8_ntf",
               "u_ln1":f"dsfd_coll_lane_{side}_safe8_ntf",
               # PORTFIX-DEAD D-MURT (10-25): the TP-end leps (lepw_mu = s_0S, lepe_nh_mu = s_7S) carry no MU tag return:
               # ot_s81sl_lep_mu_a_nrt (no mu_rt port, no return-tag build)
               "u_lep":"ot_s81sl_lep_mu_h" if flavor == "lepe_mu" else ("ot_s81sl_lep_mu_ab" if mab else "ot_s81sl_lep_mu_a_nrt"),
               "u_land":"dsdv_mu_land"}
    if mab:
        modules.update(u_ln2=f"dsfd_coll_lane_{side}_safe8_ntf", u_ln3=f"dsfd_coll_lane_{side}_safe8_ntf")
    roles = ROLES_WAB if mab else (ROLES_E if side == "e" else {k: (*v, "R0") for k, v in ROLES.items()})
    for inst,(at,envelope,orient) in roles.items():
        c = dict(inst=inst, master=modules[inst], at=at, reserved_envelope_um=envelope,
                 count=1, orient=orient)
        if inst == "u_lep" and mab:
            c["params"] = dict(LEP_AB_PARAMS)   # S81-LINK5B G7 (lead): lepmu t5c/t5d kit params
        if modules[inst] in bindings:
            c.update(copy.deepcopy(bindings[modules[inst]]))
        else:
            c["binding_state"] = "UNBOUND: preserve exact actual child view; never old-parent alias"
        children.append(c)
    return dict(schema="opentallas.s81_mu72.assembly.v1", top=top,
        source=f"rtl/dsrom_sys/s81_dv/slice/mu72/{top}.sv",
        sources=[f"rtl/dsrom_sys/s81_dv/slice/mu72/{top}.sv"]+G3_SOURCES+normal["sources"]+[
            "rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv",
            # S81-LINK5: the safe8_ntf lane's own sources (dscoll_lane_*_s8n* kit list @445e6c74c; six were missing here)
            "rtl/link/ot_link_crc32.sv", "rtl/lib/ot_rst_relay_tree3.sv", "rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv",
            "rtl/lib/ot_sram_oldread_b64.sv", "rtl/lib/ot_sram_showahead_b64.sv", "rtl/common/ot_link_credit_rx_b64.sv",
            "rtl/common/ot_link_credit_tx_rc.sv", "rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep_safe4.sv",
            "rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx_safe3.sv",
            "rtl/dsrom_sys/s81_dv/slice/mu72/ot_s81_mu72_land.sv",
            "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv",
            "rtl/dsrom_sys/s81_dv/slice/dsdv_mu_land.sv",
            "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xg_xo.sv",      # S81-RTLGAP/head 589110357: u_sl.u_xg master
            "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop_xo.sv",
            "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv",        # S81-LINK5B G7: u_sl.u_xr master ot_s81sl_xrt1 (ffn 59a8155d3)
            "rtl/lib/ot_rst_relay.sv",   # S81-LINK5: u_land #(SRAM 1) = the CLOSED dsdv_mu_land view's sources
            "physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v"],
        defines=normal.get("defines", []),
        define_values=normal.get("define_values", {}),
        compiler_defines={"OT_S81_CAP5_C":"1"},
        normal_parameters=normal["params"],
        source_dependencies={"normal":"663783aa82568d6a8d029e2ac88f65878b004e9d",
                             "normal_spec":"3c4721d69ddab3724a65c96259143faf778fe172",
                             "original_endpoint_lp":"aefbb0ca375332e55b7983b1a4da7fe40f832960",
                             "safe8_lanes":"445e6c74c"},
        outline=dict(w=OUTLINE[flavor],h=6825.6,exact=True), hardened=False,
        normal_source_envelope=dict(inst="u_sl",at=[slx,sly],outline=[1252.8,6739.2],
            hardened=False, note="Use actual hard descendants below; normal parent closure is not required for diagnostic integration"),
        children=children, clock_ports=CLOCKS, reset_port="rst_n",
        clock_connections={"u_sl.ck_C":"ck_S",**{f"u_sl.{c}":c for c in CLOCKS if c not in ("ck_S","ck_K","ck_ML")},
                           **{f"{i}."+("ck" if i.startswith("u_ln") else "clk"):"ck_K" for i in roles if i != "u_land"}, "u_land.clk":"ck_ML"},
        transport=dict(existing_S_to_K_cycles=3,existing_K_to_S_cycles=3,
                       existing_fault_output_cycles=2,CAP5_capture_increment_vs_CAPC2=12,
                       new_K_transport_cycles=None, MU_land_write_cycles=3, MU_land_command_cycles=3,
                       MU_land_return_cycles=3, MU_rc_to_first_return_cycles=10,
                       MU_rc_to_first_return_increment=6),
        soft_transport=[dict(inst=i, bank_cell_corridor=([820.8,3715.2,561.6,172.8] if mab else ([1468.8,3110.4,561.6,172.8] if side == "e" else [1468.8,2116.8,561.6,172.8])),
                             kind="existing_D4_K2_landing", physical_status="UNROUTED real gap reservation")
                        for i in ("u_ml_wr","u_ml_cmd","u_ml_ret")],
        unclosed_bundles=(MAB_BUNDLES if mab else [
            dict(ends=["u_ln0","u_lep"],nets=["l0v","l0r","l0d[552:0]","i0v","i0r","i0d[552:0]","f0[2:0]","rxv[0]"],
                 centre_distance_um=([686.88,334.8] if side == "e" else [82.08,1501.2]),
                 state=("G3: lane W face abuts the lep lane face (43.2 gap), same K region, no long transport" if side == "e"
                        else "UNLANDED long K transport; ready/data/status ages must align")),
            dict(ends=["u_ln1","u_lep"],nets=["l1v","l1r","l1d[552:0]","i1v","i1r","i1d[552:0]","f1[2:0]","rxv[1]"],
                 centre_distance_um=([686.88,356.4] if side == "e" else [82.08,745.2]),
                 state=("G3: lane W face abuts the lep lane face (43.2 gap), same K region, no long transport" if side == "e"
                        else "UNLANDED long K transport; ready/data/status ages must align")),
            dict(ends=["u_lep","u_land"],nets=["mwv","mwd[1103:0]","mrv","mrd[1103:0]","mf"],
                 centre_distance_um=[43.2,561.6],state="SOURCE FIXED: D4/K2 wr/cmd/ret +3 each; physical ring placement/STA and compiler +6 return remain open")]),
        physical_holds=["No parent CLOSED record or SS/FF/GRT claim",
                        "K clock is an explicit diagnostic implementation root; no balanced-region closure assumption",
                        "Actual lane/endpoint relay geometry pending; MU-land three real rings occupy172.8um face gap",
                        "Compiler replay return and identity-use calendar must add6 cycles before release",
                        "Actual child pins, clock/reset placement and PG composition feed ongoing die flow",
                        "External ports and source widths preserved; no tied functional ports or false paths",
                        ("S81-LINK5 copy-A/B end (4 lanes, lep_mu_ab): u_lep reservation 561.6x1987.2 needs the s81sl_lepmu kit re-floorplanned (475.2x1900.8, pair A+B on W); no old lepmu gate/view alias"
                         if mab else "No copy-B/AB physical release alias: this two-lane envelope is copy-A only")])

LEP_AB_PARAMS = {"RX_SRAM": 1, "IN_PIPE": 1, "NATIVE32": 1}   # S81-LINK5B G7: s_0N u_lep (IN_PIPE +1 cycle on ro and mu_c)
_LN = {"u_ln0": ("l0","i0","f0","rxv[0]"), "u_ln1": ("l1","i1","f1","rxv[1]"),
       "u_ln2": ("l2","i2","f2","rxvb[0]"), "u_ln3": ("l3","i3","f3","rxvb[1]")}
def _centre(r):
    (x, y), (w, h) = r[0], r[1]
    return x + w/2, y + h/2
MAB_BUNDLES = [dict(ends=[i,"u_lep"], nets=[f"{l}v",f"{l}r",f"{l}d[552:0]",f"{k}v",f"{k}r",f"{k}d[552:0]",f"{f}[2:0]",rv],
                    centre_distance_um=[round(abs(_centre(ROLES_WAB[i])[0]-_centre(ROLES_WAB["u_lep"])[0]),3),
                                        round(abs(_centre(ROLES_WAB[i])[1]-_centre(ROLES_WAB["u_lep"])[1]),3)],
                    state="S81-LINK5: lane E face abuts the lep W face (51.84 gap; face overlap >= 345.6), same K region, no long transport")
               for i, (l, k, f, rv) in _LN.items()] + [
    dict(ends=["u_lep","u_land"],nets=["mwv","mwd[1103:0]","mrv","mrd[1103:0]","mf"],
         centre_distance_um=[round(abs(_centre(ROLES_WAB["u_land"])[k]-_centre(ROLES_WAB["u_lep"])[k]),3) for k in (0,1)],state="SOURCE FIXED: D4/K2 wr/cmd/ret +3 each; physical ring placement/STA and compiler +6 return remain open")]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--normal-spec",type=Path,required=True)
    ap.add_argument("--bindings",type=Path,help="module -> exact child view/receipt dictionary; no automatic aliases")
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args(); normal=json.loads(a.normal_spec.read_text())
    bindings=json.loads(a.bindings.read_text()) if a.bindings else {}
    a.out.mkdir(parents=True,exist_ok=True)
    for f in ("lepe_mu","lepe_nh_mu","lepw_mu","lepw_mab_mu"):
        (a.out/f"{f}.json").write_text(json.dumps(assemble(normal,f,bindings),indent=2)+"\n")
if __name__=="__main__": main()
