#!/usr/bin/env python3
"""dieclock_route_step.py RUN OUT --kit KIT (REACH-FIX-2 11-12, COORD: routed re-balance as a tool)

ONE routed evaluation of a die_clock build (RUN = die_clock.py build dir, or a dieclock_routed leafcell dir):
  1. dieclock_routed prep           physical tree (balance pads stay in the branch lengths) -> OUT/clk
  2. per-net NDR                    the widths the model prices: CK8W on the trunk + levels <= --wide-levels, CK4W
                                    elsewhere (--ndr 4w), assigned net by net before global_route
  3. combo GRT (per corner)         die_trial signal kit KIT (abstracts, M4-M7 at ADJ) + the clock (M8-M9), 50 it
                                    (DIE-PROTO-2 / LAND-KV-1 mk_combo_kv form, folded in as combo())
  4. ot_clk_die_ctree build         routed RC of the clock nets
  5. dieclock_routed pads --route-ndr  balance wire (branch length - routed hop) spliced at each load pin
  6. die_clock sta                  -> OUT/pd_<C>/arr_<C>.txt
Writes OUT/step.json {corners: {C: {arr, overflow: [H, V, total], spread_ps}}, pad_um}.  Docker image --image (OpenROAD
+ OpenSTA + ASAP7 libs); every container is named --name-prefix-<corner> and runs with --rm."""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_clock as DC  # noqa: E402
import dieclock_routed as DR  # noqa: E402

LIBDIR = "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM"


def set_ndr(ndr="4w", wide_levels=10):
    DC.NDR_MODE, DC.WIDE_LEVELS = ndr, int(wide_levels)


def ndr_tcl(run, path):
    """assign_ndr per clock net: CK8W on levels <= DC.WIDE_LEVELS (and the trunk), CK4W elsewhere (combo net = ck_<net>,
    a port net keeps its name)"""
    E, _ = DC.expand_pads(DC.load_tree(run), {})
    out = ["create_ndr -name CK8W -width {M8:0.32 M9:0.32} -spacing {M8:0.08 M9:0.08}",
           "create_ndr -name CK4W -width {M8:0.16 M9:0.16} -spacing {M8:0.08 M9:0.08}", "set ot_ndr_n 0", "set ot_ndr_miss 0"]
    n8 = 0
    for n in E.nets:
        nd = "CK8W" if DC.WIDE_LEVELS and DC.net_leg_level(E, n) <= DC.WIDE_LEVELS else "CK4W"
        n8 += nd == "CK8W"
        out.append("if {[catch {assign_ndr -ndr %s -net ck_%s}]} {if {[catch {assign_ndr -ndr %s -net %s}]} "
                   "{incr ot_ndr_miss} else {incr ot_ndr_n}} else {incr ot_ndr_n}" % (nd, n["name"], nd, n["name"]))
    out.append('puts "OT_NDR_ASSIGNED $ot_ndr_n miss $ot_ndr_miss"')
    Path(path).write_text("\n".join(out) + "\n")
    return dict(nets=len(E.nets), ck8w=n8, ck4w=len(E.nets) - n8)


def combo(K, C, O, corner="TT", adj="0.75", adj7="0", sigl="M4-M7", ndr_src=None):
    """die_trial signal kit K + clock dir C (ctree.v module ctree, ctree_ck89.tcl) -> O/combo.v + O/combo.tcl"""
    os.makedirs(O, exist_ok=True)
    rv, cv = open(K + "/grt/route.v").read(), open(C + "/ctree.v").read()
    mh = re.match(r"\s*module\s+(\w+)\s*\(([^)]*)\);", rv)
    rports = [p.strip() for p in mh.group(2).split(",") if p.strip()]
    rbody = rv[mh.end():rv.rindex("endmodule")]
    mc = re.search(r"module\s+ctree\s*\(([^)]*)\);", cv, re.S)
    cports = [p.strip() for p in mc.group(1).split(",") if p.strip()]
    cbody = cv[mc.end():cv.rindex("endmodule")]
    if set(rports) & set(cports):
        raise SystemExit("combo: clock and signal kit share port names")
    P = set(cports)

    def f(n):
        return n if n in P else "ck_" + n
    out = []
    for line in cbody.split("\n"):
        s = line.strip()
        if not s or s.startswith(("input", "output")) or s.startswith("//"):
            continue
        m = re.match(r"wire\s+(\w+)\s*;", s)
        if m:
            out.append(f"  wire {f(m.group(1))};")
            continue
        m = re.match(r"(\w+)\s+(\w+)\s*\((.*)\);", s)
        if m:
            conns = re.sub(r"\.(\w+)\((\w+)\)", lambda q: f".{q.group(1)}({f(q.group(2))})", m.group(3))
            out.append(f"  {m.group(1)} ck_{m.group(2)} ({conns});")
            continue
        m = re.match(r"assign\s+(\w+)\s*=\s*(\w+)\s*;", s)
        if m:
            out.append(f"  assign {f(m.group(1))} = {f(m.group(2))};")
            continue
        raise SystemExit("combo: unparsed ctree line: " + s)
    decl = [ln for ln in cv[mc.end():].split("\n") if ln.strip().startswith(("input", "output"))]
    Path(O, "combo.v").write_text(f"module die_combo ({', '.join(rports + cports)});\n" + "\n".join(decl) + "\n" + rbody
                                  + "\n".join(out) + "\nendmodule\n")
    t = open(K + "/grt/grt.tcl").read()
    ct = open(C + "/ctree_ck89.tcl").read()
    pins = [ln for ln in ct.split("\n") if ln.startswith("place_pin")]
    insts = [re.sub(r"-name (\S+)", r"-name ck_\1", ln) for ln in ct.split("\n") if ln.startswith("place_inst")]
    pre = t.split("source /work/grt/obs.tcl")[0]
    pre = pre.replace("read_verilog /work/grt/route.v",
                      "foreach f [glob $::env(LIBDIR)/*RVT_$::env(CORNER)_nldm*.lib*] { read_liberty $f }\n"
                      "read_verilog /out/combo.v")
    pre = pre.replace(re.search(r"link_design \S+", pre).group(0), "link_design die_combo")
    nd = "source %s\n" % ndr_src if ndr_src else ""
    tail = f"""source /work/grt/obs.tcl
{chr(10).join(pins)}
{chr(10).join(insts)}
create_clock -name dck -period 833.333 [get_ports root]
set_routing_layers -signal {sigl} -clock M8-M9
set_global_routing_layer_adjustment M4 {adj}
set_global_routing_layer_adjustment M5 {adj}
set_global_routing_layer_adjustment M6 {adj}
set_global_routing_layer_adjustment M7 {adj7}
set_global_routing_layer_adjustment M8 0.4
set_global_routing_layer_adjustment M9 0.4
{nd}if {{[catch {{global_route -congestion_iterations 50 -critical_nets_percentage 0 -allow_congestion -verbose -congestion_report_file /out/congestion_$::env(CORNER).rpt}} e]}} {{ puts "OT_GRT_ERROR $e" }}
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
delete_clock [get_clocks dck]
estimate_parasitics -global_routing
puts OT_DONE
"""
    Path(O, "combo.tcl").write_text(pre + tail)
    return dict(ports=len(rports), clock_ports=len(cports), insts=len(insts), pins=len(pins), corner=corner)


def overflow(log):
    """[H, V, total] of the GRT 'Total' usage line (None when absent)"""
    for ln in Path(log).read_text(errors="replace").splitlines()[::-1]:
        m = re.match(r"^Total\s+\d+\s+\d+\s+[\d.]+%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)", ln)
        if m:
            return [int(m.group(i)) for i in (1, 2, 3)]
    return None


def docker(name, mounts, cmd, image, mem="48g", cpus=8, env=()):
    a = ["docker", "run", "--rm", "--name", name, f"--memory={mem}", f"--memory-swap={mem}", f"--cpus={cpus}"]
    for k, v in env:
        a += ["-e", f"{k}={v}"]
    for src, dst, ro in mounts:
        a += ["-v", f"{src}:{dst}" + (":ro" if ro else "")]
    return subprocess.run(a + [image, "bash", "-lc", cmd], check=False).returncode


def step(run, out, kit, corners=("TT", "FF"), image="openroad/orfs:latest", name="rf2step", jobs_mem="48g"):
    run, out = Path(run).resolve(), Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if not (run / "pads.json").exists():
        (run / "pads.json").write_text("[]\n")
    DR.main(["prep", str(run), str(out / "clk")])
    nd = ndr_tcl(run, out / "ndr.tcl")
    res = dict(ndr=nd, corners={})
    for c in corners:
        O = out / f"grt_{c}"
        (O / "clk").mkdir(parents=True, exist_ok=True)
        for fn in ("ctree.v", "ctree_ck89.tcl", "tree.json"):
            (O / "clk" / fn).write_bytes((out / "clk" / fn).read_bytes())
        (O / "ndr.tcl").write_bytes((out / "ndr.tcl").read_bytes())
        combo(str(kit), str(O / "clk"), str(O), c, ndr_src="/out/ndr.tcl")
        subprocess.run([sys.executable, str(HERE.parent / "clk" / "ot_clk_die_ctree.py"), "tcl", str(O / "combo.tcl"),
                        f"/out/combo_{c}.spef", "--out", str(O / "combo.tcl")], check=True, capture_output=True)
        rc = docker(f"{name}-grt-{c}", [(str(kit), "/work", True), (str(O), "/out", False)],
                    f"source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit "
                    f"/out/combo.tcl > /out/combo_{c}.log 2>&1; echo EXIT $? >> /out/combo_{c}.log; chown -R "
                    f"{os.getuid()}:{os.getgid()} /out", image, mem=jobs_mem, env=(("CORNER", c), ("LIBDIR", LIBDIR)))
        ov = overflow(O / f"combo_{c}.log")
        subprocess.run([sys.executable, str(HERE.parent / "clk" / "ot_clk_die_ctree.py"), "build", "--ctree-v",
                        str(O / "clk" / "ctree.v"), "--spef", str(O / f"combo_{c}.spef"), "--out", str(O / "die_ctree"),
                        "--prefix", "ck_"], check=True, capture_output=True)
        pd = out / f"pd_{c}"
        DR.main(["pads", str(run), str(O / "die_ctree" / "ctree.spef"), str(pd), "--route-ndr"])
        rc2 = docker(f"{name}-sta-{c}", [(str(out), str(out), False), (str(HERE), str(HERE), True)],
                     f"source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; export PATH=/OpenROAD-flow-scripts/tools/"
                     f"install/OpenROAD/bin:$PATH; cd {HERE} && python3 -B die_clock.py sta {pd} --corner {c} --libdir "
                     f"{LIBDIR}; chown -R {os.getuid()}:{os.getgid()} {pd}", image, mem="32g", cpus=4)
        arr = pd / f"arr_{c}.txt"
        sp = None
        if arr.exists():
            v = list(DC.read_arr(arr)[0].values())
            sp = round(max(v) - min(v), 1) if v else None
        res["corners"][c] = dict(arr=str(arr), overflow=ov, spread_ps=sp, grt_rc=rc, sta_rc=rc2)
    res["pad_um"] = json.loads((out / f"pd_{corners[0]}" / "pad_demand.json").read_text()).get("pad_um")
    (out / "step.json").write_text(json.dumps(res, indent=1) + "\n")
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("out")
    ap.add_argument("--kit", required=True, help="die_trial signal kit dir (grt/route.v, grt/grt.tcl, abstracts)")
    ap.add_argument("--corner", action="append")
    ap.add_argument("--ndr", default="4w")
    ap.add_argument("--wide-levels", type=int, default=10)
    ap.add_argument("--image", default="openroad/orfs:latest")
    ap.add_argument("--name-prefix", default="rf2step")
    a = ap.parse_args(argv)
    set_ndr(a.ndr, a.wide_levels)
    r = step(a.run, a.out, a.kit, tuple(a.corner or ["TT", "FF"]), a.image, a.name_prefix)
    print(json.dumps({c: {k: v for k, v in d.items() if k != "arr"} for c, d in r["corners"].items()}))
    return 0 if all(d["overflow"] == [0, 0, 0] and d["spread_ps"] is not None for d in r["corners"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
