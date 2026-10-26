#!/usr/bin/env python3
"""Mapped-memory two-column programme playback across dictionary bank boundaries."""
import argparse, json, subprocess
from pathlib import Path
from su_programme_compile import lower, ROOT

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    source=out/'source.mem'
    # Distinct dictionaries: col0 has17entries, col1 has261, forcing1vs3 banks.
    source.write_text(''.join(f'{((i*17)<<256)|((i%17)*71):0128x}\n' for i in range(261)))
    lower(source,out,None,0,512,'PROGRAMME',1)
    rtl='rtl/hbm_accel/generic/adapters/static_su/programme/ot_hbm_su_programme.sv'
    macro='physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v'
    def run(name,args):
        p=subprocess.run(args,cwd=ROOT,capture_output=True,text=True)
        (out/(name+'.log')).write_text(p.stdout+p.stderr);return p.returncode
    assert run('compile',['iverilog','-g2012','-s','tb','-o',str(out/'tb.vvp'),str(out/'tb.sv'),rtl,macro])==0
    rows=[]
    for mutant in ['', 'MUT_DATA','MUT_ADDR','MUT_PHASE']:
        rc=run(mutant or 'positive',['vvp',str(out/'tb.vvp'),'+DIR='+str(out)]+(['+'+mutant] if mutant else []))
        assert (rc!=0)==bool(mutant),(mutant,rc)
        rows.append(dict(case=mutant or 'positive',rc=rc))
    assert run('yosys_parse',['yosys','-Q','-T','-p','read_verilog -sv '+rtl])==0
    (out/'summary.json').write_text(json.dumps(dict(scope='component mapped programme playback; not whole-SU or die qualification',edges=261,restarts=2,columns=2,dictionary_banks=[1,3],cases=rows,yosys_parse='PASS'),indent=2)+'\n')
    print('PROGRAMME_PACKED_GATE PASS 261 edges x2 and3mutants; Yosys parse')
if __name__=='__main__':main()
