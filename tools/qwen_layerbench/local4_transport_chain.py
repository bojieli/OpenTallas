#!/usr/bin/env python3
"""Compose actual serial TT→FDN/FUP→STM table-request and TW transport paths.

Uses actual bound/landed stage counts at named ports. Historical asbuilt counts
are preserved as diagnostics; they are never added again. This emits relative
source-selected expressions, not fabricated CALR issue dates or48 user windows.
"""
import argparse,hashlib,json,re
from pathlib import Path

def sid(path):
 m=re.search(r'dvs_([EW][0-5])\.',path)
 return m[1]if m else None

def compose(census):
 if census.get('schema')!='opentallas.qc.actual_table_loader_transport.v1':raise ValueError('actual selected table transport census required')
 rows=census['paths']
 for r in rows:
  if type(r['landed_stages'])is not int or r['landed_stages']<0:raise ValueError('actual landed endpoint count invalid')
 direct=[r for r in rows if r['source']=='tt_ctlm.table_req' and r['sink_port']=='treq_i' and r['sink'].endswith('.u_fdn')]
 if len(direct)!=1:raise ValueError('one actual TT request entry required')
 entry=direct[0];first=sid(entry['sink']);arrival={first:entry['landed_stages']};chain=[first];links=[]
 while len(chain)<12:
  cur=chain[-1]
  forwarded=[r for r in rows if sid(r['source'])==cur and r['source'].endswith('.u_fdn.treq_q') and r['sink'].endswith('.u_fup') and r['sink_port']=='treq_c']
  hops=[r for r in rows if sid(r['source'])==cur and r['source'].endswith('.u_fup.treq_o') and r['sink'].endswith('.u_fdn') and r['sink_port']=='treq_i']
  if len(forwarded)!=1 or len(hops)!=1:raise ValueError('actual serial forwarding path missing/ambiguous: '+cur)
  f,h=forwarded[0],hops[0];nxt=sid(h['sink'])
  if nxt in arrival:raise ValueError('request chain cycles')
  # Actual FDN input→q1; actual FUP c→o combin0. Physical wires use
  # complete landed counts, never (landed-asbuilt)+asbuilt another time.
  arrival[nxt]=arrival[cur]+1+f['landed_stages']+h['landed_stages'];chain.append(nxt)
  links.append({'from':cur,'to':nxt,'FDN_native_q':1,'FDNq_to_FUP_c':f,'FUP_native_c_to_o':0,'FUPo_to_next_FDN':h})
 out=[]
 for s in chain:
  request=[r for r in rows if sid(r['source'])==s and r['source'].endswith('.u_fdn.treq_c') and r['sink'].endswith('.u_stm') and r['sink_port']=='treq_i']
  source_tw=[r for r in rows if sid(r['source'])==s and '.u_stm.tw_'in r['source']]
  native_tw=[r for r in rows if sid(r['source'])==s and '.u_rp.vtw_'in r['source']]
  if len(request)!=1 or not source_tw or not native_tw:raise ValueError('actual per-slice request/TW paths missing '+s)
  sd={r['landed_stages']for r in source_tw};nd={r['landed_stages']for r in native_tw}
  if len(sd)!=1 or len(nd)!=1:raise ValueError('table-write tuple is incoherent: '+s)
  T=arrival[s]+request[0]['landed_stages'];suffix=next(iter(sd))+next(iter(nd))
  out.append({'slice_site':s,'TT_output_to_FDN_input':arrival[s],'FDN_i_to_treq_c':0,'FDN_c_to_STM_input':request[0]['landed_stages'],'TT_output_to_STM_request':T,'STM_TW_to_RP_and_BTable':next(iter(sd)),'RP_native_TW_forward':0,'RP_to_native_VM_TW_relays':next(iter(nd)),'TW_external_suffix':suffix,'table_write_tuple_paths':len(source_tw)+len(native_tw),'conditions':['WK88 inactive during exclusive table-write window','exact selected FDN/FUP/RP source identities','macro-specific intrinsic store/read ages added separately'],'historical_STM_request_asbuilt':request[0]['asbuilt_stages']})
 return {'schema':'opentallas.qc.local4-transport-chain.v1','status':'SOURCE_SELECTED_RELATIVE_TRANSPORT_NOT_GLOBAL_DATES','origin':'actual TT.table_req output sampling edge; all numbers in core rising edges','endpoint_convention':'landed_stages = bound wire transport plus fixed receiver pad, from actual source-cell output to actual sink-cell input; asbuilt is replaced/reference travel, never added. Native FDN_i→q1/FUP0/RP0 and VM relay/macro captures remain separate','endpoint_convention_owner':'QC actual transport owner confirmed 2026-11-16; exact source identities/cache49 listed below','request_chain_order':chain,'initial_TT_to_FDN':entry,'links':links,'slices':out,'native_source_forwarding_authority':{'FDN_i_to_q':1,'FDN_i_to_c':0,'FUP_c_to_o':0,'RP_TW_to_vtw':0,'FDN_base_source_sha256':'bad64d67691f2bca53804b884d5da41b4900e4801db53da3c6e352b1796395a9','CE_variants_source_sha256':'98610ac39c1262e29158f5f489d175b6c05386673c9424399bcf5cb60e39bcec','FUP_generic_source_sha256':'c9aaa648c0183d5a6e8024eb202f7c5af1ac27f5b43dfd9a6604695fa2ea6c21','RP_source_sha256':'bffc7f9b702e3ac3cf8f44d66d11863db0a7611f122154554a361587480dcbdc','qualification':'actual ASB/cache49 source identities checked by QC owner; final new binding must reselect them'},'bus_groups_sha256':census['bus_groups_sha256'],'actual_bind':census['bind'],'global_enable':False,'remaining':['actual CALR→TT output edge authority','per-user TT issue dates and complete48 source-selected windows','actual complete TT/native source construction','coherent final memory/command/write/retire tuple and WK exclusion']}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--census',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();raw=a.census.read_bytes();v=compose(json.loads(raw));v['census_sha256']=hashlib.sha256(raw).hexdigest();a.out.write_text(json.dumps(v,indent=2)+'\n');print([(r['slice_site'],r['TT_output_to_STM_request'],r['TW_external_suffix'])for r in v['slices']])
if __name__=='__main__':main()
