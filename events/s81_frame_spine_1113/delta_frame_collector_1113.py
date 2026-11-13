#!/usr/bin/env python3
"""FRAME-SPINE-1113 chain stage (FRAME-FORMS-1-VOL): after the frame re-pack (compose_frame_spine.py + finalize.py) the
reset tree of every re-packed type that publishes a landing collector_tree is solved again from the new core layout and
published to the plan landing contract AND to each landed sidecar (collector sources / children re-pick their nearest
tap: plan_event_1104.publish_tree, the xfin / XS4-CORE event form, delta_xs4_collector_1113.py).

    python3 events/s81_frame_spine_1113/delta_frame_collector_1113.py PLAN_IN PLAN_OUT TYPES_FILE REPORT.json \
        SIDE_IN SIDE_OUT [SIDE_IN SIDE_OUT ...]                                         (cwd = repo root)

Report per type: reset depth, relay count, tap count and the GUARD_KEYS of added_tap_recentre.py that changed."""
import gzip
import json
import sys
from pathlib import Path

sys.path[:0] = ["physical/die_plan/s81", "tools/die_plan"]
import schema as S  # noqa: E402
import reset_tree as RT  # noqa: E402
from plan_event_1104 import plan_text, publish_tree  # noqa: E402

GUARD_KEYS = ("root", "entry", "sync_stages", "depth", "own_depth", "tap_depth", "taps", "n_clock_taps",
              "n_reset_consumers", "local_reset_taps", "outs", "core_resets")


def rd(f):
    return json.loads(gzip.decompress(Path(f).read_bytes()) if f.endswith(".gz") else Path(f).read_text())


def norm(o):
    return json.loads(json.dumps(o, sort_keys=True))


def main():
    src, out, tfile, rfile = sys.argv[1:5]
    sides = list(zip(sys.argv[5::2], sys.argv[6::2]))
    types = set(Path(tfile).read_text().split())
    P = rd(src)
    SD = [rd(s) for s, _ in sides]
    Pn = S.Plan(S.load(src), src)
    report = {}
    for tn in sorted(types):
        t = P["partition_types"][tn]
        lc = t["clock"].get("landing_contract") or {}
        if not lc.get("collector_tree"):
            continue
        old = lc["collector_tree"]
        tree = norm(RT.for_type(Pn, tn))
        rep = report[tn] = dict(reset_depth=[old.get("depth"), tree.get("depth")],
                                relays=[len(old.get("relays") or []), len(tree.get("relays") or [])],
                                taps=[len(old.get("taps") or []) if isinstance(old.get("taps"), list) else old.get("taps"),
                                      len(tree.get("taps") or []) if isinstance(tree.get("taps"), list) else tree.get("taps")],
                                guard_changed=[k for k in GUARD_KEYS if norm(old.get(k)) != tree.get(k)],
                                sidecars=[])
        publish_tree(lc, {}, tree, rep)
        for i, T in enumerate(SD):
            st = T["collector"]["types"].get(tn)
            if st is None:
                rep["sidecars"].append(None)
                continue
            same = norm(st.get("tree")) == norm(old) if st.get("tree") else None
            publish_tree({}, st, tree, rep)
            rep["sidecars"].append(dict(had_tree=bool(st.get("tree")), tree_equalled_plan_before=same))
    for (s, o), T in zip(sides, SD):
        txt = json.dumps(T, separators=(",", ":"))
        Path(o).write_bytes(gzip.compress(txt.encode())) if o.endswith(".gz") else Path(o).write_text(txt)
    Path(out).write_text(plan_text(P))
    Path(rfile).write_text(json.dumps(report, indent=1))
    print("types republished", len(report), "guard changed in", sum(bool(r["guard_changed"]) for r in report.values()))
    for tn, r in sorted(report.items()):
        print(tn, json.dumps({k: v for k, v in r.items() if k != "sidecars"}), r["sidecars"])


if __name__ == "__main__":
    main()
