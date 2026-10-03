#!/usr/bin/env python3
"""Additive DSpark system lowering successor; original unfinished pins retained.

The handover's column stride4608 overlaps its1920B main-hidden area by36B.
This fixes allocation only, reusing every original arithmetic kernel/golden.
Default-off CLI. This is the reduced checkpoint functional-machine gate, not
full-shape RTL/full-token qualification or expert-union weight-stream reuse.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v41_dspark as D

OLD_STRIDE = 4608
COLUMN_ALIGNMENT = 128
COLUMN_REGIONS = dict(X=(D.O_X,2560), PRE=(D.O_PRE,16), CTR=(D.O_CTR,4),
                      SEL=(D.O_SEL,128), NSEL=(D.O_NSEL,4), MH=(D.O_MH,1920))


def column_layout():
    ordered=sorted((base,base+size,name) for name,(base,size) in COLUMN_REGIONS.items())
    for previous,current in zip(ordered,ordered[1:]):
        if previous[1]>current[0]:
            raise ValueError('column field overlap')
    end=max(hi for _,hi,_ in ordered)
    stride=(end+COLUMN_ALIGNMENT-1)//COLUMN_ALIGNMENT*COLUMN_ALIGNMENT
    return dict(regions=COLUMN_REGIONS,end=end,stride=stride,slots=D.NCOLSLOT,
                old_stride=OLD_STRIDE,old_overlap_bytes=max(0,end-OLD_STRIDE),
                added_bytes_per_die=D.NCOLSLOT*(stride-OLD_STRIDE),
                added_bytes_total=D.TP*D.NCOLSLOT*(stride-OLD_STRIDE),
                arithmetic_changed=False,added_SRAM_bytes=0,
                six_position_verify=dict(gamma=5,columns=6,draft_block=D.B),
                expert_union_weight_reuse_qualified=False)


class ConnectedProgram(D.DProgram):
    def put(self,name,size,align=128):
        if name=='COL':
            if size!=D.NCOLSLOT*OLD_STRIDE or self.CSTR!=OLD_STRIDE:
                raise ValueError('pinned original column recipe changed')
            self.CSTR=column_layout()['stride']
            size=D.NCOLSLOT*self.CSTR
        return super().put(name,size,align)


def build(model=None):
    model=model or D.V.Model()
    if model.dspark_block!=D.B:
        raise ValueError('source checkpoint draft-block geometry differs')
    prog=ConnectedProgram(model).build_images()
    graph=[]
    for kind in D.KINDS:
        kernels={}
        for die in range(D.TP):
            for sm in range(D.NSM):
                gen=D.DGen(prog,die,sm,kind)
                kernels[die,sm]=getattr(gen,'kernel_'+kind)()
        graph.append((kind,kernels))
    code=[(kind,{key:kernel.assemble() for key,kernel in kernels.items()}) for kind,kernels in graph]
    prog.finish_images()
    D.NOISE=model.noise_id
    return model,prog,graph,code


def emit_images(out):
    """Source program/checkpoint bytes only: no golden inference or oracle trace.

    The actual DSpark controller must produce commands from real head results.
    This output supplies linked entries to ds_hbm_cmdproc_bridge.CmdprocBridge.
    """
    out=Path(out)
    out.mkdir(parents=True,exist_ok=False)
    model,prog,graph,code=build()
    images,entries=D.H.link(code)
    words=max(map(len,images.values()))
    if words>1<<14:
        raise ValueError('linked source exceeds actual IMW14')
    paths=[]
    for (die,sm),program in images.items():
        path=out/f'prog_d{die}_s{sm}.hex'
        path.write_text(''.join(f'{word:016x}\n' for word in program))
        paths.append(path)
    for die in range(D.TP):
        image=np.zeros(prog.mem_bytes,dtype=np.uint8)
        for addr,blob in prog.mem[die].items():
            image[addr:addr+len(blob)]=blob
        path=out/f'die{die}.bin'
        path.write_bytes(image.tobytes());paths.append(path)
    prompt=list(D.V.prompt_and_expected()[0])
    if any(not 0<=token<65536 for token in prompt):
        raise ValueError('actual cmdproc refuses prompt token narrowing')
    record=dict(schema='opentallas.ds_hbm_dspark_connected_images.v1',
        scope='reduced checkpoint source images; no inference or numerical verdict',
        entries=entries,imw=14,imem_words=words,tp=D.TP,nsm=D.NSM,
        mem_bytes=prog.mem_bytes,noise=model.noise_id,prompt=prompt,
        column_layout=column_layout(),layout=prog.a,
        expert_union_weight_reuse_qualified=False,
        artifacts={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (Path(__file__),Path(D.__file__),Path(D.H.__file__),D.V.CHECKPOINT)})
    (out/'program.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def validate_command(cmd,*,noise):
    if cmd.get('op') not in ('VLAYER','VHEAD','SEED','DSTAGE','DHEAD','MARKOV'):
        raise ValueError('unsupported actual control command')
    for name,bits in (('idx',8),('ncol',4),('pos',16),('tok1',16)):
        value=cmd.get(name)
        if type(value) is not int or not 0<=value<1<<bits:
            raise ValueError('current cmdproc field refuses truncation: '+name)
    if not 1<=cmd['ncol']<=D.PMAX:
        raise ValueError('finite column count')
    if cmd['op'] in ('VLAYER','VHEAD','SEED'):
        if cmd['pos']+cmd['ncol']>D.CTX:
            raise ValueError('source position storage extent')
    if cmd['op']=='VLAYER':
        if not 0<=cmd['idx']<40 or len(cmd['toks'])!=cmd['ncol']:
            raise ValueError('actual backbone layer/tokens')
        if any(type(t) is not int or not 0<=t<1<<16 for t in cmd['toks']):
            raise ValueError('current cmdproc token16 refuses truncation')
    if cmd['op']=='DSTAGE' and (cmd['idx']>=D.NST or cmd['ncol']!=D.B):
        raise ValueError('actual draft-stage geometry')
    if cmd['op']=='DHEAD' and cmd['ncol']!=D.B:
        raise ValueError('actual draft-head geometry')
    if cmd['op']=='MARKOV' and (cmd['idx']>=D.B or cmd['ncol']!=1):
        raise ValueError('actual serial Markov row')
    if type(noise) is not int or not 0<=noise<1<<16:
        raise ValueError('current cmdproc noise16 refuses truncation')
    return cmd


def check(*,ngen=8,gamma=5,out=None):
    if not 1<=gamma<=D.B or not 1<=ngen<=8:
        raise ValueError('fixed source vehicle geometry: gamma1..5/ngen1..8')
    start=time.monotonic()
    model,prog,graph,code=build()
    prompt=list(D.V.prompt_and_expected()[0])
    class GoldenObserver(D.V.Model):
        def forward_positions(self,*args,**kwargs):
            logits=super().forward_positions(*args,**kwargs)
            self.observations.extend(row.copy() for row in logits)
            return logits
    golden_model=GoldenObserver()
    golden_model.observations=[]
    gtok,glg,gpass=golden_model.generate_spec(prompt,ngen,gamma)
    print('SOURCE_PROGRAM_BUILT',prog.mem_bytes,'bytes/die; golden tokens',gtok,flush=True)
    machine=D.H.Machine(nd=D.TP,nsm=D.NSM,nl=D.NL,mem_bytes=prog.mem_bytes,L=D.H.L16)
    D.H.load_images(machine,prog)
    D.isa.FP_ERR[0]=0
    class ObservedEngine(D.Engine):
        def run(self,cmd,want_logits=False):
            result,logits=super().run(cmd,want_logits)
            self.observations.extend(row.copy() for row in logits)
            return result,logits
    engine=ObservedEngine(dict(code),machine,prog)
    engine.observations=[]
    commands=[]
    tokens,rows,steps=D.ctl_loop(engine,prompt,ngen,gamma,cmdlog=commands)
    for command in commands:
        validate_command(command,noise=model.noise_id)
    tokens_exact=tokens==gtok
    logits_exact=(len(rows)==len(glg) and all(np.array_equal(D.G.bits(a),D.G.bits(b)) for a,b in zip(rows,glg)))
    passes_exact=[(s['drafts'],s['targets'],s['accepted']) for s in steps]==[
                 (s['drafts'],s['targets'],s['accepted']) for s in gpass]
    all_columns_exact=(len(engine.observations)==len(golden_model.observations) and all(
        np.array_equal(D.G.bits(a),D.G.bits(b)) for a,b in zip(engine.observations,golden_model.observations)))
    ok=tokens_exact and logits_exact and passes_exact and all_columns_exact and D.isa.FP_ERR[0]==0
    sources=[Path(__file__),Path(D.__file__),Path(D.H.__file__),Path(D.V.__file__),D.V.CHECKPOINT]
    result=dict(schema='opentallas.ds_hbm_dspark_connected_functional.v1',
                verdict='PASS_REDUCED_FUNCTIONAL' if ok else 'FAIL_REDUCED_FUNCTIONAL',
                scope='reduced checkpoint arithmetic on functional machine; no RTL/full-shape token credit',
                tokens=tokens,golden_tokens=gtok,tokens_exact=tokens_exact,logits_exact=logits_exact,
                passes_exact=passes_exact,steps=steps,gamma=gamma,max_verify_columns=max(
                    c['ncol'] for c in commands if c['op']=='VLAYER'),
                all_prefill_verify_columns_exact=all_columns_exact,
                compared_logit_words=sum(row.size for row in engine.observations),
                fp_failed_lanes=D.isa.FP_ERR[0],launches=engine.launches,
                elapsed_seconds=time.monotonic()-start,column_layout=column_layout(),
                source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    if out:
        Path(out).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
    return ok


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--enable-dspark-connected',action='store_true',required=True)
    ap.add_argument('--check',action='store_true')
    ap.add_argument('--layout',action='store_true')
    ap.add_argument('--emit-images',type=Path,help='checkpoint lowering only; no golden/expected payload generation')
    ap.add_argument('--ngen',type=int,default=8)
    ap.add_argument('--gamma',type=int,default=5)
    ap.add_argument('--out',type=Path)
    a=ap.parse_args()
    if a.layout:
        print(json.dumps(column_layout()))
    if a.emit_images:
        print(json.dumps(emit_images(a.emit_images)))
    if a.check:
        raise SystemExit(0 if check(ngen=a.ngen,gamma=a.gamma,out=a.out) else 1)
