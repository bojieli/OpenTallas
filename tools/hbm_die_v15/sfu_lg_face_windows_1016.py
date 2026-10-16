#!/usr/bin/env python3
"""Exact partial SFU LG bit windows, no endpoint physical qualification."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def track(x):return round(.012+round((x-.012)/.048)*.048,6)
def main():
    path=Path('/home/ubuntu/wt/hnl-0030/results/arch/hbm_die_v16/source_compact_0253/contract.json');raw=path.read_bytes();c=json.loads(raw);i=c['instances']['sfucore_SW'];fields=[('local_rq','c_rq',34,'f'),('local_wq','c_wq',562,'f'),('local_rr','c_rr',514,'b'),('local_w_done','c_w_done',2,'b')]
    assert all(i['ports'][name]['bits']==4*bits for name,peer,bits,direction in fields)
    pairs=[]
    for g in range(4):
        start=track(15.456+g*190.896);target=track(320.016 if g==2 else 170.016);pins=[];index=0
        for name,peer,bits,direction in fields:
            assert c['instances'][f'sfu_SW{g}']['ports'][peer]['bits']==bits
            for k in range(bits):
                pins.append(dict(source_port=f'{name}[{g*bits+k}]',peer_port=f'{peer}[{k}]',direction=direction,source_offset_um=round(start+index*.144,6),peer_offset_um=round(target+index*.144,6)));index+=1
        pairs.append(dict(group=g,pins=pins,source_face='N',peer_face='N',source_slot_um=[start,start+1111*.144],peer_slot_um=[target,target+1111*.144],source_f_escape_um=sum(p['source_offset_um'] for p in pins if p['direction']=='f')/596,source_b_escape_um=sum(p['source_offset_um'] for p in pins if p['direction']=='b')/516,peer_f_escape_um=sum(p['peer_offset_um'] for p in pins if p['direction']=='f')/596,peer_b_escape_um=sum(p['peer_offset_um'] for p in pins if p['direction']=='b')/516))
    allpins=[p for v in pairs for p in v['pins']];assert len({p['source_port'] for p in allpins})==4448
    out=dict(schema='opentallas.hbm.sfu_lg_face_windows.v1',qualification='PARTIAL_ABI_PIN_PROPOSAL_NO_NATIVE_ENDPOINT_VIEW',source_contract_sha256=hashlib.sha256(raw).hexdigest(),source_master=i['master'],source_params=i['params'],unadopted_R23_param_delta={'LG_PATH':24},source=str(path),pairs=pairs,total_source_bits=4448,source_face_utilization=4448*.096/763.56,peer_face_utilization=1112*.096/500,
             transform='canonical SW N face; other quarters require actual mirrored master pins/clock roots, not aliases',open=['actual SFU endpoint views/native pin arcs','remaining full source/core ports and clocks','M5 PG/OBS and whole-face assignment','actual reset/clock station kit and source compiler adoption'])
    d=ROOT/'results/arch/hbm_die_v15/core4_sfu2_wide';(d/'sfu_lg_face_windows.json').write_text(json.dumps(out,indent=1)+'\n');print(out['source_face_utilization'])
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,1,figsize=(13,4.5))
    for pair in pairs:
        for direction,color in [('f','#2878bb'),('b','#dc8225')]:
            pp=[p for p in pair['pins'] if p['direction']==direction];lo=pp[0]['source_offset_um'];hi=pp[-1]['source_offset_um']
            axes[0].plot([lo,hi],[0,0],linewidth=13,color=color)
            axes[0].text((lo+hi)/2,.18,f"LG{pair['group']} {direction} {len(pp)}b",ha='center',fontsize=8)
            if pair['group']==2:
                lo=pp[0]['peer_offset_um'];hi=pp[-1]['peer_offset_um'];axes[1].plot([lo,hi],[0,0],linewidth=13,color=color);axes[1].text((lo+hi)/2,.18,f'{direction} {len(pp)}b',ha='center',fontsize=8)
    axes[0].set(xlim=(0,763.56),ylim=(-.3,.4),yticks=[],title='Partial source-pinned core N face: four independent1112-bit LG windows; all4448 bits exactly once; utilization0.559233',xlabel='canonical face offset um')
    axes[1].axvspan(0,244,color='#d9d9d9',label='upper-side store blocks vertical approach here (geometry only)')
    axes[1].set(xlim=(0,500),ylim=(-.3,.4),yticks=[],title='LG2 peer N face: active windows shift to320..480um, clear of adjacent SFUS approach',xlabel='canonical peer face offset um')
    axes[1].legend(loc='lower left',fontsize=7)
    fig.suptitle('ABI pin proposal only: actual endpoint views, full other ports, clocks, PG/OBS and transformed masters remain OPEN',fontsize=10)
    fig.tight_layout();fig.savefig(d/'sfu_lg_face_windows.png',dpi=160);plt.close(fig)
if __name__=='__main__':main()
