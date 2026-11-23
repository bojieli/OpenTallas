"""adv_stn_conflict.py -- PRECHECK-R2 ADV-STN-CONFLICT (COORD 11-23): station rows the bind cannot realise as one station per bus.

  Only types the bind realises natively (as-built internal_stations_types, family prefix as clock_landings
  .expand_station_types; scope internal_stations_buses) refuse; on kit types per-core rows are merged (kit_istations) and
  are only counted.  Without an as-built (plan_gate_pre --asbuilt / kw asbuilt) OUT conflicts are counted, not listed.
  CONFLICT     a bus with >= 2 internal_stations rows (conn bus:<name>) of differing geometry (every key but note).  On an
               OUT bus native_istations.source_entries raises 'conflicting OUT station geometry <bus>' (VIS-S81-MISC gate 10:
               iqf idx_o0 carried two J8 rows, qr 149 bits and qr_v 1 bit, each with its own geometry).  On an IN bus the kit
               merges per-core rows to the deepest chain, but rows with exact sites (bit_route / bit_sites_um /
               face_bit_sites_um) and different counts make the bind raise 'conflicting destination station counts'.
  VALID-SPLIT  a valid bit stationed apart from its data with a different station COUNT (cycles): a 1-bit row next to a
               wider row on the same bus, or a bus <x>_v / _vld / _valid whose chain count differs from bus <x>.
Fix: one row per bus (merge the valid bit into the data row's geometry), or the same regs_um on both rows.
findings(raw, plan_path, tree=None, **kw) -> WARN lines; never raises.
"""
import time

CHECK = "ADV-STN-CONFLICT"
MAX_LINES = 20
EXACT_KEYS = ("bit_route", "bit_sites_um", "face_bit_sites_um")
VALID_SUFFIX = ("_v", "_vld", "_valid", "_val")


def _geom(e):
    return {k: v for k, v in e.items() if k != "note"}


def _nbits(e):
    for k in ("bits", "width", "nbits"):
        v = e.get(k)
        if isinstance(v, int):
            return v
        if isinstance(v, list):
            return len(v)
    for k in ("bit_sites_um", "face_bit_sites_um"):
        v = e.get(k)
        if isinstance(v, list) and v:
            return len(v)
    return None


def _diff_keys(a, b):
    return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))


def native_scope(ab, tn):
    """None = not native; set() = every OUT bus; else the listed OUT buses"""
    sel = set((ab or {}).get("internal_stations_types") or [])
    if not any(tn == x or tn.startswith(x + "_") for x in sel):
        return None
    sc = (ab or {}).get("internal_stations_buses") or {}
    for k in (tn,) + tuple(x for x in sel if tn.startswith(x + "_")):
        if k in sc:
            return set(sc[k])
    return set()


def type_findings(tn, t, ab=None):
    out = []
    nat = native_scope(ab, tn) if ab is not None else None
    buses = {x.get("name"): x for x in t.get("buses") or [] if isinstance(x, dict)}
    rows = {}
    for e in t.get("internal_stations") or []:
        if isinstance(e, dict) and str(e.get("conn", "")).startswith("bus:"):
            rows.setdefault(e["conn"][4:], []).append(e)
    for name, rs in sorted(rows.items()):
        if len(rs) < 2:
            continue
        g0 = _geom(rs[0])
        diff = [(i, _diff_keys(g0, _geom(r))) for i, r in enumerate(rs[1:], 1) if _geom(r) != g0]
        if not diff:
            continue
        d = (buses.get(name) or {}).get("dir")
        nb = [_nbits(r) for r in rs]
        counts = [len(r.get("regs_um") or []) for r in rs]
        valid = any(n == 1 for n in nb if n is not None) and any((n or 0) > 1 for n in nb) and len(set(counts)) > 1
        if d == "out" and nat is not None and (not nat or name in nat):
            why = f"native type: bind native_istations raises 'conflicting OUT station geometry {name}'"
        elif len(set(counts)) > 1 and any(any(k in r for k in EXACT_KEYS) for r in rs):
            why = "exact-site rows with different counts: bind raises 'conflicting destination station counts'"
        else:
            why = "kit merges them to the deepest chain (per-core rows): valid and data get different cycle counts"
            if not valid:
                if d == "out":
                    out.append((0, None))     # counted: refuses only if the type is made native
                continue                      # ordinary per-core rows: merged by design, not a finding
        kind = "VALID-SPLIT" if valid else "CONFLICT"
        out.append((2 if "native type" in why else 1, f"WARN {CHECK} {tn}: {kind} bus {name} ({d or '?'}) has {len(rs)} station rows of "
                    f"differing geometry (regs {counts}, bits {nb}; row 1 vs 0 differ in {', '.join(diff[0][1][:5])}): {why}; "
                    f"fix: one row per bus (fold the valid bit into the data row) or identical regs_um"))
    for name, rs in sorted(rows.items()):
        for suf in VALID_SUFFIX:
            if name.endswith(suf) and name[: -len(suf)] in rows:
                base = name[: -len(suf)]
                a = [r.get("regs_um") for r in rows[base]]
                b = [r.get("regs_um") for r in rs]
                if [len(x or []) for x in a] != [len(x or []) for x in b]:
                    out.append((1, f"WARN {CHECK} {tn}: VALID-SPLIT bus {name} is stationed apart from its data bus {base} "
                                f"(regs {[len(x or []) for x in b]} vs {[len(x or []) for x in a]}): valid and data can "
                                f"arrive in different cycles or sites; fix: same regs_um as {base}"))
                break
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        t0 = time.time()
        pt = raw.get("partition_types") if isinstance(raw, dict) else None
        if not pt:
            return [f"WARN {CHECK} not checked: plan has no partition_types"]
        used = {p.get("type") for p in raw.get("partitions") or [] if isinstance(p, dict)}
        ab = kw.get("asbuilt")
        if isinstance(ab, str):
            import json
            with open(ab) as f:
                ab = json.load(f)
        hits = []
        for tn, t in sorted(pt.items()):
            if not isinstance(t, dict) or t.get("hard") is True or (used and tn not in used):
                continue
            hits += type_findings(tn, t, ab if isinstance(ab, dict) else None)
        quiet = sum(1 for h in hits if h[1] is None)
        hits = [h for h in hits if h[1] is not None]
        hits.sort(key=lambda h: -h[0])
        out = [h[1] for h in hits[:MAX_LINES]]
        if hits:
            out.append(f"WARN {CHECK} summary: {len(hits)} finding(s) in {len({h[1].split()[2] for h in hits})} type(s) "
                       f"({sum(1 for h in hits if h[0] == 2)} on native OUT buses = bind refusal); {quiet} multi-geometry OUT "
                       f"bus(es) on kit types (merged by the kit; refuse only if made native)"
                       f"{'' if isinstance(ab, dict) else ' (no as-built: native types unknown)'}; {time.time() - t0:.1f} s")
        return out
    except Exception as e:  # noqa: BLE001
        return [f"WARN {CHECK} not checked: {type(e).__name__}: {str(e)[:200]}"]


if __name__ == "__main__":
    import json
    import sys
    for ln in findings(json.load(open(sys.argv[1])), sys.argv[1]):
        print(ln)
