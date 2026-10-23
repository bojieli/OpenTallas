#!/usr/bin/env python3
"""dv_rtl_kit.py -- a variant-correct full-RTL Verilator kit for an S81-DV die top or a cut slice top (LAYERBENCH-S81,
TOK.DS.BENCH.3, 2026-10-18).

Why: die_port_bind.py --elab-out resolves every module NAME to one file of the tree.  Several rtl/v41rom modules are
defined twice under the same name (ot_v41_rom_elem_w10 in ot_v41_rom_elem_w10.sv and ot_v41_rom_elem_w10_rne_wake_prepare.sv,
ot_v41_bf16_lanes2 in ot_v41_bf16_lanes2.sv and ot_v41_bf16_lanes2_rne_prepare.sv); the elab closure took the base
files, while the frames (col_h9 / col_h10 _l4) are built and benched from tools/s81_dv/frame_bench.f, i.e. the
_rne_* variants (the 10-18 07:38 whole-die probe failed PINNOTFOUND on GRADUAL_RNE / RC / WAKE_REG / ...).  It also
missed memory macros outside rtl/ (ot_sram_1r1w_256x256_m2_r2c2, physical/asap7_memory_macros_v2).

Rule implemented here:
  * sources come from ONE git ref (the die of record, results/fleet_viz/die_sources.json `ref`) via `git show`, plus
    the bind's rtl_extra files (`.../rtl_extra/<sha>/<path>` in port_bind.json rtl_files -> `git show <sha>:<path>`);
  * a module defined more than once is taken from the file named by a PREFER list (--prefer-list: a committed
    bench / flow file list of the master that uses it, e.g. tools/s81_dv/frame_bench.f), then from rtl_extra;
    a module still defined twice with different port sets, or preferred by two lists from different files, FAILS;
  * modules not under rtl/ resolve to physical/asap7_memory_macros_v2/<m>/<m>.v, then physical/asap7_memory_macros/,
    then physical/**/rtl/<m>.sv (never a *_bb.v black box);
  * the ASAP7 cells the die top instantiates (BUFx8 / INVx2 clock-forward cells) get their library function as
    one-line models (cells_used.v, as dv_bind.py writes);
  * every instance parameter override must name a parameter of the master; --strip-param MASTER:PARAM:VALUE removes a
    known die-netlist error (recorded in kit.json `stripped_params`; any other unknown parameter FAILS);
  * the closure follows every instantiated child (die_port_bind.instantiated); an unresolved child FAILS.

Usage:
  dv_rtl_kit.py --ref origin/claude/s81-die6-1018 --port-bind <port_bind.json> --top-v <die.v | slice_top.sv>
                [--top dv_die] --out DIR [--prefer-list tools/s81_dv/frame_bench.f ...] [--strip-param M:P:V ...]
Output: DIR/src/<repo path> (sources), DIR/src/top/<top file>, DIR/kit.f (paths relative to DIR), DIR/kit.json
(file sha256s, variant choices, stripped params, closure size).
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))

CELL_MODELS = {  # ASAP7 7.5T RVT library function (asap7sc7p5t_INVBUF_RVT): Y = A / Y = ~A
    'BUFx8_ASAP7_75t_R': 'module BUFx8_ASAP7_75t_R (input A, output Y); assign Y = A; endmodule',
    'INVx2_ASAP7_75t_R': 'module INVx2_ASAP7_75t_R (input A, output Y); assign Y = ~A; endmodule',
    # S81-LBGAP/G1 hop-0 lane clock gate (asap7sc7p5t_SEQ ICGx4): latch transparent while CLK is low, ANDed with CLK
    'ICGx4_ASAP7_75t_R': ('module ICGx4_ASAP7_75t_R (input CLK, input ENA, input SE, output GCLK); reg en_l; '
                          '/* verilator lint_off COMBDLY */ always_latch if (!CLK) en_l = ENA | SE; /* verilator lint_on COMBDLY */ '
                          'assign GCLK = CLK & en_l; endmodule'),
}
DEFAULT_PREFER = ['tools/s81_dv/frame_bench.f', 'tools/s81_dv/svc_rs/rs_files.sh']
MACRO_DIRS = ['physical/asap7_memory_macros_v2', 'physical/asap7_memory_macros']


def git(repo, *a, binary=False):
    r = subprocess.run(['git', '-C', str(repo), *a], capture_output=True)
    if r.returncode:
        raise SystemExit(f'dv_rtl_kit: git {" ".join(a)} failed: {r.stderr.decode()[:300]}')
    return r.stdout if binary else r.stdout.decode()


def list_files(text, label):
    """repo paths named by a bench / flow file list: a Verilator .f (one path a line) or a bash source list
    (VAR=... assignments expanded, every token ending .sv / .v); -D / +define+ names recorded in list_files.defines"""
    env, out, defs = {}, [], []
    for ln in text.split('\n'):
        m = re.match(r'\s*([A-Z_][A-Z_0-9]*)=([^\s(]+)\s*$', ln)
        if m:
            env[m.group(1)] = m.group(2)
    for ln in text.split('\n'):
        ln = ln.split('#')[0] if label.endswith('.sh') else ln
        if ln.strip().startswith('//'):
            continue
        for k, v in env.items():
            ln = ln.replace('$' + k, v).replace('${' + k + '}', v)
        defs += re.findall(r'(?:-D|\+define\+)([A-Za-z_]\w*)', ln)
        for t in re.findall(r'[\w./-]+\.s?v\b', ln):
            if '/' in t and not t.startswith('-'):
                out.append((t, None))
    list_files.defines = sorted(set(defs))
    return out


def load_dpb(repo, ref):
    """die_port_bind.py AT THE REF (its parser is the bind's parser)"""
    import importlib.util
    import tempfile
    src = git(repo, 'show', f'{ref}:tools/die_port_bind.py')
    p = Path(tempfile.mkdtemp(prefix='dvkit_')) / 'die_port_bind.py'
    p.write_text(src)
    spec = importlib.util.spec_from_file_location('die_port_bind_ref', p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--repo', default=str(ROOT))
    ap.add_argument('--ref', required=True)
    ap.add_argument('--port-bind', required=True)
    ap.add_argument('--bind-snapshot-bytes', action='store_true',
                    help='with --bind-case: a bound file whose executed snapshot bytes differ from (or are absent at) --ref '
                         'is taken from the snapshot (what the die was bound from), recorded in executed_bind_index.snapshot_overrides')
    ap.add_argument('--bind-root-bytes', action='store_true',
                    help='with --bind-case --bind-snapshot-bytes: also index every source file under the recorded rtl_roots '
                         'of the executed snapshot on disk (die_port_bind resolved masters from the whole root, not only '
                         'rtl_files): a root file absent at --ref or with different bytes is taken from the snapshot, '
                         'recorded in executed_bind_index.root_overrides (S81d-TOK 10-22: cap30 u_s_0N hbc_prod / lepw_mu_72)')
    ap.add_argument('--bind-case', help='original executed bind_case.json: honor recorded index roots/final file precedence')
    ap.add_argument('--top-v', required=True)
    ap.add_argument('--top', default=None)
    ap.add_argument('--out', required=True)
    ap.add_argument('--prefer-list', action='append', default=None)
    ap.add_argument('--strip-param', action='append', default=[], help='MASTER:PARAM:VALUE')
    ap.add_argument('--extra-file', action='append', default=[], help='repo path (at the ref) added to the index')
    ap.add_argument('--select', action='append', default=[], metavar='FILE[:SHA256]',
                    help='pin EVERY module defined in FILE (a kit path: rtl/... at the ref or rtl_extra/<sha>/...) to that '
                         'file, over any prefer list, e.g. the GEN-selected physical die source when the strict bind and '
                         'the GEN case resolved a module differently (S81 G9 XS4); optional :SHA256 must match the file')
    a = ap.parse_args(argv)
    repo, ref, out = Path(a.repo), a.ref, Path(a.out).resolve()
    sha = git(repo, 'rev-parse', ref).strip()
    D = load_dpb(repo, ref)
    pb = json.loads(Path(a.port_bind).read_text())
    bind_index = None
    if a.bind_case:
        case_path = Path(a.bind_case)
        command = json.loads(case_path.read_text())['port_bind_cmd']
        assert isinstance(command, list) and command[1].endswith('/tools/die_port_bind.py')
        snapshot = Path(command[1]).parents[1]
        def bind_path(path):
            if not Path(path).is_absolute():
                assert '..' not in Path(path).parts, ('bind path escapes source root', path)
                return str(Path(path))
            m = re.search(r'/rtl_extra/([0-9a-f]{7,40})/(.*)$', str(path))
            if m:
                return f'rtl_extra/{m[1]}/{m[2]}'
            if Path(path).name == 'cells_used.v':
                return 'cells_used.v'
            return str(Path(path).relative_to(snapshot))
        bound_files = [(bind_path(p), p) for p in pb['rtl_files']]
        bound_roots = [bind_path(p).rstrip('/') for p in pb['rtl_roots']]
        original_files = [command[i+1] for i,v in enumerate(command) if v == '--rtl-file']
        assert all(p in pb['rtl_files'] for p in original_files)
        assert [command[i+1] for i,v in enumerate(command) if v == '--define'] == pb.get('defines', [])
        bind_index = dict(bind_case_sha256=hashlib.sha256(case_path.read_bytes()).hexdigest(),
            port_bind_sha256=hashlib.sha256(Path(a.port_bind).read_bytes()).hexdigest(),
            original_command=command, original_explicit_files=original_files,
            recorded_roots=bound_roots, final_ordered_files=[p for p,f in bound_files],
            precedence='actual die_port_bind final files preference: later entry wins; recorded roots only')
    defines = {d: '' for d in pb.get('defines', [])}
    prefer_lists = a.prefer_list if a.prefer_list is not None else DEFAULT_PREFER
    src = out / 'src'
    src.mkdir(parents=True, exist_ok=True)

    # ---- index every module of the ref's rtl/ (+ macro dirs, + physical/**/rtl), parsed with the bind's parser
    names = git(repo, 'ls-tree', '-r', '--name-only', sha, 'rtl', 'physical').split('\n')
    cand = []
    for p in names:
        if not re.search(r'\.s?v$', p) or p.endswith('_bb.v'):
            continue
        base = Path(p).name
        if p.startswith('rtl/'):
            if '/test/' in p or '/tests/' in p or base.startswith('tb_') or base.startswith('tb.'):
                continue
            cand.append(p)
        elif any(p.startswith(d + '/') for d in MACRO_DIRS) or re.match(r'physical/.+/rtl/', p):
            cand.append(p)
    cand += a.extra_file
    if bind_index:
        allowed = set(bind_index['final_ordered_files'])
        cand = [p for p in cand if p in allowed or any(p.startswith(r + '/') for r in bound_roots)]
    texts = {}
    # batch read
    proc = subprocess.run(['git', '-C', str(repo), 'cat-file', '--batch'], input='\n'.join(f'{sha}:{p}' for p in cand).encode(),
                          capture_output=True)
    buf, i = proc.stdout, 0
    for p in cand:
        nl = buf.index(b'\n', i)
        hdr = buf[i:nl].decode().split()
        if len(hdr) < 3 or hdr[1] == 'missing':
            i = nl + 1
            continue
        n = int(hdr[2])
        texts[p] = buf[nl + 1:nl + 1 + n]
        i = nl + 1 + n + 1
    # rtl_extra (other commits) from the bind's file list
    extra = {}
    for f in pb.get('rtl_files', []):
        m = re.search(r'/rtl_extra/([0-9a-f]{7,40})/(.*)$', f)
        if m:
            key = f'rtl_extra/{m.group(1)}/{m.group(2)}'
            texts[key] = git(repo, 'show', f'{m.group(1)}:{m.group(2)}', binary=True)
            extra[key] = m.group(1)
    texts['cells_used.v'] = ('// ASAP7 standard cells used by the S81-DV bound die top (library function models)\n'
                             + '\n'.join(CELL_MODELS.values()) + '\n').encode()
    if bind_index:
        hashes = {}
        for rel, path in bound_files:
            body = Path(path).read_bytes()
            hashes[rel] = hashlib.sha256(body).hexdigest()
            if rel != 'cells_used.v':
                if a.bind_snapshot_bytes and texts.get(rel) != body:
                    # the executed bind read these bytes: the die IS this source (snapshot assembled from several
                    # commits, e.g. cap14 6c6821c87 carries pre-edae62d7b selector files); record both identities
                    bind_index.setdefault('snapshot_overrides', {})[rel] = dict(
                        ref_sha256=hashlib.sha256(texts[rel]).hexdigest() if rel in texts else None,
                        snapshot_sha256=hashlib.sha256(body).hexdigest())
                    texts[rel] = body
                    continue
                assert rel in texts, ('recorded bind input absent at source ref', rel)
                assert texts[rel] == body, ('recorded bind input differs from immutable ref', rel)
        if a.bind_root_bytes:
            assert a.bind_snapshot_bytes, '--bind-root-bytes needs --bind-snapshot-bytes'
            bound_set = {rel for rel, _ in bound_files}
            for root in pb['rtl_roots']:
                rp = Path(root)
                if not rp.is_absolute() or not rp.is_dir():
                    continue
                for f in sorted(rp.rglob('*')):
                    if not f.is_file() or not re.search(r'\.s?v$', f.name) or f.name.endswith('_bb.v'):
                        continue
                    rel = str(f.relative_to(snapshot))
                    if rel in bound_set or '/test/' in rel or '/tests/' in rel or f.name.startswith('tb_') or f.name.startswith('tb.'):
                        continue
                    body = f.read_bytes()
                    if texts.get(rel) != body:
                        bind_index.setdefault('root_overrides', {})[rel] = dict(
                            ref_sha256=hashlib.sha256(texts[rel]).hexdigest() if rel in texts else None,
                            snapshot_sha256=hashlib.sha256(body).hexdigest())
                        texts[rel] = body
        bind_index['original_snapshot_file_sha256'] = hashes
        bind_index['cells_used_projection'] = 'existing functional ASAP7 library models; original bind declarations separately hashed'

    defs = defaultdict(list)         # module -> [(path, Module)]   (parse cache: per ref sha + defines, ~3 min cold)
    import pickle
    ck = Path.home() / '.cache' / 'dv_rtl_kit' / (sha + '_' + hashlib.sha256(repr((sorted(defines), sorted(texts), texts['cells_used.v'])).encode()).hexdigest()[:16] + '.pkl')
    parsed = None
    if ck.exists():
        try:
            parsed = pickle.loads(ck.read_bytes())
        except Exception:
            parsed = None
    if parsed is None:
        parsed = []
        for p, t in texts.items():
            s = t.decode(errors='replace')
            if 'module' not in s:
                continue
            s = D.preprocess(D.strip_comments(s), dict(defines))
            parsed += [(p, mod) for mod in D.parse_modules(s, p)]
        ck.parent.mkdir(parents=True, exist_ok=True)
        try:
            import copyreg  # Module class lives in the ref's die_port_bind: pickle by attributes
            ck.write_bytes(pickle.dumps([(p, m.__dict__) for p, m in parsed]))
        except Exception:
            pass
    else:
        parsed = [(p, _mod(D, d)) for p, d in parsed]
    for p, mod in parsed:
        defs[mod.name].append((p, mod))

    selected, select_rec = set(), []
    for sv in a.select:
        f, _, want = sv.partition(':')
        assert f in texts, ('--select file not in the index (rtl/... at the ref or a bind rtl_extra path)', f)
        got = hashlib.sha256(texts[f]).hexdigest()
        assert not want or got == want, ('--select sha256 mismatch', f, got, want)
        mods = sorted(by_path_sel for by_path_sel, ds in defs.items() if any(q == f for q, _ in ds))
        assert mods, ('--select file defines no module', f)
        selected.add(f)
        select_rec.append(dict(file=f, sha256=got, modules=mods))
    # ---- prefer sources, in priority order: --prefer-list files, the bind table's prefer / rtl_files, then the
    #      sources of every hardened tile (physical/ref_tile/*/spec.json `sources`) whose top is in the closure
    pref_order = []                  # [(path, label)]
    if bind_index:
        # The recorded final files include the actual prefer-list/ref-tile
        # expansion. Do not widen its index with unrelated hardened snapshots.
        pref_order += [(f, 'recorded executed bind final file order')
                       for f in reversed(bind_index['final_ordered_files'])]
    bench_defines = {}
    for L in prefer_lists:
        for f, dfs in list_files(git(repo, 'show', f'{sha}:{L}'), L):
            pref_order.append((f, L))
        bench_defines[L] = list_files.defines
    for f in pb.get('rtl_files', []):
        m = re.search(r'/rtl_extra/([0-9a-f]{7,40})/(.*)$', f)
        if m:
            pref_order.append((f'rtl_extra/{m.group(1)}/{m.group(2)}', 'bind rtl_extra'))
    specs = defaultdict(list)        # tile top -> [(spec path, sources)]
    spec_paths = [p for p in names if re.fullmatch(r'physical/ref_tile/[^/]+/spec\.json', p)]
    proc = subprocess.run(['git', '-C', str(repo), 'cat-file', '--batch'], capture_output=True,
                          input='\n'.join(f'{sha}:{p}' for p in spec_paths).encode())
    buf, i = proc.stdout, 0
    for p in spec_paths:
        nl = buf.index(b'\n', i)
        hdr = buf[i:nl].decode().split()
        if len(hdr) < 3 or hdr[1] == 'missing':
            i = nl + 1
            continue
        n = int(hdr[2])
        try:
            sj = json.loads(buf[nl + 1:nl + 1 + n])
            if sj.get('top') and sj.get('sources'):
                specs[sj['top']].append((p, [x for x in sj['sources'] if isinstance(x, str)]))
        except Exception:
            pass
        i = nl + 1 + n + 1

    by_path = defaultdict(list)
    for nm, ds in defs.items():
        for p, _ in ds:
            by_path[p].append(nm)

    _mt = {}
    conflicts = []

    def mtext(nm, p):
        if (nm, p) not in _mt:
            _mt[(nm, p)] = _mtext(nm, p)
        return _mt[(nm, p)]

    def _mtext(nm, p):
        for q, mod in defs[nm]:
            if q == p:
                return re.sub(r'\s+', ' ', mod.body).strip()
        return None

    def kids(body):
        """instantiated children: die_port_bind.instantiated() misses an instance that follows a generate-block label
        (`begin : g_x  ot_v41_segtree6 #(...) u (...)`; the bind's child closure missed ot_v41_segtree6 / ot_s81sl_xr3 /
        ...), so also take every known module name followed by a parameter list or an instance name"""
        out = set()
        # (also `MASTER `MACRO inst (...)`: a parameter macro between master and instance, e.g. dsdv_gunit `DSDV_GU_MUT)
        for m in re.finditer(r'\b([A-Za-z_]\w*)\s*(?=(?:`\w+\s*)?(?:#\s*\(|[A-Za-z_\\][\w\\]*\s*(?:\[[^\]]*\]\s*)?\())', body):
            if m.group(1) in defs:
                out.add(m.group(1))
        return out

    moddup_resolved = []

    def closure(pref_of):
        problems, choices = [], {}
        moddup_resolved.clear()
        conflicts.clear()

        def pick(name):
            ds = defs.get(name)
            if not ds:
                return None
            if len(ds) == 1:
                return ds[0]
            sel = [d for d in ds if d[0] in selected]
            if sel:
                choices[name] = dict(file=sel[0][0], by='explicit --select', others=[d[0] for d in ds if d[0] != sel[0][0]])
                return sel[0]
            pd = [d for d in ds if d[0] in pref_of]
            if pd:
                best = min(pd, key=lambda d: pref_of[d[0]][0])
                rivals = sorted({d[0] for d in pd if d[0] != best[0] and mtext(name, d[0]) != mtext(name, best[0])})
                if rivals:
                    conflicts.append(f'CONFLICTING_PREFER {name}: {best[0]} ({pref_of[best[0]][1]}) vs '
                                    f'{[(r, pref_of[r][1]) for r in rivals]}')
                choices[name] = dict(file=best[0], by=pref_of[best[0]][1], others=[d[0] for d in ds if d[0] != best[0]])
                return best
            for md in MACRO_DIRS:          # memory macros: _v2 first (the r2c2 generation)
                mm = [d for d in ds if d[0].startswith(md + '/')]
                if mm:
                    choices[name] = dict(file=mm[0][0], by=f'macro dir order {MACRO_DIRS}', others=[d[0] for d in ds if d is not mm[0]])
                    return mm[0]
            bodies = {mtext(name, d[0]) for d in ds}
            if len(bodies) > 1:
                problems.append(f'AMBIGUOUS {name}: defined differently in {[d[0] for d in ds]}; no prefer source names one')
            choices[name] = dict(file=ds[0][0], by='first (identical text)' if len(bodies) == 1 else 'AMBIGUOUS',
                                 others=[d[0] for d in ds[1:]])
            return ds[0]

        seen, todo, files, unresolved, parents = set(), list(masters), [], defaultdict(set), defaultdict(set)
        while todo:
            n = todo.pop()
            if n in seen:
                continue
            seen.add(n)
            d = pick(n)
            if d is None:
                unresolved[n] |= parents[n]
                continue
            if d[0] not in files:
                files.append(d[0])
                # Verilator links EVERY module of a listed file: their children must resolve too
                for nm in by_path[d[0]]:
                    for q, mod in defs[nm]:
                        if q == d[0]:
                            for c in sorted(kids(mod.body) - {nm}):
                                parents[c].add(nm)
                                if c not in seen:
                                    todo.append(c)
            for c in sorted(kids(d[1].body) - {n}):
                parents[c].add(n)
                if c not in seen:
                    todo.append(c)
        for n, ps in sorted(unresolved.items()):
            problems.append(f'UNRESOLVED {n} (instantiated by {sorted(ps)})')
        owner, moddup_same = {}, []
        # TOKc-S81 (10-22, cap14): two closure files may both define a helper (frozen_tap_modules.sv vs eng_rr.sv:
        # dsdv_eng_tap_c).  When the kit's own per-module choice (bind precedence / --select / prefer) names one of
        # them, order that file first (Verilator MODDUP keeps the first) and record it instead of failing.
        files = list(files)
        for _ in range(len(files)):
            moved, first = False, {}
            for i, f in enumerate(files):
                for nm in by_path[f]:
                    if nm in first and first[nm] != f and mtext(nm, first[nm]) != mtext(nm, f) \
                            and choices.get(nm, {}).get('file') == f:
                        files.remove(f); files.insert(files.index(first[nm]), f); moved = True
                        moddup_resolved.append(dict(module=nm, kept=f, shadowed=first[nm]))
                        break
                    first.setdefault(nm, f)
                if moved:
                    break
            if not moved:
                break
        for f in files:                 # a helper module defined in two chosen files: Verilator MODDUP keeps the first
            for nm in by_path[f]:
                if nm in owner and owner[nm] != f:
                    if mtext(nm, owner[nm]) != mtext(nm, f) and choices.get(nm, {}).get('file') != owner[nm]:
                        problems.append(f'MODDUP {nm}: {owner[nm]} and {f} define it differently, both in the closure')
                    else:
                        moddup_same.append(nm)
                owner.setdefault(nm, f)
        return seen, files, problems, choices, pick, moddup_same

    top_text = Path(a.top_v).read_text(errors='replace') if not a.top_v.endswith('.gz') else \
        __import__('gzip').open(a.top_v, 'rt').read()
    nets, tin, tout, insts = D.parse_die(a.top_v if not a.top_v.endswith('.gz') else _ungz(a.top_v, out), a.top)
    # bench-side modules defined in the top file itself (dv_slice_cut dv_flight_sim, S81-LBGAP/G1) need no RTL source
    local_mods = set(re.findall(r'^\s*module\s+(\w+)', top_text, re.M))
    insts = [i for i in insts if i[0] not in local_mods]
    masters = sorted({i[0] for i in insts if i[0] != '__assign__'})
    pref_of = {}
    for k, (p, lab) in enumerate(pref_order):
        pref_of.setdefault(p, (k, lab))
    used_specs, snapshot_differs = {}, []
    for _ in range(4):                  # add the ref_tile sources of the tiles the closure reaches, until stable
        seen, files, problems, choices, pick, moddup_same = closure(pref_of)
        add = {t: specs[t] for t in sorted(seen) if t in specs and t not in used_specs}
        if not add:
            break
        for t, sl in add.items():
            used_specs[t] = [sp for sp, _ in sl]
            for sp, srcs in sorted(sl):
                for f in srcs:
                    m_ = re.match(r'physical/ref_tile/[^/]+/src/(rtl/.*)$', f)
                    if m_:              # a source snapshot inside the tile kit: the rtl/ file if identical, else the snapshot
                        if f in texts and m_.group(1) in texts and texts[f] == texts[m_.group(1)]:
                            f = m_.group(1)
                        elif f in texts:
                            snapshot_differs.append(dict(snapshot=f, rtl=m_.group(1), spec=sp))
                    pref_of.setdefault(f, (len(pref_of) + 1000, sp))
    strip = {}
    for s_ in a.strip_param:
        m_, p_, v_ = s_.split(':')
        strip[(m_, p_)] = v_
    stripped = defaultdict(int)
    for mst, inst, params, _ in insts:
        if mst == '__assign__':
            continue
        d = pick(mst)
        if d is None:
            problems.append(f'MASTER_NO_RTL {mst} ({inst})')
            continue
        for k, v in params.items():
            if k in d[1].params:
                continue
            if strip.get((mst, k)) == v:
                stripped[f'{mst}:{k}={v}'] += 1
            else:
                problems.append(f'PARAM_NOT_IN_RTL {mst}.{k}={v} ({inst}); die-netlist gap (use --strip-param only for a recorded gap)')
    if stripped:
        def _strip(m):
            mst = m.group(2)
            keep = []
            for pm in re.finditer(r'\.(\w+)\s*\(([^()]*)\)', m.group(3)):
                if strip.get((mst, pm.group(1))) == pm.group(2).strip():
                    continue
                keep.append(pm.group(0))
            return f'{m.group(1)}{mst} ' + (f'#({", ".join(keep)}) ' if keep else '')
        top_text = re.sub(r'^(\s*)(\w+)\s+#\((.*?)\)\s+', _strip, top_text, flags=re.M)
    top_text = '\n'.join(ln if len(ln) < 4000 else ln.replace(', ', ',\n      ') for ln in top_text.split('\n'))

    # ---- write
    rec_files = []
    for f in files:
        dst = src / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(texts[f])
        rec_files.append(dict(path=f, sha256=hashlib.sha256(texts[f]).hexdigest(),
                              origin=(extra[f] if f in extra else ('library-function' if f == 'cells_used.v' else sha))))
    # `include files (LB2-S81 L0 10-18: dsdv_svc_rs.sv / dsdv_svc_sx_hrow.sv include *_roles.svh from their own
    # directory; the kit copied only module files -> "Cannot find include file").  Written next to the includer (its
    # directory is already an +incdir), never listed as a compile unit; a missing include is a kit problem.
    includes = []
    tree_names = None
    for f in list(files):
        if f not in texts:
            continue
        for inc in re.findall(r'`include\s+"([^"]+)"', texts[f].decode(errors='ignore')):
            cand = str(Path(f).parent / inc)
            if cand not in texts:
                r_ = subprocess.run(['git', '-C', str(repo), 'show', f'{sha}:{cand}'], capture_output=True)
                if r_.returncode:      # not beside the includer: the one file of that name in the tree (an +incdir)
                    if tree_names is None:
                        tree_names = git(repo, 'ls-tree', '-r', '--name-only', sha).split('\n')
                    hits = [t for t in tree_names if t.endswith('/' + inc) and '/test/' not in t]
                    if len(hits) != 1:
                        problems.append(f'INCLUDE_MISSING {inc} (included by {f}; tree matches {hits[:4]})')
                        continue
                    cand = hits[0]
                    r_ = subprocess.run(['git', '-C', str(repo), 'show', f'{sha}:{cand}'], capture_output=True)
                texts[cand] = r_.stdout
            if cand not in includes and cand not in files:
                includes.append(cand)
                d_ = src / cand
                d_.parent.mkdir(parents=True, exist_ok=True)
                d_.write_bytes(texts[cand])
                rec_files.append(dict(path=cand, sha256=hashlib.sha256(texts[cand]).hexdigest(), origin=sha, include=True))
    tdst = src / 'top' / Path(a.top_v).name.replace('.gz', '')
    tdst.parent.mkdir(parents=True, exist_ok=True)
    tdst.write_text(top_text)
    incs = sorted({str((Path('src') / f).parent) for f in list(files) + includes})
    fl = [f'+incdir+{d}' for d in incs] + [f'+define+{d}' for d in defines] + [f'src/{f}' for f in files] + \
         [str(tdst.relative_to(out))]
    (out / 'kit.f').write_text('\n'.join(fl) + '\n')
    rec = dict(schema='opentallas.s81_dv.rtl_kit.v1', ref=ref, sha=sha, port_bind=a.port_bind, top_v=a.top_v,
               executed_bind_index=bind_index, moddup_resolved=moddup_resolved,
               top=a.top, top_sha256=hashlib.sha256(top_text.encode()).hexdigest(), masters=len(masters),
               modules=len(seen), files=rec_files, prefer_lists=prefer_lists, variant_choices=choices, selected=select_rec, ref_tile_specs_used=used_specs, moddup_identical=sorted(set(moddup_same)), snapshot_differs=snapshot_differs, prefer_conflicts=conflicts, bench_defines_not_applied=bench_defines,
               stripped_params=dict(stripped), defines=sorted(defines), problems=problems,
               verdict='PASS' if not problems else 'FAIL')
    (out / 'kit.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(f"dv_rtl_kit: {rec['verdict']} masters {len(masters)} modules {len(seen)} files {len(files)} "
          f"variants {len(choices)} stripped {dict(stripped)} problems {len(problems)} prefer conflicts {len(conflicts)}")
    for c in conflicts[:20]:
        print('  WARN ' + c[:300])
    for p in problems[:40]:
        print('  ' + p)
    return 0 if not problems else 1


def _mod(D, d):
    m = D.Module.__new__(D.Module)
    m.__dict__.update(d)
    return m


def _ungz(p, out):
    import gzip
    q = out / Path(p).name[:-3]
    q.write_text(gzip.open(p, 'rt').read())
    return str(q)


if __name__ == '__main__':
    sys.exit(main())
