#!/usr/bin/env python3
"""W18: die-level route of the V4.1 ROM layer die over the REAL-element floorplan (bundled global route).

The floorplan is tools/w18/die_floorplan.py's: 464 ROM-array clusters (column segments of W10's hardened
pair), the hub partitions, the HBM service bands and PHYs, the SerDes lanes and the UCIe modules.  Every
block is an abstract; the top level holds only the channel nets.  The route reuses W3's bundled technology
(tools/chip_assembly/v41_die.py: every layer's pitch x k, one net = k wires, track capacity per channel
preserved), because OpenROAD's GCell is fixed at 15 pitches (2.8e9 GCells for the die unbundled).

Nets (widths from the ports that exist; ASSUMED where the ledger has no edge):
  xb.<band><side>   x broadcast trunk: SU_VECTOR (the x root, W10 re-fit) -> every used cluster of one spine
                    band on one side of the hub; 549 bits = the pair's xs_* ports (ot_v41_rom_elem_q).
  rs.<band><side>   result return trunk: the same clusters -> VM; 256 bits (ASSUMED: the pack's spine result
                    share; the return tree is inside the clusters and the spine).
  px.<cluster>      probe: SU_VECTOR -> the cluster, one bundle; it measures the routed source-to-cluster path
                    length that a multi-pin trunk's total length cannot give (the crossing latency).
  pr.<cluster>      probe: the cluster -> VM.
  HBM, index, collective, link and hub-internal buses as W3 (ledger widths).
Crossing cycles = ceil(routed path / reach), reach = (920 - 60 - flop overhead) / ps_per_um of the routed
ASAP7 wire model (floorplans.wire_delay_model), compared with the model's 16 (VM -> farthest ROM),
22 (COLLECTIVE -> SerDes), 16 (COLLECTIVE -> UCIe).

    python3 tools/w18/die_route.py write --floorplan F --pack P --work W [--k 32]
    python3 tools/w18/die_route.py run --work W [--host ot-pve2]
    python3 tools/w18/die_route.py record --floorplan F --pack P --work W --output R.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from chip_assembly import v41_die as D  # noqa: E402
from chip_assembly import floorplans as FP  # noqa: E402

PAIR_X_BITS = 549          # xs_q0/q1 256+256, xs_e0/e1 10+10, xs_p 8, xs_b 3, xs_pos 3, xs_sv 2, xs_v 1
RESULT_BITS = 256          # ASSUMED spine result share (pack channel ledger: 512 act + 256 result + 64 ctrl)
MODEL = {"xb": 16, "link_serdes": 22, "link_ucie": 16}


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def model(fp: dict, pk: dict, probes: bool = True) -> dict:
    C = D.Cluster
    mm = lambda v: round(v / 1000.0, 6)  # noqa: E731
    cl, buses = [], []
    for c in fp["clusters"]:
        cl.append(C(c["name"], "w18_rom_cluster", "tile", mm(c["x"]), mm(c["y"]), mm(c["w"]), mm(c["h"]),
                    basis=f"{c['used_rows']} W10 p5 pairs (real abstract)", region=f"b{c['band']}"))
    hub = {}
    for nm, r in fp["hub"]["parts"].items():
        k = nm.replace("HUB_", "").lower()
        hub[k] = C(f"hub_{k}", "w18_hub", "hub", mm(r["x"]), mm(r["y"]), mm(r["w"]), mm(r["h"]),
                   basis=f"PLACEHOLDER {nm} (W11 hardened hub element pending)")
        cl.append(hub[k])
    svc = []
    for nm, r in fp["service"].items():
        s = C(nm.lower(), "w18_svc", "hbm_svc", mm(r["x"]), mm(r["y"]), mm(r["w"]), mm(r["h"]),
              basis="PLACEHOLDER HBM service band")
        svc.append(s)
        cl.append(s)
    links = {"SERDES": [], "UCIE": []}
    for nm, master, x, y, o, grp in pk["instances"]:
        if grp in ("SERDES", "UCIE"):
            w, h = (1000.08, 401.76) if grp == "SERDES" else (1043.28, 388.8)
            c = C(nm, master, grp.lower(), mm(x), mm(y), mm(w), mm(h), basis=f"PLACEHOLDER {master} (W15 pending)")
            links[grp].append(c)
            cl.append(c)
        elif grp == "HBM_PHY":
            from die_floorplan import lef_macro  # noqa: E402
            lm = lef_macro(ROOT / "physical/asap7_memory_macros" / master / f"{master}.lef")
            cl.append(C(nm, master, "phy_hbm", mm(x), mm(y), mm(lm["w"]), mm(lm["h"]), orient="R0",
                        basis="legal v2 PHY abstract"))
    B = D.Bus
    xr, vm = hub["su_vector"], hub["vm"]
    groups: dict[str, list] = {}
    for c in (c for c in cl if c.kind == "tile"):
        side = "w" if c.cx < xr.cx else "e"
        groups.setdefault(f"{c.region}{side}", []).append(c)
    for g, members in sorted(groups.items()):
        buses.append(dict(id=f"xb.{g}", src=xr.inst, dst=[m.inst for m in members], bits=PAIR_X_BITS,
                          basis="x broadcast trunk (pair xs_* width)", cls="xb"))
        buses.append(dict(id=f"rs.{g}", src=vm.inst, dst=[m.inst for m in members], bits=RESULT_BITS,
                          basis="ASSUMED result return trunk", cls="rs"))
    for c in (c for c in cl if c.kind == "tile" and probes):
        buses.append(dict(id=f"px.{c.inst}", src=xr.inst, dst=[c.inst], bits=1, basis="probe", cls="px"))
        buses.append(dict(id=f"pr.{c.inst}", src=c.inst, dst=[vm.inst], bits=1, basis="probe", cls="pr"))
    conn = {e["id"]: e for e in D.load(D.INPUTS["connectivity"])["edges"]}
    w = lambda e: int(conn[e]["data_bits"])  # noqa: E731
    coll, att = hub["collective"], hub["attention"]
    for grp, cls in (("SERDES", "link_serdes"), ("UCIE", "link_ucie")):
        buses.append(dict(id=f"{cls}.tx", src=coll.inst, dst=[m.inst for m in links[grp]], bits=512,
                          basis="ASSUMED 512-bit link flit (W3)", cls=cls))
        far = max(links[grp], key=lambda m: abs(m.cx - coll.cx) + abs(m.cy - coll.cy))
        buses.append(dict(id=f"{cls}.far", src=coll.inst, dst=[far.inst], bits=1, basis="probe farthest lane",
                          cls=cls + "_probe"))
    idx = conn["index_select"]["service"]
    idx_bits = int(math.ceil(idx["reader_sectors"] / idx["reader_cycles"] / len(svc))) * 256
    for s in svc:
        buses.append(dict(id=f"hbm_window.{s.inst}", src=s.inst, dst=[att.inst], bits=w("hbm_window"),
                          basis="ledger hbm_window", cls="hbm_window"))
        buses.append(dict(id=f"idx_keys.{s.inst}", src=s.inst, dst=[att.inst], bits=idx_bits,
                          basis="index keys at the measured reader rate", cls="idx_keys"))
        buses.append(dict(id=f"selected_kv.{s.inst}", src=att.inst, dst=[s.inst], bits=w("selected_kv"),
                          basis="ledger selected_kv", cls="selected_kv"))
        buses.append(dict(id=f"idx_topk.{s.inst}", src=s.inst, dst=[xr.inst], bits=32,
                          basis="index partial top-k -> SU selector (pack crossing)", cls="idx_topk"))
    buses += [dict(id="vm_coll", src=vm.inst, dst=[coll.inst], bits=w("vm_collective"), basis="ledger", cls="hub"),
              dict(id="coll_vm", src=coll.inst, dst=[vm.inst], bits=w("collective_vm"), basis="ledger", cls="hub"),
              dict(id="pv_preload", src=vm.inst, dst=[att.inst], bits=w("vm_pv_preload"), basis="ledger", cls="hub"),
              dict(id="q_attn", src=vm.inst, dst=[att.inst], bits=w("vm_he"), basis="ledger vm_he", cls="hub"),
              dict(id="attn_out", src=att.inst, dst=[vm.inst], bits=512, basis="ASSUMED", cls="hub")]
    return dict(clusters=cl, buses=buses, die_mm=[fp["die"]["w_um"] / 1000, fp["die"]["h_um"] / 1000])


def edge_for(c, peer_x, peer_y):
    """Pins of a ROM cluster face the spine (N/S) -- its E/W sides are 8.64 um column gaps; other blocks
    face their peer."""
    if c.kind == "tile":
        return "S" if peer_y < c.cy else "N"
    dx, dy = peer_x - c.cx, peer_y - c.cy
    if abs(dx) - c.w / 2 > abs(dy) - c.h / 2:
        return "E" if dx > 0 else "W"
    return "N" if dy > 0 else "S"


def write(m: dict, work: Path, k: int, obs_top: int, m89: float, low: float, iters: int = 50) -> dict:
    work.mkdir(parents=True, exist_ok=True)
    cl = {c.inst: c for c in m["clusters"]}
    plan: dict[str, dict[str, list]] = {}
    for b in m["buses"]:
        n = D.bundle_count(b["bits"], k)
        s = cl[b["src"]]
        dsts = [cl[d] for d in b["dst"]]
        # source pins face the sinks' centroid; each sink's pins face the source
        gx = sum(d.cx for d in dsts) / len(dsts)
        gy = sum(d.cy for d in dsts) / len(dsts)
        port = "o_" + re.sub(r"[^A-Za-z0-9]", "_", b["id"])
        e = edge_for(s, gx, gy)
        key = gy if e in ("E", "W") else gx
        for i in range(n):
            plan.setdefault(s.inst, {}).setdefault(e, []).append((f"{port}[{i}]", "OUTPUT", key + i * 1e-6))
        for d in dsts:
            e = edge_for(d, s.cx, s.cy)
            key = s.cy if e in ("E", "W") else s.cx
            if d.kind == "tile":
                key = d.cx                              # centred on the cluster's own edge
            pi = "i_" + re.sub(r"[^A-Za-z0-9]", "_", b["id"])
            for i in range(n):
                plan.setdefault(d.inst, {}).setdefault(e, []).append((f"{pi}[{i}]", "INPUT", key + i * 1e-6))
    for inst in plan:
        for e in plan[inst]:
            plan[inst][e].sort(key=lambda t: t[2])
    growth = []
    for c in m["clusters"]:
        for e, lst in plan.get(c.inst, {}).items():
            need = (len(lst) + 4) * 0.048 * k
            have = (c.h if e in ("E", "W") else c.w) * 1000
            if need > have:
                growth.append(dict(inst=c.inst, edge=e, bundle_pins=len(lst), need_um=round(need, 1),
                                   have_um=round(have, 1)))
                if c.kind == "tile":
                    raise SystemExit(f"ROM cluster {c.inst} edge {e} cannot hold {len(lst)} bundle pins")
                if e in ("E", "W"):
                    c.h = need / 1000
                else:
                    c.w = need / 1000
    lefs = ['VERSION 5.8 ;', 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;']
    masters = {}
    for c in m["clusters"]:
        masters[c.inst] = f"M__{c.inst}"
        text, _ = D.cluster_lef(c, plan.get(c.inst, {}), k, obs_top, masters[c.inst])
        lefs.append(text)
    lefs.append("END LIBRARY\n")
    (work / "clusters.lef").write_text("\n".join(lefs))
    (work / "tech.lef").write_text(D.bundled_tech_lef(k))
    v = ["module w18_die ();"]
    conns: dict[str, list] = {c.inst: [] for c in m["clusters"]}
    for b in m["buses"]:
        n = D.bundle_count(b["bits"], k)
        tag = re.sub(r"[^A-Za-z0-9]", "_", b["id"])
        net = "n_" + tag
        v.append(f"  wire [{n - 1}:0] {net};")
        conns[b["src"]].append(f".o_{tag}({net})")
        for d in b["dst"]:
            conns[d].append(f".i_{tag}({net})")
    for c in m["clusters"]:
        v.append(f"  {masters[c.inst]} {c.inst} (" + ", ".join(conns[c.inst]) + ");")
    v.append("endmodule\n")
    (work / "die.v").write_text("\n".join(v))
    W, H = m["die_mm"][0] * 1000, m["die_mm"][1] * 1000
    tracks = [f"make_tracks {nm} -x_offset {r[2] * k:.3f} -x_pitch {p * k:.3f} -y_offset {r[2] * k:.3f} "
              f"-y_pitch {p * k:.3f}" for nm, d, p, *r in D.ASAP7_LAYERS]
    g = 0.054 * k
    place = [f"place_inst -name {c.inst} -location {{{round(round(c.x * 1000 / g) * g, 3)} "
             f"{round(round(c.y * 1000 / g) * g, 3)}}} -orientation R0 -status FIRM" for c in m["clusters"]]
    adj = [f"set_global_routing_layer_adjustment {nm} {m89 if nm in ('M8', 'M9') else low}"
           for nm, *_ in D.ASAP7_LAYERS[1:]]
    tcl = f"""proc mem {{tag}} {{ set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {{VmRSS:\\s+(\\d+)}} $s -> r; puts "OTMEM $tag [expr {{$r/1024}}] MB [clock seconds]" }}
read_lef /work/tech.lef
read_lef /work/clusters.lef
read_verilog /work/die.v
link_design w18_die
initialize_floorplan -die_area {{0 0 {W:.3f} {H:.3f}}} -core_area {{0 0 {W:.3f} {H:.3f}}} -site bsite
{chr(10).join(tracks)}
{chr(10).join(place)}
mem placed
{chr(10).join(adj)}
set_routing_layers -signal M2-M9
global_route -verbose -allow_congestion -congestion_iterations {iters} -congestion_report_file /work/grt_congestion.rpt
mem grt
report_wire_length -net * -global_route -file /work/wirelength.csv
set blk [ord::get_db_block]
set out [open /work/gcell_usage.txt w]
set grid [$blk getGCellGrid]
if {{$grid ne "NULL"}} {{
  set gx [$grid getGridX]
  set gy [$grid getGridY]
  puts $out "GRIDX [join $gx ,]"
  puts $out "GRIDY [join $gy ,]"
  set tech [ord::get_db_tech]
  foreach ln {{M4 M5 M6 M7 M8 M9}} {{
    set layer [$tech findLayer $ln]
    set nx [llength $gx]; set ny [llength $gy]
    for {{set j 0}} {{$j < $ny}} {{incr j 4}} {{
      set row {{}}
      for {{set i 0}} {{$i < $nx}} {{incr i 4}} {{
        set cap 0; set use 0
        for {{set jj $j}} {{$jj < min($j+4,$ny)}} {{incr jj}} {{
          for {{set ii $i}} {{$ii < min($i+4,$nx)}} {{incr ii}} {{
            set cap [expr {{$cap + [$grid getCapacity $layer $ii $jj]}}]
            set use [expr {{$use + [$grid getUsage $layer $ii $jj]}}]
          }}
        }}
        lappend row "$cap/$use"
      }}
      puts $out "L $ln $j [join $row {{ }}]"
    }}
  }}
}}
close $out
mem done
"""
    (work / "run.tcl").write_text(tcl)
    man = dict(k=k, congestion_iterations=iters, obs_top=f"M{obs_top}", m8_m9_reserve=m89, m2_m7_adjustment=low, growth=growth,
               bundle_nets=sum(D.bundle_count(b["bits"], k) for b in m["buses"]),
               wires=sum(b["bits"] * 1 for b in m["buses"] if b["cls"] not in ("px", "pr")),
               instances=len(m["clusters"]), buses=len(m["buses"]))
    (work / "manifest.json").write_text(json.dumps(man, indent=1))
    return man


def run(work: Path, host: str, mem_gb: int) -> int:
    cmd = (f"docker run --rm --memory={mem_gb}g -v {work}:/work -w /work {D.ORFS_IMAGE} bash -lc "
           f"'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -exit "
           f"/work/run.tcl > /work/grt.log 2>&1; chmod -R a+rwX /work'")
    t = time.time()
    if host:
        subprocess.run(["ssh", host, f"mkdir -p {work.parent}"], check=True)
        subprocess.run(["rsync", "-a", "--delete", f"{work}/", f"{host}:{work}/"], check=True)
        p = subprocess.run(["ssh", host, cmd])
        subprocess.run(["rsync", "-a", f"{host}:{work}/", f"{work}/"], check=True)
    else:
        p = subprocess.run(cmd, shell=True)
    (work / "run_meta.json").write_text(json.dumps(dict(host=host or "local", wall_s=round(time.time() - t, 1),
                                                        rc=p.returncode)))
    return p.returncode


def record(m: dict, work: Path, fp_path: Path, pk_path: Path, k: int) -> dict:
    lens = D.parse_wirelength(work / "wirelength.csv")
    log = (work / "grt.log").read_text()
    glog = D.parse_log(log)
    wm = FP.wire_delay_model()
    reach = (D.PERIOD_PS - D.UNCERTAINTY_PS - wm["overhead_ps"]) / wm["ps_per_um"]
    cl = {c.inst: c for c in m["clusters"]}
    per = []
    for b in m["buses"]:
        tag = "n_" + re.sub(r"[^A-Za-z0-9]", "_", b["id"])
        n = D.bundle_count(b["bits"], k)
        ls = [lens.get(f"{tag}[{i}]") for i in range(n)] if n > 1 else [lens.get(tag, lens.get(f"{tag}[0]"))]
        ls = [x for x in ls if x is not None]
        L = max(ls) if ls else None
        two_pin = len(b["dst"]) == 1
        s = cl[b["src"]]
        manh = max(abs(s.cx - cl[d].cx) + abs(s.cy - cl[d].cy) for d in b["dst"]) * 1000
        per.append(dict(id=b["id"], cls=b["cls"], bits=b["bits"], sinks=len(b["dst"]), basis=b["basis"],
                        centre_manhattan_um=round(manh, 1), routed_um=round(L, 1) if L else None,
                        routed_is_path=two_pin,
                        cycles=math.ceil(L / reach) if (L and two_pin) else None))
    cls = {}
    for r in per:
        c = cls.setdefault(r["cls"], dict(nets=0, wires=0, max_routed_um=0, max_cycles=None, max_manhattan_um=0))
        c["nets"] += 1
        c["wires"] += r["bits"]
        c["max_routed_um"] = max(c["max_routed_um"], r["routed_um"] or 0)
        c["max_manhattan_um"] = max(c["max_manhattan_um"], r["centre_manhattan_um"])
        if r["cycles"] is not None:
            c["max_cycles"] = max(c["max_cycles"] or 0, r["cycles"])
    px = [r for r in per if r["cls"] == "px" and r["cycles"]]
    pr = [r for r in per if r["cls"] == "pr" and r["cycles"]]
    cross = {
        "vm_xroot_to_farthest_cluster": dict(routed_um=max(r["routed_um"] for r in px), cycles=max(r["cycles"] for r in px),
                                             model_cycles=MODEL["xb"],
                                             histogram=_hist([r["cycles"] for r in px])),
        "farthest_cluster_to_vm": dict(routed_um=max(r["routed_um"] for r in pr), cycles=max(r["cycles"] for r in pr),
                                       histogram=_hist([r["cycles"] for r in pr])),
        "collective_to_farthest_serdes": next(dict(routed_um=r["routed_um"], cycles=r["cycles"],
                                                   model_cycles=MODEL["link_serdes"]) for r in per
                                              if r["cls"] == "link_serdes_probe"),
        "collective_to_farthest_ucie": next(dict(routed_um=r["routed_um"], cycles=r["cycles"],
                                                 model_cycles=MODEL["link_ucie"]) for r in per
                                            if r["cls"] == "link_ucie_probe"),
    }
    for c in ("hbm_window", "idx_keys", "selected_kv", "idx_topk", "hub"):
        rs = [r for r in per if r["cls"] == c]
        cross[c] = dict(max_routed_um=max((r["routed_um"] or 0) for r in rs), max_cycles=max((r["cycles"] or 0) for r in rs),
                        per_net={r["id"]: r["cycles"] for r in rs})
    peak = next((int(l.split(":")[1]) for l in log.splitlines() if "Maximum resident set size" in l), None)
    return dict(
        schema="opentallas.v41.w18_die_route.v1",
        status="bundled_die_global_route" if lens else "not_routed",
        claim_boundary=("die-level placement of the real-element floorplan (ROM clusters of the routed W10 p5 pair; "
                        "hub, service and link blocks are PLACEHOLDERS) and bundled global route of the top-level "
                        "channel nets; crossing cycles from routed 2-pin probe paths and the routed ASAP7 wire model; "
                        "real-technology detailed route and timing of the channels are in the channel records"),
        manifest=json.loads((work / "manifest.json").read_text()),
        run=json.loads((work / "run_meta.json").read_text()) if (work / "run_meta.json").exists() else None,
        global_route={k_: v for k_, v in glog.items() if k_ != "mem"}, peak_rss_kb=peak,
        wire_model=dict(wm, reach_um=round(reach, 1)),
        crossings=cross, classes=cls, nets=per,
        inputs=dict(floorplan=str(fp_path), floorplan_sha256=sha(fp_path), pack=str(pk_path), pack_sha256=sha(pk_path),
                    tool_sha256=sha(Path(__file__)), v41_die_sha256=sha(D.__file__)))


def _hist(xs):
    h = {}
    for x in xs:
        h[x] = h.get(x, 0) + 1
    return dict(sorted(h.items()))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mode", choices=["write", "run", "record"])
    ap.add_argument("--floorplan", type=Path)
    ap.add_argument("--pack", type=Path)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--k", type=int, default=32)
    ap.add_argument("--obs-top", type=int, default=7)
    ap.add_argument("--m89-reserve", type=float, default=0.30)
    ap.add_argument("--low-adjust", type=float, default=0.25)
    ap.add_argument("--iters", type=int, default=50)
    ap.add_argument("--no-probes", action="store_true", help="congestion case without the 1-bundle path probes")
    ap.add_argument("--host", default="")
    ap.add_argument("--memory-gb", type=int, default=100)
    ap.add_argument("--output", type=Path)
    a = ap.parse_args(argv)
    work = a.work.resolve()
    if a.mode == "run":
        return run(work, a.host, a.memory_gb)
    fp, pk = json.loads(a.floorplan.read_text()), json.loads(a.pack.read_text())
    mdl = model(fp, pk, probes=not a.no_probes)
    if a.mode == "write":
        print(json.dumps(write(mdl, work, a.k, a.obs_top, a.m89_reserve, a.low_adjust, a.iters), indent=1))
        return 0
    rec = record(mdl, work, a.floorplan, a.pack, a.k)
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(gr=rec["global_route"].get("total"), cross=rec["crossings"]), indent=1)[:4000])
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "tools/w18"))
    raise SystemExit(main())
