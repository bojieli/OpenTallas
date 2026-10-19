#!/usr/bin/env python3
"""KV-INTEG/KITS-A 2026-10-18: lockstep bench of a singleton static tile KIT TOP (qkd_kvs_ctl / _attn / _emb generated
with OT_KV_TILE_KITS=1: clock ports ck/hck, hard children without #()) against the DIE-BOUND tile of the same design point
(OT_KV_TILE_KITS unset: one '<child>__ck' port per child, every one on the same die trunk clk_core_c).  Both tiles are
regenerated here from tools/qwen_kv_die/kv_static_die.py (the bench never reads a stale tile file).

Every edge from reset, both tiles get the same random inputs (resets low for 6 edges); checked every edge after reset:
  * every tile output equal (!==, X / Z count as values);
  * every input port of every child instance equal (u_old.u_<c>.<p> vs u_new.u_<c>.<p>): the wiring INTO the children
    is compared directly, independent of what the children do with it.
Group reference: each child input's declared leg age is injected by an independent per-pin register array,
including the hop's reset-ready edge. Stateful boot CDC/FIFO outputs are compared directly: delaying only data inputs
while reset/readiness starts at the same edge cannot be modeled by shifting the original output history. Physical
output-chain relays retain explicit edge histories. A legal three-word boot checks payload, one seal, no fault and applied.
Phase A (edges [0, E)): natural behaviour.  Phase B (edges [E, 2E)): every child output wire w_* is FORCED to the same
random value in both tiles each edge (sparse for the writer's es / expected_valid events), so every child -> child and
child -> tile-output wire carries random data.
--mut (applied to the KIT TOP only; must FAIL): 1 = one child-output slice in a tile-output assign replaced by zeros
(dropped wire); 2 = two equal-width input connections of one child swapped; 3 = the first child whose outputs reach a
tile output removed (missing child); grp kinds: 4 / 5 (KV-GRPREACH relays), 6 = the core reset relay bypassed, 7 = u_bcdc0 legs one stage short,
8 = the o_pc0 landing-calendar relay bypassed.
    python3 tools/qwen_kv_die/kvs_tile_bench.py --tile ctl|attn|emb [--mut N] [--edges 2000] --out DIR
Needs (as kv_static_die): OT_KV_STATIC_DIE=1 + the design-point env (kvj-g2-env.sh, OT_KV_HROOT=1 OT_KV_FANFOLD=1).
One line 'KVS_TILE PASS|FAIL tile=<t> ...'; exit 0 only on PASS.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
# KV-INTEG2: singletons by instance, replicated kinds (KITS-B) by the first die instance of the kind (every instance of a
# kind is the same master)
INST = dict(ctl='kvs_ctl', attn='kvs_attn', emb='kvs_emb', grp=None, grp_h=None, pc=None, pc_h=None, hroot=None)
MASTER = {k: f'qkd_kvs_{k}' for k in INST}


def gen(t, ck1):
    env = dict(os.environ, OT_KV_STATIC_DIE='1', OT_KV_TILE_KITS='1' if ck1 else '0')
    code = ('import sys, json; sys.path.insert(0, %r); import kv_static_die as S; T = S.all_tiles(); k_ = %r; d = T[k_] if k_ else next(v for v in T.values() if v["kind"] == %r); '
            'I = S.ins(); txt = S.module_text(d, %r); '
            'print(json.dumps(dict(rtl=S.RTL_FILE, text=txt, src=S.sources(), '
            'delays=(S.kit_delays(d) if hasattr(S, "kit_delays") else dict(out={}, child={})), '
            'ports=[(p, v["dir"], v["width"], v["cls"]) for p, v in d["ports"].items()], '
            'children=[(S.cluster_of(n)[2], I[n]["module"], [(p, v["width"]) for p, v in S.spec(n).items() '
            'if v["direction"] != "output"]) for n in d["members"]])))') % (str(HERE), INST[t], t, MASTER[t])
    return json.loads(subprocess.check_output([sys.executable, '-c', code], env=env, cwd=ROOT))


def mutate(txt, mut):
    """returns (mutated text, removed child loc or None, description)"""
    lines = txt.split('\n')
    if mut == 1:
        for i, ln in enumerate(lines):
            m = re.match(r'\s*assign (\w+) = (.*);$', ln)
            if not m:
                continue
            s = re.search(r'(w_\w+)\[(\d+):(\d+)\]', m.group(2))
            if s:
                w = int(s.group(2)) - int(s.group(3)) + 1
                lines[i] = ln.replace(s.group(0), f"{{{w}{{1'b0}}}}", 1)
                return '\n'.join(lines), None, f'dropped {s.group(0)} in assign {m.group(1)}'
        wd = dict((n, int(w) + 1) for w, n in re.findall(r'wire \[(\d+):0\] (w_\w+);', txt))
        for i, ln in enumerate(lines):         # KV-INTEG2: a whole child-output wire on a tile output (no slice)
            m = re.match(r'\s*assign (\w+) = (w_\w+);$', ln)
            if m and m.group(2) in wd:
                lines[i] = ln.replace(f'= {m.group(2)};', f"= {{{wd[m.group(2)]}{{1'b0}}}};", 1)
                return '\n'.join(lines), None, f'dropped {m.group(2)} in assign {m.group(1)}'
    if mut == 2:
        for i, ln in enumerate(lines):
            m = re.match(r'(\s*\w+(?: #\(.*?\))? u_\w+ \()(.*)(\);)$', ln)
            if not m:
                continue
            conns = re.findall(r'\.(\w+)\(([^()]*)\)', m.group(2))
            def width(e):
                s = re.fullmatch(r'\w+\[(\d+):(\d+)\]', e.strip())
                return int(s.group(1)) - int(s.group(2)) + 1 if s else None
            for a in range(len(conns)):
                for b in range(a + 1, len(conns)):
                    wa, wb = width(conns[a][1]), width(conns[b][1])
                    if wa and wa == wb and wa > 1 and conns[a][1] != conns[b][1]:
                        (pa, ea), (pb, eb) = conns[a], conns[b]
                        new = ln.replace(f'.{pa}({ea})', '\x00A', 1).replace(f'.{pb}({eb})', f'.{pb}({ea})', 1)
                        new = new.replace('\x00A', f'.{pa}({eb})', 1)
                        lines[i] = new
                        return '\n'.join(lines), None, f'swapped .{pa}({ea}) <-> .{pb}({eb})'
    if mut == 4:                       # KV-GRPREACH: the down chain one relay short (o_dn from the next-to-last hop)
        for i, ln in enumerate(lines):
            m = re.match(r'\s*assign o_dn = w_ftd__q(\d+);$', ln)
            if m and int(m.group(1)) > 0:
                lines[i] = ln.replace(f'w_ftd__q{m.group(1)}', f'w_ftd__q{int(m.group(1)) - 1}')
                return '\n'.join(lines), None, 'o_dn relay chain one stage short'
    if mut == 5:                       # KV-GRPREACH: u_cf1 fault legs bypass their leg registers
        for i, ln in enumerate(lines):
            m = re.search(r'\.fault_in\((w_cfl__q\d+)\)', ln)
            if m:
                lines[i] = ln.replace(m.group(0), '.fault_in(w_cfl__a)')
                return '\n'.join(lines), None, 'u_cf1 leg registers bypassed'
    if mut == 6:                       # TW2-KVGRP: the core reset relay bypassed (every child reads the rst_n port)
        new = re.sub(r'\(w_rrc\[\d+\]\)', '(rst_n)', txt)
        if new != txt:
            return new, None, 'core reset relay bypassed'
    if mut == 7:                       # TW2-KVGRP: u_bcdc0's input legs one register short
        for i, ln in enumerate(lines):
            if ' u_bcdc0 (' in ln and 'w_lgbcdc0__q1' in ln:
                lines[i] = ln.replace('w_lgbcdc0__q1', 'w_lgbcdc0__q0')
                return '\n'.join(lines), None, 'u_bcdc0 leg registers one stage short'
    if mut == 8:                       # TW2-KVGRP: o_pc0's landing-calendar relay bypassed
        for i, ln in enumerate(lines):
            if ln.strip().startswith('assign o_pc0 =') and 'w_lro_pc0__q0' in ln:
                lines[i] = ln.replace('w_lro_pc0__q0', 'w_lro_pc0__a')
                return '\n'.join(lines), None, 'o_pc0 lcal relay bypassed'
    if mut == 3:
        assigns = '\n'.join(ln for ln in lines if ln.strip().startswith('assign '))
        for i, ln in enumerate(lines):
            m = re.match(r'\s*\w+(?: #\(.*?\))? u_(\w+) \(', ln)
            if m and f'w_{m.group(1)}__' in assigns:
                del lines[i]
                return '\n'.join(lines), m.group(1), f'removed child u_{m.group(1)}'
    raise SystemExit(f'kvs_tile_bench: mutant {mut} found no site')


def delayed_input_reference(text, children, delays):
    """Independent per-pin reference delays, with the consumer's reset age.

    Stateful CDC readiness/reset cannot be translated by delaying its outputs.
    Delay each reference input explicitly and compare all resulting state/output
    values directly. The DUT uses packed qkd_static_kv_hop chains; this reference
    uses independent arrays and never reads the DUT relay implementation.
    """
    decl = []
    delayed_locs = set()
    widths = {(loc, pin): w for loc, _mod, pins in children for pin, w in pins}
    for line in text.splitlines():
        m = re.match(r'(\s*\w+(?: #\(.*?\))? u_(\w+) \()(.*)(\);)$', line)
        if not m:
            continue
        loc = m.group(2)
        pins = dict(re.findall(r'\.(\w+)\(([^()]*)\)', m.group(3)))
        conn = m.group(3)
        for key, depth in delays.items():
            cloc, pin = key.split('.', 1)
            if cloc != loc or not depth:
                continue
            delayed_locs.add(loc)
            name = f'ref_leg_{loc}_{pin}'
            width = widths[(loc, pin)]
            decl += [f'    reg [{width-1}:0] {name} [0:{depth-1}];',
                     f'    reg {name}_reset_ready;',
                     f'    always @(posedge {pins["ck"]} or negedge {pins["rst_n"]})',
                     f'        if (!{pins["rst_n"]}) {name}_reset_ready <= 0; else {name}_reset_ready <= 1;',
                     f'    always @(posedge {pins["ck"]} or negedge {name}_reset_ready) begin',
                     f'        if (!{name}_reset_ready) begin']
            decl += [f'            {name}[{i}] <= 0;' for i in range(depth)]
            decl += ['        end else begin', f'            {name}[0] <= {pins[pin]};']
            decl += [f'            {name}[{i}] <= {name}[{i-1}];' for i in range(1, depth)]
            decl += ['        end', '    end']
            conn = conn.replace(f'.{pin}({pins[pin]})', f'.{pin}({name}[{depth-1}])', 1)
        text = text.replace(line, m.group(1)+conn+m.group(4))
    text = text.replace('endmodule', '\n'.join(decl)+'\nendmodule')
    return text, delayed_locs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tile', required=True, choices=sorted(INST))
    ap.add_argument('--mut', type=int, default=0)
    ap.add_argument('--edges', type=int, default=2000)
    ap.add_argument('--out', required=True)
    ap.add_argument('--sim', default=os.environ.get('KVS_SIM', 'iverilog'), choices=('iverilog', 'verilator'))
    ap.add_argument('--threads', type=int, default=4)
    a = ap.parse_args()
    t = a.tile
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    old, new = gen(t, False), gen(t, True)
    ntext, gone, what = (new['text'], None, 'none') if a.mut == 0 else mutate(new['text'], a.mut)
    nm = MASTER[t]
    dl = new.get('delays') or dict(out={}, child={})
    oldtext, delayed_locs = delayed_input_reference(old['text'], old['children'], dl['child'])
    (out / 'tiles.sv').write_text('`timescale 1ns/1ps\n' + oldtext.replace(f'module {nm} (', 'module old_tile (', 1) +
                                  '\n' + ntext.replace(f'module {nm} (', 'module new_tile (', 1) + '\n')
    po, pn = old['ports'], new['ports']
    pnd = {p: (d, w, c) for p, d, w, c in pn}
    L = ['`timescale 1ns/1ps', 'module tb_kvs_tile;', '  reg ck = 0; always #1 ck = ~ck;',
         '  integer t, bad, chk, act; reg phb;']
    ins = [(p, w, c) for p, d, w, c in po if d == 'input' and c != 'clock']
    for p, w, c in ins:
        if p not in pnd or pnd[p][0] != 'input' or pnd[p][1] != w:
            raise SystemExit(f'kvs_tile_bench: input {p} differs between the die-bound tile and the kit top')
        L.append(f'  reg [{w - 1}:0] {p};')
    outs = [(p, w) for p, d, w, c in po if d == 'output']
    if sorted(outs) != sorted((p, w) for p, d, w, c in pn if d == 'output'):
        raise SystemExit('kvs_tile_bench: outputs differ between the die-bound tile and the kit top')
    if not set(p for p, d, w, c in pn if c == 'clock') <= {'ck', 'hck'} or 'ck' not in [p for p, d, w, c in pn]:
        raise SystemExit('kvs_tile_bench: the kit top must have one clock port per domain (ck [, hck])')
    for p, w in outs:
        L.append(f'  wire [{w - 1}:0] o__{p}, n__{p};')
    # KV-GRPREACH: kit-added edges (kv_static_die.kit_delays): kit slice [msb:lsb] at edge t == die-bound tile at t - D
    dl = new.get('delays') or dict(out={}, child={})
    # State/output effects of explicit reference input delays are already present.
    # Preserve histories only for physical output-chain relays (o_dn, i_up, lcal).
    dout = {p: [v for v in vs if not any(str(v[3]).startswith(f'w_{loc}__') for loc in delayed_locs)]
            for p, vs in dl['out'].items()}
    dch = {}
    hist = []                                   # (history name, reference expr, width, depth)
    for p, w in outs:
        for hi, lo, D, *_src in dout.get(p, []):
            hist.append((f'h__{p}_{lo}', f'o__{p}[{hi}:{lo}]', hi - lo + 1, D))
    for (loc, pin), D in dch.items():
        cw = next(w_ for l_, mod_, ps_ in new['children'] if l_ == loc for p_, w_ in ps_ if p_ == pin)
        hist.append((f'h__c_{loc}_{pin}', f'u_old.u_{loc}.{pin}', cw, D))
    for hn, ex, hw, D in hist:
        L.append(f'  reg [{hw - 1}:0] {hn} [0:{D - 1}];')
    dmax = max([0] + [h[3] for h in hist])
    # TW2-KVGRP: the kit tile's registered reset relays release its children dl['rst'][port] edges after the port; the
    # die-bound tile gets that reset port released the same number of edges later (assert together), so the children of
    # both tiles leave reset on the same edge and every compare below stays exact
    drst = {p: D for p, D in (dl.get('rst') or {}).items() if D}
    for p in drst:
        L.append(f'  reg od__{p};')
    L.append('  old_tile u_old (' + ', '.join(
        f'.{p}({"ck" if c == "clock" else ("od__" + p if p in drst else (p if d == "input" else "o__" + p))})'
        for p, d, w, c in po) + ');')
    L.append('  new_tile u_new (' + ', '.join(
        f'.{p}({"ck" if c == "clock" else (p if d == "input" else "n__" + p)})' for p, d, w, c in pn) + ');')
    rnd = lambda w: '{' + ', '.join(['$random'] * ((w + 31) // 32)) + '}'     # noqa: E731
    ow = dict((n, int(w)) for w, n in re.findall(r'wire \[(\d+):0\] (w_\w+);', old['text']))
    nw = dict((n, int(w)) for w, n in re.findall(r'wire \[(\d+):0\] (w_\w+);', ntext))
    frc = sorted(n for n in ow if n in nw and ow[n] == nw[n] and not (gone and n.startswith(f'w_{gone}__')))
    for n in frc:
        L.append(f'  reg [{ow[n]}:0] f_{n};')
    cin = [(loc, p, w) for loc, mod, ps in new['children'] for p, w in ps if loc != gone]
    legal_boot = t in ('grp', 'grp_h') and ('bcdc0', 'cfg_we') in [(x[0], x[1]) for x in cin]
    if legal_boot:
        L += ['  reg legal_phase = 0; integer legal_words = 0, legal_seals = 0;',
              '  always @(negedge ck) if (legal_phase) begin',
              '    #0.25;',
              '    if (u_new.u_bcdc0.sink_we) begin',
              "      if (u_new.u_bcdc0.sink_addr !== 8'(legal_words) || u_new.u_bcdc0.sink_data !== (64'h1234567800000000 + 64'(legal_words))) begin bad++; $display(\"MISMATCH legal boot word %0d\", legal_words); end",
              '      legal_words++;',
              '    end',
              '    if (u_new.u_bcdc0.sink_seal) legal_seals++;',
              '  end']
    L.append('  initial begin')
    L.append('    bad = 0; chk = 0; act = 0; phb = 0;')
    for p, w, c in ins:
        L.append(f'    {p} = 0;')
    for p in drst:
        L.append(f'    od__{p} = 0;')
    L.append('    repeat (6) @(negedge ck);')
    L.append('    ' + ' '.join(f"{p} = 1;" for p, w, c in ins if c in ('reset', 'pad')))
    if legal_boot:
        # A real three-word exceptional boot replay after the documented reset
        # and FIFO-ready age, including its last-word seal and applied status.
        L.append('    legal_phase = 1;')
        L.append('    for (t = 0; t < 16; t++) begin @(negedge ck);')
        for p, D in drst.items():
            L.append(f'      if (t == {D-1}) od__{p} = 1;')
        L.append('    end')
        L += ['    for (t = 0; t < 3; t++) begin',
              "      @(negedge ck); i_ctl = 0; i_ctl[7:0] = 8'(t); i_ctl[71:8] = 64'h1234567800000000 + 64'(t); i_ctl[184] = 1; i_ctl[183] = (t == 2);",
              '      @(negedge ck); i_ctl = 0;',
              '    end',
              '    repeat (30) @(negedge ck); #0.5;',
              '    legal_phase = 0;',
              '    chk++; if (legal_words != 3 || legal_seals != 1 || u_new.u_bcdc0.fault_core || u_new.u_bcdc0.fault_hbm || !u_new.u_bcdc0.applied_hbm) begin bad++; $display("MISMATCH legal boot words=%0d seals=%0d", legal_words, legal_seals); end',
              '    $display("LEGAL_BOOT words=%0d seals=%0d fault_core=%0d fault_hbm=%0d applied=%0d", legal_words, legal_seals, u_new.u_bcdc0.fault_core, u_new.u_bcdc0.fault_hbm, u_new.u_bcdc0.applied_hbm);']
        for p, w, c in ins:
            L.append(f'    {p} = 0;')
        for p in drst:
            L.append(f'    od__{p} = 0;')
        L.append('    repeat (6) @(negedge ck);')
        L.append('    ' + ' '.join(f"{p} = 1;" for p, w, c in ins if c in ('reset', 'pad')))
    L.append(f'    for (t = 0; t < {2 * a.edges}; t = t + 1) begin')
    L.append('      @(negedge ck);')
    for p, D in drst.items():
        L.append(f'      if (t == {D - 1}) od__{p} = 1;')
    L.append(f'      if (t == {a.edges}) begin phb = 1;')
    for n in frc:
        L.append(f'        force u_old.{n} = f_{n}; force u_new.{n} = f_{n};')
    L.append('      end')
    for p, w, c in ins:
        if c in ('reset', 'pad'):
            continue
        L.append(f'      {p} = {rnd(w)};')
    for n in frc:
        if n.startswith(('w_wrn__es', 'w_wrn__expected_valid')):      # sparse writer events (two-lane rule)
            L.append(f'      f_{n} = ($random % 4 == 0) ? {rnd(ow[n] + 1)} : 0;')
        else:
            L.append(f'      f_{n} = {rnd(ow[n] + 1)};')
    L.append('      #0.5;')
    L.append('      if (t > 2) begin')
    def cmp(ref, got, what, D):
        gate = f'if (t > {2 + D + 2}) ' if D else ''
        return (f'        {gate}begin chk = chk + 1; if ({ref} !== {got}) begin bad = bad + 1; '
                f'if (bad < 6) $display("MISMATCH t=%0d {what}", t); end end')
    for p, w in outs:
        segs, cur = [], w - 1                   # undelayed slices + delayed slices of output p
        for sg in sorted(dout.get(p, []), reverse=True):
            hi, lo, D = sg[:3]
            if cur > hi:
                segs.append((cur, hi + 1, 0, None))
            segs.append((hi, lo, D, sg[3] if len(sg) > 3 else None))
            cur = lo - 1
        if cur >= 0:
            segs.append((cur, 0, 0, None))
        for hi, lo, D, src in segs:
            o_ = f'o__{p}' if (hi, lo) == (w - 1, 0) else f'o__{p}[{hi}:{lo}]'
            got = f'n__{p}' if (hi, lo) == (w - 1, 0) else f'n__{p}[{hi}:{lo}]'
            if D and src in frc and not str(src).endswith('@post'):
                # a delayed CHILD-OUTPUT wire is forced (same value, both tiles) in phase B: delayed in A, direct in B
                L.append(f'        if (!phb) ' + cmp(f'h__{p}_{lo}[{D - 1}]', got, f'out {p}[{hi}:{lo}] D={D}', D).lstrip())
                L.append(f'        if (phb && t > {a.edges + D + 2}) ' + cmp(o_, got, f'out {p}[{hi}:{lo}] B', 0).lstrip())
                continue
            ref = f'h__{p}_{lo}[{D - 1}]' if D else o_
            L.append(cmp(ref, got, f'out {p}' + (f'[{hi}:{lo}] D={D}' if D else ''), D))
        L.append(f'        if (n__{p} != 0) act = act + 1;')
    for loc, p, w in cin:
        D = dch.get((loc, p), 0)
        ref = f'h__c_{loc}_{p}[{D - 1}]' if D else f'u_old.u_{loc}.{p}'
        L.append(cmp(ref, f'u_new.u_{loc}.{p}', f'child u_{loc}.{p}' + (f' D={D}' if D else ''), D))
    L.append('      end')
    for hn, ex, hw, D in hist:                  # shift after the compare: h[k] = reference k + 1 edges ago
        for k in reversed(range(1, D)):
            L.append(f'      {hn}[{k}] = {hn}[{k - 1}];')
        L.append(f'      {hn}[0] = {ex};')
    L.append('    end')
    L.append(f'    if (bad == 0) $display("KVS_TILE PASS tile={t} edges={2 * a.edges} checks=%0d active_out=%0d '
             f'outs={len(outs)} child_inputs={len(cin)} forced={len(frc)} errors=0 mut={a.mut} vs=die_bound_tile", chk, act);')
    L.append(f'    else $display("KVS_TILE FAIL tile={t} edges={2 * a.edges} checks=%0d errors=%0d mut={a.mut} '
             f'({what})", chk, bad);')
    L.append('    $finish;')
    L.append('  end')
    L.append('endmodule')
    (out / 'tb.sv').write_text('\n'.join(L) + '\n')
    # KV-INTEG2: the explicit module closure of the tile (kvs_tile_kits_rep.tile_sources: SRAM models, modules defined in a
    # file of another name), plus kv_static_die.sources(); the generated tile file itself is replaced by tiles.sv
    code = ('import sys, json; sys.path.insert(0, %r); import kv_static_die as S; import kvs_tile_kits_rep as R; '
            'print(json.dumps(R.tile_sources(S, %r, "sim")[0]))') % (str(HERE), t)
    cl = json.loads(subprocess.check_output([sys.executable, '-c', code], cwd=ROOT,
                                            env=dict(os.environ, OT_KV_STATIC_DIE='1', OT_KV_TILE_KITS='1')))
    srcs = sorted((set(old['src']) | set(new['src']) | set(cl)) - {old['rtl'], new['rtl']})
    dirs = sorted({str(Path(s).parent) for s in srcs})
    if a.sim == 'verilator':
        # KV-KITS-ATTN 10-18: the closure daemon's pinned Verilator (5.050, PATH set by the loop / kvs_tile_bench.sh)
        cmd = ['verilator', '--binary', '--timing', '-j', str(a.threads), '-Wno-fatal', '-Wno-lint', '-Wno-style',
               '-Wno-TIMESCALEMOD', '--top-module', 'tb_kvs_tile', '-Mdir', str(out / 'obj'), '-o', 'sim',
               str(out / 'tb.sv'), str(out / 'tiles.sv')] + list(srcs) + ['+libext+.sv+.v'] + [x for d in dirs for x in ('-y', d)]
        run = [str(out / 'obj' / 'sim')]
        print('SIM ' + subprocess.run(['verilator', '--version'], capture_output=True, text=True).stdout.strip())
    else:
        cmd = ['iverilog', '-g2012', '-o', str(out / 'sim'), '-s', 'tb_kvs_tile', str(out / 'tb.sv'),
               str(out / 'tiles.sv')] + list(srcs) + ['-Y', '.sv'] + [x for d in dirs for x in ('-y', d)]
        run = ['vvp', '-n', str(out / 'sim')]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:])
        print(f'KVS_TILE FAIL tile={t} build mut={a.mut} ')
        return 2
    r = subprocess.run(run, capture_output=True, text=True, cwd=ROOT)
    print(r.stdout[-4000:])
    line = [ln for ln in r.stdout.splitlines() if ln.startswith('KVS_TILE ')]
    if not line:
        print(f'KVS_TILE FAIL tile={t} no verdict mut={a.mut} ')
        return 1
    return 0 if line[-1].startswith('KVS_TILE PASS') else 1


if __name__ == '__main__':
    sys.exit(main())
