#!/usr/bin/env python3
"""DS-ROM (DeepSeek-V4.1-Flash, S81) 1M token: two SU-side terms that tools/dsrom_1m_su.py left as arithmetic,
simulated in RTL (owner measurement rule 2026-10-04).

qwired  The quantisers with the plus-hub network stages IN RTL.  tools/dsrom_1m_su.py quant timed one
        ot_hdc_actquant / ot_hdc_fp4qdq instance on each node's golden blocks and ADDED the wired variant's
        BCAST 22 + RET 15 slow cycles arithmetically (su.json wired_us).  Here the same golden block files
        (the quant_work directories that run wrote, sha256 recorded) run on rtl/test/dsrom_sys/
        tb_dsrom_1m_quant_wired.sv: 22 register stages on the issue side and 15 on the return side around the unit,
        first block in -> last block out, every block checked (codes, exponent, QDQ value, fault) against the
        golden.  Also re-runs BCAST 0 / RET 0 on the same bench as a cross-check against quant.json.

    python3 tools/dsrom_1m_su_cdcq.py qwired --su-out DIR --work W        # DIR holds quant.json + quant_work/
    python3 tools/dsrom_1m_su_cdcq.py qrecord --su-out DIR --work W [--record results/.../su_qdq_wired.json]
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

SLOW_HZ = 0.9e9
QTB = ROOT / "rtl/test/dsrom_sys/tb_dsrom_1m_quant_wired.sv"
QRTL = [ROOT / "rtl/hdc/v41/ot_hdc_actquant.sv", ROOT / "rtl/hdc/v41/ot_hdc_fp4qdq.sv"]
REC_DIR = ROOT / "results/rtl/dsrom_1m_allmeasured_20261004"
QSTAGES = {"wired": (22, 15), "unit": (0, 0)}
PAT = re.compile(r"DSQ naq=(\d+) checked=(\d+) errors=(\d+) nq4=(\d+) checked=(\d+) errors=(\d+) "
                 r"first_in=(-?\d+) last_out=(-?\d+)")


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def verilator():
    vl = Path(os.environ.get("OPENTALLAS_TOOLS_ROOT", Path.home() / ".local/opentallas-tools")) / "verilator-5.050/bin/verilator"
    return str(vl) if vl.exists() else "verilator"


def qbuild(work: Path, v: str) -> Path:
    import rtl_hdc_v41_blockdot_campaign as BC
    bc, rt = QSTAGES[v]
    obj = work / f"qobj_{v}"
    exe = obj / "Vtb_dsrom_1m_quant_wired"
    if not exe.exists():
        subprocess.run([verilator(), "--binary", "--timing", "-O2", "-Wno-fatal", "-Wno-WIDTH", "--top-module",
                        "tb_dsrom_1m_quant_wired", f"-GBCAST={bc}", f"-GRET={rt}", "-Mdir", str(obj),
                        *map(str, QRTL), *map(str, BC.LIB), str(QTB)], check=True, capture_output=True)
    return exe


def cmd_qwired(a):
    su = Path(a.su_out)
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    q = json.loads((su / "quant.json").read_text())
    rows = []
    for v in QSTAGES:
        exe = qbuild(work, v)
        for r in q["rows"]:
            d = su / "quant_work" / f"{r['layer']}_{r['node']}"
            arg = f"+NQ4={r['beats']}" if r["kind"] == "q4" else f"+NAQ={r['beats']}"
            files = sorted(p.name for p in d.glob("*.mem"))
            out = subprocess.run([str(exe), arg], cwd=d, capture_output=True, text=True).stdout
            m = PAT.search(out)
            naq, ca, ea, nq4, cb, eb, fi, lo = map(int, m.groups())
            cyc = lo - fi + 1
            rows.append(dict(variant=v, bcast=QSTAGES[v][0], ret=QSTAGES[v][1], layer=r["layer"], node=r["node"],
                             part=r["part"], kind=r["kind"], beats=r["beats"], first_in=fi, last_out=lo, cycles=cyc,
                             us=round(cyc / SLOW_HZ * 1e6, 5),
                             exact=bool("PASS" in out and ea == 0 and eb == 0 and ca + cb == r["beats"]
                                        and r["golden_function_check"]),
                             quant_json_cycles=r["cycles_one_instance"],
                             inputs_sha256={f: sha(d / f) for f in files}))
            print(v, r["layer"], r["node"], cyc, rows[-1]["exact"], flush=True)
    (work / "qwired_runs.json").write_text(json.dumps(dict(generated_utc=now(), rows=rows,
                                                           quant_json_sha256=sha(su / "quant.json")), indent=1) + "\n")
    return 0 if all(r["exact"] for r in rows) else 1


def cmd_qrecord(a):
    su = Path(a.su_out)
    runs = json.loads((Path(a.work) / "qwired_runs.json").read_text())
    by = {}
    for r in runs["rows"]:
        by.setdefault((r["layer"], r["node"]), {})[r["variant"]] = r
    nodes = {}
    for (L, n), v in by.items():
        w, u = v["wired"], v["unit"]
        nodes[f"{L}.{n}"] = dict(part=w["part"], kind=w["kind"], blocks=w["beats"], qdq_wired_cycles=w["cycles"],
                                 qdq_wired_us=w["us"], unit_cycles=u["cycles"], unit_us=u["us"],
                                 unit_equals_quant_json=u["cycles"] == u["quant_json_cycles"],
                                 stages_simulated=w["cycles"] - u["cycles"], clock_hz=SLOW_HZ,
                                 exact=bool(w["exact"] and u["exact"]),
                                 source=f"one {'ot_hdc_fp4qdq' if w['kind'] == 'q4' else 'ot_hdc_actquant'} instance + "
                                        f"22 issue / 15 return register stages in RTL (tb_dsrom_1m_quant_wired), golden "
                                        f"blocks back to back, first in -> last out at 0.9 GHz")
    exact = all(x["exact"] for x in nodes.values())
    rec = dict(schema="opentallas.dsrom-1m.su-qdq-wired.v1", generated_utc=now(), source_commit=a.source_commit,
               exact=exact, clock_hz=SLOW_HZ,
               scope="the DS-ROM SU quantiser nodes (quant.json rows of tools/dsrom_1m_su.py, same golden block files) "
                     "with the plus-hub BCAST 22 / RET 15 network stages simulated as RTL register stages instead of "
                     "added; one instance (as su.json's measured quantiser term)",
               nodes=nodes, quant_json_sha256=runs["quant_json_sha256"],
               rtl_sha256={str(p.relative_to(ROOT)): sha(p) for p in (*QRTL, QTB)},
               tool_sha256={"tools/dsrom_1m_su_cdcq.py": sha(ROOT / "tools/dsrom_1m_su_cdcq.py")})
    Path(a.record).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: (v["unit_cycles"], v["qdq_wired_cycles"], v["exact"]) for k, v in nodes.items()}))
    return 0 if exact else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("qwired", "qrecord"))
    ap.add_argument("--su-out", default=None)
    ap.add_argument("--work", required=True)
    ap.add_argument("--source-commit", default=None)
    ap.add_argument("--record", default=str(REC_DIR / "su_qdq_wired.json"))
    a = ap.parse_args()
    return dict(qwired=cmd_qwired, qrecord=cmd_qrecord)[a.step](a)


if __name__ == "__main__":
    sys.exit(main())
