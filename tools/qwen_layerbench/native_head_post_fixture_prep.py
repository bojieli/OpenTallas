#!/usr/bin/env python3
"""Prepare genuine BTAB/command requirements for selected native S8 post cone.

No numerical stimulus is fabricated. TG4 raw partials are not full logits.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import dv_lower as D

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('calr-object','btab','scale-image','source-readset','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 cal=json.loads(a.calr_object.read_text());bt=json.loads(a.btab.read_text());sc=[int(x,16)for x in a.scale_image.read_text().split()]
 assert len(sc)==1200
 cmds=[dict(source_index=x['old_index'],word=x['cmd'],decoded=D.decode_cmd(int(x['cmd'],16)))for x in cal['retained_head_commands']]
 stns=[x for x in cmds if x['decoded']['kind']==2];assert len(stns)==298 and {x['decoded']['kc']for x in stns}=={8}
 receivers=[x for x in stns if x['decoded']['amax']];assert sorted({x['decoded']['dst']for x in receivers})==[1,3,5,6,8,10] and len(receivers)==149
 fixtures=[];boot={}
 for block,dst,base,nwords,scale0 in [(0,1,72,8,0),(148,8,264,3,1184)]:
  rx=next(x for x in receivers if x['decoded']['dbase']==128*block)
  d=rx['decoded'];assert (d['dst'],d['mode'],d['sbase'],d['nwords'],d['wsrc'])==(dst,2,base,nwords,0)
  sender=next(x for x in stns if x['source_index']==rx['source_index']-1);assert sender['decoded']['dst']==dst^1 and sender['decoded']['mode']==3 and sender['decoded']['nwords']==nwords
  for j in range(nwords):
   address=(base+j)&~3;record=next(x for x in bt if x['slice']==dst and x['kind']==2 and x['addr']==address)
   payload=int(record['payload_hex'],16);word=(payload>>(256*((base+j)%4)))&((1<<256)-1)
   assert word==sc[scale0+j],(block,j)
   boot[(dst,address)]=record
  fixtures.append(dict(block=block,receiver=dst,sender=dst^1,rows=[128*block,128*block+16*nwords],words=nwords,KC=8,sbase=base,BTAB_words=list(range(base,base+nwords)),genuine_scale_words=list(range(scale0,scale0+nwords)),sender_command=sender,receiver_command=rx,
   component_inputs=dict(region0='two lanes from each actual own L6 port fs/ns/fn/nn, plus real neighbor L8 word',full_vector='all8 two-lane regions simultaneously;16lane word for actual per-userAMAX',streams_per_pair=8,raw_K_blocks=8,raw_words_per_stream=8*nwords,final_scaled_vectors=nwords),
   expected_addresses=[128*block+16*j for j in range(nwords)],row_scale_rule='Each final16-row vector multiplies the corresponding genuine BF16 BTAB word after full512split tree. No scale before global sum.'))
 records=[boot[k]for k in sorted(boot)];assert len(records)==3
 (a.out/'genuine_btab_boot_records.json').write_text(json.dumps(records,indent=2)+'\n')
 record=dict(status='SELECTED_POST_SOURCE_AND_GENUINE_FIXTURE_REQUIREMENTS_ONLY',readset={str(x):sha(x)for x in [a.calr_object,a.btab,a.scale_image,a.source_readset]},selected_sources=json.loads(a.source_readset.read_text()),fixtures=fixtures,
  smallest_numeric_cone=dict(sender='sl_W5_st_a.u_u_r0 / qfd_dv_s8_station_tail1_nb0',receiver='sl_W4_st_a.u_u_r0 / qfd_dv_s8_station_tail1',region_lanes=2,shared_scale_store='qfd_dv_s6_btab -> qfd_dv_s5_btab_s4 -> qfd_dv_s5_btab_safe ->4actual128x256SRAMs',parameters=dict(ADD_LAT=7,SCALE_LAT=7,SKEW=14,JB=8,PIN_IN=1,BT_LAT=1),input_boundary='actual L6 collector ports; not bare TG4 partial',output_boundary='two final scaledFP32lanes +r_v/r_idx/r_last; fullAMAXrequires8regions'),
  arithmetic_order='KC8 selects lastK; ylo=add(fs,ns),yhi=add(fn,nn),ownL8=add(ylo,yhi);sender emits ownL8;receiver adds heldownL8+neighborL8;then BF16 row-scale mul',
  AMAX_boundary=dict(module='qfd_dv_amax_mu NU4 under selected qfd_dv_s5_ctl_repair4_leaf',result_address='stn_dbase+(r_idx<<4)+lane; global rank offset already in STNdbase',events='STNuser/amax captured on actual command; sixreceiveronlyclear;8stationregionresults formfull16lanevector; taggedcandidate am_v/am_idx/am_val/am_u to selectedscalarup/root',scope='No full logit or token claim until full512split collector values and root transport are supplied'),
  still_required=['Canonical H4096 BF16 projection and genuine selected INT8 rows for blocks0 and148 across all4096columns, without checkpoint regeneration','Actual collector source mapping of8L6 streams to group/column intervals and exactRNE tree order; do not replace64-group L6 values with4-group tile0 values','KC8 complete intermediate-prefix sequences for each64-group stream:8 K blocks in slot order, not only finalK7 data','Actual selected pair neighbor transport publication/own9 lead and sharedBTAB response contract from frozen wrappers; no fittedlatency','Eightregion assembly/r_v coherence for16laneAMAX; realtagged6candidateROOTinterface; no fake ME ready/results'],
  qualification='No RTL compile/simulation/heavy dispatch; genuineBTAB data join only; no genericPART2 substitute')
 (a.out/'post_fixture_requirements.json').write_text(json.dumps(record,indent=2)+'\n');print(record['status'],'boot_records',len(records))
if __name__=='__main__':main()
