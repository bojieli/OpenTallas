#!/usr/bin/env python3
"""One released-source PC40 operand capture; oracle starts after native capture.

The unchanged historical executor produces PCs0..39 from qualified immutable
checkpoint images. This stops before token completion and calls its exact NEG
and exp step0 FMAX recipes. No reference activation enters that executor.
"""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/c0_pc40_payload_lease_20261003'
SOURCE='870c5fe581b768df28dd2998b2d0aecc24510c23'
IMAGE_SHA='83491cd2487ec026e86b5943e0420a4efcb6830aaf35f761e20190a469fd69e7'

def canonical(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def require(ok,msg):
    if not ok:raise ValueError(msg)

def source_runtime(source_root,images):
    source_root=Path(source_root).resolve();images=Path(images).resolve()
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=source_root,text=True).strip()==SOURCE,
            'unchanged historical executor commit')
    require(not subprocess.check_output(['git','status','--porcelain'],cwd=source_root,text=True), 'clean historical worktree')
    pins=json.loads((BASE/'numeric_input_manifest_r1.json').read_text())
    for row in pins:
        require(sha((source_root/row['source_path']).read_bytes())==row['sha256'],'exact original source '+row['source_path'])
    require(sha((images/'manifest.json').read_bytes())==IMAGE_SHA,'qualified immutable images manifest')
    sys.path.insert(0,str(source_root/'tools'))
    N=importlib.import_module('h3_qwen_bounded_native')
    B=importlib.import_module('qwen_trained_byte_provider')
    native=B.native()
    require(sha(B.canonical(native))=='ab3fe8d6469d6a1552e2eeaa9efe945c025cc35a567f0d8161e3c2a02fc59354',
            'actual fullshape source program')
    backend=B.TrainedByteBackend(images,native)
    machine=N.TiledMachine(native,N.HBMByteTileProvider(backend))
    return N,B,native,backend,machine

def capture(source_root,images,out,*,preflight=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    start=time.monotonic()
    N,B,native,backend,machine=source_runtime(source_root,images)
    import numpy as np
    if preflight:
        result=dict(schema='C0_PC40_ACTUAL_CONSTRUCTOR_PREFLIGHT_R1',source_commit=SOURCE,
                    original_backend_constructed=True,original_executor_constructed=True,
                    arithmetic_executed=False,provider_active=backend.active is not None,
                    maxrss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                    image_manifest_sha256=IMAGE_SHA)
        (out/'preflight.json').write_bytes(canonical(result));backend.close();return result
    historical=json.loads((BASE/'historical_prefix_hashes_r1.json').read_text())
    expected={r['pc']:r for r in historical['records']}
    observations=[];saved={}
    class GateReady(Exception):pass
    def observe(op,store):
        # Observer diagnostics do not contribute physical timing credit.
        entries=[]
        for version in op['writes']:
            digest=hashlib.sha256()
            if version in store.control:
                digest.update(B.canonical(store.control[version]))
            else:
                shape,kind=store.shapes[version];count=2 if kind=='winner' else int(np.prod(shape))
                for i in range(0,count,128):digest.update(store.read(version,i,min(128,count-i)).tobytes())
            entries.append(dict(version=version,shape=list(store.shapes[version][0]),sha256=digest.hexdigest()))
        require(entries==expected[op['pc']]['outputs'],'historical actual producer hash PC'+str(op['pc']))
        observations.append(dict(pc=op['pc'],opcode=op['opcode'],outputs=entries))
        with (out/'producer_progress.jsonl').open('a') as f:
            f.write(json.dumps(observations[-1],sort_keys=True)+'\n');f.flush()
        print(json.dumps(dict(event='SOURCE_PRODUCER_POSTHASH_MATCH',PC=op['pc'],elapsed_s=time.monotonic()-start)),flush=True)
        if op['pc']==35:saved['residual']=store.debug_snapshot(op['writes'][0]).copy()
        if op['pc']==36:saved['rstd']=store.read(op['writes'][0],0,1).copy()
        if op['pc']==39:
            version=op['writes'][0]
            key,lane=store.key(version,0,0)
            require(key==('RF',0,0,38) and lane==0,'actual source gate RF38')
            require(store.owners[key]==version and version in store.published,'actual live published gate lease')
            require(np.array_equal(store.pages[key][0],store.pages[key][1]),'source physical mirror model equality')
            saved['gate']=store.read(version,0,128).copy()
            saved['gate_owner']=dict(version=version,source_key=list(key),lease='value:'+version,
                published=True,logical_source_retire_PC=40,mirror_word_sha256=sha(store.pages[key][0].tobytes()))
            raise GateReady()
    try:
        try:machine.run(9707,0,observer=observe)
        except GateReady:
            # Complete exactly the original run-loop's PC39 retirement. Gate
            # remains live for its actual PC40 consumer; never infer release.
            machine.store.retire(39);machine.done.add(39)
        require(len(observations)==40 and set(machine.done)==set(range(40)),'all source producers complete')
        machine.current_pc=40;machine.vm.current_pc=40
        gate=saved['gate']
        require(gate.dtype==np.float32 and gate.shape==(128,),'actual source gate dtype/aperture')
        negative=machine.kernel('neg',x=gate)
        step=native['microcode']['exp'][0]
        require(step==dict(dst='ex',op='FMAX',src=['x','f32(-87)']),'actual ordered source leaf')
        scalar=N.expression(step['src'][1],dict(x=negative))
        require(np.asarray(scalar).dtype==np.float32,'actual expression literal dtype')
        constant=np.broadcast_to(scalar,(128,)).copy()
        result=machine.vm.run_qwen([step],dict(x=negative),reserved=9+len(machine.stack))
        payloads={name:value.astype('<f4',copy=False).tobytes() for name,value in
                  [('gate',gate),('negative',negative),('constant',constant),('FMAX',result)]}
        for name,raw in payloads.items():
            require(len(raw)==512,'full actual source frame')
            with (out/(name+'.bin')).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        frozen=dict(schema='C0_PC40_NATIVE_PAYLOAD_CAPTURE_R1',source_commit=SOURCE,
                    image_manifest_sha256=IMAGE_SHA,checkpoint_revision=backend.manifest['identity']['checkpoint_revision'],
                    native_PC=40,template='exp',step=0,opcode='FMAX',actual_gate_owner=saved['gate_owner'],
                    operands=dict(a='negative.bin',b='constant.bin'),result='FMAX.bin',
                    frames={n:dict(file=n+'.bin',bytes=len(raw),sha256=sha(raw)) for n,raw in payloads.items()},
                    producer_PC_hash_matches=40,source_call_complete=True,oracle_started=False,
                    input_token=9707,position=0,whole_token_completed=False,scope='bounded source producer replay and one native leaf',
                    real_RF_or_HBM_handshake=False,source_gate_lease_released=False,
                    maxrss_bytes_before_oracle=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                    provider=backend.observations())
        (out/'native_capture.json').write_bytes(canonical(frozen))
        # Oracle imports and checkpoint arithmetic start AFTER immutable native
        # operand/result files and their capture record have been written.
        import torch
        import qwen3_deployment_quality as G
        from qwen_hbm_complete_executor import CheckpointWeights
        torch.set_num_threads(1)
        weights=CheckpointWeights(native['source_program'],backend.manifest['identity']['snapshot'],row_batch=128)
        descriptor=native['source_program']['weight_descriptors']['L0.gu.d0']
        offset,codebytes,scalebytes=next(B.matrix_rows(weights,descriptor,batch=128))
        require(offset==0,'actual first checkpoint weight row block')
        codes=np.frombuffer(codebytes,np.int8).reshape(128,descriptor['K']).copy()
        scales=(np.frombuffer(scalebytes,'<u2').astype(np.uint32)<<16).view(np.float32).copy()
        residual=torch.from_numpy(saved['residual'].copy())[None,:]
        raw=G._chunk_tree_dot_ref(G.to_bf16(residual),torch.from_numpy(codes),descriptor['split'])
        rstd=G.rstd_g(residual,native['source_program']['config']['rms_norm_eps'])[:,None]
        expected_gate=G.mul(G.mul(raw,torch.from_numpy(scales)[None,:]),rstd).numpy().reshape(128)
        expected_negative=(-torch.from_numpy(expected_gate.copy())).numpy()
        expected_FMAX=torch.maximum(torch.from_numpy(expected_negative.copy()),torch.tensor(-87,dtype=torch.float32)).numpy()
        comparisons={}
        for name,actual,expected_value in [('gate',gate,expected_gate),('negative',negative,expected_negative),
                                           ('constant',constant,np.full(128,np.float32(-87))),('FMAX',result,expected_FMAX)]:
            comparisons[name]=dict(words=128,bit_mismatches=int(np.count_nonzero(actual.view(np.uint32)!=expected_value.view(np.uint32))),
                                   actual_nonfinite=int(np.count_nonzero(~np.isfinite(actual))),
                                   expected_sha256=sha(expected_value.astype('<f4',copy=False).tobytes()))
        verdict='PASS' if all(v['bit_mismatches']==0 and v['actual_nonfinite']==0 for v in comparisons.values()) else 'FAIL'
        terminal=dict(schema='C0_PC40_CHECKPOINT_PAYLOAD_PROOF_R1',verdict=verdict,
                      comparisons=comparisons,oracle_only_after_capture=True,oracle_input_injection=False,
                      original_source_executor=True,native_gate_matches_historical_hash=True,
                      independent_checkpoint_gate_compare=True,checkpoint_provenance=weights.provenance(),
                      maxrss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                      elapsed_s=time.monotonic()-start,hardware_admitted=False,installed_workspace_call=False,
                      workspace_slots_17_18_19_scope='prospective until calendar/lease adapter joins')
        (out/'terminal.json').write_bytes(canonical(terminal))
        require(verdict=='PASS','actual checkpoint operand/output mismatch')
        return terminal
    except BaseException as error:
        if not (out/'terminal.json').exists():
            (out/'terminal.json').write_bytes(canonical(dict(verdict='FAIL',error=repr(error),source_commit=SOURCE,
                completed_producer_PCs=len(observations),elapsed_s=time.monotonic()-start,hardware_admitted=False)))
        raise
    finally:backend.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--images',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--preflight',action='store_true');a=p.parse_args()
    print(json.dumps(capture(a.source_root,a.images,a.out,preflight=a.preflight),sort_keys=True))

if __name__=='__main__':main()
