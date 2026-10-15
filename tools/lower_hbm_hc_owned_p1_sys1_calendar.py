#!/usr/bin/env python3
"""Prepared owned-row P1 HC component; no canonical wholeprofile claim."""
import argparse,json
from pathlib import Path
from lower_hbm_hc_mtp_static_calendar import pack,lower

def prepare(rank=3,first_row=4096,sys_latency=86):
    lo,hi=24*rank//96,24*(rank+1)//96
    if hi-lo!=1:raise ValueError('G22 rank has no single owned row')
    delta=sys_latency-33
    if delta<0:raise ValueError('SYS latency')
    gather=first_row+400;tail=first_row+448
    tw,tm=lower('tail',first_consumer_cycle=tail,sink_divisor=7,sink_phase=0,tail_position=0)
    payload=[pack(row_npos=1,row_id=lo,norm_eps=0x358637bd) for _ in range(448)]
    payload[0]|=pack(row_launch=1,clear=1)
    for c in (160+delta,264+delta):payload[c]|=pack(row_raw_read=1)
    payload+=[w&((1<<51)-1) for w in tw]
    image=[(0xc7a1<<240)|(pc<<223)|w for pc,w in enumerate(payload)]
    assert len(image)<=2048 and sum(bool(w&2) for w in image)==1
    meta={'status':'PREPARED_NOT_RUN','scope':'G22 owned-row rank3 shape plus G25 P1 gather descriptor, not a canonical wholeprofile or actual HCOLLproducer',
      'ownership':{'TP':96,'rows':24,'rank':rank,'lo':lo,'hi':hi,'formula':'lo=24*rank//96;hi=24*(rank+1)//96;owner(row)=4*row+3','G25_rank0_row':'NOP'},
      'ROW_LOOP':0,'TAIL_LOOP':0,'npos':1,'nout':1,'chosen_row':lo,'SYS_LAT':sys_latency,'SYS_DELTA':delta,'configuration_words':len(image),'start_base':0,'start_limit':len(image),'start_loops':1,'programme_start':first_row-5,'first_row_consumer':first_row,
      'raw_SS':first_row+160+delta,'raw_row':first_row+264+delta,'expected_owned_result':first_row+269+delta,
      'weight_drain':{'first_edge':2048,'interval_cycles':640,'valid_beats':320,'valid_every':2,'last_macro_commit_expected':2687,'native_PHY_prefetch':'DECLARED aperture fixture, parent owns actualprefetch join'},
      'residual_fill':{'first_edge':16,'waves':80,'last_input_edge':95,'extra_input_register_edge':1,'source':'synthetic BF16-valued fixture'},
      'gather':{'launch':gather,'npos':1,'base_sector':18136,'stride':0,'engine_first':gather+21,'engine_last':gather+44,'phase_end_inclusive':gather+44,'payload':'all24 declared post-collective golden mixes from actualVM SRAM; owned row checked independently before landing'},
      'tail_launch':tail,'tail':tm['events_relative_consumer0'],'sink_divisor':7,'sink_phase':0,'clock_roots':92,'physical_phase':'NOT qualified; equalphase functional roots and divided sink only','actual_SRAMs':106,'bench_launch_authorized':False,'canonical_wholeprofile_qualified':False,'physical_qualified':False}
    return image,meta

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    w,m=prepare();(a.out/'owned_p1_programme.mem').write_text(''.join(f'{x:064x}\n' for x in w));(a.out/'model.json').write_text(json.dumps(m,indent=2)+'\n')
    print('Prepared rank3/row0 P1 image; no RTL build/simulation launched')
if __name__=='__main__':main()
