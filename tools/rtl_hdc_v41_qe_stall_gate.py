"""Numerical and no-stall cycle checks for phase-preserving QE weight stalls."""
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import hdc_golden_v41 as G
import rtl_hdc_v41_blockdot_campaign as B
RTL=[ROOT/f'rtl/hdc/v41/{n}.sv' for n in ('ot_hdc_v41_qe','ot_hdc_actquant','ot_hdc_fp4qdq','ot_hdc_blockdot','ot_hdc_chunk8_stack')]+B.LIB
TB=ROOT/'rtl/test/tb_hdc_v41_qe_stall.sv'
OUT=ROOT/'results/rtl/v41_qe_weight_stall.json'

def vectors(path,il,chunk,fp4):
    nb,rows=17,2*il
    rng=np.random.default_rng(8117)
    x=G.to_bf16(rng.normal(size=32*nb).astype(np.float32))
    table=G.E2M1 if fp4 else G.E4M3[np.array([i for i in range(256) if i&0x7f!=0x7f])]
    codes=table[rng.integers(0,len(table),size=(rows,32*nb))]
    exps=rng.integers(-4,3,size=(rows,nb),dtype=np.int64)
    qx,xe=G.quant_fp8(x)
    terms=[np.ldexp((codes[:,b*32:(b+1)*32]@qx[b*32:(b+1)*32]).astype(np.float32),exps[:,b]+xe[b]).astype(np.float32) for b in range(nb)]
    if chunk: acc=G.csum(np.stack(terms,axis=-1))
    else:
        acc=np.zeros(rows,dtype=np.float32)
        for term in terms: acc=(acc+term).astype(np.float32)
    weights=[]
    for tile in range(2):
        for b in range(nb):
            for j in range(il):
                row=tile*il+j
                wc=(B.e2m1_codes if fp4 else B.e4m3_codes)(codes[row,b*32:(b+1)*32])
                weights.append(B.hexw(wc,8)|((int(exps[row,b])&0xffff)<<256))
    (path/'x.mem').write_text(''.join(f'{B.hexw(G.bits(x[b*32:(b+1)*32]),32):0256x}\n' for b in range(nb)))
    (path/'q.mem').write_text(''.join(f'{w:068x}\n' for w in weights))
    (path/'acc.mem').write_text(''.join(f'{int(w):08x}\n' for w in G.bits(acc)))
    (path/'bf16.mem').write_text(''.join(f'{int(w):08x}\n' for w in G.bits(G.to_bf16(acc))))

def hashes():
    files=[*RTL,TB,Path(__file__),ROOT/'tools/hdc_golden_v41.py',ROOT/'tools/hdc_golden.py',ROOT/'tools/rtl_hdc_v41_blockdot_campaign.py']
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}

def run():
    results=[]
    with tempfile.TemporaryDirectory(prefix='qe-stall-') as tmp:
        tmp=Path(tmp)
        for il in (8,16):
            for chunk in (0,1):
                for stall in (0,1):
                    exe=tmp/f'qe{il}_{chunk}_{stall}.vvp'
                    subprocess.run(['iverilog','-g2012','-s','tb_hdc_v41_qe_stall',f'-Ptb_hdc_v41_qe_stall.IL={il}',f'-Ptb_hdc_v41_qe_stall.CHUNK8={chunk}',f'-Ptb_hdc_v41_qe_stall.STALL={stall}','-o',str(exe),*map(str,RTL),str(TB)],check=True,capture_output=True,text=True)
                    for fp4 in (0,1):
                        vectors(tmp,il,chunk,fp4)
                        for gaps in ((0,) if not stall else (0,1)):
                            for unrounded in (0,1):
                                cmd=['vvp',str(exe),f'+FP4={fp4}',f'+UNROUNDED={unrounded}']+(['+GAPS'] if gaps else [])
                                p=subprocess.run(cmd,cwd=tmp,capture_output=True,text=True,timeout=120)
                                assert p.returncode==0,p.stdout+p.stderr
                                assert 'PASS' in p.stdout,p.stdout
                                line=next(x for x in p.stdout.splitlines() if x.startswith('V41QE '))
                                metrics={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',line)}
                                line=next(x for x in p.stdout.splitlines() if x.startswith('STALLMETRIC '))
                                metrics.update({k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',line)})
                                results.append(dict(il=il,chunk8=chunk,stall=stall,gaps=gaps,**metrics))
        # Mutation reproduces the legacy accumulator bug: an invalid first
        # metadata bit must not clear a circulating partial sum during bubbles.
        old_dot=tmp/'blockdot_invalid_first.sv'
        old_dot.write_text((ROOT/'rtl/hdc/v41/ot_hdc_blockdot.sv').read_text().replace('(p8_v && p8_first) ?', 'p8_first ?'))
        mutant=[old_dot if p.name=='ot_hdc_blockdot.sv' else p for p in RTL]
        exe=tmp/'mutant.vvp'
        subprocess.run(['iverilog','-g2012','-s','tb_hdc_v41_qe_stall','-Ptb_hdc_v41_qe_stall.CHUNK8=0','-o',str(exe),*map(str,mutant),str(TB)],check=True,capture_output=True,text=True)
        vectors(tmp,8,0,0)
        bad=subprocess.run(['vvp',str(exe),'+GAPS'],cwd=tmp,capture_output=True,text=True,timeout=120)
        assert bad.returncode!=0 and 'QE mismatch' in bad.stdout
        mutation={'old_invalid_first_rejected':True,'mismatched_rows':bad.stdout.count('QE mismatch')}
    for r in results:
        if r['stall'] and not r['gaps']:
            base=next(b for b in results if not b['stall'] and all(b[k]==r[k] for k in ('il','chunk8','fp4','unrounded')))
            assert r['cycles']==base['cycles'],(r,base)
    rec={'status':'pass','sources':hashes(),'cases':results,'mutation':mutation,'scope':'QE BL1 two output tiles,17 blocks each,IL8/16; FP8/FP4 weights and BF16/FP32 output, numericalgolden. No shared HBM/core integration or physical throughput claim.', 'ready_contract':'qr_issue_ready reserves registered read consumed next edge; provider subtracts current qr_re from available words','storage_added_bits':0,'pipeline_added_cycles':0}
    OUT.write_text(json.dumps(rec,indent=2)+'\n');return rec
if __name__=='__main__':print(json.dumps(run(),indent=2))
