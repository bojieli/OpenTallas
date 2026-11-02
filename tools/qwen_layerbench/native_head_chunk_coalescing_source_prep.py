#!/usr/bin/env python3
"""Source/record assessment of continuous multi-round HEAD and opt-in STN stride."""
import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ['capture','calendar','btab-proof','pc-proof','out']:p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
assert hashlib.sha256(a.capture.read_bytes()).hexdigest()=='c3db0ddac19d2e7d4803ca2300eb3409d16aef47279c44fbf2660b7899e815b3'
records=[x.split()for x in a.capture.read_text().splitlines()if not x.startswith('#')];assert len(records)==1600 and [int(x[0])for x in records]==list(range(1600))
cadence=[]
for first,count in [(0,512),(512,512),(1024,512),(1536,64)]:
 times=[int(x[1])for x in records[first:first+count]];deltas=[b-a for a,b in zip(times,times[1:])];assert set(deltas)=={833000}
 cadence.append(dict(first_raw=first,count=count,consecutive_deltas=len(deltas),all_delta_fs=833000,round_boundaries=[dict(a=i-1,b=i,delta_fs=int(records[i][1])-int(records[i-1][1]))for i in range(first+64,first+count,64)]))
cal=json.loads(a.calendar.read_text());stns={}
for x in cal['retained_head_commands']:
 w=int(x['cmd'],16)
 if (w>>1)&7==2:
  assert not((w>>67)&1)
  stns[x['old_index']]=dict(word=w,dst=(w>>112)&15,mode=(w>>4)&3,nwords=(w>>7)&255,sbase=(w>>15)&511,dbase=(w>>26)&0xffffff,kc=((w>>59)&255)+1)
assert len(stns)==298
rx={}
for idx,x in stns.items():
 if x['mode']==2:
  r=x['dbase']//768;q=(x['dbase']%768)//128;assert x['dbase']==768*r+128*q and x['kc']==8 and x['sbase']==72+8*r
  rx[q,r]=(idx,x)
coalesced=[];allrows=[];allold=set();receivers=[1,3,5,6,8,10];senders=[0,2,4,7,9,11]
for chunk,r0 in enumerate([0,8,16,24]):
 for q in range(6 if r0<24 else 5):
  rounds=8 if r0<24 else 1;idx,old=rx[q,r0];nw=64 if rounds==8 else old['nwords'];tx=stns[idx-1];assert tx['mode']==3 and tx['dst']==senders[q]and old['dst']==receivers[q]
  for r in range(r0,r0+rounds):
   oi,ow=rx[q,r];assert ow['sbase']==old['sbase']+8*(r-r0);allold.update([oi-1,oi])
  tw=(tx['word']&~(255<<7))|(nw<<7);rw=(old['word']&~(255<<7))|(nw<<7)|(1<<67)
  addrs=[old['dbase']+768*(j//8)+16*(j%8)for j in range(nw)]
  original=[rx[q,r][1]['dbase']+16*j for r in range(r0,r0+rounds)for j in range(rx[q,r][1]['nwords'])]
  assert addrs==original
  for addr in addrs:allrows.extend(range(addr,addr+16))
  coalesced.append(dict(chunk=chunk,q=q,round_first=r0,rounds=rounds,TX=dict(dst=tx['dst'],nwords=nw,word=f'{tw:029x}'),RX=dict(dst=old['dst'],nwords=nw,sbase=old['sbase'],dbase=old['dbase'],head_stride_bit67=1,word=f'{rw:029x}'),BTAB_words=list(range(old['sbase'],old['sbase']+nw)),addresses=addrs,dates='UNASSIGNED;actualcfg/drain/newleaseproofrequired'))
assert len(coalesced)==23 and len(allold)==298 and sorted(allrows)==list(range(18992)) and len(allrows)==len(set(allrows))
for idx in range(256):
 q=idx>>3;threeq=(q<<1)+q;offset=(threeq<<8)|((idx&7)<<4);assert offset==768*(idx>>3)+16*(idx&7) and threeq<128 and offset<(1<<15)
root=Path('/home/ubuntu/OpenTallas');part=root/'rtl/physical/a0_rc14_selected_2000/ot_qwen_w12_matvec_land32.sv';station=root/'rtl/qwen_dv/s5/s8/qfd_dv_s8_station_tail1.sv';ctl=root/'rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv';hard=root/'rtl/qwen_dv/s5/qfd_dv_s5_ctl_repair4_leaf.sv'
assert 'wire             j_last = (j == IL - 1);'in part.read_text()
assert 'wire cfg_schedule_fault=(cfg_v||cfg_mid||cfg_final[0])&&(rs_s_c[0]||rs_s_c[2]||rs_n_c[0]||rs_n_c[2]||nb_c[0]);'in station.read_text()
assert "wire [23:0] r_addr = stn_dbase + {12'd0, r_idx, 4'd0};"in ctl.read_text()
assert 'else if (c_stn) begin stn_left <= {1\'b0, cmd_q[14:7]};'in ctl.read_text()
result=dict(status='SOURCE_COALESCING_PROPOSAL_NOT_IMPLEMENTED_OR_EXECUTABLE',actual_capture_cadence=cadence,broader_hazard='512consecutive rawvalids per8round nativecommand; no realcollector addsround-aware holes. AnySTNreconfigurationwithinthisstreamoverlapscfg_v/mid/final withnear/farvalid; singlecfgstatehasnoFIFO. Existing24wordonecontextpostPASSdoesnotqualify8roundreconfiguration.',preferred_candidate=dict(GME='retain4actual8/8/8/1MEinstructions+END;5fixedissuerowsfitcurrentDEPTH8',STNs=46,pairs=23,old_STNs=298,saved_CALR_entries=252,four_entry_alignment_preserved=True,authority='current68fS8KC8object;notlegacyKC1calendar_candidate',nent_change='1021→769 ifallotherentries/paddingunchanged;local37first1020→768',coalesced_commands=coalesced,full_real_rows_exactly_once=18992),BTAB_source_proof=json.loads(a.btab_proof.read_text()),address_stride=dict(default_off=True,formula='r_addr=stn_dbase+768*(r_idx>>3)+16*(r_idx&7)',equivalent='oldlinear+640*(r_idx>>3)',small_logic='q=r_idx[7:3];threeq=3*q sevenbits;headoffset={9zero,threeq[6:0],0,r_idx[2:0],4zero};onlyoffsetbits14:7need8bitmux; existing24bitdbaseadder retained',widths='all256r_idxvalues checked;NWORDS64 andr_idx0..63fit8bits,SBASEmax271fit9bits',flag_proposal='source-onlynewSTNbit67 (all298currentSTNs0;KC59..66,user51..52);latch1bitatc_stn underdefaultOFFcontrollerparameter;stn_cfg29/stationportsunchanged;allBASE/newprofileguardmustbecheckedbeforeenabling',uses='changecommonr_addrsoMUindices,VMaddressandARwordagree;HARD1actualgeneratedrepair4requiresnewguardedsourceview/regeneration+equivalence/TTFF, notjustlogicalreferenceedit',analytic_cost='~1latchedflagFFpercontroller(12perrank)+7bitconstantadder+8bitoffsetmux;existing24bitadder/noextraedge. Notmeasured, closure/fanoutmustbepriced.'),hard_qualifications=['configureoncebeforeeach512rawburst,notbetweenrounds','nextcfgmustwaitoldr_vlast/busyclearANDalloldnear/far/neighborinputs+cfgpayloadpipeline exclusion;no guesseddate','h9ringc8/c9wrap8eachround;positivelead<=8andprefetch/wavecadence mustremainsource-qualified','peruserMUunionunchangedonlyifactualusercapture/clear/emit/draincoherent','q4lasttail24sparse/q5absentstillneedsreviewedpublisher/sinkvalidcontract;coalescingalone doesnotfixit','cheap5FFpublisherstillneedsNEWmode-changingGOdrainlease/assertion;oldcallerready/barrierinsufficient','freshCALRpayload/descriptor/digest/epochandactualclockframesrequired;nooldauthtransfer'],alternative25round_PC_capacity=json.loads(a.pc_proof.read_text()),readset={str(x):hashlib.sha256(x.read_bytes()).hexdigest()for x in [a.capture,a.calendar,a.btab_proof,a.pc_proof,part,station,ctl,hard]})
(a.out/'source_assessment.json').write_text(json.dumps(result,indent=2)+'\n');print('SOURCE_PROPOSAL pairs23 STNs46 saved252 realrows18992; actualfirst512cadence511x833000fs')
