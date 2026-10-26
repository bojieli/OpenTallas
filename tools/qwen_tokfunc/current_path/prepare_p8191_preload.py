#!/usr/bin/env python3
"""Separate actual P8191 prehistory from expected new-row/attention outputs for a live compute peer."""
import argparse,hashlib,json,shutil
from pathlib import Path

def prepare(vectors,out):
    if out.exists():raise ValueError('refuse existing output')
    m=json.loads((vectors/'meta.json').read_text());r=m['real_token']
    assert m['ctx']==8192 and m['position']==8191 and m['groups']==3072 and m['attn_splits']==[128,256]
    assert r['kv_pre_p_row_zero'] and r['kv_fp8_representable'] and r['tp4_repro_word_mismatch']==0
    rows=(vectors/'kv.hex').read_text().splitlines();assert len(rows)==16384 and all(len(x)==256 for x in rows)
    expected=rows[:];rows[8191]=rows[16383]='0'*256
    out.mkdir(parents=True);(out/'reference').mkdir()
    (out/'kv.hex').write_text('\n'.join(rows)+'\n')
    (out/'reference/kv_expected_after.hex').write_text('\n'.join(expected)+'\n')
    for name in ['q.hex','gold.hex','check.hex']:shutil.copyfile(vectors/name,out/'reference'/name)
    hashes={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*.hex')}
    result=dict(schema='opentallas.qwen.p8191.native_preload.v1',layer=0,context_total=8192,past_valid_rows=8191,position=8191,
        load_file='kv.hex',kv_format='FP8E4M3,dim0=LSBbyte;8192Krows then8192Vrows;TP8die0/head0',
        last_k_v_rows_zero=True,new_row_source='must be written by actual bound QC producer through real D2D/nativeKV',
        reference_only='reference/ files must never drive new Q/K/V or serve as a compute endpoint',
        source_history_sha256='14ba2f92c1bd0fdcf2d80a62c5fe754ecf99f90b0929ec53ebd1c7cce6aee87a',
        runtime_layout=dict(k='(t//16)*2048+d*16+t%16',v='2*1048576+t*128+d',head=0),
        ctx_qualification='8191 prior positions plus actual newposition8191 =>8192 attention rows; native consumer still needs qualification',
        tp4_reproduction_mismatches=0,tp8_vs_tp4_attn=r['tp8_vs_tp4_attn'],hashes=hashes,
        qualification='INPUT_READY_ONLY; no native boot/setup/physical/token verdict')
    (out/'preload.json').write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(result))
if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--vectors',type=Path,required=True);a.add_argument('--out',type=Path,required=True);p=a.parse_args();prepare(p.vectors,p.out)
