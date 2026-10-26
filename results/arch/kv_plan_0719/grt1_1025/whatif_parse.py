#!/usr/bin/env python3
"""PATH-KV-GRT1 10-25: collect the die-GRT model what-ifs (die_trial kit of DIE-FT it5, plan e6326d34, unchanged
plan; only the model differs) -> whatif_die_grt.json.
  base      = DIE-FT it5 as run: planned head cores OBS M4/M5 (die_trial.core_obs), M4-M7 adjustment 0.75
  strict75  = head cores OBS through M7 (as g2.probe_blockages / sigmax M7 harden), adjustment 0.75
  strict65  = strict cores, adjustment 0.65 (35 % of M4-M7 left for die feedthroughs)
  strict50  = strict cores, adjustment 0.50 (= g2.py part-probe own-logic model, --adjust 0.5)
usage: whatif_parse.py ROOT(base kit dir parent) WHATIF_ROOT OUT.json"""
import json, re, sys
from collections import Counter
from pathlib import Path

ROW = re.compile(r"^(M\d+|Total)\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)")


def parse(d):
    log = (d / "grt/grt.log").read_text(errors="replace")
    tab, cur = [], None
    for ln in log.splitlines():
        m = ROW.match(ln.strip())
        if m:
            if cur is None:
                cur = {}
                tab.append(cur)
            cur[m.group(1)] = dict(usage_pct=float(m.group(4)), overflow=int(m.group(7)))
        elif cur is not None and ln.strip() and not ln.strip().startswith("-"):
            cur = None
    last = tab[-1] if tab else {}
    wl = re.findall(r"Total wirelength: (\d+)", log)
    el = re.findall(r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): (\S+)", log)
    rpt = d / "grt/congestion.rpt"
    hot = Counter()
    if rpt.exists():
        for ln in rpt.read_text(errors="replace").splitlines():
            if ln.strip().startswith("srcs:"):
                for n in re.findall(r"net:ft_([A-Za-z]+_[A-Z]+)_\d+__", ln):
                    hot[n] += 1
    return dict(overflow={k: v["overflow"] for k, v in last.items() if v["overflow"] or k == "Total"},
                usage_pct=last.get("Total", {}).get("usage_pct"), wirelength_um=int(wl[-1]) if wl else None,
                grt_0113_0114=len(re.findall(r"GRT-011[34]", log)), elapsed=el[-1] if el else None,
                congestion_src_columns=dict(hot.most_common(8)), exit_ok="EXIT 0" in log)


def main():
    base, wi, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    res = dict(schema="opentallas.kv_die_grt_model_whatif.v1", plan_sha256_8="e6326d34",
               kit="DIE-FT it5 epyc1:/srv/opentallas-scratch2/claude/die-ft-1830/qwen_kvsys/kit (die_trial, main 20b4554a0f)",
               note=__doc__.split("\n")[1:7], runs={"base": parse(base)})
    for v in ("strict75", "strict65", "strict50"):
        if (wi / v / "grt/grt.log").exists():
            res["runs"][v] = parse(wi / v)
    out.write_text(json.dumps(res, indent=1) + "\n")
    for k, v in res["runs"].items():
        print(k, v["overflow"], v["usage_pct"], v["grt_0113_0114"], v["elapsed"], v["congestion_src_columns"])


if __name__ == "__main__":
    main()
