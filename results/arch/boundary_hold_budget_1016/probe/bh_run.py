#!/usr/bin/env python3
"""FLOW-HOLD probe driver (runs ON the fleet host): bh_run.py OUTDIR C U JOB=RUNDIR ... -> OUTDIR/<job>.{ff,tt}.log"""
import concurrent.futures as cf, glob, os, re, subprocess, sys
PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
L = ["AO_RVT_{c}_nldm_211120.lib.gz", "INVBUF_RVT_{c}_nldm_220122.lib.gz", "OA_RVT_{c}_nldm_211120.lib.gz",
     "SEQ_RVT_{c}_nldm_220123.lib", "SIMPLE_RVT_{c}_nldm_211120.lib.gz"]
HERE = os.path.dirname(os.path.abspath(__file__))
out, C, U = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)


def vts(odb):
    found = set()
    pat = re.compile(rb"_ASAP7_75t_(SL|L)(?![A-Za-z0-9_])")
    with open(odb, "rb") as fh:
        tail = b""
        while True:
            ch = fh.read(1 << 26)
            if not ch: break
            found.update(m.group(1).decode() for m in pat.finditer(tail + ch)); tail = ch[-32:]
    return [v for v in ("L", "SL") if v in found]


def one(arg):
    job, run = arg.split("=", 1)
    bases = glob.glob(f"{run}/routes/*/work/orfs/results/asap7/*/base")
    if not bases: return job, "NOBASE"
    base = bases[0]; rdir = base.split("/work/orfs/")[0]
    sdc = f"{rdir}/signoff.sdc" if os.path.exists(f"{rdir}/signoff.sdc") else ""
    v = vts(f"{base}/6_final.odb")
    for corner in ("ff", "tt"):
        c = corner.upper()
        libs = [f"{PLAT}/lib/NLDM/asap7sc7p5t_" + l.format(c=c) for l in L]
        libs += [x.replace("_RVT_", "_LVT_" if t == "L" else "_SLVT_") for t in v for x in libs[:5]]
        lefs = [f"{PLAT}/lef/asap7_tech_1x_201209.lef", f"{PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef"] + \
               [f"{PLAT}/lef/asap7sc7p5t_28_{t}_1x_220121a.lef" for t in v]
        env = ["-e", f"BH_CORNER={corner}", "-e", f"BH_BASE={base}", "-e", f"BH_SDC={sdc}", "-e", f"BH_C={C}",
               "-e", f"BH_U={U}", *(["-e", "BH_OUTONLY=1"] if os.environ.get("BH_OUTONLY") else []), "-e", "BH_LIBS=" + " ".join(libs), "-e", "BH_LEFS=" + " ".join(lefs)]
        cmd = ["docker", "run", "--rm", "-v", f"{run}:{run}:ro", "-v", f"{HERE}:/bh:ro", *env, "openroad/orfs:asap7lock",
               "bash", "-lc", "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /bh/bh_probe.tcl"]
        p = subprocess.run(cmd, capture_output=True, text=True)
        open(f"{out}/{job}.{corner}.log", "w").write(f"BASE {base}\nSDC {sdc}\nVT {v}\n" + p.stdout + "\n--stderr--\n" + p.stderr[-4000:])
    return job, "OK"


with cf.ThreadPoolExecutor(int(os.environ.get("BH_PAR", "6"))) as ex:
    for j, s in ex.map(one, sys.argv[4:]): print(j, s, flush=True)
