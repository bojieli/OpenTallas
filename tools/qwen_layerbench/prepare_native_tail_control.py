#!/usr/bin/env python3
"""Prepare a real-data station counter witness, not a full L6 numeric fixture."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hdc_golden as G
import numpy as np


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('capture','scales','boot','stage','out'):
        p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    if sha(a.capture)!='c3db0ddac19d2e7d4803ca2300eb3409d16aef47279c44fbf2660b7899e815b3':
        raise ValueError('requires unchanged actual native prefix capture')
    if sha(a.scales)!='df41b740b4cbbe3cdf67fae428cfbf081513269412baca49f5fcf15ccc9d3674' or sha(a.boot)!='8b46afb9e1b98102495ec07a447405ad3b481d923f27d0287e4c92874eb7c762':
        raise ValueError('requires unchanged genuine scale/boot source from completed post gate')
    captured=[]
    for line in a.capture.read_text().splitlines():
        if line.startswith('#'):
            continue
        ordinal,when,value=line.split()
        if int(ordinal)!=len(captured):
            raise ValueError('actual prefix order changed')
        captured.append(int(value,16))
    if len(captured)!=1600:
        raise ValueError('complete actual capture required')
    cadence=[int(line.split()[1]) for line in a.capture.read_text().splitlines() if not line.startswith('#')][:512]
    if any(b-a!=833000 for a,b in zip(cadence,cadence[1:])):
        raise ValueError('actual first8-round raw publication cadence changed')
    captured=captured[:128]
    scales=[int(x,16)for x in a.scales.read_text().split()]
    boots=a.boot.read_text().split()
    if len(scales)!=1200 or len(boots)!=3:
        raise ValueError('actual complete scale and boot fixture required')
    stage=json.loads(a.stage.read_text())
    if stage['stage']!=37:
        raise ValueError('actual linked HEAD stage required')
    bt={x['addr']:int(x['payload_hex'],16) for s in stage['slices'] if s['slice']==1 for x in s['btab']}
    if [bt[x] for x in [72,76]]!=[int(x,16) for x in boots[:2]]:
        raise ValueError('actual stage BTAB differs from completed post source')
    bt_words=[(bt[72+4*(i//4)]>>(256*(i%4)))&((1<<256)-1) for i in range(16)]
    if bt_words[:8]!=scales[:8] or bt_words[8:]!=scales[48:56]:
        raise ValueError('native receiver contiguous BTAB round mapping changed')
    def control_gold(ordinal,slot):
        v=G.from_bits(np.array([(captured[ordinal]>>(32*i))&0xffffffff for i in range(2)],dtype=np.uint32))
        # Eight input ports deliberately reuse the captured TG4 word. This is
        # nonzero control stimulus, never a claim about real L6 tree values.
        pair=G.add(v,v);own=G.add(pair,pair);total=G.add(own,own)
        bf=np.array([(bt_words[slot]>>(16*i))&65535 for i in range(2)],dtype=np.uint32)
        result=G.bits(G.mul(total,G.from_bits(bf<<16)))
        return int(result[0])|(int(result[1])<<32)
    good=[control_gold((i//8)*64+56+(i%8),i)for i in range(16)]
    bad=[control_gold(21+i,i)for i in range(3)]
    if good[:3]==bad:
        raise ValueError('real control data fails to distinguish old prefix selection')
    a.out.mkdir(parents=True,exist_ok=False)
    for name,words,width in [('captured_TG4_128.hex',captured,128),('good16.hex',good,16),('bad3_first.hex',bad,16),('genuine_btab_four_records.hex',[bt[x]for x in [72,76,80,84]],256)]:
        (a.out/name).write_text(''.join(f'{word:0{width}x}\n'for word in words))
    r=dict(status='SOURCE_CONTROL_FIXTURE_NOT_EXECUTED',source_sha256={str(x):sha(x)for x in [a.capture,a.scales,a.boot,a.stage,Path(G.__file__)]},
           data='first128 actual TG4 prefix words, low2 lanes replayed identically at8 independent station control-test input ports',
           actual_cadence='first512 captured fullleaf publications have511 consecutive833000fs deltas; includes63to64 and127to128',
           scope='counter/control witness only; input words are not full L6 sums and output gold is not a genuine LM logit',
           DUT='actual unchanged tail1 sender/receiver, genuine shared BTAB rows72..87, nominal833ps/SKEW14/direct neighbor boundary',
           cases=dict(raw8='64 accepted words; actual KC8 selects56..63',bad3='64 accepted words; actual KC8/nwords3 selects21..23/45..47 and faults at fourth receiver fv',keep3='external contract model only:64 physical slots, publishj<3;24accepted words select56..58, no implemented publisher repair',round16='128continuous words, one NWORDS16 descriptor,16selected outputs with genuine contiguous receiver scales',cfg_between='128continuous words, NWORDS8 descriptor replaced at raw round boundary; intrinsic cfg_schedule_fault expected'),
           intended_repair='separate selected-source placement and ABI event required; this external keep model does not qualify an RTL implementation',
           output_sha256={x.name:sha(x)for x in a.out.glob('*.hex')})
    (a.out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
    print(r['status'], 'actual_words',len(captured),'full_L6_claim',False)


if __name__=='__main__':
    main()
