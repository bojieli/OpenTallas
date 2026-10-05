#!/usr/bin/env python3
"""Charge ungated front and existing leaf ICG duty separately; never root-stop."""
import argparse
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
from tools.w10_liberty_event_energy import events
from tools.w10_q_power_envelope import coefficients, serial

def charge_cycles(root_cycles,leaf_cycles,root_W,leaf_W,on_icg_W,off_icg_W,hz):
    if root_cycles < 0 or leaf_cycles < 0 or leaf_cycles > root_cycles:
        raise ValueError('invalid leaf/root counts')
    return (root_W*root_cycles+leaf_W*leaf_cycles+on_icg_W*leaf_cycles+off_icg_W*(root_cycles-leaf_cycles))/hz

def build(inventory,libs,macros,duty):
    hz=D('1.2e9');voltage=D('.77');rc=D('.145426');proof={};cs={};sources={}
    for corner in ('SS','TT','FF'):
        e={};caps={}
        for kind,group,name,fixed in [
          ('storage','SEQ','DFFASRHQNx1_ASAP7_75t_R',{'RESETN':True,'SETN':True}),
          ('buffer','INVBUF','BUFx12_ASAP7_75t_R',{}),
          ('icg_on','SEQ','ICGx1_ASAP7_75t_R',{'ENA':True,'SE':False}),
          ('icg_off','SEQ','ICGx1_ASAP7_75t_R',{'ENA':False,'SE':False})]:
            p=libs/(group+'_'+corner+'.cells.lib');text=p.read_text();sources[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
            e[kind]=events(text,name,fixed);caps[kind]=coefficients(text,name,D('1e-12'))
        p=macros/('ot_rom_4096x274_m8_'+corner.lower()+'.lib');text=p.read_text();sources[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
        # Macro power is clock input energy; no separate data internal table exists.
        caps['macro']=coefficients(text,'ot_rom_4096x274_m8',D('1e-9'))
        proof[corner]=e;cs[corner]=caps
    def event(kind,pin):return max(D(proof[c][kind]['event_cycle_fJ'].get(pin,'0')) for c in proof)
    def cap(kind,pin):return max(cs[c][kind]['pins'][pin]['cap_fF'] for c in cs)
    def leak(kind):return max(cs[c][kind]['leakage_W'] for c in cs)
    groups=inventory['conditional_clock_reserve']['groups']
    root=groups['[2]'];leaf_buffers=sum(g['buffer_count'] for n,g in groups.items() if n!='[2]')
    root_storage=inventory['storage_bits_by_clock_net']['[2]'];leaf_storage=inventory['conservative_storage_clock_sinks']-root_storage
    root_cap=root_storage*cap('storage','CLK')+8*cap('icg_on','CLK')+root['buffer_count']*cap('buffer','A')
    root_wire=root['buffer_count']*500*rc*2
    leaf_cap=leaf_storage*cap('storage','CLK')+4*cap('macro','clk')+leaf_buffers*cap('buffer','A')
    leaf_wire=leaf_buffers*500*rc*2+200*rc*2
    buf_energy=event('buffer','A');ff_energy=event('storage','CLK')
    macro_energy=max(cs[c]['macro']['internal_cycle_fJ'] for c in cs)
    root_energy=root_storage*ff_energy+root['buffer_count']*buf_energy
    leaf_energy=leaf_storage*ff_energy+leaf_buffers*buf_energy+4*macro_energy
    def power(cap_ff,energy_fJ):return (cap_ff*voltage*voltage+energy_fJ)*D('1e-15')*hz
    rootW=power(root_cap+root_wire,root_energy)
    leafW=power(leaf_cap+leaf_wire,leaf_energy)
    offICG=8*event('icg_off','CLK')*D('1e-15')*hz
    onICG=8*event('icg_on','CLK')*D('1e-15')*hz
    ffdata=event('storage','D')
    front_dataW=root_storage*ffdata*D('1e-15')*hz
    leaf_dataW=leaf_storage*ffdata*D('1e-15')*hz
    wake_event_J=8*event('icg_on','ENA')*D('1e-15')
    traces=[]
    for r in duty['records']:
        if r['case'].startswith('bf16_') or r['case']=='exact':continue
        for m in r['measured']:
            roots=m['root_rising_edges'];on=m['each_of_eight_leaf_rising_edges']
            energy=charge_cycles(roots,on,rootW,leafW,onICG,offICG,hz)+int(m['wake_register_transitions'])*wake_event_J
            reset_extra=max(cs[c]['storage']['internal_cycle_fJ'] for c in cs)*inventory['conservative_storage_clock_sinks']*int(m['reset_root_edges'])*D('1e-15')
            energy+=reset_extra
            traces.append({'case':r['case'],'element':m['element'],'source_trace_sha256':r['trace_sha256'],
               'root_cycles':roots,'leaf_cycles':on,'drain_only_cycles':m['drain_only_edges'],
               'enabled_intervals':m['enabled_intervals'],'stopped_intervals':m['stopped_intervals'],
               'conditional_clock_energy_J':energy,'conditional_average_clock_W':energy*hz/roots,
               'clock_scope':'Actual Q-XF4 protocol projected onto Q construction, not source-mapped power measurement',
               'reset_all_storage_all_arc_extra_budget_J':reset_extra,
               'reset_scope':'Extra full all-arc storage charge on every reset-root edge; conservative overlap, not actual reset energy'})
    family={}
    for name,active in [('expert_w1',832),('expert_w3',832),('expert_w2',1024)]:
        family[name]={'resident_qpairs':1024,'active_qpairs':active,
            'conditional_root_clock_W':1024*rootW,
            'conditional_existing_ICG_clock_W':active*onICG+(1024-active)*offICG,
            'conditional_active_leaf_clock_W':active*leafW,
            'conditional_total_clock_W':1024*rootW+active*(leafW+onICG)+(1024-active)*offICG,
            'active_count_binding':'Ram allocator handoff; not a source-pinned fulltoken stage program yet',
            'drain_policy':'127 drain cycles are already in observed enabled intervals; use interval union, never add them twice'}
    return serial({'schema':'w10_q_existing_icg_clock_ledger_v1','source_sha256':sources,
      'compatible_event_proof':proof,'frequency_Hz':hz,'characterized_voltage_ceiling_V':voltage,
      'root_stop_credit':0,'existing_leaf_ICG_suppression_preserved':True,
      'root':{'buffers':root['buffer_count'],'storage_clock_bits':root_storage,
              'endpoint_and_buffer_input_fF':root_cap,'guarded_wire_fF':root_wire,
              'conditional_clock_W':rootW,'worst_storage_D_internal_W':front_dataW},
      'leaf':{'buffers':leaf_buffers,'storage_clock_bits':leaf_storage,'macro_clock_inputs':4,
              'endpoint_and_buffer_input_fF':leaf_cap,'guarded_wire_fF':leaf_wire,
              'conditional_enabled_clock_W':leafW,'conditional_stopped_clock_W':D(0),
              'worst_enabled_storage_D_internal_W':leaf_dataW},
      'icg':{'always_source_clk_inputs':8,'enabled_internal_W':onICG,'stopped_internal_W':offICG,
             'wake_transition_energy_J':wake_event_J},
      'leakage_storage_buffer_icg_macro_W':(root_storage+leaf_storage)*leak('storage')+(root['buffer_count']+leaf_buffers)*leak('buffer')+8*leak('icg_on')+4*leak('macro'),
      'Q_trace_projections':traces,'family_clock_allocations':family,
      'BF_root_reserve':{'buffers':107,'source':'results/uarch/w10_clock_tree_site_budget_r1/receipt.json','separate_from_Q_root_54':True},
      'no_doublecount':'Clock term replaces matching construction clock charge only; does not subtract historical TT pair power.',
      'remaining':['full-stage source-pinned activity/count interval union','non-clock actual construction pin/wire loads and data event costs','reset energy and glitch multiplicity','spatial phase/RC/SSFF/PG/IR'],
      'physical_admission':False,'actual_power_qualified':False})
def main():
    p=argparse.ArgumentParser()
    for n in ('inventory','libs','macros','duty','output'):p.add_argument('--'+n,required=True)
    a=p.parse_args();out=build(json.loads(Path(a.inventory).read_text()),Path(a.libs),Path(a.macros),json.loads(Path(a.duty).read_text()))
    out['input_files']={n:{'path':getattr(a,n),'sha256':hashlib.sha256(Path(getattr(a,n)).read_bytes()).hexdigest()} for n in ('inventory','duty')}
    Path(a.output).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
if __name__=='__main__':main()
