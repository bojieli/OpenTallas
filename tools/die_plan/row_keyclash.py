"""P-ROW-SILENT-OVERWRITE (COMPOSE-KEYCLASH-R1): two rows that are READY alone can still collide when composed, because both write
the same plan key and the later one silently overwrites the earlier (13:56 landing_contract collision: two rows edit one key;
15:50 the STA clk_land_clear row did raw.pop("clk_land_clear") and erased the SU_C clr flag).  The composed gate lists every plan key
written by more than one row and FAILS (KEYCLASH) unless the later row names the earlier one: its ROW-READY field `overrides`
(row_gate.py gate --overrides ID, repeatable) lists the earlier row's id (its --row-id, lane, ledger key or row file name).

A row WRITES a path when the plan before and after it differs there: dict keys (add / del / change), elements of a list of dicts with
a unique name/id/key/inst/conn (per element), any other list or scalar atomically.  Row B clashes with an earlier row A when B writes
A's path, or an ancestor of it (B replaced or popped a subtree holding A's write).  B editing inside a subtree A merely added is
layering, not a clash.  Rows of one group (the specs of one ledger row set) never clash with each other."""
import json

SEP = "/"


def _lkey(lst):
    if not isinstance(lst, list) or not lst or not all(isinstance(e, dict) for e in lst):
        return None
    for k in ("name", "id", "key", "inst", "conn"):
        vals = [e.get(k) for e in lst]
        if all(isinstance(v, (str, int)) for v in vals) and len(set(vals)) == len(vals):
            return k
    return None


def _J(o):
    return json.dumps(o, sort_keys=True)


def writes(old, new, path=(), out=None):
    """-> {path tuple: 'add'|'del'|'set'} for every plan key the step old -> new writes"""
    out = {} if out is None else out
    if _J(old) == _J(new):
        return out
    if isinstance(old, dict) and isinstance(new, dict):
        for k in set(old) | set(new):
            if k not in new:
                out[path + (str(k),)] = "del"
            elif k not in old:
                out[path + (str(k),)] = "add"
            else:
                writes(old[k], new[k], path + (str(k),), out)
        return out
    if isinstance(old, list) and isinstance(new, list):
        k = _lkey(old)
        if k and _lkey(new) == k:
            om, nm = ({e[k]: e for e in x} for x in (old, new))
            for n in set(om) | set(nm):
                sub = path + (f"[{k}={n}]",)
                if n not in nm:
                    out[sub] = "del"
                elif n not in om:
                    out[sub] = "add"
                else:
                    writes(om[n], nm[n], sub, out)
            return out
    out[path or ("",)] = "set"
    return out


def names(meta):
    """the ids a later row can use to name this row"""
    return {str(x) for x in (meta.get("ids") or []) if x}


def check(rows, prior=None):
    """rows: [dict(group, ids, overrides, writes={path: kind})] in apply order; prior: {path string: [[ids], ...]} writers already in
    the current plan (earlier compose rounds).  -> [dict(path, earlier, later, kind)] clashes no `overrides` names"""
    seen = {}      # path -> [(group, ids, written path)]  (the path itself)
    under = {}     # ancestor path -> [(group, ids, written path)]
    for p, lists in (prior or {}).items():
        t = tuple(p.split(SEP))
        for ids in lists:
            seen.setdefault(t, []).append((None, set(ids), t))
            for i in range(len(t)):
                under.setdefault(t[:i], []).append((None, set(ids), t))
    clashes = []
    for r in rows:
        ov = {str(x) for x in (r.get("overrides") or [])}
        ids = names(r)
        for q, kind in sorted(r["writes"].items()):
            for g, eids, p in seen.get(q, []) + under.get(q, []):
                if g is not None and g == r["group"]:
                    continue
                if ov & eids:
                    continue
                clashes.append(dict(path=SEP.join(q), earlier=sorted(eids)[0] if eids else "?", later=sorted(ids)[0] if ids else "?",
                                    kind=kind, earlier_path=SEP.join(p)))
        for q in r["writes"]:
            seen.setdefault(q, []).append((r["group"], ids, q))
            for i in range(len(q)):
                under.setdefault(q[:i], []).append((r["group"], ids, q))
    return clashes


def describe(clashes, limit=5):
    return (f"KEYCLASH {len(clashes)} plan key(s) written by more than one row without `overrides`: "
            + "; ".join(f"{c['path']} ({c['earlier']} then {c['later']} {c['kind']})" for c in clashes[:limit]))
