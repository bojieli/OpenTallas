#!/usr/bin/env python3
"""S81-P9-FACE/CAPC (2026-10-23): per-instance channel variants of the S81 DV slice masters.

The as-built die (dv_die) feeds every slice the full 8-lane frame-return bus rt[559:0] and the 1104-b band input bi,
and ties the absent channels to constants (rt upper lanes 350'd0 / 140'd0, bi 1104'd0).  Owner rule: an unused
channel must not exist as a port.  This tool derives the used channels from the die itself and emits slice variants
whose ports exist only for those channels:

  * rt lanes: the die's rt concatenation must be {K'd0, <real lanes>} with the constant only at the MSB end (the used
    lanes are a contiguous low range 0..NRT-1; asserted).  The variant has rt[70*NRT-1:0]; the return relay, the CAP
    input landings and the CAP cluster (ot_s81sl_capc5r_n #(NRT)) carry only those lanes.
  * bi: when the die ties bi to a constant, the variant has no bi port and no bo port (both are dead in every C1 master:
    ot_s81sl_slice_c1x_k8_cap5r_lp drives bo = 0 and never reads bi; ot_s81sl_slice HB = 0 likewise).  A bi driven by a
    real net is kept.

Variant bodies are derived TEXTUALLY from the current masters (single source of truth; every substitution asserts it
matched), so the default masters stay byte-identical and their default build is unchanged.

Usage:
  python3 tools/s81_dv/slice_chan_variants.py --die DIE_ASB.V [--src-root ROOT] [--out SV] [--rewrite OUT.V] [--table]
    --out      write the generated variants (default rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_chan_variants.sv)
    --rewrite  write DIE_ASB.V with the slice instances moved to their variants (rewrite(text) -> text)
  As a module: from slice_chan_variants import plan, rewrite, emit
"""
import argparse, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
SL = 'rtl/dsrom_sys/s81_dv/slice'
SRC = {   # master -> source file (repo-relative); every master the die binds as a slice
    'ot_s81sl_slice_c1x_k8_cap5r_w': SL + '/landed/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_w.sv',
    'ot_s81sl_slice_c3x_k8_cap5r_w': SL + '/landed/c3x_k8_cap5r/ot_s81sl_slice_c3x_k8_cap5r_w.sv',
    'ot_s81sl_slice_c1x_k8_cap5r_lp': SL + '/landed/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_lp.sv',
    'ot_s81sl_slice_c3x_k8_cap5r_lp': SL + '/landed/c3x_k8_cap5r/ot_s81sl_slice_c3x_k8_cap5r_lp.sv',
    'ot_s81sl_slice_lepw_mu_72': SL + '/mu72/ot_s81sl_slice_lepw_mu_72.sv',
    'ot_s81sl_slice_lepw_mab_hbc_prod_mu_72': SL + '/mu72/ot_s81sl_slice_lepw_mab_hbc_prod_mu_72.sv',
    'ot_s81sl_slice_lepe_mu_72': SL + '/mu72/ot_s81sl_slice_lepe_mu_72.sv',
    'ot_s81sl_slice_lepe_nh_mu_72': SL + '/mu72/ot_s81sl_slice_lepe_nh_mu_72.sv',
    'ot_s81sl_slice_sukv_raw512': SL + '/ot_s81sl_slice_sukv_raw512.sv',
    'ot_s81sl_slice_iq': 'rtl/dsrom_sys/s81_dv/idx/dsdv_idx_bsplit.sv',
    'ot_s81sl_slice': SL + '/ot_s81sl_slice.sv',
}
# wrapper master -> the body master it instantiates (the body is the one that owns rt relay + CAP)
CHILD = {
    'ot_s81sl_slice_c1x_k8_cap5r_w': 'ot_s81sl_slice_c1x_k8_cap5r_lp',
    'ot_s81sl_slice_c3x_k8_cap5r_w': 'ot_s81sl_slice_c3x_k8_cap5r_lp',
    'ot_s81sl_slice_lepw_mu_72': 'ot_s81sl_slice_c1x_k8_cap5r_lp',
    'ot_s81sl_slice_lepw_mab_hbc_prod_mu_72': 'ot_s81sl_slice_c1x_k8_cap5r_lp',
    'ot_s81sl_slice_lepe_mu_72': 'ot_s81sl_slice_c1x_k8_cap5r_lp',
    'ot_s81sl_slice_lepe_nh_mu_72': 'ot_s81sl_slice_c1x_k8_cap5r_lp',
    'ot_s81sl_slice_sukv_raw512': 'ot_s81sl_slice',
    'ot_s81sl_slice_iq': 'ot_s81sl_slice',
}
LANE = 70
NLANE = 8
BIW = 1104


# ------------------------------------------------------------------------------------------------ die parsing
def _split_top(s):
    out, d, cur = [], 0, ''
    for ch in s:
        if ch in '({[': d += 1
        elif ch in ')}]': d -= 1
        if ch == ',' and d == 0:
            out.append(cur.strip()); cur = ''
        else:
            cur += ch
    if cur.strip(): out.append(cur.strip())
    return out


def _conns(body):
    """.port(expr) pairs of one instance body (text between the instance's outer parentheses)."""
    res = {}
    for item in _split_top(body):
        m = re.match(r'\.(\w+)\s*\((.*)\)$', item, re.S)
        assert m, item
        res[m.group(1)] = m.group(2).strip()
    return res


INST_RE = re.compile(r'^(\s*)(ot_s81sl_slice\w*)\s*(#\(.*?\))?\s*(u_s_\w+)\s*\((.*)\);\s*$')
CONST_RE = re.compile(r"^(\d+)'[dhb]0+$")


def _width(item):
    m = CONST_RE.match(item)
    if m: return int(m.group(1)), True
    m = re.match(r'^\w+\[(\d+):(\d+)\]$', item)
    assert m, 'cannot size rt item %r' % item
    return int(m.group(1)) - int(m.group(2)) + 1, False


def plan(text):
    """[{inst, line, module, params, nrt, bi, new}] for every slice instance of the die text."""
    rows = []
    for ln, line in enumerate(text.split('\n')):
        m = INST_RE.match(line)
        if not m: continue
        mod, params, inst, body = m.group(2), m.group(3) or '', m.group(4), m.group(5)
        assert mod in SRC, 'unknown slice master %s (%s)' % (mod, inst)
        c = _conns(body)
        rt = c['rt']; assert rt.startswith('{') and rt.endswith('}'), rt
        items = _split_top(rt[1:-1])          # MSB first
        widths = [_width(x) for x in items]
        assert sum(w for w, _ in widths) == LANE * NLANE, (inst, widths)
        const = [k for k, (_, z) in enumerate(widths) if z]
        # used lanes = contiguous low range: constants only as a prefix (MSB end)
        assert const == list(range(len(const))), '%s: rt constant not confined to the MSB end' % inst
        zbits = sum(widths[k][0] for k in const)
        assert zbits % LANE == 0, '%s: rt constant %d b is not whole lanes' % (inst, zbits)
        nrt = NLANE - zbits // LANE
        assert nrt >= 1
        bi = c.get('bi')
        bi_used = bi is not None and not CONST_RE.match(bi)
        assert 'bo' not in c or bi_used, '%s: bo connected but bi tied' % inst
        new = mod
        if nrt < NLANE: new += '_rt%d' % nrt
        if not bi_used: new += '_nb'
        rows.append(dict(inst=inst, line=ln, module=mod, params=params, nrt=nrt, bi=bi_used, new=new,
                         removed=zbits + (0 if bi_used else BIW)))
    return rows


def rewrite(text):
    """die text -> die text with every slice instance moved to its channel variant, tied rt lanes / bi removed."""
    lines = text.split('\n')
    for r in plan(text):
        if r['new'] == r['module']: continue
        line = lines[r['line']]
        m = INST_RE.match(line)
        ind, mod, params, inst, body = m.groups()
        items = _split_top(body)
        out = []
        for it in items:
            pm = re.match(r'\.(\w+)\s*\((.*)\)$', it, re.S)
            p, e = pm.group(1), pm.group(2).strip()
            if p == 'bi' and not r['bi']: continue
            if p == 'rt':
                rs = [x for x in _split_top(e[1:-1]) if not CONST_RE.match(x)]
                it = '.rt({%s})' % ', '.join(rs)
            out.append(it)
        lines[r['line']] = '%s%s %s%s (%s);' % (ind, r['new'], (params + ' ') if params else '', inst, ', '.join(out))
    return '\n'.join(lines)


# ------------------------------------------------------------------------------------------------ RTL derivation
def _read(mod, src_root):
    return open(os.path.join(src_root, SRC[mod])).read()


def _module(text, mod):
    m = re.search(r'^module %s\b.*?^endmodule\b' % re.escape(mod), text, re.S | re.M)
    assert m, mod
    return m.group(0)


def _sub(t, old, new, count=1, regex=False):
    n = len(re.findall(old, t)) if regex else t.count(old)
    assert n == count, 'expected %d x %r, found %d' % (count, old, n)
    return re.sub(old, new, t) if regex else t.replace(old, new)


def _add_nrt_param(t, mod, newmod, default):
    t = _sub(t, 'module %s #(' % mod, 'module %s #(\n    parameter integer NRT = %d,   // frame return lanes present (rt[70*NRT-1:0])' % (newmod, default))
    return t


def _rt_port(t):
    return _sub(t, r'input\s+wire\s+\[(?:559|8\s*\*\s*70\s*-\s*1):0\]\s+rt\b', 'input wire [70*NRT-1:0] rt', regex=True)


def _drop_bi(t):
    """Remove the bi / bo ports and their pass-through; assert nothing else uses them."""
    t = re.sub(r'[ \t]*input\s+wire\s+\[1103:0\]\s+bi,\s*output\s+wire\s+\[512:0\]\s+bo,[ \t]*\n', '', t, count=1)
    t = re.sub(r'[ \t]*input\s+wire\s+\[1103:0\]\s+bi,[ \t]*\n', '', t, count=1)
    t = re.sub(r'[ \t]*output\s+wire\s+\[512:0\]\s+bo,[ \t]*\n', '', t, count=1)
    t = re.sub(r'\.bi\(bi\),\s*\.bo\(bo\),\s*', '', t)
    t = re.sub(r"[ \t]*assign bo = 513'd0;[^\n]*\n", '', t)
    left = re.findall(r'.*\b(?:bi|bo)\b.*', re.sub(r'//[^\n]*', '', t))
    assert not left, 'bi/bo still used: %s' % left[:3]
    return t


def derive_lp(mod, src_root, nb):
    """c1x/c3x landed slice body with NRT lanes (and no bi/bo when nb)."""
    new = mod + 'n' + ('_nb' if nb else '')
    t = _module(_read(mod, src_root), mod)
    t = _add_nrt_param(t, mod, new, NLANE)
    t = _rt_port(t)
    t = _sub(t, '    wire [559:0] rt_q;', '    wire [70*NRT-1:0] rt_q;\n'
             '    localparam integer NW = (NRT > 4) ? 4 : NRT;      // W CAP column lanes present\n'
             '    localparam integer NE = (NRT > 4) ? NRT - 4 : 0;  // E CAP column lanes present')
    t = _sub(t, 'ot_s81sl_rly #(.W(560), .D(DR)) u_rt', 'ot_s81sl_rly #(.W(70*NRT), .D(DR)) u_rt')
    t = _sub(t, '    wire [279:0] cap5_w_in, cap5_e_in;', '    wire [70*NRT-1:0] cap5_rt_in;')
    t = _sub(t, 'ot_s81sl_capc5r u_cap (', 'ot_s81sl_capc5r_n #(.NRT(NRT)) u_cap (')
    t = _sub(t, '.rt_w(cap5_w_in), .rt_e(cap5_e_in)', '.rt(cap5_rt_in)')
    # W landing: only the present W lanes
    t = _sub(t, 'wire [4*280-1:0] cap5_west_in_bank;', 'wire [4*70*NW-1:0] cap5_west_in_bank;')
    t = _sub(t, 'wire [4*((280+23)/24)-1:0] cap5_west_in_vld;', 'wire [4*((70*NW+23)/24)-1:0] cap5_west_in_vld;')
    t = _sub(t, 'ot_pl_land_n32_chunk_w #(.W(280), .D(4), .CHUNK_BITS(24)) u_lpl_cap5_west_in_w\n        (.ck(ck_C), .rsi(cap5_rst_C), .i(rt_q[279:0])',
             'ot_pl_land_n32_chunk_w #(.W(70*NW), .D(4), .CHUNK_BITS(24)) u_lpl_cap5_west_in_w\n        (.ck(ck_C), .rsi(cap5_rst_C), .i(rt_q[70*NW-1:0])')
    t = _sub(t, 'ot_pl_land_chunk_r #(.W(280), .D(4), .K(2), .CHUNK_BITS(24)) u_lpl_cap5_west_in_r',
             'ot_pl_land_chunk_r #(.W(70*NW), .D(4), .K(2), .CHUNK_BITS(24)) u_lpl_cap5_west_in_r')
    t = _sub(t, '.vld(cap5_west_in_vld), .o(cap5_w_in));', '.vld(cap5_west_in_vld), .o(cap5_rt_in[70*NW-1:0]));')
    # E landing: present only with E lanes
    m = re.search(r'\n    wire \[4\*280-1:0\] cap5_east_in_bank;.*?\.o\(cap5_e_in\)\);\n', t, re.S)
    assert m
    e = m.group(0)
    e = _sub(e, 'wire [4*280-1:0] cap5_east_in_bank;', 'wire [4*70*NE-1:0] cap5_east_in_bank;')
    e = _sub(e, 'wire [4*((280+23)/24)-1:0] cap5_east_in_vld;', 'wire [4*((70*NE+23)/24)-1:0] cap5_east_in_vld;')
    e = _sub(e, '#(.W(280), .D(4), .CHUNK_BITS(24))', '#(.W(70*NE), .D(4), .CHUNK_BITS(24))')
    e = _sub(e, '#(.W(280), .D(4), .K(2), .CHUNK_BITS(24))', '#(.W(70*NE), .D(4), .K(2), .CHUNK_BITS(24))')
    e = _sub(e, '.i(rt_q[559:280])', '.i(rt_q[70*NRT-1:280])')
    e = _sub(e, '.o(cap5_e_in)', '.o(cap5_rt_in[70*NRT-1:280])')
    e = '\n    generate if (NE > 0) begin : g_cap5_e   // E CAP column lanes only when present' + \
        e.replace('\n    ', '\n        ').rstrip(' ') + '    end endgenerate\n'
    t = t.replace(m.group(0), e)
    if nb: t = _drop_bi(t)
    return new, t


def derive_slice(src_root, nb):
    """ot_s81sl_slice (flat C1/C3 slice on capc2) with NRT lanes; nb: C1 only (HB = 0), no bi/bo."""
    mod = 'ot_s81sl_slice'
    new = mod + ('_nb' if nb else '_n')
    t = _module(_read(mod, src_root), mod)
    t = _add_nrt_param(t, mod, new, NLANE)
    t = _rt_port(t)
    t = _sub(t, '    wire [8*70-1:0] rt_q;', '    wire [70*NRT-1:0] rt_q;')
    t = _sub(t, 'ot_s81sl_rly #(.W(8 * 70), .D(DR)) u_rt', 'ot_s81sl_rly #(.W(70 * NRT), .D(DR)) u_rt')
    t = _sub(t, '    ot_s81sl_capc2 u_cap (.clk(clk), .rst_n(rst_n), .rt_w(rt_q[279:0]), .rt_e(rt_q[559:280]),',
             '    // ot_s81sl_capc2 is a hard view (kit s81sl_capc2, fixed 4+4-lane pins): absent lanes reach its pins as 0\n'
             '    wire [8*70-1:0] cap_rt;\n'
             '    generate if (NRT < 8) begin : g_cap_pad\n'
             "        assign cap_rt = {{(70*(8-NRT)){1'b0}}, rt_q};\n"
             '    end else begin : g_cap_full\n'
             '        assign cap_rt = rt_q;\n'
             '    end endgenerate\n'
             '    ot_s81sl_capc2 u_cap (.clk(clk), .rst_n(rst_n), .rt_w(cap_rt[279:0]), .rt_e(cap_rt[559:280]),')
    if nb:
        m = re.search(r'    generate if \(HB != 0\) begin : g_c3\n.*?    end else begin : g_c1\n', t, re.S)
        assert m
        t = t.replace(m.group(0), '    generate if (HB == 0) begin : g_c1   // _nb: C1 only (C3 needs the band port)\n')
        t = _drop_bi(t)
    return new, t


def derive_wrapper(mod, nrt, nb, src_root, child_new):
    new = mod + ('_rt%d' % nrt if nrt < NLANE else '') + ('_nb' if nb else '')
    t = _module(_read(mod, src_root), mod)
    child = CHILD[mod]
    if re.search(r'^module %s #\(' % re.escape(mod), t, re.M):
        t = _add_nrt_param(t, mod, new, nrt)
    else:   # parameter-free wrapper: stays parameter-free (die binds it by name)
        t = _sub(t, 'module %s (' % mod, 'module %s #(\n    parameter integer NRT = %d   // fixed: die binds by name\n) (' % (new, nrt))
    t = _rt_port(t)
    t, n = re.subn(r'\b%s(\s*)#\(' % re.escape(child), lambda m: '%s%s#(.NRT(NRT), ' % (child_new, m.group(1)), t)
    assert n == 1, (mod, child, n)
    if nb: t = _drop_bi(t)
    return new, t


HDR = """`timescale 1ns/1ps
// GENERATED by tools/s81_dv/slice_chan_variants.py -- do not edit.  Regenerate:
//   python3 tools/s81_dv/slice_chan_variants.py --die <die_asb.v>
// Per-instance channel variants of the S81 DV slice masters, derived from the die's own slice instances: a variant
// has rt[70*NRT-1:0] for the NRT frame-return lanes the die drives (lanes 0..NRT-1) and, when the die does not drive
// bi, no bi / bo ports.  Bodies are textual derivations of the masters (relay, CAP landings and CAP cluster sized to
// NRT; ot_s81sl_capc5r_n carries only present lanes, hard CAP leaves keep fixed pins).  Masters are unchanged.
// Instances:
"""


def emit(rows, src_root=ROOT):
    parts, done = [], set()
    for r in rows:
        if r['new'] == r['module']: continue
        mod, nrt, nb = r['module'], r['nrt'], not r['bi']
        child = CHILD[mod]
        if child == 'ot_s81sl_slice':
            cnew, cbody = derive_slice(src_root, nb)
        else:
            cnew, cbody = derive_lp(child, src_root, nb)
        if cnew not in done:
            done.add(cnew); parts.append(cbody)
        wnew, wbody = derive_wrapper(mod, nrt, nb, src_root, cnew)
        assert wnew == r['new'], (wnew, r['new'])
        if wnew not in done:
            done.add(wnew); parts.append(wbody)
    hdr = HDR + ''.join('//   %-8s %-40s -> %-48s rt %d lanes, bi %s, -%d tied b\n' % (
        r['inst'], r['module'], r['new'], r['nrt'], 'kept' if r['bi'] else 'dropped', r['removed']) for r in rows)
    return hdr + '\n' + '\n\n'.join(parts) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--die', required=True)
    ap.add_argument('--src-root', default=ROOT)
    ap.add_argument('--out', default=os.path.join(ROOT, SL, 'ot_s81sl_slice_chan_variants.sv'))
    ap.add_argument('--rewrite')
    ap.add_argument('--table', action='store_true')
    a = ap.parse_args()
    text = open(a.die).read()
    rows = plan(text)
    open(a.out, 'w').write(emit(rows, a.src_root))
    if a.rewrite:
        open(a.rewrite, 'w').write(rewrite(text))
    tot = 0
    for r in rows:
        tot += r['removed']
        if a.table:
            print('%-6s %-40s -> %-46s rt %d bi %-4s -%d' % (r['inst'], r['module'], r['new'], r['nrt'],
                                                             'kept' if r['bi'] else 'drop', r['removed']))
    print('slice instances %d, variants %d, tied bits removed %d' % (len(rows), len({r['new'] for r in rows if r['new'] != r['module']}), tot))


if __name__ == '__main__':
    main()
