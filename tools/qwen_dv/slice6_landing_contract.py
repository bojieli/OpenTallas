#!/usr/bin/env python3
"""Emit a source-pinned, non-adopting landing inventory and face migration contract."""
import collections
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/arch/qw_slice6_1019/landing_contract_1020'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name, value): (OUT/name).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
def parent(top):
    rp=ROOT/f'results/arch/qw_slice6_1019/lp/{top}_record.json'
    sp=ROOT/f'rtl/qwen_dv/s5/lp/{top}.sv'
    r=json.loads(rp.read_text()); readers=r['landings']; rings={}
    for row in readers:
        key=row['ring_of']
        if key not in rings: rings[key]={'id':key,'width':row['width'],'src_region':row['src_region'],'net':row['net'],'writer':row['ring'],'readers':[]}
        assert rings[key]['width']==row['width'] and rings[key]['src_region']==row['src_region']
        rings[key]['readers'].append(row['read'])
    banks=list(rings.values())
    for b in banks:
        b['payload_storage_bits']=b['width']*r['D']
        b['storage_requirement']='SRAM_REQUIRED' if b['payload_storage_bits']>2048 else 'bounded_native_census_required'
    return {'source':str(sp.relative_to(ROOT)),'source_sha256':sha(sp),'record_sha256':sha(rp),'top':top,
      'status':'BLOCKED_NO_PARENT_GATE','D':r['D'],'K':r['K'],'added_receiver_edges':r['added_edges_per_landing'],
      'reader_count':len(readers),'shared_writer_count':len(banks),'reader_width_sum':sum(x['width'] for x in readers),
      'unique_writer_width_sum':sum(x['width'] for x in banks),'payload_storage_bits':sum(x['payload_storage_bits'] for x in banks),
      'over_2k_banks':sum(x['payload_storage_bits']>2048 for x in banks),'over_2k_payload_bits':sum(x['payload_storage_bits'] for x in banks if x['payload_storage_bits']>2048),
      'record_flops':r['flops'],'reset':r['reset'],'regions':r['regions'],'banks':banks,
      'blocking_obligations':['Joint canonical ot_pl_land_w/r SRAM backend and generator opt-in, preserving shared writers',
       'Actual mapped all-driver census <=32 including wc/rc/decode/warm/reset; physicalchunk24 alone is insufficient',
       'Per-reader actual writer/reader phase, K, epoch, reset release and first-use proof',
       '405um clock/data/reset reach plus registered boundary pins and hard-child clock references',
       'Compile offsets and exact composed serial-chain price after qualified leaf bindings']}
def face():
    p=ROOT/'results/arch/qw_slice4_1019/slice_face_landings.json'; old=json.loads(p.read_text()); links=old['links']
    # Low-to-high ordering is explicit; an RTL adapter must use this exact partition.
    packs=[('outbound_ch',['arv','art','arm','arl','ard','dd'],[182,182,182,183,183,183]),
           ('return_ch',['rv','re','rr','rl','rd','dr'],[173]*6)]
    grouped=collections.defaultdict(list)
    for i,l in enumerate(links): grouped[(l['src'],l['dst'],l['face'])].append((i,l))
    consumed=set(); units=[]
    for key,rows in sorted(grouped.items()):
        byport={d['port'].rsplit('_',1)[0]:(i,l,d) for i,l in rows for d in l['dst_ports']}
        for label,ports,widths in packs:
            if not all(x in byport for x in ports): continue
            parts=[]; off=0
            for port in ports:
                i,l,d=byport[port]; assert len(l['dst_ports'])==1 and i not in consumed
                parts.append({'link_index':i,'bus':l['bus'],'dst_port':d['port'],'lsb':off,'width':d['width']}); off+=d['width'];consumed.add(i)
            assert off==sum(widths)
            units.append({'kind':label,'src':key[0],'dst':key[1],'face':key[2],'width':off,'low_to_high_fields':parts,'sram_slice_widths_low_to_high':widths})
    exact={453:[151,151,151],520:[174,173,173],548:[183,183,182],1088:[173,183,183,183,183,183]}
    for i,l in enumerate(links):
        if i in consumed: continue
        units.append({'kind':'single_bus','src':l['src'],'dst':l['dst'],'face':l['face'],'width':l['bits'],
         'low_to_high_fields':[{'link_index':i,'bus':l['bus'],'dst_ports':l['dst_ports'],'lsb':0,'width':l['bits']}],
         'sram_slice_widths_low_to_high':exact.get(l['bits']),
         'status':'SRAM_NATIVE32_ONLY_PHASE_OWED' if l['bits'] in exact else 'NEEDS_QUALIFIED_EXACT_WIDTH_MASTER'})
    for u in units:
        u['nominal_added_edges']=5 if u['sram_slice_widths_low_to_high'] else None
        u['K']=None;u['phase_proof']=None;u['reset_first_use_proof']=None
    return {'schema':'opentallas.qw_slice6.face_contract.v1','status':'MODEL_ONLY_NO_RTL_BIND_OR_K_EMIT',
     'historical_input_sha256':sha(p),'historical_input_provenance':old['inputs'],
     'historical_links':len(links),'historical_bits':sum(x['bits'] for x in links),'clock_groups':old['face_port_groups'],
     'units':units,'qualified_sram_widths_native32':[151,173,174,182,183],
     'sram_master_pattern':'qfd_landh0d8s_{W}_EW_98x171','nominal_sram_edges_vs_flop':2,
     'sram_calendar':{'K':'(L+G-R0-2) mod 16','write_to_read_age':'(L-3)*T+phi in [1.25*T,4.125*T]','first_output':'zero until R0+4+K'},
     'blocking_obligations':['GEN must acknowledge current actual clock/phase table; historical input is not current binding authority',
      'All fields of packed coherent bundle use same clock/en/reset/K and first-valid age; no old +3 control with +5 payload',
      '107/116 flop masters HELD by mapped fanout failures; small flop widths need full mapped census evidence',
      'No padding, tied functional inputs, implicit K defaults or unqualified 512/514 widths',
      'Actual per-instance phase/reset/warm/first-use proof plus exact compiler pricing before emitting RTL',
      'Physical face area/pins/reach/clock references and 43.2um lattice remain unplanned']}
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for top in ['qfd_dv_s5_lp','qfd_dv_s5b_lp']: write(top+'_inventory.json',parent(top))
    write('face182_contract.json',face())
if __name__=='__main__': main()
