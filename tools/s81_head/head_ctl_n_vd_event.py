#!/usr/bin/env python3
"""HEAD plan + die clock event l48vd (DIE-HEAD-84, COORD 11-07 19:2x), on l48uo: the hd_ctl_n CTLn vC form.

 1. clock.landing_network.input_pin_cycles {coll_WN3_u__0: 1, coll_WN3_d__0: 1} (token 6bc70acd6d validates the
    WN3 collector pins 4 -> 5 cycles).
 2. hd_ctl_n clock.landing_ring_wreg on w3u_i/w3d_i: WREG + FREG, WRITE_CHUNK 8, READ_CHUNK 32, WRITE_TAIL 1, numeric
    FREG order (Codex CTLn vC internal form).  Strap K + 2 on both rings; the die-top literals follow.
 3. hd_ctl_n ft_slots: w3u 5 -> 6, w3d 5 -> 6, unit_ft 1 -> 2 stations with per-bit sites (Codex reform_preview5), so
    every planned feedthrough hop is <= 351 um.
 4. die clock: hd_ctl_n clock.tap_mode density -> explicit.  The l48uo taps clk..clk_t9 keep their names and sites;
    clk_t10..clk_t13 are appended (COORD (B)): no renumbering, no other type or pin moves.  Checked with
    taps.explicit_taps (every sink within tap_radius_um, every tap under tap_max_sinks).
 5. The new taps re-derive the hd_ctl_n reset tree, so the relay names move.  The landing START keys are re-derived
    by head_cland_stage_delta on the new relay table (GEN of the plan without those keys), and each
    reset_start_raw_exports row moves to the relay of the same depth at the same site (else the nearest one of that
    depth; the export pin keeps its l48uo site).
 6. latency.lanes regenerated (gen.latency_table): coll_WN3_u/d 11 -> 12, unit_lep 5 -> 6.

usage: head_ctl_n_vd_event.py L48UO_DIR OUT_DIR --tools-root ROOT [--delta head_ctl_n_vd_delta.json.gz]
"""
import argparse
import gzip
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EVENT = "l48vd"
TYPE = "hd_ctl_n"
START_KEYS = ("landing_reader_start", "landing_writer_start", "landing_status_input_stages",
              "landing_status_anchors", "landing_local_resets")
APPENDED = ("clk_t10", "clk_t11", "clk_t12", "clk_t13")


def apply_delta(plan, delta, schema, taps):
    """items 1-4 on the l48uo plan; -> the l48uo tap table"""
    por = schema.tap_grid(schema.Plan(json.loads(json.dumps(plan))), TYPE)    # before the station change re-derives them
    ln = plan["clock"]["landing_network"]
    if ln.get("input_pin_cycles"):
        raise ValueError("base plan already has input_pin_cycles")
    ln["input_pin_cycles"] = dict(delta["input_pin_cycles"])
    T = plan["partition_types"][TYPE]
    ck = T["clock"]
    if ck.get("landing_ring_wreg") or ck.get("tap_mode") != "density":
        raise ValueError(f"{TYPE}: base plan is not the l48uo form")
    d = delta[TYPE]
    ck["landing_ring_wreg"] = dict(d["landing_ring_wreg"])
    T["ft_slots"] = json.loads(json.dumps(d["ft_slots"]))
    if [n for n, _, _ in por] != ["clk"] + [f"clk_t{i}" for i in range(1, len(por))]:
        raise ValueError("unexpected l48uo tap names")
    add = d["taps_appended"]
    if [p["name"] for p in add] != [f"clk_t{i}" for i in range(len(por), len(por) + len(add))]:
        raise ValueError("appended taps must number on from the l48uo taps")
    ck["tap_mode"] = "explicit"
    ck["taps"] = ([t for t in ck.get("taps", []) if t.get("kind") == "core"] +
                  [{"name": n, "xy": [round(x, 4), round(y, 4)]} for n, x, y in por] + [dict(p) for p in add])
    res = taps.explicit_taps(schema.Plan(json.loads(json.dumps(plan))), TYPE)
    return por, [dict(name=n, xy=[round(x, 1), round(y, 1)], load=int(k), reach_um=round(r, 1)) for n, x, y, k, r in res]


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


def patch_top_straps(top_path, old_k, new_k, CL):
    """die-top count-strap literals of the changed K (head_cland_stage_delta.strap_update on a prepared dir's top)"""
    top, ch = top_path.read_text(), []
    for part in sorted(set(old_k) | set(new_k)):
        for sp in sorted(set(old_k.get(part, {})) | set(new_k.get(part, {}))):
            o, n = old_k.get(part, {}).get(sp), new_k.get(part, {}).get(sp)
            if o == n:
                continue
            w, v = n
            inst = CL.ident(part)
            m = re.search(r"\n    (\w+)(?:\s*#\(.*?\))?\s+" + re.escape(inst) + r"\s*\((.*?)\n    \);", top, re.S)
            assert m, inst
            body = m.group(2)
            pm = re.search(r"\." + re.escape(sp) + r"\((\d+)'b([01]+)\)", body)
            assert pm and int(pm.group(2), 2) == o[1], (inst, sp, o)
            body = body[:pm.start()] + ".%s(%d'b%s)" % (sp, w, format(v, "0%db" % w)) + body[pm.end():]
            top = top[:m.start(2)] + body + top[m.end(2):]
            ch.append([inst, sp, o[1], v])
    top_path.write_text(top)
    return ch


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("src", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--tools-root", type=Path, required=True)
    ap.add_argument("--delta", type=Path, default=Path(__file__).with_name("head_ctl_n_vd_delta.json.gz"))
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
    delta = json.loads(gzip.decompress(a.delta.read_bytes()))
    rel_dir = out.relative_to(root).as_posix()
    with tempfile.TemporaryDirectory(dir=out.parent) as td:
        pre, stripped, staged = Path(td) / "pre", Path(td) / "stripped", Path(td) / "staged"
        U.plain_tree(src, pre)
        base_bytes = (pre / "source_plan.json").read_bytes()
        side_bytes = (pre / "source_sidecar.json").read_bytes()
        plan, side = json.loads(base_bytes), json.loads(side_bytes)
        old_k = CL.Landings(json.loads(base_bytes), side).strap_expected()
        T = plan["partition_types"][TYPE]
        por_wrapper = pre / "published" / (T["module"] + ".sv")
        por_rrl = H.rrl_from_rtl(por_wrapper)
        por_taps, tap_rows = apply_delta(plan, delta, schema, taps)
        moved = U.refresh_latency(plan, gen, schema)
        start_keys = {k: T["clock"].pop(k) for k in START_KEYS if k in T["clock"]}
        # the new reset tree: GEN of the plan without the landing START keys (they name l48uo relays)
        shutil.copytree(pre, stripped)
        (stripped / "source_plan.json").write_text(json.dumps(plan, indent=1) + "\n")
        boot = Path(td) / "boot"
        r = subprocess.run([sys.executable, str(root / "tools/die_plan/gen.py"), "phys", str(stripped / "source_plan.json"),
                            "--clock-landing", str(stripped / "source_sidecar.json"), "--types", TYPE, "--out", str(boot),
                            "--rtl-root", str(root), "--trial"], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"{TYPE}: GEN of the new reset tree failed:\n{(r.stdout + r.stderr)[-2000:]}")
        boot_rtl = boot / "_rtl" / (T["module"] + ".sv")
        exports = remap_exports(T, por_rrl, H.rrl_from_rtl(boot_rtl))
        rrl_rtl = Path(td) / "rrl.sv"
        rrl_rtl.write_text(alias_patch(boot_rtl.read_text(), T.get("reset_start_raw_exports", [])))
        (stripped / "source_plan.json").write_text(json.dumps(plan, indent=1) + "\n")
        H.main([str(stripped), str(staged), "--types", TYPE, "--rrl-from", f"{TYPE}={rrl_rtl}", "--republish", str(root),
                "--repo", str(root)])
        final = json.loads((staged / "source_plan.json").read_text())
        FT = final["partition_types"][TYPE]["clock"]
        missing = [k for k in start_keys if k not in FT]
        if missing:
            raise SystemExit(f"stage delta did not re-derive {missing}")
        if {k: v["cycles"] for k, v in final["latency"]["lanes"].items()} != {k: v["cycles"] for k, v in plan["latency"]["lanes"].items()}:
            raise SystemExit("the START re-derivation moved a lane")
        new_k = CL.Landings(json.loads(json.dumps(final)), side).strap_expected()
        straps = patch_top_straps(staged / "source" / "s81_head_top.sv", old_k, new_k, CL)
        # sink bins: the l48uo assets were read during the event; the record points at its own (same-byte) copies
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
    record = dict(event=EVENT, tool="tools/s81_head/head_ctl_n_vd_event.py", base="l48uo",
                  base_plan_sha256=U.sha(base_bytes), plan_sha256=plan_sha, sidecar_sha256=U.sha(side_bytes),
                  sidecar_changed=False, delta_sha256=U.sha(a.delta.read_bytes()), sink_bins_file=bins,
                  input_pin_cycles=delta["input_pin_cycles"], lanes_moved={k: list(v) for k, v in moved.items()},
                  landing_ring_wreg=delta[TYPE]["landing_ring_wreg"],
                  ft_stations={v["name"]: v["stations"] for v in delta[TYPE]["ft_slots"]},
                  taps_kept=[n for n, _, _ in por_taps], taps_appended=list(APPENDED), taps=tap_rows,
                  reset_start_raw_exports=exports, die_top_straps=straps,
                  published_wrapper_sha256=U.sha(wrapper.read_bytes()))
    w = json.loads((out / "wave_prepare.json").read_text())
    w[EVENT] = record
    (out / "wave_prepare.json").write_text(json.dumps(w, indent=1) + "\n")
    (out / f"{EVENT}_event.json").write_text(json.dumps(record, indent=1) + "\n")
    sums = out / "SHA256SUMS"
    names = [ln.partition("  ")[2] for ln in sums.read_text().splitlines()] + [f"{EVENT}_event.json"]
    sums.write_text("".join(f"{U.sha((out / n).read_bytes())}  {n}\n" for n in dict.fromkeys(names) if (out / n).is_file()))
    print(json.dumps(dict(plan_sha256=plan_sha, lanes=record["lanes_moved"], straps=straps, exports=exports,
                          pack=U.pack(src, out)), indent=1))


if __name__ == "__main__":
    main()
