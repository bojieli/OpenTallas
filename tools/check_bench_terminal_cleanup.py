#!/usr/bin/env python3
"""Small remote simulator checks of terminal policy; no arithmetic requalification."""
from pathlib import Path
import argparse, hashlib, json, re, subprocess

ROOT = Path(__file__).resolve().parents[1]

def run(argv, out, name, expected):
    result = subprocess.run(argv, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / (name+'.log')).write_text(result.stdout)
    if (result.returncode == 0) != (expected == 0):
        raise RuntimeError(f'{name}: unexpected exit {result.returncode}; inspect preserved log')
    return dict(name=name, argv=argv, returncode=result.returncode, expected_zero=expected==0)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True,type=Path);args=ap.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    checks=[];pins={}
    # Execute the exact changed terminal guards, with successful counts (including
    # expected refusal/outside-domain counters) and then one unexpected mismatch.
    guards=[]
    for p in sorted((ROOT/'rtl/test').rglob('*.sv')):
        if not any(t in p.name for t in ['equiv','lockstep','tb_spec_seed8_fixed']):continue
        s=p.read_text()
        for pred in re.findall(r'if \(([^\n]+)\) \$fatal\(1, "(?:EQUIVALENCE|LOCKSTEP)_TERMINAL_FAIL"\);',s):
            guards.append((p,pred))
        if 'if (bad != 0) $fatal(1, "LOCKSTEP FAIL mismatches=%0d", bad);' in s:guards.append((p,'bad != 0'))
    assert len(guards)>=25
    vars_=sorted(set(re.findall(r'\b[a-zA-Z_]\w*\b',' '.join(pred for _,pred in guards))))
    for fail in [False,True]:
        lines=['module terminal_fixture;']+[f'integer {v}=0;' for v in vars_]
        lines+=['integer outside=17, refused=5, expected_faults=4;','initial begin','checked=1; n=1; expect_n=1; qw=2; qr=2; near_steps=1; near_responses=1; n_wide=1; n_rec=1;']
        if fail:lines+=['bad=1; mism=1; mismatch=1; errors=1; failures=1; bada=1;']
        for p,pred in guards:
            pins[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
            lines += [f'if ({pred}) '+ ('$display("GUARD_REJECTED");' if fail else '$fatal(1,"good counts rejected");')]
        # Negative mode must reject every guard independently, not stop at first.
        if fail:
            lines += [f'if (!({pred})) $fatal(1,"mismatch escaped guard");' for _,pred in guards]
        lines+=['$display("PASS terminal predicate fixtures"); $finish; end endmodule']
        source=out/f'guards_{int(fail)}.sv';source.write_text('\n'.join(lines)+'\n')
        exe=out/f'guards_{int(fail)}.out'
        checks.append(run(['iverilog','-g2012','-s','terminal_fixture','-o',str(exe),str(source)],out,f'guard_build_{int(fail)}',0))
        checks.append(run(['vvp','-n',str(exe)],out,f'guard_run_{int(fail)}',0))
    # Real current spec RTL + actual bench. Small dimensions bound only fixture size;
    # historical seed8/model records are not replayed/regraded by this check.
    bench='rtl/test/ctl_spec_seed8_20261005/tb_spec_seed8_fixed.sv'
    sources=['rtl/hdc/ot_hdc_prefix.sv','rtl/gpu/dshbm/ot_dshbm_spec_state.sv',
             'rtl/experimental/ctl_spec_seed8_20261005/ot_dshbm_spec_state_f_token_edge.sv',bench]
    for p in sources:pins[p]=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
    for inject in [False,True]:
        wrapper=out/f'spec_{int(inject)}.sv'
        wrapper.write_text('module spec_fixture; tb_spec_state_lockstep #(.NREQ(160),.W(4),.PMAX(2),.WR(6),.SR(6),.TR(2),.NG(2),.NL(2),.CKMAX(32)) b();\n'+('initial begin #10; force b.bad=1; end\n' if inject else '')+'endmodule\n')
        exe=out/f'spec_{int(inject)}.out'
        checks.append(run(['iverilog','-g2012','-s','spec_fixture','-o',str(exe),*sources,str(wrapper)],out,f'spec_build_{int(inject)}',0))
        checks.append(run(['vvp','-n',str(exe)],out,f'spec_run_{int(inject)}',1 if inject else 0))
    (out/'receipt.json').write_text(json.dumps(dict(scope='terminal predicates and small actual spec RTL; no historical PASS regrade',source_pins=pins,guard_count=len(guards),checks=checks),indent=2)+'\n')
    print('PASS',len(checks),'checks;',len(guards),'terminal guards')

if __name__=='__main__':main()
