#!/usr/bin/env python3
"""QC-CBGLUE-1116 plan delta: set clock.landing_raw_branches (qc_raw_branches_gen.py output) on the listed types and
assert every other byte of the plan's meaning is unchanged.  Types whose generator output has no branch are left as
they are.  A type that already carries landing_raw_branches is refused unless --replace.
usage: qc_raw_branches_delta.py PLAN_IN RAWBR.json PLAN_OUT [--replace]"""
import argparse
import copy
import json
import re
import sys


def _fmt(x):
    return json.dumps(x, indent=1).replace("\n", "\n  ")


def apply(text, br, replace=False):
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    done = {}
    for tn, r in br.items():
        if not r["branches"]:
            continue
        ck = raw["partition_types"][tn].setdefault("clock", {})
        if "landing_raw_branches" in ck and not replace:
            raise ValueError(f"{tn}: landing_raw_branches already set (use --replace)")
        ck["landing_raw_branches"] = r["branches"]
        done[tn] = r["branches"]
    for tn in raw["partition_types"]:
        x = copy.deepcopy(raw["partition_types"][tn])
        if tn in done:
            x["clock"].pop("landing_raw_branches", None)
            o = copy.deepcopy(orig["partition_types"][tn])
            o.get("clock", {}).pop("landing_raw_branches", None)
            if "clock" not in orig["partition_types"][tn] and x.get("clock") == {}:
                x.pop("clock")
            assert x == o, tn
        else:
            assert x == orig["partition_types"][tn], tn
    assert {k: v for k, v in raw.items() if k != "partition_types"} == \
        {k: v for k, v in orig.items() if k != "partition_types"}
    if json.dumps(orig) == text.rstrip("\n"):           # one-line plan (QC plan_of_record): same serialisation
        text = json.dumps(raw) + text[len(text.rstrip("\n")):]
        assert json.loads(text) == raw
        return text, done
    for tn in done:
        m = re.search(r'^  "' + re.escape(tn) + r'": ', text, re.M)
        if m is None:
            raise ValueError(f"{tn}: partition type not at the plan's 2-space key indent")
        _, j = json.JSONDecoder().raw_decode(text, m.end())
        text = text[:m.end()] + _fmt(raw["partition_types"][tn]) + text[j:]
    assert json.loads(text) == raw
    return text, done


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan_in")
    ap.add_argument("rawbr")
    ap.add_argument("plan_out")
    ap.add_argument("--replace", action="store_true")
    a = ap.parse_args(argv)
    text, done = apply(open(a.plan_in).read(), json.load(open(a.rawbr)), a.replace)
    open(a.plan_out, "w").write(text)
    for tn, b in done.items():
        print(tn, "raw branches", len(b), "copies", sum(len(x["stages"]) for x in b))
    return 0


if __name__ == "__main__":
    sys.exit(main())
