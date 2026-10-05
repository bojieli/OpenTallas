#!/usr/bin/env python3
"""Connected software opcode proof of QK->attention output, not RTL/fulltoken.

Consumes a bounded retained checkpoint-query/initial-KV fixture. Every arithmetic
stage uses published instructions; reference arithmetic is isolated for checks.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
import hdc_golden as G
import hdc_golden_v41 as V
import w19_norm_opcode_proof as N
import w19_gpu_attention_finish as C
from w19_gpu_attention_dots import dot_program
from w19_attention_typed_vm import Machine,collector,dot_memory,wire_f32

ROOT=Path(__file__).resolve().parents[1]


def connected(q,rows,sink,cs,scale):
    n=rows.shape[0]
    if rows.shape!=(n,512) or q.shape!=(512,) or n not in [128,640]:raise ValueError('fullshape required')
    if not np.all(np.isfinite(q)) or not np.all(np.isfinite(rows)):raise ValueError('finite fullpath fixture required')
    profile=C.profile(n);recipes=profile['recipes'];machines={}
    def run(name,recipe,memory,lanes=1):
        m=Machine(recipe,memory,scale,lanes).run();machines[name]=m;return m
    # Views/packing only. QK arithmetic occurs in the actual chunk8 recipe.
    b=rows.reshape(n,2,32,8);a=np.broadcast_to(q,rows.shape).reshape(b.shape)
    m=Machine(dot_program(32),dot_memory(a,b),scale,32,dot=True).run();machines['QK_chunk']=m
    partial=m.regs['sum'].f32()[...,0]
    m=collector(partial[:,0],partial[:,1]);machines['QK_collect']=m;qk=wire_f32(m.stores[-1])
    m=run('score_scale',recipes['score_scale'],{'actualQK':N.f32(qk)},n//32);score=wire_f32(m.stores[-1])
    local=np.full((32,32),-np.inf,np.float32);local[:,:n//32]=score.reshape(32,n//32)
    m=run('max_local',recipes['max_local'],{'scaledQK scores paddedNEG_INF':N.f32(local)},4 if n==128 else 32)
    m=run('max_global',recipes['max_global'],{'SMpartialmax paddedNEG_INF':N.f32(m.regs['v'].f32()[:,0])},32)
    mb=m.regs['v'].f32()[0]
    m=run('probabilities',recipes['probabilities'],{'actual scaledQK':N.f32(score.reshape(32,n//32)),
             'actual globalmax':N.f32(mb)},n//32)
    e=wire_f32(m.stores[0]).reshape(n);eb=wire_f32(m.stores[1]).reshape(n)
    groups=e.reshape(16,8) if n==128 else e.reshape(20,32)
    mem={f'actual EXP at SMbase+{k}':N.f32(groups[:,k]) for k in range(groups.shape[1])}
    m=run('den_local',recipes['den_local'],mem)
    denpart=wire_f32(m.stores[-1]);pad=np.zeros(32,np.float32);pad[:len(denpart)]=denpart
    m=run('den_global',recipes['den_global'],{'actual contiguous SM sum subtrees; remaining leaves +0':N.f32(pad)},16 if n==128 else 32)
    den=m.regs['v'].f32()[0]
    m=run('sink_den',recipes['sink_den'],{'checkpoint attn_sink[head]':N.f32(sink),'actualglobalmax':N.f32(mb),
             'actual unrounded EXP chunk8 tree':N.f32(den)})
    total=wire_f32(m.stores[-1])
    # PV uses rounded EXP and actual rows, retaining original row order.
    left=np.broadcast_to(eb,(512,n));right=rows.T
    if n==128:
        a=left.reshape(256,32,8);b=right.reshape(a.shape)
        m=Machine(dot_program(16),dot_memory(a,b),scale,32,dot=True).run();machines['PV_chunk']=m
        pv=m.regs['sum'].f32()[...,::16].reshape(512)
    else:
        a=left[:,:512].reshape(512,2,32,8);b=right[:,:512].reshape(a.shape)
        m=Machine(dot_program(32),dot_memory(a,b),scale,32,dot=True).run();machines['PV_first64chunk']=m
        part=m.regs['sum'].f32()[...,0]
        m=collector(part[:,0],part[:,1]);machines['PV_first64_collect']=m;first=wire_f32(m.stores[-1])
        a=left[:,512:].reshape(256,32,8);b=right[:,512:].reshape(a.shape)
        m=Machine(dot_program(16),dot_memory(a,b),scale,32,dot=True).run();machines['PV_last16chunk']=m
        tail=m.regs['sum'].f32()[...,::16].reshape(512)
        p=[C.ins('LOAD','tail',source='tail'),C.ins('FADD','pad32',['tail','@ZERO']),
           C.ins('FADD','pad64',['pad32','@ZERO']),C.ins('STORE32',src=['pad64'])]
        m=run('PV_tail_zero_subtrees',p,{'tail':N.f32(tail)})
        m=collector(first,wire_f32(m.stores[-1]));machines['PV_final_collect']=m;pv=wire_f32(m.stores[-1])
    m=run('output_div_bf16',recipes['output_div_bf16'],{'actual PV result':N.f32(pv),
             'actual denominator+sink':N.f32(total)},16)
    out=wire_f32(m.stores[-1])
    m=run('inverse_rope',recipes['inverse_rope'],{'outputBF16dim448+pair*2':N.bf16_memory(out[-64::2]),
             'outputBF16dim449+pair*2':N.bf16_memory(out[-63::2]),
             'actual position coefficient COS':N.f32(cs[0]),'actual position coefficient SIN':N.f32(cs[1])},8)
    final=out.copy();final[-64::2]=wire_f32(m.stores[0]);final[-63::2]=wire_f32(m.stores[1])
    return dict(qk=qk,score=score,mb=np.asarray(mb,np.float32),e=e,eb=eb,den=np.asarray(den,np.float32),
                total=np.asarray(total,np.float32),pv=pv,out=out,final=final),machines


def reference(q,rows,sink,cs,scale):
    old=V.ARITH
    try:
        V.ARITH='chunk8'
        qk=V.dots(q[None,:],rows)[0];score=G.mul(qk,scale);mb=np.max(score)
        e=G.exp(G.add(score,G.neg(mb)));eb=G.to_bf16(e)
        den=V.reduce_rows(e[None,:])[0];total=G.add(den,G.exp(G.add(sink,G.neg(mb))))
        pv=V.dots(eb[None,:],rows.T)[0];out=G.to_bf16(V.div(pv,total));final=V.rope_tail(out,cs,inverse=True)
        return dict(qk=qk,score=score,mb=np.asarray(mb,np.float32),e=e,eb=eb,den=np.asarray(den,np.float32),
                    total=np.asarray(total,np.float32),pv=pv,out=out,final=final)
    finally:V.ARITH=old


def execute(fixture,out):
    if out.exists():raise ValueError('refuse overwrite verdict')
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise ValueError('clean source required')
    out.mkdir(parents=True)
    z=np.load(fixture,allow_pickle=False)
    arrays={k:z[k] for k in z.files};results=[];all_traces={}
    for n in [128,640]:
        q=arrays[f'q{n}'];rows=arrays[f'rows{n}'];sink=arrays[f'sink{n}'];cs=(arrays[f'cos{n}'],arrays[f'sin{n}']);scale=arrays['scale']
        got,machines=connected(q,rows,sink,cs,scale);expected=reference(q,rows,sink,cs,scale)
        checks={k:dict(mismatch_bits=int(np.count_nonzero(np.asarray(got[k]).view(np.uint32)!=np.asarray(expected[k]).view(np.uint32))),
                       opcode_sha256=N.sha(np.asarray(got[k]).tobytes()),reference_sha256=N.sha(np.asarray(expected[k]).tobytes())) for k in got}
        results.append(dict(rows=n,checks=checks,opcode_boundaries=sum(len(m.trace) for m in machines.values())))
        all_traces[str(n)]={k:[{kk:vv for kk,vv in r.items() if kk!='value'} for r in m.trace] for k,m in machines.items()}
        np.savez_compressed(out/f'outputs{n}.npz',**got)
    paths=['tools/w19_attention_opcode_proof.py','tools/w19_attention_typed_vm.py','tools/w19_norm_opcode_proof.py',
           'tools/w19_gpu_attention_finish.py','tools/w19_gpu_attention_dots.py','tools/w19_gpu_simd_contract.py',
           'tools/hdc_golden.py','tools/hdc_golden_v41.py',
           'results/rtl/w19_checkpoint_production_20261001/gpu-attention-finish-r1.json',
           'results/rtl/w19_checkpoint_production_20261001/gpu-attention-dots-r1.json']
    verdict='PASS' if all(v['mismatch_bits']==0 for r in results for v in r['checks'].values()) else 'FAIL'
    record=dict(schema='opentallas.w19.attention-typed-opcode-proof.v1',verdict=verdict,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_pins={p:N.sha((ROOT/p).read_bytes()) for p in paths},
        fixture_sha256=N.sha(fixture.read_bytes()),fixture_path=str(fixture),
        fixture_provenance=json.loads(fixture.with_suffix('.json').read_text()),numpy=np.__version__,
        backend='CPU typed interpreter of published GPU candidate opcodes. No RTL/GPU timing or token execution.',
        MAX_MIN_policy='leftNaN->left rawbits;otherwise rightNaN->right rawbits;orderedties including +/-0->RIGHT operandbits; no nativefmax assumption',
        F2I_policy='finite integral[-126,127]F32 ->signedI32bits;SHL/IADD U32modulo typedbitview, no floatingnumeric conversion',
        connected='QK->score->max->EXP->orderedden+sink andPV->DIV->BF16->inverseRoPE; actual predecessor interpreter results at every LOAD',
        production_missing=['actual SM SIMD/RF/staging RTL and physical/model admission','finite real NoC/CDC/controller generation/credit/fence events',
                            'positioncos/sin production service: fixture coefficients only, no fulltoken claim'],
        cases=results,full_token_qualified=False,RTL_qualified=False,adopted=False)
    (out/'trace.json').write_text(json.dumps(all_traces,indent=2)+'\n')
    (out/'proof.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'verdict':verdict,'rows':[r['rows'] for r in results],'opcode_boundaries':sum(r['opcode_boundaries'] for r in results)}))
    if verdict!='PASS':raise SystemExit(1)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--fixture',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();execute(a.fixture,a.out)
