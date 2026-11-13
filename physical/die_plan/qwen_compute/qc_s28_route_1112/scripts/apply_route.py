#!/usr/bin/env python3
"""QC-S28-ROUTE 11-12: guarded apply of the route delta on the HF-1c plan (base plan_hf1c_s 55d318eece08).

    apply_route.py build PLAN SPINE_DELTA.json A22_WIN.json DELTA_OUT.json   (make the delta; from-values recorded)
    apply_route.py apply PLAN_IN PLAN_OUT DELTA.json                         (refuses on any from-value mismatch)
    apply_route.py check PLAN DELTA.json                                     (rc 0 when PLAN already carries the delta)

Keys (all NEW, from-value 'absent'):
  partition_types[T].relay_sites                       T = cbx_q10__cl89936551(_h), cbx_q10__cl94a12200(_h)
  partition_types[T].ft_slots[name=a22].in_window_um / in_layers / in_order   (same 4 types)
Guards (unchanged values the delta relies on, checked equal): outline_um, hard_cores origins, the y_o21 internal
station (QC-S28-C, re-based +34.56 on the _h variants), the a22 slot in/out faces + width + stations.
R1/R2: no change (variant (a); see route/R1R2_variants.tsv)."""
import hashlib, json, sys

TYPES = ["cbx_q10__cl89936551", "cbx_q10__cl94a12200", "cbx_q10__cl89936551_h", "cbx_q10__cl94a12200_h"]


def style(b, P):
    for f in (lambda p: json.dumps(p, separators=(",", ":")) + "\n", lambda p: json.dumps(p) + "\n",
              lambda p: json.dumps(p, indent=1) + "\n", lambda p: json.dumps(p, indent=2) + "\n",
              lambda p: json.dumps(p, separators=(",", ":")), lambda p: json.dumps(p)):
        if f(P).encode() == b:
            return f
    raise SystemExit("plan JSON style unknown (refusing to rewrite it)")


def guards(t):
    a22 = next(s for s in t["ft_slots"] if s["name"] == "a22")
    ist = [e for e in t.get("internal_stations", []) if e.get("conn") == "bus:y_o21"]
    return dict(outline_um=t["outline_um"], cores={h["inst"]: h["origin_um"] for h in t["hard_cores"]},
                y_o21=[dict(from_um=e["from_um"], to_um=e["to_um"], regs_um=e["regs_um"]) for e in ist],
                a22={k: a22.get(k) for k in ("in_face", "out_face", "width", "stations", "out_window_um", "layers")})


def a22(t):
    return next(s for s in t["ft_slots"] if s["name"] == "a22")


def build(plan, spine, win, out):
    b = open(plan, "rb").read(); raw = json.loads(b); T = raw["partition_types"]
    sp = json.load(open(spine))["changes"]; w = json.load(open(win))
    d = dict(schema="opentallas.qc_s28_route_delta.v1", lane="QC-S28-ROUTE", base_plan_sha256_12=hashlib.sha256(b).hexdigest()[:12],
             r1r2="variant (a): no lane/port/slot/latency change", changes={})
    for tn in TYPES:
        t = T[tn]
        if t.get("relay_sites"):
            raise SystemExit(f"{tn}: relay_sites already present")
        s = a22(t)
        for k in ("in_window_um", "in_layers", "in_order"):
            if k in s:
                raise SystemExit(f"{tn}: a22.{k} already present")
        d["changes"][tn] = dict(guard=guards(t), relay_sites=sp[tn]["relay_sites"],
                                a22=dict(in_window_um=w[tn]["in_window_um"], in_layers=w[tn]["in_layers"],
                                         in_order=w[tn]["in_order"]))
    open(out, "w").write(json.dumps(d, indent=1) + "\n")
    print("delta", out, {tn: len(c["relay_sites"]) for tn, c in d["changes"].items()})


def apply(pin, pout, delta):
    b = open(pin, "rb").read(); raw = json.loads(b); dump = style(b, raw); T = raw["partition_types"]
    d = json.load(open(delta)); sha = hashlib.sha256(b).hexdigest()
    if sha[:12] != d["base_plan_sha256_12"]:
        print(f"NOTE: base sha {sha[:12]} != delta base {d['base_plan_sha256_12']}; applying on from-value guards")
    bad = []
    for tn, c in d["changes"].items():
        t = T.get(tn)
        if t is None:
            bad.append(f"{tn}: type missing"); continue
        if guards(t) != c["guard"]:
            bad.append(f"{tn}: guard values differ (outline / cores / y_o21 station / a22 slot)")
        if t.get("relay_sites"):
            bad.append(f"{tn}: relay_sites present (from-value must be absent)")
        for k in c["a22"]:
            if k in a22(t):
                bad.append(f"{tn}: a22.{k} present (from-value must be absent)")
    if bad:
        raise SystemExit("REFUSED:\n  " + "\n  ".join(bad))
    for tn, c in d["changes"].items():
        T[tn]["relay_sites"] = dict(c["relay_sites"])
        a22(T[tn]).update(c["a22"])
    open(pout, "w").write(dump(raw))
    print("applied", pout, hashlib.sha256(open(pout, "rb").read()).hexdigest()[:12])


def check(plan, delta):
    raw = json.load(open(plan)); T = raw["partition_types"]; d = json.load(open(delta)); bad = []
    for tn, c in d["changes"].items():
        if T[tn].get("relay_sites") != c["relay_sites"]:
            bad.append(f"{tn}: relay_sites differ")
        if any(a22(T[tn]).get(k) != v for k, v in c["a22"].items()):
            bad.append(f"{tn}: a22 in window differs")
        if guards(T[tn]) != c["guard"]:
            bad.append(f"{tn}: guard values differ")
    print("CHECK", "OK" if not bad else bad)
    return 0 if not bad else 1


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "build":
        build(*a[1:5])
    elif a[0] == "apply":
        apply(*a[1:4])
    elif a[0] == "check":
        sys.exit(check(*a[1:3]))
    else:
        raise SystemExit(__doc__)
