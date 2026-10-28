"""Markdown PASS/FAIL report."""


def markdown(res):
    L = [f"# clkplan: {res['plan']} -- {res['verdict']}", "", f"model {res['model']}, {res['sec']} s", "",
         "| check | verdict | detail |", "|---|---|---|"]
    L += [f"| {c['check']} | {c['verdict']} | {c['detail']} |" for c in res["checks"]]
    t = res["tree"]
    L += ["", "## Tree", f"{t['levels']} levels, {t['nodes']} nodes ({t['leaves']} leaves), {t['repeaters']} repeaters, "
          f"{t['wire_um']} um wire, {t['sinks']} sinks."]
    for c, v in t["corners"].items():
        L.append(f"- {c}: tree insertion {v['insertion_min_ps']}-{v['insertion_max_ps']} ps; latency incl. macro insertion "
                 f"{v['latency_min_ps']}-{v['latency_max_ps']} ps")
    b = res["budgets"]
    L += ["", "## Latency budget", f"target {b['target_latency_ps']} ps ({b['corner']}); {b['early_taps']} macros need an "
          f"earlier tap (worst {b['worst_early_ps']} ps); total pad {b['pad_total_ps']} ps."]
    cs = res["crossings"]["summary"]
    L += ["", "## Crossings", f"{cs['landed']} landed / {cs['crossings']} listed; {cs['fail']} under {cs['min_margin_ps']} ps."]
    for r in res["crossings"]["rows"][:10]:
        if "error" in r:
            L.append(f"- {r['a']} -> {r['b']}: {r['error']}")
            continue
        L.append(f"- {r['a']} -> {r['b']} ({r['kind']}): worst margin {r['worst_margin_ps']} ps, LCA {r['lca']} "
                 f"(level {r['lca_level']}), unshared TT {r['TT']['unshared_a_ps']}/{r['TT']['unshared_b_ps']} ps")
    L += ["", "## Top-metal tracks"]
    for ln, v in res["tracks"].get("layers", {}).items():
        s = v["supply"]
        L.append(f"- {ln} ({v['dir']}): {s['slots']} slots / {s['period_um']} um, off-window {s['off_window']}; "
                 f"max trunks/bin {v['max_trunks']}, escapes {v['escapes']}, bins over {v['bins_over']}/{v['bins']}")
    return "\n".join(L) + "\n"
