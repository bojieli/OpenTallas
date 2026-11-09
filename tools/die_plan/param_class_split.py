#!/usr/bin/env python3
"""param_class_split.py (DIE-QC-97 11-09): one plan type per bound LOGIC parameter value set, so every type kits by
construction with the generic bind.py kit-rtl.

Why: the bind passes per-instance parameters to a type's bound module (bind.py _type_vals: the parameters whose value
differs across the type's instances, e.g. the QC coll_regen HI_PAD latency pads 30/29 per slice on qfd_qc_sle_st_b).
One hardened kit is ONE value set, so kit-rtl stops ('instances of M carry different parameters ...').  A die kit recipe
cannot fix that: instances that differ in a logic parameter are different hardware.  Instances that differ only in ID
parameters (tile_id, sidx, ...: the kit_wave ID_PARAM names) are NOT split here; those are parent_id_straps (OWNER
10-25 B) and stay one type.

What: for every plan type T whose bound instances (bind.bound_instance_params on the bind of record, the exact strings
kit-rtl reads) carry >1 LOGIC value set, T is replaced by one clone per value set, named T__pv<sha256(T+set)[:8]> (the
clock_landing_plan __cl<hash> form; a split copy "<base>__<suffix>" still matches its base wherever a plan rule reads
tn.split("__")[0], e.g. clock.ring_hold.write_fall_types).  Clone = deep copy of T with module = its name,
param_base_type = T, param_set = the logic values it binds, the partitions of that value set retyped.  Every other
exact reference to T is carried over:
  * a dict key T (reset.in_sites, clock.tap_window.per_type_ps, sidecar collector.types) -> one copy per clone (the T
    key stays, as clock_landing_plan leaves it);
  * a list entry T (write_fall_types, asbuilt internal_stations_types, ...) -> the clones are added after it;
  * a string T under a key "type" -> the clone (inside a copied subtree) or the partition's clone (sidecar
    collector.parts.<part>.type); under any key naming a base type (base_type, landing_base_type, param_base_type,
    base_type_by_part) -> kept;
  * any other exact string T fails closed (unknown semantics: the report names its path).
The bound RTL of every instance is unchanged (same leaves, same values); after the rebind each clone has one value set,
so the bind bakes it into the clone's module (no per-instance parameter) and kit-rtl needs no --instance.
Idempotent: on a bind whose types each carry one logic value set it splits nothing (exit 0, splits []).

usage: param_class_split.py PLAN --bind-out BIND_OUT [--out PLAN_OUT] [--sidecar IN --sidecar-out OUT]
                            [--asbuilt IN --asbuilt-out OUT [--sidecar-ref REL]] [--types T,..] [--report R.json]
                            [--check]
  The bind reads asbuilt.clock_landing_table under the asbuilt base and refuses a path outside it: put the split
  sidecar (and the asbuilt copy, whose relative base/map_file/files keep their meaning only next to the original)
  in the source tree beside the originals.
  --check: only report; exit 3 when a split is needed (a pre-kit gate), 0 otherwise."""
import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind as B  # noqa: E402

# = tools/autopilot/kit_wave.ID_PARAM: per-instance ID parameters are parent_id_straps, not a class split
ID_PARAM = re.compile(r"(?:_id|_tid|sidx|map_lane_j)$")
TYPE_KEYS = ("type",)


class SplitError(Exception):
    pass


def parse_params(pset):
    """'#(.A(1), .B({x, y}))' -> {'A': '1', 'B': '{x, y}'} (top-level commas only; balanced parentheses)"""
    s = (pset or "").strip()
    if not s:
        return {}
    if not (s.startswith("#(") and s.endswith(")")):
        raise SplitError(f"not a parameter list: {s[:80]}")
    body, out, depth, cur = s[2:-1], [], 0, ""
    for ch in body:
        if ch in "({[":
            depth += 1
        elif ch in ")}]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    res = {}
    for x in out:
        m = re.match(r"\s*\.(\w+)\s*\((.*)\)\s*$", x, re.S)
        if not m:
            raise SplitError(f"not a named parameter: {x.strip()[:80]}")
        res[m.group(1)] = m.group(2).strip()
    return res


def logic_groups(pinst, id_re=ID_PARAM):
    """{inst: pset} -> (diff names, logic names, {logic key json: dict(insts, values)}); one group = no split"""
    sets = {i: parse_params(s) for i, s in pinst.items()}
    names = sorted({k for v in sets.values() for k in v})
    diff = [k for k in names if len({v.get(k) for v in sets.values()}) > 1]
    logic = [k for k in diff if not id_re.search(k)]
    groups = {}
    for i in sorted(sets):
        vals = {k: sets[i].get(k) for k in logic}
        g = groups.setdefault(json.dumps(vals, sort_keys=True), dict(insts=[], values=vals))
        g["insts"].append(i)
    return diff, logic, groups


def clone_name(tn, key):
    return f"{tn}__pv{hashlib.sha256((tn + key).encode()).hexdigest()[:8]}"


def find_splits(raw, bind_out, only=None):
    """-> (splits [{type, module, logic, id_params, clones: [{name, partitions, values}]}], unsplit rows)"""
    rep = json.loads((Path(bind_out) / "bind_report.json").read_text())
    die = raw["die"]["name"]
    parts = {}
    for p in raw["partitions"]:
        parts.setdefault(p["type"], []).append(p["name"])
    splits, rows = [], []
    for tn in sorted(raw["partition_types"]):
        if only and tn not in only:
            continue
        if tn not in rep.get("types", {}) or tn not in parts:
            rows.append(dict(type=tn, status="not bound / no partition"))
            continue
        bmod = rep["types"][tn]["module"]
        pinst = B.bound_instance_params(bind_out, die, bmod)
        missing = sorted(set(parts[tn]) - set(pinst))
        if missing:
            raise SplitError(f"{tn}: plan partitions {missing[:5]} are not instances of {bmod} in the bound top")
        pinst = {i: s for i, s in pinst.items() if i in parts[tn]}
        diff, logic, groups = logic_groups(pinst)
        idp = [k for k in diff if k not in logic]
        if len(groups) < 2:
            rows.append(dict(type=tn, module=bmod, status="one logic value set", id_params=idp,
                             params=bool(any(pinst.values()))))
            continue
        clones = [dict(name=clone_name(tn, k), partitions=g["insts"], values=g["values"])
                  for k, g in sorted(groups.items(), key=lambda kv: kv[1]["insts"][0])]
        if len({c["name"] for c in clones}) != len(clones) or any(c["name"] in raw["partition_types"] for c in clones):
            raise SplitError(f"{tn}: clone name collision {[c['name'] for c in clones]}")
        splits.append(dict(type=tn, module=bmod, logic=logic, id_params=idp, clones=clones))
    return splits, rows


def _rewrite(x, path, tn, by_part, clone, refs):
    """the references to tn inside x (in place): see the module doc.  clone = the clone a copied subtree belongs to"""
    def base_ctx(p):
        return any(isinstance(k, str) and "base_type" in k for k in p)

    if isinstance(x, dict):
        for k in list(x):
            v = x[k]
            if k == tn and clone is None:
                for c in by_part["__clones__"]:
                    if c in x:
                        raise SplitError(f"{'.'.join(map(str, path))}: key {c} exists")
                    cp = copy.deepcopy(v)
                    x[c] = _rewrite(cp, path + [c], tn, by_part, c, refs)
                refs.append(dict(path=".".join(map(str, path + [k])), action="key copied to the clones"))
            if isinstance(v, str) and v == tn:
                if base_ctx(path + [k]):
                    refs.append(dict(path=".".join(map(str, path + [k])), action="kept (base type)"))
                elif clone is not None and (k in TYPE_KEYS or (k == "module" and len(path) == 2)):
                    x[k] = clone
                    refs.append(dict(path=".".join(map(str, path + [k])), action=f"-> {clone}"))
                elif k in TYPE_KEYS and path and path[-1] in by_part:
                    x[k] = by_part[path[-1]]
                    refs.append(dict(path=".".join(map(str, path + [k])), action=f"-> {by_part[path[-1]]}"))
                else:
                    raise SplitError(f"{'.'.join(map(str, path + [k]))}: names {tn} with unknown semantics")
            elif k != tn or clone is not None:
                _rewrite(v, path + [k], tn, by_part, clone, refs)
    elif isinstance(x, list):
        i = 0
        while i < len(x):
            v = x[i]
            if isinstance(v, str) and v == tn:
                if clone is not None:
                    raise SplitError(f"{'.'.join(map(str, path))}[{i}]: list entry {tn} inside the type itself")
                add = [c for c in by_part["__clones__"] if c not in x]
                x[i + 1:i + 1] = add
                refs.append(dict(path=f"{'.'.join(map(str, path))}[{i}]", action=f"clones added {add}"))
                i += 1 + len(add)
                continue
            _rewrite(v, path + [i], tn, by_part, clone, refs)
            i += 1
    return x


def apply_plan(raw, splits):
    """raw (in place) with every split type replaced by its clones; -> reference log"""
    refs = []
    for s in splits:
        tn = s["type"]
        names = [c["name"] for c in s["clones"]]
        by_part = {p: c["name"] for c in s["clones"] for p in c["partitions"]}
        by_part["__clones__"] = names
        old = raw["partition_types"][tn]
        pts = {}
        for k, v in raw["partition_types"].items():
            if k != tn:
                pts[k] = v
                continue
            for c in s["clones"]:
                t = copy.deepcopy(old)
                t = _rewrite(t, ["partition_types", c["name"]], tn, by_part, c["name"], refs)
                t["module"] = c["name"]
                t["param_base_type"] = tn
                t["param_set"] = dict(c["values"])
                t["note"] = (t.get("note", "") + f";DIE-QC-97 param class from {tn}: "
                             + ", ".join(f"{k2}={v2}" for k2, v2 in sorted(c["values"].items()))).lstrip(";")
                pts[c["name"]] = t
        raw["partition_types"] = pts
        for p in raw["partitions"]:
            if p["type"] == tn:
                p["type"] = by_part[p["name"]]
        for k in list(raw):
            if k in ("partition_types", "partitions"):
                continue
            _rewrite(raw[k], [k], tn, by_part, None, refs)
    return refs


def apply_side(side, splits, label):
    """a sidecar / asbuilt json (in place) with the same reference rules; -> reference log"""
    refs = []
    for s in splits:
        by_part = {p: c["name"] for c in s["clones"] for p in c["partitions"]}
        by_part["__clones__"] = [c["name"] for c in s["clones"]]
        _rewrite(side, [label], s["type"], by_part, None, refs)
    return refs


def _dump_like(obj, text):
    """json text in the style of the input (one-line plan dumps or indent 1 / 2)"""
    orig = json.loads(text)
    for kw in (dict(separators=(", ", ": ")), dict(separators=(",", ":")), dict(indent=1), dict(indent=2)):
        if json.dumps(orig, **kw).rstrip("\n") == text.rstrip("\n"):
            return json.dumps(obj, **kw) + "\n"
    return json.dumps(obj, indent=1) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("--bind-out", required=True)
    ap.add_argument("--out")
    ap.add_argument("--sidecar")
    ap.add_argument("--sidecar-out")
    ap.add_argument("--asbuilt")
    ap.add_argument("--asbuilt-out")
    ap.add_argument("--sidecar-ref", help="clock_landing_table value written to --asbuilt-out (base-relative path of "
                                          "the split sidecar where it will live; default: --sidecar-out under the base)")
    ap.add_argument("--types", help="comma list: only these types")
    ap.add_argument("--report")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    text = Path(a.plan).read_text()
    raw = json.loads(text)
    try:
        splits, rows = find_splits(raw, a.bind_out, set(a.types.split(",")) if a.types else None)
        rep = dict(schema="opentallas.die_plan.param_class_split.v1", plan=str(a.plan),
                   plan_sha256=hashlib.sha256(text.encode()).hexdigest(), bind_out=str(a.bind_out),
                   splits=splits, types=rows)
        if not a.check and splits:
            if not a.out:
                raise SplitError("--out is required when a split is needed")
            rep["plan_refs"] = apply_plan(raw, splits)
            out = _dump_like(raw, text)
            Path(a.out).write_text(out)
            rep["out"], rep["out_sha256"] = a.out, hashlib.sha256(out.encode()).hexdigest()
            for nm, src, dst in (("sidecar", a.sidecar, a.sidecar_out), ("asbuilt", a.asbuilt, a.asbuilt_out)):
                if not src:
                    continue
                st = Path(src).read_text()
                obj = json.loads(st)
                rep[f"{nm}_refs"] = apply_side(obj, splits, nm)
                if nm == "asbuilt" and a.sidecar_out and obj.get("clock_landing_table"):
                    # bind reads clock_landing_table under the asbuilt base; a manifest inside the repository must name
                    # repository-relative paths (bind._gate_manifest_paths), so relative when the sidecar is under it
                    base = (Path(src).resolve().parent / obj.get("base", ".")).resolve()
                    so_p = Path(a.sidecar_out).resolve()
                    if a.sidecar_ref:
                        obj["clock_landing_table"] = a.sidecar_ref
                    else:
                        try:
                            obj["clock_landing_table"] = str(so_p.relative_to(base))
                        except ValueError:
                            obj["clock_landing_table"] = str(so_p)
                    rep["asbuilt_refs"].append(dict(path="asbuilt.clock_landing_table",
                                                    action=f"-> {obj['clock_landing_table']}"))
                if not dst:
                    raise SplitError(f"--{nm}-out is required with --{nm}")
                so = _dump_like(obj, st)
                Path(dst).write_text(so)
                rep[f"{nm}_out"], rep[f"{nm}_out_sha256"] = dst, hashlib.sha256(so.encode()).hexdigest()
    except (SplitError, B.BindError, OSError, KeyError, ValueError) as e:
        print(f"param_class_split: ERROR {e}", file=sys.stderr)
        return 2
    js = json.dumps(rep, indent=1) + "\n"
    if a.report:
        Path(a.report).write_text(js)
    for s in splits:
        print(f"SPLIT {s['type']} ({s['module']}; {', '.join(s['logic'])}): " +
              "; ".join(f"{c['name']} <- {','.join(c['partitions'])}" for c in s["clones"]))
    print(f"param_class_split: {len(splits)} type(s) need a split" + (" (check only)" if a.check else ""))
    return 3 if (a.check and splits) else 0


if __name__ == "__main__":
    sys.exit(main())
