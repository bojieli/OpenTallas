#!/usr/bin/env python3
"""DIE-S81-36 one-block follow-up of the VES W172.8 fix (delta_ves_w1728_1030.py): the wider ve_s template moves the
reset relays of every leaf type that holds a ve_s core, but the landing collector trees (plan
clock.landing_contract.collector_tree and the bind's clock landing table h2_2249/landed_sidecar_h2.json) still held
the pre-VES tree -> strict bind 'EMIT collector rst_rl_113: raw reset parent rst_rl_110 absent'.
For every type whose stored collector relay edges (q, d) differ from reset_tree.for_type on this plan, store the
recomputed tree (as clock_landing_plan does).  Depth / own_depth and the taps used by collector children and local
sources must be unchanged; nothing else in the plan or table changes.
usage (repo root): delta_ves_coll_1030.py PLAN SIDECAR REPORT.json   (rewrites PLAN and SIDECAR in place)"""
import copy
import json
import os
import re
import sys

sys.path.insert(0, os.path.join("tools", "die_plan"))
import reset_tree as RT  # noqa: E402
import schema as S  # noqa: E402


def splice_tree(text, tn, tree):
    """Replace only <type>.clock.landing_contract.collector_tree in place (indent-1 style, 5-space base), so the
    rest of the plan text (compact ft_slots etc.) stays byte-identical."""
    m = re.search(r'^  "' + re.escape(tn) + r'": ', text, re.M)
    assert m, tn
    _, end = json.JSONDecoder().raw_decode(text, m.end())
    i = text.find('"landing_contract": ', m.end(), end)
    i = text.find('"collector_tree": ', i, end)
    assert i > 0, tn
    ls = text.rfind("\n", 0, i) + 1
    ind = text[ls:i]
    assert ind.strip() == "", tn
    v = i + len('"collector_tree": ')
    _, j = json.JSONDecoder().raw_decode(text, v)
    return text[:v] + json.dumps(tree, indent=1).replace("\n", "\n" + ind) + text[j:]


def edges(t):
    return {(r["q"], r["d"]) for r in t["relays"]}


def main():
    pp, sp, rp = sys.argv[1:4]
    text = open(pp).read()
    plan = json.loads(text)
    side = json.loads(open(sp).read())
    PN = S.Plan(S.load(pp), pp)
    ct = side["collector"]["types"]
    expected = copy.deepcopy(plan)
    report = {}
    for tn, ent in ct.items():
        old_t = ent.get("tree")
        if not old_t:
            continue
        lc = expected["partition_types"][tn]["clock"]["landing_contract"]
        assert lc["collector_tree"] == old_t, tn
        T = json.loads(json.dumps(RT.for_type(PN, tn)))
        if edges(T) == edges(old_t):
            continue
        assert T["depth"] == old_t["depth"] and T["own_depth"] == old_t["own_depth"], tn
        used = {int(m.group(1)) for c in lc["collector_children"] for m in [re.search(r"_t(\d+)$", c["node"])] if m}
        used |= {s_["tap"] for s_ in lc["collector_local_sources"] if "tap" in s_}
        for i in used:
            assert T["taps"][i] == old_t["taps"][i], (tn, i)
        lc["collector_tree"] = T
        ent["tree"] = T
        report[tn] = dict(relays=[len(old_t["relays"]), len(T["relays"])], depth=T["depth"],
                          edges_changed=len(edges(old_t) ^ edges(T)), used_taps=sorted(used))
        text = splice_tree(text, tn, T)
    assert json.loads(text) == expected, "unexpected plan edit"
    open(pp, "w").write(text)
    open(sp, "w").write(json.dumps(side, separators=(",", ":")) + "\n")
    json.dump(report, open(rp, "w"), indent=1)
    print(len(report), "types:", " ".join(sorted(report)))


if __name__ == "__main__":
    main()
