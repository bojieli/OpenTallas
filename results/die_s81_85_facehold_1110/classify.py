#!/usr/bin/env python3
"""FACEHOLD-S81 census classifier (read-only): census.tsv (census_tail.tcl) -> per-endpoint face class.
classes (worst violating path per endpoint; register-launched violators hidden behind a worse port path are added):
  IN_FACE   start = non-clock top input port (in_min -40 receiver contract)         -> parent (NEEDS_PARENT)
  OUT_FACE  end   = top output port (out_min 0 sender contract)                       -> parent (NEEDS_PARENT) / face latch
  CORE      register (or other) start, register end: in-type hold, blocks port_only_hold (local sign-off)
sub-class by instance names: in-face first station u_ft_*_o_0, out-face last station, ft hop, landing ring u_cland_,
reset relay u_rrl_, async (removal) checks.  usage: classify.py CENSUS.tsv [--ck-ports p ...] [--json OUT]"""
import collections
import json
import re
import sys


def sub(start, end, sk, ek):
    if ek == "port":
        m = re.match(r"(?:u_bound\.)?u_ft_(\w+?)_(\d+)/", start)
        port = re.sub(r"\[\d+\]$", "", end)
        return ("last_station->" + port) if m else (start.split("/")[0] + "->out_port")
    if sk == "port":
        m = re.match(r"(?:u_bound\.)?u_ft_(\w+?)_(\d+)/", end)
        if m:
            return f"in_port->station{m.group(2)}"
        return "in_port->" + re.sub(r"\[\d+\].*$", "", end.split("/")[0])
    a = re.match(r"(?:u_bound\.)?u_ft_(\w+?)_(\d+)/", start)
    b = re.match(r"(?:u_bound\.)?u_ft_(\w+?)_(\d+)/", end)
    if a and b:
        return "ft_hop" if a.group(1) == b.group(1) else "ft_cross_slot"
    if "u_rrl_" in start:
        return "reset_relay->" + ("station" if b else end.split("/")[0])
    if "u_cland" in start or "u_cland" in end:
        return "landing_ring"
    return "other"


def main(argv):
    path = argv[0]
    ck = set(argv[argv.index("--ck-ports") + 1:]) if "--ck-ports" in argv else set()
    rows = [l.rstrip("\n").split("\t") for l in open(path)][1:]
    ep = {}
    for r in rows:
        st, sl, s, sk, sc, e, ek, ec = r[:8]
        sl = float(sl)
        if sk == "port" and s.split("[")[0] in ck:
            sk = "clockport"
        key = e
        if ek == "port":
            cls = "OUT_FACE"
        elif sk == "port":
            cls = "IN_FACE"
        else:
            cls = "CORE"
        old = ep.get(key)
        # a register-launched violator hidden behind a worse port path makes the endpoint CORE (signoff 'reg' count)
        if old is None or (st == "reg" and cls == "CORE" and old["cls"] != "CORE") or (cls == old["cls"] and sl < old["slack"]):
            if old is not None and st == "reg" and cls == "CORE" and old["cls"] == "IN_FACE":
                rec = dict(cls="CORE", slack=sl, start=s, end=e, sub=sub(s, e, sk, ek), hidden_behind_port=old["slack"],
                           sc=sc, ec=ec)
            else:
                rec = dict(cls=cls, slack=sl, start=s, end=e, sub=sub(s, e, sk, ek), sc=sc, ec=ec)
            ep[key] = rec
    by = collections.defaultdict(list)
    for e, r in ep.items():
        by[(r["cls"], r["sub"])].append(r)
    out = dict(census=path, endpoints=len(ep), classes={})
    for (c, s), v in sorted(by.items(), key=lambda kv: (kv[0][0], min(x["slack"] for x in kv[1]))):
        w = min(v, key=lambda x: x["slack"])
        out["classes"].setdefault(c, {})[s] = dict(n=len(v), wns=w["slack"], worst_start=w["start"], worst_end=w["end"],
                                                   clocks=f"{w['sc']}->{w['ec']}")
    for c in ("IN_FACE", "OUT_FACE", "CORE"):
        v = [r for r in ep.values() if r["cls"] == c]
        out.setdefault("totals", {})[c] = dict(n=len(v), wns=min((x["slack"] for x in v), default=None))
    out["core_endpoints"] = sorted(([r["slack"], r["start"], r["end"], r["sub"]] for r in ep.values() if r["cls"] == "CORE"))[:40]
    if "--json" in argv:
        open(argv[argv.index("--json") + 1], "w").write(json.dumps(out, indent=1) + "\n")
    print(json.dumps(dict(totals=out["totals"], classes=out["classes"]), indent=1))
    print("CORE endpoints:")
    for x in out["core_endpoints"][:20]:
        print("  ", x)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
