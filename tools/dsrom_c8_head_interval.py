#!/usr/bin/env python3
"""Measure the real reduced MTP head adapter on six existing cached operands.

No inference, ISA execution or expectation generation. Inputs are the normalized
head vectors retained in the existing serial golden's final VM; expected outputs
are its final six head vectors. This is a reduced head measurement, not 12.37 us
at full shape, SS/FF closure, or a combined token result. Model basis: 4f0c050b8.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import hdc_isa_v41 as I


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--image',type=Path,required=True)
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--jobs',type=int,default=16)
    a=ap.parse_args()
    a.image=a.image.resolve(); a.work=a.work.resolve()
    isa=json.loads((a.image/'isa.json').read_text())
    assert isa['equal_golden_tokens'] and isa['committed_logits_bit_exact_with_golden']
    tags={int(s.split(' ',1)[0]):s.split(' ',1)[1] for s in (a.image/'prog_tags.txt').read_text().splitlines()}
    words=[int(s,16) for s in (a.image/'prog.hex').read_text().splitlines()]
    heads=[I.decode(w) for pc,w in enumerate(words) if tags.get(pc)=='head' and I.decode(w)['unit']==I.UNIT_ME]
    heads=[f for f in heads if f['me_amax']]
    # One prefill head followed by six verify slots, no Markov/draft head.
    assert len(heads)==7 and [f['dslot'] for f in heads[1:]]==list(range(6))
    heads=heads[1:]
    cfg=[int(s,16) for s in (a.image/'cfg.hex').read_text().splitlines()]
    fields=('me_nout','me_tiles','me_k','me_wbase','me_xbase','me_xjs','me_split','me_round','me_obase','me_ots','me_ojs')
    desc=[]
    for slot,f in enumerate(heads):
        assert f['me_nout']==4040 and f['me_k']==160 and not f['me_wsrc']
        assert not any(f[k] for k in ('me_d_xbase','me_d_wbase','me_d_nout','me_d_k'))
        desc += [f[k] for k in fields]+[cfg[1]&15,isa['targets'][-1][slot],0,0,0]
    a.work.mkdir(parents=True,exist_ok=False)
    stim=a.work/'stim'; stim.mkdir()
    for src,dst in [('expect_vm.hex','vm.hex'),('mbank.hex','mbank.hex')]:
        (stim/dst).symlink_to(a.image/src)
    (stim/'desc.hex').write_text(''.join(f'{x:08x}\n' for x in desc))
    logits=(a.image/'exp_heads.hex').read_text().splitlines()
    assert len(logits)==isa['heads']*4040
    (stim/'head_logits.hex').write_text('\n'.join(logits[-6*4040:])+'\n')
    import rtl_hdc_v41x_decode_campaign as X
    sources=[*X.rtl_sources(True),ROOT/'rtl/test/tb_dsrom_c8_head_interval.sv']
    pins={str(p.relative_to(ROOT)):sha(p) for p in sources}
    rec={'status':'building','scope':'actual reduced head adapter, six cached serial-golden operands',
         'model_basis':'4f0c050b8 (model only)', 'shape':{'positions':6,'dim':160,'vocab':4040,'MG':8},
         'input_sha256':{p:sha(a.image/p) for p in ('isa.json','prog.hex','prog_tags.txt','cfg.hex','expect_vm.hex','mbank.hex','exp_heads.hex')},
         'source_sha256':pins,'clock_claim':False,'full_shape_interval_measured':False}
    (a.work/'result.json').write_text(json.dumps(rec,indent=1)+'\n')
    harness=a.work/'driver.cpp'
    harness.write_text('#include "Vtb_dsrom_c8_head_interval.h"\n#include "verilated.h"\nint main(int argc,char**argv){Verilated::commandArgs(argc,argv);auto*t=new Vtb_dsrom_c8_head_interval;while(!Verilated::gotFinish()){t->clk=!t->clk;t->eval();}t->final();delete t;}\n')
    cmd=['verilator','--cc','--exe','--build','-O2','-Wno-fatal','--top-module','tb_dsrom_c8_head_interval',
         '-Mdir',str(a.work/'obj'),'-I'+str(X.SVH.parent),*map(str,sources),str(harness),'-j',str(a.jobs)]
    with (a.work/'build.log').open('x') as log: rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
    (a.work/'build.rc').write_text(str(rc)+'\n')
    rec['build_rc']=rc
    if rc==0:
        exe=a.work/'obj/Vtb_dsrom_c8_head_interval'
        with (a.work/'run.log').open('x') as log:
            p=subprocess.Popen(['stdbuf','-oL',str(exe),'+DIR='+str(stim)],stdout=log,stderr=subprocess.STDOUT)
            rec['status']='running';rec['pid']=p.pid
            (a.work/'result.json').write_text(json.dumps(rec,indent=1)+'\n')
            rc=p.wait()
        (a.work/'run.rc').write_text(str(rc)+'\n')
        out=(a.work/'run.log').read_text()
        m=re.search(r'C8_HEAD positions=(\d+) logits_checked=(\d+) errors=(\d+)',out)
        rec['run_rc']=rc
        rec['head_ii_cycles']=[int(x) for x in re.findall(r'HEAD_II from=\d+ to=\d+ cycles=(\d+)',out)]
        rec['summary']=None if not m else dict(zip(('positions','logits_checked','errors'),map(int,m.groups())))
        rec['pass']=rc==0 and m is not None and m.groups()==('6','24240','0') and 'PASS' in out.splitlines()
    else: rec['pass']=False
    rec['sources_unchanged']=all(sha(ROOT/p)==h for p,h in pins.items())
    rec['pass']=rec['pass'] and rec['sources_unchanged']
    rec['status']='pass' if rec['pass'] else 'fail'
    (a.work/'result.json').write_text(json.dumps(rec,indent=1)+'\n')
    return 0 if rec['pass'] else 1


if __name__=='__main__': raise SystemExit(main())
