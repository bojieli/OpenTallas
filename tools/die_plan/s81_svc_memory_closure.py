#!/usr/bin/env python3
"""S81 svc memory-closure CLASS transform (DIE-S81-51/MEM, CLOSURE S81-066, 11-03).

Applies the adopted T7 memory-closure source event (12605dc2 = PMEM cut -> PVQ cut -> LAND cut -> staging
SRAM_MACRO=1, COORD 11-03 00:33) to every sibling svc type whose bound carries the same native helpers
(ot_bind_native_193c9 pmem 512x512, 9c281 pvq 8x2120, 4c805 land 640x256, attn_staging 4x160x265).

The four reference transforms (results/rtl/s81_T7_*) are executed UNCHANGED in their proof logic. Only two things
are re-targeted per type:
  * the instance prefix u_rsv_14_ -> the type's u_rsv_NN_ (one svc instance per type);
  * bind-numbered nets (N_Y / procmux_N_Y) through a structural name map (sigmap: driver text with prefix
    canonicalised and numbered operands replaced recursively by their own signature + source location), each
    mapped net unique in both files.
The T7 preimage HASH locks are replaced by: (a) self-check that the ported chain reproduces 12605dc2 byte-exactly on
the T7 original, (b) every structural proof obligation of each transform (port identity, capture identity,
struct field identity, per-lane row/valid/win/need/scale identity, removal counts, untouched-lines-in-order,
header identity) still raising on mismatch.
"""
import argparse, gzip, hashlib, json, re, sys, threading, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.setrecursionlimit(1000000); threading.stack_size(512 * 1024 * 1024)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s81_svc_idx_fit as IDX   # MEM idx fit (svc_lo dsdv_idx_rg3 -> dsdv_idx_rg3_fit), gate s81_svc_idx_fit_1103
REF = {
    'pmem': ROOT / 'results/rtl/s81_T7_pmem_bound_cut_0900/transform.py',
    'pvq': ROOT / 'results/rtl/s81_T7_pvq_bound_cut_1040/transform.py',
    'land': ROOT / 'results/rtl/s81_T7_LAND_bound_cut_1102/transform.py',
    'stage': ROOT / 'results/rtl/s81_T7_STAGE_macro_gate_1102/stage_flip.py',
}
CHILDREN = {
    'ot_t7_pmem_capture_candidate.sv': ('results/rtl/s81_T7_pmem_bound_cut_0900/ot_t7_pmem_capture_candidate.sv', '3d7ab5aa'),
    'ot_t7_pvq_capture_candidate.sv': ('results/rtl/s81_T7_pvq_bound_cut_1040/ot_t7_pvq_capture_candidate.sv', '80367218'),
    'ot_t7_land_capture_candidate.sv': ('results/rtl/s81_T7_LAND_bound_cut_1102/ot_t7_land_capture_candidate.sv', '64e23cf3'),
}
# MEM v2 (svc fit, 2026-11-03): right-sized children, gate results/rtl/s81_svc_memory_fit_1103/run.sh
CHILDREN_V2 = {
    'ot_t7_pmem_capture_v2.sv': ('results/rtl/s81_svc_memory_fit_1103/ot_t7_pmem_capture_v2.sv', None),
    'ot_t7_pvq_capture_v2.sv': ('results/rtl/s81_svc_memory_fit_1103/ot_t7_pvq_capture_v2.sv', None),
    'ot_t7_land_capture_v2.sv': ('results/rtl/s81_svc_memory_fit_1103/ot_t7_land_capture_v2.sv', None),
    'ot_hdc_v41x_attn_staging_fit.sv': ('results/rtl/s81_svc_memory_fit_1103/ot_hdc_v41x_attn_staging_fit.sv', None),
}
MACROS = {'v1': {'ot_sram_1r1w_256x256_m2_r2c2': 32, 'ot_sram_1r1w_32x64_m1': 34},
          'v2': {'ot_sram_1r1w_160x256_m1_r0c0': 12, 'ot_sram_1r1w_160x265_m1_r0c0': 8,
                 'ot_sram_1r1w_256x256_m1_r0c0': 4, 'ot_sram_1r1w_32x128_m1_r0c0': 17}}
FIT_RE = [(re.compile(r'^(\s*)ot_t7_(land|pmem|pvq)_capture_candidate( \w+ \()$', re.M), r'\1ot_t7_\2_capture_v2\3', 3),
          (re.compile(r"^(\s*)ot_hdc_v41x_attn_staging( #\(\.D\(32\), \.NL\(4\), \.SRAM_MACRO\(1'b1\), \.TROWS\(640\)\) "
                      r"\w+_g_stage2_u_stage[01] \()$", re.M), r'\1ot_hdc_v41x_attn_staging_fit\2', 2)]


def fit_v2(closed):
    """MEM v2: the v1 closed bound with its 3 capture children and 2 staging instances bound to the right-sized
    children (port-identical, gated against the v1 children in s81_svc_memory_fit_1103)."""
    if re.search(r'^\s*ot_t7_land_capture_v2 ', closed, re.M): return closed   # already v2 (v2 packet)
    for rx, rep, n in FIT_RE:
        closed, k = rx.subn(rep, closed)
        if k != n: raise ValueError('MEM v2: expected %d instances of %s, found %d' % (n, rx.pattern[:40], k))
    return closed


def children(form):
    return CHILDREN if form == 'v1' else CHILDREN_V2


def idx_fit(closed, files, rtl=None):
    """MEM idx fit (v2 only): rename the svc_lo dsdv_idx_rg3 instance to dsdv_idx_rg3_fit and generate that child
    from the dsdv_idx_rg3.sv the kit lists (`files`; sha-checked + proof preconditions in s81_svc_idx_fit).
    DIE-S81-66 11-05: the chain-end reader dsdv_idx_rg3_nq (svc_lo t7) -> dsdv_idx_rg3_nq_fit + dsdv_idx_rg3_nq_native_fit
    from the listed dsdv_idx_rg3_nq.sv / dsdv_idx_rg3_nq_native.sv.
    Returns (closed, {child name: text}, macros, receipt) - no children / macros when the bound has no reader."""
    closed, n = IDX.fit_bound(closed)
    kind = IDX.bound_kind(closed)
    if kind is None: return closed, {}, {}, None

    def one(name):
        srcs = [f for f in files if Path(f).name == name]
        if len(srcs) != 1: raise ValueError('idx fit: %d %s in the kit file list' % (len(srcs), name))
        return srcs[0], Path(srcs[0]).read_text()

    kids = {'dsdv_idx_fit_mem.sv': (ROOT / IDX.FIT_MEM).read_text()}
    if kind == 'rg3':
        p, src = one('dsdv_idx_rg3.sv'); fit = IDX.fit_source(src)
        kids['dsdv_idx_rg3_fit.sv'] = fit; origs = {p: 'dsdv_idx_rg3'}
    else:
        p, src = one('dsdv_idx_rg3_nq_native.sv'); fit = IDX.fit_source(src, nq=True)
        pw, wsrc = one('dsdv_idx_rg3_nq.sv')
        kids['dsdv_idx_rg3_nq_native_fit.sv'] = fit; kids['dsdv_idx_rg3_nq_fit.sv'] = IDX.fit_nq_wrapper(wsrc)
        origs = {pw: 'dsdv_idx_rg3_nq', p: 'dsdv_idx_rg3_nq_native'}
    # an original reader leaves the kit lists when nothing else instantiates it (bound now binds the fit child)
    dropped = []
    for o, mod in origs.items():
        users = [f for f in files if f.endswith('.sv') and f not in origs and Path(f).exists()
                 and re.search(r'^\s*' + mod + r'\s+#\(', Path(f).read_text(), re.M)]
        if rtl is not None: users = [f for f in users if Path(f).resolve() != Path(rtl).resolve()]
        if not users: dropped.append(o)
    return closed, kids, IDX.bound_macros(closed), dict(source=p, source_sha=IDX.sha12(src), fit_sha=IDX.sha12(fit), renamed=n,
                                          kind=kind, dropped=dropped)


REF_GZ = ROOT / 'results/rtl/s81_T7_pmem_bound_cut_0900/native_parent.sv.gz'   # T7 original bound 61c902f1
# Regenerated reference (s81_svc_ref_regen.py): a current T7 bound + the map from the 61c902f1 names the transforms use
CUR_REF = ROOT / 'results/rtl/s81_svc_memory_fit_1103/ref_1105'
RE_HASH = re.compile(r'src_([0-9a-f]{20})')
RE_PROC = re.compile(r'procmux_(\d+)')
RE_ENG = re.compile(r"E\+'(\d+)_Y")
RE_ATT = re.compile(r"(?<![\w$])(?<!E\+')(\d+)_Y\b|'(\d{2,3})'")
NATIVE = ('ot_bind_native_193c9bdc13b0c4251a5bbbc4', 'ot_bind_native_9c28130c03bbd6a26f6fd9a5',
          'ot_bind_native_4c805a5536bda0930879099e', 'ot_hdc_v41x_attn_staging')
T7_ORIG = '61c902f184b49e231c34de041d0f1832a4117749592f81fa3bf42d6ff4df504a'
T7_CLOSURE = '12605dc2'
NUM = re.compile(r'^w_u_rsv_\d+_\w*?_(?:procmux_)?\d+_Y$')
TOK = re.compile(r'\bw_\w+\b')
REF_NUMBERED = re.compile(r"procmux_\d+|(?<![\w])\d+_Y\b|'(\d+)'")


def sha(s): return hashlib.sha256(s.encode()).hexdigest()


def rsv(s):
    """svc head: 'u_rsv_NN_' (rs types, T7) or 'u_rsv_NN_u_' (pvso_entry wrapper level) so that head + 'u_u_att_' is
    the attention unit prefix."""
    m = set(re.findall(r'\bw_u_rsv_(\d+)_', s))
    if len(m) != 1: raise ValueError('expected one svc instance prefix, got %r' % sorted(m))
    n = m.pop(); heads = [h for h in ('u_rsv_%s_' % n, 'u_rsv_%s_u_' % n) if ('w_' + h + 'u_u_att_') in s]
    if len(heads) != 1: raise ValueError('svc att prefix not unique: %r' % heads)
    return heads[0]


def signatures(s):
    n = rsv(s); drv = {}
    for l in s.splitlines():
        code, _, loc = l.partition('  //'); code = code.strip()
        m = re.match(r'assign (w_\w+) = (.*);$', code)
        if m: drv.setdefault(m[1], []).append(m[2] + ' @' + loc.strip()); continue
        m = re.match(r'(ot_bind_native_\w+) g_\w+ \((.*)\.Y\((w_\w+)\)\);$', code)
        if m: drv.setdefault(m[3], []).append(m[1] + '|' + m[2])
    pre = 'w_' + n; memo = {}; stk = set()
    def sig(t):
        if not NUM.match(t): return t.replace(pre, 'w_P_')
        if t in memo: return memo[t]
        if t in stk: return 'CYC'
        stk.add(t); d = drv.get(t)
        if not d or len(d) != 1: r = 'UNDRIVEN%d' % len(d or [])
        else: r = 'h' + hashlib.sha1(TOK.sub(lambda m: '<' + sig(m.group(0)) + '>', d[0]).replace(pre, 'w_P_').encode()).hexdigest()[:20]
        stk.discard(t); memo[t] = r; return r
    return n, {t: sig(t) for t in drv if NUM.match(t)}


def name_map(ref_s, typ_s):
    rn, rs = signatures(ref_s); tn, ts = signatures(typ_s)
    inv = {}; rc = {}
    for k, v in ts.items(): inv.setdefault(v, []).append(k)
    for v in rs.values(): rc[v] = rc.get(v, 0) + 1
    return rn, tn, {k: inv[v][0] for k, v in rs.items() if rc[v] == 1 and len(inv.get(v, [])) == 1}


def port_source(src, tn, nmap, ref_head='u_rsv_14_'):
    """Re-target one reference transform: numbered suffixes via nmap, head u_rsv_14_ -> type head, hash locks off."""
    assert ref_head == 'u_rsv_14_'
    P = 'w_' + ref_head + 'u_u_att_'; TP = 'w_' + tn + 'u_u_att_'
    suf = {}
    for k, v in nmap.items():
        if k.startswith(P):
            a = k[len(P):-2]; b = v[len(TP):-2] if v.startswith(TP) else None
            if b is None: continue
            if a.startswith('u_eng_'): continue
            suf[a] = b
    used = []
    def sub_procmux(m):
        a = m.group(0)
        if a not in suf: raise ValueError('unmapped reference net %s' % a)
        used.append((a, suf[a])); return suf[a]
    out = re.sub(r'procmux_\d+', sub_procmux, src)
    # plain numbered nets ('558', '711_Y', 60_Y in regexes) must map to the same number, else refuse
    eng = set(re.findall(r"E\+'(\d+)_Y", src))
    for a in (set(re.findall(r"(?<![\w$])(\d+)_Y\b", src)) | set(re.findall(r"'(\d{2,3})'", src))) - eng:
        if a in suf and suf[a] != a: raise ValueError('numbered net %s maps to %s: renumbered plain net not supported' % (a, suf[a]))
        if a not in suf and a not in ('0', '1'):
            raise ValueError('reference net %s_Y not structurally mapped' % a)
    for e in re.findall(r"E\+'(\d+)_Y", src):
        k = P + 'u_eng_%s_Y' % e
        if nmap.get(k) != TP + 'u_eng_%s_Y' % e: raise ValueError('u_eng net %s not mapped identically' % e)
    out = out.replace(ref_head, tn)
    out = out.replace("if digest(s.encode())!=EXPECTED:raise ValueError('native parent body hash')", "pass  # hash lock -> class port (self-check on T7)")
    out = out.replace("if sha(s) not in ALLOWED:raise ValueError('unapproved preimage hash')", "pass  # hash lock -> class port")
    out = out.replace("if h not in ALLOWED: raise ValueError('unapproved preimage hash')", "pass  # hash lock -> class port")
    out = out.replace("    if h not in ALLOWED:\n        raise ValueError('unapproved preimage hash ' + h[:8])", "    pass  # hash lock -> class port")
    if 'hash lock -> class port' not in out: raise ValueError('hash lock not found in reference transform')
    return out, used


def cur_ref():
    """(current T7 bound, token map), or (None, None) before a reference is regenerated."""
    if not (CUR_REF / 'ref_map.json').exists(): return None, None
    j = json.loads((CUR_REF / 'ref_map.json').read_text()); s = gzip.decompress((CUR_REF / 'ref_t7_bound.sv.gz').read_bytes()).decode()
    if sha(s) != j['reference']: raise ValueError('regenerated reference hash')
    return s, j['map']


def rebase_source(src, rm):
    """A reference transform written for 61c902f1 -> the same transform on the regenerated reference: only net names
    change, in one pass.  A token the map does not have refuses."""
    def sub(k, t):
        if t not in rm[k]:
            raise ValueError('reference %s token %s not in the regenerated map' % (k, t))
        return rm[k][t]
    def one(m):
        if m['h']: return 'src_' + sub('hash', m['h'])
        if m['p']: return 'procmux_' + sub('procmux', m['p'])
        if m['e']: return "E+'" + sub('eng', m['e']) + '_Y'
        if m['a']: return (sub('att', m['a']) if m['a'] not in ('0', '1') else m['a']) + '_Y'
        return "'" + sub('att', m['q']) + "'"
    return re.sub(r"src_(?P<h>[0-9a-f]{20})|procmux_(?P<p>\d+)|E\+'(?P<e>\d+)_Y|(?<![\w$])(?P<a>\d+)_Y\b|'(?P<q>\d{2,3})'", one, src)


def load(src):
    g = {'__name__': 's81_ported', '__file__': '<ported>'}; exec(compile(src, '<ported>', 'exec'), g); return g


def close_type(s, ref_s, rm=None):
    rn, tn, nmap = name_map(ref_s, s)
    rep = dict(rsv=tn, before_sha256=sha(s), mapped_nets=len(nmap), steps=[])
    cur = s; t0 = time.time()
    for step in ('pmem', 'pvq', 'land', 'stage'):
        src = REF[step].read_text()
        src, used = port_source(rebase_source(src, rm) if rm else src, tn, nmap, rn)
        g = load(src)
        if step == 'stage': new = g['flip'](cur)[0]
        else: new = g['transform'](cur)[0]
        rep['steps'].append(dict(step=step, renamed_procmux=len(used), before=sha(cur)[:12], after=sha(new)[:12],
                                 removed_lines=sum(1 for l in cur.splitlines() if l not in set(new.splitlines()))))
        cur = new
        print('  %s r%s %s %.0fs' % (step, tn, sha(cur)[:8], time.time() - t0), file=sys.stderr, flush=True)
    rep['after_sha256'] = sha(cur)
    return cur, rep


def _one(args):
    f, ref_s, rm = args; f = Path(f) if f else None
    threading.stack_size(512 * 1024 * 1024); box = {}
    def run():
        try:
            new, rep = close_type(f.read_text() if f else ref_s, ref_s, rm); rep['status'] = 'CLOSED'; box['r'] = (new, rep)
        except Exception as e:
            box['r'] = (None, dict(status='REFUSED', reason=str(e)[:300]))
    t = threading.Thread(target=run); t.start(); t.join(); return (f.name if f else 'T7'), box['r']


def ref_text(path=None):
    s = Path(path).read_text() if path else gzip.decompress(REF_GZ.read_bytes()).decode()
    if sha(s) != T7_ORIG: raise ValueError('reference is not the T7 original 61c902f1')
    return s


def applies(bound_text):
    """True when a bound carries the svc native helper set (the class this event closes)."""
    return all(re.search(r'^\s*' + m + r'\b', bound_text, re.M) for m in NATIVE)


def apply_kit(rtl_dir, ref_s=None, closed=None, form='v2', rm=None):
    """Kit-RTL application (same recipe as the T7 canary3): replace s81p_<type>_bound.sv by its closure and list the
    three capture children right after it in kit_rtl.f / kit_rtl_sim.f / kit_rtl.json files. Writes
    memory_closure.json receipt. `closed` = a precomputed closed bound text (else computed here)."""
    rtl = Path(rtl_dir).resolve(); kr = json.loads((rtl / 'kit_rtl.json').read_text())
    bound = rtl / (kr['bound_module'] + '.sv')
    if not bound.exists(): bound = rtl / ('s81p_%s_bound.sv' % kr['bound_type'])
    s = bound.read_text()
    if (rtl / 'memory_closure.json').exists(): return json.loads((rtl / 'memory_closure.json').read_text())
    if not applies(s): return dict(status='NOT_APPLICABLE')
    if closed is None:
        box = {}
        def run(): box['r'] = close_type(s, ref_s or ref_text(), rm)
        threading.stack_size(512 * 1024 * 1024); t = threading.Thread(target=run); t.start(); t.join()
        if 'r' not in box: raise RuntimeError('closure failed for ' + str(bound))
        closed, rep = box['r']
    else:
        rep = dict(before_sha256=sha(s), after_sha256=sha(closed))
    if form == 'v2':
        rep['v1_after_sha256'] = sha(closed); closed = fit_v2(closed); rep['after_sha256'] = sha(closed)
    idx_kids, idx_macros, drop = {}, {}, []
    if form == 'v2':
        closed, idx_kids, idx_macros, idx_rep = idx_fit(closed, kr['files'], bound)
        if idx_rep:
            rep['v2_after_sha256'] = rep['after_sha256']; rep['after_sha256'] = sha(closed); rep['idx_fit'] = idx_rep
            drop = idx_rep['dropped']
    kids = []
    for c, (p, h) in children(form).items():
        b = (ROOT / p).read_bytes()
        if h and hashlib.sha256(b).hexdigest()[:8] != h: raise ValueError('child hash ' + c)
        (rtl / c).write_bytes(b); kids.append(str(rtl / c))
    for c, t in idx_kids.items(): (rtl / c).write_text(t); kids.append(str(rtl / c))
    macros = {m: MACROS[form].get(m, 0) + idx_macros.get(m, 0) for m in {**MACROS[form], **idx_macros}}
    # macro views the closure instantiates and bind did not see (bind runs before this event): black box in
    # kit_rtl.f / files, behavioural model in kit_rtl_sim.f, lef + libs in hard_macros (same form as bind)
    hm = kr.setdefault('hard_macros', {}); bbs, models = [], []
    for mac in macros:
        if mac in hm: continue
        d = next((ROOT / md / mac for md in ('physical/asap7_memory_macros_v2', 'physical/asap7_memory_macros')
                  if (ROOT / md / mac / (mac + '.lef')).exists()), None)
        if d is None: raise ValueError('MEM: no macro view for ' + mac)
        hm[mac] = dict(dir=str(d), lef=str(d / (mac + '.lef')),
                       libs=[str(d / ('%s_%s.lib' % (mac, c))) for c in ('ff', 'ss', 'tt')],
                       bb=str(d / (mac + '_bb.v')), model=str(d / (mac + '.v')))
        bbs.append(hm[mac]['bb']); models.append(hm[mac]['model'])
    edits = {}
    for fl in ('kit_rtl.f', 'kit_rtl_sim.f'):
        p = rtl / fl
        if not p.exists(): continue
        L = p.read_text().split('\n'); i = L.index(str(bound))
        for x in drop: i -= L.index(x) < i; L.remove(x)
        L[i + 1:i + 1] = kids + (models if fl == 'kit_rtl_sim.f' else bbs); edits[p] = '\n'.join(L)
    for x in drop: kr['files'].remove(x)
    if 'sim_files' in kr: kr['sim_files'] = [x for x in kr['sim_files'] if x not in drop]
    i = kr['files'].index(str(bound)); kr['files'][i + 1:i + 1] = kids + bbs
    if 'sim_files' in kr and str(bound) in kr['sim_files']:
        i = kr['sim_files'].index(str(bound)); kr['sim_files'][i + 1:i + 1] = kids + models
    edits[rtl / 'kit_rtl.json'] = json.dumps(kr, indent=1)
    for p, t in edits.items(): p.write_text(t)
    bound.write_text(closed)
    rep.update(status='APPLIED', event='S81-066 svc memory closure (T7 12605dc2 class port)', bound=str(bound),
               children=kids, form=form, macros_added=macros)
    (rtl / 'memory_closure.json').write_text(json.dumps(rep, indent=1) + '\n')
    return rep


def closure_inputs(form, ref=None):
    """Every repo file the --kit-rtl path needs.  A source tree without ref_1105 would otherwise fall back silently to
    the 61c902f1 reference, whose numbered nets no longer match a current bound."""
    p = list(REF.values()) + [CUR_REF / 'ref_map.json', CUR_REF / 'ref_t7_bound.sv.gz', Path(ref) if ref else REF_GZ]
    p += [ROOT / f for f, _ in children(form).values()]
    if form == 'v2': p.append(ROOT / IDX.FIT_MEM)
    return p


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--ref', help='T7 original bound (sha 61c902f1); default the committed native_parent.sv.gz')
    ap.add_argument('--bound', nargs='+', help='type bound files s81p_<type>_bound.sv')
    ap.add_argument('--out', help='fresh output dir')
    ap.add_argument('--kit-rtl', nargs='+', help='apply in place to kit rtl dirs (kit_rtl.json/.f); with --closed-dir reuse closed bounds')
    ap.add_argument('--closed-dir', help='packet dir (closure.json + closed/<bound>.sv.gz) or a dir of closed bounds; used only when the kit bound sha equals the recorded before sha, else the closure is computed')
    ap.add_argument('--form', choices=('v1', 'v2'), default='v2', help='v2 (default) = right-sized children '
                    '(MEM v2 svc fit); v1 = the 12605dc2 class port with 256x256_m2 / 32x64 masters')
    ap.add_argument('--jobs', type=int, default=1)
    ap.add_argument('--skip-self-check', action='store_true', help='only when the self-check already ran on this tool sha')
    a = ap.parse_args()
    if a.kit_rtl:
        missing = [str(p) for p in closure_inputs(a.form, a.ref) if not p.exists()]
        if missing: sys.exit('closure inputs missing: ' + ' '.join(missing))
    ref_s = ref_text(a.ref); cur_s, rm = cur_ref()
    if a.kit_rtl:
        for d in a.kit_rtl:
            closed = None
            if a.closed_dir:
                rep_j = json.loads((Path(a.closed_dir) / 'closure.json').read_text())
                kr = json.loads((Path(d) / 'kit_rtl.json').read_text()); t = kr['bound_type']
                r = rep_j['types'].get(t, {}); b = Path(d) / ('s81p_%s_bound.sv' % t)
                if r.get('status') == 'CLOSED' and b.exists() and sha(b.read_text()) == r['before_sha256']:
                    cd = Path(a.closed_dir); gz = cd / "closed" / (b.name + ".gz")
                    closed = gzip.decompress(gz.read_bytes()).decode() if gz.exists() else (cd / b.name).read_text()
                    if sha(closed) != r['after_sha256']: sys.exit('closed bound sha mismatch ' + t)
            print(d, json.dumps({k: v for k, v in apply_kit(d, cur_s or ref_s, closed, a.form, rm).items() if k in ('status', 'after_sha256')}), flush=True)
        return
    out = Path(a.out)
    if out.exists(): sys.exit('refusing existing ' + str(out))
    out.mkdir(parents=True)
    jobs = [(str(ref_s_path), ref_s) for ref_s_path in []]
    todo = ([] if a.skip_self_check else [(a.ref, ref_s, None)]) + [(f, cur_s or ref_s, rm) for f in a.bound]
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        res = list(ex.map(_one, todo))
    report = dict(types={})
    if not a.skip_self_check:
        _, (t7, r7) = res.pop(0)
        ok = bool(t7) and r7['after_sha256'].startswith(T7_CLOSURE)
        report['self_check'] = dict(t7=r7.get('after_sha256', r7.get('reason', ''))[:80], expect=T7_CLOSURE, ok=ok)
        print('SELF-CHECK', 'PASS' if ok else 'FAIL', report['self_check']['t7'][:8], flush=True)
        if not ok:
            (out / 'closure.json').write_text(json.dumps(report, indent=1) + '\n'); sys.exit(2)
    for c, (p, h) in children(a.form).items():
        b = (ROOT / p).read_bytes()
        if h and hashlib.sha256(b).hexdigest()[:8] != h: sys.exit('child hash ' + c)
        (out / c).write_bytes(b)
    for name, (new, rep) in res:
        typ = re.sub(r'^s81p_|_bound\.sv$', '', name)
        if new is not None and a.form == 'v2':
            rep['v1_after_sha256'] = rep['after_sha256']; new = fit_v2(new); rep['after_sha256'] = sha(new)
        if new is not None: (out / name).write_text(new)
        report['types'][typ] = rep; print(typ, rep['status'], rep.get('reason', rep.get('after_sha256', '')[:8]), flush=True)
    (out / 'closure.json').write_text(json.dumps(report, indent=1) + '\n')


if __name__ == '__main__':
    main()
