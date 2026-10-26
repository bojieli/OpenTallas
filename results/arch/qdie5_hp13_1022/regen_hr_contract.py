#!/usr/bin/env python3
"""QDIE5-HP13 10-22: re-derive results/arch/hp13_corepub39_1021/HR_SOURCE_CONTRACT.json on regenerated cpub39 netlists.

The contract (Codex 20e44d096, no generator committed) names, per cpub39 master, the 72 ARM HR capture registers
(output Q -> hr bit, D == source scheduler Q, both on ck_hr), the HR-valid startup pair, and the 380-bit head bijection
(hr[73+i] == u_hr.rom_cmd bit).  Here every relation is located again in the NEW netlist by hr BIT POSITION (from the
old contract + old netlist) and re-proved structurally on the new netlist (no net name is inherited):
  ARM72:  new hr[k] driven by a DFF Q whose D is a DFF Q or a combinational cone of DFF Qs, all C == the ck_hr alias net;
  HR_valid: same producer -> output pair shape (producer D == 1'b1);
  head380: new hr[k] net == the same rom_cmd bit of u_hr.
usage: regen_hr_contract.py OLD_ROOT_REV NEW_ROOT RECEIPT_JSON   (writes NEW_ROOT/results/arch/hp13_corepub39_1021/HR_SOURCE_CONTRACT.json)
"""
import hashlib, json, re, subprocess, sys
from pathlib import Path
REV, ROOT, RECEIPT = sys.argv[1], Path(sys.argv[2]).resolve(), sys.argv[3]
CP = 'results/arch/hp13_corepub39_1021/HR_SOURCE_CONTRACT.json'
def git(p): return subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{REV}:{p}'], text=True)
def sha(b): return hashlib.sha256(b).hexdigest()
CELL = re.compile(r'(qfd_bmath_dff_\w+) #\(\.ID\(0\)\) (u_\d+)\(([^;]+)\);')
ANY = re.compile(r'(qfd_bmath_\w+) #\(\.ID\(0\)\) (u_\d+)\(([^;]+)\);')
def parse(text):
    hr = re.search(r'^assign hr = \{([^}]*)\};', text, re.M).group(1).split(',')
    hr = list(reversed([x.strip() for x in hr]))                     # hr[0] first
    ff = {}; comb = {}
    for m in ANY.finditer(text):
        ps = dict(re.findall(r'\.(\w+)\(([^()]+)\)', m.group(3)))
        if m.group(1).startswith('qfd_bmath_dff_'): ff[ps['Q']] = dict(instance=m.group(2), **ps)
        else: comb[ps['Y']] = dict(instance=m.group(2), cell=m.group(1), ins=[v for k, v in ps.items() if k != 'Y'])
    COMB[id(ff)] = comb
    ckhr = re.search(r'^assign (n_\d+) = ck_hr;', text, re.M).group(1)
    hrc = re.search(r'ot_qfd_tt_ctlm_static_hr_safe32_native32_1r[^;]*?\\?u_hr\s*\((.*?)\);', text, re.S)
    rom = None
    if hrc:
        rc = re.search(r'\.rom_cmd\(\{([^}]*)\}\)', hrc.group(1))
        if rc: rom = list(reversed([x.strip() for x in rc.group(1).split(',')]))
    return hr, ff, ckhr, rom
COMB = {}
def cone(ff, net, depth=0):
    """register sources of a D net through combinational bmath cells: [(src_reg, comb_depth)]; constants ignored"""
    comb = COMB[id(ff)]
    if net in ff: return [(ff[net], depth)]
    if net not in comb: assert re.fullmatch(r"1'b[01]", net), net; return []
    out = []
    for i in comb[net]['ins']: out += cone(ff, i, depth + 1)
    return out
def reg(r): return {k: r[k] for k in ('instance', 'C', 'D', 'Q', 'R') if k in r}
old_contract = json.loads(git(CP)); new = []
for c in old_contract:
    ohr, off, ock, orom = parse(git(c['rtl'])); nb = (ROOT / c['rtl']).read_bytes(); nhr, nff, nck, nrom = parse(nb.decode())
    assert len(ohr) == len(nhr) == 453 and c['clock_port'] == 'ck_hr'
    pos = {net: k for k, net in enumerate(ohr)}
    rows = []
    for b in c['ARM72']['bit_rows']:
        k = pos[b['output_register']['Q']]
        out = nff[nhr[k]]; srcs = cone(nff, out['D'])
        assert out['C'] == nck and srcs and all(r['C'] == nck for r, _ in srcs), (c['master'], k)
        row = dict(bit=b['bit'], hr_bit=k, output_register=reg(out),
                   source_registers=[dict(reg(r), comb_depth=d) for r, d in srcs])
        if out['D'] in nff: row['source_register'] = reg(nff[out['D']])   # direct capture (pre-SEGCAL form)
        rows.append(row)
    assert len(rows) == 72 and len({r['output_register']['Q'] for r in rows}) == 72
    v = c['HR_valid']; k = pos[v['output']['Q']]
    vo = nff[nhr[k]]; vp = nff[vo['D']]; assert vp['D'] == "1'b1" and vo['C'] == vp['C'] == nck
    bij = {}
    for hk, rb in c['head380']['bit_bijection'].items():
        hk = int(hk); assert orom and ohr[hk] == orom[rb]
        assert nrom and nhr[hk] == nrom[rb], (c['master'], hk, rb)
        bij[str(hk)] = rb
    assert len(bij) == 380
    n = json.loads(json.dumps(c))
    n.update(rtl_sha256=sha(nb), compiled_construction_receipt=RECEIPT,
             compiled_construction_receipt_sha256=sha((ROOT / RECEIPT).read_bytes()),
             regenerated=dict(by='QDIE5-HP13 10-22 regen_hr_contract.py', previous_rtl_sha256=c['rtl_sha256'],
                              method='positional (hr bit) re-derivation on the new netlist + structural re-proof'))
    n['ARM72']['bit_rows'] = rows
    n['ARM72']['proof'] = ('72 distinct HR capture Qs on ck_hr; each D is a combinational cone (QW-SEGCAL xpf_hr = xpf_g[0] ? '
                           'xpf_g : xpf) of ck_hr scheduler register Qs: still exactly 1 register edge source -> HR output')
    n['HR_valid'].update(producer=reg(vp), output=reg(vo))
    n['head380']['bit_bijection'] = bij
    new.append(n)
(ROOT / CP).write_text(json.dumps(new, indent=2) + '\n')
print('HR_SOURCE_CONTRACT regenerated', [(n['master'], n['rtl_sha256'][:12]) for n in new])
