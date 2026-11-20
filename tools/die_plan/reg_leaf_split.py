"""REG-LEAF-SPLIT (FABLE-FIX-KV-HG K / KV-D23-COMPOSE D25e2, 11-19): kept copies of a pure 1-stage registered soft leaf, one per
consumer pin group, each FIRM at its own site.  0 added cycles.

KV hgi_v1 head 2: the gather tail u_hst2_t2 (qkh_head_gather_stage, 1,575 bits) feeds the front ports of four head eighths
e0 / e2 / e4 / e6 on three channels.  As one leaf GPL puts it at the centroid and every pin wire crosses channels (k6: the
x 200-400 channel took 21,000 GRT overflow).  Split per channel, every pin wire stays inside its own channel.  k6 was a hand
edit of the kit RTL (fable-fix-kv-hg3/k6/split_t2.py); this is the generator form.

Opt-in plan key (absent = byte-identical kit):

    partition_types[T].reg_leaf_split = [
      {"leaf": "u_hst2_t2",
       "copies": [{"name": "a", "pins": ["u_head2_e0.*", "u_head2_e2.g_front_1_u_front__c_in", ...], "site_um": [40.0, 285.0]},
                  {"name": "b", "pins": ["u_head2_e2.g_front_1_u_front__row_in", "u_head2_e4.*"], "site_um": [40.0, 618.0]},
                  {"name": "c", "pins": ["u_head2_e6.*"], "site_um": [40.0, 950.0]}]}]

pins are fnmatch patterns on "<consumer inst>.<port>" (bound instance names of the type's bound RTL).  A bind core-input lockup
latch (clock.core_input_lockup: one-line `ot_dp_lk #(.W(n)) u_lk_nk_* (.clk(..), .d(<leaf output slice>), .q(<lk wire>));` whose
<lk wire> is one whole hard-core port connection) is seen through: its d is matched as "<core inst>.<core port>" and re-pointed
to the copy, so the copy -> latch -> core order stays (KV-PLAN-R1 11-20: kR GRT readback FF hold 5,105 rls copy -> head-core
pins to -277.6 ps; the core ETM books its clock insertion as hold, the same class QC NK closed with core_input_lockup).

Applied by gen_phys.write_type_kit on the kit copy of the bound RTL (kd/rtl): the leaf instance is replaced by one
ot_dp_dly_keep #(.W(n), .D(1)) <leaf>_rls_<name> per copy (W = the leaf output bits that copy's pins read), and every consumer
pin is re-pointed to its copy.  Sites: one is_place line per copy in istations.tcl (all flops of the copy at site_um).

Fail closed (ValueError): a leaf module not in PURE (a 1-stage register, no reset / enable) or with a non-pure parameter, a
leaf found 0 or 2+ times, an output wire that is not a plain declared wire, an input that is not <wire>, <wire>[i] or
<wire>[hi:lo] of the output's width, a use of an output wire that is not a whole-port connection of an instance, a
consumer pin matched by 0 or 2+ copies, a copy that matches no pin, a name collision, no ot_dp_dly_keep definition and no
place to put one.

Receipt kd/reg_leaf_split.json: {type, leaves: [{leaf, module, bits, copies: [{name, inst, bits, pins, site_um}]}],
flops_removed, flops_added}.
"""
import fnmatch
import json
import re
from pathlib import Path

KEY = "reg_leaf_split"
SUFFIX = "_rls_"

# module -> clock port, {input port: output port}, parameter values under which the module is a plain register
PURE = {
    "qkh_head_gather_stage": dict(clk="ck", d2q={"ti_a": "ti_b", "e_a": "e_b"}, params={"MUT": "0"}),
    "qkh_head_tstage": dict(clk="ck", d2q={"ti_a": "ti_b", "e_a": "e_b"}, params={}),
}

KEEP_MODULE = "ot_dp_dly_keep"

ID = r"[A-Za-z_]\w*"
HEAD = re.compile(rf"^\s*({ID})\s*(#\s*\((.*)\))?\s+({ID})\s*\(\s*$")
PORT = re.compile(rf"^\s*\.({ID})\s*\((.*)\)\s*,?\s*(//.*)?$")
SEL = re.compile(rf"^({ID})(?:\[(\d+)(?::(\d+))?\])?$")
LK1 = re.compile(rf"^(\s*)ot_dp_lk\s*#\(\s*\.W\((\d+)\)\s*\)\s+({ID})\s*\(\s*\.clk\(([^()]*)\)\s*,\s*\.d\(([^()]*)\)\s*,"
                 rf"\s*\.q\(({ID})\)\s*\)\s*;\s*(//.*)?$")


def config(t):
    """validated reg_leaf_split rows of one partition type; [] when absent"""
    rows = t.get(KEY) or []
    if not isinstance(rows, list):
        raise ValueError(f"{KEY}: must be a list")
    seen = set()
    for r in rows:
        if not isinstance(r, dict) or set(r) != {"leaf", "copies"} or not re.fullmatch(ID, str(r["leaf"])):
            raise ValueError(f"{KEY}: row {r!r} needs exactly leaf + copies")
        if r["leaf"] in seen:
            raise ValueError(f"{KEY}: leaf {r['leaf']} listed twice")
        seen.add(r["leaf"])
        cs = r["copies"]
        if not isinstance(cs, list) or len(cs) < 2:
            raise ValueError(f"{KEY} {r['leaf']}: >= 2 copies needed")
        names = set()
        for c in cs:
            if not isinstance(c, dict) or set(c) != {"name", "pins", "site_um"}:
                raise ValueError(f"{KEY} {r['leaf']}: copy {c!r} needs exactly name + pins + site_um")
            if not re.fullmatch(r"[A-Za-z0-9]\w*", str(c["name"])) or c["name"] in names:
                raise ValueError(f"{KEY} {r['leaf']}: copy name {c['name']!r} bad or repeated")
            names.add(c["name"])
            if not c["pins"] or not all(isinstance(p, str) and "." in p for p in c["pins"]):
                raise ValueError(f"{KEY} {r['leaf']}.{c['name']}: pins must be '<inst>.<port>' patterns")
            s = c["site_um"]
            if not (isinstance(s, list) and len(s) == 2 and all(isinstance(v, (int, float)) for v in s)):
                raise ValueError(f"{KEY} {r['leaf']}.{c['name']}: site_um must be [x, y]")
    return rows


def _module_span(lines, i):
    a = max((k for k in range(i, -1, -1) if re.match(r"^\s*module\b", lines[k])), default=None)
    b = next((k for k in range(i, len(lines)) if re.match(r"^\s*endmodule\b", lines[k])), None)
    if a is None or b is None:
        raise ValueError(f"{KEY}: no module around line {i + 1}")
    return a, b


def _block(lines, h):
    """(end line of the instance starting at h, {port: expr})"""
    ports = {}
    for k in range(h + 1, len(lines)):
        if re.match(r"^\s*\)\s*;\s*$", lines[k]):
            return k, ports
        m = PORT.match(lines[k])
        if not m:
            raise ValueError(f"{KEY}: unexpected instance line {k + 1}: {lines[k].strip()!r}")
        ports[m.group(1)] = m.group(2).strip()
    raise ValueError(f"{KEY}: instance at line {h + 1} not closed")


def _latch_core(lines, a, b, qw, leaf):
    """the "<core inst>.<core port>" a core-input lockup latch output wire qw drives: exactly one whole port connection"""
    hits, inst = [], None
    for k in range(a, b):
        hm = HEAD.match(lines[k])
        if hm:
            inst = hm.group(4)
        m = PORT.match(lines[k])
        if m and m.group(2).strip() == qw and inst is not None:
            hits.append(f"{inst}.{m.group(1)}")
        elif re.search(rf"\b{re.escape(qw)}\b", lines[k]) and not re.match(rf"^\s*wire\b", lines[k]) and not LK1.match(lines[k]):
            hits.append(None)
    if len(hits) != 1 or hits[0] is None:
        raise ValueError(f"{KEY} {leaf}: latch output {qw} is not exactly one whole core port connection ({hits})")
    return hits[0]


def _params(txt):
    return dict(re.findall(rf"\.({ID})\s*\(\s*([^()]*?)\s*\)", txt or ""))


def _decls(lines, a, b):
    """{wire: (msb, lsb, line)} of `wire [m:l] x, y;` lines in the module span"""
    out = {}
    for k in range(a, b):
        m = re.match(rf"^\s*wire\s*(?:\[(\d+):(\d+)\])?\s*({ID}(?:\s*,\s*{ID})*)\s*;\s*(//.*)?$", lines[k])
        if m:
            hi, lo = (int(m.group(1)), int(m.group(2))) if m.group(1) is not None else (0, 0)
            for n in re.split(r"\s*,\s*", m.group(3)):
                out[n] = (hi, lo, k)
    return out


def _bits(expr, decls, what):
    """'w[hi:lo]' / 'w[i]' / 'w' -> (name, [lsb .. msb] bit indices)"""
    m = SEL.match(expr.replace(" ", ""))
    if not m:
        raise ValueError(f"{KEY}: {what}: {expr!r} is not <wire>, <wire>[i] or <wire>[hi:lo]")
    n = m.group(1)
    if m.group(2) is None:
        if n not in decls:
            raise ValueError(f"{KEY}: {what}: wire {n} not declared in the module")
        hi, lo = decls[n][:2]
    else:
        hi = int(m.group(2)); lo = int(m.group(3)) if m.group(3) is not None else hi
    if hi < lo:
        raise ValueError(f"{KEY}: {what}: ascending range {expr!r}")
    return n, list(range(lo, hi + 1))


def _runs(name, idx):
    """MSB-first concat text of name[idx[-1]] .. name[idx[0]] (idx = q index per bit, LSB first)"""
    parts, k = [], len(idx) - 1
    while k >= 0:
        j = k
        while j - 1 >= 0 and idx[j - 1] == idx[j] - 1:
            j -= 1
        parts.append(f"{name}[{idx[k]}]" if j == k else f"{name}[{idx[k]}:{idx[j]}]")
        k = j - 1
    return parts[0] if len(parts) == 1 else "{" + ", ".join(parts) + "}"


def _src_concat(srcs):
    """MSB-first concat of [(wire, bit)] given LSB first, runs compressed"""
    parts, k = [], len(srcs) - 1
    while k >= 0:
        w, hb = srcs[k]
        j = k
        while j - 1 >= 0 and srcs[j - 1][0] == w and srcs[j - 1][1] == srcs[j][1] - 1:
            j -= 1
        lb = srcs[j][1]
        parts.append(f"{w}[{hb}]" if hb == lb else f"{w}[{hb}:{lb}]")
        k = j - 1
    return parts[0] if len(parts) == 1 else "{" + ", ".join(parts) + "}"


def split_text(text, row, what="bound RTL"):
    """apply one reg_leaf_split row to a bound RTL text; returns (new text, receipt row).  ValueError on any doubt."""
    leaf = row["leaf"]
    lines = text.split("\n")
    heads = [k for k, l in enumerate(lines) if (m := HEAD.match(l)) and m.group(4) == leaf]
    if len(heads) != 1:
        raise ValueError(f"{KEY} {leaf}: found {len(heads)} instance(s) in {what}")
    h = heads[0]
    hm = HEAD.match(lines[h])
    mod = hm.group(1)
    if mod not in PURE:
        raise ValueError(f"{KEY} {leaf}: module {mod} is not a known pure 1-stage register leaf ({sorted(PURE)})")
    form = PURE[mod]
    prm = _params(hm.group(3))
    for p, v in prm.items():
        if form["params"].get(p) != v:
            raise ValueError(f"{KEY} {leaf}: parameter {p}={v} is not the pure-register form {form['params']}")
    a, b = _module_span(lines, h)
    e, conn = _block(lines, h)
    want = {form["clk"], *form["d2q"], *form["d2q"].values()}
    if set(conn) != want:
        raise ValueError(f"{KEY} {leaf}: ports {sorted(conn)} != {sorted(want)}")
    decls = _decls(lines, a, b)
    clk = conn[form["clk"]]
    src = {}   # out wire -> [(in wire, bit)] per out bit (LSB first)
    for ip, op in form["d2q"].items():
        ow = conn[op]
        if not re.fullmatch(ID, ow) or ow not in decls:
            raise ValueError(f"{KEY} {leaf}.{op}: output {ow!r} is not a plain declared wire")
        ohi, olo, _ = decls[ow]
        if olo != 0:
            raise ValueError(f"{KEY} {leaf}.{op}: output wire {ow} is not [n:0]")
        iw, ib = _bits(conn[ip], decls, f"{leaf}.{ip}")
        if len(ib) != ohi + 1:
            raise ValueError(f"{KEY} {leaf}: {ip} is {len(ib)} bits, {ow} is {ohi + 1}")
        src[ow] = [(iw, x) for x in ib]
    # every use of an output wire: a whole-port connection of an instance in this module
    pat = re.compile(r"\b(" + "|".join(map(re.escape, src)) + r")\b")
    drop = {decls[n][2] for n in src}
    for k in drop:
        if any(n not in src for n, v in decls.items() if v[2] == k):
            raise ValueError(f"{KEY} {leaf}: line {k + 1} declares a leaf output together with other wires")
    pins = []   # (line, inst, port, wire, bits)
    alias = {}  # line of a core-input lockup latch -> "<core inst>.<core port>" it feeds
    inst = None
    for k in range(a, b):
        if HEAD.match(lines[k]):
            inst = HEAD.match(lines[k]).group(4)
        if h <= k <= e or k in drop or not pat.search(lines[k]):
            continue
        lm = LK1.match(lines[k])
        if lm:
            w, bb = _bits(lm.group(5).strip(), decls, f"{lm.group(3)}.d")
            if w not in src or max(bb) >= len(src[w]):
                raise ValueError(f"{KEY} {leaf}: line {k + 1}: latch d {lm.group(5)!r} is not a slice of one leaf output")
            pins.append((k, lm.group(3), "d", w, bb))
            alias[k] = _latch_core(lines, a, b, lm.group(6), leaf)
            continue
        m = PORT.match(lines[k])
        if not m or inst is None:
            raise ValueError(f"{KEY} {leaf}: line {k + 1} uses a leaf output outside a port connection: {lines[k].strip()!r}")
        w, bb = _bits(m.group(2).strip(), decls, f"{inst}.{m.group(1)}")
        if w not in src or max(bb) >= len(src[w]):
            raise ValueError(f"{KEY} {leaf}: line {k + 1}: {m.group(2)!r} is not a slice of one leaf output")
        pins.append((k, inst, m.group(1), w, bb))
    if not pins:
        raise ValueError(f"{KEY} {leaf}: the leaf drives no instance pin")
    if min(p[0] for p in pins) < min(drop):
        raise ValueError(f"{KEY} {leaf}: a leaf output is used before its declaration")
    # assign pins to copies
    owner = {}
    for k, ins, prt, w, bb in pins:
        key = alias.get(k, f"{ins}.{prt}")
        hit = [c["name"] for c in row["copies"] if any(fnmatch.fnmatchcase(key, p) for p in c["pins"])]
        if len(hit) != 1:
            raise ValueError(f"{KEY} {leaf}: pin {ins}.{prt} matches {len(hit)} copies {hit}")
        owner[k] = hit[0]
    rec = dict(leaf=leaf, module=mod, bits=sum(len(v) for v in src.values()), copies=[])
    new_inst, new_wires, rewire = [], [], {}
    used = {n for n in decls} | {HEAD.match(l).group(4) for l in lines[a:b] if HEAD.match(l)}
    order = list(src)
    for c in row["copies"]:
        cn = f"{leaf}{SUFFIX}{c['name']}"
        qn = f"w_{cn.removeprefix('u_')}_q"
        if cn in used or qn in used:
            raise ValueError(f"{KEY} {leaf}: copy name {cn} / {qn} collides")
        mine = [p for p in pins if owner[p[0]] == c["name"]]
        if not mine:
            raise ValueError(f"{KEY} {leaf}.{c['name']}: pins {c['pins']} match no consumer pin")
        slot = {}
        for _, _, _, w, bb in sorted(mine, key=lambda p: (order.index(p[3]), p[0])):
            for x in bb:
                slot.setdefault((w, x), len(slot))
        for k, ins, prt, w, bb in mine:
            rewire[k] = (prt, _runs(qn, [slot[(w, x)] for x in bb]))
        n = len(slot)
        d = _src_concat([src[w][x] for (w, x) in sorted(slot, key=slot.get)])
        new_wires.append(f"    wire [{n - 1}:0] {qn};   // {KEY} {leaf} copy {c['name']}")
        new_inst.append(f"    {KEEP_MODULE} #(.W({n}), .D(1)) {cn} (.clk({clk}), .d({d}), .q({qn}));")
        rec["copies"].append(dict(name=c["name"], inst=cn, bits=n, site_um=[float(v) for v in c["site_um"]],
                                  pins=sorted(f"{p[1]}.{p[2]}" for p in mine),
                                  via_latch=sorted(f"{p[1]}->{alias[p[0]]}" for p in mine if p[0] in alias)))
    out = []
    for k, l in enumerate(lines):
        if k == h:
            out.append(f"    // {KEY}: {leaf} ({mod}, {rec['bits']} bits) as {len(row['copies'])} kept copies per consumer group, 0 cycles")
            out.extend(new_inst)
            continue
        if k == min(drop):
            out.extend(new_wires)      # where the leaf outputs were declared: before every use
            continue
        if h < k <= e or k in drop:
            continue
        if k in rewire and k in alias:
            lm = LK1.match(l)
            l = l[:lm.start(5)] + rewire[k][1] + l[lm.end(5):]
        elif k in rewire:
            prt, ex = rewire[k]
            ind = l[:len(l) - len(l.lstrip())]
            tail = "," if l.rstrip().split("//")[0].rstrip().endswith(",") else ""
            l = f"{ind}.{prt}({ex}){tail}"
        out.append(l)
    rec["flops_added"] = sum(c["bits"] for c in rec["copies"])
    new = "\n".join(out)
    _self_check(new, rec, clk, {(p[1], p[2]): [src[p[3]][x] for x in p[4]] for p in pins})
    return new, rec


def _concat_bits(expr):
    """'{a[3:1], b[0]}' / 'a[2]' -> [(wire, bit)] LSB first"""
    e = expr.strip()
    if e.startswith("{") and e.endswith("}"):
        e = e[1:-1]
    out = []
    for part in reversed([x.strip() for x in e.split(",")]):
        m = re.fullmatch(rf"({ID})\[(\d+)(?::(\d+))?\]", part)
        if not m:
            raise ValueError(f"{KEY} self-check: cannot read {part!r}")
        hi = int(m.group(2)); lo = int(m.group(3)) if m.group(3) is not None else hi
        out += [(m.group(1), x) for x in range(lo, hi + 1)]
    return out


def _self_check(new, rec, clk, want):
    """re-read the written text: every consumer pin bit is the copy flop of exactly the leaf input bit it had before"""
    qsrc = {}
    for c in rec["copies"]:
        m = re.search(rf"^\s*{KEEP_MODULE} #\(\.W\((\d+)\), \.D\(1\)\) {c['inst']} \(\.clk\((.*?)\), \.d\((.*)\), "
                      rf"\.q\((\w+)\)\);$", new, re.M)
        if not m or int(m.group(1)) != c["bits"] or m.group(2) != clk:
            raise ValueError(f"{KEY} self-check: copy {c['inst']} not written as expected")
        d = _concat_bits(m.group(3))
        if len(d) != c["bits"]:
            raise ValueError(f"{KEY} self-check: copy {c['inst']} d is {len(d)} bits, W {c['bits']}")
        qsrc[m.group(4)] = d
    lines, inst, got = new.split("\n"), None, {}
    for l in lines:
        hm = HEAD.match(l)
        if hm:
            inst = hm.group(4)
        lm = LK1.match(l)
        if lm and (lm.group(3), "d") in want and any(q in lm.group(5) for q in qsrc):
            got[(lm.group(3), "d")] = [qsrc[w][x] for w, x in _concat_bits(lm.group(5))]
            continue
        m = PORT.match(l)
        if m and (inst, m.group(1)) in want and any(q in m.group(2) for q in qsrc):
            got[(inst, m.group(1))] = [qsrc[w][x] for w, x in _concat_bits(m.group(2))]
    if got != want:
        bad = sorted(k for k in set(want) | set(got) if got.get(k) != want.get(k))
        raise ValueError(f"{KEY} self-check: {len(bad)} pin(s) not mapped to their old source bits, e.g. {bad[:3]}")
    if rec["leaf"] in {HEAD.match(l).group(4) for l in lines if HEAD.match(l)}:
        raise ValueError(f"{KEY} self-check: leaf {rec['leaf']} still instantiated")


def apply(rtl_dir, tn, t):
    """apply the type's reg_leaf_split rows to the kit RTL in rtl_dir (in place).  Returns (receipt or None, extra sv file
    or None): the extra file defines ot_dp_dly_keep when no kit RTL does."""
    rows = config(t)
    if not rows:
        return None, None
    files = sorted(Path(rtl_dir).glob("*.sv")) + sorted(Path(rtl_dir).glob("*.v"))
    texts = {f: f.read_text() for f in files}
    rec = dict(type=tn, leaves=[])
    for r in rows:
        hit = [f for f, s in texts.items() if any((m := HEAD.match(l)) and m.group(4) == r["leaf"] for l in s.split("\n"))]
        if len(hit) != 1:
            raise ValueError(f"{KEY} {tn}: leaf {r['leaf']} found in {len(hit)} kit RTL files")
        texts[hit[0]], lr = split_text(texts[hit[0]], r, what=hit[0].name)
        lr["file"] = hit[0].name
        rec["leaves"].append(lr)
    extra = None
    if not any(re.search(rf"^\s*module\s+{KEEP_MODULE}\b", s, re.M) for s in texts.values()):
        import bind_pad_tail_split as TS
        extra = Path(rtl_dir) / "reg_leaf_split_cells.sv"
        extra.write_text(TS.KEEP_CELL)
    for f, s in texts.items():
        if s != f.read_text():
            f.write_text(s)
    rec["flops_removed"] = sum(lr["bits"] for lr in rec["leaves"])
    rec["flops_added"] = sum(lr["flops_added"] for lr in rec["leaves"])
    for lr in rec["leaves"]:
        print(f"OT_REG_LEAF_SPLIT {tn} {lr['leaf']}: {lr['bits']} bits -> "
              + ", ".join(f"{c['inst']} {c['bits']} @ {c['site_um']}" for c in lr["copies"]))
    return rec, extra


def site_lines(rec):
    """istations.tcl is_place lines: every flop of a copy at its site"""
    return [f"is_place {{*{c['inst']}[./]*}} {c['site_um'][0]} {c['site_um'][1]} rls:{c['inst']}"
            for lr in rec["leaves"] for c in lr["copies"]]


def install(kd, rec):
    """write the receipt and the site lines into kd/istations.tcl (before its `close $is_fh`, or a new file)"""
    kd = Path(kd)
    (kd / "reg_leaf_split.json").write_text(json.dumps(rec, indent=1) + "\n")
    lines = site_lines(rec)
    f = kd / "istations.tcl"
    if f.is_file():
        s = f.read_text().split("\n")
        i = next((k for k in range(len(s) - 1, -1, -1) if s[k].strip() == "close $is_fh"), None)
        if i is None:
            raise ValueError(f"{KEY}: {f} has no 'close $is_fh' line")
        f.write_text("\n".join(s[:i] + lines + s[i:]))
    else:
        import kit_istations as KI
        f.write_text(KI._genbug_gate("\n".join([KI.TCL_HEAD] + lines + [
            "close $is_fh", 'puts "OT_ISTATIONS placed $is_n flops FIRM (missing: [llength $is_miss] $is_miss)"'])) + "\n")
