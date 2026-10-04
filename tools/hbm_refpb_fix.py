#!/usr/bin/env python3
"""HBM controller-model REFpb correctness fix (2026-10-04): before/after of the benches that measure bandwidth on the
behavioural refresh-live model rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv (family A), each run under the independent
JESD238 command checker of rtl/test/ot_hdc_v41x_idx_hbm_trace.sv.

The fix (in the model, default): a REFpb issues no earlier than its due time and tRREFD after the pseudo-channel's last
ACT and last REFpb, after its bank's tRC / tRP and its own previous REFpb's tRFCpb; no ACT falls within tRREFD of a
REFpb (either side); the refresh-aware choice skips a bank still refreshing.  REF_LEGACY = 1 is the old placement.

Two derived controllers (work dir, never committed): the traced copy renamed to ot_hdc_v41x_idx_hbm with a `final`
dram_check per instance -- `fixed` (REF_LEGACY 0, the default) and `legacy` (REF_LEGACY 1).  The trace lines only log
commands, so the cycles are those of the plain model (tools/dsrom_idxkey_layout.py trace proves the copy).

  reader  tools/dsrom_1m_measure.py's reader runs (DS ROM full index scans, results/rtl/dsrom_1m_measured_20261004).
  window  tools/dsrom_hbm_path_audit.py window (DS ROM WINDOW load, 64 refresh phases).
  cand    tools/dsrom_hbm_path_audit.py cand (re-index candidate-key list gather, three layouts).
Usage: PATH=<verilator 5.050>:$PATH python3 tools/hbm_refpb_fix.py {reader,window} --work DIR --out JSON
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
MODEL = "rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv"
TRACE = "rtl/test/ot_hdc_v41x_idx_hbm_trace.sv"
CHK = re.compile(r"DRAMCHK s=\d+ pre=(\d+) ref=(\d+) act=(\d+) rd=(\d+) wr=(\d+) viol=(\d+) rrefd=(\d+) "
                 r"ref_round_bad=(\d+) ref_gap_max_ps=(\d+)")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def derived(work: Path, legacy: bool) -> Path:
    s = (ROOT / TRACE).read_text()
    s = s.replace("module ot_hdc_v41x_idx_hbm_trace #(", "module ot_hdc_v41x_idx_hbm #(", 1)
    if legacy:
        old = "    parameter integer REF_LEGACY = 0,"
        assert s.count(old) == 1
        s = s.replace(old, "    parameter integer REF_LEGACY = 1,")
    i = s.rindex("endmodule")
    s = s[:i] + "    final dram_check(0);\n" + s[i:]
    p = work / ("ctl_legacy" if legacy else "ctl_fixed") / "ot_hdc_v41x_idx_hbm.sv"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s)
    return p


def dram(stdout: str) -> dict:
    rows = [list(map(int, m.groups())) for m in CHK.finditer(stdout)]
    tot = [sum(r[i] for r in rows) for i in range(8)] if rows else [0] * 8
    return dict(instances=len(rows), pre=tot[0], refpb=tot[1], act=tot[2], rd=tot[3], wr=tot[4],
                violations=tot[5], trrefd=tot[6], ref_round_bad=tot[7],
                ref_gap_max_ns=max((r[8] for r in rows), default=0) / 1000,
                first_violations=[l for l in stdout.splitlines() if l.startswith("DRAMCHK_VIOLATION")][:6])


def cmd_reader(a):
    import dsrom_1m_measure as M
    import w11_idx_reader_rate as W
    work = a.work.resolve()
    rec = dict(schema="opentallas.hbm-refpb-fix.reader.v1", source_sha256={p: sha(ROOT / p) for p in
               (MODEL, TRACE, "tools/hbm_refpb_fix.py", "tools/w11_idx_reader_rate.py", "tools/dsrom_1m_measure.py",
                *W.QS_SOURCES[1:], W.QS_CPP)},
               before_record="results/rtl/dsrom_1m_measured_20261004/reader.json", variants={})
    before = {r["name"]: r for r in json.loads((ROOT / rec["before_record"]).read_text())["runs"]}
    for variant in ("legacy", "fixed"):
        ctl = derived(work, variant == "legacy")
        (work / variant).mkdir(parents=True, exist_ok=True)
        W.QS_SOURCES = [str(ctl)] + W.QS_SOURCES[1:]

        def one(r, variant=variant):
            name, n, params = r
            row = W.build_and_run((name, "quarter_stack", n, params, "dsrom_1m"), work / variant)
            out = subprocess.run([str(work / variant / name / "Vtb_w11_idx_quarter_stack")], capture_output=True,
                                 text=True, cwd=ROOT).stdout
            clk = params["CLK_PS"]
            frac = row["sectors"] * 32 / (row["cycles"] * clk * 1e-12) / 1e12 / (4 * 32 * 32 / 1024e-12 / 1e12)
            b = before[name]
            return name, dict(cycles=row["cycles"], sectors=row["sectors"], checked_keys=row["checked_keys"],
                              keys=row["keys"], fraction_of_peak=round(frac, 4),
                              before_cycles=b["cycles"], before_fraction=round(b["fraction_of_peak"], 4),
                              delta_pct=round(100 * (frac / b["fraction_of_peak"] - 1), 3),
                              refreshes=sum(s["refreshes"] for s in row["hbm_per_stack"]), dram_check=dram(out))
        with cf.ThreadPoolExecutor(a.jobs) as ex:
            rec["variants"][variant] = dict(ex.map(one, M.reader_runs()))
        for n, r in rec["variants"][variant].items():
            print(f"{variant:6s} {n:34s} cyc {r['before_cycles']} -> {r['cycles']}  {100 * r['fraction_of_peak']:.2f}% "
                  f"({r['delta_pct']:+.2f}%) viol {r['dram_check']['violations']} refpb {r['dram_check']['refpb']}",
                  flush=True)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")


def cmd_window(a):
    import dsrom_hbm_path_audit as A
    work = a.work.resolve()
    before = json.loads((ROOT / "results/rtl/hbm_path_bandwidth_audit_20261004/dsrom_window_load.json").read_text())
    rec = dict(schema="opentallas.hbm-refpb-fix.window.v1",
               source_sha256={p: sha(ROOT / p) for p in (MODEL, TRACE, "tools/hbm_refpb_fix.py",
                                                         "tools/dsrom_hbm_path_audit.py", *A.WIN_SRC[1:])},
               before_record="results/rtl/hbm_path_bandwidth_audit_20261004/dsrom_window_load.json", variants={})
    phases = [5000 + i * A.TREFI_CYC // 64 + (i * 37) % 11 for i in range(64)]
    for variant in ("legacy", "fixed"):
        ctl = derived(work, variant == "legacy")
        srcs = [str(ctl)] + A.WIN_SRC[1:]
        exe = A.build(work / variant, "tb_dsrom_window_load_bw", srcs, dict(MODE=1), "stream_la")

        def one(t):
            o = subprocess.run([str(exe), f"+t0={t}"], capture_output=True, text=True).stdout
            bw = [l for l in o.splitlines() if l.startswith("BW ")]
            r = A.kv(bw[-1]) if bw else {}
            ver = [l for l in o.splitlines() if l.startswith("VERDICT ")]
            r["verdict"] = ver[-1].split()[1] if ver else "FAIL"
            r["dram_check"] = dram(o)
            return r
        with cf.ThreadPoolExecutor(a.jobs) as ex:
            rows = list(ex.map(one, phases))
        st = A.stats(rows)
        first = A.stats(rows, "first_rsp_cycles")
        nsect = rows[0]["sectors"]
        rec["variants"][variant] = dict(
            exact=all(r["verdict"] == "PASS" and r.get("bad", 1) == 0 and r.get("fault", 1) == 0 for r in rows),
            cycles=st, first_access_cycles=first,
            sustained_after_first_access_frac=round(nsect / (st["median"] - first["median"]) / (32 * A.CLK_PS / 1024), 4),
            frac_peak_median=round(rows[0]["bytes"] / (st["median"] * A.CLK_PS * 1e-12) / 1e12 / A.PEAK_STACK_TBPS, 4),
            us_max=round(st["max"] * A.CLK_PS / 1e6, 4),
            dram_violations=sum(r["dram_check"]["violations"] for r in rows),
            refpb=sum(r["dram_check"]["refpb"] for r in rows),
            first_violations=[v for r in rows for v in r["dram_check"]["first_violations"]][:6],
            per_phase_cycles=[r["cycles"] for r in rows])
    b = before["summary"]["stream_la"]
    rec["before"] = dict(cycles=b["cycles"], first_access_cycles=b["first_access_cycles"],
                         sustained_after_first_access_frac=b["sustained_after_first_access_frac"],
                         frac_peak_median=b["frac_peak_median"], us_max=b["us_max"])
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: {kk: v[kk] for kk in ("exact", "cycles", "sustained_after_first_access_frac", "dram_violations")}
                      for k, v in rec["variants"].items()}, indent=1), json.dumps(rec["before"]))


def cmd_cand(a):
    """tools/dsrom_hbm_path_audit.py cand (re-index candidate-key list gather, ot_dsrom_hbm_list_gather_la) with the
    controller swapped for the derived checked copies; DRAM checker totals added to every run."""
    import dsrom_hbm_path_audit as A
    work = a.work.resolve()
    before = json.loads((ROOT / "results/rtl/hbm_path_bandwidth_audit_20261004/dsrom_reindex_candidate_gather.json")
                        .read_text())

    def run(exe, args):
        o = subprocess.run([str(exe)] + args, capture_output=True, text=True).stdout
        bw = [l for l in o.splitlines() if l.startswith("BW ")]
        ver = [l for l in o.splitlines() if l.startswith("VERDICT ")]
        r = A.kv(bw[-1]) if bw else {}
        r["verdict"] = ver[-1].split()[1] if ver else "FAIL"
        d = dram(o)
        r["dram_violations"], r["refpb"] = d["violations"], d["refpb"]
        r["first_violations"] = d["first_violations"][:2]
        return r
    A.run = run
    rec = dict(schema="opentallas.hbm-refpb-fix.cand.v1",
               source_sha256={p: sha(ROOT / p) for p in (MODEL, TRACE, "tools/hbm_refpb_fix.py",
                                                         "tools/dsrom_hbm_path_audit.py", *A.CAND_SRC[1:])},
               before_record="results/rtl/hbm_path_bandwidth_audit_20261004/dsrom_reindex_candidate_gather.json",
               before={k: v for k, v in before["summary"].items()}, variants={})
    for variant in ("legacy", "fixed"):
        ctl = derived(work, variant == "legacy")
        A.CAND_SRC = [str(ctl)] + A.CAND_SRC[1:]
        sub = argparse.Namespace(work=work / variant, cand=a.cand, jobs=a.jobs, out=work / f"{variant}.json")
        (work / variant).mkdir(parents=True, exist_ok=True)
        A.cmd_cand(sub)
        r = json.loads(sub.out.read_text())
        summ = r["summary"]
        for k in A.LAYOUTS:
            rows = [x for x in r["runs"] if x["layout"] == k]
            summ[k]["dram_violations"] = sum(x["dram_violations"] for x in rows)
            summ[k]["first_violations"] = [v for x in rows for v in x["first_violations"]][:4]
        rec["variants"][variant] = summ
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=("reader", "window", "cand"))
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=7)
    ap.add_argument("--cand", default="/home/ubuntu/w17work/ref/ctx1048576_seed20260930/ctx1048576_cand.npz")
    a = ap.parse_args()
    dict(reader=cmd_reader, window=cmd_window, cand=cmd_cand)[a.cmd](a)


if __name__ == "__main__":
    main()
