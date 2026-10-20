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
           Hard macros (no Liberty function) are the same blackbox (the kit's *_bb.v) on both sides; equiv_make pairs
           the same-named instances and proves their inputs.  Tap/filler/decap cells (no logical pin) are dropped.
           When the closed kit landed its resets in the flow (reset_landing.json), gold is that shell
           (<port>__ot_rl<i> stages, core u_ot_pr_core) around the RTL, so the proof covers shell and core.
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
from collections import defaultdict
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
FLOP_NAME = re.compile(r'^(?P<base>[^$]+)\$_[A-Z][A-Z0-9_]*$')


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
    used, models, macros = set(), {}, {}
    flops, driver, drops = [], {}, []
    for inst in mod.instances:
        c = rvt(inst.cell, cells)
        if not inst.pins:
            drops.append(inst.span)          # tap / filler / decap: no logical pin
            continue
        if c is None:
            macros[inst.name] = inst.cell
            continue
        models[inst.cell] = c
        outs = [p for p, i in c['pins'].items() if i['direction'] == 'output']
        for p in outs:
            for bit in inst.pins.get(p, []):
                driver[bit] = (inst, c, p)
        if c.get('ff'):
            flops.append((inst, c))
        elif c.get('latch'):
            raise ValueError(f'{inst.name}: latch cell {inst.cell} in routed netlist (unsupported by audit)')

    def root(bit):
        # follow non-inverting buffers (function == single input) back to the logical net
        seen = 0
        while bit in driver and seen < 64:
            inst, c, p = driver[bit]
            f = c['pins'][p]['function']
            if c.get('ff') or not f or not re.fullmatch(r'\(?\s*[A-Za-z_]\w*\s*\)?', f.strip()):
                break
            bit = inst.pins[f.strip(' ()')][0]
            seen += 1
        return bit

    def dkey(inst, c):
        role = sequential_role(c)
        return tuple((p, root(inst.pins[p][0]) if inst.pins.get(p) else None)
                     for p in sorted(role['data_pins'])) + (('ns', str(role['next_state'])),)

    states, named, unnamed, edits = {}, {}, [], []
    for inst, c in flops:
        m = FLOP_NAME.match(inst.name)
        if m:
            if m['base'] in named:
                raise ValueError(f'two routed flops for state {m["base"]}')
            named[m['base']] = inst
            states[sname(m['base'], used)] = (m['base'], inst, False)
        else:
            unnamed.append((inst, c))
    by_d = {}
    for base, inst in named.items():
        by_d.setdefault(dkey(inst, rvt(inst.cell, cells)), base)
    orphans = []
    for inst, c in unnamed:
        # flow-inserted replica (ot_prs_* pin-register split): same logical D as a named register
        base = by_d.get(dkey(inst, c))
        if base is None:
            orphans.append(inst.name)
            continue
        states[sname(base + '__rep__' + inst.name, used)] = (base, inst, True)
    if orphans:
        raise ValueError(f'routed flops that are neither named registers nor replicas: {orphans[:8]} (+{len(orphans)})')
    for s_, (_base, inst, _rep) in states.items():
        a_, b_ = inst.span
        k = text.index('(', text.index(nl.verilog_name(inst.name).rstrip(), a_), b_)
        edits.append((k + 1, k + 1, f'.OT_S({s_}), '))
    edits += [(a_, b_, '') for a_, b_ in drops]
    out, last = [], 0
    for k, e, ins in sorted(edits):
        out += [text[last:k], ins]
        last = e
    out.append(text[last:])
    text = ''.join(out)
    decl = ''.join(f'  wire {s_};\n' for s_ in states)
    text = text.replace('endmodule', decl + 'endmodule', 1) if text.count('endmodule') == 1 else None
    if text is None:
        raise ValueError('routed netlist must hold exactly one module')
    (work / 'gate.v').write_text(text)
    (work / 'cells.v').write_text('\n'.join(cell_model(n, c) for n, c in sorted(models.items())) + '\n')
    return {s_: (b_, r_) for s_, (b_, _i, r_) in states.items()}, macros, mod


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


def dup_witnesses(a, work, regs, bit_of, hit):
    """KV-BIND4 10-19 (--dup-witness): a power-up WITNESS for gold-only registers, never an assumption about the netlist.

    The reset base is an existential statement about the RTL: the routed netlist's one power-up state must be admitted by
    SOME RTL power-up state.  Paired registers take the netlist's value.  A gold-only register is a register synthesis
    removed: Yosys itself (opt_dff -sat + opt_merge -share_all on the elaborated gold, the same passes synthesis runs)
    tells which ones are CONSTANT (D is a constant under every state: the owner-accepted shared power-up base, 10-19
    18:16) and which ones are MERGED into a kept twin (identical D / clock / enable / reset after constant propagation).
    Those take the constant resp. the twin's netlist value at step 1, and the witness is ALSO a compared miter output at
    every checked step (gold dup == gate twin, gold const == const), so a wrong classification fails the proof; nothing is
    masked.  Registers the passes leave alone (dead or live) stay FREE.  Returns
    [(gold_name, twin_gold_name | None, const | None, why)]."""
    (work / 'gold2.ys').write_text('\n'.join([
        'read_rtlil gold1.il'] + ['opt_expr -full', 'opt_dff -sat', 'opt_merge -share_all', 'opt_clean'] * 4
        + ['write_json gold2.json', '']))
    rc, _t = run([a.yosys, '-q', '-s', 'gold2.ys'], work, 'gold2.log', a.timeout)
    if rc:
        raise SystemExit('dup-witness: gold opt failed: ' + (work / 'gold2.log').read_text()[-1500:])
    m = json.loads((work / 'gold2.json').read_text())['modules']['gold']
    ffq = set()
    for c in m['cells'].values():
        t = c['type']
        if t in FF_TYPES or t.startswith(('$_DFF', '$_SDFF', '$_ALDFF', '$_DFFSR')):
            ffq.update(b for b in c['connections'].get('Q', []) if isinstance(b, int))
    bit2 = {}
    for w, n in m['netnames'].items():
        if w.startswith('$'):
            continue
        bits, off, upto = n['bits'], n.get('offset', 0), n.get('upto', 0)
        for i, b in enumerate(bits):
            idx = off + (len(bits) - 1 - i if upto else i)
            bit2[w if len(bits) == 1 and off == 0 and not upto else f'{w}[{idx}]'] = b
    kept = {}                            # gold2 Q bit -> a PAIRED gold1 register name aliasing it
    for b_, ns in regs.items():
        if b_ in hit:
            for n in ns:
                if isinstance(bit2.get(n), int) and bit2[n] in ffq:
                    kept.setdefault(bit2[n], ns[0])
    out = []
    for b_, ns in regs.items():
        if b_ in hit or not ns:
            continue
        v = next((bit2[n] for n in ns if n in bit2), None)
        if v in ('0', '1'):
            out.append((ns[0], None, int(v), 'constant (opt_dff -sat)'))
        elif isinstance(v, int) and v in kept:
            out.append((ns[0], kept[v], None, 'merged into ' + kept[v] + ' (opt_merge -share_all)'))
    return out


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
    # 1. the selected view IS this closed run (bytes, not names): either the view's TT/FF Liberty equal the archived
    #    final libs, or (view re-exported from the same routed odb with another interface SDC) the view's raw abstract
    #    LEF -- pinned by abstract.json export_provenance -- equals the archived final LEF and abstract.json's orfs_dir
    #    is that job's route.
    tie = None
    libs = [(vd / f'{vd.name}_{c}.lib', arch / 'final' / f'{vd.name}_{c}.lib') for c in ('tt', 'ff')]
    if all(f.is_file() and sha(v) == sha(f) for v, f in libs):
        tie = 'view TT/FF liberty bytes == closed final liberty'
    else:
        ab = json.loads((vd / 'abstract.json').read_text())
        fl = arch / 'final' / f'{vd.name}.lef'
        same_job = f'/{arch.name}/' in ab.get('orfs_dir', '')
        raw = vd / 'provenance/raw' / f'{vd.name}.lef'
        man = vd / ab.get('export_provenance', {}).get('raw_manifest', 'missing')
        if same_job and fl.is_file() and raw.is_file() and sha(raw) == sha(fl) and \
                man.is_file() and sha(man) == ab['export_provenance'].get('raw_manifest_sha256'):
            tie = 'view raw abstract LEF bytes == closed final LEF; abstract.json orfs_dir = closed job route'
        elif same_job and fl.is_file() and sha(vd / f'{vd.name}.lef') == sha(fl):
            tie = 'view LEF bytes == closed final LEF (libraries re-exported); abstract.json orfs_dir = closed job route'
    if tie is None:
        raise SystemExit(f'{a.module}: view {a.view} is not the closed run {arch}')
    # the closed run's own synthesis record (what ORFS synthesised), not the mutable kit spec
    phys = sorted(arch.glob('run/routes/*/physical.json'))
    if len(phys) != 1:
        raise SystemExit(f'{a.module}: expected one routed physical.json under {arch}, got {phys}')
    spec = json.loads(phys[0].read_text())['design']
    res['closed'] = dict(job=arch.name, commit=(arch / 'commit.txt').read_text().strip(), top=spec['top'],
                         spec_params=spec.get('parameters', {}), physical_json_sha256=sha(phys[0]),
                         synth_sources={s_['path']: s_['sha256'] for s_ in spec['sources']},
                         final_v_sha256=sha(arch / 'final/6_final.v'),
                         lef_sha256=sha(arch / 'final' / f'{vd.name}.lef'), view_tie=tie)
    defaults = EP.integer_defaults((root / a.rtl).read_text(), a.module)
    closed_eff = dict(defaults, **spec.get('parameters', {}))
    res['closed_spec_diff'] = {k: [closed_eff.get(k), v] for k, v in params.items() if closed_eff.get(k) != v}
    res['identity'] = EP.artifact_identity(root, a.view, a.rtl)
    srcs = sorted({s_['path'] for s_ in spec['sources']} | {a.rtl})
    res['sources'] = {s: sha(root / s) for s in srcs}
    res['sources_changed_since_closure'] = sorted(s for s, h in res['closed']['synth_sources'].items()
                                                  if res['sources'].get(s) != h)
    # 2. gate side
    cells = lib.load_cells(lib.default_asap7_liberty(), work / 'cache')
    states, macros, gmod = prepare_gate(arch / 'final/6_final.v', spec['top'],
                                  cells, work)
    res['gate'] = dict(flops=len(states), macros=macros)
    # 3. gold pass 1: elaborate with the exact profile parameters
    rd = ' '.join(str(root / s_) for s_ in srcs)
    bbs = [s_ for s_ in srcs if s_.endswith('_bb.v')]
    rl = json.loads(Path(a.reset_landing).read_text()) if a.reset_landing else None
    if rl and rl.get('enable'):
        # the closed flow's reset landing (physical/common_flow/ot_pin_regs.tcl OT_RST_LAND): every declared reset port
        # lands in `stages` registered stages <port>__ot_rl<i> at the face; the core is u_ot_pr_core.  Gold rebuilds that
        # shell around the RTL at the profile parameters; the proof then covers shell AND core.
        if rl.get('first_copies'):
            raise SystemExit(f'{a.module}: reset_landing first_copies wrapper not modelled by this audit')
        ck, st = rl['clock'], int(rl['stages'])
        W = ['module ot_kvp_wrap (' + ', '.join(gmod.ports) + ');']
        for p_ in gmod.ports:
            r_ = gmod.ranges.get(p_)
            W.append(f'  {gmod.port_dirs[p_]} ' + (f'[{r_[0]}:{r_[1]}] ' if r_ else '') + f'{p_};')
        conn = {p_: p_ for p_ in gmod.ports}
        for r_ in rl['reset_ports']:
            prev = r_
            for i in range(st):
                W += [f'  (* keep *) reg {r_}__ot_rl{i};', f'  always @(posedge {ck}) {r_}__ot_rl{i} <= {prev};']
                prev = f'{r_}__ot_rl{i}'
            conn[r_] = prev
        W.append(f'  {a.module} #(' + ', '.join(f'.{k}({v})' for k, v in sorted(params.items())) + ') u_ot_pr_core (' +
                 ', '.join(f'.{p_}({c_})' for p_, c_ in conn.items()) + ');')
        W.append('endmodule')
        (work / 'gold_wrap.v').write_text('\n'.join(W) + '\n')
        rd += ' ' + str(work / 'gold_wrap.v')
        gtop, chp = 'ot_kvp_wrap', ''
        res['wrapper'] = dict(kind='reset_landing', stages=st, clock=ck, reset_ports=rl['reset_ports'],
                              reset_landing_sha256=sha(a.reset_landing))
    else:
        gtop, chp = a.module, ' '.join(f'-chparam {k} {v}' for k, v in sorted(params.items()))
    (work / 'gold1.ys').write_text('\n'.join([
        f'read_verilog -sv -DSYNTHESIS {rd}', f'hierarchy -check -top {gtop} {chp}',
        'proc', 'setattr -unset keep_hierarchy', 'setattr -mod -unset keep_hierarchy', 'flatten', 'memory -nomap',
        'memory_map', 'opt_clean', f'rename {gtop} gold',
        'write_json gold1.json', 'write_rtlil gold1.il', '']))
    rc, t1 = run([a.yosys, '-q', '-s', 'gold1.ys'], work, 'gold1.log', a.timeout)
    if rc:
        res['error'] = 'gold elaboration failed: ' + (work / 'gold1.log').read_text()[-1500:]
        return res
    regs = gold_states(json.loads((work / 'gold1.json').read_text()), 'gold')
    ge = observe_ge_cells(a.observe_ge, work / 'gold1.il')
    bit_of = {}
    for b_, ns in regs.items():
        for n in ns:
            bit_of[n] = b_
    # older ORFS flattening spells hierarchy with '/', Yosys flatten with '.' (KV-PARAMS ep6 run copy, 10-19 12:30)
    pair = {s_: base.replace('/', '.') for s_, (base, _rep) in states.items() if base.replace('/', '.') in bit_of}
    hit = {bit_of[b_] for b_ in pair.values()}
    gold_only = sorted(ns[0] if ns else f'bit{b_}' for b_, ns in regs.items() if b_ not in hit)
    gate_only = sorted(base for s_, (base, _rep) in states.items() if s_ not in pair)
    res['gate']['replicas'] = sum(1 for _b, r in states.values() if r)
    res['state'] = dict(gold_regs=len(regs), paired=len(pair), gold_only=len(gold_only), gate_only=len(gate_only),
                        gold_only_sample=gold_only[:20], gate_only_sample=gate_only[:20])
    # 4. equivalence: ports + paired state only
    # --macro-model CELL=MODEL.v (KV-PARAMS2 10-19, PV slice SRAM): a hard macro with no Liberty function gets the SAME
    # stateful SAT model on both sides instead of the blackbox; its array words and read register become paired state
    # (shared arbitrary initial memory, never zero-filled).  MODEL must define module CELL with reg arrays `arr` and
    # registered output `rd_out` (sram_gen behaviour); the words / read register are paired by instance name.
    mm = dict(x.split('=', 1) for x in (a.macro_model or []))
    mstate = []
    if mm:
        unknown = sorted(set(mm) - set(macros.values()))
        if unknown:
            raise SystemExit(f'--macro-model for cells not in the routed netlist: {unknown}')
        bbs_r = [b_ for b_ in bbs if not any(re.search(r'module\s+' + re.escape(c) + r'\b', (root / b_).read_text())
                                             for c in mm)]
        res['macro_models'] = {c: dict(path=f, sha256=sha(f)) for c, f in mm.items()}
        for inst, cell in sorted(macros.items()):
            if cell in mm:
                m_ = re.search(r'reg\s*\[\s*(\d+)\s*:\s*0\s*\]\s*arr\s*\[\s*0\s*:\s*(\d+)\s*\]', Path(mm[cell]).read_text())
                wbits, words = int(m_[1]) + 1, int(m_[2]) + 1
                tag = re.sub(r'[^A-Za-z0-9_]', '_', inst)
                mstate += [(f'S__mm_{tag}_arr_{k}', f'{inst}.arr[{k}]', wbits) for k in range(words)]
                mstate.append((f'S__mm_{tag}_rd_out', f'{inst}.rd_out', wbits))
        pre = (['read_verilog -sv cells.v'] + [f'read_verilog -sv {root / b_}' for b_ in bbs_r]
               + [f'read_verilog -sv {f}' for f in mm.values()] + ['proc', 'memory -nomap', 'memory_map', 'opt_clean'])
        L = pre + ['read_verilog gate.v', f'rename {spec["top"]} gate', 'hierarchy -check -top gate', 'proc',
                   'read_rtlil gold1.il', 'flatten gate gold', 'cd gold']
        res['macro_state_pairs'] = len(mstate)
    else:
        L = ['read_verilog -sv cells.v'] + [f'read_verilog -sv {root / b_}' for b_ in bbs] + ['read_verilog gate.v', f'rename {spec["top"]} gate', 'hierarchy -check -top gate',
             'proc', 'flatten gate', 'read_rtlil gold1.il', 'cd gold']
    if mstate:
        for side in ('gold', 'gate'):
            L += ['cd', f'cd {side}'] + [x for s_, w_, n_ in mstate for x in (f'add -wire {s_} {n_}', f'connect -set {s_} {w_}')]
        L += ['cd', 'cd gold']
    for s, n in sorted(pair.items()):
        L += [f'add -wire {s} 1', f'connect -set {s} {n}']
    wit_lines, wit_sets, wit_rec, wit_at = [], [], [], len(L)
    if a.dup_witness and a.reset_base:
        swire = {}
        for s_, n_ in pair.items():
            if not states[s_][1]:
                swire.setdefault(bit_of[n_], s_)
        ws = dup_witnesses(a, work, regs, bit_of, hit)
        gate_side = []
        for i, (nm, twin, cst, why) in enumerate(ws):
            if a.observe_zero_regex and re.search(a.observe_zero_regex, nm):
                continue        # already an observe-zero comparison with its tied-0 power-up value
            if cst is None and bit_of[twin] not in swire:
                continue        # twin is a flow replica: stays free
            w_ = f'S__wit_{i:04d}'
            wit_lines += [f'add -wire {w_} 1', f'connect -set {w_} {nm}']
            gate_side += [f'add -wire {w_} 1', f"connect -set {w_} " + (f"1'{cst}" if cst is not None else swire[bit_of[twin]])]
            wit_sets.append(f'-set-at 1 gold.{w_} gate.{w_}')
            wit_rec.append(dict(gold=nm, witness=(twin if cst is None else f"1'{cst}"), why=why))
        if gate_side:   # the gate twin is ALSO a compared output at every checked step: dup == kept flop is proven
            wit_lines += ['cd', 'cd gate'] + gate_side + ['cd', 'cd gold']
        res['dup_witness'] = dict(count=len(wit_rec), merged=sum(1 for w in wit_rec if w['why'].startswith('merged')),
                                  constant=sum(1 for w in wit_rec if w['why'].startswith('constant')),
                                  gold2_log_sha256=sha(work / 'gold2.log'),
                                  gold_only=len(gold_only), unwitnessed=len(gold_only) - len(wit_rec), list=wit_rec)
    # KV-PARAMS2 10-19 joint mode: source registers that synthesis removed as constants (e.g. the adder's unreset
    # *_err[1] metadata chain x->s1->t->w->s2->u, only E_NONE/E_NONFINITE upstream) are no invariant of an arbitrary
    # induction state.  --observe-zero-regex names gold-only registers whose ZERO value is then an extra comparison
    # (gold reg == gate 1'b0): proven together with every original comparison by the induction AND the reset base,
    # never assumed.  The resolved list is recorded.
    obs = sorted(n for n in gold_only if a.observe_zero_regex and re.search(a.observe_zero_regex, n))
    for i, n in enumerate(obs):
        L += [f'add -wire S__proof_meta_{i:03d} 1', f'connect -set S__proof_meta_{i:03d} {n}']
    if obs:
        L += ['cd', 'cd gate'] + [x for i in range(len(obs)) for x in
                                  (f'add -wire S__proof_meta_{i:03d} 1', f"connect -set S__proof_meta_{i:03d} 1'0")]
    # --observe-ge: a reachable-state RANGE invariant (e.g. a 40-deep FIFO pointer never holds 40..63): a $ge cell added
    # to the elaborated gold (gold1.il; its sha is recorded) whose output is proven ZERO the same joint way.
    for i, w_ in enumerate(ge):
        L += [f'add -wire S__proof_ge_{i:03d} 1', f'connect -set S__proof_ge_{i:03d} {w_["wire"]}']
    if ge:
        L += ['cd', 'cd gate'] + [x for i in range(len(ge)) for x in
                                  (f'add -wire S__proof_ge_{i:03d} 1', f"connect -set S__proof_ge_{i:03d} 1'0")]
    res['observe_zero'] = dict(regex=a.observe_zero_regex, signals=obs, ge=ge,
                               gold1_il_sha256=sha(work / 'gold1.il')) if (a.observe_zero_regex or ge) else None
    L += ['cd', 'setattr -set keep 1 w:S__*']
    L += ['select -set keep w:S__* i:* o:*', 'rename -hide w:* @keep %d']
    prelude = list(L)
    if wit_lines:   # base only: the gold-side witness wires (gold has no gate twin; equiv_make never sees them)
        prelude = prelude[:wit_at] + wit_lines + prelude[wit_at:]
    L += ['async2sync',
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
    if a.reset_base and res['proven']:
        res['proven'] = False
        # observe-zero metadata registers have no routed flop: the netlist implements them as the constant 0, so the ONE
        # power-up state gives the RTL's unreset (X) register that value at step 1 (the gate side of S__proof_meta is
        # 1'0).  Range predicates (--observe-ge) are NOT paired: they would restrict real routed power-up states.
        res['base'] = reset_base(a, work, prelude, states, pair, [s_ for s_, _w, _n in mstate]
                                 + [f'S__proof_meta_{i:03d}' for i in range(len(obs))], wit_sets)
        res['proven'] = res['base']['proven']
        res['equiv']['method'] += (f'; reset base: {a.reset_base} {a.reset_port}={a.reset_active} edges, paired initial '
                                   f'state, steps {a.reset_base + 1}..{a.reset_base + 4} (miter, sat -verify)')
    return res


def observe_ge_cells(specs, il):
    """'WIRE:LSB:WIDTH:CONST' -> a $ge cell (WIRE[LSB+:WIDTH] >= CONST) appended to module gold of gold1.il."""
    if not specs:
        return []
    text = il.read_text()
    k = text.index('module \\gold\n')
    e = text.index('\nend\n', k)
    add, out = [], []
    for i, sp in enumerate(specs):
        wire, lsb, wid, const = sp.rsplit(':', 3)
        lsb, wid, const = int(lsb), int(wid), int(const)
        if not re.search(r'^  wire width \d+ (?:offset \d+ )?' + re.escape('\\' + wire) + r'$', text[k:e], re.M):
            raise SystemExit(f'--observe-ge: gold has no wire {wire}')
        name = f'kvp_obs_ge_{i:03d}'
        add += [f'  wire width 1 \\{name}', f'  cell $ge $kvp_obs_ge_cell_{i:03d}', '    parameter \\A_SIGNED 0',
                f'    parameter \\A_WIDTH {wid}', '    parameter \\B_SIGNED 0', f'    parameter \\B_WIDTH {wid}',
                '    parameter \\Y_WIDTH 1', f'    connect \\A \\{wire} [{lsb + wid - 1}:{lsb}]',
                f"    connect \\B {wid}'{format(const, '0' + str(wid) + 'b')}", f'    connect \\Y \\{name}', '  end']
        out.append(dict(spec=sp, wire=name, predicate=f'{wire}[{lsb + wid - 1}:{lsb}] >= {const}'))
    il.write_text(text[:e] + '\n' + '\n'.join(add) + text[e:])
    return out


def reset_base(a, work, prelude, states, pair, extra=(), witness=()):
    """KV-PARAMS2 10-19: the reset base the induction needs (equiv_induct assumes its comparisons for 3 steps).

    The chip has ONE power-up state, the routed netlist's.  The RTL admits that state on the same registers, so every
    paired NON-replica register is equal at step 1 (gold.S__x == gate.S__x); gold-only registers (incl. observe-zero
    metadata) and flow replicas stay FREE (a replica may power up unlike its master).  Independent gold/gate power-up
    words make two copies of the same unreset datapath disagree until it flushed -- RTL-vs-itself fails that way too
    (kv-native-comparator-replay 2c2bd3c92: 213 u_cc bits, kp_r 7 stages deep, 6 reset edges) -- so that formulation
    proves nothing about the netlist.  Every original comparison and observation stays a miter output; the reset port
    is held active for N target edges, all other inputs arbitrary, steps N+1..N+4 checked."""
    n = a.reset_base
    paired = sorted(s_ for s_ in pair if not states[s_][1]) + list(extra)   # extra: macro-model array/read state
    sets = ' '.join(f'-set-at {i} in_{a.reset_port} {a.reset_active}' for i in range(1, n + 1))
    sets += ' ' + ' '.join(f'-set-at 1 gold.{s_} gate.{s_}' for s_ in paired)
    if witness:
        sets += ' ' + ' '.join(witness)
    B = prelude + ['async2sync', 'expose gold/w:S__* gate/w:S__*', 'miter -equiv -flatten -make_assert gold gate miter',
                   'hierarchy -top miter', 'opt_clean',
                   f'sat -seq {n + 4} -prove-asserts -prove-skip {n} -set-def-inputs {sets} -dump_json base_cex.json '
                   '-verify', '']
    (work / 'base.ys').write_text('\n'.join(B))
    rc, t = run([a.yosys, '-l', 'base.log', '-q', '-s', 'base.ys'], work, 'base.out', a.timeout)
    log = (work / 'base.log').read_text() if (work / 'base.log').is_file() else ''
    ok = rc == 0 and 'no model found: SUCCESS!' in log
    return dict(rc=rc, seconds=t, proven=ok, reset_edges=n, reset_port=a.reset_port, reset_active=a.reset_active,
                checked_steps=[n + 1, n + 4], paired_initial=len(paired), witnesses=len(witness), free_replicas=sum(1 for s_ in pair if states[s_][1]), macro_state=len(extra),
                log_sha256=sha(work / 'base.log') if log else None,
                cex=str(work / 'base_cex.json') if (work / 'base_cex.json').is_file() else None,
                error=None if log else (work / 'base.out').read_text()[-1500:])


def receipts(a):
    """PROVEN audits -> frozen receipts + profiles (keyed by RTL module, one evaluated parameter set each)."""
    root, out = Path(a.root).resolve(), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
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
                                 closed_lef_sha256=r['closed']['lef_sha256'], view_tie=r['closed']['view_tie'], sources=r['sources'],
                                 equiv_cells=r['equiv']['cells'], equiv_log_sha256=r['equiv']['log_sha256'],
                                 state=r['state'], audit=str(p.name), audit_sha256=sha(p),
                                 observe_zero=r.get('observe_zero'), reset_base=r.get('base')))
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
    a1.add_argument('--reset-landing', help="the kit's reset_landing.json at the closed commit (flow landing shell)")
    a1.add_argument('--expect', choices=('pass', 'fail'), default='pass', help='fail = parameter mutant control')
    a1.add_argument('--seq', type=int, default=2)
    a1.add_argument('--observe-zero-regex', help='gold-only registers proven ZERO jointly (see audit())')
    a1.add_argument('--macro-model', action='append', default=[], help='CELL=MODEL.v stateful SAT model, both sides')
    a1.add_argument('--observe-ge', action='append', default=[],
                    help="WIRE:LSB:WIDTH:CONST gold range predicate proven ZERO jointly (repeatable)")
    a1.add_argument('--reset-base', type=int, default=0, help='N: paired-initial reset base after N reset edges')
    a1.add_argument('--dup-witness', action='store_true',
                    help='reset base: merged-duplicate / constant gold-only registers take their kept twin / constant')
    a1.add_argument('--reset-port', default='rst_n')
    a1.add_argument('--reset-active', type=int, choices=(0, 1), default=0)
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
