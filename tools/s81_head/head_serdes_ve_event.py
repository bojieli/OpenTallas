#!/usr/bin/env python3
"""HEAD plan + die clock event l48ve (HEAD-FORMS-2, COORD 11-07 19:4x / 20:0x), on l48vd: the hd_serdes SC clock taps.

The SC form (vF..vJ) hung every clk register on ONE tap at the die-spine anchor (1442.88, 77.76): vH CTS insertion
837-1404 ps (mean 918), clk reg->reg hold -200 ps classes in u_rm and on the W reset/START relays (CTS repair wire
buffers).  DIE-HEAD-84's clock class (screen 19:50) and the HEAD-FORMS-2 vJ CTS (20:0x) split clk into local trees:
tap mean 366..453 ps, clk-domain hold worst -46.5 / -100.6, none below -150.  pma_rck stays ONE tree (unchanged).

 1. hd_serdes clock.tap_mode explicit: clk keeps its l48vd site (the frozen die-spine anchor); clk_t1 (1934.70, 31.10)
    for the E cluster (u_rm / u_prx / coll ring / arst_n, start_i); clk_t2 (540.00, 13.50) for the W reset/START OUT
    pins (rst_o_0 / start_o_0).  clock.control_sinks on, so those registered control pins are sinks of the table
    (taps.control_pin_sinks); tap_radius_um 1000 / tap_max_sinks 3000 (the SC kits' OT_TAP_PITCH_UM 100000 nearest
    split).  Checked with taps.explicit_taps.
 2. NOT in this event: the early core tap clk_c0 at u_phy.u_link.u_tx/clk (insertion 471, 21 ps early).  The l48vd
    hd_serdes has no u_tx hard core (hard_cores = dmem, cmem, chn: the pre-SC form), so gen_phys.core_tap_rows has no
    instance to bind; clk_c0 lands with the plan event that brings the SC form (u_tx, u_bm0..2 hard children).
 3. The new taps re-derive the hd_serdes reset tree (one relay per tap), so each reset_start_raw_exports row moves to
    the relay of the same depth at the same site (else the nearest of that depth); the export pin keeps its site.
 4. latency.lanes regenerated (gen.latency_table) and must not move.

usage: head_serdes_ve_event.py L48VD_DIR OUT_DIR --tools-root ROOT
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EVENT = "l48ve"
BASE = "l48vd"
TYPE = "hd_serdes"
GRID_TAPS = (("clk_t1", 1934.70, 31.10), ("clk_t2", 540.00, 13.50))
DEFERRED_CORE_TAP = {"name": "u_phy.u_link.u_tx", "xy": [2403.096, 86.4], "kind": "core", "insertion_ps": 471.07}
TAP_RADIUS_UM = 1000.0
TAP_MAX_SINKS = 3000


def apply_taps(plan, schema, taps, plan_path):
    """items 1-2 on the l48vd plan; -> (l48vd taps, [dict(name, xy, load, reach_um)])"""
    por = schema.tap_grid(schema.Plan(json.loads(json.dumps(plan)), str(plan_path)), TYPE)
    ck = plan["partition_types"][TYPE]["clock"]
    if [n for n, _, _ in por] != ["clk"] or ck.get("tap_mode") or ck.get("taps") or ck.get("core_taps"):
        raise ValueError(f"{TYPE}: base plan is not the l48vd single-tap form")
    ck["tap_mode"] = "explicit"
    ck["control_sinks"] = True
    ck["tap_radius_um"] = TAP_RADIUS_UM
    ck["tap_max_sinks"] = TAP_MAX_SINKS
    ck["taps"] = ([{"name": "clk", "xy": [round(por[0][1], 4), round(por[0][2], 4)]}] +
                  [{"name": n, "xy": [x, y]} for n, x, y in GRID_TAPS])
    P = schema.Plan(json.loads(json.dumps(plan)), str(plan_path))   # native census files resolve beside the plan
    res = taps.explicit_taps(P, TYPE)
    return por, [dict(name=n, xy=[round(x, 2), round(y, 2)], load=int(k), reach_um=round(r, 1)) for n, x, y, k, r in res]


def remap_exports(T, por_rrl, new_rrl):
    """reset_start_raw_exports -> the new relay of the same depth at the same site (else nearest of that depth)"""
    depth = {net: dep for net, dep, _, _, _ in por_rrl}
    rows = []
    for e in T.get("reset_start_raw_exports", []):
        dep, (x, y) = depth[e["net"]], e["xy_um"]
        cands = sorted((abs(nx - x) + abs(ny - y), net) for net, nd, nx, ny, _ in new_rrl if nd == dep)
        if not cands:
            raise ValueError(f"{e['port']}: no depth-{dep} relay in the new reset tree")
        dist, net = cands[0]
        old = (e["instance"], e["net"])
        e["net"], e["instance"] = net, "u_rrl_" + net.rsplit("_", 1)[1]
        rows.append(dict(port=e["port"], old=list(old), new=[e["instance"], net], depth=dep, relay_moved_um=round(dist, 1)))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("src", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--tools-root", type=Path, required=True)
    a = ap.parse_args(argv)
    root, src, out = a.tools_root.resolve(), a.src.resolve(), a.out.resolve()
    sys.path[:0] = [str(root / "tools/die_plan"), str(root / "tools/s81_head")]
    import clock_landings as CL
    import gen
    import schema
    import taps
    import head_cland_stage_delta as H
    import head_l48uo_event as U
    from head_start_reset_aliases import patch_rtl as alias_patch
    if out.exists():
        raise SystemExit(f"{out} exists: an event never overwrites")
    rel_dir = out.relative_to(root).as_posix()
    with tempfile.TemporaryDirectory(dir=out.parent) as td:
        pre, stripped, staged = Path(td) / "pre", Path(td) / "stripped", Path(td) / "staged"
        U.plain_tree(src, pre)
        base_bytes = (pre / "source_plan.json").read_bytes()
        side_bytes = (pre / "source_sidecar.json").read_bytes()
        plan, side = json.loads(base_bytes), json.loads(side_bytes)
        old_k = CL.Landings(json.loads(base_bytes), side).strap_expected()
        T = plan["partition_types"][TYPE]
        por_rrl = H.rrl_from_rtl(pre / "published" / (T["module"] + ".sv"))
        por_taps, tap_rows = apply_taps(plan, schema, taps, pre / "source_plan.json")
        moved = U.refresh_latency(plan, gen, schema)
        if moved:
            raise SystemExit(f"latency lanes moved: {moved}")
        shutil.copytree(pre, stripped)
        (stripped / "source_plan.json").write_text(json.dumps(plan, indent=1) + "\n")
        boot = Path(td) / "boot"
        r = subprocess.run([sys.executable, str(root / "tools/die_plan/gen.py"), "phys", str(stripped / "source_plan.json"),
                            "--clock-landing", str(stripped / "source_sidecar.json"), "--types", TYPE, "--out", str(boot),
                            "--rtl-root", str(root), "--trial"], capture_output=True, text=True,
                           cwd=stripped)   # plans built from a dict resolve the native census (native_domains/) from cwd
        if r.returncode:
            raise SystemExit(f"{TYPE}: GEN of the new reset tree failed:\n{(r.stdout + r.stderr)[-2000:]}")
        boot_rtl = boot / "_rtl" / (T["module"] + ".sv")
        exports = remap_exports(T, por_rrl, H.rrl_from_rtl(boot_rtl))
        rrl_rtl = Path(td) / "rrl.sv"
        rrl_rtl.write_text(alias_patch(boot_rtl.read_text(), T.get("reset_start_raw_exports", [])))
        (stripped / "source_plan.json").write_text(json.dumps(plan, indent=1) + "\n")
        # hd_serdes has no landing START keys (head_cland_stage_delta.TYPES): only the published wrapper is regenerated
        # (head_cland_stage_delta.republish = alias_patch(GEN bootstrap) of the new plan); the die top is not touched
        # here, as in l48vd (the die clock tool lands the new tap drops)
        shutil.copytree(stripped, staged, symlinks=True)
        H.writable(staged)
        cwd = os.getcwd()
        os.chdir(staged)   # same: native_domains/ beside the plan
        try:
            H.republish(staged, root, [TYPE], staged / "source_sidecar.json")
        finally:
            os.chdir(cwd)
        if (staged / "published" / (T["module"] + ".sv")).read_text() != rrl_rtl.read_text():
            raise SystemExit("republished wrapper differs from the reset-tree bootstrap")
        final = json.loads((staged / "source_plan.json").read_text())
        if {k: v["cycles"] for k, v in final["latency"]["lanes"].items()} != {k: v["cycles"] for k, v in plan["latency"]["lanes"].items()}:
            raise SystemExit("the re-derivation moved a lane")
        new_k = CL.Landings(json.loads(json.dumps(final)), side).strap_expected()
        if new_k != old_k:
            raise SystemExit("count straps moved: this event changes clock taps only")
        bins = U.repoint_sink_bins(final, rel_dir)
        (staged / "source_plan.json").write_text(json.dumps(final, indent=1) + "\n")
        rec = json.loads((staged / "wave_prepare.json").read_text())
        rec["prepared_plan_sha256"] = U.sha((staged / "source_plan.json").read_bytes())
        (staged / "wave_prepare.json").write_text(json.dumps(rec, indent=1) + "\n")
        for f in [*staged.glob("republish_*.log"), staged / "cland_report.json"]:
            f.unlink(missing_ok=True)
        shutil.copytree(staged, out)
    plan_sha = U.sha((out / "source_plan.json").read_bytes())
    wrapper = out / "published" / (T["module"] + ".sv")
    record = dict(event=EVENT, tool="tools/s81_head/head_serdes_ve_event.py", base=BASE,
                  base_plan_sha256=U.sha(base_bytes), plan_sha256=plan_sha, sidecar_sha256=U.sha(side_bytes),
                  sidecar_changed=False, sink_bins_file=bins, taps_kept=[n for n, _, _ in por_taps],
                  taps_added=[n for n, _, _ in GRID_TAPS], core_tap_deferred=dict(DEFERRED_CORE_TAP, port="clk_c0", why="no u_tx hard core in the l48vd hd_serdes"), taps=tap_rows,
                  control_sinks=True, tap_radius_um=TAP_RADIUS_UM, tap_max_sinks=TAP_MAX_SINKS,
                  reset_start_raw_exports=exports, published_wrapper_sha256=U.sha(wrapper.read_bytes()))
    w = json.loads((out / "wave_prepare.json").read_text())
    w[EVENT] = record
    (out / "wave_prepare.json").write_text(json.dumps(w, indent=1) + "\n")
    (out / f"{EVENT}_event.json").write_text(json.dumps(record, indent=1) + "\n")
    sums = out / "SHA256SUMS"
    names = [ln.partition("  ")[2] for ln in sums.read_text().splitlines()] + [f"{EVENT}_event.json"]
    sums.write_text("".join(f"{U.sha((out / n).read_bytes())}  {n}\n" for n in dict.fromkeys(names) if (out / n).is_file()))
    print(json.dumps(dict(plan_sha256=plan_sha, taps=tap_rows, exports=exports, pack=U.pack(src, out)), indent=1))


if __name__ == "__main__":
    main()
