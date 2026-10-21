#!/usr/bin/env python3
"""HBM-HCBANK9 10-20 (H.STA.BLK.17): edge ring bank e2 (ot_hbm_hc_bankq_ft_static, positions 2 / 6) on the _rl / _rm
pattern of hc9bank_rl.py (one clock root per compact, pin-anchored register mass; 0 added edges).

Base: hbm_hcq_bank_e2_1017 (single clk, die-slot 734.4 sq, sum straight through W -> E, write / feed pins S).
Changes:
  * top ot_hbm_hc_bankq_ft_rl_static / _rm_static: hybrid_entries cluster (ck_l / ck_w / ck_x hard entries) + glue roots
    clk (S-face landing / feed registers / reset), clk_a (write mass), clk_c (stage control), clk_w<r> / clk_x<r>
    (_rm: clk_r<r>) SRAM read capture anchored beside rd_out, clk_e<r> lane enables beside lv_i / ss_i.
    No CPI / CPO on the edge bank (chain pins unregistered as before) -> no clk_i / clk_q / clk_o.
  * weight SRAMs MY (rd_out faces E, toward the lane leaves at x 259.2, was facing the W tile edge); x SRAMs R0 at
    x 600.48 (rd_out faces W, toward the leaves).  Positions unchanged (43.2 lattice x, die-slot outline exact).
  * root pins on the free N face above their column.
Usage: python3 tools/ref_tile/specs_hbm_b_rtl2_1017/hc9bank_e2.py
"""
import copy
import json
from pathlib import Path

RT = Path(__file__).resolve().parents[3] / "physical" / "ref_tile"
WIT = "results/rtl/hbm_hc_ring_1020_bankrl"


def rng(c):
    return [round(c - 0.5, 3), round(c + 0.5, 3)]


def make(var):
    s = json.loads((RT / "hbm_hcq_bank_e2_1017" / "spec.json").read_text())
    t = json.loads((RT / f"hbm_hcq_bank_cb_{var}" / "spec.json").read_text())
    name = f"hbm_hcq_bank_e2_{var}"
    s["name"] = name
    s["top"] = f"ot_hbm_hc_bankq_ft_{var}_static"
    s["sources"] = t["sources"]
    s["params"] = {}
    s["clock"] = "hybrid_entries"
    rs = ["clk", "clk_a", "clk_c"]
    rs += ([f"clk_w{i}" for i in range(4)] + [f"clk_x{i}" for i in range(4)]) if var == "rl" else [f"clk_r{i}" for i in range(4)]
    rs += [f"clk_e{i}" for i in range(4)]
    s["clock_cts_roots"] = rs
    s["clock_ports"] = rs + [f"ck_l[{g}]" for g in range(8)] + [f"ck_w[{g}]" for g in range(8)] + [f"ck_x[{h}]" for h in range(4)]
    for c in s["children"]:
        pass                                # lane leaves: entries bound by the hybrid flow (ck_l), as the cb / b0 kits
    for m in s["macros"]:
        g = int(m["inst"].split("?")[1])
        if "g_w" in m["inst"]:
            m["orient"] = "MY"
            m["clock_entry"] = {"port": f"ck_w[{g}]", "pin": "clk", "reference": "raw_liberty_clock_pin"}
        else:
            m["orient"] = "R0"
            m["clock_entry"] = {"port": f"ck_x[{g}]", "pin": "clk", "reference": "raw_liberty_clock_pin"}
    pins = s["pins"]
    pins["ANY"] = ["ck_l", "ck_w", "ck_x"]
    pins["N"] = [p for p in rs if p != "clk"]
    pr = s["pin_ranges"]
    # N face: capture roots above their SRAM column, lane enables above the leaf columns, clk_a / clk_c mid
    for r in range(4):
        if var == "rl":
            pr[f"clk_w{r}"] = rng(100.0 + 24.0 * r)
            pr[f"clk_x{r}"] = rng(620.0 + 24.0 * r)
        else:
            pr[f"clk_r{r}"] = rng(100.0 + 24.0 * r)
        pr[f"clk_e{r}"] = rng(300.0 + 24.0 * r)
    pr["clk_a"] = rng(420.0)
    pr["clk_c"] = rng(450.0)
    io = dict(s.get("io_flop_at_pins") or {"cols": 4, "allow_none": True})
    io["macro_out_pins"] = ["rd_out"]
    io["macro_pins"] = ["lv_i", "ss_i"]
    s["io_flop_at_pins"] = io
    s["route"]["peak_ram_gb"] = 128
    s["reset_landing"] = {"enable": True, "stages": 2, "clock": "clk", "why": "rst_n lands at the S face in 2 clk stages, then the RTL ot_rst_relay copies (bankrc u_rst / u_rst_b, feed u_rst)"}
    s["slot_change_request"] = (
        "HC edge bank 734.4 x 734.4 (= e2_1017 die slot); master ports unchanged + clock entries (" + ", ".join(rs) +
        " glue roots, ck_l[7:0], ck_w[7:0], ck_x[3:0]): die clock forest delivers each entry at phi - R")
    s["structural_change"] = (
        "HBM-HCBANK9 10-20: e2 on the b0/cb _" + var + " pattern (one clock root per compact pin-anchored register mass; "
        "b0_rp / cb_rw CTS spread FAIL evidence in hc9bank_rl.py).  Single-clk e2_1017 -> hybrid entries + per-mass glue "
        "roots; weight SRAMs MY so rd_out faces the lanes.  0 added edges.")
    s["reroute_reason"] = {"kind": "structural", "failed_job": "e2_1017 ring1-47247cc08 (cancelled GRT hang 10-19)",
                           "why": "per-mass anchored clock roots + hybrid entries (HBM-HCBANK9)"}
    j = s["job"]
    j.update({k: t["job"][k] for k in ("owner", "branch", "extra_paths", "benches")})
    j["purpose"] = f"HC edge bank {name}: one clock root per anchored register mass ({var})"
    j["views_to"] = f"physical/ref_tile/{name}/views"
    j["record_to"] = f"results/rtl/ref_tile/{name}"
    for k in ("orfs_vars",):
        s.pop(k, None)
    d = RT / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
    print("wrote", d / "spec.json", len(rs), "roots")


if __name__ == "__main__":
    make("rl")
    make("rm")
