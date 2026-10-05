#!/usr/bin/env python3
"""Source-bound declared return storage scaling; no occupancy or hardware admission."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/dsrom_return_scaling_source_audit_20261002'
FIELD='3a89958cacaa742eaa0fbf716180d35530fc8d28'
TEMPLATE='ecc0b0d4a14cd9d97d2ffb6e73f063c19baafe2c'
LIFETIME='93efabc2d9fd6f3402a6f586798b45fd97adbabc'
PINS={}


def read(rev,path):
    raw=subprocess.check_output(['git','show',rev+':'+path],cwd=ROOT)
    PINS[rev+':'+path]=hashlib.sha256(raw).hexdigest()
    return raw


def declaration(np,r=128,nbf=1024,rd=64,rootd=128,rst=1):
    if min(np,r,nbf)<1 or rst<0 or np<nbf or np&(np-1) or r&(r-1) or r>np or min(rd,rootd)<2:
        raise ValueError('illegal source topology/depth')
    if rd&(rd-1) or rootd&(rootd-1):
        raise ValueError('circular FIFO depths must be powers of two')
    nodes=2*np-r
    node_queues=nodes*2*rd*65
    node_rst=nodes*rst*66
    root_floor=r*rootd*(65+66)
    bits=node_queues+node_rst+root_floor
    return dict(compiled_NP=np,R=r,NBF=nbf,return_nodes=nodes,
        logical_macro_leaves=2*np,physical_PP4096_banks=4*np,
        node_queue_bits=node_queues,node_RST_bits=node_rst,
        fixed_root_bits=root_floor,declared_lower_bits=bits,
        conservative_FF_50pct_mm2=bits*.37908/.5/1e6,
        region_tree_levels=(2*np//r).bit_length()-1,
        sibling_noqueue_source_cycles=((2*np//r).bit_length()-1)*6,
        root_public_port_count=r,root_public_bits_per_cycle=r*69,
        distributed_node_write_bytes_per_cycle=nodes*2*65/8,
        distributed_node_read_bytes_per_cycle=nodes*2*65/8,
        source_array_discount_admitted=False,physical_or_calendar_qualified=False)


def generate():
    PINS.clear()
    field=read(FIELD,'rtl/v41die/ot_v41_field_w17w10.sv').decode()
    ret=read(FIELD,'rtl/v41rom/ot_v41_ret.sv').decode()
    retn=read(FIELD,'rtl/v41die/ot_v41_retn_w17w10.sv').decode()
    pair=read(FIELD,'rtl/v41die/ot_v41_pair_w17w10.sv').decode()
    template=json.loads(read(TEMPLATE,'results/uarch/dsrom_return_partition_template_20261002/model.json'))
    lifetime=json.loads(read(LIFETIME,'results/rtl/dsrom_return_lifetime_audit_20261002/model.json'))
    needles=[('field',field,'localparam integer NL = 2 * NP'),
        ('field',field,'for (g = 0; g < NP; g = g + 1)'),
        ('field',field,'for (g = 0; g < (NL >> (l + 1)); g = g + 1)'),
        ('field',field,'for (g = 0; g < R; g = g + 1)'),
        ('ret',ret,'reg [31:0] at [0:D-1], bt [0:D-1]'),
        ('ret',ret,'reg [31:0] qt [0:QD-1]'),
        ('ret',ret,'reg        bv [0:D-1]'),
        ('retn',retn,'ot_hdc_delay #(.W(65), .D(RST))'),
        ('pair',pair,'ot_v41_rom_elem_w10 #')]
    for kind,text,needle in needles:
        if needle not in text:raise ValueError('source equation changed: '+kind+' '+needle)
    cases=[]
    for prior in template['partition_cases']:
        np=prior['tree']['NP'];now=declaration(np)
        if now['declared_lower_bits']!=prior['tree']['lower_bits']:
            raise ValueError('prior declared topology count differs')
        now['preexisting_capacity_reference_layer_dies']=prior['layer_dies']
        now['aggregate_pair_capacity_reference']=prior['layer_dies']*np
        now['aggregate_return_declared_bits_reference']=prior['layer_dies']*now['declared_lower_bits']
        cases.append(now)
    return dict(schema='opentallas.return.compiled_topology_scaling.v1',
        status='DECLARED_STATE_SCALES_WITH_COMPILED_TOPOLOGY_NOT_ACTIVE_WORKLOAD_CREDIT',
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),source_pins=dict(PINS),
        equations=dict(nodes='2*NP-R',
            bits='(2*NP-R)*(2*RD*65+RST*66)+R*(QD*65+D*66), QD=D=ROOTD128',
            current_fixed_depth='8386*(2*NP-128)+2146304',
            meaning='138469120bits is exact NP8192/R128 declared lower bound, not an irreducible fixed workload storage demand. It remains reserved for that compiled topology; source controls, adders and mux/clock costs are extra.'),
        current_compiled=declaration(8192),
        active_pair_mask=dict(compiled_NP=8192,active_workload_pairs=6899,
            declared_lower_bits=138469120,
            reason='RTL generates every pair and every return node using NP, not image active mask. Fewer configured live pairs alone cannot remove parent state or prove synthesis pruning.',
            current_BF_site_image_hardware_mismatch=781),
        preexisting_partition_parameter_cases_not_new_sweep=cases,
        aggregate_scaling='At fixed aggregate compiled pair capacity, fewer pairs per die lower per-die storage but replicated root contexts add a fixed positive per-die intercept. No aggregate storage saving or token speedup follows automatically. Existing reference partition counts are parameter arithmetic, not compiled ownership.',
        parameter_change_obligations=[
            'Compile-bind actual power-of-two NP/R/NBF full topology and all padded complete elements; no arbitrary2966-node geometry or active-only return surrogate.',
            'Re-emit every affected bank/config/ROM/program phase under fixed4096 PP macro geometry, preserving aggregate payload, compute contexts and exact row/segment/position tags and golden order.',
            'Prove per-pair NSEG8/class/FIFO and ROM depth capacity; reduced NP can increase work and live backlog per pair. A per-die tree capacity reduction is not workload occupancy proof.',
            'Resolve actual BF site map and preserve1024 BF pairs/128 row ports; image relocation is a mandatory source binding gate.',
            'Join actual arrival skew, node/root occupancy, leaf DRAIN127, freeclock return quiet, all write visibility and dependent consumer reads to Maxwell calendar.',
            'Price extra die instances/links/serial service latency and all omitted return logic before reticle fit or adoption; no physical or token qualification from parameter arithmetic.'],
        lifetimes_and_ports=dict(source_record_commit=LIFETIME,
            contracts=lifetime['lifetime_contracts'],
            VM_edge_contract=lifetime['retained_VM_consumer_source_contract'],
            actual_current_L0_L20_peak_live_bytes=None,
            legal_reuse='Only existing local FIFO slots released by old-head capture/pop and root held slots released by sibling capture. Pipeline value remains live. No cross-owner scratch pool/address alias/ACK exists in current source.',
            port_credit=0,occupancy_area_credit=0,embedded_slot_area_credit=0,
            same_edge_read_write='Local old-data capture before NBA overwrite is necessary; cross-owner sharing also requires simultaneous independent read/write ports and source latency equivalence.'),
        exact_once_scope=dict(pair_local='Pair-local chain/segment state belongs to element slot.',
            field_parent='g_lv.u_n and g_r.u_root are outside pair hierarchy, counted once as global return. No named mapped-provider proof demonstrates they are already inside historical slot pricing.',
            generic_return_adder='Replace earlier approximate return-adder model with exact source count; never add both.'),
        decision=dict(current_reservation_bits=138469120,current_reservation_mm2=104.9817480192,
            compiled_NP_resize_admitted=False,reticle_fit=False,fulltoken=False,
            no_scratch_alias=True,no_new_RTL=True,no_PNR=True,no_jobs=True,
            priority='DSROM fixed4096/fewer-complete-element reticle proof; archived HBM draft deferred.'))


if __name__=='__main__':print(json.dumps(generate(),indent=2,sort_keys=True))
