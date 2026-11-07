#!/usr/bin/env python3
"""DIE-HEAD-77-LEP2 hd_lep0N vF (OWNER 11-06 21:5x conservative form, RE-FORM of hd_lep0N, CTS tap 1251 ps vs 450):
ORFS hard-core kits for the D2 split pieces ot_s81hd_lep0N_hub_core and ot_s81hd_lep0N_region_core (K) through the
shared gen_core_kit_hbm generator, with registered faces (generator face shell, +1 cycle per pin crossing, PIN CYCLES)
and a registered reset relay.  Vehicle form: same-clock seam, no count-aligned landing rings; die windows of the
parent plan are NOT changed here.

Geometry (DIE-HEAD-77-LEP2 estimate, same 1762.56 x 1226.88 footprint, rows from the 5 TX banks of each region):
  bottom regions 881.28 x 578.88, hub strip 1762.56 x 69.12 at y 578.88, top regions 881.28 x 578.88 at y 648.
  Region (bottom form, K=2): pair MX at (69.12, 8.64), K face up; TX banks in two rows above the pair, right of the
  K band; seam on the N face, coll on the W face at the plan windows.
  Hub: RX banks in columns (lane 2/0 low row, lane 1/3 high row), MU landing in the middle, lepk at the E end of S face.

    python3 -I tools/s81_head/head_lep_split_kit.py --piece hub|rg --k 2 --out KITROOT [--ve-views DIR] [-- gen args]
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "physical/die_plan/hbm_arch_cores"))
import gen_core_kit_hbm as G  # noqa: E402

PAIR = "ot_s81hd_lep_pair"
SPLIT = "rtl/dsrom_sys/s81_head/ot_s81hd_lep0N_split.sv"
DEFINES = ("OT_COLL_NATIVE32", "OT_COLL_NATIVE32_OFF")
MEM = "physical/asap7_memory_macros_v2/{0}/{0}_bb.v"
M_TX, M_RX, M_LAND = "ot_sram_1r1w_512x128_m4_r0c0", "ot_sram_1r1w_32x128_m1_r0c0", "ot_sram_1r1w_128x256_m1_r0c0"
COMMON = ["physical/die_plan/s81/bind/source_modules/portfix178/ot_s81_mu72_lnland.sv",
          "physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_lep.sv",
          "rtl/common/landed_parent/ot_pl_land.sv", "rtl/common/landed_parent/ot_pl_land_field_copies.sv",
          "rtl/common/landed_parent/ot_pl_land_kept_enable.sv", "rtl/common/landed_parent/ot_pl_land_reset_forest.sv",
          "rtl/common/ot_link_credit_rx_b64.sv", "rtl/common/ot_link_credit_tx_rc.sv",
          "rtl/dsrom_sys/s81_dv/slice/mu72/ot_s81_mu72_land.sv", "rtl/dsrom_sys/s81_head/generated/ot_s81hd_lep_nr.sv",
          "rtl/dsrom_sys/s81_head/generated/ot_s81hd_lep_split_nr.sv",
          "rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv", "rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep_safe4.sv",
          "rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx_safe3.sv", "rtl/lib/ot_rst_relay.sv", "rtl/lib/ot_rst_relay_tree3.sv",
          "rtl/lib/ot_sram_oldread_b64.sv", "rtl/lib/ot_sram_showahead_1r1w.sv", "rtl/lib/ot_sram_showahead_b64.sv",
          "rtl/link/ot_link_crc32.sv"]
M5P, M5O, M4P, M4O, M6P, M6O = 0.048, 0.024, 0.048, 0.024, 0.064, 0.032
PLAN_WIN = {2: dict(i=(120.0, 326.0), o=(342.0, 547.2)), 1: dict(i=(640.0, 846.0), o=(862.0, 1067.2))}


def spread(names, lo, hi, pitch, off):
    """evenly spread pins on one lattice over [lo, hi]; returns [(name, coord)]"""
    n = len(names)
    step = (hi - lo) / max(n, 1)
    if step < pitch:
        raise SystemExit(f"window [{lo},{hi}] cannot hold {n} pins at pitch {pitch}")
    out, last = [], None
    for i, nm in enumerate(names):
        k = round((lo + i * step - off) / pitch)
        if last is not None and k <= last:
            k = last + 1
        last = k
        out.append((nm, round(off + k * pitch, 4)))
    return out


def bits(b, w, lo=0):
    return [f"{b}[{i}]" for i in range(lo, lo + w)]


def m5_face(names, x0, x1, y):
    return [dict(name=n, layer="M5", x=x, y=y) for n, x in spread(names, x0, x1, M5P, M5O)]


def lane_seam(k):
    return (bits("tx_psh", 1, k) + bits("tx_pg", 18, 18 * k) + bits("tx_wd", 553, 553 * k) + bits("tx_ovf", 1, k)
            + bits("k_li_v", 1, k) + bits("k_li_r", 1, k) + bits("k_li_d", 553, 553 * k) + bits("k_rxv", 1, k)
            + bits("k_flt", 3, 3 * k))


def hub_inputs():
    w, h = 1762.56, 69.12
    pins = []
    pins += m5_face(lane_seam(2), 20.0, 860.0, 0.0) + m5_face(lane_seam(0), 900.0, 1300.0, 0.0)
    pins += m5_face(bits("lepk_i0", 1104) + bits("lepk_o0", 1104), 1320.0, 1750.0, 0.0)
    pins += m5_face(lane_seam(1), 20.0, 860.0, h) + m5_face(lane_seam(3), 900.0, 1640.0, h)
    misc = ["lepf_i0"] + bits("unit_i0", 45) + bits("ctrl_o0", 32) + ["fault_o0"] + bits("lw_o", 11)
    pins += m5_face(misc, 1650.0, 1750.0, h)
    pins += [dict(name="ck", layer="M5", x=round(M5O + M5P * round((880.0 - M5O) / M5P), 4), y=h),
             dict(name="rst_n", layer="M5", x=round(M5O + M5P * round((884.0 - M5O) / M5P), 4), y=h)]
    mp = []
    for i in range(5):
        x = round(216.0 + 64.8 * i, 2)
        mp.append(dict(k=f"u_core.u_lep.u.g_rx[2].g_sa.g_true_sram.u_rx_mem.g_bank[{i}].u_m", origin_um=[x, 8.64], orient="R0", macro=M_RX))
        mp.append(dict(k=f"u_core.u_lep.u.g_rx[1].g_sa.g_true_sram.u_rx_mem.g_bank[{i}].u_m", origin_um=[x, 38.88], orient="R0", macro=M_RX))
        x = round(1080.0 + 64.8 * i, 2)
        mp.append(dict(k=f"u_core.u_lep.u.g_rx[0].g_sa.g_true_sram.u_rx_mem.g_bank[{i}].u_m", origin_um=[x, 8.64], orient="R0", macro=M_RX))
        mp.append(dict(k=f"u_core.u_lep.u.g_rx[3].g_sa.g_true_sram.u_rx_mem.g_bank[{i}].u_m", origin_um=[x, 38.88], orient="R0", macro=M_RX))
        mp.append(dict(k=f"u_core.u_land.g_sram.g_t[{i}].g_128.u_m", origin_um=[round(540.0 + 108.0 * i, 2), 12.96], orient="R0", macro=M_LAND))
    files = [MEM.format(M_RX), MEM.format(M_LAND), SPLIT] + COMMON
    return dict(module="ot_s81hd_lep0N_hub", top="ot_s81hd_lep0N_hub_core", w=w, h=h, pins=pins, mp=mp, files=files,
                macros=[M_RX, M_LAND], params={}, macro_dirs={}, sigmax="M6")


def rg_inputs(k, ve):
    if k != 2:
        raise SystemExit("only the bottom-left form K=2 is drawn yet")
    w, h = 881.28, 578.88
    win = PLAN_WIN[k]
    ci, co = bits("coll_i", 514), bits("coll_o", 512)
    pins = []
    for names, (lo, hi) in ((ci, win["i"]), (co, win["o"])):
        m4 = names[0::2]
        m6 = names[1::2]
        pins += [dict(name=n, layer="M4", x=0.0, y=y) for n, y in spread(m4, lo, hi, M4P, M4O)]
        pins += [dict(name=n, layer="M6", x=0.0, y=y) for n, y in spread(m6, lo, hi, M6P, M6O)]
    seam = (["tx_rt"] + bits("tx_rst", 106) + ["tx_psh"] + bits("tx_pg", 18) + bits("tx_wd", 553) + ["tx_ovf", "k_li_v", "k_li_r"]
            + bits("k_li_d", 553) + ["k_rxv"] + bits("k_flt", 3))
    pins += m5_face(seam, 20.0, 460.0, h)
    pins += [dict(name="ck", layer="M5", x=round(M5O + M5P * round((466.0 - M5O) / M5P), 4), y=h),
             dict(name="rst_n", layer="M5", x=round(M5O + M5P * round((470.0 - M5O) / M5P), 4), y=h)]
    mp = [dict(k="u_core.u_pair", origin_um=[69.12, 8.64], orient="MX", macro=PAIR)]
    sites = [(483.84, 509.76), (665.28, 509.76), (483.84, 544.32), (665.28, 544.32), (302.4, 544.32)]
    for i, xy in enumerate(sites):
        mp.append(dict(k=f"u_core.u_txl.g_safe_write.u_m.g_bank[{i}].u_m", origin_um=list(xy), orient="R0", macro=M_TX))
    bb = ve / f"{PAIR}_bb.v"
    files = [MEM.format(M_TX), str(bb.relative_to(ROOT)), SPLIT] + COMMON
    return dict(module=f"ot_s81hd_lep0N_rg{k}", top="ot_s81hd_lep0N_region_core", w=w, h=h, pins=pins, mp=mp, files=files,
                macros=[M_TX, PAIR], params=dict(K=k, LOCAL_RST=1), macro_dirs={PAIR: str(ve.relative_to(ROOT))}, sigmax="M7")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--piece", required=True, choices=["hub", "rg"])
    ap.add_argument("--k", type=int, default=2)
    ap.add_argument("--out", required=True)
    ap.add_argument("--plan", default=str(ROOT / "physical/die_plan/s81_head/die_plan.json"))
    ap.add_argument("--ve-views", default=str(ROOT / "results/die_head_77_1106/lep_pair_views_vE"))
    ap.add_argument("rest", nargs="*")
    a = ap.parse_args()
    d = hub_inputs() if a.piece == "hub" else rg_inputs(a.k, Path(a.ve_views).resolve())
    mod = d["module"]
    work = Path(a.out) / "_inputs"
    work.mkdir(parents=True, exist_ok=True)
    pf = work / f"{mod}_pins.json"
    pf.write_text(json.dumps(d["pins"], indent=0) + "\n")
    vf = work / f"views_{mod}.json"
    vf.write_text(json.dumps(dict(plan=str(Path(a.plan).resolve()), view_list=[dict(
        view=f"{mod}@kit", module=mod, outline_um=[d["w"], d["h"]], pins_file=str(pf.resolve()),
        pins_sha256=hashlib.sha256(pf.read_bytes()).hexdigest(), instances=[mod], placed=1, recipe_keys=[mod])]), indent=1) + "\n")
    mf = work / f"{mod}_macros.json"
    mf.write_text(json.dumps(dict(source="head_lep_split_kit.py", macro_placement=d["mp"]), indent=1) + "\n")
    rec = {mod: dict(top=d["top"], files=d["files"], defines=list(DEFINES), params=d["params"], macros=d["macros"],
                     macro_dirs=d["macro_dirs"], source="DIE-HEAD-77-LEP2 head_lep_split_kit.py vF")}
    sys.argv = ["gen_core_kit_hbm.py", "--views", str(vf), "--view", f"{mod}@kit", "--out", a.out, "--recipe-key", mod,
                "--face-shell", "on", "--face-reset-relay", "2", "--core-insertion", "none", "--sigmax", d["sigmax"],
                "--macro-placement", str(mf), "--macro-inst-fmt", "{k}"] + a.rest
    G.main(recipe_overrides=rec)
    if a.piece != "hub":  # yosys resolves the pair to its liberty cell, which has no CHB; the signed pair is one netlist
        f = Path(a.out) / f"{mod}_kit" / "rtl" / "ot_s81hd_lep0N_split.sv"
        f.write_text(f.read_text().replace("ot_s81hd_lep_pair #(.CHB(CHB))u_pair(", "ot_s81hd_lep_pair u_pair("))


if __name__ == "__main__":
    main()
