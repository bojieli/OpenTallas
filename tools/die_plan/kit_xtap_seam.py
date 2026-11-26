#!/usr/bin/env python3
"""kit_xtap_seam.py -- C-XTAP-HOLD 11-26 (COORD 09:22 ruling): the planned HARD-SEAM hold element, both forms, opt-in.

Why (xtap_hold_census.py, residual after the pre-GRT FF hold repair): the cross-tap hold ends the in-flow repair cannot
close are hard-core OUTPUT pin -> neighbouring hard-core INPUT pin wires whose two cores hang on different early core
taps (S81 col_h9_r2 pv9e92407b: u_view.u_ha/otag,oval,ov,oerr,fault (clk_c4, insertion 303.17 ps) -> u_view.u_c/r_t_a,
r_val_a,r_v_a,r_err_a,r_f_a (clk_c3, 434.57 ps), capture 131.4 ps later, 50 ends to -16.59 ps FF with 3,827 repair
buffers spent; QC cbx_q10_h -49.25; KV pv_v5ne; HEAD hd_lep0N_w).  The wire lives in a library wrapper (ot_v41_bf_col3:
three hard cores, wires only), not in bind-emitted RTL, and widening tap affinity makes it worse (QC-DRT-ECO 11-25).

What: plan clock.xtap_seam_element {"<type>" | "<prefix>*": {"pairs": [PAIR, ...]}} (absent = off, byte-identical kits).
At GEN the pass edits the STAGED kit RTL (never a hard core): on every capture instance whose name full-matches PAIR.inst
(and whose module is in PAIR.types, when given) each named input port connection goes through one element on the SOFT
side of the core boundary:
  form "hb4"     ot_dp_hd #(.W(w), .N(n)) u_xshd_<inst>_<port>   n kept HB4xp67 per bit on the capture-side D net
                 (n given, or ceil((deficit_ps + margin_ps) / 37 ps FF)); 0 cycles (a buffer chain).
  form "lockup"  ot_dp_lk #(.W(w)) u_xslk_<inst>_<port>          negative-level latch (transparent while clk is LOW) on the
                 launch side; an ordinary fabric clock sink (nearest tap; deliberately not u_fl_/u_lk_nk_: the follow-D pass
                 would hang it on the launch CORE tap, which is pre-skewed early).  latch -> capture has about
                 T/2 + delta - window of setup and gains about T/2 - delta of hold; 0 cycles (lec.py latch_to_wire).
PAIR = {"inst": "<capture instance regex>", "ports": [...], "form": "hb4" | "lockup", "types": [module, ...],
        "n": N, "deficit_ps": D, "margin_ps": M (25), "delta_ps": capture - launch insertion, "window_ps": W (100),
        "clk": "<clock net of the wrapper>" (default: the capture instance's own clk connection), "launch": "<doc>",
        "allow_missing": false}
Both forms add 0 cycles: nothing to carry through LATCHECK (a pair that needs a cycle is not this element).
A PAIR that matches no staged instance fails GEN closed (XsError) unless allow_missing.

    spec_of(raw, tn) / apply(txt, spec) / apply_kit(RTL_DIR, spec) / keep_tcl(spec)
    findings(raw, plan_path, **kw) -> ["WARN ADV-XTAP-SEAM ..."]   (plan_advisory check, report-only)
Usage: kit_xtap_seam.py RTL.sv SPEC.json [--out OUT.sv]
"""
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_zl_lockup as Z  # noqa: E402  (the same RTL instance / connection reader as clock.zl_lockup)

CHECK = "XTAP-SEAM"
HB4_FF_PS = 37.0        # one HB4xp67 at FF / TT (hold_pad_hb4.tcl header; OT_HOLD_PAD log line)
HB4_TT_PS = 60.0
T_PS = 833.0
MARGIN_PS = 25.0        # the pre-GRT FF hold margin (pregrt_ff_hold pass all)
WINDOW_PS = 100.0       # tap window + latch D->Q + wire reserved on the latch -> capture leg
SETUP_RESERVE_PS = 200.0
N_MAX = 12
FORMS = ("hb4", "lockup")


class XsError(Exception):
    pass


class XsParse(XsError):
    """a module the reader cannot parse (apply_kit leaves it as it is and records it; a pair that then matches nothing fails)"""


def spec_of(raw, tn):
    """plan clock.xtap_seam_element entry of type tn (exact name, else the longest 'prefix*'); None = off."""
    v = ((raw or {}).get("clock") or {}).get("xtap_seam_element") or {}
    if tn in v:
        return v[tn]
    hit = [b for b in v if b.endswith("*") and tn and str(tn).startswith(b[:-1])]
    return v[max(hit, key=len)] if hit else None


def size_hb4(deficit_ps, margin_ps=MARGIN_PS, lib_ps=HB4_FF_PS):
    """HB4 cells per bit that cover a measured FF hold deficit (positive ps) plus margin: ceil((deficit + margin) / lib)."""
    need = float(deficit_ps) + float(margin_ps)
    return max(1, int(math.ceil(need / float(lib_ps) - 1e-9)))


def pair_n(pair):
    """the HB4 count of an hb4 pair: explicit n, else sized from deficit_ps (+ margin_ps)."""
    if pair.get("n") is not None:
        return int(pair["n"])
    if pair.get("deficit_ps") is None:
        raise XsError(f"hb4 pair {pair.get('inst')!r}: needs n or deficit_ps")
    return size_hb4(abs(float(pair["deficit_ps"])), pair.get("margin_ps", MARGIN_PS))


def hb4_setup_ps(n, delta_ps=0.0, period_ps=T_PS, reserve_ps=SETUP_RESERVE_PS):
    """TT setup left on the same pair after n HB4: T + delta (capture later = more time) - n x 60 - reserve."""
    return float(period_ps) + float(delta_ps) - n * HB4_TT_PS - float(reserve_ps)


def lockup_setup_ps(delta_ps=0.0, period_ps=T_PS, window_ps=WINDOW_PS):
    """latch -> capture setup: the latch opens at the fall edge, so T/2 + delta - window (delta = capture - launch insertion)."""
    return float(period_ps) / 2.0 + float(delta_ps) - float(window_ps)


def lockup_hold_ps(delta_ps=0.0, period_ps=T_PS):
    """latch -> capture hold gained: new data leaves the latch T/2 after the launch edge, the capture edge is delta late."""
    return float(period_ps) / 2.0 - float(delta_ps)


def _base(name):
    return re.sub(r"\W", "_", name[2:] if name.startswith("u_") else name)


def _blank(txt):
    """txt with every // and /* */ comment replaced by spaces (newlines kept): same length, same offsets."""
    return re.sub(r"//[^\n]*|/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), txt, flags=re.S)


def _header_end(code):
    """offset just past the ';' closing the module header of comment-free module text (any parameter-list nesting)."""
    m = re.search(r"\bmodule\s+[A-Za-z_]\w*\s*", code)
    if not m:
        raise XsParse("no module header")
    k = m.end()
    try:
        if code[k:k + 1] == "#":
            k = Z._close(code, code.index("(", k))
            k = re.compile(r"\s*").match(code, k).end()
        if code[k:k + 1] == "(":
            k = Z._close(code, k)
        return code.index(";", k) + 1
    except (Z.LkError, ValueError) as ex:
        raise XsParse(f"module header not readable: {ex}")


_INST_HEAD = re.compile(r"(?m)^[ \t]*([A-Za-z_]\w*)\s*(?=[#A-Za-z_])")
_WS = re.compile(r"\s*")
_ID = re.compile(r"[A-Za-z_]\w*")


def _instances(code):
    """[(module type, instance name, '(' offset, offset past ')')] of comment-free module body text; parameter lists of
    any nesting depth (kit_zl_lockup.instances reads one level only)."""
    out, k = [], 0
    while True:
        m = _INST_HEAD.search(code, k)
        if not m:
            return out
        k = m.end()
        mt = m.group(1)
        if mt in Z.KEYWORDS:
            continue
        j = k
        try:
            if code[j:j + 1] == "#":
                j = _WS.match(code, j + 1).end()
                if code[j:j + 1] != "(":
                    continue
                j = _WS.match(code, Z._close(code, j)).end()
            nm = _ID.match(code, j)
            if not nm or nm.group(0) in Z.KEYWORDS:
                continue
            lp = _WS.match(code, nm.end()).end()
            if code[lp:lp + 1] != "(":
                continue
            e = Z._close(code, lp)
        except Z.LkError:
            continue
        out.append((mt, nm.group(0), lp, e))
        k = e


def apply(txt, spec):
    """one module text -> (text, [element records], {skip reason: n}); a pair that matches nothing here is not an error
    (apply_kit decides over all staged files)."""
    pairs = []
    for p in spec.get("pairs") or []:
        if p.get("form") not in FORMS:
            raise XsError(f"pair {p.get('inst')!r}: form must be one of {FORMS}")
        if not p.get("ports"):
            raise XsError(f"pair {p.get('inst')!r}: no ports")
        pairs.append((re.compile(p["inst"]), set(p.get("types") or []), p))
    src = txt
    txt = _blank(src)            # comments blanked, same offsets: every read below is on code only, edits go to src
    hdr_end = _header_end(txt)
    widths = Z.decl_widths(txt)
    edits, els, used = [], [], set()
    skipped = dict(reset=0, const=0, missing=0, already=0)
    for mt, name, lp, e in _instances(txt[hdr_end:]):
        if mt in ("ot_dp_lk", "ot_dp_hd"):
            continue
        sel = next(((i, p) for i, (rx, types, p) in enumerate(pairs) if rx.fullmatch(name) and (not types or mt in types)), None)
        if sel is None:
            continue
        pi, p = sel
        cs = Z.conns(txt, hdr_end + lp, hdr_end + e)
        ck = p.get("clk") or (cs["clk"][0] if "clk" in cs and re.fullmatch(r"[A-Za-z_]\w*", cs["clk"][0]) else "clk")
        for port in p["ports"]:
            if port not in cs:
                if p.get("allow_missing"):
                    skipped["missing"] += 1
                    continue
                raise XsError(f"{name}: no connection for port {port}")
            x = cs[port][0]
            if Z.RESET_NET.fullmatch(x):
                skipped["reset"] += 1
                continue
            if Z.CONST_RE.match(x):
                skipped["const"] += 1
                continue
            if re.fullmatch(r"xs_\w+", x):
                skipped["already"] += 1           # a second GEN on the same staged file: the element is there
                continue
            try:
                w = Z.expr_width(x, widths)
            except Z.LkError as ex:
                raise XsError(f"{name}.{port}: {ex}")
            net = f"xs_{_base(name)}_{port}"
            while net in used or net in widths:
                net += "_x"
            used.add(net)
            rec = dict(pair=pi, form=p["form"], capture=name, module=mt, port=port, width=w, src=x, net=net)
            if p["form"] == "hb4":
                rec.update(inst=f"u_xshd_{_base(name)}_{port}", n=pair_n(p))
                if not 1 <= rec["n"] <= N_MAX:
                    raise XsError(f"{name}.{port}: hb4 n {rec['n']} outside 1..{N_MAX} (use the lockup form)")
            else:
                rec.update(inst=f"u_xslk_{_base(name)}_{port}", clk=ck)
            els.append(rec)
            edits.append((cs[port][1], cs[port][2], net))
    txt = src
    if not els:
        return txt, els, skipped
    for a, b, net in sorted(edits, reverse=True):
        txt = txt[:a] + net + txt[b:]
    decl = [f"    // kit_xtap_seam (C-XTAP-HOLD, plan clock.xtap_seam_element): {len(els)} hard-seam hold element(s), 0 cycles"]
    body = []
    for r in els:
        wd = f"[{r['width'] - 1}:0]" if isinstance(r["width"], int) else f"[{r['width']}-1:0]"
        decl.append(f"    wire {wd} {r['net']};  // kit_xtap_seam {r['form']}: {r['capture']}.{r['port']}")
        if r["form"] == "hb4":
            body.append(f"    ot_dp_hd #(.W({r['width']}), .N({r['n']})) {r['inst']} (.a({r['src']}), .y({r['net']}));")
        else:
            body.append(f"    ot_dp_lk #(.W({r['width']})) {r['inst']} (.clk({r['clk']}), .d({r['src']}), .q({r['net']}));")
    txt = txt[:hdr_end] + "\n" + "\n".join(decl) + txt[hdr_end:]
    k = txt.rindex("endmodule")
    txt = txt[:k].rstrip(" \t") + ("" if txt[:k].rstrip(" \t").endswith("\n") else "\n") + "\n".join(body) + "\n" + txt[k:]
    return txt, els, skipped


def _bits(els):
    return sum(r["width"] for r in els if isinstance(r["width"], int))


def apply_kit(rtl_dir, spec):
    """gen_phys entry: the pass on every staged *.sv / *.v with a matching instance name.  A pair that matches in NO file
    fails closed (XsError) unless allow_missing.  Adds ot_dp_hd / ot_dp_lk to the first patched file when no staged file
    defines the cell.  -> {file: {elements, bits, hb4_cells, forms, skipped}, "_pairs": [hits per pair]}"""
    import gen_rtl
    files = sorted(Path(rtl_dir).glob("*.sv")) + sorted(Path(rtl_dir).glob("*.v"))
    pairs = list(spec.get("pairs") or [])
    rxs = [re.compile(p["inst"]) for p in pairs]
    out, hits, patched, forms, unparsed = {}, [0] * len(pairs), [], set(), []
    for f in files:
        src = f.read_text(errors="replace")
        if not re.search(r"\bmodule\b", src):
            continue
        words = set(re.findall(r"[A-Za-z_]\w*", src))
        if not any(rx.fullmatch(w) for w in words for rx in rxs):
            continue
        pieces, els, sk, k = [], [], {}, 0
        for m in re.finditer(r"(?s)\bmodule\s+[A-Za-z_]\w*.*?\bendmodule\b", src):
            pieces.append(src[k:m.start()])
            try:
                ctxt, cel, csk = apply(m.group(0) + "\n", spec)
            except XsParse as ex:
                unparsed.append(f"{f.name}:{m.group(0)[:60].split('(')[0].strip()}: {ex}")
                ctxt, cel, csk = m.group(0) + "\n", [], {}
            pieces.append(ctxt[:-1])
            els += cel
            for a, b in csk.items():
                sk[a] = sk.get(a, 0) + b
            k = m.end()
        pieces.append(src[k:])
        if not els:
            continue
        for r in els:
            hits[r["pair"]] += 1
            forms.add(r["form"])
        tmp = f.with_name(f.name + ".xs_tmp")
        tmp.write_text("".join(pieces))
        tmp.replace(f)
        patched.append(f)
        out[f.name] = dict(elements=len(els), bits=_bits(els),
                           hb4_cells=sum(r["width"] * r["n"] for r in els if r["form"] == "hb4" and isinstance(r["width"], int)),
                           forms=sorted({r["form"] for r in els}), skipped=sk,
                           insts=[f"{r['inst']}:{r['form']}:{r['width']}" + (f"x{r['n']}" if r["form"] == "hb4" else "") for r in els])
    for i, p in enumerate(pairs):
        if not hits[i] and not p.get("allow_missing"):
            raise XsError(f"clock.xtap_seam_element pair {p['inst']!r} ports {p.get('ports')} matched no instance in {rtl_dir}")
    if patched:
        text = "".join(f.read_text(errors="replace") for f in files)
        add = ""
        if "hb4" in forms and not re.search(r"\bmodule\s+ot_dp_hd\b", text):
            add += "\n" + gen_rtl.HOLD_CELLS
        if "lockup" in forms and not re.search(r"\bmodule\s+ot_dp_lk\b", text):
            add += Z.LK_MODULE
        if add:
            with open(patched[0], "a") as fh:
                fh.write(add)
            out[patched[0].name]["cells_added"] = True
    out["_pairs"] = hits
    if unparsed:
        out["_unparsed_modules"] = unparsed[:50]
    return out


def keep_tcl(spec):
    """PRE_FLOORPLAN text keeping the u_xshd_* HB4 chains (dont_touch cells and their nets, as hold_pad_dont_touch_tcl does
    for u_hdly_lk_*) and failing the kit when the netlist lost them.  "" without an hb4 pair (byte-same)."""
    if not any(p.get("form") == "hb4" for p in (spec or {}).get("pairs") or []):
        return ""
    return ("# clock.xtap_seam_element hb4 form (kit_xtap_seam.py): keep the hard-seam hold chains (u_xshd_*, HB4xp67)\n"
            "set ot_xs {}\n"
            "foreach i [[ord::get_db_block] getInsts] {\n"
            "  if {[string match *u_xshd_* [$i getName]] && [string match HB*xp67* [[$i getMaster] getName]]} { lappend ot_xs $i }\n"
            "}\n"
            "foreach i $ot_xs { $i setDoNotTouch 1\n"
            "  foreach it [$i getITerms] { set n [$it getNet]; if {$n ne \"NULL\" && [$n getSigType] eq \"SIGNAL\"} { $n setDoNotTouch 1 } } }\n"
            "puts \"OT_XTAP_SEAM dont_touch [llength $ot_xs] hard-seam HB4 cells (and their nets)\"\n"
            "if {![llength $ot_xs]} { error \"OT_XTAP_SEAM: plan declares an hb4 hard-seam element for this type but the netlist has no u_xshd_ cell\" }\n")


ABUT_UM = 1.0           # two hard cores closer than this on a facing edge leave no soft site between their face pins


def _box(h):
    """(x0, y0, x1, y1) of a plan hard core record, or None without origin / outline."""
    o, wh = h.get("origin_um"), h.get("outline_um")
    if not o or not wh:
        return None
    w, ht = (wh[1], wh[0]) if "90" in str(h.get("orient") or "") or "270" in str(h.get("orient") or "") else (wh[0], wh[1])
    return (float(o[0]), float(o[1]), float(o[0]) + float(w), float(o[1]) + float(ht))


def abutted(t, pair):
    """[(capture core inst, neighbour core inst, gap um)] for every capture core of pair on type record t that has another
    hard core within ABUT_UM on a facing edge.  Face pins on that edge meet by abutment (S81 col_h9 / col_h10 u_view.u_ha |
    u_c: 0 um, M4 face pins at the same y): no soft-side element can sit between them, the pair needs the core-tap
    contract (or the core's own boundary) instead."""
    rx, types = re.compile(pair["inst"]), set(pair.get("types") or [])
    cores = [(h, _box(h)) for h in (t or {}).get("hard_cores") or []]
    out = []
    for h, b in cores:
        if b is None or not rx.fullmatch(str(h.get("inst", "")).split(".")[-1]) or (types and h.get("module") not in types):
            continue
        for g, c in cores:
            if g is h or c is None:
                continue
            ox = min(b[2], c[2]) - max(b[0], c[0])          # overlap along x / y (negative = gap)
            oy = min(b[3], c[3]) - max(b[1], c[1])
            if (oy > 0 and -ABUT_UM < ox <= 0) or (ox > 0 and -ABUT_UM < oy <= 0):
                out.append((h.get("inst"), g.get("inst"), abs(round(max(-ox if oy > 0 else -oy, 0.0), 3))))
    return out


def _w(obj, msg):
    return f"WARN ADV-{CHECK} {obj}: {msg}"


def findings(raw, plan_path=None, tree=None, **_kw):
    """plan_advisory check (report-only): every declared pair is well formed, sized, and leaves setup on the same pair."""
    v = ((raw or {}).get("clock") or {}).get("xtap_seam_element") or {}
    out = []
    types = (raw or {}).get("partition_types") or {}
    period = float(((raw or {}).get("die") or {}).get("period_ps") or T_PS)
    for key, spec in sorted(v.items()):
        hit = [t for t in types if t == key or (key.endswith("*") and t.startswith(key[:-1]))]
        if not hit:
            out.append(_w(key, "matches no partition type (the element is never emitted)"))
        for p in spec.get("pairs") or []:
            obj = f"{key}/{p.get('inst')}"
            ab = [(tn, x) for tn in hit for x in abutted(types[tn], p)] if p.get("inst") else []
            if ab:
                tn, (ci, ni, gap) = ab[0]
                out.append(_w(obj, f"ABUT: capture core abuts a neighbour core on {len({a_[0] for a_ in ab})} type(s) "
                                   f"({len(ab)} faces; e.g. {tn}: {ci} | {ni} gap {gap:g} um): pins on that face have no soft site, "
                                   "the element is not placeable there; use the core-tap pair contract for those pins"))
            d = float(p.get("delta_ps") or 0.0)
            if p.get("form") == "hb4":
                try:
                    n = pair_n(p)
                except XsError as ex:
                    out.append(_w(obj, str(ex)))
                    continue
                if n > N_MAX:
                    out.append(_w(obj, f"hb4 n {n} > {N_MAX}: use the lockup form"))
                if p.get("deficit_ps") is not None and n * HB4_FF_PS < abs(float(p["deficit_ps"])) + float(p.get("margin_ps", MARGIN_PS)):
                    out.append(_w(obj, f"hb4 n {n} x {HB4_FF_PS:g} ps < deficit {abs(float(p['deficit_ps'])):g} + margin"))
                s = hb4_setup_ps(n, d, period)
                if s < 0:
                    out.append(_w(obj, f"hb4 n {n}: TT setup estimate {s:.0f} ps < 0 on the same pair (T {period:g}, delta {d:g})"))
            elif p.get("form") == "lockup":
                s = lockup_setup_ps(d, period, p.get("window_ps", WINDOW_PS))
                if s < 0:
                    out.append(_w(obj, f"lockup: latch -> capture setup T/2 + delta - window = {s:.0f} ps < 0"))
                if lockup_hold_ps(d, period) <= 0:
                    out.append(_w(obj, f"lockup: delta {d:g} ps >= T/2, a half-cycle latch cannot hold this pair"))
            else:
                out.append(_w(obj, f"form {p.get('form')!r} is not one of {FORMS}"))
    return out


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    rtl, spec = Path(argv[0]), json.loads(Path(argv[1]).read_text())
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else rtl
    txt, els, sk = apply(rtl.read_text(), spec)
    out.write_text(txt)
    print(json.dumps(dict(elements=len(els), bits=_bits(els), skipped=sk)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
