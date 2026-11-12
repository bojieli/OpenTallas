#!/usr/bin/env python3
"""WINDOW-REDERIVE-1112 proof: generate the kit SDC (gen_phys.sdc) of EVERY plan type before and after the stage and
classify every type whose SDC changes:
  intended    = a type the stage wrote (its per_port_ps entry changed): may differ in the tap-window comment, the
                set_clock_latency -source -early lines and the IO shift lines (set_input_delay -max / set_output_delay -min)
  side effect = any other type: only a sender ft output budget (set_output_delay -max) may differ (the receiver's largest
                port window moves the sender's budget); any other changed line is listed in 'bad'
  signed      = flagged when the type is in --signed (must be empty) or in --name-only (informational)
usage: proof_sdc_diff.py PLAN_BEFORE PLAN_AFTER REPORT_JSON OUT_JSON [--signed F] [--name-only F] [--procs 6]"""
import argparse, difflib, json, re, sys, time
from multiprocessing import Pool
from pathlib import Path
here = Path(__file__).resolve()
for up in here.parents:
    if (up / "tools" / "die_plan" / "gen_phys.py").exists():
        sys.path.insert(0, str(up / "tools" / "die_plan")); break
import gen_phys, schema

ap = argparse.ArgumentParser()
ap.add_argument("before"); ap.add_argument("after"); ap.add_argument("report"); ap.add_argument("out")
ap.add_argument("--signed"); ap.add_argument("--name-only"); ap.add_argument("--procs", type=int, default=6)
a = ap.parse_args()
PA, PB = (schema.Plan(json.load(open(f))) for f in (a.before, a.after))
names = sorted(json.load(open(a.before))["partition_types"])
written = set(json.load(open(a.report))["types_written"])
rl = lambda p: {l.split("\t")[0].strip() for l in open(p) if l.strip() and not l.startswith("#")} if p else set()
signed, name_only = rl(a.signed), rl(a.name_only)
ALLOWED = re.compile(r"^(# tap window: |set_clock_latency -source -early -clock |set_input_delay -max |set_output_delay -min )")
SIDE = re.compile(r"^set_output_delay -max ")


def one(t):
    try:
        x = gen_phys.sdc(PA, t, gen_phys.type_pins(PA, t))
        y = gen_phys.sdc(PB, t, gen_phys.type_pins(PB, t))
    except Exception as e:
        return t, "error", f"{type(e).__name__}: {e}"[:160]
    if x == y:
        return t, "same", None
    om = lambda txt: {m.group(2): float(m.group(1)) for l in txt.splitlines()
                      for m in [re.match(r"^set_output_delay -max ([-0-9.]+) -clock vclk (.*)$", l)] if m}
    xa, xb = om(x), om(y)
    omd = {k: [xa.get(k), xb.get(k)] for k in sorted(set(xa) | set(xb)) if xa.get(k) != xb.get(k)}
    ch = [l[1:] for l in difflib.unified_diff(x.splitlines(), y.splitlines(), lineterm="", n=0)
          if l[:1] in "+-" and l[:3] not in ("+++", "---")]
    return t, "diff", (ch, omd)


if __name__ == "__main__":
    t0 = time.time()
    res = dict(n=len(names), identical=0, intended=[], side_effect=[], bad=[], errors=[], signed_changed=[],
               name_only_changed=[], side_effect_lines={})
    with Pool(a.procs) as pool:
        for t, k, v in pool.imap_unordered(one, names, chunksize=2):
            if k == "error":
                res["errors"].append([t, v]); continue
            if k == "same":
                res["identical"] += 1; continue
            v, omd = v
            if omd:
                res.setdefault("outmax_changes", {})[t] = omd
            ok_re = ALLOWED if t in written else SIDE
            (res["intended"] if t in written else res["side_effect"]).append(t)
            if t not in written:
                res["side_effect_lines"][t] = v[:6]
            bad = [l for l in v if not ok_re.match(l)]
            if bad:
                res["bad"].append([t, bad[:3]])
            if t in signed:
                res["signed_changed"].append(t)
            if t in name_only:
                res["name_only_changed"].append(t)
    for k in ("intended", "side_effect", "signed_changed", "name_only_changed"):
        res[k].sort()
    res["unwritten_intended"] = sorted(written - set(res["intended"]))
    res["seconds"] = round(time.time() - t0)
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    print({k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in res.items()})
