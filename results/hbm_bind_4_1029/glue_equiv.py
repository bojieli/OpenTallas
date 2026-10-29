#!/usr/bin/env python3
"""HBM-BIND-4: formal equivalence of every emitted native-glue $shift/$shiftx helper.

Gold = the original single Yosys primitive (the helper's own JSON: actual parameters,
literal constants, shared repeated nets). Gate = the SV text bind emitted (stock Yosys
write_verilog), re-read by Yosys. equiv_make/equiv_simple/equiv_status -assert must PASS;
a mutant gate with output bit 0 inverted must FAIL (CAUGHT) for every helper.
"""
import json, sys, subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools' / 'die_plan'))
import bind_elab as E

def run(ys, log, mounts):
    try:
        E.run_yosys(ys, log, mounts, mem_gb=8)
        return True
    except E.ElabError:
        # a failure counts only when equiv_status itself reports unproven cells (never a tool/setup error)
        if 'unproven $equiv cells' in Path(log).read_text():
            return False
        raise

def main():
    gd = Path(sys.argv[1]); wd = Path(sys.argv[2]); wd.mkdir(parents=True, exist_ok=True)
    rows = []
    for j in sorted(gd.glob('ot_bind_native_*.json')):
        mod = j.stem
        d = json.loads(j.read_text())['modules'][mod]
        typ = d['cells']['primitive']['type']
        sv = j.with_suffix('.sv')
        ports = d['ports']
        decl = ', '.join(f"{'input' if p['direction']=='input' else 'output'} [{len(p['bits'])-1}:0] {n}" for n, p in ports.items())
        conn = ', '.join(f'.{n}({n}_w)' if ports[n]['direction'] == 'output' else f'.{n}({n})' for n in ports)
        wires = ' '.join(f"wire [{len(p['bits'])-1}:0] {n}_w;" for n, p in ports.items() if p['direction'] == 'output')
        assigns = ' '.join((f"assign {n} = {n}_w ^ {{{{{len(p['bits'])-1}{{1'b0}}}}, 1'b1}};" if len(p['bits']) > 1
                            else f"assign {n} = ~{n}_w;") for n, p in ports.items() if p['direction'] == 'output')
        mut = wd / f'{mod}_mut.sv'
        mut.write_text(sv.read_text().replace(f'module {mod}', f'module {mod}_inner') +
                       f'\nmodule {mod}_mutw({decl}); {wires} {mod}_inner u({conn}); {assigns}\nendmodule\n')
        res = {}
        for tag, gate_file, gate_mod in (('equiv', sv, mod), ('mutant', mut, f'{mod}_mutw')):
            ys = wd / f'{mod}_{tag}.ys'
            ys.write_text(f'read_json "{j}"\nrename {mod} gold\nread_verilog -sv "{gate_file}"\n'
                          f'rename {gate_mod} gate\nproc\nflatten gate\nequiv_make gold gate eq\nhierarchy -top eq\n'
                          f'equiv_simple -undef\nequiv_induct -undef\nequiv_status -assert\n')
            res[tag] = run(ys, wd / f'{mod}_{tag}.log', [wd, gd])
        ok = res['equiv'] and not res['mutant']
        rows.append(dict(helper=mod, type=typ, equiv='PASS' if res['equiv'] else 'FAIL',
                         mutant_out0_inverted='CAUGHT' if not res['mutant'] else 'SURVIVED', verdict='PASS' if ok else 'FAIL'))
        print(mod, typ, rows[-1]['equiv'], rows[-1]['mutant_out0_inverted'])
    v = 'PASS' if rows and all(r['verdict'] == 'PASS' for r in rows) else 'FAIL'
    rec = dict(schema='hbm.bind4.native_glue_equiv.v1', verdict=v, helpers=len(rows), rows=rows,
               method='gold=original primitive JSON, gate=emitted write_verilog SV; equiv_simple/induct -undef; mutant gate inverts output bit 0')
    (wd / 'receipt.json').write_text(json.dumps(rec, indent=1) + '\n')
    print('VERDICT', v, len(rows))
    sys.exit(0 if v == 'PASS' else 1)

if __name__ == '__main__':
    main()
