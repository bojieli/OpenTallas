#!/usr/bin/env python3
"""A2 controlled, R0-only assigned pin templates; no native/whole-VM fit claim."""
from area_id_pin_plan import template
from area_model_1417 import ROOT, checked_write, sha

def build():
    data=template('s81_area_stripe_W16',237.6,54.,{
        'N':[('i_data',848,'input')],
        'S':[('i_sel',168,'input'),('i_drain_v',8,'input'),('i_drain_slot',16,'input')],
        'E':[('o_data',128,'output'),('o_v',8,'output'),('fault',1,'output')],
        'W':[('ck',1,'input'),('rst_n',1,'input')]})
    meta=template('s81_area_stripe_W26',237.6,54.,{
        'N':[('i_data',1378,'input')],
        'S':[('i_sel',168,'input'),('i_drain_v',8,'input'),('i_drain_slot',16,'input')],
        'E':[('o_data',208,'output'),('o_v',8,'output'),('fault',1,'output')],
        'W':[('ck',1,'input'),('rst_n',1,'input')]})
    ctrl=template('s81_a2_controller',172.8,54.,{
        'N':[('ids',168,'output'),('dr_v',8,'output'),('dr_s',16,'output')],
        'S':[('src_v',53,'input'),('src_bank',424,'input'),('header_epoch',3,'input'),('payload_epoch',12,'input')],
        'E':[('fault',1,'output')],'W':[('ck_control',1,'input'),('rst_n',1,'input')]})
    fault=template('s81_area_id_fault_join',21.6,21.6,{
        'W':[('i_fault',10,'input'),('ck',1,'input'),('rst_n',1,'input')],
        'E':[('fault',1,'output')]})
    header=template('s81_a2_w0_header',216.,86.4,{
        'N':[('i_v',53,'input'),('i_row',742,'input'),('i_tag',424,'input')],
        'S':[('o_v',53,'output'),('o_row',742,'output'),('o_tag',424,'output'),('o_epoch',3,'output')],
        'W':[('ck',1,'input'),('rst_n',1,'input')]})
    payload=template('s81_a2_w0_payload',1166.4,86.4,{
        'N':[('i_data',6784,'input')],'S':[('o_data',6784,'output')],
        'W':[('i_mask',212,'input'),('ck',1,'input'),('rst_n',1,'input')],
        'E':[('o_mask',212,'output'),('o_epoch',3,'output')]})
    local=[dict(name='u_control',template='controller',xy_um=[324.,0.]),
           dict(name='u_fault',template='fault',xy_um=[453.6,137.7])]
    for k in range(9):local.append(dict(name='u_meta' if k==8 else f'u_data[{k}]',
        template='metadata26' if k==8 else 'data16',xy_um=[48.6+243*(k%3),81.+81*(k//3)]))
    sources=['tools/s81_vm/area_a2_controlled.sv','tools/s81_vm/area_id_native.sv','tools/s81_vm/area_id_native_join.sv']
    return dict(schema='opentallas.s81.vm-a2-controlled-pin-plan.v1',
        status='ASSIGNED_TEMPLATE_PINS_LOCAL_POSES_ONLY_NOT_NATIVE_OR_GLOBAL_FIT',
        source_sha256={p:sha(ROOT/p) for p in sources},
        templates=dict(data16=data,metadata26=meta,controller=ctrl,fault=fault,header=header,payload=payload),
        quarter_R0_outline_budget_um=[820.8,324.],local_quarter_leaves=local,
        repeated_quarters=[dict(slice=s,bank_base=q*8,
            candidate_instance=f'payload[{s}].quarter[{q}].u_quarter',clock_index=s*4+q,
            native_global_xy_um=None) for s in range(4) for q in range(4)],
        clock_ports=dict(W0_header='ck_header',W0_payload='ck_payload[3:0]',
            control='ck_control[15:0]',metadata='ck_meta[15:0]',fault='ck_fault[15:0]',data='ck_data[127:0]'),
        ingress_per_quarter=dict(W0_payload_and_metadata=8162,raw_source_header=477,registered_epochs=15,total=8654,
            source_clock_reset_excluded=True,source_N_S_budget_bits=[4327,4327],
            source_N_S_fraction_at820p8=4327*.096/820.8,
            W0payload_kept_wide_fraction=6784*.096/1166.4,
            narrow691p2_payload_fraction=6784*.096/691.2,
            narrow691p2_status='REFUSED_ON_ONE_LAYER_WITHOUT_STRUCTURAL_SPLIT_OR_EXACT_LEGAL_LAYER_PROOF'),
        local_hops=dict(controller_ID_and_drain_max_manhattan_um=432.,
            diagnostic_fault_max_manhattan_budget_um=451.,
            clock_reference='Each real root phi-R; insertion/spread unmeasured',
            global_status='Rawsource→controller,W0→fourquarters,read/return/bank/relaysand16faultcollectorUNPLACED'),
        routing_reserve=dict(quarter_boxes_mm2=16*820.8*324/1e6,
            quarter_internal_roads_mm2=2.25068544,
            source_global_PG_and_perimeter_status='Budgetonly; actualPGstripes/roads/layersunallocated'),
        assertions=['No rotation permitted without new pin/PG audit','All128realSRAM and32logicalR/Wports retained',
            'No14mm2fit,nativeclosure,fullprogrammepriceorproductionadoption claim'])

if __name__=='__main__':
    target=ROOT/'results/arch/s81_vm_area_1417/a2_pin_plan.json'
    checked_write(target,build());print(target)
