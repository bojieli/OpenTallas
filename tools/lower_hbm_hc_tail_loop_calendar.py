#!/usr/bin/env python3
"""Price-preserving fixed-phase repeated HC tail image; component calendar only."""
import argparse,hashlib,json
from pathlib import Path
from lower_hbm_hc_mtp_static_calendar import lower

def lower_tail_loop(*,first_consumer_cycle,sink_divisor=7,sink_phase=0,npos=8):
    if npos not in (6,8):raise ValueError('production tail loop supports6/8 positions')
    words,meta=lower('tail',first_consumer_cycle=first_consumer_cycle,sink_divisor=sink_divisor,sink_phase=sink_phase,tail_position=0)
    unpadded=len(words)
    padded=((len(words)+sink_divisor-1)//sink_divisor)*sink_divisor
    # Pad with actual valid programme words: real PC identity and zero controls.
    for pc in range(len(words),padded):words.append((0xc7a1<<240)|(pc<<223))
    meta.update({'kind':'tail_loop','start_limit':padded,'start_loops':npos,'TAIL_LOOP':1,'period_cycles':padded,
        'phase_preserved':padded%sink_divisor==0,'unrolled_duration_cycles':npos*padded,
        'configuration_words':padded,'previous_configuration_words':npos*unpadded,
        'scope':'real issuer image only; no arithmetic/physical/clock/rate qualification or repricing'})
    return words,meta

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    model={}
    for n in (6,8):
        words,meta=lower_tail_loop(first_consumer_cycle=2051,npos=n)
        assert len(words)==497 and meta['events_relative_consumer0']['sink_launch']==203
        assert meta['events_relative_consumer0']['sink_capture']==492 and meta['events_relative_consumer0']['result']==493
        for k in range(n):assert (2051+k*497+203)%7==0
        path=a.out/f'tail_n{n}.mem';path.write_text(''.join(f'{w:064x}\n' for w in words))
        meta['image_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();model[f'n{n}']=meta
    (a.out/'model.json').write_text(json.dumps(model,indent=2)+'\n')
if __name__=='__main__':main()
