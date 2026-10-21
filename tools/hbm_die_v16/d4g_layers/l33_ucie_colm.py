#!/usr/bin/env python3
"""Bind exact UCIEcolm component source/ports; expose parent clock/calendar debt."""
import argparse,collections,copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
VIEW='physical/ref_tile/hbm_pdie_ucie_colh/views/ot_pdie_ucie_col'
RECORD='84e9c94d03338c6959a5cff779c2032bb1dd63ef'
def apply(c,grants):
 n='host_N';i=c['instances'][n];old=copy.deepcopy(i)
 assert i['master']=='ot_pdie_ucie' and i.get('params',{}) in ({},{'PMA_LAT':2}), 'Unreviewed host source/params'
 assert i['ports']['pma_rck']==dict(direction='input',bits=1)
 spec=json.loads((ROOT/'physical/ref_tile/hbm_pdie_ucie_colh/spec.json').read_text())
 ledger=json.loads((ROOT/'results/arch/hbm_release_r16_1021/ucie_colm_integration.json').read_text())
 for f in ledger['source_manifest']:
  assert hashlib.sha256((ROOT/f['path']).read_bytes()).hexdigest()==f['sha256'], ('frozen source differs',f['path'])
 ports={k:copy.deepcopy(v) for k,v in i['ports'].items() if k not in ('clk','rst','pma_rck')}
 for p in ('ck_tx','ck_rx','ck_rck','rst_tx','rst_rx','rst_rck'):ports[p]=dict(direction='input',bits=1)
 i.update(master='ot_pdie_ucie_col',source=spec['sources'][0],rtl_deps=spec['sources'][1:],params={'MUT':0},ports=ports,physical_view=VIEW,closed_record=RECORD)
 i.pop('force_synth',None)
 i['binding_qualification']='EXACT_CLOSED_COMPONENT_SOURCE_PORT_PARAMS; PARENT_CLOCK_RESET_ARRIVAL_CALENDAR_OPEN'
 i['note']+='; UCIEcolm explicit3regional clock/reset ABI. RX delta includes1rck beforeFIFO +1rx visibility +2rx out; phase/occupancy variable, not universalfixedstreamcycle. TXsamePMA2. Componentclosure does not prove before-ingress runtime.'
 cr=[r for r in c['clock_resets'] if r['instance']==n]
 oldclk=next(r for r in cr if r['port']=='clk');oldrst=next(r for r in cr if r['port']=='rst')
 c['clock_resets']=[r for r in c['clock_resets'] if r['instance']!=n]
 for p in ('ck_tx','ck_rx'):c['clock_resets'].append(dict(oldclk,port=p))
 for p in ('rst_tx','rst_rx','rst_rck'):c['clock_resets'].append(dict(oldrst,port=p))
 dp=next(p for p in c['die_pins'] if p['instance']==n and p['port']=='pma_rck');dp['port']='ck_rck'
 dp['signal_kind']='external_forwarded_clock' # external package name stays unchanged
 ext=dict(instance=n,port='ck_rck',die_pin=dp['name'],domain='host_ucie_rck',source_kind='external_forwarded_clock',pll_alias=False,
  nominal_period_ps=833.333,phase='externalrecovered; actualpackage/root/arrival proof owed',related_stream='CDC through realgray synchronisers +dualclock SRAM',
  reset_port='rst_rck',reset_source=list(oldrst['source']),reset_semantics='new2plainlocalpad stages; not identical oldasync assert proof',
  qualification='SOURCE_PIN_MAPPING_ONLY; GEN directexternalentry and physicaldelivery/STA required')
 c.setdefault('external_clock_entries',[]).append(ext)
 c['masters']=dict(collections.Counter(a['master'] for a in c['instances'].values()))
 slot=next(s for s in grants['slots'] if s['name']==i['slot']);before=copy.deepcopy(slot)
 slot.update(cell=i['master'],source=i['source']);slot['outline']=copy.deepcopy(spec['outline']);slot['outline'].pop('exact',None)
 slot['notes']=slot.get('notes','')+'; exactCLOSEDcolh259.2x1555.2, source3e3,3clocks, nooldbodyalias'
 report=dict(status='EXACT_COMPONENT_BOUND_PARENT_CLOCK_CALENDAR_OPEN',instance=n,record=RECORD,old=old,new=i,
  old_slot=before,new_slot=slot,external_clock_entry=ext,source_manifest=ledger['source_manifest'],
  source_qualification='All9 exact frozenblobs; no reusedoldmaster or oldclockalias',
  latency='TXsame1+PMA2; RX +1recovered +1receiver availability +2receiverout vslegacy; no universalfixedstreamdelta',
  executed_token_boundary='ExistingCpBus drives host_cp_ingress outputs; CFG_LAT2 is hleaf afteringress, not UCIE',
  remaining=['GEN externalclockentry/model +realboundaryclockdelivery/STA','per-region startup/reset-running proof','actual pre-ingress arrival/staticcalendar envelope','freshGEN/S4 with actual newoutline/source'])
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in ['input','grants','output','out_grants','report']:p.add_argument(n,type=Path)
 a=p.parse_args();c=json.loads(a.input.read_text());g=json.loads(a.grants.read_text());r=apply(c,g)
 for path,obj in [(a.output,c),(a.out_grants,g),(a.report,r)]:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,indent=1)+'\n')
 print('L33_UCIE_COLH EXACT_COMPONENT_BOUND PARENT_CLOCK_CALENDAR_OPEN')
