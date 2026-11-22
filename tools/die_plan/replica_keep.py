#!/usr/bin/env python3
"""MERGE-CENSUS (FABLE-GENBUG brief 4.2, G5): derive the registers yosys opt_merge would fold between intended replicas.

Replica pattern in RTL: a module that is instantiated more than once in the kit (textually twice, inside a generate-for,
or inside another multiply instantiated module) and holds PORT-STAGING registers: a register whose every non-constant
assignment is a bare input port, a slice / concatenation of input ports, or another staging register (a pure delay stage,
as qkh_head_tstage ti_b <= ti_a, qkd_seq_fan_s qd <= q / qd2 <= qd, ot_sram_oldread_wreg wdata <= wd, ot_dp_dly r).
Two copies fed by the same signals are then identical flops and opt_merge folds them into one that drives loads far
apart.  The keep is declared per MODULE ('Mod:reg' entries of OT_KEEP_WIRES, ot_keep_regs.tcl), so a register named `q`
elsewhere is untouched.  Function is unchanged: keep only stops the folding.
usage: replica_keep.py RTL_DIR [--stations ISTATIONS.tcl] [--json]    prints one 'Mod:reg' per line.
"""
import re, sys, json
from pathlib import Path

_MOD = re.compile(r"^\s*module\s+(\w+)\b(.*?)^\s*endmodule\b", re.M | re.S)
_PARAMS = r"(?:#\s*\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\)\s*)?"
_FOR = re.compile(r"\bfor\s*\(\s*(?:genvar\s+)?\w+\s*=")


def strip_comments(t):
    t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    return re.sub(r"//[^\n]*", "", t)


def parse(rtl_dir):
    mods = {}
    for f in sorted(Path(rtl_dir).glob("*.sv")) + sorted(Path(rtl_dir).glob("*.v")):
        txt = strip_comments(f.read_text(errors="replace"))
        for m in _MOD.finditer(txt):
            mods.setdefault(m.group(1), m.group(0))
    return mods


def multiplicity(mods):
    """Effective instance count of every module below the tops (generate-for counts as 2)."""
    inst = {m: {} for m in mods}
    names = sorted(mods, key=len, reverse=True)
    if not names:
        return {}
    rx = re.compile(r"\b(" + "|".join(map(re.escape, names)) + r")\b\s*" + _PARAMS + r"(\w+)\s*\(")
    for p, body in mods.items():
        hdr = body.split(";", 1)[0]
        # generate-for extents: from each for( header to the next endgenerate (else the end of the module)
        spans = []
        for fm in _FOR.finditer(body):
            e = body.find("endgenerate", fm.start())
            spans.append((fm.start(), e if e >= 0 else len(body)))
        for mm in rx.finditer(body):
            c = mm.group(1)
            if c == p or mm.start() < len(hdr):
                continue
            n = 2 if any(a < mm.start() < b for a, b in spans) else 1
            inst[p][c] = inst[p].get(c, 0) + n
    called = {c for d in inst.values() for c in d}
    mult = {m: 0 for m in mods}
    order = []
    seen = set()

    def visit(m):
        if m in seen:
            return
        seen.add(m)
        for c in inst[m]:
            visit(c)
        order.append(m)
    for m in mods:
        visit(m)
    for m in mods:
        if m not in called:
            mult[m] = 1
    for m in reversed(order):          # parents before children
        for c, n in inst[m].items():
            mult[c] = min(mult[c] + mult[m] * n, 10 ** 6)
    return mult


def _ids(s):
    return set(re.findall(r"[A-Za-z_]\w*", s))


def staging_regs(body):
    """Names of registers of this module whose every assignment is a pure input-port delay stage."""
    hdr_and_body = body
    inputs = set()
    for m in re.finditer(r"\binput\s+(?:wire\s+|reg\s+|logic\s+)*(?:signed\s+)?(?:\[[^\]]*\]\s*)?([\w\s,]+?)(?=[;)]|\binput\b|\boutput\b|\binout\b)", hdr_and_body):
        inputs |= set(re.findall(r"[A-Za-z_]\w*", m.group(1)))
    params = set(re.findall(r"\b(?:parameter|localparam)\b[^;,)]*?\b([A-Za-z_]\w*)\s*=", hdr_and_body))
    regs = set()
    for m in re.finditer(r"\b(?:reg|logic)\s+(?:signed\s+)?(?:\[[^\]]*\]\s*)?([\w\s,]+?)(?=[;=)]|\[)", hdr_and_body):
        regs |= set(re.findall(r"[A-Za-z_]\w*", m.group(1)))
    asg = {}
    impure = set()
    pure_spans = []
    # a staging assignment sits in an UNCONDITIONAL clocked block: always @(posedge ck) [begin] lhs <= rhs; ... [end]
    for m in re.finditer(r"\balways\s*@\s*\(\s*posedge\s+\w+\s*\)\s*(?:begin\b(.*?)\bend\b|([^;]*;))", hdr_and_body, re.S):
        blk = m.group(1) if m.group(1) is not None else m.group(2)
        if re.search(r"\b(?:begin|if|else|case|casez|casex|for|while)\b", blk):
            continue
        pure_spans.append((m.start(), m.end()))
    # async-reset blocks whose only conditional is the reset itself: if (!rn) ... else ... (reset values are constants)
    for m in re.finditer(r"\balways\s*@\s*\(\s*posedge\s+\w+\s*(?:or\s+negedge\s+\w+|`OT_ARST\s*\(\s*\w+\s*\))\s*\)(.*?)(?=\balways\b|\bassign\b|\bgenerate\b|\binitial\b|\bendmodule\b|\Z)", hdr_and_body, re.S):
        blk = m.group(1)
        conds = re.findall(r"\bif\s*\(([^)]*)\)", blk)
        if re.search(r"\b(?:case|casez|casex|for|while)\b", blk) or len(conds) != 1 or not re.fullmatch(r"\s*[!~]\s*\w+\s*", conds[0]):
            continue
        pure_spans.append((m.start(), m.end()))
    for m in re.finditer(r"(?<![<=!>])\b([A-Za-z_]\w*)\s*(?:\[[^\]]*\]\s*)*<=\s*([^;]*);", hdr_and_body):
        n = m.group(1)
        if n not in regs:
            continue
        if any(a <= m.start() < b for a, b in pure_spans):
            asg.setdefault(n, []).append(m.group(2).strip())
        else:
            impure.add(n)
    for n in impure:
        asg.pop(n, None)
    ok = {}

    def qual(rhs, depth=0):
        r = re.sub(r"\s+", " ", rhs.strip())
        if re.fullmatch(r"(?:\d+)?'[sS]?[bdhBDH]\s*[0-9a-fA-FxzXZ_]+|\d+", r):
            return None                      # constant (reset value)
        if "?" in r:
            depth_ = 0
            q = None
            for i, ch in enumerate(r):
                depth_ += ch in "({["
                depth_ -= ch in ")}]"
                if ch == "?" and depth_ == 0:
                    q = i
                    break
            if q is None:
                return False
            cond, rest = r[:q], r[q + 1:]
            colon, d2 = -1, 0
            for i, ch in enumerate(rest):
                d2 += ch in "({["
                d2 -= ch in ")}]"
                if ch == ":" and d2 == 0:
                    colon = i
                    break
            if colon < 0:
                return False
            a, b = rest[:colon], rest[colon + 1:]
            if not _ids(cond) <= params:
                return False
            ra, rb = qual(a, depth + 1), qual(b, depth + 1)
            return False if (ra is False or rb is False) else (True if (ra or rb) else None)
        if re.fullmatch(r"\{\s*[\w\s+\-*()]+\{\s*(?:\d+)?'[sS]?[bdhBDH]\s*[0-9a-fA-FxzXZ_]+\s*\}\s*\}", r):
            return None                      # replicated constant {W{1'b0}} (reset value)
        if r.startswith("{") and r.endswith("}"):
            parts = re.split(r",(?![^\[\]{}()]*[\]\}\)])", r[1:-1])
            res = [qual(p, depth + 1) for p in parts]
            return False if any(x is False for x in res) else (True if any(res) else None)
        if r.startswith("(") and r.endswith(")"):
            return qual(r[1:-1], depth + 1)
        m = re.fullmatch(r"([A-Za-z_]\w*)\s*(?:\[[^\]]*\]\s*)*", r)
        if not m:
            return False
        n = m.group(1)
        if n in inputs:
            return True
        if n in regs and n in asg and depth < 8:
            return True if n in staged_cache else (False if n in bad else None if False else _chain(n, depth))
        return False

    staged_cache, bad = set(), set()

    def _chain(n, depth):
        if n in ok:
            return ok[n]
        ok[n] = False                         # cycle guard
        res = [qual(x, depth + 1) for x in asg[n]]
        ok[n] = (not any(x is False for x in res)) and any(res)
        return ok[n]
    out = []
    for n in sorted(asg):
        if _chain(n, 0):
            out.append(n)
    return out


def derive(rtl_dir):
    mods = parse(rtl_dir)
    mult = multiplicity(mods)
    res = []
    for m, body in sorted(mods.items()):
        if mult.get(m, 0) < 2:
            continue
        for r in staging_regs(body):
            res.append(f"{m}:{r}")
    return res


_IS_PLACE = re.compile(r"^\s*is_place(?:_alt)?\s+\{\*([A-Za-z_]\w*)\*\}", re.M)
_REG_DECL = re.compile(r"^\s*reg\s*(?:\[[^\]]*\]\s*)?([A-Za-z_]\w*)\s*;", re.M)


def station_regs(rtl_dir, ist_files):
    """FABLE-FIX-S81-LEAF 11-18 (S81 leaf family, TT -220..-778 on D8e): the registers of a BOUND module that the kit's
    istations.tcl places FIRM at a plan site (`is_place {*<name fragment>*} x y tag`) are declared stations, one per lane
    / group, each wired to its own consumer.  The bind writes them as plain registers of the one bound module
    (g_<path>_cst_hi_gd_s_<k>_u_src_<hash>_q), so derive() (replicated MODULES) never sees them, and stations with equal
    data fold: leaf t25 / t27 keep 2,048 of 8,200 hig bits and 1,040 of 4,112 lane cst_hi bits; the surviving lane-9 flop
    then drives the lane 1 / 5 / 13 macro pins on one net (t27 TT: 693 ps of wire at 2.2 ns slew, slack -271).
    Returns `Module:reg` for every register declaration whose name contains an is_place fragment.  Function unchanged
    (keep only stops the folding); no cycle changes; a kit without istations.tcl or without such registers gets []."""
    frags = set()
    for f in ist_files or []:
        f = Path(f)
        if f.is_file():
            frags |= set(_IS_PLACE.findall(f.read_text(errors="replace")))
    if not frags:
        return []
    res = []
    for m, body in sorted(parse(rtl_dir).items()):
        for r in sorted(set(_REG_DECL.findall(body))):
            if any(fr in r for fr in frags):
                res.append(f"{m}:{r}")
    return res


# FLOW-OPS-1300 item 6 / FABLE-CLOSURE-1320 lever 2 (no-merge default): yosys opt_merge folds the registers of relay /
# station / landing / reset-sync cells whose copies see the same D -- S81 col xo: 8 stations -> 1 rq flop driving 2,210
# pins (552 of 980 failing col ends, -169 ps); QC coll_core ot_reset_sync reset_pipe -> 1 flop on 719 pins; QC st_a
# rs_n_c -333 ps; c1x_C.  These registers exist only to be placed apart, so every clocked register of such a module and
# the named reset-synchroniser stages anywhere are kept (Mod:reg, module-scoped).  Function unchanged (keep only stops the
# folding, LEC names stay 1:1); applies to new synth only.  OT_CLASS_KEEP=0 omits it.
# CANARY-NARROW-1122 (FLOW-OPS-R2, s81_head_cl canary -5 ps TT GRT slack / 0 -> 14 GRT slew violations): A/B at 8a2a7b31a97 traced the
# regression to the ot_dp_clk_landing / _ca control registers (align_c, arm, count, fault_state, on, ready, rst_l ...) that the
# "landing" class added to OT_KEEP_WIRES.  Clock landing control is not a placed-apart relay stage, so it is left out; relay /
# station / ROM-input stations / reset-sync stay kept (S81 col 52 ROM-input stations need them).  Its (* async_reg *) synchronisers
# are still kept by ot_keep_regs.tcl.
CLASS_MOD = re.compile(r"(rly|relay|station|_stn[hv]?(?:_|\d|$)|_svc_stn|reset_sync|rst_sync|rst_relay)", re.I)
CLASS_SKIP = re.compile(r"clk_landing", re.I)
CLASS_NAMED = (("*", ("reset_pipe", "r_reset_meta", "sync_q", "rst_meta", "rst_sync_q")),
               ("_sel_hist", ("gs0", "gs1")))          # FAM-S81-SLICE-R5: WREG gs1 fan-out flop (t9: 124 pins)
_NB = re.compile(r"(?<![<=!>])\b([A-Za-z_]\w*)\s*(?:\[[^\]]*\]\s*)*<=")


def class_regs(rtl_dir):
    """`Module:reg` for every non-blocking-assigned register of a relay / station / landing / reset-sync module (CLASS_MOD)
    and the CLASS_NAMED reset-synchroniser / fan-out stages of any module.  -> sorted, de-duplicated list"""
    res = set()
    for m, body in parse(rtl_dir).items():
        regs = set()
        for d in re.finditer(r"\b(?:reg|logic)\s+(?:signed\s+)?(?:\[[^\]]*\]\s*)*([A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)*)", body):
            regs |= set(re.findall(r"[A-Za-z_]\w*", d.group(1)))
        assigned = {n for n in _NB.findall(body) if n in regs}
        if CLASS_MOD.search(m) and not CLASS_SKIP.search(m):
            res |= {f"{m}:{r}" for r in assigned}
        for frag, names in CLASS_NAMED:
            if frag == "*" or frag in m:
                res |= {f"{m}:{r}" for r in names if r in assigned}
    return sorted(res)


_KEEP_GLUE = re.compile(r"\(\*\s*keep\s*\*\)\s*reg\s*(?:\[[^\]]*\]\s*)?(g_\w+_q)\s*;")


def keep_glue_regs(rtl_dir):
    """KEEP-THROUGH (COORD 11-22, LEPE-4): `Module:reg` of every (* keep *) glue register the binder re-emitted from a (* keep *) source
    register of a dissolved parent (bind.py _glue: `(* keep *) reg [..] g_<path>_q;`).  Also named in OT_KEEP_WIRES so ot_keep_regs.tcl
    keeps the cells whatever the frontend does with a reg attribute.  OT_KEEP_THROUGH=0 omits them."""
    res = []
    for m, body in sorted(parse(rtl_dir).items()):
        res.extend(f"{m}:{r}" for r in sorted(set(_KEEP_GLUE.findall(body))))
    return res


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    res = derive(argv[0])
    if "--class" in argv:
        res += class_regs(argv[0])
    if "--stations" in argv:
        res += station_regs(argv[0], [argv[argv.index("--stations") + 1]])
    if "--json" in argv:
        print(json.dumps(res))
    else:
        print("\n".join(res))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
