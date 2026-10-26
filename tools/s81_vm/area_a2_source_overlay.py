#!/usr/bin/env python3
"""Bit graph substitution over immutable geometry evidence, not elaboration."""
import collections
import copy
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
BASE=Path('/home/ubuntu/wt/s81-vm-geometry-1103/results/physical/s81_vm_geometry_1103')
OUT=ROOT/'results/arch/s81_vm_area_1417'
LOCK=Path('/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock')
SOURCES=['tools/s81_vm/area_a2_controlled.sv','tools/s81_vm/area_id_native.sv',
         'tools/s81_vm/area_id_native_join.sv','tools/s81_vm/area_a2_hardmasters.sv']
REMOVE={'dsfd_vm_static_wdispatch128','dsfd_vm_static_wstage128',
        'dsfd_vm_static_write_capture128','dsfd_vm_static_wcontrol'}


def check_lock():
    if json.loads(LOCK.read_text())['owner'] not in ('claude','codex'):
        raise RuntimeError('coordinator ownership changed')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ports(inputs,outputs):
    return {name:dict(direction=direction,bits=width)
            for direction,items in [('input',inputs),('output',outputs)]
            for name,width in items.items()}


def main():
    old=json.loads((BASE/'inventory.json').read_text())
    source_map=json.loads((BASE/'write_source_map.json').read_text())
    oldleaves=old['leaves']
    leaves=[]
    remap={}
    removed={i for i,l in enumerate(oldleaves)if l['master']in REMOVE}
    assert len(oldleaves)==640 and len(removed)==273
    header=next(i for i,l in enumerate(oldleaves)if l['master']=='dsfd_vm_static_w0_header')
    payload={int(re.search(r'w0_payload\[(\d+)\]',l['path'])[1]):i for i,l in enumerate(oldleaves)
             if l['master']=='dsfd_vm_static_w0_payload'}
    source_sha={name:sha(ROOT/name) for name in SOURCES}
    for i,leaf in enumerate(oldleaves):
        if i in removed:continue
        remap[i]=len(leaves)
        new=copy.deepcopy(leaf)
        if i==header or i in payload.values():
            kind='header' if i==header else 'payload'
            new.update(master='s81_a2_w0_'+kind,native_view_present=False,
                       master_source_sha256=source_sha[SOURCES[0]],
                       master_source_path=SOURCES[0],
                       candidate_rtl_path=('s81_a2_controlled.u_header' if kind=='header' else
                                           f's81_a2_controlled.payload[{next(k for k,v in payload.items()if v==i)}].u_payload'),
                       replacement_scope='same port mapping; native-reset source changed; prior view does not qualify candidate')
            new['prior_route_source_binding']=new.pop('route_source_binding',None)
        leaves.append(new)
    assert len(leaves)==367
    controls={}; stripes={}; metas={}; joins={}
    def add(x,q,name,master,params,pins,outline,pose,source,candidate_suffix):
        path=f'dut.u_core.u_ws.a2.payload[{x}].quarter[{q}].{name}'
        index=len(leaves)
        leaves.append(dict(path=path,master=master,parameters=params,ports=pins,home=None,
                           local_quarter_pose_um=pose,local_quarter_key=[x,q],
                           outline_um=outline,outline_scope='budget only; no native physical view',
                           native_view_present=False,kit=None,master_source_path=source,
                           master_source_sha256=source_sha[source],
                           candidate_rtl_path=f's81_a2_controlled.payload[{x}].quarter[{q}].u_quarter.'+candidate_suffix))
        return index
    for x in range(4):
        for q in range(4):
            controls[x,q]=add(x,q,'u_control',f's81_a2_controller_b{q*8}',{},
                ports(dict(ck_control=1,rst_n=1,src_v=53,src_bank=424,header_epoch=3,payload_epoch=12),
                      dict(ids=168,dr_v=8,dr_s=16,fault=1)),[172.8,54],[324,0],SOURCES[3],f'control_b{q*8}.u_control')
            for k in range(9):
                w=16 if k<8 else 26
                index=add(x,q,f'u_data{k}' if k<8 else 'u_meta',
                    's81_a2_stripe_data16' if k<8 else 's81_a2_stripe_meta26',{},
                    ports(dict(ck=1,rst_n=1,i_data=w*53,i_sel=168,i_drain_v=8,i_drain_slot=16),
                          dict(o_v=8,o_data=8*w,fault=1)),[237.6,54],
                    [48.6+243*(k%3),81+81*(k//3)],SOURCES[3],
                    f'data_stripe[{k}].u_data' if k<8 else 'u_meta')
                if k<8:stripes[x,q,k]=index
                else:metas[x,q]=index
            joins[x,q]=add(x,q,'u_fault','s81_area_id_fault_join',{},
                ports(dict(ck=1,rst_n=1,i_fault=10),dict(fault=1)),[21.6,21.6],
                [453.6,137.7],SOURCES[2],'u_fault')
    assert len(leaves)==543
    def endpoint(index,port,bit,direction='INPUT'):
        return [index,port,bit,direction]
    def stripe_targets(x,q):
        return [metas[x,q]]+[stripes[x,q,k]for k in range(8)]
    def map_consumer(e):
        i,port,bit,direction=e
        if i<0:return [e]
        if i not in removed:return [[remap[i],port,bit,direction]]
        leaf=oldleaves[i]
        if leaf['master']!='dsfd_vm_static_wdispatch128':return []
        x,q=map(int,re.search(r'slice\[(\d+)\].quarter\[(\d+)\]',leaf['path']).groups())
        if port=='i_data':
            s,b=divmod(bit,128)
            return [endpoint(stripes[x,q,b//16],'i_data',s*16+b%16)]
        if port in ('i_row','i_mask','i_tag'):
            width,offset={'i_row':(14,0),'i_mask':(4,14),'i_tag':(8,18)}[port]
            s,b=divmod(bit,width)
            return [endpoint(metas[x,q],'i_data',s*26+offset+b)]
        return []
    def map_driver(e):
        i,port,bit,direction=e
        if i<0:return [e]
        if i not in removed:return [[remap[i],port,bit,direction]]
        leaf=oldleaves[i]
        if leaf['master']!='dsfd_vm_static_write_capture128':return []
        x,group,local=map(int,re.search(r'slice\[(\d+)\].*write_group\[(\d+)\].capture\[(\d+)\]',leaf['path']).groups())
        bank=group*8+local;q=bank//8;b=bank%8
        if port=='o_data':return [endpoint(stripes[x,q,bit//16],'o_data',16*b+bit%16,'OUTPUT')]
        if port in ('o_row','o_mask','o_tag'):
            offset={'o_row':0,'o_mask':14,'o_tag':18}[port]
            return [endpoint(metas[x,q],'o_data',26*b+offset+bit,'OUTPUT')]
        if port in ('o_v','o_we'):return [endpoint(metas[x,q],'o_v',b,'OUTPUT')]
        return []
    stats=collections.Counter();input_seen=set();source_status=collections.Counter()
    check_lock()
    OUT.mkdir(parents=True,exist_ok=True)
    check_lock()
    with gzip.open(BASE/'pin_producer_join.jsonl.gz','rt')as inp,gzip.open(OUT/'a2_pin_join.jsonl.gz','wt')as output:
        def emit(row):
            for key,direction in [('drivers','output'),('consumers','input')]:
                for i,p,b,d in row[key]:
                    if i<0:continue
                    assert 0<=i<len(leaves) and p in leaves[i]['ports']
                    assert 0<=b<leaves[i]['ports'][p]['bits']
                    assert leaves[i]['ports'][p]['direction']==direction
            for i,p,b,d in row['consumers']:
                if i>=0:
                    assert (i,p,b)not in input_seen,'input bit belongs to multiple nets'
                    input_seen.add((i,p,b))
            stats[row['status']]+=1
            output.write(json.dumps(row,separators=(',',':'))+'\n')
        replacement_output_nets={}
        for line in inp:
            row=json.loads(line)
            consumers=[mapped for e in row['consumers']for mapped in map_consumer(e)]
            drivers=[mapped for e in row['drivers']for mapped in map_driver(e)]
            # Raw control inputs derive from the exact PRE-W0 source endpoints.
            for i,port,bit,direction in row['consumers']:
                if i==header and port=='i_v':
                    consumers.extend(endpoint(j,'src_v',bit)for j in controls.values())
                if i==header and port=='i_row' and bit%14<8:
                    consumers.extend(endpoint(j,'src_bank',(bit//14)*8+bit%14)for j in controls.values())
            # Actual W0 observation outputs feed all sixteen controller phase pins.
            for i,port,bit,direction in row['drivers']:
                if i==header and port=='o_epoch':
                    consumers.extend(endpoint(j,'header_epoch',bit)for j in controls.values())
                if i in payload.values() and port=='o_epoch':
                    x=next(k for k,v in payload.items()if v==i)
                    consumers.extend(endpoint(j,'payload_epoch',x*3+bit)for j in controls.values())
            if not consumers:continue
            # An unresolved/constant producer remains unresolved/constant.
            if row['drivers'] and not drivers:
                raise AssertionError(f'removed producer has unhandled retained consumers: {row}')
            row.update(drivers=drivers,consumers=consumers)
            if drivers and any(e[0]>=367 for e in drivers):
                # Old capture o_v and o_we collapse to one real metadata o_v
                # output. Preserve a single physical net with both fanouts.
                key=(row['status'],tuple(tuple(e)for e in drivers))
                if key in replacement_output_nets:
                    replacement_output_nets[key]['consumers'].extend(consumers)
                else:replacement_output_nets[key]=row
            else:emit(row)
        for row in replacement_output_nets.values():
            row['consumers']=[list(e)for e in dict.fromkeys(tuple(e)for e in row['consumers'])]
            emit(row)
        for x in range(4):
            for q in range(4):
                ctrl=controls[x,q];targets=stripe_targets(x,q)
                for outport,inport,width in [('ids','i_sel',168),('dr_v','i_drain_v',8),('dr_s','i_drain_slot',16)]:
                    for bit in range(width):
                        emit(dict(status='ONE_DRIVER',drivers=[endpoint(ctrl,outport,bit,'OUTPUT')],
                                  consumers=[endpoint(j,inport,bit)for j in targets],overlay_internal=True))
                # join input bit order follows {fd[7:0],fm,fc}.
                faults=[ctrl,metas[x,q]]+[stripes[x,q,k]for k in range(8)]
                for bit,j in enumerate(faults):
                    emit(dict(status='ONE_DRIVER',drivers=[endpoint(j,'fault',0,'OUTPUT')],
                              consumers=[endpoint(joins[x,q],'i_fault',bit)],overlay_internal=True))
                for j in [ctrl]+targets+[joins[x,q]]:
                    for p in leaves[j]['ports']:
                        if p not in ('ck_control','ck','rst_n'):continue
                        role='clock' if p!='rst_n' else 'reset'
                        root_index=x*4+q
                        if j==ctrl:clock_port='ck_control';reset_port='rst_control_n'
                        elif j==metas[x,q]:clock_port='ck_meta';reset_port='rst_meta_n'
                        elif j==joins[x,q]:clock_port='ck_fault';reset_port='rst_fault_n'
                        else:
                            k=next(k for k in range(8)if stripes[x,q,k]==j)
                            clock_port='ck_data';reset_port='rst_data_n';root_index=8*root_index+k
                        top_port=clock_port if role=='clock' else reset_port
                        emit(dict(status='ONE_DRIVER',drivers=[endpoint(-1,'A2_'+top_port,root_index,'OUTPUT')],
                                  consumers=[endpoint(j,p,0)],overlay_planned_native_pin=True,
                                  candidate_top_port=top_port,candidate_top_port_bit=root_index,
                                  clock_reset_delivery_qualified=False))
    missing=[]
    for i in range(367,len(leaves)):
        for p,description in leaves[i]['ports'].items():
            if description['direction']=='input':
                missing.extend([i,p,b]for b in range(description['bits'])if(i,p,b)not in input_seen)
    assert not missing,missing[:10]
    clocks=sum(p['bits']for l in leaves for n,p in l['ports'].items()if 'ck'in n and p['direction']=='input')
    assert clocks==591
    retained_sram=[l for l in leaves if l['master']=='dsfd_vm_static_bank128']
    old_sram=[l for l in oldleaves if l['master']=='dsfd_vm_static_bank128']
    assert retained_sram==old_sram and len(retained_sram)==128
    families=dict(collections.Counter(l['master']for l in leaves))
    inventory=dict(schema='opentallas.s81.a2-source-overlay.v1',scope='SOURCE_BIT_GRAPH_SUBSTITUTION_NOT_ELABORATED_OR_PHYSICALLY_QUALIFIED',
                   base_source_commit=old['source_commit'],configuration=old['configuration'],
                   source_sha256=source_sha,hard_leaf_count=543,hard_clock_pin_count=591,
                   families=families,leaves=leaves,source_write_map=source_map,
                   local_quarter_bbox_um=[820.8,324],local_pose_scope='relative quarter template only; no global coordinates or full fit',
                   global_diagnostic_collector='OPEN: sixteen new fault-join outputs have no global collector',
                   not_claimed=['new elaboration','global geometry','routed native views','timing','complete diagnostic collector'])
    summary=dict(status='PASS_SOURCE_OVERLAY_STRUCTURAL_CHECKS_ONLY',old_hard_leaves=640,removed=273,retained=367,
                 added_native_quarter_leaves=176,new_hard_leaves=543,hard_clock_pins=591,
                 SRAM=dict(instances=128,bytes=1048576,all_inventory_records_ports_and_source_binding_byte_equal=True),
                 raw_ingress_per_quarter=dict(W0_payload_and_metadata_bits=8162,raw_src_bits=477,epoch_bits=15,
                                             total_logical_ingress_bits=8654,clock_reset_additional=True,
                                             scope='logical distinct input signal positions before local fanout; constants/aliases may reduce actual unique drivers'),
                 graph_status_counts=dict(stats),new_leaf_missing_input_bits=0,
                 graph_endpoint_direction_and_width_errors=0,multiple_net_input_bits=0,
                 old_unknown_and_constant_status_preserved=True,
                 global_fault_collector='OPEN',new_unconnected_join_fault_outputs=16,
                 source_sha256=source_sha,
                 input_evidence_sha256={name:sha(BASE/name)for name in ['inventory.json','pin_producer_join.jsonl.gz','write_source_map.json']},
                 generator_sha256=sha(Path(__file__)),
                 limitations='Source overlay using explicit bit substitutions, not elaborated replacement. Retained legs/source bindings preserved; no invented homes, new clocks planned, no whole-VM fit or physical qualification.')
    check_lock();(OUT/'a2_inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    check_lock();(OUT/'a2_overlay_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:summary[k]for k in ['status','new_hard_leaves','hard_clock_pins','new_leaf_missing_input_bits']}))


if __name__=='__main__':main()
