#!/usr/bin/env python3
"""Staged process proof: actual QK -> actual SU exp -> actual PV -> actual SU divide.

Requires the attention capture harness with +capture=<dir> and +rows=<T>.
Captures are head-major FP32 hex from actual SC/PV ports.
This is functional composition across process/file boundaries. Per-process cycle
counts cannot establish live composition latency or overlap.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import numpy as np
import rtl_hdc_v41x_attn_campaign as A
import rtl_hdc_v41x_vec_campaign as C
import rtl_v41x_su_softmax_campaign as S


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def capture(path, width):
    words=C.read_hex(path).astype(np.uint32)
    assert len(words)==16*width
    return words.reshape(16,width)


def decode_kv(path,tokens):
    out=np.zeros((tokens,512),np.float32)
    rows=Path(path).read_text().splitlines()
    assert len(rows)==tokens
    for t,line in enumerate(rows):
        row=int(line,16)
        for g in range(16):
            w=(row>>(265*g)) & ((1<<265)-1)
            fmt=(w>>264)&1
            for i in range(32):
                code=(w>>((4 if fmt else 8)*i)) & (15 if fmt else 255)
                scale=(w>>(128+8*(i//16) if fmt else 256))&255
                out[t,g*32+i]=A.deq_value(fmt,code,scale)
    return out


def run_attention(exe,d,label,tokens):
    cap=d/f'{label}_capture';cap.mkdir(exist_ok=True)
    sc=cap/'actual_scores_fp32.hex';pv=cap/'actual_pv_fp32.hex'
    cmd=[str(exe),f'+dir={d}','+njob=1',f'+capture={cap}',f'+rows={tokens}']
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=1800)
    log=d/f'{label}.log';log.write_text(r.stdout+r.stderr)
    summary=re.search(r'V41XATTN jobs=1 sc_checked=(\d+) sc_errors=(\d+) pv_checked=(\d+) pv_errors=(\d+) faults=(\d+).*?cycles=(\d+) timeout=(\d+)',r.stdout)
    assert r.returncode==0 and summary, (r.returncode,str(log))
    scc,sce,pvc,pve,faults,cycles,timeout=map(int,summary.groups())
    assert sce==pve==faults==timeout==0 and pvc==8192 and scc==16*tokens, str(log)
    return sc,pv,dict(cycles=cycles,scores_checked=scc,pv_checked=pvc,log_sha256=sha(log),
        capture_metadata=(cap/'capture.txt').read_text().strip(),
        capture_sha256={'scores':sha(sc),'pv':sha(pv)},
        job_trace=[line for line in r.stdout.splitlines() if line.startswith('V41XJOB ')])


def run_su(exe,d,tokens,scores,pv=None):
    mem,ops,expected,regions=S.fixture(tokens,scores,pv)
    C.write_case(d,mem,ops)
    tr=C.run_case(exe,d,4)
    assert tr['end'][1]=='ok' and tr['faults']==tr['orders']==0
    assert tr['kv'] is not None and np.array_equal(tr['kv'],mem.kv)
    assert np.array_equal(tr['vm'],expected.vm), 'actual SU whole VM differs from independent golden'
    return tr,dict(accepted_cycles=tr['acc'],end_cycle=tr['end'][0],
                   last_reducer_cycles={str(k):max(v) for k,v in tr['ress'].items()},
                   whole_vm_mismatches=0,vm_sha256=sha(d/'vmo.hex'))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--attention-exe',type=Path,required=True)
    ap.add_argument('--su-exe',type=Path,required=True)
    ap.add_argument('--vectors',type=Path,required=True)
    ap.add_argument('--output-dir',type=Path,required=True)
    ap.add_argument('--source-kind',choices=('standalone-attention','connected-window'),default='standalone-attention')
    args=ap.parse_args()
    d=args.output_dir.resolve();d.mkdir(parents=True,exist_ok=True)
    src=args.vectors.resolve()
    assert d!=src
    for path in src.glob('*.hex'):shutil.copy2(path,d/path.name)
    jobs=(d/'jobs.hex').read_text().splitlines();assert len(jobs)==1
    tokens=int(jobs[0],16)&0xffffffff;assert tokens in (128,640)
    kv=decode_kv(d/'kv.hex',tokens)
    # Probe computes QK with zero PV operands; they are never used for final PV.
    A.write_hex(d/'p.hex',[0]*(tokens//2),512)
    A.write_hex(d/'pv.hex',[0]*512,528)
    sc,_,qk_record=run_attention(args.attention_exe.resolve(),d,'qk_probe',tokens)
    words=capture(sc,tokens)
    scores=d/'actual_qk_head_major.hex';C.write_hex(scores,words.reshape(-1),32)
    tr,su_record=run_su(args.su_exe.resolve(),d/'su_exp',tokens,scores)
    exp=A.V.to_bf16(C.ffrom(tr['vm'][:16*tokens]).reshape(16,tokens))
    bf=A.bf16_bits(exp).T.reshape(-1)
    A.write_hex(d/'p.hex',[sum(int(bf[i+j])<<(16*j) for j in range(32)) for i in range(0,len(bf),32)],512)
    # Golden is only the comparison operand; actual p.hex comes from SU RTL VM.
    expected_pv=A.golden_dot(exp,kv.T)
    A.write_hex(d/'pv.hex',[A.pack_vals(expected_pv[:,i]) for i in range(512)],528)
    sc2,pv,pv_record=run_attention(args.attention_exe.resolve(),d,'actual_exp_pv',tokens)
    assert np.array_equal(capture(sc2,tokens),words)
    pv_words=capture(pv,512)
    assert np.array_equal(pv_words,A.u32(expected_pv).astype(np.uint32))
    accumulator=d/'actual_pv_head_major.hex';C.write_hex(accumulator,pv_words.reshape(-1),32)
    final,epilogue_record=run_su(args.su_exe.resolve(),d/'su_epilogue',tokens,scores,accumulator)
    C.write_hex(d/'actual_final_bf16.hex',final['vm'][17408:17408+8192]>>16,16)
    paths=[d/x for x in ('jobs.hex','sc.hex','pv.hex','q.hex','kv.hex','window_blocks264.hex','actual_qk_head_major.hex','p.hex','actual_pv_head_major.hex','actual_final_bf16.hex') if (d/x).exists()]
    report=dict(status='pass',proof='staged process arithmetic chain; no live latency or overlap claim',
        source_kind=args.source_kind,heads=16,tokens=tokens,head_dim=512,sink='float32(head/16 - 0.5)',
        arithmetic='scale max; exp sum; BF16 exp to PV; exp(sink-max)+sum; divide PV then BF16',
        executables_sha256={'attention':sha(args.attention_exe),'su':sha(args.su_exe)},
        intermediate_sha256={p.name:sha(p) for p in paths},
        stages=dict(qk_probe=qk_record,su_exp=su_record,actual_exp_pv=pv_record,su_epilogue=epilogue_record))
    (d/'chain.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
