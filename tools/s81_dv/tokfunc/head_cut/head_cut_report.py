#!/usr/bin/env python3
"""RTLGAP2-HEADTB: collect run_head_cut.sh cases -> OUT/result.json (schema opentallas.tokfunc_s81.head_cut_run.v1)."""
import argparse
import json
import os
import re


def peak_gb(p):
    if not os.path.exists(p):
        return None
    m = re.search(r"Maximum resident set size \(kbytes\): (\d+)", open(p).read())
    return round(int(m.group(1)) / 1e6, 2) if m else None


def verdict(p, pat):
    if not os.path.exists(p):
        return None, None
    t = open(p).read()
    m = re.search(pat, t, re.M)
    return (m.group(1) if m else "NO_RESULT"), (m.group(0) if m else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--img", required=True)
    ap.add_argument("--bind", required=True)
    a = ap.parse_args()
    o = a.out
    g = json.load(open(os.path.join(a.img, "golden.json")))
    res = dict(schema="opentallas.tokfunc_s81.head_cut_run.v1",
               grade="RTL-functional CUT (per-tile full RTL x 253 + whole bound die RTL with replayed bundle faces)",
               bind=a.bind, golden=dict(local=g["local"], peers=g["peers"], token=g["token"]), cases={},
               build_peak_rss_gb={n: peak_gb(os.path.join(o, f"build_{n}.time")) for n in ("a", "b", "b_mut_slice")},
               run_peak_rss_gb={"b": peak_gb(os.path.join(o, "b.time"))})
    if os.path.exists(os.path.join(o, "a.json")):
        aj = json.load(open(os.path.join(o, "a.json")))
        res["cases"]["a"] = dict(verdict="PASS" if aj["pass_"] == aj["tiles"] == 253 else "FAIL", expect="PASS",
                                 tiles=aj["tiles"], tiles_pass=aj["pass_"], bundle_lat=aj["lats"],
                                 failing=[k for k, v in aj["tiles_detail"].items() if not v["ok"]][:20])
    for n in os.listdir(os.path.join(o, "a_mut")) if os.path.isdir(os.path.join(o, "a_mut")) else []:
        v, ln = verdict(os.path.join(o, "a_mut", n, "run.log"), r"^(PASS|FAIL) tilecut.*$")
        res["cases"]["a_mut"] = dict(verdict=v, line=ln, expect="FAIL", what=f"tile {n} reads u_t_N00Wo0's ROM images")
    for n in ("b", "b_mut_rec", "b_mut_slice"):
        p = os.path.join(o, n + ".log")
        v, ln = verdict(p, r"^(PASS|FAIL) head_die.*$")
        if v is None:
            continue
        t = open(p).read()
        cyc = {}
        for m in re.finditer(r"^CYC (.*)$", t, re.M):
            for k, val in re.findall(r"(\S+) (-?\d+)", m.group(1)):
                cyc[k] = int(val)
        c = dict(verdict=v, line=ln, expect="PASS" if n == "b" else "FAIL", cycles=cyc,
                 face_ok=len(re.findall(r"^FACE_XOK ", t, re.M)), face_fail=len(re.findall(r"^FACE_FAIL ", t, re.M)))
        if n == "b" and v == "PASS" and (c["face_ok"] != 253 or c["face_fail"] != 0):
            c["verdict"] = "FAIL"
            c["why"] = f"bundle input faces ok {c['face_ok']}/253, fail {c['face_fail']}"
        res["cases"][n] = c
    res["ok"] = bool(res["cases"]) and all(c["verdict"] == c["expect"] for c in res["cases"].values()) \
        and all(k in res["cases"] for k in ("a", "b"))
    json.dump(res, open(os.path.join(o, "result.json"), "w"), indent=1)
    print("HEAD_CUT", "PASS" if res["ok"] else "FAIL", {k: v["verdict"] for k, v in res["cases"].items()},
          "build GB", res["build_peak_rss_gb"])


if __name__ == "__main__":
    main()
