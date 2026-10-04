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

xing    The SU crossings.  su.json charges every SU node with a fast-domain input the model's W18 ratio-FIFO latency
        (4 slow cycles, uarch_model.CDC_W18) and the model charges a fast node fed by an SU node 5 fast cycles; neither
        had a bench.  Under the adopted ROM-die clocking (option C, results/uarch/rom_die_clocking_decision_20261003.md
        "DS RTL": entry/exit meso FIFOs on the field broadcast and return trees, the ratio CDC inside the hub region)
        an SU operand from a field / streamed producer crosses the closed mesochronous FIFO (ot_meso_fifo W512 D4,
        closed main 1fd9484ce) into the hub region and then the closed 3:4 ratio FIFO (ot_ratio_cdc_fifo W512 D4,
        results/rtl/two_clock_crossing_20261003 f2s_w512_d4) into the 0.9 GHz domain; a result goes back the reverse
        way.  rtl/test/su_xing (three clocks from one PLL + the region's static mesochronous phase) simulates both
        chains together, sweeping the slow divider phase (0..3 VCO ticks) and the region phase (0..T), with sparse
        single words (latency accept -> take) and 160-word bursts (a 5,120-FP32 operand in 512-bit words), every word
        bit-exact and in order.  The worst latency over all phases is the per-crossing term.

    python3 tools/dsrom_1m_su_cdcq.py qwired --su-out DIR --work W        # DIR holds quant.json + quant_work/
    python3 tools/dsrom_1m_su_cdcq.py qrecord --work W [--record results/.../su_qdq_wired.json]
    python3 tools/dsrom_1m_su_cdcq.py xing --work W [--jobs 16]           # builds rtl/test/su_xing, sweeps phases
    python3 tools/dsrom_1m_su_cdcq.py xrecord --work W [--record results/.../su_cdc.json]
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


XRE = re.compile(r"(\w+)=([-\d./]+)")
XRTL = ["rtl/common/ot_meso_fifo.sv", "rtl/common/ot_ratio_cdc_fifo.sv", "rtl/test/su_xing/tb_su_xing_top.sv",
        "rtl/test/su_xing/tb_su_xing.cpp", "rtl/test/su_xing/build_tb.sh"]
RPH = 16


def cmd_xing(a):
    from concurrent.futures import ThreadPoolExecutor
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, VERILATOR=verilator())
    exe = subprocess.run([str(ROOT / "rtl/test/su_xing/build_tb.sh"), str(work / "xobj")], env=env, check=True,
                         capture_output=True, text=True).stdout.strip()
    T = 1e12 / 1.2e9
    jobs = [(sph, round(k * T / RPH, 3), 1 + sph * RPH + k) for sph in range(4) for k in range(RPH)]

    def one(j):
        sph, rph, seed = j
        r = subprocess.run([exe, f"+sph={sph}", f"+rph={rph}", f"+seed={seed}", "+sparse=2000", "+burst=160"],
                           capture_output=True, text=True)
        line = next((x for x in r.stdout.splitlines() if x.startswith("RESULT")), r.stdout[-400:])
        kv = dict(XRE.findall(line))
        return dict(sph=sph, rph_ps=rph, seed=seed, returncode=r.returncode, verdict="PASS" if line.endswith("PASS") else "FAIL",
                    **{k: v for k, v in kv.items() if k not in ("sph", "rph")})
    with ThreadPoolExecutor(a.jobs) as ex:
        rows = list(ex.map(one, jobs))
    (work / "xing_runs.json").write_text(json.dumps(dict(generated_utc=now(), rows=rows,
                                                         rtl_sha256={p: sha(ROOT / p) for p in XRTL}), indent=1) + "\n")
    print(sum(r["verdict"] == "PASS" for r in rows), "of", len(rows), "PASS")
    return 0 if all(r["verdict"] == "PASS" for r in rows) else 1


def cmd_xrecord(a):
    runs = json.loads((Path(a.work) / "xing_runs.json").read_text())
    rows = runs["rows"]
    T, TS = 1e12 / 1.2e9, 1e12 / 0.9e9

    def stat(key, i):
        return [float(r[key].split("/")[i]) for r in rows]
    out = {}
    for p, dst in (("f2s", TS), ("s2f", T)):
        mx, mn = max(stat(f"{p}_sparse_ps", 2)), min(stat(f"{p}_sparse_ps", 0))
        mean = sum(stat(f"{p}_sparse_ps", 1)) / len(rows)
        bf = max(float(r[f"{p}_burst_first_ps"]) for r in rows)
        rate = min(float(r[f"{p}_burst_words_per_ns"]) for r in rows)
        out[p] = dict(latency_ps_min=round(mn, 1), latency_ps_mean=round(mean, 1), latency_ps_max=round(mx, 1),
                      latency_dst_cycles_max=round(mx / dst, 3), burst_first_word_ps_max=round(bf, 1),
                      burst_sink_words_per_ns_min=rate, us=round(max(mx, bf) * 1e-6, 6),
                      charged="worst over 64 phases of max(sparse word latency, burst first-word latency)")
    model = dict(f2s_us=round(4 / 0.9e9 * 1e6, 6), s2f_us=round(5 / 1.2e9 * 1e6, 6),
                 src="tools/uarch_model.py CDC_W18 (W18 ratio FIFO: fast->slow 4 slow cycles, slow->fast 5 fast cycles)")
    ok = all(r["verdict"] == "PASS" and r["returncode"] == 0 for r in rows)
    rec = dict(schema="opentallas.dsrom-1m.su-cdc.v1", generated_utc=now(), source_commit=a.source_commit, applies=True,
               exact=ok,
               verdict_note=("ot_meso_fifo is a same-frequency FIFO, so it cannot alone carry the 1.2 GHz <-> 0.9 GHz SU "
                             "crossing; under the adopted clocking (option C, DS RTL item 4) the SU's operand crossing is "
                             "the meso FIFO at the field-region -> hub-region boundary followed by the closed 3:4 ratio "
                             "FIFO inside the hub region, and a result the reverse.  Both FIFOs are simulated in series "
                             "in the actual positions (three clocks of one PLL + the region's static phase)."),
               crossing=dict(rtl=["rtl/common/ot_meso_fifo.sv W512 D4 OFFSET2 (closed main 1fd9484ce)",
                                  "rtl/common/ot_ratio_cdc_fifo.sv W512 D4 (closed results/rtl/two_clock_crossing_20261003/"
                                  "physical/f2s_w512_d4)"], **out),
               model=model, phases=dict(slow_divider_ticks=[0, 1, 2, 3], region_phase_points=RPH, runs=len(rows)),
               composition_rule=("every dependency edge of the S81 graph between a 0.9 GHz node (kinds vector / reduce / "
                                 "sinkhorn) and a 1.2 GHz node pays one crossing: f2s on the slow consumer, s2f on the "
                                 "fast consumer (the edges uarch_model charges CDC_W18 on); hop edges excluded as the "
                                 "model does"),
               runs=rows, rtl_sha256=runs["rtl_sha256"],
               tool_sha256={"tools/dsrom_1m_su_cdcq.py": sha(ROOT / "tools/dsrom_1m_su_cdcq.py")})
    Path(a.record).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(ok=ok, **{k: {kk: v[kk] for kk in ("latency_ps_min", "latency_ps_max", "us")} for k, v in out.items()})))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("qwired", "qrecord", "xing", "xrecord"))
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--su-out", default=None)
    ap.add_argument("--work", required=True)
    ap.add_argument("--source-commit", default=None)
    ap.add_argument("--record", default=None)
    a = ap.parse_args()
    if a.record is None:
        a.record = str(REC_DIR / ("su_cdc.json" if a.step.startswith("x") else "su_qdq_wired.json"))
    return dict(qwired=cmd_qwired, qrecord=cmd_qrecord, xing=cmd_xing, xrecord=cmd_xrecord)[a.step](a)


if __name__ == "__main__":
    sys.exit(main())
