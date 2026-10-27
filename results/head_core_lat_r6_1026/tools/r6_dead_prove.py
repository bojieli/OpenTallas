#!/usr/bin/env python3
"""HEAD-CORE-LAT-R6: prove the JOIN-0 elemB macro inputs row0/b_v/b_d dead (no load after flatten + opt).

Unlike tools/die_plan/dead_inputs.py (children opaque), the closed element ot_dsrom_head_elem consumes these ports
directly, so the proof elaborates the WHOLE macro flat from the kit's exact RTL (yosys proc; flatten; opt), with only the
ROM macro (ot_rom_4096x274_m8, blackbox) opaque: every blackbox input is counted as a load (conservative); top output
port bits count as loads.  PASS = every declared bit has zero loads.
usage (inside the ORFS image): r6_dead_prove.py KIT OUTDIR
"""
import hashlib, json, subprocess, sys
from pathlib import Path
kit, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
cfg = (kit / "config.mk").read_text()
files = [l.split("=", 1)[1].split() for l in cfg.splitlines() if l.startswith("export VERILOG_FILES")][0]
files = [str(kit / Path(f).relative_to("/work")) for f in files]
TOP, DEAD = "ot_s81hd_elemB_cv", {"row0": 17, "b_v": 1, "b_d": 32}
ys = (f"read_verilog -sv -DSYNTHESIS -I{kit}/rtl " + " ".join(files) + "\n"
      f"hierarchy -check -top {TOP}\nproc\nflatten\nopt -full\nopt_clean -purge\nwrite_json {out}/flat_opt.json\nstat\n")
(out / "run.ys").write_text(ys)
r = subprocess.run(["yosys", "-q", "-l", str(out / "yosys.log"), "-s", str(out / "run.ys")])
if r.returncode:
    sys.exit("yosys failed")
J = json.loads((out / "flat_opt.json").read_text())
m = J["modules"][TOP]
loads = {}
for p in m["ports"].values():
    if p["direction"] != "input":
        for b in p["bits"]:
            loads.setdefault(b, []).append("PORT_OUT")
for cn, c in m["cells"].items():
    for pn, bits in c["connections"].items():
        if c.get("port_directions", {}).get(pn, "input") != "output":
            for b in bits:
                loads.setdefault(b, []).append(cn + "." + pn)
res, ok = {}, True
for port, w in DEAD.items():
    bits = m["ports"][port]["bits"]
    assert len(bits) == w, (port, len(bits))
    live = {i: loads[b][:3] for i, b in enumerate(bits) if isinstance(b, int) and b in loads}
    res[port] = dict(width=w, loaded_bits=len(live), examples=dict(list(live.items())[:3]))
    ok &= not live
sha = {f: hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in files}
outj = dict(schema="opentallas.dead_inputs.flat.v1", top=TOP, method="yosys.proc.flatten.opt.no_fanout",
            opaque=["ot_rom_4096x274_m8 (blackbox: every input counted as a load)"],
            params="ot_dsrom_head_elem LV 6 PAD 2 JOIN 0 ROWS 128 CUT 0x1ff SPLIT9 1 IOREG 1 SAFE 1",
            ports={k: [[0, v - 1]] for k, v in DEAD.items()}, result=res,
            remaining_loads=sum(v["loaded_bits"] for v in res.values()),
            sources={Path(f).name: s for f, s in sha.items()}, verdict="PASS" if ok else "FAIL")
(out / "dead_inputs.json").write_text(json.dumps(outj, indent=1) + "\n")
print("DEAD_PROVE", outj["verdict"], json.dumps(res))
