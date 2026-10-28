"""CORE-VIEWS-1 check: every plan hard-core instance of a module with an exported view -> die_sta_related.pins_relation
(the gate's own --core-view-match-pins test) + the view's ETM parses at TT and FF (core_view_model)."""
import json, sys, collections
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import schema as S, die_sta_related as DSR
plan_path, views_root = Path(sys.argv[2]), Path(sys.argv[3])
raw = json.loads(plan_path.read_text()); P = S.Plan(raw)
cnt = collections.Counter(p["type"] for p in P.parts.values())
views = {d.name: d for d in views_root.iterdir() if (d / "provenance.json").exists()} if views_root.exists() else {}
out = {}
for m, vd in sorted(views.items()):
    try:
        cm = {c: DSR.core_view_model(m, vd, c, 1.0, 0.0) for c in ("TT", "FF")}
        etm = {c: dict(clk_tree_ps=cm[c]["etm"]["clock_tree_path_ps"], clkq_max=cm[c]["clkq_max"], setup=cm[c]["setup"], hold=cm[c]["hold"]) for c in cm}
        meta = cm["TT"]["meta"]
    except SystemExit as e:
        out[m] = dict(etm_error=str(e)); continue
    rel = collections.Counter(); pf = collections.Counter()
    for tn, t in P.types.items():
        for h in t.get("hard_cores", []) or []:
            if h["module"] != m: continue
            how, why = DSR.pins_relation(meta, h.get("pins_file"), plan_path.parent, h.get("outline_um"))
            rel[how or ("MISMATCH: " + why)] += cnt[tn]; pf[(h.get("pins_file"), how or why)] += cnt[tn]
    out[m] = dict(etm=etm, instances=dict(rel), by_pins_file={f"{a} -> {b}": n for (a, b), n in pf.items()})
print(json.dumps(out, indent=1))
