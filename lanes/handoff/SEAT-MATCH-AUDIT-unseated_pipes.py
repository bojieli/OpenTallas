#!/usr/bin/env python3
"""Count bind-emitted pad / pipe flops (ot_dp_dly / _keep / _cnt instances) of every bound type and how the plan seats them:
EXACT (internal_stations bit_sites_um, kit is_packed_exact_banks), POINT (internal_stations regs_um: every bit of a stage at one point),
RELAY (relay_sites keys naming the instance: counted per key), NONE.  usage: unseated_pipes.py PLAN BIND_RTL_DIR [OUT.tsv]"""
import json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import seat_match as SM

def regs(mod, par):
    w = int(par.get("W", 1))
    if mod == "ot_dp_dly_cnt":
        return w * int(par.get("DMAX", 1))
    if mod == "ot_dp_st":
        return w
    return w * int(par.get("D", 1))

def main(plan, rtl, out=None):
    P = json.loads(Path(plan).read_text())["partition_types"]
    tot, rows = Counter(), []
    for tn, t in sorted(P.items()):
        f = SM._bound_file(rtl, tn)
        if f is None or not isinstance(t, dict):
            continue
        inst = SM.bound_instances(f.read_text(errors="replace"))
        keys = defaultdict(int)
        for k in (t.get("relay_sites") or {}):
            keys[re.sub(r"\[\d+\]", "", re.split(r"[./]", k, maxsplit=1)[0])] += 1
        ist = {}
        for e in t.get("internal_stations") or []:
            c = str(e.get("conn", ""))
            if c.startswith("bus:"):
                ist[c[4:]] = "EXACT" if ("bit_sites_um" in e or "face_bit_sites_um" in e) else "POINT"
        for i, (mod, par) in inst.items():
            if mod not in ("ot_dp_dly", "ot_dp_dly_keep", "ot_dp_dly_cnt"):
                continue
            n = regs(mod, par)
            m = re.match(r"u_lpad_(.+)$", i)
            if m and gen_id(m.group(1)) in {gen_id(b) for b in ist}:
                how = next(v for b, v in ist.items() if gen_id(b) == gen_id(m.group(1)))
                seated = n
            elif keys.get(i):
                how, seated = "RELAY", min(n, keys[i])
            else:
                how, seated = "NONE", 0
            cls = ("lpad" if i.startswith("u_lpad_") else "pipe_u_d" if re.match(r"u_d\d+_", i) else "relay_u_y" if i.startswith("u_y_")
                   else "strap_u_r8b" if i.startswith("u_r8b_") else "pad_u_pd" if re.match(r"u_pd\d+_", i) else "other")
            tot[(cls, how, "flops")] += n
            tot[(cls, how, "unseated")] += n - seated
            rows.append((tn, i, mod, json.dumps(par), n, how, n - seated, cls))
    if out:
        with open(out, "w") as fh:
            fh.write("type\tinst\tmodule\tparams\tflops\tseat\tunseated\tclass\n")
            for r in rows:
                fh.write("\t".join(map(str, r)) + "\n")
    return tot, rows

def gen_id(s):
    return re.sub(r"[^A-Za-z0-9_]", "_", s)

if __name__ == "__main__":
    tot, rows = main(*sys.argv[1:4])
    agg = defaultdict(Counter)
    for (c, h, k), v in tot.items():
        agg[(c, h)][k] += v
    for (c, h), v in sorted(agg.items()):
        print(f"{c}\t{h}\tflops {v['flops']}\tunseated {v['unseated']}")
    un = Counter()
    for r in rows:
        un[r[0]] += r[6]
    print("unseated total", sum(un.values()), "types with unseated", sum(1 for v in un.values() if v), "top", un.most_common(6))
