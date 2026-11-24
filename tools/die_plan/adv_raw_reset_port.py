"""adv_raw_reset_port.py -- PRECHECK ADV-RAW-RESET-TO-PORT (COORD 11-23 FABLE FLOW REVIEW): a START stage whose raw reset relay drives an output port.

QC C1b strict died after 3628 s at EMIT on sle_su_c.x_ctl_o: 'writer START raw reset rr_t85 drives an output port; plan a non-port
registered relay' (clock_landings writer/reader START: a port flop must feed only its port, face_guard 'shared').  The raw name is a
plan row's landing_writer_start / landing_reader_start branch stage raw_reset; whether that relay also drives an output port is a
fact of the BOUND RTL of an earlier bind of the same type (relay rr_tN = tap N's reset relay, stable while the taps are).  SU2R moved
the stage onto rr_t85, which the C4 bound body ties to an output port (assign o = rr_t85), B1/C4 used other relays.

For every type with START branches this lists each stage raw_reset that, in the type's bound module (BIND_OUT/rtl/<module>.sv: bind_out=
kw / OT_ADV_BIND_OUT / plan-of-record sibling, as ADV-GHOST-MACRO), is an `output` itself or is the source of `assign <output> = raw;`.
Since LANDING-WRAP-TOOL 11-23 the bind privatises writer and reader stages alike with a raw-export pair (clock_landings.
_private_raw_copy: +1 flop, 0 cycles), so every line is INFO (advisory, no bind refusal).  Optional cleanup: re-pick the stage's
raw_reset to a non-port relay of the same tap neighbourhood to save the extra flop.
findings(raw, plan_path, tree=None, **kw) -> WARN lines, never raises.
"""
import re
import sys
from pathlib import Path

CHECK = "ADV-RAW-RESET-TO-PORT"
MAX_LINES = 20
OUT_RE = re.compile(r"\boutput\s+(?:wire\s+|reg\s+)?(?:\[[^\]]*\]\s*)?(\w+)")
ASSIGN_RE = re.compile(r"\bassign\s+(\w+)\s*=\s*(\w+)\s*;")


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def port_driven(body):
    """raws of a bound module body that are an output or drive `assign <output> = raw;`"""
    outs = set(OUT_RE.findall(body))
    return outs | {r for o, r in ASSIGN_RE.findall(body) if o in outs}


def start_stages(t):
    """[(role, bus, stage index, raw_reset)] of a plan type's landing_writer_start / landing_reader_start branches"""
    ck = (t.get("clock") or {}) if isinstance(t, dict) else {}
    out = []
    for role, key in (("writer", "landing_writer_start"), ("reader", "landing_reader_start")):
        cfg = ck.get(key)
        for bus, br in ((cfg or {}).get("branches") or {}).items():
            for i, st in enumerate((br or {}).get("stages") or [] if isinstance(br, dict) else []):
                if isinstance(st, dict) and isinstance(st.get("raw_reset"), str):
                    out.append((role, bus, i, st["raw_reset"]))
    return out


def judge(stages, driven):
    """-> [(role, bus, i, raw)] stages whose raw is port-driven"""
    return [s for s in stages if s[3] in driven]


def _findings(raw, plan_path, tree=None, **kw):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import adv_ghost_macro as G
    types = raw.get("partition_types") or {}
    used = {p.get("type") for p in raw.get("partitions") or [] if isinstance(p, dict)}
    bdir, n_bound = G._choose_bind(raw, plan_path, tree, kw, types)
    if not bdir:
        return [_w("not checked: no bound RTL (no BIND_OUT/rtl/<module>.sv; pass bind_out=)")]
    hits, n, nobound = [], 0, 0
    for tn, t in sorted(types.items()):
        if not isinstance(t, dict) or t.get("hard") is True or (used and tn not in used) or not t.get("module"):
            continue
        st = start_stages(t)
        if not st:
            continue
        p, _m = G._bound_path(bdir, t["module"], tn)
        if not p:
            nobound += 1
            continue
        n += 1
        try:
            driven = port_driven(Path(p).read_text(errors="replace"))
        except OSError:
            continue
        bad = judge(st, driven)
        if bad:
            w = [b for b in bad if b[0] == "writer"]
            rd = [b for b in bad if b[0] == "reader"]
            # LANDING-WRAP-TOOL 11-23: the bind wraps writer stages exactly like reader stages (clock_landings._private_raw_copy):
            # a port-driving raw relay becomes ot_dp_head_raw_export_pair (+1 flop, 0 cycles), no EMIT refusal on either side
            sides = "/".join(s for s, l in (("writer", w), ("reader", rd)) if l)
            hits.append((0 if w else 1, _w(f"{tn}: INFO {sides} START stage raw reset " + ", ".join(sorted({f'{b[3]} ({b[0]} {b[1]}[{b[2]}])' for b in bad})[:6]) +
                                           " drives an output port (bind copies it with a raw-export pair, +1 flop, 0 cycles, no refusal)")))
    hits.sort(key=lambda h: h[0])
    out = [m for _, m in hits[:MAX_LINES]]
    nw = sum(1 for h in hits if h[0] == 0)
    out.append(_w("summary", f"{nw} type(s) with a writer START raw reset on a port-driving relay, {len(hits) - nw} reader-only (all copied by the bind, advisory); "
                             f"{n} types with START stages checked against bound RTL {bdir} ({nobound} without a bound body)"))
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    import json
    for ln in findings(json.load(open(sys.argv[1])), sys.argv[1], sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None,
                       bind_out=sys.argv[3] if len(sys.argv) > 3 else None):
        print(ln)
