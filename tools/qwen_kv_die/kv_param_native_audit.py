#!/usr/bin/env python3
"""Native parameter audit of an expanded KV die leaf against its CLOSED routed netlist (K.STA.PARAMS).

kv_expand (strict) binds a parameterised leaf only with a frozen opentallas.native_parameter_profile.v1 receipt that
ties the exact evaluated parameters to the exact selected view.  A kit spec or a gate receipt names parameters; it does
not prove the routed view implements them.  This audit proves it:

  audit    gold = the leaf RTL elaborated with the die's evaluated parameters (exact profile values, defaults included)
           gate = the closed run's routed netlist (closed_archive/<kit>/<job>/final/6_final.v) over Liberty cell models
           (ASAP7 RVT functions; _L/_SL cells share the RVT function).  The closed run is identified by the selected
           view's TT/FF Liberty bytes (sha256 equal to the archived final libs), never by name.  State is matched by the
           routed flop instance names (`<reg>$_DFF_*_`): each routed flop exposes its captured state as S__<n>, gold
           aliases the same register bit as S__<n>; every other internal name is hidden.  Yosys then proves
           equiv_make / equiv_simple -seq / equiv_induct / equiv_status -assert over every port and paired state bit.
           Hard macros (no Liberty function) are cut identically on both sides (expose -evert) so their pins are
           compared as ports.
  receipt  turns PROVEN audits whose identity still matches the worktree into frozen receipts + a profiles file for
           OT_KV_PARAMETER_PROFILES.  A NOT PROVEN audit never produces a receipt: it is a re-harden for the tile lane.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import kv_expand_parameters as EP  # noqa: E402
from dft import liberty as lib  # noqa: E402
from dft import netlist as nl  # noqa: E402
from dft.scan_insert import sequential_role  # noqa: E402

YOSYS = Path.home() / '.local/opentallas-tools/yosys-0.68/bin/yosys'
SCHEMA = 'opentallas.native_parameter_profile.v1'
AUDIT_SCHEMA = 'opentallas.kv_param_native_audit.v1'
FF_TYPES = {'$dff', '$adff', '$dffe', '$adffe', '$sdff', '$sdffe', '$sdffce', '$dffsr', '$dffsre', '$aldff',
            '$aldffe'}
FLOP_NAME = re.compile(r'^(?P<base>.+)\$_[A-Z0-9]+_(?:_\d+)?$')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sname(base, used):
    s = 'S__' + re.sub(r'[^A-Za-z0-9_]', '_', base)
    if s in used:
        raise ValueError(f'state name collision {base} -> {s}')
    used.add(s)
    return s


def rvt(cell, cells):
    if cell in cells:
        return cells[cell]
    for suf in ('_ASAP7_75t_L', '_ASAP7_75t_SL', '_ASAP7_75t_SRAM'):
        if cell.endswith(suf) and cell[:-len(suf)] + '_ASAP7_75t_R' in cells:
            return cells[cell[:-len(suf)] + '_ASAP7_75t_R']
    return None


def cell_model(name, cell):
    """Liberty function model; a flop also drives OT_S = the D-polarity captured state."""
    ins = [p for p, i in cell['pins'].items() if i['direction'] == 'input']
    outs = [p for p, i in cell['pins'].items() if i['direction'] == 'output']
    ff, latch = cell.get('ff'), cell.get('latch')
    ports = ins + outs + (['OT_S'] if ff else [])
    L = [f'module {name} ({", ".join(ports)});'] + [f'  input {p};' for p in ins] + [f'  output {p};' for p in outs]
    if ff:
        role = sequential_role(cell)
        v0 = ff['vars'][0]
        ns = role['next_state']
        inv = ns[0] == 'not'
        L += ['  output OT_S;', f'  reg {v0};', f'  assign OT_S = {"~" if inv else ""}{v0};']
        if len(ff['vars']) > 1:
            L.append(f'  wire {ff["vars"][1]} = ~{v0};')
        sens = [f'{"posedge" if role["edge"] == "pos" else "negedge"} {role["clock_pin"]}']
        body = []
        if 'clear' in ff:
            L.append(f'  wire clr__w = {lib.to_verilog(lib.parse_function(ff["clear"]))};')
            sens.append('posedge clr__w')
            body.append(f'if (clr__w) {v0} <= 1\'b0;')
        if 'preset' in ff:
            L.append(f'  wire pre__w = {lib.to_verilog(lib.parse_function(ff["preset"]))};')
            sens.append('posedge pre__w')
            body.append(('else ' if body else '') + f'if (pre__w) {v0} <= 1\'b1;')
        body.append(('else ' if body else '') + f'{v0} <= {lib.to_verilog(ns)};')
        L.append(f'  always @({" or ".join(sens)}) begin ' + ' '.join(body) + ' end')
    elif latch:
        v0 = latch['vars'][0]
        L.append(f'  reg {v0};')
        if len(latch['vars']) > 1:
            L.append(f'  wire {latch["vars"][1]} = ~{v0};')
        L.append(f'  always @* if ({lib.to_verilog(lib.parse_function(latch["enable"]))}) '
                 f'{v0} = {lib.to_verilog(lib.parse_function(latch["data_in"]))};')
    for p in outs:
        f = cell['pins'][p]['function']
        L.append(f'  assign {p} = ' + ("1'bx" if f is None else lib.to_verilog(lib.parse_function(f))) + ';')
    L.append('endmodule')
    return '\n'.join(L)


def prepare_gate(netlist, top, cells, work):
    """Rewrite the routed netlist: every flop instance gets .OT_S(S__<base>); returns (state names, macros)."""
    text = Path(netlist).read_text()
    mod = nl.read_module(Path(netlist), top)
    used, states, models, macros, unnamed = set(), {}, {}, {}, []
    edits = []
    for inst in mod.instances:
        c = rvt(inst.cell, cells)
        if c is None:
            macros[inst.name] = inst.cell
            continue
        models[inst.cell] = c
        if not c.get('ff'):
            if c.get('latch'):
                raise ValueError(f'{inst.name}: latch cell {inst.cell} in routed netlist (unsupported by audit)')
            continue
        m = FLOP_NAME.match(inst.name)
        if not m:
            unnamed.append(inst.name)
            continue
        s = sname(m['base'], used)
        if m['base'] in states:
            raise ValueError(f'two routed flops for state {m["base"]}')
        states[m['base']] = s
        a, b = inst.span
        k = text.index('(', text.index(nl.verilog_name(inst.name).rstrip(), a), b)
        edits.append((k + 1, f'.OT_S({s}), '))
    if unnamed:
        raise ValueError(f'routed flops without a register name: {unnamed[:8]} (+{len(unnamed)})')
    out, last = [], 0
    for k, ins in sorted(edits):
        out += [text[last:k], ins]
        last = k
    out.append(text[last:])
    text = ''.join(out)
    decl = ''.join(f'  wire {s};\n' for s in states.values())
    text = text.replace('endmodule', decl + 'endmodule', 1) if text.count('endmodule') == 1 else None
    if text is None:
        raise ValueError('routed netlist must hold exactly one module')
    (work / 'gate.v').write_text(text)
    (work / 'cells.v').write_text('\n'.join(cell_model(n, c) for n, c in sorted(models.items())) + '\n')
    return states, macros


def gold_states(js, top):
    """register bit -> every public name aliasing its Q (yosys log_signal spelling)."""
    m = js['modules'][top]
    names = {}
    for w, n in m['netnames'].items():
        if w.startswith('$') or n.get('hide_name'):
            continue
        bits, off, upto = n['bits'], n.get('offset', 0), n.get('upto', 0)
        for i, b in enumerate(bits):
            if isinstance(b, int):
                idx = off + (len(bits) - 1 - i if upto else i)
                names.setdefault(b, []).append(w if len(bits) == 1 and off == 0 and not upto else f'{w}[{idx}]')
    regs = {}
    for c in m['cells'].values():
        t = c['type']
        if t not in FF_TYPES and not t.startswith(('$_DFF', '$_SDFF', '$_ALDFF', '$_DFFSR')):
            continue
        for b in c['connections'].get('Q', []):
            if isinstance(b, int):
                regs[b] = names.get(b, [])
    return regs


def run(cmd, work, log, timeout):
    t = time.time()
    p = subprocess.run(cmd, cwd=work, capture_output=True, text=True, timeout=timeout)
    (work / log).write_text(p.stdout + p.stderr)
    return p.returncode, round(time.time() - t, 1)


def audit(a):
    root, work = Path(a.root).resolve(), Path(a.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    params = json.loads(a.params)
    arch = Path(a.archive_run).resolve()
    vd = (root / a.view).resolve()
    res = dict(schema=AUDIT_SCHEMA, module=a.module, rtl=a.rtl, view=a.view, parameters=params,
               expect=a.expect, archive_run=str(arch), proven=False)
    # 1. the selected view IS this closed run: archived final TT/FF Liberty bytes equal the view's
    for c in ('tt', 'ff'):
        v, f = vd / f'{vd.name}_{c}.lib', arch / 'final' / f'{vd.name}_{c}.lib'
        if not f.is_file() or sha(v) != sha(f):
            raise SystemExit(f'{a.module}: view {c} lib does not match closed run {arch}')
    spec = json.loads((arch / 'spec.json').read_text())
    res['closed'] = dict(job=arch.name, commit=(arch / 'commit.txt').read_text().strip(), top=spec['top'],
                         spec_params=spec.get('params', {}), pin_regs=spec.get('pin_regs'),
                         final_v_sha256=sha(arch / 'final/6_final.v'),
                         lib_sha256={c: sha(arch / 'final' / f'{vd.name}_{c}.lib') for c in ('tt', 'ff')})
    defaults = EP.integer_defaults((root / a.rtl).read_text(), a.module)
    closed_eff = dict(defaults, **spec.get('params', {}))
    res['closed_spec_diff'] = {k: [closed_eff.get(k), v] for k, v in params.items() if closed_eff.get(k) != v}
    res['identity'] = EP.artifact_identity(root, a.view, a.rtl)
    srcs = sorted(set(spec['sources']) | {a.rtl})
    res['sources'] = {s: sha(root / s) for s in srcs}
    # 2. gate side
    cells = lib.load_cells(lib.default_asap7_liberty(), work / 'cache')
    states, macros = prepare_gate(arch / 'final/6_final.v', spec['top'] if spec['top'] == vd.name else vd.name,
                                  cells, work)
    res['gate'] = dict(flops=len(states), macros=macros)
    # 3. gold pass 1: elaborate with the exact profile parameters
    chp = ' '.join(f'-chparam {k} {v}' for k, v in sorted(params.items()))
    rd = ' '.join(str(root / s) for s in srcs)
    (work / 'gold1.ys').write_text('\n'.join([
        f'read_verilog -sv -DSYNTHESIS {rd}', f'hierarchy -check -top {a.module} {chp}',
        'proc', 'flatten', 'memory -nomap', 'memory_map', 'opt_clean', f'rename {a.module} gold',
        'write_json gold1.json', 'write_rtlil gold1.il', '']))
    rc, t1 = run([a.yosys, '-q', '-s', 'gold1.ys'], work, 'gold1.log', a.timeout)
    if rc:
        res['error'] = 'gold elaboration failed: ' + (work / 'gold1.log').read_text()[-1500:]
        return res
    regs = gold_states(json.loads((work / 'gold1.json').read_text()), 'gold')
    pair, gold_only = {}, []
    for b, ns in regs.items():
        hit = [n for n in ns if n in states]
        if hit:
            pair[states[hit[0]]] = hit[0]
        else:
            gold_only.append(ns[0] if ns else f'bit{b}')
    gate_only = sorted(set(states) - set(pair.values()))
    res['state'] = dict(gold_regs=len(regs), paired=len(pair), gold_only=len(gold_only), gate_only=len(gate_only),
                        gold_only_sample=sorted(gold_only)[:20], gate_only_sample=gate_only[:20])
    # 4. equivalence: ports + paired state only
    L = ['read_rtlil gold1.il', 'read_verilog -sv cells.v', 'read_verilog gate.v']
    L += [f'rename {spec["top"] if spec["top"] == vd.name else vd.name} gate', 'hierarchy -check', 'proc',
          'flatten gate', 'cd gold']
    for s, n in sorted(pair.items()):
        L += [f'add -wire {s} 1', f'connect -set {s} {n}']
    L += ['cd', 'opt_clean']
    if macros:
        L += ['expose -evert gold gate']
    L += ['select -set keep w:S__* %u i:* o:*', 'rename -hide w:* @keep %d', 'opt_clean', 'async2sync',
          'equiv_make gold gate equiv', 'hierarchy -top equiv', f'equiv_simple -seq {a.seq}', 'equiv_induct',
          'equiv_status', 'equiv_status -assert', '']
    (work / 'equiv.ys').write_text('\n'.join(L))
    rc, t2 = run([a.yosys, '-l', 'equiv.log', '-q', '-s', 'equiv.ys'], work, 'equiv.out', a.timeout)
    log = (work / 'equiv.log').read_text() if (work / 'equiv.log').is_file() else ''
    m = re.findall(r'Found (\d+) \$equiv cells in equiv:\s*\n\s*Of those cells (\d+) are proven and (\d+) are unproven',
                   log)
    res['equiv'] = dict(rc=rc, seconds=[t1, t2], cells=int(m[-1][0]) if m else None,
                        proven_cells=int(m[-1][1]) if m else None, unproven_cells=int(m[-1][2]) if m else None,
                        log_sha256=sha(work / 'equiv.log') if log else None,
                        unproven_sample=re.findall(r'Unproven \$equiv [^\n]*', log)[:20],
                        method=f'equiv_make (ports + routed-flop-name state), equiv_simple -seq {a.seq}, equiv_induct')
    res['proven'] = rc == 0 and bool(m) and m[-1][2] == '0' and int(m[-1][0]) > 0
    if not log:
        res['error'] = (work / 'equiv.out').read_text()[-1500:]
    return res


def receipts(a):
    """PROVEN audits -> frozen receipts + profiles (keyed by RTL module, one evaluated parameter set each)."""
    root, out = Path(a.root).resolve(), Path(a.out)
    profiles, table = {}, {}
    for p in sorted(Path(a.audits).glob('*.audit.json')):
        r = json.loads(p.read_text())
        if r.get('expect') != 'pass':
            continue
        mod = r['module']
        ident = EP.artifact_identity(root, r['view'], r['rtl'])
        ok = r['proven'] and ident == r['identity'] and \
            all(sha(root / s) == h for s, h in r['sources'].items())
        table[mod] = dict(proven=r['proven'], identity_current=ident == r['identity'], closed=r['closed']['job'],
                          spec_diff=r.get('closed_spec_diff'), state=r.get('state'), equiv=r.get('equiv'))
        if not ok:
            continue
        rec = dict(schema=SCHEMA, module=mod, identity=ident, parameters=r['parameters'], native_qualified=True,
                   evidence=dict(method=r['equiv']['method'], closed_job=r['closed']['job'],
                                 closed_commit=r['closed']['commit'], final_v_sha256=r['closed']['final_v_sha256'],
                                 closed_lib_sha256=r['closed']['lib_sha256'], sources=r['sources'],
                                 equiv_cells=r['equiv']['cells'], equiv_log_sha256=r['equiv']['log_sha256'],
                                 state=r['state'], audit=str(p.name), audit_sha256=sha(p)))
        rp = out / 'receipts' / f'{mod}.json'
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(json.dumps(rec, indent=1, sort_keys=True) + '\n')
        rel = str(rp.resolve().relative_to(root))
        profiles[mod] = dict(parameters=r['parameters'], identity=ident, frozen_receipt=dict(path=rel, sha256=sha(rp)))
    (out / 'profiles.json').write_text(json.dumps(profiles, indent=1, sort_keys=True) + '\n')
    (out / 'audit_table.json').write_text(json.dumps(table, indent=1, sort_keys=True) + '\n')
    print(f'{len(profiles)} receipts / {len(table)} audited modules')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    a1 = sp.add_parser('audit')
    a1.add_argument('--root', required=True)
    a1.add_argument('--module', required=True)
    a1.add_argument('--rtl', required=True)
    a1.add_argument('--view', required=True)
    a1.add_argument('--params', required=True, help='JSON object: the full evaluated parameter profile')
    a1.add_argument('--archive-run', required=True, help='closed_archive/<kit>/<job>')
    a1.add_argument('--work', required=True)
    a1.add_argument('--out', required=True)
    a1.add_argument('--expect', choices=('pass', 'fail'), default='pass', help='fail = parameter mutant control')
    a1.add_argument('--seq', type=int, default=2)
    a1.add_argument('--timeout', type=int, default=14400)
    a1.add_argument('--yosys', default=str(YOSYS))
    a2 = sp.add_parser('receipt')
    a2.add_argument('--root', required=True)
    a2.add_argument('--audits', required=True)
    a2.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    if a.cmd == 'receipt':
        return receipts(a)
    r = audit(a)
    Path(a.out).write_text(json.dumps(r, indent=1, sort_keys=True) + '\n')
    ok = r['proven'] == (a.expect == 'pass')
    print(f'{a.module} expect={a.expect}: {"PROVEN" if r["proven"] else "NOT PROVEN"} '
          f'{(r.get("equiv") or {}).get("proven_cells")}/{(r.get("equiv") or {}).get("cells")} '
          f'state {r.get("state", {}).get("paired")}/{r.get("state", {}).get("gold_regs")} -> {"OK" if ok else "UNEXPECTED"}')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
