import json
from pathlib import Path
r=Path('results/rtl/s81_cfifo_partition_1016');rows=[]
for lane,widths in enumerate([[113]*5,[108,108,107,107,107]]):
 lo=0
 for k,w in enumerate(widths):
  rows.append(dict(name=f'ingress_{lane}_{k}',master='dsfd_cfifo_ingress_slice',params=dict(W=w),outline_um=[47.52,47.52],home_um=[2.16+69.12*k,2.16+69.12*lane],clock_entries=['f_ck','ck'],clock_reset_ports=['rst_n'],source_root_sinks=9*w+37,read_root_sinks=w+23,rtl_bits=dict(lane=lane,lo=lo,width=w),pins=dict(i='S pitch0.096',o='N pitch0.096',f_ck='S adjacent i',ck='N adjacent o',rst_n='W',fault='N'),layer_cap='M5',PG='M5; parent straps M6',status='SOURCE_PROVEN_LAYOUT_UNQUALIFIED'));lo+=w
for k in range(9):
 w=128 if k<8 else 76
 rows.append(dict(name=f'format_{k}',master=('dsfd_cfifo_format_slice' if k in [2,4] else 'dsfd_cfifo_data_slice'),params=dict(W=w,QUALIFY=sum(1<<(b-128*k) for b in [282,549,550,564,568] if 128*k<=b<128*k+w)),outline_um=[21.6,17.28],home_um=[2.16+43.2*k,140.4],clock_entries=['ck'],clock_reset_ports=[],root_sinks=w,pins=dict(d='S pitch0.096',q='N pitch0.096',v='E',ck='W'),layer_cap='M5',PG='M5; parent straps M6',status='SOURCE_PROVEN_LAYOUT_UNQUALIFIED'))
rows.append(dict(name='return_control',master='dsfd_cfifo_return_control',outline_um=[25.92,17.28],home_um=[354.24,2.16],clock_entries=['ck'],clock_reset_ports=['rst','rs'],root_sinks=73,pins=dict(ri='N',st='N',rd='S',lane_fault='E',av='E',bv='E',rs='W',rst='W',ck='W'),layer_cap='M5',PG='M5; parent straps M6',status='PARENT_RI_TO_RD_PIN_REACH_NEEDS_CONNECTED_REDESIGN'))
for row in rows:
 if row['master']=='dsfd_cfifo_data_slice':
  row['params'].pop('QUALIFY',None);row['pins'].pop('v',None)
 if row['master']=='dsfd_cfifo_ingress_slice':
  row['payload_width']=row['params']['W'];row['master']='dsfd_cfifo_ingress'+str(row['payload_width']);row['params']={}
 elif row['master']=='dsfd_cfifo_data_slice':
  row['payload_width']=row['params']['W'];row['master']='dsfd_cfifo_data'+str(row['payload_width']);row['params']={}
 elif row['master']=='dsfd_cfifo_format_slice':
  row['payload_width']=row['params']['W'];row['master']='dsfd_cfifo_fmt128_'+('qa' if row['name']=='format_2' else 'qb');row['params']={}
 row['required_literal_pin_role_metadata']={'OT_PIN_REGS_CLOCK_PORTS':','.join(row['clock_entries']),'OT_PIN_REGS_RESET_PORTS':','.join(row['clock_reset_ports'])}
(r/'leaf_blueprint.json').write_text(json.dumps(dict(scope='UNQUALIFIED_PARTITION_SIZING_NOT_A_ROUTE_SPEC',leaves=rows,physical_clock_entries=30,cycles_added=0,source_semantics='oa[0] qualifies every output; lane faults ORed inside return_control; lane-valid mismatch sticky status unchanged',blockers=['10 first-pass overlaps: 8 source cx/cx_x2 stations at cf10/11/17/23 plus 2 foreign KV relays','Return ri N to rd S separation must be resolved using actual peer pins, extra output stage priced if needed','Parent source/read/output wires and actual cuts not proven','No final die plan/clock delivery/native qualification']),indent=2)+'\n')
