"""bind_tool_stamp.py -- BIND-GEN-TOOLSKEW (FLOW-FIX-0400, COORD item 5).

A private bind run with one tree's tools, then generated with a newer rt, fails at gen hours later with "physical collector_tree differs from captured bound
reset identity" (S81 leaf t44, KV hgi_v6).  bind.py stamps the tool sha it ran with and the content hashes of the reset / relay generators into
<bind_out>/bind_tool.json; kit prep runs `check` against the gen rt before any heavy work and refuses a mismatch in those generators at once.

  python3 -I bind_tool_stamp.py stamp --bind-out DIR [--tools ROOT]
  python3 -I bind_tool_stamp.py check --bind-out DIR [--tools ROOT] [--plan PLAN --type T ...]
        exit 0 ok / no stamp (a bind written before the stamp), exit 3 BIND-GEN-TOOLSKEW

SEMANTIC-TOOLSKEW-1122 (COORD 21:0x; S81 svc lo t3, leaf t31, KV pc_v3 / IOPC, S81 slice LP t2 tonight): a hash difference alone no
longer refuses.  With --plan and --type, check re-runs THIS rt's reset solve (reset_tree.for_type, at the cap the tree was bound with,
as gen_phys.install_bound_native_reset does) on the bind's plan for every named type and compares it with the tree the bind consumed
(<bind_out>/rtl/*.reset_tree.json, plan_type = T).  That solve is the ONLY place gen compares a re-derived output with what the
bind consumed ('physical collector_tree differs from captured bound reset identity'); identical for every type -> accept
(BIND-GEN-TOOLSKEW ok semantic ...).  A differing generator the solve does not import is listed in the accept note: gen never
re-derives it against the bind (bind-time emitters whose output the bind captured, or kit-time appliers such as kit_relay_depth
that fail loudly on the bound text themselves and are pre-checked by kit_wave BIND-STALE).  Refused (fail closed), naming the type
and the differing tree fields, when a solved tree differs, a type has no bound reset receipt, or the solve cannot run / raises.
Without --plan/--type the hash rule is unchanged.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

STAMP = "bind_tool.json"
CLASS_LINE = "BIND-GEN-TOOLSKEW"
# the generators that decide the bound reset identity and the relay chains gen_phys re-derives (tools/die_plan/)
GENERATORS = ("reset_tree.py", "bound_reset_contract.py", "cbc_rules.py", "reset_consumers.py", "reset_port_relays.py", "reset_anchor.py", "reset_provider.py",
              "reset_replicate.py", "reset_carriers.py", "reset_leg_plan.py", "kit_reset_contract.py", "kit_relay_depth.py", "relay_depth.py", "relay_branch.py",
              "relay_bay.py", "reach_relay_plan.py", "native_relay_plan.py", "native_relay_apply.py", "local_reset_writeback.py", "bind_leaf_reset.py")


def tools_root(arg=None):
    return Path(arg).resolve() if arg else Path(__file__).resolve().parents[2]


def tools_sha(root):
    """the rt snapshot sha (root = .../rt/<sha>), else OT_TOOLS_SHA, else git HEAD of root, else ''"""
    root = Path(root)
    if root.parent.name == "rt" and len(root.name) >= 12:
        return root.name
    if os.environ.get("OT_TOOLS_SHA"):
        return os.environ["OT_TOOLS_SHA"]
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def generator_hashes(root):
    out = {}
    for n in GENERATORS:
        f = Path(root) / "tools" / "die_plan" / n
        if f.is_file():
            out[n] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out


def stamp(bind_out, root=None):
    root = tools_root(root)
    rec = {"tools_sha": tools_sha(root), "generators": generator_hashes(root)}
    Path(bind_out).mkdir(parents=True, exist_ok=True)
    (Path(bind_out) / STAMP).write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    return rec


def _identity(tree):
    """gen_phys._bound_reset_identity: the tree without what gen adds later (core_resets[].physical_inst)"""
    tree = json.loads(json.dumps(tree))
    for c in (tree or {}).get("core_resets") or []:
        c.pop("physical_inst", None)
    return tree


def receipts(bind_out, types):
    """{type: receipt} of the bind's per-type reset_tree.json receipts for the named types"""
    want, out = set(types), {}
    for f in sorted((Path(bind_out) / "rtl").glob("*.reset_tree.json")):
        try:
            r = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        if r.get("plan_type") in want:
            out[r["plan_type"]] = r
    return out


def tree_diff(a, b):
    """short text of the fields where two reset trees differ"""
    keys = sorted(k for k in set(a or {}) | set(b or {}) if (a or {}).get(k) != (b or {}).get(k))
    out = []
    for k in keys[:8]:
        x, y = (a or {}).get(k), (b or {}).get(k)
        if isinstance(x, list) and isinstance(y, list):
            n = sum(1 for i in range(max(len(x), len(y))) if (x[i] if i < len(x) else None) != (y[i] if i < len(y) else None))
            out.append(f"{k} ({len(x)} vs {len(y)} rows, {n} differ)")
        else:
            out.append(f"{k} ({str(x)[:40]} vs {str(y)[:40]})")
    return ", ".join(out) + (" ..." if len(keys) > 8 else "")


def semantic_replay(bind_out, root, plan, types, diff):
    """SEMANTIC-TOOLSKEW-1122 -> ('', note) when this rt's reset solve reproduces every bound tree, else (refusal reason, '')"""
    import importlib
    for sub in ("autopilot", "die_plan"):             # schema imports tools/autopilot helpers (goal_table)
        tdir = str(Path(root) / "tools" / sub)
        if tdir not in sys.path:
            sys.path.insert(0, tdir)
    recs = receipts(bind_out, types)
    miss = [t for t in types if t not in recs]
    if miss:
        return f"no bound reset receipt (rtl/*.reset_tree.json) for {', '.join(miss[:4])}: cannot replay", ""
    try:
        S = importlib.import_module("schema")
        RT = importlib.import_module("reset_tree")
        BRC = importlib.import_module("bound_reset_contract")
        CBC = importlib.import_module("cbc_rules")
        P = S.Plan(json.loads(Path(plan).read_text()), path=str(plan))
    except Exception as e:                    # fail closed: the generators cannot be re-run
        return f"replay could not start ({type(e).__name__}: {e})", ""
    done = []
    for tn in types:
        rec = recs[tn]
        captured = _identity(rec.get("tree"))
        cap = BRC.reach_cap_um(rec) or BRC.reach_cap_um(rec.get("tree") or {})
        solved, err = None, ""
        for c in ([cap] if cap else list(getattr(BRC, "LEGACY_CAPS", ())) + [None]):
            try:
                with CBC.bound_reset_hop_cap(c):
                    solved = _identity(RT.for_type(P, tn))
                err = ""
            except Exception as e:
                solved, err = None, f"{type(e).__name__}: {e}"
            if solved == captured:
                break
        if err and solved is None:
            return f"type {tn}: this rt's reset solve raised ({err[:200]})", ""
        if solved != captured:
            return f"type {tn}: this rt's reset solve differs from the bound tree: {tree_diff(captured, solved)}", ""
        done.append(tn)
    used = {n for n in GENERATORS if n[:-3] in sys.modules}
    ex, unex = [n for n in diff if n in used], [n for n in diff if n not in used]
    return "", (f"semantic: this rt's reset solve reproduces the bound tree of {', '.join(done)}"
                + (f"; exercised and identical: {', '.join(ex)}" if ex else "")
                + (f"; not re-derived against the bind at gen: {', '.join(unex)}" if unex else ""))


def check(bind_out, root=None, plan=None, types=(), note=None):
    """-> '' (ok, or no stamp / unreadable stamp: a bind written before the stamp is not refused) or the BIND-GEN-TOOLSKEW refusal text.
    With plan + types a hash difference is replayed (SEMANTIC-TOOLSKEW-1122); note (a list) receives the accept line."""
    f = Path(bind_out) / STAMP
    try:
        rec = json.loads(f.read_text())
    except (OSError, ValueError):
        return ""
    root = tools_root(root)
    bsha, gsha = str(rec.get("tools_sha") or ""), tools_sha(root)
    if bsha and gsha and bsha == gsha:
        return ""
    old, now = rec.get("generators") or {}, generator_hashes(root)
    diff = sorted(n for n in set(old) | set(now) if old.get(n) != now.get(n))
    if not diff:
        return ""
    why = ""
    if plan and types:
        why, ok = semantic_replay(bind_out, root, plan, list(types), diff)
        if not why:
            if note is not None:
                note.append(ok)
            return ""
        why = f" Semantic replay refused: {why}."
    return (f"{CLASS_LINE}: bind of record {bind_out} ran with tools {bsha[:12] or '?'}, this gen runs rt {gsha[:12] or '?'}; reset / relay generators differ: {', '.join(diff[:8])}"
            f"{' ...' if len(diff) > 8 else ''}.  Fix: rebind on the gen rt ({gsha[:12] or 'this rt'}); gen would fail hours later with 'differs from captured bound reset identity'" + why)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("stamp", "check"))
    ap.add_argument("--bind-out", required=True)
    ap.add_argument("--tools")
    ap.add_argument("--plan", help="SEMANTIC-TOOLSKEW-1122: the bind's plan (replay the reset solve on it)")
    ap.add_argument("--type", action="append", default=[], help="plan type(s) of the kit (repeatable)")
    a = ap.parse_args(argv)
    if a.cmd == "stamp":
        rec = stamp(a.bind_out, a.tools)
        print(f"bind tool stamp: {rec['tools_sha'][:12] or '?'} ({len(rec['generators'])} generators)")
        return 0
    note = []
    why = check(a.bind_out, a.tools, a.plan, a.type, note)
    if why:
        print(why)
        return 3
    print("BIND-GEN-TOOLSKEW ok" + (" " + note[0] if note else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
