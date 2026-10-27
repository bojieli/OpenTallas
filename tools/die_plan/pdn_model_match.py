#!/usr/bin/env python3
"""pdn_model_match: the real pdngen PDN of a die vs the die_infra PG model (ONE PDN RULE, COORD 10-26 13:13, PDN-ONE).

The clock / shield / reset tools place wires against die_infra.pg_rects(P, pg_grid(P)).  That model is only freeze
evidence when it IS the PDN the die is built with: this gate runs OpenROAD pdngen (docker, memory cap) on the real PDN
script of one generator on an empty die of the plan's outline, dumps every special-net wire (all layers, vias skipped)
and compares it with the model rect for rect in dbu.  MATCH = identical multisets of (net, layer, rect) after merging
touching collinear same-net pieces; anything else is MISMATCH with the difference classified (net swap on a common
track, track only in the real PDN / only in the model, same track + net with different extents).

  pdn_model_match.py PLAN --out DIR [--gen regions|trial|assembly] [--pg PG.json] [--mem 16g] [--image IMG]
  pdn_model_match.py PLAN --out DIR --dump REAL.txt        # compare an existing dump only (no docker)

  --gen regions   pg_regions.pdn_tcl (the regional VDD / VDDPHY PDN of the assembly with pg_map)
        trial     die_trial.psm_pdn_tcl (die_trial / infra_pg kits)
        assembly  gen_phys.die_pdn_tcl without pg_map (core-only assembly)
Report DIR/pdn_model_match.json; exit 0 on MATCH, 1 on MISMATCH, 2 on a run failure."""
import argparse
import collections
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_infra as DI  # noqa: E402
import pg_regions as G  # noqa: E402
import schema as S  # noqa: E402

DBU = 1000                       # asap7 LEF DATABASE MICRONS
IMAGE = "openroad/orfs:asap7lock"
OPENROAD = "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"
PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"

RUN_TCL = """read_lef {plat}/lef/asap7_tech_1x_201209.lef
read_lef {plat}/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_verilog /w/top.v
link_design top
initialize_floorplan -die_area {{0 0 {W} {H}}} -core_area {{0 0 {W} {H}}} -site asap7sc7p5t
source /w/pdn.tcl
pdngen
set blk [ord::get_db_block]
set fh [open /w/real.txt w]
foreach n [$blk getNets] {{
  if {{![$n isSpecial]}} {{ continue }}
  foreach sw [$n getSWires] {{
    foreach b [$sw getWires] {{
      if {{[$b isVia]}} {{ continue }}
      puts $fh "[$n getName] [[$b getTechLayer] getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax]"
    }}
  }}
}}
close $fh
puts PDN_DUMP_DONE
"""


def gen_tcl(P, gen, pg=None):
    die = dict(P.die, outline_um=[P.W, P.H])
    grid = json.loads(Path(pg).read_text())["grid"] if pg else None
    if grid is not None:
        die["pg"] = dict(die.get("pg", {}), grid=grid)
        P.die = die
    if gen == "regions":
        return G.pdn_tcl(die)
    if gen == "trial":
        import die_trial
        return die_trial.psm_pdn_tcl(P)
    if gen == "assembly":
        import gen_phys
        return gen_phys.die_pdn_tcl(P)
    raise SystemExit(f"unknown --gen {gen}")


def merge(rects):
    """merge touching / overlapping collinear same-net same-track pieces -> Counter of (net, layer, x0, y0, x1, y1)."""
    by = collections.defaultdict(list)
    for n, L, x0, y0, x1, y1 in rects:
        V = (x1 - x0) <= (y1 - y0)
        by[(n, L, V, (x0, x1) if V else (y0, y1))].append((y0, y1) if V else (x0, x1))
    out = collections.Counter()
    for (n, L, V, (a, b)), ivs in by.items():
        ivs.sort()
        m = []
        for s, e in ivs:
            if m and s <= m[-1][1]:
                m[-1][1] = max(m[-1][1], e)
            else:
                m.append([s, e])
        for s, e in m:
            out[(n, L) + ((a, s, b, e) if V else (s, a, e, b))] += 1
    return out


def track(r):
    n, L, x0, y0, x1, y1 = r
    V = (x1 - x0) <= (y1 - y0)
    return (L, "V" if V else "H", x0 + x1 if V else y0 + y1, x1 - x0 if V else y1 - y0)   # 2*centre, width (dbu)


def compare(real, model, limit=8):
    A, B = merge(real), merge(model)
    only_r, only_m = A - B, B - A
    ta, tb = collections.defaultdict(set), collections.defaultdict(set)
    for r in A:
        ta[track(r)].add(r[0])
    for r in B:
        tb[track(r)].add(r[0])
    common = set(ta) & set(tb)
    swap = collections.Counter(f"real {'/'.join(sorted(ta[t]))} | model {'/'.join(sorted(tb[t]))}"
                               for t in common if ta[t] != tb[t])
    tr_only = sorted(set(ta) - set(tb))
    tm_only = sorted(set(tb) - set(ta))
    extent = sum(1 for r in only_r if track(r) in common and r[0] in tb[track(r)])
    layers = collections.Counter(r[1] for r in A.elements())
    um = lambda r: [r[0], r[1]] + [v / DBU for v in r[2:]]
    return dict(verdict="MATCH" if not only_r and not only_m else "MISMATCH",
                real_rects=sum(A.values()), model_rects=sum(B.values()), real_layers=dict(layers),
                only_real=sum(only_r.values()), only_model=sum(only_m.values()),
                tracks_real=len(ta), tracks_model=len(tb), common_tracks=len(common),
                net_mismatch_tracks=sum(swap.values()), net_mismatch=dict(swap.most_common(6)),
                tracks_only_real=len(tr_only), tracks_only_model=len(tm_only),
                extent_diff_rects=extent,
                ex_only_real=[um(r) for r in sorted(only_r)[:limit]],
                ex_only_model=[um(r) for r in sorted(only_m)[:limit]])


def load_dump(path):
    out = []
    for line in Path(path).read_text().splitlines():
        n, L, *v = line.split()
        out.append((n, L) + tuple(int(round(float(x))) for x in v))
    return out


def model_dbu(P, pg=None):
    D = DBU
    return [(n, L) + tuple(int(round(v * D)) for v in (x0, y0, x1, y1))
            for n, L, x0, y0, x1, y1 in DI.pg_rects(P, DI.pg_grid(P, pg))]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--out", required=True)
    ap.add_argument("--gen", default="trial", choices=("regions", "trial", "assembly"))
    ap.add_argument("--pg", help="IR-sized pg.json (grid) used by both the PDN script and the model")
    ap.add_argument("--dump", help="existing real dump (net layer x0 y0 x1 y1 in dbu); skips pdngen")
    ap.add_argument("--image", default=IMAGE)
    ap.add_argument("--mem", default="16g")
    a = ap.parse_args(argv)
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    P = S.Plan(S.load(a.plan), Path(a.plan))
    rep = dict(schema="opentallas.pdn_model_match.v1", plan=str(Path(a.plan).resolve()), die=P.name,
               outline_um=[P.W, P.H], gen=a.gen, pg=a.pg, domains=len(P.die.get("pg", {}).get("domains") or []))
    dump = a.dump
    if not dump:
        (out / "pdn.tcl").write_text(gen_tcl(S.Plan(S.load(a.plan), Path(a.plan)), a.gen, a.pg))
        (out / "top.v").write_text("module top(); endmodule\n")
        import gen_phys
        (out / "run.tcl").write_text(RUN_TCL.format(plat=PLAT, W=gen_phys._um(P.W), H=gen_phys._um(P.H)))
        t0 = time.time()
        cmd = ["docker", "run", "--rm", "-m", a.mem, "--memory-swap", a.mem, "-v", f"{out}:/w", a.image,
               OPENROAD, "-exit", "/w/run.tcl"]
        with open(out / "pdngen.log", "w") as fh:
            rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT).returncode
        rep.update(image=a.image, mem=a.mem, pdngen_rc=rc, pdngen_s=round(time.time() - t0, 1))
        log = (out / "pdngen.log").read_text()
        if rc or "PDN_DUMP_DONE" not in log:
            rep["verdict"] = "RUN_FAIL"
            (out / "pdn_model_match.json").write_text(json.dumps(rep, indent=1) + "\n")
            print(json.dumps(rep))
            return 2
        dump = out / "real.txt"
    real = load_dump(dump)
    model = model_dbu(P, a.pg)
    rep.update(compare(real, model))
    um = lambda R: [(n, L) + tuple(v / DBU for v in r) for n, L, *r in R]
    rep["real_conflicts"] = {k: v for k, v in DI.pg_conflicts(um(real), limit=3).items()}
    (out / "pdn_model_match.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: v for k, v in rep.items() if not k.startswith("ex_")}))
    return 0 if rep["verdict"] == "MATCH" else 1


if __name__ == "__main__":
    sys.exit(main())
