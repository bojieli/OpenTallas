#!/usr/bin/env python3
"""S81-LNB-1 11-08 (class LN-BROADCAST, S81 leaf t56 place smells): per-lane register copies in a BOUND S81 leaf kit.

Measured on t56 (place smells.json): one register word of the vp hc_post coefficient file (ot_s81sl_vp cf[0:19], bound as
the native memory g_u_vp_cf) feeds the 4 hc_post lanes gl/4 == K, and the plan spreads those 4 LN macros over the whole
LN column (K spread 400-1120 um on all 79 leaf types); 640 word bits each drive 4 macro pins up to 1055 um apart, through
the 6-25 um LN-column gutters.  One reset relay copy (u_rr.rst_n[2] = rs_p) also resets all 16 lane macros (fanout 53,
1214 um).

Opt-in per plan type (partition_types[T].ln_copies, absent = no change, byte-identical kit RTL), applied by
`bind.py kit-rtl` to the private kit copy of the bound module (the bind output stays immutable):
  cf    the native memory instance `mem` (default g_u_vp_cf) whose RD_DATA is read only through constant-address read
        words: every consumer statement (`assign X = {...}` reading RD_DATA slices) gets its OWN copy module holding only
        the words it reads, written by the same write ports with the same statements in the same order (last write wins
        in both), so each copy word equals the original word in every cycle: 0 added cycles, same enables, same data.
        The copy words are (* keep *) registers, so synthesis cannot fold the 4 identical copies of one K back into one
        flop (physical/common_flow/ot_keep_regs.tcl); placement puts each copy next to its lane.  The original memory
        instance and its RD_DATA wire are removed (no reader is left).
  relay the ot_rst_relay instance `relay` (default u_u_vp_u_rr): REGIONS R -> R + n, and each of the n lane hard cores
        matching `lane_re` (default u_u_vp_g_ln_(\\d+)_u_l) whose .rst_n is relay bit k gets its own new relay bit
        R + i.  Relay copies are the same kept relay_q stage of the same sync_q (equal depth, SYNC_STAGES + TREE_STAGES
        unchanged): 0 added cycles.
Fail-closed: any structure that does not match exactly (an RD_DATA use outside an assign, a slice that is not one read
word, a write statement of another form, lanes on different relay bits) raises LnCopyError and the kit is not built.

  apply(btxt, cfg, native_dirs) -> (new_btxt, extra_module_text, report)
  python3 kit_ln_copies.py BOUND.sv NATIVE_DIR [--cfg JSON] --out NEW.sv --mods MODS.sv --report R.json
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SCHEMA = "opentallas.kit_ln_copies.v1"
DEFAULTS = {"cf": True, "relay": True, "mem": None, "relay_inst": None, "lane_re": None}
# the bind prefixes the leaf's names with its as-built path (t56: g_u_vp_cf; t10: g_u_lf4_u_vp_cf): the defaults take
# the ONE vp coefficient memory of the bound module and derive the relay / lane names from its prefix
AUTO_MEM = re.compile(r"^\s*ot_bind_native_[0-9a-f]{24}\s+g_(\w*?)u_vp_cf\s*\(", re.M)


class LnCopyError(ValueError):
    pass


def _split_conns(body):
    """'.A(x), .B({y, z})' -> {A: 'x', B: '{y, z}'} (paren / brace depth aware)"""
    out, i, n = {}, 0, len(body)
    while i < n:
        m = re.compile(r"\s*,?\s*\.(\w+)\s*\(").match(body, i)
        if not m:
            if body[i:].strip(" \t\n,") == "":
                break
            raise LnCopyError(f"unparsed connection text: {body[i:i + 80]!r}")
        j, depth = m.end(), 1
        while j < n and depth:
            depth += {"(": 1, ")": -1}.get(body[j], 0)
            j += 1
        if depth:
            raise LnCopyError("unbalanced connection list")
        out[m.group(1)] = body[m.end():j - 1].strip()
        i = j
    return out


def _instance(btxt, inst):
    """-> (match span start, end, module, params, conns) of the one instance named inst"""
    rx = re.compile(r"^([ \t]*)(\w+)\s*(#\((?:[^()]|\([^()]*\))*\))?\s*" + re.escape(inst) + r"\s*\(", re.M)
    ms = list(rx.finditer(btxt))
    if len(ms) != 1:
        raise LnCopyError(f"instance {inst}: found {len(ms)} times (want exactly 1)")
    m = ms[0]
    j, depth = m.end(), 1
    while j < len(btxt) and depth:
        depth += {"(": 1, ")": -1}.get(btxt[j], 0)
        j += 1
    k = re.compile(r"\s*;[ \t]*\n?").match(btxt, j)
    if not k:
        raise LnCopyError(f"instance {inst}: no ';' after the port list")
    return m.start(), k.end(), m.group(2), m.group(3) or "", _split_conns(btxt[m.end():j - 1])


# ------------------------------------------------------------------------------------------------ native memory parse
def parse_native(text):
    """the bind's ot_bind_native $mem_v2 helper: constant-address async read words + ONE posedge write block."""
    mm = re.search(r"^\s*module\s+(\w+)\s*\(([^)]*)\)\s*;", text, re.M)
    if not mm:
        raise LnCopyError("native module header not found")
    ports = [p.strip() for p in mm.group(2).split(",") if p.strip()]
    decl = {}
    for d, w, nm in re.findall(r"^\s*(input|output)\s+(?:\[(\d+):0\]\s+)?(\w+)\s*;", text, re.M):
        decl[nm] = (d, int(w) + 1 if w else 1)
    if set(decl) != set(ports):
        raise LnCopyError(f"native ports {ports} vs declared {sorted(decl)}")
    mems = re.findall(r"^\s*reg\s+\[(\d+):0\]\s+(\S+)\s+\[(\d+):0\]\s*;", text, re.M)
    if len(mems) != 1:
        raise LnCopyError("native module must declare exactly one memory array")
    ww, mname, depth = int(mems[0][0]) + 1, mems[0][1], int(mems[0][2]) + 1
    me = re.escape(mname)
    reads = {}
    for hi, lo, n in re.findall(r"^\s*assign\s+RD_DATA\[(\d+):(\d+)\]\s*=\s*" + me + r"\s*\[32'd(\d+)\]\s*;", text, re.M):
        hi, lo, n = int(hi), int(lo), int(n)
        if hi - lo + 1 != ww or n >= depth:
            raise LnCopyError(f"read word RD_DATA[{hi}:{lo}] = word {n}: not one full word")
        reads[(hi, lo)] = n
    if "RD_DATA" in decl and sum(hi - lo + 1 for hi, lo in reads) != decl["RD_DATA"][1]:
        raise LnCopyError("RD_DATA is not fully covered by constant-address read words")
    blocks = re.findall(r"always\s*@\s*\(([^)]*)\)\s*begin(.*?)\n\s*end\b", text, re.S)
    if len(blocks) != 1 or blocks[0][0].strip() != "posedge WR_CLK[0]":
        raise LnCopyError("native module must have exactly one 'always @(posedge WR_CLK[0])' write block")
    if len(re.findall(r"\balways\b", text)) != 1 or re.search(r"\binitial\b", text):
        raise LnCopyError("native module has other processes")
    stm = re.compile(r"\s*if\s*\(WR_EN\[(\d+)\]\)\s*" + me +
                     r"\s*\[(32'd\d+|WR_ADDR\[\d+:\d+\])\]\[(\d+):(\d+)\]\s*<=\s*(WR_DATA\[\d+\])\s*;")
    writes, i, body = [], 0, blocks[0][1]
    while True:
        m = stm.match(body, i)
        if not m:
            if body[i:].strip():
                raise LnCopyError(f"unsupported native write statement: {body[i:i + 120].strip()!r}")
            break
        if m.group(3) != m.group(4):
            raise LnCopyError("native write of more than one bit per statement")
        a = m.group(2)
        writes.append(dict(en=int(m.group(1)), addr=int(a[4:]) if a.startswith("32'd") else a, bit=int(m.group(3)),
                           data=m.group(5)))
        i = m.end()
    if not writes:
        raise LnCopyError("native module has no write statements")
    return dict(module=mm.group(1), ports=ports, decl=decl, ww=ww, depth=depth, reads=reads, writes=writes)


def copy_module(nat, words, name):
    """a module with the native ports (RD_DATA narrowed to len(words) words) holding only `words` as kept registers"""
    ww, ws = nat["ww"], set(words)
    L = [f"// S81-LNB-1 kit_ln_copies: private copy of native helper {nat['module'].split('_')[-1]} words {list(words)} (same write statements, same",
         "// order, same clock; (* keep *) so synthesis keeps every copy).  GENERATED, do not edit.",
         f"module {name}({', '.join(nat['ports'])});"]
    for p in nat["ports"]:
        d, w = nat["decl"][p]
        if p == "RD_DATA":
            w = ww * len(words)
        L.append(f"  {d} [{w - 1}:0] {p};" if w > 1 or p == "RD_DATA" else f"  {d} {p};")
    for n in words:
        L.append(f'  (* keep = "true" *) reg [{ww - 1}:0] w{n};')
    L.append("  always @(posedge WR_CLK[0]) begin")
    for s in nat["writes"]:
        if isinstance(s["addr"], int):
            if s["addr"] in ws:
                L.append(f"    if (WR_EN[{s['en']}]) w{s['addr']}[{s['bit']}] <= {s['data']};")
        else:
            for n in words:
                L.append(f"    if (WR_EN[{s['en']}] && {s['addr']} == 32'd{n}) w{n}[{s['bit']}] <= {s['data']};")
    L.append("  end")
    for i, n in enumerate(words):
        L.append(f"  assign RD_DATA[{ww * i + ww - 1}:{ww * i}] = w{n};")
    L.append("endmodule\n")
    return "\n".join(L)


# ------------------------------------------------------------------------------------------------ the two transforms
def copy_cf(btxt, cfg, native_dirs):
    mem = cfg["mem"]
    s, e, mod, params, conns = _instance(btxt, mem)
    if not re.fullmatch(r"ot_bind_native_[0-9a-f]{24}", mod) or params:
        raise LnCopyError(f"{mem} is {mod}{params}: not a bind native memory helper")
    src = next((Path(d) / f"{mod}.sv" for d in native_dirs if (Path(d) / f"{mod}.sv").is_file()), None)
    if src is None:
        raise LnCopyError(f"{mod}.sv not found in {list(map(str, native_dirs))}")
    nat = parse_native(src.read_text())
    if set(conns) != set(p for p in nat["ports"]):
        raise LnCopyError(f"{mem} connects {sorted(conns)}, module ports {nat['ports']}")
    rd = conns["RD_DATA"]
    if not re.fullmatch(r"\w+", rd):
        raise LnCopyError(f"{mem}.RD_DATA is {rd!r}, not a plain wire")
    MARK = "\x00LNC_INSTANCES\x00"
    if MARK in btxt:
        raise LnCopyError("marker collision")
    rest = btxt[:s] + MARK + btxt[e:]
    dre = re.compile(r"^[ \t]*wire\s+\[(\d+):0\]\s+" + re.escape(rd) + r"\s*;[ \t]*\n", re.M)
    dm = list(dre.finditer(rest))
    if len(dm) != 1 or int(dm[0].group(1)) + 1 != nat["decl"]["RD_DATA"][1]:
        raise LnCopyError(f"declaration of {rd}: {len(dm)} found or width differs")
    rest = rest[:dm[0].start()] + rest[dm[0].end():]
    use = re.compile(r"\b" + re.escape(rd) + r"\b(\[(\d+):(\d+)\])?")
    lines = rest.split("\n")
    consumers, mods, report = [], {}, []
    for li, line in enumerate(lines):
        if not use.search(line):
            continue
        am = re.fullmatch(r"([ \t]*assign\s+(\w+)\s*=\s*)(.*;)\s*", line)
        if not am:
            raise LnCopyError(f"{rd} read outside an assign statement: {line.strip()[:120]}")
        words, slices = [], []
        for u in use.finditer(am.group(3)):
            if not u.group(1):
                raise LnCopyError(f"{rd} read without a word slice in {am.group(2)}")
            key = (int(u.group(2)), int(u.group(3)))
            if key not in nat["reads"]:
                raise LnCopyError(f"{rd}{u.group(1)} in {am.group(2)} is not one constant-address read word")
            n = nat["reads"][key]
            if n not in words:
                words.append(n)
            slices.append((u.span(), n))
        consumers.append((li, am, words, slices))
    if not consumers:
        raise LnCopyError(f"{rd} has no reader")
    inst_lines = []
    ww = nat["ww"]
    for li, am, words, slices in consumers:
        cons = am.group(2)
        h = hashlib.sha256(json.dumps([nat["module"], words]).encode()).hexdigest()[:10]
        name = f"ot_lnc_{h}"
        mods.setdefault(name, copy_module(nat, words, name))
        wn = f"lnc_{cons}_RD"
        expr = am.group(3)
        for (a, b), n in reversed(slices):
            i = words.index(n)
            expr = expr[:a] + f"{wn}[{ww * i + ww - 1}:{ww * i}]" + expr[b:]
        lines[li] = am.group(1) + expr
        cc = ", ".join(f".{p}({wn})" if p == "RD_DATA" else f".{p}({conns[p]})" for p in nat["ports"])
        inst_lines.append(f"    wire [{ww * len(words) - 1}:0] {wn};")
        inst_lines.append(f"    {name} g_lnc_{cons} ({cc});")
        report.append(dict(consumer=cons, instance=f"g_lnc_{cons}", module=name, words=words))
    rest = "\n".join(lines)
    # the copies go where the original instance was
    block = (f"    // S81-LNB-1 kit_ln_copies: {mem} (native helper {mod.split('_')[-1]}) -> {len(consumers)} private copies, one per reader "
             f"(0 added cycles)\n" + "\n".join(inst_lines) + "\n")
    if rest.count(MARK) != 1:
        raise LnCopyError("instance marker lost")
    rest = rest.replace(MARK, block)
    words_orig = len(set(nat["reads"].values()))
    return rest, mods, dict(mem=mem, module=mod, native_file=str(src), readers=len(consumers),
                            words_original=words_orig, words_copied=sum(len(r["words"]) for r in report),
                            flops_original=words_orig * ww, flops_copied=sum(len(r["words"]) for r in report) * ww,
                            copies=report)


def copy_relay(btxt, cfg):
    inst = cfg["relay_inst"]
    s, e, mod, params, conns = _instance(btxt, inst)
    pm = re.fullmatch(r"#\(\s*\.REGIONS\((\d+)\),\s*\.SYNC_STAGES\((\d+)\),\s*\.TREE_STAGES\((\d+)\)\s*\)", params.strip())
    if mod != "ot_rst_relay" or not pm:
        raise LnCopyError(f"{inst} is {mod}{params}: not an ot_rst_relay with REGIONS/SYNC_STAGES/TREE_STAGES")
    R = int(pm.group(1))
    rw = conns.get("rst_n", "")
    if not re.fullmatch(r"\w+", rw):
        raise LnCopyError(f"{inst}.rst_n is {rw!r}, not a plain wire")
    dre = re.compile(r"^([ \t]*wire\s+)\[(\d+):0\](\s+" + re.escape(rw) + r"\s*;)", re.M)
    dm = list(dre.finditer(btxt))
    if len(dm) != 1 or int(dm[0].group(2)) + 1 != R:
        raise LnCopyError(f"declaration of {rw} ({R} bits) not found exactly once")
    # aliases a = rw[k] (the bind's per-bit glue wires) -> k
    alias = {a: int(k) for a, k in re.findall(r"^\s*assign\s+(\w+)\s*=\s*" + re.escape(rw) + r"\[(\d+)\]\s*;", btxt, re.M)}
    lane_rx = re.compile(r"^[ \t]*(\w+)\s*(#\((?:[^()]|\([^()]*\))*\))?\s*(" + cfg["lane_re"] + r")\s*\(", re.M)
    lanes = sorted(((int(m.group(4)), m.group(3)) for m in lane_rx.finditer(btxt)))
    if not lanes:
        raise LnCopyError(f"no lane instance matches {cfg['lane_re']}")
    bits, edits = set(), []
    for idx, (l, name) in enumerate(lanes):
        ls, le, lmod, lpar, lc = _instance(btxt, name)
        x = lc.get("rst_n")
        m = re.fullmatch(r"(\w+)\[0\]|(\w+)", x or "")
        w = (m.group(1) or m.group(2)) if m else None
        if w in alias:
            k = alias[w]
        else:
            m2 = re.fullmatch(re.escape(rw) + r"\[(\d+)\]", x or "")
            if not m2:
                raise LnCopyError(f"{name}.rst_n = {x!r} is not a bit of {rw}")
            k = int(m2.group(1))
        bits.add(k)
        edits.append((ls, le, name, x, R + idx, l))
    if len(bits) != 1:
        raise LnCopyError(f"lanes use relay bits {sorted(bits)}; want one shared bit")
    n = len(lanes)
    out = btxt
    for ls, le, name, x, nb, l in sorted(edits, reverse=True):
        seg = out[ls:le]
        seg2, c = re.subn(r"\.rst_n\(\s*" + re.escape(x) + r"\s*\)", f".rst_n({rw}[{nb}])", seg)
        if c != 1:
            raise LnCopyError(f"{name}: .rst_n connection not rewritten exactly once")
        out = out[:ls] + seg2 + out[le:]
    s, e, *_ = _instance(out, inst)
    seg = out[s:e]
    seg2 = seg.replace(f".REGIONS({R})", f".REGIONS({R + n})", 1)
    out = out[:s] + seg2 + out[e:]
    out, c = dre.subn(lambda m: f"{m.group(1)}[{R + n - 1}:0]{m.group(3)}", out)
    if c != 1:
        raise LnCopyError(f"declaration of {rw} not widened")
    return out, dict(relay=inst, regions_original=R, regions=R + n, shared_bit=bits.pop(),
                     lanes=[dict(lane=l, instance=name, rst_n=f"{rw}[{R + i}]") for i, (l, name) in enumerate(lanes)])


def apply(btxt, cfg, native_dirs):
    """-> (btxt, module text ('' if none), report).  cfg = plan partition_types[T].ln_copies (True = defaults)."""
    if not cfg:
        return btxt, "", None
    c = dict(DEFAULTS)
    if isinstance(cfg, dict):
        bad = set(cfg) - set(DEFAULTS)
        if bad:
            raise LnCopyError(f"ln_copies: unknown keys {sorted(bad)}")
        c.update(cfg)
    elif cfg is not True:
        raise LnCopyError("ln_copies must be true or an object")
    if not (c["mem"] and c["relay_inst"] and c["lane_re"]):
        found = AUTO_MEM.findall(btxt)
        if len(found) != 1:
            raise LnCopyError(f"ln_copies: {len(found)} vp coefficient memories (g_*u_vp_cf) in the bound module, want 1")
        pre = found[0]
        c["mem"] = c["mem"] or f"g_{pre}u_vp_cf"
        c["relay_inst"] = c["relay_inst"] or f"u_{pre}u_vp_u_rr"
        c["lane_re"] = c["lane_re"] or (r"u_" + re.escape(pre) + r"u_vp_g_ln_(\d+)_u_l")
    rep, mods = dict(schema=SCHEMA, cycles_changed=0, cfg=c), {}
    if c["cf"]:
        btxt, mods, rep["cf"] = copy_cf(btxt, c, native_dirs)
    if c["relay"]:
        btxt, rep["relay"] = copy_relay(btxt, c)
    text = "".join(mods[k] for k in sorted(mods))
    return btxt, text, rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("bound")
    ap.add_argument("native_dir", nargs="+")
    ap.add_argument("--cfg", default="true")
    ap.add_argument("--out", required=True)
    ap.add_argument("--mods", required=True)
    ap.add_argument("--report", required=True)
    a = ap.parse_args(argv)
    t, m, r = apply(Path(a.bound).read_text(), json.loads(a.cfg), a.native_dir)
    Path(a.out).write_text(t)
    Path(a.mods).write_text(m)
    Path(a.report).write_text(json.dumps(r, indent=1) + "\n")
    print(json.dumps({k: v for k, v in (r or {}).items() if k != "cfg"}, default=str)[:600])
    return 0


if __name__ == "__main__":
    sys.exit(main())
