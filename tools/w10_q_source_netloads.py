#!/usr/bin/env python3
"""Source coarse fanout/cone inventory and constructive pin load, not mapped RC."""
import argparse
import collections
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
from tools.w10_q_constructive_area_bound import count_gates
from tools.w10_q_elaboration_inventory import REG

def inventory(m,construction,power):
    cells=m['cells']; roots=set(); consumers=collections.Counter();drivers=collections.Counter();combs=[]
    for p in m['ports'].values():
        if p['direction']=='input':roots.update(b for b in p['bits'] if isinstance(b,int))
    for n,c in cells.items():
        t=c['type'];co=c['connections']
        for p,bits in co.items():
            direction=c['port_directions'][p]
            if direction=='input' and p not in ('CLK','WR_CLK','RD_CLK'):
                consumers.update(b for b in bits if isinstance(b,int))
            elif direction=='output':drivers.update(b for b in bits if isinstance(b,int))
        if t in REG:
            if co['CLK']==[2]:roots.update(b for b in co['Q'] if isinstance(b,int))
        elif t=='$mem_v2':
            if set(co['WR_CLK'])=={2}:roots.update(b for b in co['RD_DATA'] if isinstance(b,int))
        elif t.startswith('$') and t!='$scopeinfo':
            ins={b for p,v in co.items() if c['port_directions'][p]=='input' for b in v if isinstance(b,int)}
            outs={b for p,v in co.items() if c['port_directions'][p]=='output' for b in v if isinstance(b,int)}
            combs.append((n,c,ins,outs))
    changed=True
    while changed:
        changed=False
        for n,c,ins,outs in combs:
            if ins&roots and not outs<=roots:roots|=outs;changed=True
    classes=collections.Counter(); types={}
    root_sensitive_leaf_D_bits=0
    root_register_D_bits=0
    memory_lowering=[]
    for name,cell in cells.items():
        co=cell['connections']
        if cell['type'] in REG:
            if co['CLK']==[2]:root_register_D_bits+=len(co['D'])
            else:root_sensitive_leaf_D_bits+=sum(b in roots for b in co['D'])
        elif cell['type']=='$mem_v2':
            p=cell['parameters'];size=int(p['SIZE'],2);width=int(p['WIDTH'],2)
            ports=int(p['WR_PORTS'],2)
            active_bits=[sum(b!='0' for b in co['WR_EN'][i*width:(i+1)*width]) for i in range(ports)]
            active_ports=sum(n>0 for n in active_bits)
            read=(size-1)*width*int(p['RD_PORTS'],2)
            write=size*sum(active_bits)
            decode=size*active_ports*(2*((size-1).bit_length())+2)+2*write
            memory_lowering.append({'name':name,'write_clock_net':str(sorted(set(co['WR_CLK']))),
                'root_CFG_storage':set(co['WR_CLK'])=={2},
                'storage_bits':size*width,'read_mux_nand2':4*read,'write_mux_nand2':4*write,'decode_enable_nand2':decode,
                'active_write_bits_by_port':active_bits,'disabled_write_ports':ports-active_ports,
                'source_scope':'Exact constant WR_EN pruning; existing FAST fw payload is leaf-registered before FIFO write'})
    for n,c,ins,outs in combs:
        group='root_reachable' if ins&roots else 'leaf_only_or_static'
        gates=count_gates(c);classes[group]+=gates
        types.setdefault(group,collections.Counter())[c['type']]+=gates
    aliases={}; top_fanout=set(dict(consumers.most_common(16)))
    for n,w in m.get('netnames',{}).items():
        for b in w['bits']:
            if b in top_fanout:aliases.setdefault(str(b),[]).append(n)
    coeff=power['conservative_coefficients'];nandcap=D(coeff['nand']['input_cap_fF'])
    capbykind={k:D(v['input_cap_fF'])*power['counts'][k] for k,v in coeff.items()}
    # Count all physical construction input pins exactly once, including clocks.
    # It replaces the old all-input PLUS all-output-max-cap charge. Non-clock
    # wire cannot be inferred from pin incidence; retain a numerical interval.
    totalpins=sum(capbykind.values(),D(0)); clockpins=D(power['clock_endpoint_cap_fF'])+D(power['clock_buffer_input_cap_fF'])
    wire_ceiling=D(power['cell_output_load_ceiling_cap_fF'])
    root_nand_pin_cap=nandcap*classes['root_reachable']
    leaf_nand_pin_cap=nandcap*classes['leaf_only_or_static']
    maxwire=wire_ceiling # No subtraction without a per-net driver-to-sink join.
    volts=D('.77');freq=D('1.2e9')
    return {'schema':'w10_q_source_pin_fanout_v1','coarse_consumer_bit_fanout_histogram':dict(sorted(collections.Counter(consumers.values()).items())),
      'highest_coarse_fanout':[{'bit':b,'coarse_consumers':n,'aliases':aliases.get(str(b),[])} for b,n in consumers.most_common(16)],
      'primitive_nand2_activity_classes':dict(classes),'primitive_nand2_classes_by_type':{k:dict(v) for k,v in types.items()},
      'root_register_D_bits':root_register_D_bits,'root_sensitive_leaf_D_bits':root_sensitive_leaf_D_bits,
      'memory_lowering':memory_lowering,
      'memory_write_port_pruning_scope':'Only literal all-zero WR_EN ports are removed. No runtime family label is used as a constant.',
      'construction_pin_cap_by_kind_fF':{k:str(v) for k,v in capbykind.items()},
      'construction_all_input_cap_fF':str(totalpins),'clock_endpoint_and_buffer_input_fF':str(clockpins),
      'construction_nonclock_input_cap_fF':str(totalpins-clockpins),
      'root_reachable_primitive_input_cap_fF':str(root_nand_pin_cap),
      'leaf_only_primitive_input_cap_fF':str(leaf_nand_pin_cap),
      'nonclock_wire_allocation_interval_fF':['0',str(maxwire)],
      'all_output_ceiling_minus_all_input_scope':'Aggregate source load ceiling retained as unresolved wire allocation bound; no downstream pin subtraction until per-net driver/sink join. Clock-wire is separate; upper allocation overcounts.',
      'nonclock_pin_only_full_activity_switching_W':str((totalpins-clockpins)*volts*volts*freq*D('1e-15')),
      'nonclock_wire_upper_activity1_switching_W':str(maxwire*volts*volts*freq*D('1e-15')),
      'source_scope':'Actual coarse bit fanout and source dependency reachability; weights are constructive NAND palette, not mapped physical cells.',
      'activity_rule':'root-reachable primitive cones receive no leaf-stop discount; leaf-only/static cones use validated leaf union. Root-sensitive leaf D is charged despite stopped CLK. CFG storage data is charged for CFG/read-address changes, not assumed root-stop. FAST FIFO writes source retained leaf fw registers.',
      'remaining':['Per-net gate expansion and placement-bound wire length inside the interval','root-reachable data activation from stage/CFG/BEAT schedule','memory mux and reset/enable construction activity','stage family interval union and drain overlap'],
      'physical_admission':False,'actual_power_qualified':False,'root_stop_credit':0}
def main():
    p=argparse.ArgumentParser()
    for n in ('netlist','construction','power','output'):p.add_argument('--'+n,required=True)
    a=p.parse_args();m=json.loads(Path(a.netlist).read_text())['modules']['ot_v41_rom_elem_q_wake_w10'];x=inventory(m,json.loads(Path(a.construction).read_text()),json.loads(Path(a.power).read_text()))
    x['inputs']={n:{'path':getattr(a,n),'sha256':hashlib.sha256(Path(getattr(a,n)).read_bytes()).hexdigest()} for n in ('netlist','construction','power')}
    Path(a.output).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
if __name__=='__main__':main()
