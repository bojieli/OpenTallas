#!/usr/bin/env python3
"""Conservative Boolean construction budget, not a mapped result or fit proof."""
import argparse
import collections
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import re
from tools.w10_q_elaboration_inventory import REG, inventory

def count_gates(c):
    t=c['type']; p=c.get('parameters',{}); co=c.get('connections',{})
    def width(k): return int(p.get(k+'_WIDTH','0'),2) or len(co.get(k,[]))
    a,b,y=width('A'),width('B'),width('Y'); n=max(a,b,y,1)
    if t in REG or t in ('$mem_v2','$scopeinfo','ICGx1_ASAP7_75t_R','ot_rom_4096x274_m8'): return 0
    if t in ('$and','$or'): return 2*y
    if t=='$xor': return 4*y
    if t=='$not': return y
    if t in ('$add','$sub','$neg'): return 12*n
    if t=='$mul': return 11*y*y # sign extension to output width; partial AND + ripple sums
    if t=='$mux': return 4*y
    if t=='$pmux': return 4*width('Y')*(len(co['S'])+1)
    if t in ('$eq','$ne','$lt','$le','$gt','$ge'): return 12*n+2*y
    if t in ('$reduce_bool','$reduce_or','$reduce_and','$logic_not','$logic_and','$logic_or'):
        return 4*(a+b+y+1)
    if t in ('$shl','$shr','$shift','$shiftx'):
        # Full barrel construction plus high-bit/negative-range detection and saturation.
        return 4*max(a,y,1)*(math.ceil(math.log2(max(a,y,1)))+2)+16*b+8*y
    raise ValueError('unsupported primitive '+t)

def bound(netlist, lef):
    inv=inventory(netlist); cells=netlist['modules']['ot_v41_rom_elem_q_wake_w10']['cells']
    primitives=collections.Counter()
    for c in cells.values(): primitives[c['type']]+=count_gates(c)
    memory_mux=4*(inv['memory_read_mux2_count']+inv['memory_write_mux2_count'])
    memory_decode=sum(x['SIZE']*x['WR_PORTS']*(2*math.ceil(math.log2(x['SIZE']))+2)
                      +2*x['storage_bits']*x['WR_PORTS'] for x in inv['memories'])
    # ASR flop palette covers retained async-reset storage; ten NANDs/bit reserve
    # covers reset/enable selection and polarity, including memories.
    reset_enable=10*inv['conservative_storage_clock_sinks']
    gates=sum(primitives.values())+memory_mux+memory_decode+reset_enable
    areas={}
    for name, body in re.findall(r'MACRO\s+(\S+)(.*?)END\s+\1',lef,re.S):
        size=re.search(r'SIZE\s+(\S+)\s+BY\s+(\S+)',body)
        if size: areas[name]=Decimal(size[1])*Decimal(size[2])
    palette={'nand':'NAND2x1_ASAP7_75t_R','storage':'DFFASRHQNx1_ASAP7_75t_R',
             'buffer':'BUFx12_ASAP7_75t_R','icg':'ICGx1_ASAP7_75t_R'}
    used={k:areas[v] for k,v in palette.items()}
    std=Decimal(gates)*used['nand']+inv['conservative_storage_clock_sinks']*used['storage']
    std+=inv['conditional_clock_reserve']['buffer_count']*used['buffer']+8*used['icg']
    macro=Decimal('125.280')*Decimal('62.910')*4
    return {'schema':'w10_q_boolean_construction_bound_v1',
      'primitive_nand2_counts':dict(sorted(primitives.items())),
      'memory_mux_nand2':memory_mux,'memory_decode_enable_nand2':memory_decode,
      'reset_enable_nand2':reset_enable,'total_nand2':gates,
      'palette':{k:{'cell':palette[k],'area_um2':str(v)} for k,v in used.items()},
      'conditional_standard_construction_area_um2':str(std),
      'macro_area_um2':str(macro),
      'conditional_50pct_cell_plus_macro_budget_um2':str(std*2+macro),
      'density':'0.50','root_stop_credit':0,'physical_admission':False,
      'actual_mapped_standard_area_um2':None,
      'scope':'finite conservative Boolean construction allocation, not optimization or mapped measurement; overbudget does not prove actual implementation impossible',
      'excluded_unqualified_terms':['post-map fanout/hold/ties/taps repair','legal corridor and PG allocation',
       'hub/descriptor composition','source-bound clock load/energy/voltage envelope',
       'SS/FF timing of constructed gate network'],
      'clock_inventory':inv['conditional_clock_reserve']}
def main():
    p=argparse.ArgumentParser();p.add_argument('--netlist',required=True);p.add_argument('--lef',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    x=bound(json.loads(Path(a.netlist).read_text()),Path(a.lef).read_text())
    x['inputs']={k:{'path':getattr(a,k),'sha256':hashlib.sha256(Path(getattr(a,k)).read_bytes()).hexdigest()} for k in ('netlist','lef')}
    Path(a.output).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
if __name__=='__main__':main()
