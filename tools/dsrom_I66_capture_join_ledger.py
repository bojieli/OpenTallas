#!/usr/bin/env python3
"""Source-declaration ledger; existing/core/transport/repair never double counted."""
import ast,hashlib,json,operator,re
from pathlib import Path
import dsrom_I66_capture_owner as O
BASE=O.OUT/'inputs'
def register_count(source):
    constants=dict(PF=64,NBIN=256,CB=14,DIG=8)
    ops={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul}
    def value(s):
        def walk(n):
            if isinstance(n,ast.Constant) and type(n.value)==int:return n.value
            if isinstance(n,ast.Name):return constants[n.id]
            if isinstance(n,ast.BinOp) and type(n.op) in ops:return ops[type(n.op)](walk(n.left),walk(n.right))
            raise ValueError('unsupported register dimension')
        return walk(ast.parse(s,mode='eval').body)
    wanted=re.compile(r'^(hist_pc_\d+|hist_valid|suffix_up_\d+|suffix_down_\d+|choose_lower_sum|choose_pred|choose_node_\d+|eq_count_\d+|eq_id_\d+|eq_gt_\d+|eq_mask_\d+|eq_v_\d+|sort_record_\d+|take_count_\d+|take_total_\d+|sort_valid|pvalid|pk)$')
    inventory={}
    for m in re.finditer(r'\breg\s+(?:\[([^:\]]+):([^\]]+)\]\s*)?([^;]+);',source):
        for entry in m[3].split(','):
            name=re.match(r'\s*([A-Za-z0-9_]+)',entry)
            if not name or not wanted.fullmatch(name[1]):continue
            n=abs(value(m[1])-value(m[2]))+1 if m[1] else 1
            for lo,hi in re.findall(r'\[([^:\]]+):([^\]]+)\]',entry):n*=abs(value(lo)-value(hi))+1
            if name[1] in inventory:raise ValueError('duplicate register')
            inventory[name[1]]=n
    if sum(inventory.values())-3!=127140:raise ValueError('source core register count')
    return inventory

def ledger():
    origins=json.loads((BASE/'current_join_origins.json').read_text())
    for name,meta in origins.items():
        if hashlib.sha256((BASE/name).read_bytes()).hexdigest()!=meta['sha256']:raise ValueError('source join archive changed')
    transport=json.loads((BASE/'selector_transport.json').read_text())
    parent=json.loads((BASE/'selector_parent_review.json').read_text())
    inv=register_count((BASE/'selector_core.sv').read_text())
    ff=sum(x['EDGES']*(x['WIDTH']+1) for x in transport['helpers'])
    if ff!=476180 or ff!=parent['transport_total_FF']:raise ValueError('source transport register count')
    core_total=698354;core_delta=sum(inv.values())-3
    return dict(core=dict(full_state_bits=core_total,source_added_gross_bits=sum(inv.values()),replaced_baseline_bits=3,
                    net_added_bits=core_delta,inherited_core_state_bits=core_total-core_delta,source_inventory=inv),
                transport=dict(full_state_bits=ff,payload_HQ_bits=transport['instance_ledger']['DFFHQNx1_ASAP7_75t_R'],
                    present_ASR_bits=transport['instance_ledger']['DFFASRHQNx1_ASAP7_75t_R'],
                    helper_shapes=transport['helpers'],present_ties=229,core_ties_separate=35,
                    repair_changes_state_bits=0,existing_station_replaced_not_readded=True),
                selector_core_plus_transport_full_state_bits=core_total+ff,
                selector_delta_plus_transport_state_bits=core_delta+ff,
                delta_plus_transport_is_not_full_baseline_cost=True,
                capture=dict(raw_HQ_bits=39744,baseline_controller_ASR_bits=1483,read_pipeline_and_CDC_bits=None,required_extra_frozen_key_PC_identity_bits=46,
                    required_extra_identity_feedback_BUF_lower_bound=92,
                    extra_identity_not_inside_R49_baseline_controller=True,
                    feedback_only_BUF_bits=0,feedback_BUF_cells=82454,body_area_um2=O.hold_repair()['body_area_um2']),
                no_inherited_area_containment_credit=True,complete_slot_clock_reset_PG_union=False,
                link=dict(source_commit=origins['selected_link_handoff.json']['commit'],
                    proposal_ACK_TIMEOUT=4096,source_default_ACK_TIMEOUT=1024,default_FAIL_preserved=True,
                    local_capture_does_not_select_timeout=True,packet_ACK_is_not_VM_visible=True))
