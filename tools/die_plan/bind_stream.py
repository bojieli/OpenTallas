"""BIND-STREAM-LAUNCH 11-24 (COORD): per-type native topology records while a strict die bind runs.

A strict die bind takes hours (S81 c8: 403 types, 5+ h) and writes OUT/native_topology.json and OUT/bind_report.json only
at its very end, so no kit could start (kit_topology KIT_TOPOLOGY_BIND_STALE; kit-rtl FileNotFoundError bind_report.json)
until the last type was emitted.  Here the bind streams:

    start   (bind start)  OUT/native_topology.d/ is cleared; _context.json = this run's id, plan sha256, as-built sha256 and the
                          FULL native topology receipt (the exact dict write_bind_receipt writes at the end; native_contract of
                          the input plan, computed before any type is emitted)
    type    (each type)   OUT/native_topology.d/<type>.json, written the moment that type's emit and its per-type RTL passes end
                          with NO gap of its own: final=true, run id, context sha256, module, instances, the type's RTL files
                          (sha256 each) and its bind.f (lib + extra_lib + bind_cells.sv + the type's files)
    finish  (bind end)    a type named by any bind error is withdrawn (final=false + the errors); bind_report.json /
                          native_topology.json then take over as before

Readers (kit_topology.bind_matches, bind.py kit-rtl, kit_wave PROBE_BIND) use a record only while the bind has not ended
(no bind_report.json newer than _context.json) and only when: the record is final, of this run and context, every listed
RTL file still has its recorded sha256, and (kit_topology) the context plan the kit names has the bind's plan sha256.  The
per-type checks are the existing ones: kit_topology compares the same receipt fields (transport, types[tn], reset /
selected reset scope, as-built sha256).  A record never replaces a finished bind: once bind_report.json is written, the
finished bind decides (a failing bind refuses kit-rtl exactly as before)."""
import hashlib
import json
import os
import re
import time
import uuid
from pathlib import Path

SCHEMA_CTX = "opentallas.native_topology_stream_context.v1"
SCHEMA_TYPE = "opentallas.native_topology_stream.v1"
DIR = "native_topology.d"
CTX = "_context.json"


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write(path, doc):
    path = Path(path)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    os.replace(tmp, path)


def _fname(tn):
    if not re.fullmatch(r"[A-Za-z0-9_.\-]+", tn) or tn.startswith("."):
        raise ValueError(f"bind stream: type name not a safe file name: {tn!r}")
    return f"{tn}.json"


def start(out, receipt, plan_path, asbuilt=None):
    """bind start: clear OUT/native_topology.d (tool-owned, only regular files this module wrote) and write _context.json -> ctx.
    receipt = kit_topology.bind_receipt(...): the exact dict the bind end writes to native_topology.json."""
    d = Path(out) / DIR
    d.mkdir(parents=True, exist_ok=True)
    for e in os.scandir(d):
        if e.is_file(follow_symlinks=False) and e.name.endswith((".json", ".tmp")):
            os.unlink(e.path)
    ctx = dict(schema=SCHEMA_CTX, run_id=f"{time.strftime('%Y%m%dT%H%M%S')}-{os.getpid()}-{uuid.uuid4().hex[:12]}",
               plan=str(Path(plan_path).resolve()), plan_sha256=_sha(plan_path),
               asbuilt=str(Path(asbuilt).resolve()) if asbuilt else None, receipt=dict(receipt))
    _write(d / CTX, ctx)
    return dict(dir=str(d), run_id=ctx["run_id"], context_sha256=_sha(d / CTX), plan_sha256=ctx["plan_sha256"])


def write_type(ctx, tn, module, instances, files, lib, extra_lib, cells, instance_params=None):
    """one type emitted with no gap of its own -> OUT/native_topology.d/<tn>.json (final)"""
    if not ctx:
        return None
    files = [str(f) for f in files]
    side = []
    for f in files:                       # bound_reset_contract.emitted writes <module>.reset_tree.json next to the bound file
        s = Path(f).with_suffix(".reset_tree.json")
        if s.is_file():
            side.append(str(s))
    rec = dict(schema=SCHEMA_TYPE, type=tn, final=True, run_id=ctx["run_id"], context_sha256=ctx["context_sha256"],
               plan_sha256=ctx["plan_sha256"], module=module, instances=instances,
               files={f: _sha(f) for f in files + side + [str(cells)] if Path(f).is_file()},
               bind_f=[str(x) for x in lib] + [str(x) for x in extra_lib] + [str(cells)] + files,
               extra_lib=[str(x) for x in extra_lib], instance_params=instance_params, written=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    _write(Path(ctx["dir"]) / _fname(tn), rec)
    return rec


def finish(ctx, errors, refused=None):
    """bind end: withdraw every streamed type an error names (identifier match on the type or its split base) or that the
    error attribution refused (bind.attribute_errors) -> [withdrawn]"""
    if not ctx:
        return []
    refused = set(refused or ())
    d = Path(ctx["dir"])
    toks = {}
    for e in errors or []:
        for t in set(re.findall(r"[A-Za-z0-9_]+", str(e))):
            toks.setdefault(t, []).append(str(e)[:300])
    out = []
    for e in sorted(os.scandir(d), key=lambda x: x.name):
        if e.name == CTX or not e.name.endswith(".json"):
            continue
        rec = json.loads(Path(e.path).read_text())
        tn = rec.get("type", "")
        hit = toks.get(tn) or toks.get(tn.split("__")[0]) or (["attributed by the bind error attribution"] if tn in refused else None)
        if hit and rec.get("final"):
            rec.update(final=False, withdrawn=hit[:5], n_withdrawing_errors=len(hit))
            _write(e.path, rec)
            out.append(tn)
    return out


def _live(out):
    """-> (context, context sha) while this OUT's bind has not ended, else None"""
    out = Path(out)
    c = out / DIR / CTX
    if not c.is_file():
        return None
    rep = out / "bind_report.json"
    if rep.is_file() and rep.stat().st_mtime >= c.stat().st_mtime:
        return None                       # the bind ended: bind_report.json / native_topology.json decide
    try:
        return json.loads(c.read_text()), _sha(c)
    except (OSError, ValueError):
        return None


def _context(out):
    """-> (context, context sha) of the last bind run of this OUT (ended or not), else None"""
    c = Path(out) / DIR / CTX
    try:
        return json.loads(c.read_text()), _sha(c)
    except (OSError, ValueError):
        return None


def records(out, tn, why=None, require_live=True):
    """final, intact records of type tn (key tn, else its split variants tn__*) of the live run -> [record] ([] = none usable).
    require_live=False: of the last run even after it ended (the instance parameters of a scoped bind without a die top)."""
    live = _live(out) if require_live else _context(out)
    if live is None:
        if why is not None:
            why.append("no live stream (no native_topology.d/_context.json, or the bind ended)")
        return []
    ctx, csha = live
    d = Path(out) / DIR
    names = [_fname(tn)] if (d / _fname(tn)).is_file() else sorted(
        e.name for e in os.scandir(d) if e.name.startswith(tn + "__") and e.name.endswith(".json"))
    recs = []
    for n in names:
        try:
            r = json.loads((d / n).read_text())
        except (OSError, ValueError):
            if why is not None:
                why.append(f"{n}: unreadable")
            return []
        bad = (not r.get("final") and "not final") or (r.get("run_id") != ctx.get("run_id") and "other run") or \
              (r.get("context_sha256") != csha and "other context")
        if not bad:
            for f, s in (r.get("files") or {}).items():
                if not Path(f).is_file() or _sha(f) != s:
                    bad = f"file changed {f}"
                    break
        if bad:
            if why is not None:
                why.append(f"{n}: {bad}")
            return []
        recs.append(r)
    if not recs and why is not None:
        why.append(f"type {tn} not emitted yet")
    return recs


def receipt(out, tn, plan_path=None, why=None):
    """the full native topology receipt for type tn while the bind runs (kit_topology.bind_matches), or None"""
    recs = records(out, tn, why)
    if not recs:
        return None
    ctx = _live(out)[0]
    if plan_path is not None:
        try:
            psha = _sha(plan_path)
        except OSError:
            psha = None
        if psha != ctx.get("plan_sha256"):
            if why is not None:
                why.append(f"plan sha256 {str(psha)[:12]} != bind plan {ctx.get('plan_sha256', '')[:12]}")
            return None
    return ctx.get("receipt")


def report(out, key):
    """kit-rtl view of one streamed type (the bind_report.json fields kit-rtl reads), or None"""
    recs = records(out, key)
    if not recs:
        return None
    return dict(schema=SCHEMA_TYPE, stream=True, n_errors=0, errors=[],
                types={r["type"]: dict(module=r["module"], instances=r.get("instances")) for r in recs},
                extra_lib=recs[0].get("extra_lib", []), bind_f=recs[0].get("bind_f", []),
                stream_records={r["type"]: dict(run_id=r["run_id"], context_sha256=r["context_sha256"],
                                                plan_sha256=r["plan_sha256"]) for r in recs})


def instance_params(out, key, module, why=None):
    """{instance: '#(...)' or ''} of the bound module from the final records of type key (this OUT's last run, also after it
    ended), or None.  The scoped / probe-only bind and the running bind have no die top; bound_instance_params reads the top."""
    recs = records(out, key, why, require_live=False)
    res = {}
    for r in recs:
        if r.get("module") != module:
            continue
        if not isinstance(r.get("instance_params"), dict):
            if why is not None:
                why.append(f"{r.get('type')}: record has no instance parameters (older bind tool)")
            return None
        res.update(r["instance_params"])
    if not res and why is not None and recs:
        why.append(f"no record of module {module}")
    return res or None


def newer_than_context(out):
    """mtime of the live stream context (sidecars older than it belong to an earlier bind of this OUT), or None"""
    c = Path(out) / DIR / CTX
    return c.stat().st_mtime if _live(out) is not None else None


def launch_check(bind_out, tn, plan, asbuilt=None):
    """BIND-STREAM-LAUNCH wave gate (kit_wave option bind_stream_launch) -> (rc, line).  A finished bind: its bind_report.json must
    report 0 errors (unchanged).  A running bind: type tn needs its own final, intact record of this run AND
    kit_topology.bind_matches on the item plan / as-built (the exact check the kit_topology stage makes later)."""
    out = Path(bind_out)
    if _live(out) is None:
        try:
            e = json.loads((out / "bind_report.json").read_text()).get("errors")
        except (OSError, ValueError) as exc:
            return 3, f"BIND unreadable: {type(exc).__name__} (no bind_report.json and no live stream)"
        n = len(e) if isinstance(e, list) else e
        if n:
            import sys as _sys
            _sys.path.insert(0, str(Path(__file__).resolve().parent))
            import kit_topology
            ok, why = kit_topology.receipt_type_clean(out, tn, tn.split("__")[0] if tn.split("__")[0] != tn else tn)
            if ok:
                return 0, f"BIND errors {n}, TYPE_RECEIPT: {why}"
        return (0 if n == 0 else 3), f"BIND errors {n}"
    why = []
    if not records(out, tn, why):
        return 3, f"BIND_STREAM {tn}: no usable record ({'; '.join(why)[:300]})"
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent))
    import kit_topology
    raw = json.loads(Path(plan).read_text())
    base = tn if tn in raw.get("partition_types", {}) else tn.split("__")[0]
    if base not in raw.get("partition_types", {}):
        return 3, f"BIND_STREAM {tn}: type not in plan {plan}"
    if not kit_topology.bind_matches(raw, base, out, asbuilt, plan):
        why = []
        receipt(out, base, plan, why)
        return 3, f"BIND_STREAM {tn}: KIT_TOPOLOGY_BIND_STALE vs plan {plan} ({'; '.join(why)[:200] or 'receipt fields differ'})"
    return 0, f"BIND_STREAM {tn}: final record of the running bind, kit_topology match (BIND errors 0 for this type)"


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="bind_stream check --bind-out B --type T --plan P [--asbuilt A]")
    ap.add_argument("cmd", choices=["check"])
    ap.add_argument("--bind-out", required=True)
    ap.add_argument("--type", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--asbuilt")
    a = ap.parse_args(argv)
    rc, line = launch_check(a.bind_out, a.type, a.plan, a.asbuilt)
    print(line)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
