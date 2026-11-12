#!/usr/bin/env python3
"""QC-S28-E (DIE-QC-99, 11-12) re-appliable delta: glue clock -> QC density-tap form (+ the sidecar collector entry).

  python3 -I apply_s28e.py apply PLAN_IN PLAN_OUT DELTA [--sidecar SIDE_IN SIDE_OUT]
  python3 -I apply_s28e.py make  BASE NEW DELTA --sidecar SIDE_BASE SIDE_NEW --bins REL      (author side)

Keys touched: partition_types.glue (whole object; only its clock.* and reset.* differ, see delta 'changed') and the
sidecar collector.types.glue entry.  Every replacement is guarded by the sha256 of the canonical JSON of the BASE
object: if another lane changed glue, apply refuses (fail closed).  Nothing else in the plan is read or written, so it
re-applies onto plans that carry the other s28 deltas (A..D do not touch glue).  The bins file
(clock.sink_bins_file) is a separate file that must exist in the kit tree; its sha is checked when --repo is given."""
import hashlib, json, sys
from pathlib import Path


def csha(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _diffkeys(a, b, p=""):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if a.get(k) != b.get(k):
                out += _diffkeys(a.get(k), b.get(k), f"{p}.{k}" if p else k) if p.count(".") < 2 else [f"{p}.{k}"]
        return out
    return [p]


def make(base, new, delta, sb, sn, bins):
    B, N = json.load(open(base)), json.load(open(new))
    for k in B:
        if k != "partition_types" and B[k] != N[k]:
            raise SystemExit(f"top-level {k} differs: not a glue-only delta")
    ch = [t for t in B["partition_types"] if B["partition_types"][t] != N["partition_types"].get(t)]
    if ch != ["glue"]:
        raise SystemExit(f"types changed {ch}")
    SB, SN = json.load(open(sb)), json.load(open(sn))
    gb, gn = SB["collector"]["types"].get("glue"), SN["collector"]["types"].get("glue")
    d = dict(event="QC-S28-E glue density taps", base_plan_sha256=hashlib.sha256(open(base, "rb").read()).hexdigest(),
             new_plan_sha256=hashlib.sha256(open(new, "rb").read()).hexdigest(),
             glue_base_csha=csha(B["partition_types"]["glue"]), glue_new=N["partition_types"]["glue"],
             changed=_diffkeys(B["partition_types"]["glue"], N["partition_types"]["glue"], "glue"),
             sidecar_glue_base_csha=csha(gb), sidecar_glue_new=gn,
             bins=dict(path=bins, sha256=hashlib.sha256(open(bins, "rb").read()).hexdigest()))
    Path(delta).write_text(json.dumps(d, separators=(",", ":")) + "\n")
    print("delta", delta, "changed", d["changed"])


def apply(pin, pout, delta, side=None, repo=None):
    D = json.load(open(delta))
    text = open(pin).read()
    P = json.loads(text)
    if csha(P["partition_types"]["glue"]) == csha(D["glue_new"]):
        print("plan: glue already in the s28e form")
    elif csha(P["partition_types"]["glue"]) != D["glue_base_csha"]:
        raise SystemExit("plan: partition_types.glue differs from the s28e base (another delta touched glue)")
    P["partition_types"]["glue"] = D["glue_new"]
    Path(pout).write_text(json.dumps(P, indent=1 if text.startswith("{\n") else None) + "\n")
    print("plan ->", pout, hashlib.sha256(open(pout, "rb").read()).hexdigest()[:12])
    if side:
        st = open(side[0]).read()
        S = json.loads(st)
        cur = S["collector"]["types"].get("glue")
        if csha(cur) not in (D["sidecar_glue_base_csha"], csha(D["sidecar_glue_new"])):
            raise SystemExit("sidecar: collector.types.glue differs from the s28e base")
        S["collector"]["types"]["glue"] = D["sidecar_glue_new"]
        Path(side[1]).write_text(json.dumps(S, indent=1 if st.startswith("{\n") else None) + "\n")
        print("sidecar ->", side[1], hashlib.sha256(open(side[1], "rb").read()).hexdigest()[:12])
    if repo:
        f = Path(repo) / D["bins"]["path"]
        if hashlib.sha256(f.read_bytes()).hexdigest() != D["bins"]["sha256"]:
            raise SystemExit(f"bins {f}: sha mismatch / missing")
        print("bins ok", f)


if __name__ == "__main__":
    a = sys.argv[1:]
    def opt(n, k=1):
        return a[a.index(n) + 1:a.index(n) + 1 + k] if n in a else None
    if a and a[0] == "make":
        s = opt("--sidecar", 2)
        make(a[1], a[2], a[3], s[0], s[1], opt("--bins")[0])
    elif a and a[0] == "apply":
        r = opt("--repo")
        apply(a[1], a[2], a[3], opt("--sidecar", 2), r[0] if r else None)
    else:
        raise SystemExit(__doc__)
