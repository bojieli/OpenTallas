"""RELAY-ANCHOR (DIE-QC-97 11-10, class RELAY-REMAP): plan references to generated reset relays by SITE, not by index.

reset_tree.py names the wavefront relays of a type rst_rl_<k> by build order.  The plan's START transport and local
resets (clock.landing_reader_start / landing_writer_start stages raw_reset, clock.landing_local_resets raw) name such
relays literally, so any change to a reset-tree input renumbers the tree and silently invalidates those names:
TAPREACH-1 (ac700dd6170) re-binned sle_ctl__cl67434795 (501 -> 513 relays), and a strict bind of the unchanged plan of
record failed with "writer START raw reset rst_rl_228 has no registered wavefront driver"; candidate ft_slots edits
did the same to slw_sc_v1 (rst_rl_97).  Names that still exist after the renumbering point at relays elsewhere.

Plan writers record, per type, clock.reset_tree_anchor = {inputs: {sink_bins, ft_slots, taps: sha256}, tol_um,
relays: {name: {depth, xy}}} for every relay name the plan references (record()).  At bind (resolve()) every
anchored name is checked against the tree the bind builds: a relay of that name at the same depth and site is kept;
otherwise the name is re-picked as the re-pick of RELAY-REMAP-1 (dq97/sctl/remap.py) did by hand: the non-ported
rst_rl relay of the SAME depth nearest (Manhattan) to the recorded site, ties by name.  Every remap is logged with
the input whose sha changed.  No relay within tol_um of the site, or a referenced name the anchor does not carry,
fails closed.  A plan without an anchor, or whose anchored relays all still match, binds byte-identically.
"""
import hashlib
import json
import re
from pathlib import Path

KEY = "reset_tree_anchor"
SECTIONS = ("landing_reader_start", "landing_writer_start", "landing_local_resets")
NAME = re.compile(r"^rst_rl_\d+$")
SITE_EPS_UM = 1e-3


class AnchorError(ValueError):
    pass


def _sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def input_shas(t, root):
    """sha256 of the reset-tree inputs of type dict t that plan events change in place: the sink bins file bytes
    (clock.sink_bins_file, resolved under root as taps.sink_sites reads it), the ft_slots and the clock tap keys."""
    ck = t.get("clock") or {}
    bins = "none"
    if ck.get("sink_bins_file"):
        p = Path(root) / ck["sink_bins_file"]
        bins = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "missing"
    taps = {k: v for k, v in ck.items() if k == "taps" or k.startswith("tap_")}
    return dict(sink_bins=bins, ft_slots=_sha(t.get("ft_slots") or []), taps=_sha(taps))


def refs(t):
    """[(container, key)] of every rst_rl_<k> name the type's START transport / local resets reference.
    landing_contract.collector_tree is excluded: a self-contained tree with its own relay names."""
    out = []

    def walk(o):
        items = o.items() if isinstance(o, dict) else enumerate(o) if isinstance(o, list) else ()
        for k, v in items:
            if isinstance(v, str) and NAME.match(v):
                out.append((o, k))
            else:
                walk(v)
    ck = t.get("clock") or {}
    for sec in SECTIONS:
        walk(ck.get(sec) or {})
    return out


def ported(tree):
    """relay nets that also drive an rst_o port (a port flop must feed only its port: never a re-pick target)"""
    import reset_tree as RT
    txt = "\n".join(RT.rtl_lines(tree))
    return set(re.findall(r"\bassign\s+rst_o_\w+\s*=\s*(\w+)\s*;", txt))


def record(t, tree, root, tol_um):
    """the anchor of type dict t against the reset tree the plan was solved with (plan writers)"""
    by = {r["q"]: r for r in tree["relays"]}
    names = sorted({c[k] for c, k in refs(t)})
    bad = [n for n in names if n not in by]
    if bad:
        raise AnchorError(f"reset_tree_anchor: {len(bad)} referenced relay(s) not in the tree: {bad[:8]}")
    return dict(inputs=input_shas(t, root), tol_um=float(tol_um),
                relays={n: dict(depth=int(by[n]["depth"]), xy=[round(float(v), 3) for v in by[n]["xy"]]) for n in names})


def snapshot(t):
    """the solve-time reset tree a plan publishes with its landing contract (clock.landing_contract.collector_tree,
    the reset_tree.for_type tree the landing names were picked on), or None"""
    ct = ((t.get("clock") or {}).get("landing_contract") or {}).get("collector_tree")
    rel = ct.get("relays") if isinstance(ct, dict) else None
    if not rel or not all(isinstance(r, dict) and {"q", "depth", "xy"} <= set(r) for r in rel):
        return None
    return {"relays": rel}


_BOUND_RELAY = re.compile(r"\bot_dp_rrelay(?:_nl)?\s+\w+\s*\([^;]*?\.q\(\s*(rst_rl_\d+)\s*\)[^;]*\);[ \t]*//[^\n]*?"
                          r"depth\s+(\d+)\s+@\s+\(([-\d.]+),\s*([-\d.]+)\)")


def bound_tree(sv_text):
    """the generated relays of a BOUND type body (bind rtl/<type>.sv, as reset_tree.rtl_lines comments each relay
    'depth D @ (x, y)'): the tree a bind of record actually emitted, sites rounded to 0.1 um"""
    rel = [dict(q=m.group(1), depth=int(m.group(2)), xy=[float(m.group(3)), float(m.group(4))])
           for m in _BOUND_RELAY.finditer(sv_text)]
    return {"relays": rel} if rel else None


def _d(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def resolve(tn, t, tree, root, ported_fn=ported):
    """re-pick the anchored relay names of type dict t onto `tree` (the tree this bind builds); edits t in place only
    when a name moves.  Returns the receipt, or None for a type without an anchor.  Raises AnchorError (fail closed)."""
    ck = t.get("clock") or {}
    anc = ck.get(KEY)
    if not anc:
        return None
    rows = anc.get("relays") or {}
    tol = float(anc.get("tol_um", 0))
    rf = refs(t)
    unanchored = sorted({c[k] for c, k in rf} - set(rows))
    if unanchored:
        raise AnchorError(f"{tn}: reset_tree_anchor lacks referenced relay(s) {unanchored[:8]}: re-record the anchor")
    by = {r["q"]: r for r in tree["relays"]}
    keep = {n for n, a in rows.items()
            if n in by and int(by[n]["depth"]) == int(a["depth"]) and _d(by[n]["xy"], a["xy"]) <= SITE_EPS_UM}
    now = input_shas(t, root)
    changed = sorted(k for k, v in (anc.get("inputs") or {}).items() if now.get(k) != v)
    receipt = dict(type=tn, anchored=len(rows), kept=len(keep), changed_inputs=changed, remaps=[], tol_um=tol)
    if len(keep) == len(rows):
        return receipt
    port = ported_fn(tree)
    cand = {}
    for r in tree["relays"]:
        if NAME.match(r["q"]) and r["q"] not in port:
            cand.setdefault(int(r["depth"]), []).append(r)
    mp, bad = {}, []
    for n in sorted(set(rows) - keep):
        a = rows[n]
        c = cand.get(int(a["depth"]), [])
        b = min(c, key=lambda r: (_d(r["xy"], a["xy"]), r["q"])) if c else None
        d = _d(b["xy"], a["xy"]) if b else None
        if b is None or d > tol:
            bad.append(f"{n} (depth {a['depth']} @ {a['xy']}): " +
                       (f"nearest same-depth relay {b['q']} is {d:.1f} um > tol {tol:g}" if b else "no same-depth relay"))
            continue
        mp[n] = b["q"]
        receipt["remaps"].append(dict(name=n, to=b["q"], depth=int(a["depth"]), was_xy=a["xy"],
                                      xy=[round(float(v), 3) for v in b["xy"]], moved_um=round(d, 3)))
    if bad:
        raise AnchorError(f"{tn}: reset_tree_anchor: {len(bad)} anchored relay(s) have no relay within the recorded "
                          f"site tolerance (inputs changed: {changed or 'none'}): " + "; ".join(bad[:5]))
    receipt["refs_rewritten"] = sum(1 for c, k in rf if c[k] in mp)
    for c, k in rf:
        if c[k] in mp:
            c[k] = mp[c[k]]
    # the in-memory anchor now describes the names the plan references (a second resolve is a no-op)
    ck[KEY] = dict(anc, relays={n: dict(depth=int(by[n]["depth"]), xy=[round(float(v), 3) for v in by[n]["xy"]])
                                for n in sorted({c[k] for c, k in rf})})
    return receipt


def resolve_plan(raw, P, root, tree_fn=None, ported_fn=ported):
    """bind entry: resolve every anchored type of raw (P = schema.Plan over the same dicts).  -> (receipts, errors)"""
    if tree_fn is None:
        if P is None:
            return [], ["RESET_ANCHOR reset_tree_anchor needs reset.release 'wavefront' (generated relay tree)"]
        import reset_tree as RT
        tree_fn = lambda tn: RT.for_type(P, tn)
    receipts, errors = [], []
    for tn, t in raw.get("partition_types", {}).items():
        if not (t.get("clock") or {}).get(KEY):
            continue
        try:
            receipts.append(resolve(tn, t, tree_fn(tn), root, ported_fn))
        except (AnchorError, OSError) as exc:
            errors.append(f"RESET_ANCHOR {exc}")
    return receipts, errors


def main(argv):
    """record: python3 reset_anchor.py record PLAN OUT [--types T1,T2] [--tol-um 405] [--source tree|snapshot|auto]
    Anchors every type with START/local relay references against the tree of the plan as it stands (plan writers run
    it on the plan they solved; a later in-place input change is then re-picked at bind).  --source snapshot / auto
    take the sites from the plan's own solve-time tree (landing_contract.collector_tree) instead, for a plan whose
    names were picked before a later event or generator change renumbered the tree (auto: snapshot when it holds every
    referenced name, else the tree)."""
    import argparse
    import sys
    ap = argparse.ArgumentParser(description=main.__doc__)
    ap.add_argument("cmd", choices=["record"])
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--types", default="")
    ap.add_argument("--tol-um", type=float, default=None, help="default: the reset relay reach (reset_tree.relay_um)")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--solved-bins", action="append", default=[], metavar="TYPE=PATH",
                    help="the sink bins a type's plan was SOLVED with, when the file at its sink_bins_file has since "
                         "been replaced in place (the plan keeps its sink_bins_file; the anchor records that tree)")
    ap.add_argument("--source", choices=["tree", "snapshot", "auto"], default="tree")
    ap.add_argument("--bound-rtl", help="rtl/ of a bind of record: with --bound-plan, a type whose references equal "
                                        "that plan's is anchored where that bind emitted the relays (first choice)")
    ap.add_argument("--bound-plan", help="the plan the --bound-rtl bind bound")
    a = ap.parse_args(argv[1:])
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import schema
    import reset_tree as RT
    raw = json.loads(Path(a.plan).read_text())
    keep = {}
    for sb in a.solved_bins:
        tn, f = sb.split("=", 1)
        ck = raw["partition_types"][tn]["clock"]
        keep[tn] = ck["sink_bins_file"]
        ck["sink_bins_file"] = str(Path(f).resolve())
    P = schema.Plan(raw, Path(a.plan).parent / "die_plan.json")     # as bind.Binder.wavefront_plan (pins_file paths)
    tol = a.tol_um if a.tol_um is not None else RT.relay_um(P)
    want = set(filter(None, a.types.split(",")))
    bplan = json.loads(Path(a.bound_plan).read_text())["partition_types"] if a.bound_plan and a.bound_rtl else {}
    n = 0
    for tn, t in raw["partition_types"].items():
        if (want and tn not in want) or not refs(t):
            continue
        names = {c[k] for c, k in refs(t)}
        has = lambda tr: tr is not None and names <= {r["q"] for r in tr["relays"]}  # noqa: E731
        src, tree = None, None
        if a.source == "auto" and tn in bplan and [c[k] for c, k in refs(bplan[tn])] == [c[k] for c, k in refs(t)]:
            f = Path(a.bound_rtl) / f"{tn}.sv"
            bt = bound_tree(f.read_text()) if f.is_file() else None
            if has(bt):
                src, tree = "bound", bt
        if tree is None and a.source in ("tree", "auto"):
            tt = RT.for_type(P, tn)
            if a.source == "tree" or has(tt):
                src, tree = "tree", tt
        if tree is None:
            snap = snapshot(t)
            if a.source == "snapshot" or has(snap):
                src, tree = "snapshot", snap
        if tree is None:
            raise AnchorError(f"{tn}: no source holds every referenced relay (bound / tree / snapshot)")
        t["clock"][KEY] = record(t, tree, a.root, tol)
        n += 1
        print(f"{tn}: anchored {len(t['clock'][KEY]['relays'])} relay(s) from the {src}, tol {tol:g} um", flush=True)
    for tn, f in keep.items():
        raw["partition_types"][tn]["clock"]["sink_bins_file"] = f
    Path(a.out).write_text(json.dumps(raw, separators=(",", ":")))
    print(f"wrote {a.out} sha256 {hashlib.sha256(Path(a.out).read_bytes()).hexdigest()[:12]} ({n} types)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv))
