#!/usr/bin/env python3
"""Slack sweep: add a fixed number of edges to every record of one or more DS classes of a measured-law JSON,
re-run the census schedule (info_banklat_all) and report the DS AR + Qwen schedule totals.  The smallest delta that
moves the DS total bounds the critical-path slack of that class.
    sweep_slack.py BASE.json OUTDIR CLASS[+CLASS2] DELTA[+DELTA2][,DELTA...] [--bw B --bridge 1]
e.g. HC.HC_MIX+FUSED.QDQ_FP8 0+0,495+47 = base and the two approved costs together."""
import json, subprocess, sys, os
from pathlib import Path
base, out, cls, deltas = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4].split(",")
classes = cls.split("+")
extra = sys.argv[5:]
out.mkdir(parents=True, exist_ok=True)
m0 = json.loads(base.read_text())
res = {}
for dl in deltas:
    m = json.loads(json.dumps(m0))
    for c, d in zip(classes, [int(x) for x in dl.split("+")], strict=True):
        for e in m["designs"]["ds_ar"][c]["shapes"].values():
            if e.get("cycles") is not None:
                e["cycles"] += d
    f = out / f"{cls}_{dl}.json"
    f.write_text(json.dumps(m))
    o = out / f"{cls}_{dl}_census.json"
    subprocess.run([sys.executable, "-m", "hgi_sim.toksim_hbm_census_1019", "--measured", str(f), "--out", str(o)] + extra,
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=dict(os.environ, PYTHONPATH="tools"))
    j = json.loads((out / f"{cls}_{dl}_census_jobs/info_banklat_all__AR.json").read_text())
    q = json.loads((out / f"{cls}_{dl}_census_jobs/info_banklat_all__qwen.json").read_text())
    res[dl] = dict(ds_schedule_total=j["schedule_total"], qwen_schedule_total=q["schedule_total"],
                   crit={c: [j["classes"][c]["crit_n"], j["classes"][c]["crit_cycles"], j["classes"][c]["used_sum"]] for c in classes})
    print(cls, dl, res[dl], flush=True)
(out / f"sweep_{cls}{'_' + '_'.join(extra).replace('-', '') if extra else ''}.json").write_text(json.dumps(res, indent=1) + "\n")
