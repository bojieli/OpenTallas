#!/usr/bin/env python3
"""Standard equivalence (LEC) of a KV die leaf: RTL at the exact die parameters vs its CLOSED routed netlist.

OWNER 10-20 09:05: no native parameter proofs.  A leaf receipt is a STANDARD equivalence check of
  gold = the leaf RTL elaborated with the exact parameters the die instantiates (chparam), inside the closed flow's
         own generated shell when the kit used one (ot_pin_regs_wrapper.v / ot_rst_land_wrapper.v: pin registers and
         reset landing stages, core renamed <top>__ot_pr_core exactly as ORFS synthesised it), and
  gate = the closed run's routed netlist 6_final.v over ASAP7 Liberty function models (tap/fill/decap dropped).
No register naming or pairing is used.  Yosys builds a sequential miter (miter -equiv, every output port compared every
cycle); a harness holds the reset port active for --reset-cycles clock edges and only then arms the comparison (the
die's reset protocol), every other input is free on every cycle.  All registers on both sides power up 0
(write_aiger -zinit): datapath registers are unreset by design (owner reset rule: control/valid only), which is fine
here because both sides start from the same state and every free input sequence is checked.  ABC `dprove`
(signal correspondence + induction + SAT sweeping, the standard sequential equivalence engine) proves the armed miter
output constant 0.  Hard macros (no Liberty function) are cut points: their inputs are compared outputs, their outputs
one shared free input on both sides.
Verdict: EQUIVALENT / NOT_EQUIVALENT (with ABC counter-example frame) / UNDECIDED.
A parameter mutant control (--expect fail) must come out NOT_EQUIVALENT.
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
from dft import liberty as lib  # noqa: E402
from dft import netlist as nl  # noqa: E402
import kv_param_native_audit as NA  # noqa: E402  (Liberty cell models, macro cut models)

YOSYS = Path.home() / '.local/opentallas-tools/yosys-0.68/bin/yosys'
ABC = Path.home() / '.local/opentallas-tools/yosys-0.68/bin/yosys-abc'
SCHEMA = 'opentallas.kv_leaf_lec.v1'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(cmd, cwd, log, timeout):
    t = time.time()
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        out, rc = p.stdout + p.stderr, p.returncode
    except subprocess.TimeoutExpired as e:
        out, rc = (e.stdout or b'').decode(errors='replace') if isinstance(e.stdout, bytes) else (e.stdout or ''), 124
    (Path(cwd) / log).write_text(out)
    return rc, round(time.time() - t, 1), out


PORT_RE = re.compile(r'\b(input|output)\s+(?:wire\s+|reg\s+)?(?:\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*)?(\w+)')


def cut_ports(text):
    """[(direction, pin, width)] of a macro blackbox / cut model header."""
    out = [(d_, pin, abs(int(hi) - int(lo)) + 1 if hi else 1) for d_, hi, lo, pin in PORT_RE.findall(text)
           if not pin.startswith(('cut_in_', 'cut_out_'))]
    if not out:
        sys.exit('macro cut: no ports parsed')
    return out


def _pval(v):
    """chparam value: a sized Verilog literal (64'hffddffdeffdcffdc, > 32 bits) verbatim, else an integer"""
    return v if isinstance(v, str) and re.fullmatch(r"\d+'s?[hdbo][0-9a-fA-F_]+", v) else int(v)


def cut_model(cell, bb_text):
    """Cut point of a hard macro: (* keep *) cut_in_<pin> = input; every output = undriven cut_out_<pin>."""
    # KV-AHUB8 10-20: THIS cell's header of a multi-module blackbox; NA.cut_ports reads multi-pin declarations
    mm = re.search(r'\bmodule\s+' + re.escape(cell) + r'\b.*?\bendmodule\b', bb_text, re.S)
    ports = NA.cut_ports(mm.group(0) if mm else bb_text)
    L = [f'// kv_leaf_lec cut model of {cell}', f'module {cell} (',
         ',\n'.join(f'    {d_} wire ' + (f'[{w_ - 1}:0] ' if w_ > 1 else '') + p_ for d_, p_, w_ in ports), ');']
    names = {p_ for _d, p_, _w in ports}
    for d_, p_, w_ in ports:
        r_ = f'[{w_ - 1}:0] ' if w_ > 1 else ''
        if d_ == 'input':
            # sram_gen 1R1W port semantics (ot_sram_*.v: `if (r_ce_in) rd_out <= word_read(r_addr_in)`,
            # `if (w_ce_in) word_write(w_addr_in, wd_in, w_mask_in)`): an address / data / mask pin matters only
            # while its port's chip enable is high, a data bit only where its mask bit is set.  Compare exactly that.
            g = p_[0] + '_ce_in' if p_ not in ('clk', 'r_ce_in', 'w_ce_in') and p_[0] in 'rw' else None
            e = p_
            if g in names:
                e = f'({p_} & {{{w_}{{{g}}}}})'
                if p_ == 'wd_in' and 'w_mask_in' in names:
                    e = f'({p_} & w_mask_in & {{{w_}{{{g}}}}})'
            L += [f'  (* keep *) wire {r_}cut_in_{p_};', f'  assign cut_in_{p_} = {e};']
        else:
            L += [f'  (* keep *) wire {r_}cut_out_{p_};', f'  assign {p_} = cut_out_{p_};']
    return '\n'.join(L + ['endmodule']) + '\n'


def zero_state_model(text):
    """Power-up: the flop's CAPTURED (D-polarity) state OT_S is 0, like every gold register (inverted-storage cells
    such as DFFHQN keep ~D internally, so their internal variable starts at 1)."""
    m = re.search(r'assign OT_S = (~?)(\w+);', text)
    if not m:
        return text
    return re.sub(r'\breg ' + re.escape(m[2]) + ';', f"reg {m[2]} = 1'b{1 if m[1] else 0};", text, count=1)


def prepare_gate(netlist, top, cells, work):
    text = Path(netlist).read_text()
    mod = nl.read_module(Path(netlist), top)
    models, macros, drops, flops = {}, {}, [], 0
    for inst in mod.instances:
        c = NA.rvt(inst.cell, cells)
        if not inst.pins:
            drops.append(inst.span)
            continue
        if c is None:
            macros[inst.name] = inst.cell
            continue
        models[inst.cell] = c
        flops += bool(c.get('ff'))
    out, last = [], 0
    for a_, b_ in sorted(drops):
        out += [text[last:a_]]
        last = b_
    out.append(text[last:])
    (work / 'gate.v').write_text(''.join(out))
    (work / 'cells.v').write_text('\n'.join(zero_state_model(NA.cell_model(n, c)) for n, c in sorted(models.items())) + '\n')
    return mod, macros, flops


def lec(a):
    src, work = Path(a.src).resolve(), Path(a.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    params = json.loads(a.params)
    a.gate = str(Path(a.gate).resolve())
    a.wrapper = str(Path(a.wrapper).resolve()) if a.wrapper else None
    srcs = list(a.source)
    if a.physical_json:
        spec = json.loads(Path(a.physical_json).read_text())['design']
        srcs = [s_['path'] for s_ in spec['sources']]
    srcs = [s_ for s_ in srcs if (src / s_).is_file() or sys.exit(f'missing source {s_} under {src}')]
    res = dict(schema=SCHEMA, module=a.top, parameters=params, expect=a.expect, gate=str(a.gate),
               gate_sha256=sha(a.gate), gate_top=a.gate_top, sources={s_: sha(src / s_) for s_ in srcs},
               wrapper=None, gold_opt=bool(a.gold_opt), reset=dict(port=a.reset, active=a.reset_active, cycles=a.reset_cycles, once=bool(a.reset_once)), verdict=None)
    cells = lib.load_cells(lib.default_asap7_liberty(), work / 'cache')
    gmod, macros, gflops = prepare_gate(a.gate, a.gate_top, cells, work)
    res['gate_stats'] = dict(instances=len(gmod.instances), flops=gflops, macros=macros)
    # macro cut models (same model on both sides)
    cutf = {}
    for cell in sorted(set(macros.values())):
        if cell not in a.macro_cut:
            sys.exit(f'routed netlist has hard macro {cell} with no Liberty function: pass --macro-cut {cell}')
        bb = [s_ for s_ in srcs if s_.endswith('_bb.v') and re.search(r'module\s+' + re.escape(cell) + r'\b',
                                                                       (src / s_).read_text())]
        if len(bb) != 1:
            sys.exit(f'--macro-cut {cell}: need one *_bb.v among the sources, got {bb}')
        f = work / f'{cell}_cut.v'
        f.write_text(cut_model(cell, (src / bb[0]).read_text()))
        cutf[cell] = (f, bb[0])
    cut_bb = {b_ for _f, b_ in cutf.values()}
    rd = [str(src / s_) for s_ in srcs if s_ not in cut_bb] + [str(f) for f, _b in cutf.values()]
    # 1. gold
    G = [f'read_verilog -sv -DSYNTHESIS {" ".join(rd)}']
    # KV-AHUB8 10-20: a sized Verilog literal (64'hffddffdeffdcffdc: the hub's 4 x 16-bit AP_OFS, > 32 bits) goes to chparam
    # verbatim; every other value as an integer
    G += [f'chparam -set {k} {_pval(v)} {a.top}' for k, v in sorted(params.items())]
    if a.wrapper:
        wt = Path(a.wrapper).read_text()
        core = f'{a.gate_top}__ot_pr_core'
        if f'{core} u_ot_pr_core' not in wt:
            sys.exit(f'wrapper {a.wrapper} does not instantiate {core} u_ot_pr_core')
        res['wrapper'] = dict(path=str(a.wrapper), sha256=sha(a.wrapper), core=core)
        G += [f'rename {a.top} {core}', f'read_verilog -sv {a.wrapper}', f'hierarchy -check -top {a.gate_top}']
        gtop = a.gate_top
    else:
        G += [f'hierarchy -check -top {a.top}']
        gtop = a.top
    G += ['proc', 'setattr -unset keep_hierarchy', 'setattr -mod -unset keep_hierarchy', 'flatten',
          'memory -nomap', 'memory_map', 'opt_clean']
    if a.gold_opt:
        # x-init semantics, as synthesis applies them: an UNRESET register (undefined power-up) whose next state is
        # provably constant or itself is replaced by that constant (opt_dff -sat), equal registers are merged.  The
        # same Yosys passes ORFS synthesis ran; every other register keeps its zero power-up.
        G += ['opt -full -sat -share_all', 'opt -full -sat -share_all', 'opt_clean']
    G += [f'rename {gtop} gold', 'write_rtlil gold.il', '']
    (work / 'gold.ys').write_text('\n'.join(G))
    rc, t1, out = run([str(a.yosys), '-q', '-s', 'gold.ys'], work, 'gold.log', a.timeout)
    if rc:
        res['verdict'] = 'ERROR'
        res['error'] = 'gold elaboration failed: ' + out[-1500:]
        return res
    # 2. miter + reset harness
    L = ['read_verilog -sv cells.v'] + [f'read_verilog -sv {f}' for f, _b in cutf.values()]
    L += ['read_verilog gate.v', f'hierarchy -check -top {a.gate_top}', 'proc', 'flatten', f'rename {a.gate_top} gate',
          'read_rtlil gold.il']
    extra_in = []
    for side in ('gold', 'gate'):
        L += ['cd', f'cd {side}']
        for inst, cell in sorted(macros.items()):
            tag = re.sub(r'[^A-Za-z0-9_]', '_', inst)
            for d_, pin, w_ in cut_ports(cutf[cell][0].read_text()):
                if d_ == 'input':
                    L += [f'add -output S__mc_{tag}_{pin} {w_}', f'connect -set S__mc_{tag}_{pin} {inst}.cut_in_{pin}']
                else:
                    L += [f'add -input P__mc_{tag}_{pin} {w_}', f'connect -set {inst}.cut_out_{pin} P__mc_{tag}_{pin}']
                    if side == 'gold':
                        extra_in.append((f'P__mc_{tag}_{pin}', w_))
    L += ['cd', 'setundef -zero gold', 'miter -equiv -flatten' + (' -make_outputs' if a.diagnose else '') + ' gold gate miter']
    outs = []
    for p_ in gmod.ports:
        if gmod.port_dirs[p_] == 'output':
            r_ = gmod.ranges.get(p_)
            outs.append((p_, abs(r_[0] - r_[1]) + 1 if r_ else 1))
    for inst, cell in sorted(macros.items()):
        tag = re.sub(r'[^A-Za-z0-9_]', '_', inst)
        outs += [(f'S__mc_{tag}_{pin}', w_) for d_, pin, w_ in cut_ports(cutf[cell][0].read_text()) if d_ == 'input']
    ports = []
    for p_ in gmod.ports:
        if gmod.port_dirs[p_] == 'input':
            r_ = gmod.ranges.get(p_)
            ports.append((p_, abs(r_[0] - r_[1]) + 1 if r_ else 1))
    ports += extra_in
    if a.reset not in dict(ports) or a.clock not in dict(ports):
        sys.exit(f'clock {a.clock} / reset {a.reset} not input ports of {a.gate_top}')
    act = f"1'b{a.reset_active}"
    dn = [f'd_{p_}' for p_, _w in outs] if a.diagnose else []
    H = ['module ot_lec_top(' + ', '.join([p_ for p_, _w in ports] + ['bad'] + dn) + ');']
    H += [f'  input ' + (f'[{w_ - 1}:0] ' if w_ > 1 else '') + f'{p_};' for p_, w_ in ports]
    H += ['  output bad;', '  reg [7:0] ot_lec_cnt;', f'  wire ot_lec_live = (ot_lec_cnt >= 8\'d{a.reset_cycles});',
          f'  always @(posedge {a.clock}) if (!ot_lec_live) ot_lec_cnt <= ot_lec_cnt + 8\'d1;', '  wire trig;']
    inact = f"1'b{1 - a.reset_active}"
    rexp = inact if a.reset_once else a.reset
    conn = [f'.in_{p_}({p_})' if p_ != a.reset else f'.in_{p_}(ot_lec_live ? {rexp} : {act})' for p_, _w in ports]
    if a.diagnose:
        for p_, w_ in outs:
            r_ = f'[{w_ - 1}:0] ' if w_ > 1 else ''
            H += [f'  output d_{p_};', f'  wire {r_}g_{p_}, t_{p_};', f'  assign d_{p_} = ot_lec_live & |(g_{p_} ^ t_{p_});']
            conn += [f'.gold_{p_}(g_{p_})', f'.gate_{p_}(t_{p_})']
    H += ['  miter u_m(' + ', '.join(conn + ['.trigger(trig)']) + ');', '  assign bad = trig & ot_lec_live;',
          'endmodule', '']
    (work / 'lec_top.v').write_text('\n'.join(H))
    L += ['read_verilog lec_top.v', 'hierarchy -check -top ot_lec_top', 'proc', 'flatten', 'async2sync', 'opt_clean',
          'setundef -undriven -expose', 'techmap', 'opt -fast', 'dffunmap', 'techmap', 'opt_clean',
          'setundef -undriven -expose', 'setundef -zero -init', 'aigmap', 'opt_clean', 'stat', 'write_aiger -zinit -map lec.aim lec.aig', '']
    (work / 'lec.ys').write_text('\n'.join(L))
    rc, t2, out = run([str(a.yosys), '-q', '-s', 'lec.ys'], work, 'lec_yosys.log', a.timeout)
    if rc or not (work / 'lec.aig').is_file():
        res['verdict'] = 'ERROR'
        res['error'] = 'miter build failed: ' + out[-1500:]
        return res
    # vacuity guard: the armed miter output must not be a constant in the written AIG
    with open(work / 'lec.aig', 'rb') as f_:
        h_ = f_.readline().split()
        for _ in range(int(h_[3])):
            f_.readline()
        olit = int(f_.readline().split()[0])
    if olit in (0, 1) and not a.diagnose:
        res['verdict'] = 'ERROR'
        res['error'] = f'vacuous miter: output literal {olit} is constant'
        return res
    # 3. ABC sequential equivalence
    cmd = f'read_aiger lec.aig; print_stats; strash; dprove -v -T {a.abc_timeout}'
    if a.diagnose:
        cmd = 'read_aiger lec.aig; print_stats; strash; bmc3 -a -v -F 60 -T 1800'
    if a.abc_script:
        cmd = a.abc_script
    rc, t3, out = run([str(a.abc), '-c', cmd], work, 'abc.log', a.timeout)
    stats = re.findall(r'(\S+)\s*:\s*i/o\s*=\s*(\d+)\s*/\s*(\d+)\s+lat\s*=\s*(\d+)\s+and\s*=\s*(\d+)', out)
    res['aig'] = dict(pi=int(stats[0][1]), po=int(stats[0][2]), latches=int(stats[0][3]), ands=int(stats[0][4])) if stats else None
    neq = re.search(r'NOT EQUIVALENT|Networks are not equivalent|asserted in frame|Counter-example|(?<!UN)SATISFIABLE', out, re.I)
    if neq:
        v = 'NOT_EQUIVALENT'
        m = re.search(r'(?:frame|Frame)\s+(\d+)', out)
        res['cex_frame'] = int(m[1]) if m else None
    elif re.search(r'Networks are equivalent|Property proved|UNSATISFIABLE', out, re.I):
        v = 'EQUIVALENT'
    else:
        v = 'UNDECIDED'
    res.update(verdict=v, engine=dict(tool='yosys 0.68 miter -equiv + ABC dprove', abc_cmd=cmd, rc=rc,
                                      abc_log_sha256=sha(work / 'abc.log'), seconds=[t1, t2, t3],
                                      abc_tail=out[-1200:]),
               aig_sha256=sha(work / 'lec.aig'), lec_ys_sha256=sha(work / 'lec.ys'), gold_ys_sha256=sha(work / 'gold.ys'))
    res['ok'] = (v == 'EQUIVALENT') if a.expect == 'pass' else (v == 'NOT_EQUIVALENT')
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--src', required=True, help='source tree root (the closed run source checkout)')
    ap.add_argument('--top', required=True, help='RTL module')
    ap.add_argument('--params', required=True, help='JSON: exact die-instantiated parameters')
    ap.add_argument('--source', action='append', default=[])
    ap.add_argument('--physical-json', help='closed route physical.json (design.sources = the synthesised sources)')
    ap.add_argument('--gate', required=True, help='closed routed netlist 6_final.v')
    ap.add_argument('--gate-top', required=True)
    ap.add_argument('--wrapper', help="closed flow's generated shell (ot_pin_regs_wrapper.v / ot_rst_land_wrapper.v)")
    ap.add_argument('--macro-cut', action='append', default=[])
    ap.add_argument('--clock', default='clk')
    ap.add_argument('--reset', default='rst_n')
    ap.add_argument('--reset-active', type=int, choices=(0, 1), default=0)
    ap.add_argument('--reset-cycles', type=int, default=8)
    ap.add_argument('--expect', choices=('pass', 'fail'), default='pass')
    ap.add_argument('--work', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--timeout', type=int, default=4 * 3600)
    ap.add_argument('--abc-timeout', type=int, default=3 * 3600)
    ap.add_argument('--abc-script')
    ap.add_argument('--reset-once', action='store_true', help='boot reset only: reset port held inactive after release')
    ap.add_argument('--gold-opt', action='store_true', help='apply synthesis x-init constant/merge passes to gold')
    ap.add_argument('--diagnose', action='store_true', help='one PO per output port (armed diff); ABC bmc3 -a lists them')
    ap.add_argument('--yosys', default=str(YOSYS))
    ap.add_argument('--abc', default=str(ABC))
    a = ap.parse_args(argv)
    r = lec(a)
    Path(a.out).write_text(json.dumps(r, indent=1, sort_keys=True) + '\n')
    print(f"{a.top} {json.dumps(r['parameters'], sort_keys=True)} expect={a.expect}: {r['verdict']}"
          f" {'OK' if r.get('ok') else 'UNEXPECTED'}")
    return 0 if r.get('ok') else 1


if __name__ == '__main__':
    sys.exit(main())
