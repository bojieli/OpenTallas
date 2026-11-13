"""Source/delay identity guard for opt-in frozen split-lane references.

Graph records use symbolic cell paths, ports and real transport stage counts.
Numeric cell indices and net IDs are never serialized.  The active RTL resolver
is rerun so an unchanged old file cannot mask a newly selected duplicate master.
"""
import gzip
import hashlib
import json
from pathlib import Path

import bind_elab as E
from split_bind_routes import cell_fingerprint


class SourceGuardError(ValueError):
    pass


SOURCE_RULE_FIELDS = (
    "transport", "reducers", "sources", "clocks", "resets", "straps", "alias", "aliases",
    "substitute", "substitute_inst", "substitute_parent", "defines", "lib_defines",
    "dissolve", "core_splits", "compose", "subtype_bind", "structural_bridges",
    "internal_primitive_constants", "glue_source_names", "prefer", "files", "rtl_roots",
)
_CONFIG_FIELDS = {"core_splits", "compose", "subtype_bind", "structural_bridges"}


def _json(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    except (TypeError, ValueError) as exc:
        raise SourceGuardError(f"noncanonical source-guard record: {exc}") from exc


def _frame(h, value):
    raw = value if isinstance(value, bytes) else _json(value)
    h.update(len(raw).to_bytes(8, "big")); h.update(raw)


def _stage(value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise SourceGuardError(f"invalid source transport stage count {value!r}")
    return value


def symbolic_source(b, source):
    """Canonical RAW Graph.source descriptor, before bound transport is inserted."""
    if not isinstance(source, (tuple, list)) or not source:
        raise SourceGuardError(f"invalid logical source descriptor {source!r}")
    kind = source[0]
    if kind == "pin" and len(source) == 5:
        _, ci, pn, bit, stages = source
        if not isinstance(ci, int) or isinstance(ci, bool) or not 0 <= ci < len(b.F.cells):
            raise SourceGuardError("logical source references an invalid cell")
        c = b.F.cells[ci]
        if pn not in c.ports or not isinstance(bit, int) or isinstance(bit, bool) or not 0 <= bit < len(c.ports[pn]):
            raise SourceGuardError(f"logical source bit out of range: {c.path}.{pn}[{bit}]")
        return [kind, c.path, pn, bit, _stage(stages)]
    if kind in ("or", "and") and len(source) == 3:
        children = [symbolic_source(b, child) for child in source[1]]
        children.sort(key=_json)   # reducer enumeration order is not circuit identity
        return [kind, children, _stage(source[2])]
    if kind == "const" and len(source) >= 2:
        # Graph's third field is diagnostic provenance, not a signal or delay.
        return [kind, source[1]]
    if kind == "top" and len(source) == 4:
        return [kind, source[1], source[2], _stage(source[3])]
    if kind == "clock" and len(source) == 2:
        return [kind, source[1]]
    if kind == "reset" and len(source) == 3:
        return [kind, source[1], _stage(source[2])]
    if kind == "undriven" and len(source) == 1:
        return [kind]
    if kind == "dropped" and len(source) == 2 and isinstance(source[1], str):
        return [kind, source[1]]
    if kind == "multi" and len(source) == 3 and all(isinstance(p, str) for p in source[2]):
        return [kind, source[1], sorted(source[2])]
    raise SourceGuardError(f"unsupported logical source descriptor {kind!r}")


def logical_graph_fingerprint(b):
    """Stream hash of all symbolic cells, input connections and top-port sources."""
    order = sorted(range(len(b.F.cells)), key=lambda ci: b.F.cells[ci].path)
    names = [b.F.cells[ci].path for ci in order]
    if len(set(names)) != len(names):
        raise SourceGuardError("duplicate symbolic paths in source graph")
    h = hashlib.sha256(); _frame(h, "opentallas.symbolic_source_graph.v1")
    source_cache = {}  # runtime-only net IDs; only symbolic bytes enter the hash
    def src(net):
        if net not in source_cache:
            source_cache[net] = _json(symbolic_source(b, b.G.source(net)))
        return source_cache[net]
    for ci in order:
        c = b.F.cells[ci]
        _frame(h, dict(cell=c.path, fingerprint=cell_fingerprint(c), kind=b.G.kind[ci]))
        directions = b.G.dirs[ci] if hasattr(b.G, "dirs") else c.dirs
        for pn, bits in sorted(c.ports.items()):
            if directions.get(pn) not in ("input", "inout"):
                continue
            _frame(h, ["input", pn, len(bits)])
            for net in bits:
                _frame(h, src(net))
    for pn, (direction, bits) in sorted(getattr(b.F, "top_ports", {}).items()):
        _frame(h, ["top_port", pn, direction, len(bits)])
        for net in bits:
            _frame(h, src(net))
    return h.hexdigest()


def _absolute(base, value):
    p = Path(value)
    return p if p.is_absolute() else Path(base) / p


def _config_value(value, base, field):
    if isinstance(value, dict):
        return {k: _config_value(v, base, field) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_config_value(v, base, field) for v in value]
    if field in _CONFIG_FIELDS and isinstance(value, str) and value.endswith((".json", ".json.gz")):
        p = _absolute(base, value)
        if not p.is_file():
            raise SourceGuardError(f"missing source-rule configuration {p}")
        try:
            raw = gzip.decompress(p.read_bytes()) if p.suffix == ".gz" else p.read_bytes()
            config = json.loads(raw)
        except (OSError, ValueError, EOFError) as exc:
            raise SourceGuardError(f"invalid source-rule configuration {p}: {exc}") from exc
        return {"configuration_sha256": hashlib.sha256(_json(config)).hexdigest()}
    return value


def source_rules_fingerprint(b):
    """Canonical logical-rule/selection hash; physical split metadata is excluded."""
    value = {key: _config_value(b.ab.get(key), b.base, key) for key in SOURCE_RULE_FIELDS}
    return hashlib.sha256(_json(value)).hexdigest()


def validate_guard(reference, b):
    """Validate logical graph, rules and current selected RTL before prefill."""
    if reference is None:
        return dict(enabled=False)
    if not isinstance(reference, dict):
        raise SourceGuardError("split source reference must be an object")
    rules = source_rules_fingerprint(b)
    if reference.get("source_rules_sha256") != rules:
        raise SourceGuardError("split reference source_rules_sha256 mismatch")
    graph = logical_graph_fingerprint(b)
    if reference.get("source_graph_sha256") != graph:
        raise SourceGuardError("split reference source_graph_sha256 mismatch")
    entries = reference.get("rtl_sources")
    if not isinstance(entries, list) or not entries:
        raise SourceGuardError("split reference needs nonempty rtl_sources receipts")
    extra = list(getattr(b, "extra_lib", []))
    files = list(b.ab.get("files", [])) + extra
    roots = b.ab.get("rtl_roots", ["rtl"])
    prefer = [str(_absolute(b.base, f)) for f in b.ab.get("prefer", [])] + [str(_absolute(b.base, f)) for f in extra]
    try:
        E.validate_preferred_files(prefer)
        index = E.module_index(roots, files, b.base)
    except (E.ElabError, OSError, ValueError) as exc:
        raise SourceGuardError(f"current RTL source selection failed: {exc}") from exc
    cache = {}; modules = includes = 0
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("file"), str):
            raise SourceGuardError("malformed rtl_sources receipt")
        path = _absolute(b.base, entry["file"])
        if not path.is_file():
            raise SourceGuardError(f"missing reference RTL source {path}")
        kind = entry.get("kind")
        module = entry.get("module")
        if kind == "module":
            if not isinstance(module, str) or not module:
                raise SourceGuardError("module receipt lacks a module name")
            chosen, _ambiguous = E.pick(index, module, prefer)
            if chosen is None or Path(chosen).resolve() != path.resolve():
                raise SourceGuardError(f"current selected module file changed: {module}: {chosen} != {path}")
            key = (str(path.resolve()), module)
            if key not in cache:
                body = E.module_body(path, module)
                if not body:
                    raise SourceGuardError(f"module {module} absent from {path}")
                cache[key] = hashlib.sha256(body.encode()).hexdigest()
            modules += 1
        elif kind == "include":
            key = (str(path.resolve()), None)
            if key not in cache:
                cache[key] = hashlib.sha256(path.read_bytes()).hexdigest()
            includes += 1
        else:
            raise SourceGuardError(f"unknown RTL receipt kind {kind!r}")
        if entry.get("sha256") != cache[key]:
            raise SourceGuardError(f"RTL source body changed: {path} ({module or kind})")
    return dict(enabled=True, source_graph_sha256=graph, source_rules_sha256=rules,
                module_receipts=modules, include_receipts=includes)
