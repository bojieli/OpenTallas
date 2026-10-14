#!/usr/bin/env python3
"""Prepare an executable cycle bench of retained logic against its flat parent.

Hard arithmetic interiors use identical deterministic surrogates in both sides.
This gate tests the retained state, ICG and cut wiring, never arithmetic inside
the twelve already published hard leaves. All surrogate definitions are saved.
"""
import copy
import argparse
import json
from pathlib import Path
from hbm_sm_own_logic_1013 import ROOT, HARD, extract


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mapped', help='ASIC mapped ownleaf JSON; EG/WG share the identical functional graph')
    args = ap.parse_args()
    src = ROOT / 'results/arch/hbm_native_1013/sm_compaction'
    out = ROOT / 'results/arch/hbm_native_1013/sm_own_logic'
    for v in ('eg', 'wg'):
        d = json.loads((src / (v + '.json')).read_text())
        original, leaf, parent, roots, row = extract(d, v)
        if args.mapped:
            mapped = json.loads(Path(args.mapped).read_text())
            leaf = copy.deepcopy(mapped['modules']['ot_smh_own_eg'])
            assert set(leaf['ports']) == set(roots['cells']['u_own']['connections'])
            assert all(p['direction'] == roots['cells']['u_own']['port_directions'][n]
                       and len(p['bits']) == len(roots['cells']['u_own']['connections'][n])
                       for n, p in leaf['ports'].items())
        gold = copy.deepcopy(d)
        gold['modules']['gold_' + v] = gold['modules'].pop(row['source_top'])
        split = copy.deepcopy(d)
        split['modules']['split_' + v] = roots
        split['modules'].pop(row['source_top'])
        split['modules'][row['own_master']] = leaf
        mutant = copy.deepcopy(split)
        cut = next(n for n, p in leaf['ports'].items() if p['direction'] == 'output')
        # Tie the leaf output internally. The parent's output connection stays
        # legal so the negative reaches executable cycle comparison.
        mutant['modules'][row['own_master']]['ports'][cut]['bits'] = ['0']
        if cut in mutant['modules'][row['own_master']]['netnames']:
            mutant['modules'][row['own_master']]['netnames'][cut]['bits'] = ['0']
        for tag, design in [('gold', gold), ('split', split), ('mut', mutant)]:
            (out / (v + '_' + tag + '.json')).write_text(json.dumps(design) + '\n')
        stubs = []
        for name in sorted(HARD):
            mod = d['modules'][name]
            ports = mod['ports']
            decls = [p['direction'] + ' wire ' + (f'[{len(p["bits"])-1}:0] ' if len(p['bits']) > 1 else '') + n for n, p in ports.items()]
            # Same immediate combinational surrogate on both sides; its outputs
            # vary with every input bit, exercising downstream retained flops.
            folds = ['(^' + n + ')' for n, p in ports.items() if p['direction'] == 'input']
            lines = ['module ' + name + '(' + ','.join(decls) + ');', 'wire fold = ' + '^'.join(folds) + ';']
            for index, (n, p) in enumerate(ports.items()):
                if p['direction'] == 'output':
                    width = len(p['bits'])
                    lines.append(f'assign {n} = {{{width}{{fold}}}} ^ {width}\'d{index};')
            lines.append('endmodule')
            stubs += lines
        if not args.mapped:
            stubs += ['module ICGx1_ASAP7_75t_R(input CLK, ENA, SE, output GCLK);',
                  'reg enable_latched; always_latch if (!CLK) enable_latched = ENA | SE;',
                  'assign GCLK = CLK & enable_latched; endmodule']
        (out / (v + '_surrogates.sv')).write_text('\n'.join(stubs) + '\n')
        tb = ['module tb;', 'integer mismatches=0; integer checked=0;']
        inputs, outputs = [], []
        for n, p in original['ports'].items():
            w = len(p['bits']); size = f'[{w-1}:0] ' if w > 1 else ''
            if p['direction'] == 'input':
                tb.append('reg ' + size + n + ';'); inputs.append((n, w))
            else:
                tb += ['wire ' + size + 'g_' + n + ';', 'wire ' + size + 's_' + n + ';']; outputs.append(n)
        for prefix in ('gold', 'split'):
            conn = ['.' + n + '(' + (n if p['direction'] == 'input' else ('g_' if prefix == 'gold' else 's_') + n) + ')' for n, p in original['ports'].items()]
            if prefix == 'split':
                conn += ['.' + c['parent_clock_port'] + '(clk)' for c in row['child_clocks']]
            tb.append(prefix + '_' + v + ' u_' + prefix + '(' + ','.join(conn) + ');')
        tb += ['initial begin', 'clk=0;', 'for (integer cycle=0; cycle<4128;cycle=cycle+1) begin']
        for n, w in inputs:
            if n in ('clk', 'rst_n'): continue
            tb.append(f'for(integer bitbase=0;bitbase<{w};bitbase=bitbase+1) {n}' + ('[bitbase]' if w > 1 else '') + '=$urandom_range(0,1);')
        tb += ['rst_n=(cycle>=16 && !(cycle>=2000 && cycle<2016));', '#2; clk=1; #2;']
        tb += ['// Warm initial unreset library state before comparing defined operation.', 'if (cycle>=32) begin']
        for n in outputs:
            tb.append('if(g_' + n + ' !== s_' + n + ') mismatches=mismatches+1;')
        tb += ['checked=checked+1; end; clk=0; #2;', 'end',
               '$display("OWN_LOGIC_CYCLE_BENCH checked=%0d mismatches=%0d",checked,mismatches);',
               'if(mismatches) $fatal(1,"retained own logic differs from flat pinned parent");', '$finish;', 'end', 'endmodule']
        (out / (v + '_tb.sv')).write_text('\n'.join(tb) + '\n')
        script = ['#!/bin/bash', 'set -euo pipefail', 'cd "$(dirname "$0")"', 'tag=${1:-split}',
                  'V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}',
                  '"$V" --version | tee verilator_version.txt',
                  '"$V" --version | grep -q "Verilator 5.050"',
                  f'yosys -Q -p "read_json {v}_gold.json; hierarchy -top gold_{v}; write_verilog -noattr {v}_gold.sv" > {v}_gold_emit.log',
                  f'yosys -Q -p "read_json {v}_${{tag}}.json; hierarchy -top split_{v}; write_verilog -noattr {v}_dut.sv" > {v}_dut_emit.log',
                  f'"$V" --binary --timing -j 4 -Wno-fatal --top-module tb --Mdir work_{v}_${{tag}}_v5050 {v}_gold.sv {v}_dut.sv {v}_surrogates.sv {v}_tb.sv ' + ('retention_cell_models.sv ' if args.mapped else '') + f'> {v}_${{tag}}_build.log 2>&1',
                  'set +e',
                  f'./work_{v}_${{tag}}_v5050/Vtb > {v}_${{tag}}_runtime.log 2>&1',
                  'sim_rc=$?', 'set -e',
                  f'cat {v}_${{tag}}_runtime.log', 'exit "$sim_rc"']
        path = out / (v + '_run.sh'); path.write_text('\n'.join(script) + '\n'); path.chmod(0o755)


if __name__ == '__main__':
    main()
