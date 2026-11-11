#!/usr/bin/env python3
"""Kit-level edits of a bound reset tree (SERDES-KITWIN-1111 follow-up, DIE-S81-85 for DIE-S81-87, COORD 11-11).

Two opt-in operations on an assembled kit (nothing happens unless one is asked for; with neither the files are untouched):

  plain      the internal reset relays u_rrl_<k> go from ot_dp_rrelay_nl (negedge lockup) to ot_dp_rrelay (plain posedge),
             i.e. the plan event "relay_lockup.types minus the serdes types" (results/die_s81_85_serdes_plainrelay_1109)
             applied to the bound RTL the kit already carries.  Same 1 cycle per hop; the tree's depth map is unchanged.
  station    SITES ONLY (bound_reset_contract.placement semantics): the listed PAD relays move to the midpoint of the
             hop that feeds them, so a hop longer than a station reach becomes two shorter hops.  A pad only delays, so
             the graph, the depth of every tap (reset-release cycle) and every relay ID stay as bound: +0 cycles.  The
             move needs a reviewed PASS record (image + findings), as bound_reset_contract.placement demands.

Both rewrite rtl/bound_reset.json (hashes recomputed) and rtl/reset_tree.tcl through bound_reset_contract.stage, and the kit
root bound_native_reset.json.  usage:
  bound_reset_edit.py KIT [--plain] [--station SRC:DST ...] [--review REVIEW_JSON] [--check]
"""
import argparse, copy, hashlib, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bound_reset_contract as BRC  # noqa: E402
import reset_tree as RT  # noqa: E402

NL, PLAIN = "ot_dp_rrelay_nl", "ot_dp_rrelay"


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def depth_map(tree):
    """{tap output q: number of relays from the root} over the tree's relay graph (root = 'rst_root_n')."""
    drv = {r["q"]: r for r in tree["relays"]}
    out = {}
    for r in tree["relays"]:
        n, cur = 0, r
        while True:
            n += 1
            if cur["d"] == "rst_root_n" or cur["d"] not in drv:
                break
            cur = drv[cur["d"]]
        out[r["q"]] = n
    return out


def hops(nodes, tree):
    xy = {"rst_root_n": tuple(tree["root"])}
    xy.update({r["q"]: tuple(r["xy"]) for r in nodes})
    return {r["name"]: sum(abs(a - b) for a, b in zip(r["xy"], xy[r["d"]])) for r in nodes if r["d"] in xy}


def midpoints(nodes, pairs):
    byname = {r["name"]: r for r in nodes}
    sites = {}
    for src, dst in pairs:
        s, d = byname[src], byname[dst]
        if d["d"] != s["q"]:
            raise SystemExit(f"{dst} is not fed by {src}")
        if d.get("kind") != "pad":
            raise SystemExit(f"{dst} is a {d.get('kind')} relay: only PAD relays may move (the tap relay owns its clock tap)")
        sites[dst] = [round((a + b) / 2, 2) for a, b in zip(s["xy"], d["xy"])]
    return sites


def edit(kit, plain=False, station=(), review=None, write=True):
    kit = Path(kit)
    rtl = kit / "rtl"
    rec = json.loads((rtl / "bound_reset.json").read_text())
    BRC.validate(rec, rec["plan_type"])
    hits = [f for f in sorted(rtl.glob("*.sv")) if re.search(r"\bot_dp_rrelay(?:_nl)?\s+u_rrl_0\s*\(", f.read_text())]
    if len(hits) != 1:
        raise SystemExit(f"the bound RTL (the one instantiating u_rrl_0) is not exactly one rtl/*.sv: {hits}")
    bound = hits[0]
    text = bound.read_text()
    tree = copy.deepcopy(rec["tree"])
    nodes = copy.deepcopy(rec["physical_nodes"])
    sites = copy.deepcopy(rec.get("placement_sites") or {})
    rev = copy.deepcopy(rec.get("placement_review"))
    rep = dict(plain=plain, station=[list(p) for p in station])
    before = depth_map(tree)
    if plain:
        if tree.get("relay_lockup"):
            del tree["relay_lockup"]
        new, n = re.subn(rf"\b{NL}(\s+u_rrl_\d+\s*\()", PLAIN + r"\1", text)
        if re.search(rf"\b{NL}\b", re.sub(rf"module\s+{NL}\b.*?endmodule", "", new, flags=re.S)):
            raise SystemExit(f"{NL} is still instantiated outside u_rrl_<k> after the swap")
        text, rep["relays_to_plain"] = new, n
    if station:
        if not (isinstance(review, dict) and review.get("verdict") == "PASS" and review.get("findings") and review.get("image")
                and Path(review["image"]).is_file()):
            raise SystemExit("station re-sites need a PASS review record with findings and an existing image (bound_reset_contract.placement)")
        new_sites = midpoints(nodes, [tuple(p) for p in station])
        sites.update(new_sites)
        rev = copy.deepcopy(review)
        for r in nodes:
            if r["name"] in new_sites:
                r["xy"] = list(new_sites[r["name"]])
        h = hops(nodes, tree)
        bad = {k: round(v, 1) for k, v in h.items() if v > float(tree["reach_um"]) + 1e-6}
        if bad:
            raise SystemExit(f"hops beyond the reach {tree['reach_um']}: {bad}")
        rep["sites"] = new_sites
        rep["max_hop_um"] = round(max(h.values()), 2)
    after = depth_map(tree)
    if before != after:
        raise SystemExit("reset-release depth of a tap changed")
    rep["depth_map_unchanged"] = True
    rep["taps"] = len(after)
    if not (plain or station):
        return rep
    verified = sorted(set(re.findall(r"\b(ot_dp_r(?:relay_nl|relay))\s+u_r", text)) | {c for c in rec["verified_cell_classes"] if c not in (NL, PLAIN)})
    if plain:
        verified = [c for c in verified if c != NL] or [PLAIN]
    rec2 = copy.deepcopy(rec)
    rec2.update(tree=tree, tree_sha256=BRC.digest(tree), bound_rtl_sha256=_sha(text.encode()))
    contract = dict(native_paths=rec["native_paths"], physical_nodes=nodes, verified_cell_classes=verified,
                    placement_sites=sites, placement_review=rev)
    rep["bound_rtl_sha256"] = rec2["bound_rtl_sha256"]
    if not write:
        return rep
    bound.write_text(text)
    BRC.stage(rtl, rec2, contract)
    nat = kit / "bound_native_reset.json"
    if nat.is_file():
        d = json.loads(nat.read_text())
        d["tree"] = tree
        d["physical_nodes"] = nodes
        d["placement_sites"] = sites
        d["placement_review"] = rev
        d["verified_cell_classes"] = verified
        if isinstance(d.get("source_authority"), dict):
            d["source_authority"].update(tree=tree, tree_sha256=BRC.digest(tree), bound_rtl_sha256=rec2["bound_rtl_sha256"])
        nat.write_text(json.dumps(d, indent=2) + "\n")
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("kit")
    ap.add_argument("--plain", action="store_true")
    ap.add_argument("--station", action="append", default=[], metavar="SRC:DST")
    ap.add_argument("--review")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    st = [tuple(s.split(":")) for s in a.station]
    rv = json.loads(Path(a.review).read_text()) if a.review else None
    print(json.dumps(edit(a.kit, a.plain, st, rv, write=not a.check), indent=1))


if __name__ == "__main__":
    main()
