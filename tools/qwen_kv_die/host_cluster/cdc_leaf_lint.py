#!/usr/bin/env python3
"""KV-HOSTCL-CDC2: run the reviewed_gray_fifos structural CDC lint on the actual multi-family HOST-cluster leaves.

Builds a lint spec per leaf from the leaf's generated child file (rtl/qwen_sys/host_cluster_20261017/<top>.v, one file
per child since KVJ-A3 r2 c3) plus
the census source list (results/arch/qwen_split_1014/host_root_cluster/census/elab.ys; SRAM macros as their _bb.v
views through spec.macros). Port families are inferred from the actual elaborated netlist: an input belongs to the
family of the registers/macros that sample it, an output to the family of its driving register; a port sampled by
several families is reported (it is assigned to the first and the lint names the resulting refusal).

    python3 tools/qwen_kv_die/host_cluster/cdc_leaf_lint.py [--json OUT] [top ...]
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
                             synchronizers=[
        dict(name='qm_csr', src_domain='ingest', dst_domain='core', source=QM + 'csr_tgl',
             chain=[QM + 'tg_s[0]', QM + 'tg_s[1]', QM + 'tg_s[2]'], payload=[QM + 'share_i'],
             sync_max_delay_ps=773.333, payload_max_delay_ps=773.333,
             why='toggle-qualified CSR: share_c <= share_i when tg_s[2] != tg_s[1]'),
        dict(name='qm_hov', src_domain='host', dst_domain='ingest', source=QM + 'u_hx.ovf',
             chain=[QM + 'hov_s[0]', QM + 'hov_s[1]'], sync_max_delay_ps=940.0, why='sticky host FIFO overflow level'),
        # rov_s: u_rx write side is tied off (RMW_EN 0), its overflow is constant and the synchroniser folds away.
        # fs: fs[0] <= f_any = (f_code != 0) has logic in front of stage 1 and is left undeclared on purpose.
    ]),
    'qkd_hr_cdc_pc': dict(families=('core', 'phy'), synchronizers=None),
}


def sources(top):
    """The census sources that define the module closure of `top` (the child's generated file first)."""
    toks = ' '.join(CENSUS.read_text().splitlines()[:2]).split()
    files = [f'{CLUSTER_DIR}/{top}.v'] + [t[len('src/'):] for t in toks if t.startswith('src/') and not t.endswith('_bb.v')]
    body, owner = {}, {}
    for f in files:
        text = re.sub(r'//[^\n]*|/\*.*?\*/', '', (ROOT / f).read_text(), flags=re.S)
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
    return [f for f in files if f in used]


def base_spec(top, leaf, inputs, outputs):
    s = dict(name=top, top=top, kind='tile', sources=sources(top), clock='multiple_cts_roots', clock_port='ck_core',
             clock_ports=[CLOCKS[f] for f in leaf['families']], clock_data_paths=G.POLICY,
             clock_relationship=dict(kind=G.RELATIONSHIP_KIND, periods_ps={f: G.FAMILIES[f] for f in leaf['families']}),
             clock_entry_domains={f: dict(ratio=G.family_ratio(f), ports=[CLOCKS[f]], inputs=inputs.get(f, []),
                                          outputs=outputs.get(f, [])) for f in leaf['families']})
    if leaf.get('synchronizers'):
        s['cdc_synchronizers'] = leaf['synchronizers']
    if leaf.get('macros'):
        s['macros'] = leaf['macros']
    return s


def infer_ports(top, leaf):
    """(inputs, outputs, notes): actual port families from the elaborated netlist."""
    s = base_spec(top, leaf, {}, {})
    hashes, _ = G._elaborate_sources(s, ROOT)
    hashes = hashes + G._macro_sources(s, ROOT)
    doc = G.elaborate(str(ROOT), top, hashes, (), G._yosys())
    net = G._netlist(doc, s, {k: v[2] for k, v in G._macro_views(s, ROOT).items()})
    m = doc['modules'][top]
    sampled = {}
    for q, f in net.flops.items():
        for pin, bit in (('D', f['d']), ('R', f['r'])):
            for leafbit in net.cone(bit):
                sampled.setdefault(leafbit, set()).add((net.domain(q), pin))
    for c in net.macros.values():
        for pin, bits in c['inputs'].items():
            for b in bits:
                for leafbit in net.cone(b):
                    sampled.setdefault(leafbit, set()).add((c['domain'], 'macro'))
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
                    elif lb in net.macro_out:
                        fams.add(net.macros[net.macro_out[lb]]['domain'])
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
    hashes = G._elaborate_sources(s, ROOT)[0] + G._macro_sources(s, ROOT)
    net = G._netlist(G.elaborate(str(ROOT), top, hashes, (), G._yosys()), s,
                     {k: v[2] for k, v in G._macro_views(s, ROOT).items()})
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
    'qkd_hr_ingest_qm': [(
        'rtl/qwen_sys/host_20261013/qkd_host_native_qm_debt.sv',
        'else begin fs <= {fs[0], f_any}; fault_c <= fault_c | fs[1]; end',
        'else begin fs <= {fs[0], f_any_q}; fault_c <= fault_c | fs[1]; end\n'
        '    reg f_any_q; always @(posedge clk_i or negedge rn_i) if (!rn_i) f_any_q <= 1\'b0; else f_any_q <= f_any;',
        [dict(name='qm_fault', src_domain='ingest', dst_domain='core', source=QM + 'f_any_q',
              chain=[QM + 'fs[0]', QM + 'fs[1]'], sync_max_delay_ps=773.333, why='registered sticky fault level')])],
}


def patched(top, leaf, ins, outs, scratch):
    """DIAGNOSTIC: the lint on a scratch copy of the sources with PATCHES[top] applied."""
    import shutil
    s = base_spec(top, leaf, ins, outs)
    groups = list(s.get('cdc_synchronizers') or [])
    for f in s['sources'] + [x[0] for x in G._macro_sources(s, ROOT)] + \
            [str(p.relative_to(ROOT)) for m in s.get('macros', []) for p in (ROOT / m['view']).glob('*.lib')]:
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
        hashes = G._elaborate_sources(s, ROOT)[0] + G._macro_sources(s, ROOT)
        doc, added, moved = split_reset(G.elaborate(str(ROOT), top, hashes, (), G._yosys()), top, m.group(1), leaf['families'])
        ins2 = {f: v + ([added[f]] if f in added else []) for f, v in ins.items()}
        for f in added:
            ins2.setdefault(f, [added[f]])
        original = G.elaborate
        G.elaborate = lambda *a: doc
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
    a = ap.parse_args()
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
