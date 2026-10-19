#!/usr/bin/env python3
"""KV-HOSTCL-CDC2: run the reviewed_gray_fifos structural CDC lint on the actual multi-family HOST-cluster leaves.

Builds a lint spec per leaf from the leaf's generated child file (rtl/qwen_sys/host_cluster_20261017/<top>.v, one file
per child since KVJ-A3 r2 c3) plus
the census source list (results/arch/qwen_split_1014/host_root_cluster/census/elab.ys; SRAM macros as their _bb.v
views through spec.macros). Port families are inferred from the actual elaborated netlist: an input belongs to the
family of the registers/macros that sample it, an output to the family of its driving register; a port sampled by
several families is reported (it is assigned to the first and the lint names the resulting refusal).

    python3 tools/qwen_kv_die/host_cluster/cdc_leaf_lint.py [--json OUT] [top ...]
    python3 tools/qwen_kv_die/host_cluster/cdc_leaf_lint.py --unfix qkd_host_native_qm_debt qkd_hr_ingest_qm
        # MUTANT (expect REFUSED): the leaf binds the shared original instead of its CDC fork

KV-CDC2 (10-18): the leaves bind leaf-local CDC forks (rtl/qwen_sys/host_cluster_cdc_20261018/forks.json) and their
mixed-family output buses are split per family by gen_cluster.py; the pre-fix record (cdc_leaf_lint.json, REFUSED x3)
stays as committed history, the fixed run writes cdc_leaf_lint_cdc2.json.

KV-HROOT-CDC (10-18): runs on main's gray_fifo_cdc_constraints.py with the ported (d) event groups; hard SRAM macros
use main's extension mode (reviewed_gray_fifo_extensions, blackbox view listed in sources, SAT-miter storage proof).
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/ref_tile'))
import cdc_sync_constraints as S          # noqa: E402
import gray_fifo_cdc_constraints as G     # noqa: E402

CLUSTER_DIR = 'rtl/qwen_sys/host_cluster_20261017'   # one generated file per child
FORKS = json.loads((ROOT / 'rtl/qwen_sys/host_cluster_cdc_20261018/forks.json').read_text())
FORKS.pop('_doc', None)
CENSUS = ROOT / 'results/arch/qwen_split_1014/host_root_cluster/census/elab.ys'
SRAM = 'physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1'
CLOCKS = dict(core='ck_core', host='ck_host', ingest='ck_ingest', phy='ck_phy_fam')
# Toggle/ack and level synchronisers of the visibility fence (rtl/qwen_sys/host_20261013/qkd_host_visibility_fence.sv)
FENCE = 'u_rank__u_fence.g_on.'
QM = 'u_rank__u_qm.'
LEAVES = {
    'qkd_hr_cdc_host': dict(families=('core', 'host'), event_diagnostic=True, synchronizers=[
        dict(name='fence_req', src_domain='core', dst_domain='host', source=FENCE + 'req',
             chain=[FENCE + 'rc1', FENCE + 'rc2'], seen=FENCE + 'ack_host', payload=[FENCE + 'snapshot'],
             sync_max_delay_ps=773.333, payload_max_delay_ps=940.0,
             why='toggle request; held snapshot captured into landed/fh when rc2 != ack_host'),
        dict(name='fence_ack', src_domain='host', dst_domain='core', source=FENCE + 'ack_host',
             chain=[FENCE + 'ac1', FENCE + 'ac2'], sync_max_delay_ps=773.333, why='toggle acknowledge'),
        dict(name='fence_fault', src_domain='core', dst_domain='host', source=FENCE + 'fc',
             chain=[FENCE + 'fc1', FENCE + 'fc2'], sync_max_delay_ps=773.333, why='sticky fault level')]),
    'qkd_hr_ingest_qm': dict(families=('core', 'host', 'ingest'), macros=[dict(view=SRAM, count=32, inst='*')],
                             ext='32 ot_sram_1r1w_32x128_m1 qm table macros, each clocked by one family root',
                             synchronizers=[
        dict(name='qm_csr', src_domain='ingest', dst_domain='core', source=QM + 'csr_tgl',
             chain=[QM + 'tg_s[0]', QM + 'tg_s[1]', QM + 'tg_s[2]'], payload=[QM + 'share_i'],
             sync_max_delay_ps=773.333, payload_max_delay_ps=773.333,
             why='toggle-qualified CSR: share_c <= share_i when tg_s[2] != tg_s[1]'),
        dict(name='qm_hov', src_domain='host', dst_domain='ingest', source=QM + 'u_hx.ovf',
             chain=[QM + 'hov_s[0]', QM + 'hov_s[1]'], sync_max_delay_ps=940.0, why='sticky host FIFO overflow level'),
        # rov_s: u_rx write side is tied off (RMW_EN 0), its overflow is constant and the synchroniser folds away.
        # KV-CDC2 fork qkd_hr_native_qm_cdc: the sticky fault leaves clk_i from registers only
        dict(name='qm_fault', src_domain='ingest', dst_domain='core', source=QM + 'f_any_q',
             chain=[QM + 'fs[0]', QM + 'fs[1]'], sync_max_delay_ps=773.333, why='registered sticky fault level -> die clock'),
        dict(name='qm_fault_h', src_domain='ingest', dst_domain='host', source=QM + 'f_any_h',
             chain=[QM + 'fh_s[0]', QM + 'fh_s[1]'], sync_max_delay_ps=940.0,
             why='registered sticky fault level -> host clock (quiet_h)'),
    ]),
    'qkd_hr_cdc_pc': dict(families=('core', 'phy'), synchronizers=None),
}


def all_files(top):
    """Every file sources() scans: the child's generated file, the CDC forks and the census sources."""
    toks = ' '.join(CENSUS.read_text().splitlines()[:2]).split()
    return [f'{CLUSTER_DIR}/{top}.v'] + [v['file'] for v in FORKS.values()] + \
        [t[len('src/'):] for t in toks if t.startswith('src/') and not t.endswith('_bb.v')]


def sources(top, base=ROOT):
    """The census sources plus the CDC forks that define the module closure of `top` (the child's generated file first);
    `base` is the tree whose files are read (a scratch copy for the --unfix mutant)."""
    files = all_files(top)
    body, owner = {}, {}
    for f in files:
        text = re.sub(r'//[^\n]*|/\*.*?\*/', '', (base / f).read_text(), flags=re.S)
        for m in re.finditer(r'\bmodule\s+(\w+)(.*?)\bendmodule\b', text, re.S):
            if m.group(1) not in owner:
                owner[m.group(1)], body[m.group(1)] = f, m.group(2)
    need, todo = set(), [top]
    while todo:
        mod = todo.pop()
        if mod in need:
            continue
        need.add(mod)
        todo += [w for w in set(re.findall(r'\b(\w+)\s*(?:#\s*\(|\w+\s*\()', body[mod])) if w in owner and w != mod]
    used = {owner[m] for m in need}
    macros = [f'{m["view"]}/{Path(m["view"]).name}_bb.v' for m in LEAVES.get(top, {}).get('macros') or []]
    return [f for f in files if f in used] + macros


def macro_files(spec, base=ROOT):
    """Liberty views of the declared macros (the lint reads them; the blackbox is already a source)."""
    return [str(p.relative_to(base)) for m in spec.get('macros', []) for p in (base / m['view']).glob('*.lib')]


def netlist(s, base=ROOT):
    """The lint's own elaboration + netlist of spec s (main's API: extension mode when the leaf has macros)."""
    hashes = G._elaborate_sources(s, base)[0]
    doc = G.elaborate(str(base.resolve()), s['top'], hashes, (), G._yosys(), s.get('cdc_synchronizers') is not None)
    ext = G.extensions(s) is not None
    return doc, (G._netlist(doc, s, G._macro_clock_pins(s, base), True) if ext else G._netlist(doc, s))


def macro_domain(net, c):
    return net.clock_domain.get(c['conn'][c['clock']][0])


def base_spec(top, leaf, inputs, outputs, base=ROOT):
    s = dict(name=top, top=top, kind='tile', sources=sources(top, base), clock='multiple_cts_roots', clock_port='ck_core',
             clock_ports=[CLOCKS[f] for f in leaf['families']], clock_data_paths=G.POLICY,
             clock_relationship=dict(kind=G.RELATIONSHIP_KIND, periods_ps={f: G.FAMILIES[f] for f in leaf['families']}),
             clock_entry_domains={f: dict(ratio=G.family_ratio(f), ports=[CLOCKS[f]], inputs=inputs.get(f, []),
                                          outputs=outputs.get(f, [])) for f in leaf['families']})
    if leaf.get('synchronizers'):
        s['cdc_synchronizers'] = leaf['synchronizers']
    if leaf.get('macros'):
        s['macros'] = leaf['macros']
    if leaf.get('ext'):
        s[G.EXTENSIONS] = dict(why=leaf['ext'])
    return s


def infer_ports(top, leaf):
    """(inputs, outputs, notes): actual port families from the elaborated netlist."""
    s = base_spec(top, leaf, {}, {})
    doc, net = netlist(s)
    m = doc['modules'][top]
    sampled = {}
    for q, f in net.flops.items():
        for pin, bit in (('D', f['d']), ('R', f['r'])):
            for leafbit in net.cone(bit):
                sampled.setdefault(leafbit, set()).add((net.domain(q), pin))
    for c in net.macros.values():
        for pin, bits in c['conn'].items():
            if pin == c['clock'] or c['dirs'][pin] != 'input':
                continue
            for b in bits:
                for leafbit in net.cone(b):
                    sampled.setdefault(leafbit, set()).add((macro_domain(net, c), 'macro'))
    ins, outs, notes = {}, {}, []
    for name, p in m['ports'].items():
        if name in CLOCKS.values():
            continue
        if p['direction'] == 'input':
            fams = sorted({d for b in p['bits'] for d, _ in sampled.get(b, ())})
            if len(fams) > 1:
                notes.append(f'input {name} sampled by families {fams} '
                             f'({sorted({k for b in p["bits"] for k in sampled.get(b, ())})})')
            fam = 'core' if 'core' in fams or not fams else fams[0]
            ins.setdefault(fam, []).append(name)
        else:
            fams = set()
            for b in p['bits']:
                for lb in net.cone(b):
                    if lb in net.flops:
                        fams.add(net.domain(lb))
                    elif net.driver.get(lb, ('',))[0] == 'macro':
                        fams.add(macro_domain(net, net.macros[net.driver[lb][1]]))
            fams = sorted(fams)
            if len(fams) > 1:
                notes.append(f'output {name} driven by families {fams}')
            outs.setdefault(fams[0] if fams else 'core', []).append(name)
    return ins, outs, notes


def lint(top, leaf, ins, outs):
    s = base_spec(top, leaf, ins, outs)
    try:
        record = G.lint(s, ROOT)
        return dict(verdict='PASS', counts=record['counts'],
                    fifos={k: {x: f[x] for x in ('scope', 'module', 'writer', 'reader')} for k, f in record['fifos'].items()},
                    events=record.get('events', {}), macros=record.get('macros', {}), resets=len(record['resets']))
    except G.GrayFifoError as e:
        return dict(verdict='REFUSED', refusal=str(e))


def split_reset(doc, top, port, families):
    """DIAGNOSTIC: give every non-core register whose asynchronous control is the raw `port` bit its own per-family
    copy of the port (as if the wrapper delivered a family-synchronised reset), so the lint reaches the next path."""
    doc = json.loads(json.dumps(doc))
    m = doc['modules'][top]
    bit = m['ports'][port]['bits'][0]
    clk = {m['ports'][CLOCKS[f]]['bits'][0]: f for f in families}
    nxt = 1 + max(b for c in m['cells'].values() for v in c['connections'].values() for b in v if isinstance(b, int))
    added, moved = {}, 0
    for c in m['cells'].values():
        con = c['connections']
        if c['type'].startswith('$_DFF') and con.get('R') == [bit] and clk.get(con['C'][0], 'core') != 'core':
            fam = clk[con['C'][0]]
            if fam not in added:
                added[fam] = (f'{port}__{fam}', nxt)
                m['ports'][added[fam][0]] = dict(direction='input', bits=[nxt])
                nxt += 1
            con['R'] = [added[fam][1]]
            moved += 1
    return doc, {f: n for f, (n, _) in added.items()}, moved


def event_diagnostic(top, leaf, ins, outs):
    """DIAGNOSTIC: the declared event groups alone (Gray source, chain, seen, payload hold, gated capture) on the actual
    netlist, independent of the leaf's other refusals."""
    if not leaf.get('synchronizers'):
        return None
    s = base_spec(top, leaf, ins, outs)
    net = netlist(s)[1]
    role = {}

    def tag(q, r):
        if q in role and role[q] != r:
            raise G.GrayFifoError(f'{net.key(q)} carries two roles {role[q]} / {r}')
        role[q] = r
    try:
        events = G._events(s, net, tag)
        owner = {b: n for n, e in events.items() for b in e['pay']}
        captures = {}
        for q, f in net.flops.items():
            gs = {owner[x] for x in net.cone(f['d']) if x in owner and net.domain(x) != net.domain(q)}
            if gs:
                captures[q] = gs
        G._event_captures(net, events, captures, role, tag)
        return dict(verdict='PASS', counts={k: sum(1 for r in role.values() if r[0] == k)
                                            for k in ('esrc', 'esync1', 'estage', 'epay', 'ecap')},
                    captures=sorted({net.key(q).split('[')[0] for q, r in role.items() if r[0] == 'ecap'}))
    except (G.GrayFifoError, S.CdcError) as e:
        return dict(verdict='REFUSED', refusal=str(e))


# DIAGNOSTIC RTL patches (proposed fixes, never committed RTL): applied to a scratch copy of the sources so the lint can
# report what refuses after the first refusal. Each entry: (file, old, new, extra cdc_synchronizers groups).
PATCHES = {
    # 'qkd_hr_ingest_qm': the f_any_q register is now real RTL (KV-CDC2 fork qkd_hr_native_qm_cdc)
}


def patched(top, leaf, ins, outs, scratch):
    """DIAGNOSTIC: the lint on a scratch copy of the sources with PATCHES[top] applied."""
    import shutil
    s = base_spec(top, leaf, ins, outs)
    groups = list(s.get('cdc_synchronizers') or [])
    for f in s['sources'] + macro_files(s):
        (scratch / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / f, scratch / f)
    applied = []
    for f, old, new, extra in PATCHES.get(top, []):
        text = (scratch / f).read_text()
        if text.count(old) != 1:
            raise SystemExit(f'diagnostic patch no longer applies: {f}')
        (scratch / f).write_text(text.replace(old, new))
        groups += extra
        applied.append(f)
    s['cdc_synchronizers'] = groups
    try:
        record = G.lint(s, scratch)
        return dict(patched=applied, verdict='PASS', counts=record['counts'], events=sorted(record.get('events', {})),
                    macros=record.get('macros', {}), consumes=len(record.get('consumes', {})),
                    constant_chains=record.get('constant_chains', []))
    except G.GrayFifoError as e:
        return dict(patched=applied, verdict='REFUSED', refusal=str(e))


def unfixed(top, orig):
    """MUTANT: the lint of `top` on a scratch copy whose leaf file binds the shared original `orig` instead of its fork."""
    import shutil
    import tempfile
    leaf = LEAVES[top]
    with tempfile.TemporaryDirectory(prefix='ot-cdc-unfix-') as d:
        scratch = Path(d)
        lf = f'{CLUSTER_DIR}/{top}.v'
        text = (ROOT / lf).read_text()
        n = len(re.findall(r'(?m)^\s+' + FORKS[orig]['fork'] + r'\b', text))
        if not n:
            raise SystemExit(f'{top} binds no {FORKS[orig]["fork"]}')
        for f in set(all_files(top)) | set(sources(top)) | {FORKS[orig]['original']}:  # sources(base) scans every file
            (scratch / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / f, scratch / f)
        (scratch / lf).write_text(re.sub(r'(?m)^(\s+)' + FORKS[orig]['fork'] + r'\b', lambda m: m.group(1) + orig, text))
        s = base_spec(top, leaf, {}, {}, scratch)
        for f in macro_files(s):
            (scratch / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / f, scratch / f)
        groups = [g for g in (leaf.get('synchronizers') or []) if not g['name'].startswith('qm_fault')] \
            if orig == 'qkd_host_native_qm_debt' else leaf.get('synchronizers')
        lv = dict(leaf, synchronizers=groups)
        ins, outs, notes = infer_ports(top, leaf)
        s = base_spec(top, lv, ins, outs, scratch)
        try:
            G.lint(s, scratch)
            r = dict(verdict='PASS')
        except G.GrayFifoError as e:
            r = dict(verdict='REFUSED', refusal=str(e))
    return dict(top=top, mutant=f'unfix {orig} ({n} instance(s) of {FORKS[orig]["fork"]} bind the original)', **r)


def run(top):
    """Actual verdict; then DIAGNOSTIC re-runs that drop each refused mixed-family output port from the declaration
    (the lint checks only declared outputs), to expose every further refusal. Diagnostics grant nothing."""
    leaf = LEAVES[top]
    ins, outs, notes = infer_ports(top, leaf)
    out = dict(top=top, notes=notes, inputs=ins, outputs=outs, **lint(top, leaf, ins, outs))
    dropped, diag = [], []
    r = out
    while r['verdict'] == 'REFUSED':
        m = re.match(r'reviewed_gray_fifos output (\w+) \((\w+)\) is combinational from', r['refusal'])
        if not m:
            break
        dropped.append(m.group(1))
        outs = {f: [p for p in v if p != m.group(1)] for f, v in outs.items()}
        r = lint(top, leaf, ins, outs)
        diag.append(dict(dropped_outputs=list(dropped), **r))
    m = re.match(r'reviewed_gray_fifos cross-family asynchronous control (\w+) \(core\) -> ', r.get('refusal', ''))
    if m:
        s = base_spec(top, leaf, ins, outs)
        doc, added, moved = split_reset(netlist(s)[0], top, m.group(1), leaf['families'])
        ins2 = {f: v + ([added[f]] if f in added else []) for f, v in ins.items()}
        for f in added:
            ins2.setdefault(f, [added[f]])
        original = G.elaborate
        G.elaborate = lambda *a, **k: doc
        try:
            r = lint(top, leaf, ins2, outs)
        finally:
            G.elaborate = original
        diag.append(dict(dropped_outputs=list(dropped), split_reset=dict(port=m.group(1), registers=moved), **r))
    if diag:
        out['diagnostic'] = diag
    if PATCHES.get(top) and out['verdict'] == 'REFUSED':
        import tempfile
        with tempfile.TemporaryDirectory(prefix='ot-cdc-leaf-') as scratch:
            out['patched_diagnostic'] = patched(top, leaf, ins, outs, Path(scratch))
    ev = event_diagnostic(top, leaf, ins, outs) if leaf.get('event_diagnostic') else None
    if ev:
        out['event_groups_diagnostic'] = ev
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('tops', nargs='*', default=list(LEAVES))
    ap.add_argument('--json')
    ap.add_argument('--unfix', help='MUTANT: the named leaves bind this shared original instead of its CDC fork')
    a = ap.parse_args()
    if a.unfix:
        out = [unfixed(t, a.unfix) for t in a.tops]
        for r in out:
            print('CDC_LINT_MUTANT', r['top'], r['mutant'], r['verdict'], r.get('refusal', ''))
        if a.json:
            Path(a.json).write_text(json.dumps(out, indent=1, sort_keys=True) + '\n')
        return
    out = [run(t) for t in a.tops]
    for r in out:
        print(r['top'], r['verdict'], r.get('refusal', r.get('counts')))
        for d in r.get('diagnostic', []):
            print('   DIAGNOSTIC without outputs', d['dropped_outputs'], 'split_reset', d.get('split_reset'), d['verdict'],
                  d.get('refusal', d.get('counts')))
        if r.get('patched_diagnostic'):
            print('   DIAGNOSTIC patched RTL:', r['patched_diagnostic'])
        if r.get('event_groups_diagnostic'):
            print('   DIAGNOSTIC event groups alone:', r['event_groups_diagnostic'])
        for n in r['notes']:
            print('   note:', n)
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
