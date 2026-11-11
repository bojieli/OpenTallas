#!/usr/bin/env python3
"""HEAD-92/H2 11-10 (COORD ruling: hd_host_e form H2, structural form beside the form 5 / 5r ECOs):
ORFS hard-core kit for ot_s81hd_he_epc = u_rr + u_ep of the hd_host_e lane-1 collector (ot_s81ph_coll_lane_safe4_hd),
through the shared gen_core_kit_hbm generator.  Pure hierarchy cut: face shell OFF, no reset relay stage, so every
port crossing keeps its cycle count (0 pin cycles).

Geometry: outline 224.64 x 492.48 (26 x 57 on the 8.64 lattice) at parent origin (336.96, 60.48): E of the hd_host_e
clock tap / count straps (x 319.68-324), which stay where the plan has them.  36 ot_sram_1r1w2c_256x64_m1 in 4 columns
x 9 rows (form 5 pitch 51.84), lifted 8.64 so a 25.9 um channel stays along the S face.  Pins follow the parent flow:
W face (toward the gbx and the l1 W windows) = frame side f_rx/r_rx (low half) and f_tx/r_tx (high half), M4 + M6,
clk / rst_n / reset leaves mid W face (nearest the tap); S face (toward the coll_o1 / coll_i1 S windows) = lane out
(left half) and lane in (right half), M5 + M7.

    python3 -I tools/s81_head/head_he_epc_kit.py --out KITROOT [--plan PLAN] [-- gen args]
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "physical/die_plan/hbm_arch_cores"))
import gen_core_kit_hbm as G  # noqa: E402

MOD = "ot_s81hd_he_epc"
DEFINES = ("OT_COLL_NATIVE32", "OT_COLL_NATIVE32_OFF")
M_EP = "ot_sram_1r1w2c_256x64_m1"
MEM = "physical/asap7_memory_macros_v2/{0}/{0}_bb.v"
FILES = [MEM.format(M_EP), "rtl/dsrom_sys/s81_head/ot_s81hd_he_epc.sv",
         "rtl/lib/ot_rst_relay_tree3.sv", "rtl/link/ot_link_crc32.sv", "rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv",
         "rtl/lib/ot_sram_oldread_b64.sv", "rtl/lib/ot_sram_showahead_b64.sv", "rtl/common/ot_link_credit_rx_b64.sv",
         "rtl/common/ot_link_credit_tx_rc.sv", "rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep_safe4.sv",
         "rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx_safe3.sv", "rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv",
         "rtl/dsrom_sys/s81_head/ot_s81hd_util.sv", "rtl/dsrom_sys/s81_head/ot_s81hd_lsc_parts.sv",
         "rtl/dsrom_sys/s81_head/ot_s81hd_beat_link.sv", "rtl/dsrom_sys/s81_head/ot_s81hd_best64.sv",
         "rtl/dsrom_sys/s81_head/ot_s81hd_mesh_ep_core.sv"]
TIMED = ("out_data", "out_last", "out_valid", "in_ready", "in_valid", "out_ready_v", "r_rx_v", "r_rx", "fault",
         "rr_lo", "rr_gb", "f_tx", "f_tx_v", "r_tx", "r_tx_v", "f_rx", "f_rx_v", "in_data", "in_last", "ch_b")
W, H = 224.64, 492.48
ORIGIN = (336.96, 60.48)
M4P, M4O, M5P, M5O, M6P, M6O, M7P, M7O = 0.048, 0.024, 0.048, 0.024, 0.064, 0.032, 0.064, 0.032


def spread(names, lo, hi, pitch, off):
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


def bits(b, w):
    return [f"{b}[{i}]" for i in range(w)]


def pins():
    out = []
    # W face (x = 0), horizontal layers: receive frames low, transmit frames high, misc + clk/rst_n in the middle
    w_lo = ["f_rx_v"] + bits("f_rx", 595) + ["r_rx_v"] + bits("r_rx", 53)
    w_hi = bits("rr_lo", 8) + bits("rr_gb", 22) + ["fault", "ch_b", "f_tx_v"] + bits("f_tx", 595) + ["r_tx_v"] + bits("r_tx", 53)
    for names, (lo, hi) in ((w_lo, (12.0, 218.0)), (w_hi, (232.0, 480.0))):
        out += [dict(name=n, layer="M4", x=0.0, y=y) for n, y in spread(names[0::2], lo, hi, M4P, M4O)]
        out += [dict(name=n, layer="M6", x=0.0, y=y) for n, y in spread(names[1::2], lo, hi, M6P, M6O)]
    yc = round(M4O + M4P * round((224.0 - M4O) / M4P), 4)
    out += [dict(name="clk", layer="M4", x=0.0, y=yc), dict(name="rst_n", layer="M4", x=0.0, y=round(yc + 2.016, 4))]
    # S face (y = 0), vertical layers: lane out toward coll_o1 (W half), lane in toward coll_i1 (E half)
    s_lo = ["out_valid", "out_last"] + bits("out_ready_v", 3) + bits("out_data", 552)
    s_hi = ["in_valid", "in_ready", "in_last"] + bits("in_data", 552)
    for names, (lo, hi) in ((s_lo, (8.0, 108.0)), (s_hi, (116.0, 216.0))):
        out += [dict(name=n, layer="M5", x=x, y=0.0) for n, x in spread(names[0::2], lo, hi, M5P, M5O)]
        out += [dict(name=n, layer="M7", x=x, y=0.0) for n, x in spread(names[1::2], lo, hi, M7P, M7O)]
    return out


def macros():
    """child-local: columns 25.92 + 51.84 c, rows 25.92 + 51.84 r (generator snaps onto the macro grid)"""
    cells = []
    for b in range(9):
        for d in range(2):
            cells.append(f"u_ep.g_fifo_safe.u_m.g_bank[{b}].g_depth[{d}].g_256.u_m")
    for b in range(9):
        for d in range(2):
            cells.append(f"u_ep.g_rb_safe.u_m.g_bank[{b}].g_depth[{d}].g_256.u_m")
    mp = []
    for i, k in enumerate(cells):
        c, r = (i // 8, i % 8) if i < 32 else (i - 32, 8)
        mp.append(dict(k=k, origin_um=[round(25.92 + 51.84 * c, 2), round(25.92 + 51.84 * r, 2)], orient="R0", macro=M_EP))
    return mp


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--plan", default=str(ROOT / "physical/die_plan/s81_head/die_plan.json"))
    ap.add_argument("rest", nargs="*")
    a = ap.parse_args()
    work = Path(a.out) / "_inputs"
    work.mkdir(parents=True, exist_ok=True)
    pf = work / f"{MOD}_pins.json"
    pf.write_text(json.dumps(pins(), indent=0) + "\n")
    vf = work / f"views_{MOD}.json"
    vf.write_text(json.dumps(dict(plan=str(Path(a.plan).resolve()), view_list=[dict(
        view=f"{MOD}@kit", module=MOD, outline_um=[W, H], pins_file=str(pf.resolve()),
        pins_sha256=hashlib.sha256(pf.read_bytes()).hexdigest(), instances=[MOD], placed=1, recipe_keys=[MOD])]), indent=1) + "\n")
    mf = work / f"{MOD}_macros.json"
    mf.write_text(json.dumps(dict(source="head_he_epc_kit.py", macro_placement=macros()), indent=1) + "\n")
    rec = {MOD: dict(top=MOD, files=FILES, defines=list(DEFINES), params={}, macros=[M_EP], macro_dirs={},
                     source="HEAD-92/H2 head_he_epc_kit.py")}
    sys.argv = ["gen_core_kit_hbm.py", "--views", str(vf), "--view", f"{MOD}@kit", "--out", a.out, "--recipe-key", MOD,
                "--face-shell", "off", "--face-reset-relay", "0", "--core-insertion", "none", "--sigmax", "M7",
                "--hold-ff-margin", "0", "--macro-placement", str(mf), "--macro-inst-fmt", "{k}"] + a.rest
    G.main(recipe_overrides=rec)
    # Face shell off = the cut ports stay as in the flat circuit: SRAM read data / ready / valid cones are not one flop
    # deep.  They are timed boundaries (kit SDC IO budget in the core, the ETM arcs in the parent / die STA), declared
    # here by exact bus name (face_guard timed_face.json, DIE-KV-61/hr mechanism) instead of a +1-cycle face shell.
    (Path(a.out) / f"{MOD}_kit" / "timed_face.json").write_text(json.dumps(dict(
        schema="opentallas.kit_timed_face.v1", buses=list(TIMED),
        ruling="COORD 11-10 hd_host_e form H2: pure hierarchy cut of u_ep + u_rr, face shell off preferred (0 pin cycles)",
        reason="ot_s81ph_link_ep_safe4_hd ports are not registered at the cut (out_data = SRAM old-read mux, ready/valid "
               "handshakes, reset leaves); registering them would add a cycle per crossing"), indent=1) + "\n")


if __name__ == "__main__":
    main()
