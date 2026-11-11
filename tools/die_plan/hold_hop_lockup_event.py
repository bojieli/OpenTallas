#!/usr/bin/env python3
"""TYPE-SAFE-2 11-08 Fix A (OWNER 11-08 (A) hold-safe hops), any die: put a type's zero-logic cross-tap hops on the
existing opt-in hold-safe forms, 0 pin cycles:
  clock.ft_hop_lockup.types   (gen_rtl.ft_hop_lockup: transparent-low ot_dp_lk latch between FT stations j -> j+1)
  reset.relay_lockup.types    (form "latch", RLK-1108: hop lockup latch on internal reset relay hops)
Generalises DIE-HBM-92 FTLK-1108 v2 (delta_ftlk_1108.py, negedge relay form only) to the RLK latch form.
Fails closed when the plan uses ft_hop_lockup all/except, or when the plan's relay_lockup form differs from the
requested one (no silent form collision).  Only these two lists change (sorted, unique); every other key and every
type block is asserted byte-identical.
--relay-plain T ... takes T OFF reset.relay_lockup.types: its internal relays are the default posedge ot_dp_rrelay again
(DIE-S81-85 serdes 11-09: same-edge hops, the die hold flow pads the short ones).  Fails closed when T is not listed.
usage: hold_hop_lockup_event.py PLAN OUT RECEIPT [--ft-types T ...] [--relay-types T ...] [--relay-form latch]
       [--relay-plain T ...]"""
import argparse
import copy
import hashlib
import json
import sys


def sha(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True).encode()).hexdigest()


def apply(plan, ft_types, relay_types, relay_form="latch", relay_plain=()):
    out = copy.deepcopy(plan)
    if set(relay_types) & set(relay_plain):
        raise ValueError(f"types both added and removed: {sorted(set(relay_types) & set(relay_plain))}")
    miss = [t for t in set(ft_types) | set(relay_types) | set(relay_plain) if t not in out["partition_types"]]
    if miss:
        raise ValueError(f"types not in plan: {sorted(miss)}")
    if ft_types:
        lk = dict(out["clock"].get("ft_hop_lockup") or {})
        if lk.get("all") or lk.get("except"):
            raise ValueError("plan uses ft_hop_lockup all/except; edit it explicitly")
        lk["types"] = sorted(set(lk.get("types", [])) | set(ft_types))
        out["clock"]["ft_hop_lockup"] = lk
    if relay_types:
        out.setdefault("reset", {})
        rl = dict(out["reset"].get("relay_lockup") or {"form": relay_form, "types": []})
        if rl.get("form") != relay_form:
            raise ValueError(f"plan relay_lockup form {rl.get('form')!r} != requested {relay_form!r}")
        rl["types"] = sorted(set(rl.get("types", [])) | set(relay_types))
        out["reset"]["relay_lockup"] = rl
    if relay_plain:
        rl = dict(out.get("reset", {}).get("relay_lockup") or {})
        off = sorted(set(relay_plain) - set(rl.get("types", [])))
        if off:
            raise ValueError(f"types not on reset.relay_lockup.types: {off}")
        rl["types"] = sorted(set(rl["types"]) - set(relay_plain))
        out["reset"]["relay_lockup"] = rl
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("receipt")
    ap.add_argument("--ft-types", nargs="*", default=[])
    ap.add_argument("--relay-types", nargs="*", default=[])
    ap.add_argument("--relay-form", default="latch")
    ap.add_argument("--relay-plain", nargs="*", default=[])
    a = ap.parse_args(argv)
    raw_b = open(a.plan, "rb").read()
    raw = json.loads(raw_b)
    new = apply(raw, a.ft_types, a.relay_types, a.relay_form, a.relay_plain)
    for k in raw:
        if k in ("clock", "reset"):
            ok = {x: v for x, v in raw[k].items() if x not in ("ft_hop_lockup", "relay_lockup")} == \
                 {x: v for x, v in new[k].items() if x not in ("ft_hop_lockup", "relay_lockup")}
        else:
            ok = sha(raw[k]) == sha(new[k])
        if not ok:
            raise AssertionError(f"key {k} changed beyond the two lockup lists")
    data = (json.dumps(new, indent=1) + "\n").encode()
    open(a.out, "wb").write(data)
    rec = dict(event="TS2-FIXA-HOLD-HOP", tool="tools/die_plan/hold_hop_lockup_event.py",
               plan_in=a.plan, plan_in_sha256=hashlib.sha256(raw_b).hexdigest(),
               plan_out=a.out, plan_out_sha256=hashlib.sha256(data).hexdigest(),
               ft_types_added=sorted(set(a.ft_types)), relay_types_added=sorted(set(a.relay_types)),
               relay_types_plain=sorted(set(a.relay_plain)),
               ft_hop_lockup=new["clock"].get("ft_hop_lockup"), relay_lockup=new.get("reset", {}).get("relay_lockup"),
               type_blocks_unchanged=True, pin_cycles_added=0)
    json.dump(rec, open(a.receipt, "w"), indent=1)
    print(json.dumps({k: rec[k] for k in ("ft_types_added", "relay_types_added", "plan_out_sha256")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
