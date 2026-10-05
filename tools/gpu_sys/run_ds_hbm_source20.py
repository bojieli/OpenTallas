"""Execute a saved source-native DS program on the persistent real SM backend.

One requested token after the archived prompt, or its first source-entry pair.
No ABI3 reinterpretation, functional Machine, inference, forced drafter,
expected payload injection, timeout or hidden geometry enlargement.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from tools.gpu_sys.ds_hbm_simulator20 import Simulator20, sha
from tools.gpu_sys.ds_hbm_sm_engine20_guarded import SMEngine20Guarded


def source_launches(source, phase):
    prompt=source['prompt']
    if not prompt or len(prompt)>source['position_extent']:
        raise ValueError('source prompt exceeds its actual state image')
    if not all(type(t) is int and 0<=t<131072 for t in prompt):
        raise ValueError('unsigned source token17 required')
    if phase=='source-entry':
        yield 'swapin',0,0
        yield 'embed',prompt[0],0
        return
    if phase!='token':raise ValueError('unsupported source execution phase')
    # The frozen D.expand trajectory: one actual column, original forty
    # source layers in order, then head and DSpark seed. No new arithmetic.
    for position,token in enumerate(prompt):
        for layer in range(40):
            yield 'swapin',0,layer
            if layer==0:yield 'embed',token,position
            yield 'layer',token,position
            yield 'swapout',0,position
        yield 'swapin',0,63
        yield 'head',0,position
        yield 'seed',0,position


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--enable',action='store_true',required=True)
    p.add_argument('--executable',type=Path,required=True)
    p.add_argument('--source-manifest',type=Path,required=True)
    p.add_argument('--phase',choices=('source-entry','token'),required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    source=json.loads(a.source_manifest.read_text())
    launches=list(source_launches(source,a.phase))
    for kind,_,_ in launches:
        if kind not in source['entries']:raise ValueError('missing source entry: '+kind)
    pins=Simulator20(a.executable,a.source_manifest,enable=True,log_dir=a.out/'backend')
    engine=SMEngine20Guarded(pins,enable=True)
    print(json.dumps(dict(simulator_pid=pins.process.pid,source_sha256=sha(a.source_manifest),
        phase=a.phase,launches=len(launches),initial=pins.snapshot())),flush=True)
    tokens=[]
    try:
        with (a.out/'kernels.jsonl').open('w') as log:
            for job,(kind,token,position) in enumerate(launches,1):
                engine.launch(entry_pc=source['entries'][kind],token=token,
                    position=position,job=job,generation=1,
                    expected_status=0 if kind in ('head','markov') else 2)
                receipt=None
                while receipt is None:
                    receipt=engine.poll()
                record=dict(kind=kind,input_token=token,**asdict(receipt))
                log.write(json.dumps(record)+'\n');log.flush()
                if kind=='head':
                    tokens.append(receipt.token)
                    print(json.dumps(dict(position=position,actual_head_token=receipt.token,
                        completion=asdict(receipt))),flush=True)
        final=pins.snapshot()
        if final['sys_fault'] or any(s['busy'] for s in final['sms']):
            raise RuntimeError('actual system did not drain after source execution')
        pins.close()
        result=dict(verdict='COMPLETED_SOURCE_NATIVE_'+a.phase.upper().replace('-','_'),
            source_manifest_sha256=sha(a.source_manifest),kernel_launches=len(launches),
            heads=tokens,requested_token=tokens[-1] if tokens else None,final=final,
            numerical_qualified=False,full_shape_qualified=False,
            accelerator_adopted=False,scope=source['full_shape'])
        (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result),flush=True)
        return 0
    except Exception as error:
        # No retry, source remapping, arithmetic fallback or reset/ACK repair.
        (a.out/'failure.json').write_text(json.dumps(dict(error=str(error),
            actual=pins.snapshot(),numerical_qualified=False),indent=2)+'\n')
        raise


if __name__=='__main__':raise SystemExit(main())
