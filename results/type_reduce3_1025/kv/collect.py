#!/usr/bin/env python3
"""TR3-KV-LEC 2026-10-25: collect the odd head strap-master LEC + lockstep receipts into this directory.

    python3 collect.py SCRATCH          (SCRATCH = epyc1:/srv/opentallas-scratch2/claude/tr3-kv)

Copies each lec.json (lec/<pair>.lec.json, lec/kit_m_e<M>.lec.json) and each miter sim.log, writes summary.json.
Receipts carry the run-time /work paths of lec.py; the sources they name are repo-relative at the commit in summary.json:
  generator  physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py (--head-lane-ltcopy --head-lane-taps
             [--head-strap-odd for the masters]), tools/die_plan/lec.py, tie_strap.py / pair_lec.sh / miter/miter.sh here.
"""
import hashlib, json, re, shutil, subprocess, sys
from pathlib import Path

S = Path(sys.argv[1]); HERE = Path(__file__).resolve().parent
PAIRS = {"m1_vs_e1": (1, 1, "00"), "m1_vs_e3": (1, 3, "01"), "m5_vs_e5": (5, 5, "10"), "m5_vs_e7": (5, 7, "11")}
(HERE / "lec").mkdir(exist_ok=True); (HERE / "miter" / "logs").mkdir(parents=True, exist_ok=True)


def lec(p, dst):
    if not p.is_file():
        return dict(verdict="RUNNING/MISSING", path=str(p))
    shutil.copy(p, dst)
    r = json.loads(p.read_text())
    return dict(verdict=r["verdict"], counts=r.get("counts"), note=r.get("note", r.get("reason")), t_total_s=r.get("t_total_s"),
                receipt=str(dst.relative_to(HERE.parents[2])))


out = dict(schema="opentallas.tr3_kv_lec.v1", lane="TR3-KV-LEC (TYPE-REDUCE-3)",
           commit=subprocess.run(["git", "-C", str(HERE), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
           rule="OWNER 10-25 option B: one hardened master, strap_* tied at the parent, false_path from straps, no pin register "
                "on straps, LEC each master against its old constant variants",
           method="gold = old constant-variant kit RTL (gen_core_kit_kv.py, old plan e6326d34 = aa073c9f47, same flags as the PATH-KV "
                  "e1f kit: RTL/SDC/config of old e1 byte-identical to e1f kit 374d479b); gate = master kit 1_2_yosys.v with strap_bsel "
                  "tied to the variant constant (assign) and alpha-renamed to the variant names (tie_strap.py); lec.py (= origin/main)",
           pairs={}, kit_lec={}, miter={})
for k, (m, n, b) in PAIRS.items():
    d = out["pairs"][k] = dict(master=f"e{m}", variant=f"e{n}", strap_bsel=f"2'b{b}")
    d.update(lec(S / "lec" / k / "out" / "lec.json", HERE / "lec" / f"{k}.lec.json"))
    sh = S / "lec" / k / "inputs.sha256"
    if sh.is_file():
        d["inputs_sha256"] = {Path(l.split()[1]).name: l.split()[0][:16] for l in sh.read_text().splitlines()}
for m in (1, 5):
    kd = next((S / "kits" / f"m_e{m}").glob("kv3_head_eighth_e*"))
    out["kit_lec"][f"m_e{m}"] = lec(kd / "lec" / "lec.json", HERE / "lec" / f"kit_m_e{m}.lec.json")
    out["kit_lec"][f"m_e{m}"]["kit_hash"] = json.loads((kd / "freeze.json").read_text())["kit_hash"]
    sdc = (kd / "constraint.sdc").read_text()
    out["kit_lec"][f"m_e{m}"]["sdc_false_path_strap"] = "set_false_path -from [get_ports {strap_bsel}]" in sdc
for c in ("m1_e1", "m1_e3", "m5_e5", "m5_e7", "mut_m1_e3_00"):
    lg = S / "miter" / c / "sim.log"
    line = next((l for l in lg.read_text().splitlines() if "CORE MITER" in l), None) if lg.is_file() else None
    if lg.is_file():
        shutil.copy(lg, HERE / "miter" / "logs" / f"{c}.sim.log")
    mm = re.search(r"(PASS|FAIL) mismatches=(\d+).*edges=(\d+)", line or "")
    out["miter"][c] = dict(line=line, result=mm and mm.group(1), mismatches=mm and int(mm.group(2)), edges=mm and int(mm.group(3)),
                           expect="FAIL" if c.startswith("mut") else "PASS")
(HERE / "summary.json").write_text(json.dumps(out, indent=1) + "\n")
print(json.dumps({k: v.get("verdict") for k, v in out["pairs"].items()}), json.dumps({k: v.get("verdict") for k, v in out["kit_lec"].items()}),
      json.dumps({k: (v["result"], v["mismatches"]) for k, v in out["miter"].items()}))
