#!/usr/bin/env python3
"""Role-specific HBROM service reservations. Analytical estimates, never closure.

Cell estimates are expanded at 50% utilization; existing physical reservations
and macro abstracts are not expanded a second time. Explicit allowances remain
unmeasured and are not guaranteed upper bounds. Shared matrix tile private and
cluster RF/scratch inventories are excluded: hbrom_model already prices them.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / 'results/uarch/hbrom/inputs'


def service_area(role='full_service', *, index_keys_per_cycle=64,
                 he_lanes=1536, quantizers=32, persistent_layers=40):
    if role in ('layer', 'source_owner', 'source_owner_candidates', 'head'):
        return _layer_service_area(role, index_keys_per_cycle, he_lanes, quantizers)
    if role not in ('full_service', 'dedicated_service', 'compute_only', 'archive'):
        raise ValueError('unknown service role')
    for v in (index_keys_per_cycle, he_lanes, quantizers, persistent_layers):
        if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
            raise ValueError('positive integer dimensions required')
    if index_keys_per_cycle % 4:
        raise ValueError('index scorer consists of four-key slices')
    rows=[]
    def add(name, count, unit, basis, includes, evidence='analytical_allowance'):
        rows.append(dict(name=name, replicas=count, unit_reservation_mm2=unit,
                         area_mm2=count*unit, basis=basis, includes=includes,
                         evidence=evidence, measured_for_hbrom=False))
    # Existing d2d endpoints are not inside compute-tile arithmetic/RF macros.
    add('link_endpoints_and_router', 1, 8, 'explicit unmeasured physical allowance',
        'two link endpoints, arbitration, credit queues; excludes external PHY silicon')
    add('control_identity_protection', 1, 2, 'explicit unmeasured physical allowance',
        'scheduler, descriptors, tags, address bounds, protected mutable ownership')
    add('CDC_and_link_protection', 1, 2, 'explicit unmeasured physical allowance',
        'ratio FIFOs, link check/retry storage; no ROM ECC')
    if role in ('full_service','dedicated_service'):
        hub=json.loads((INPUTS/'hbrom-hub.json').read_text())
        att=json.loads((INPUTS/'hbrom-attention.json').read_text())
        idx=json.loads((INPUTS/'hbrom-index.json').read_text())
        index_unit=next(x['estimated_scorer_area_mm2']/x['NK4_slices']
                        for x in idx['compute_sweep'] if x['keys_per_cycle']==4)
        add('SU_VM',1,hub['physical']['minimum_existing_SU_VM_footprint_mm2'],
            'VMC_BLOCK physical reservation', '1024/256 lanes, 1536 SRAM macros, VM network',
            'inherited_floorplan_reservation')
        add('attention_compute',1,att['area']['compute_estimate_mm2_per_engine']*2,
            'primitive MAC cells / 0.50 placement utilization',
            '64 H16 TD32 tiles; excludes all attention SRAM and load flops')
        add('index_scorer',index_keys_per_cycle//4,index_unit*2,
            'NK4 primitive cells / 0.50 placement utilization',
            'exact FP4 products and per-key head sums; excludes reader and selectors')
        phy_path=ROOT/'physical/asap7_memory_macros_v2/ot_hbm3e_phy_v41x_aw30/ot_hbm3e_phy_v41x_aw30.lef'
        phy_wh=[float(x) for x in re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',phy_path.read_text()).groups()]
        add('HBM_PHY',4,math.prod(phy_wh)/1e6,'ot_hbm3e_phy_v41x_aw30 actual LEF SIZE',
            'four stack PHYs only; HBM DRAM silicon counted separately', 'macro_abstract')
        add('HBM_controllers_readers_collectors',4,1.5,
            'explicit unmeasured physical allowance per stack',
            '128 total PC readers, sector response assembly, arbitration, protection')
        add('HE_projection',he_lanes,1168.791e-6*2,
            'FP32 add+mul cells / 0.50 utilization', 'FP32 MAC lanes only')
        add('HE_tree_operand_delivery',1,2,'explicit unmeasured physical allowance',
            'chunk8 accumulators, tree, independent side-branch operand supply')
        add('Sinkhorn',1,.0330914*2,'historical cell area / 0.50 utilization',
            '4x4 20-iteration unit; frequency remains historical151.9MHz pending qualification')
        add('quantizers',quantizers,.05,
            'explicit unmeasured per32-element quantizer physical allowance',
            'FP8/FP4 scale/max/round logic; no fast32-instance service until validated')
        add('index_select_and_merge',index_keys_per_cycle,.0353424*2,
            'K512 unit cells / 0.50 utilization; one per key lane',
            'local selector units; merge storage/controller additional')
        add('selector_merge_and_router_select',1,2,'explicit unmeasured physical allowance',
            'global-index exact top512 merge, candidate membership, router top6/order6')
        # Same SRAM density as the existing SUVM macro inventory; whole macros.
        sram_per=10.893/1536
        stores={
          'attention_packed_staging':att['storage']['packed_engine_staging_provisioned_B'],
          'attention_stationary_PWORDS2':att['storage']['PWORDS2_stationary_B'],
          'attention_scores_probability_PV':40960+20480+32768,
          'persistent_windows':persistent_layers*67584,
          # Worst-rank candidate placement, not assumed balanced quarter.
          'index_candidate_keys':16384*68,
          'selector_lists_and_membership':index_keys_per_cycle*512*8+16384*8,
        }
        for name, size in stores.items():
            add(name,math.ceil(size/8192),sram_per,
                'whole256x256 SRAM macros at inherited density',
                f'{size} useful bytes before SECDED; packed staging retains selected rows',
                'analytic_macro_reservation')
        extra_sram=sum(x['area_mm2'] for x in rows if x['evidence']=='analytic_macro_reservation')
        add('SRAM_protection_parity',1,(10.893+extra_sram)/8,
            '72/64 SECDED check-bit capacity allowance',
            'SUVM and dedicated SRAM parity capacity; codec not included')
        add('SRAM_protection_codecs',1,4,'explicit unmeasured physical allowance',
            'parallel ECC encode/decode/fault gating; all active service ports')
        add('attention_load_registers',1,65536*.2916e-6*2,
            'DFF cell area /0.50 utilization', 'PWORDS2 tile load registers')
        add('service_global_routing_clock',1,12,'explicit unmeasured physical allowance',
            'hub inter-unit channels, registers, clock gates/CTS; local placement already included')
    elif role=='archive':
        add('lookup_service_SRAM',1,2,'explicit unmeasured physical allowance',
            'Engram/embedding lookup response queues and protected scratch')
        add('lookup_address_fanout',1,2,'explicit unmeasured physical allowance',
            'hash/tag/ROM descriptor selection, address fanout and result collection')
    else:
        add('compute_die_global_routing',1,4,'explicit unmeasured physical allowance',
            'matrix cluster-to-link activation/result channels; tile local routing excluded')
    return dict(role=role,total_mm2=sum(x['area_mm2'] for x in rows),components=rows,
                qualified=False,complete_measured_inventory=False,
                assumptions=dict(index_keys_per_cycle=index_keys_per_cycle,he_lanes=he_lanes,
                                 quantizers=quantizers,persistent_layers=persistent_layers),
                missing_measured_components=[x['name'] for x in rows if x['evidence']=='analytical_allowance'],
                excluded=['weight ROM macros and captures','matrix tiles and cluster RF/scratch',
                          'HBM DRAM dies','Engram external table payload storage'],
                claim='nonzero analytical reservations, not guaranteed physical bounds or SS/FF closure')


def _layer_service_area(role, index_keys_per_cycle, he_lanes, quantizers):
    """One colocated layer per rank, with HBM only on the four source owners."""
    base=service_area('full_service',index_keys_per_cycle=index_keys_per_cycle,
                      he_lanes=he_lanes,quantizers=quantizers,persistent_layers=1)
    rows=base['components']
    if role!='source_owner_candidates':
        rows=[r for r in rows if r['name']!='index_candidate_keys']
    if role in ('layer','head'):
        absent={'HBM_PHY','HBM_controllers_readers_collectors','index_scorer',
                'index_select_and_merge','selector_lists_and_membership'}
        rows=[r for r in rows if r['name'] not in absent]
        for r in rows:
            if r['name']=='selector_merge_and_router_select':
                r.update(name='router_select',unit_reservation_mm2=1,area_mm2=1,
                         includes='local top6/index-order selection; remote index selection not duplicated')
    if role=='head':
        absent={'attention_compute','attention_packed_staging','attention_stationary_PWORDS2',
                'attention_scores_probability_PV','persistent_windows','attention_load_registers'}
        rows=[r for r in rows if r['name'] not in absent]
        for r in rows:
            if r['name']=='router_select':
                r.update(name='head_select',includes='exact local/global argmax candidate tracking and tie order')
    else:
        # Separate forward lease lets selected rows remain live while next hop accepts them.
        n=math.ceil(147456/8192)
        rows.append(dict(name='selected_forward_slot',replicas=n,
                         unit_reservation_mm2=10.893/1536,area_mm2=n*10.893/1536,
                         basis='whole256x256 SRAM macros at inherited density',
                         includes='147456B additional immutable selected-row forwarding lease',
                         evidence='analytic_macro_reservation',measured_for_hbrom=False))
    # Recompute parity after deleting role-inapplicable data arrays and adding forward lease.
    extra=sum(r['area_mm2'] for r in rows if r['evidence']=='analytic_macro_reservation')
    for r in rows:
        if r['name']=='SRAM_protection_parity':
            r['area_mm2']=r['unit_reservation_mm2']=(10.893+extra)/8
    base.update(role=role,components=rows,total_mm2=sum(r['area_mm2'] for r in rows),
                missing_measured_components=[r['name'] for r in rows if r['evidence']=='analytical_allowance'])
    base['assumptions']['persistent_layers']=0 if role=='head' else 1
    base['assumptions']['HBM_stacks']=4 if role.startswith('source_owner') else 0
    base['communication_obligations']=(
        'source_owner is L2/L8/L14; source_owner_candidates is L20. All other layers retain local SU/attention. '
        'L24/28/32/36 index queries execute remotely at L20: charge query, IDs and selected-row responses, '
        'source-owner index resource contention, forwarding hops and protected row leases. '
        'Head has no attention/window/HBM/index. SRAM-only windows persist per layer; initial context population '
        'and updates require explicit source transport. No free remote service is implied by area savings.')
    return base


def build(compute_dies=4, archive_dies=1):
    if compute_dies<=0 or archive_dies<0:
        raise ValueError('invalid die counts')
    roles={r:service_area(r) for r in ('full_service','dedicated_service','compute_only','archive','layer','source_owner','source_owner_candidates','head')}
    uniform=dict(role_counts={'full_service':compute_dies,'archive':archive_dies},
                 extra_service_dies=0,HBM_stacks=4*compute_dies)
    dedicated=dict(role_counts={'compute_only':compute_dies,'dedicated_service':4,'archive':archive_dies},
                   extra_service_dies=4,HBM_stacks=16,
                   incremental_remote_traffic_B_per_token=dict(Q=40*65536,PV=40*131072),
                   minimum_additional_phase_crossings=80,
                   caveat='Q/PV alone: norm/SU/HC offload, index queries, residuals, KV updates and routing endpoint serialization additional; must rebuild DAG/calendar before claiming dedicated-role TPOT')
    for v in (uniform,dedicated):
        v['total_service_reservation_mm2']=sum(roles[r]['total_mm2']*n for r,n in v['role_counts'].items())
    paths=[INPUTS/f'hbrom-{n}.json' for n in ('hub','attention','index')]+[Path(__file__), ROOT/'physical/asap7_memory_macros_v2/ot_hbm3e_phy_v41x_aw30/ot_hbm3e_phy_v41x_aw30.lef']
    return dict(schema='opentallas.hbrom.service-area.v1',roles=roles,
                scenarios=dict(uniform_colocated=uniform,dedicated_four_rank=dedicated),
                source_owner_layer_roles={str(l): ('source_owner_candidates' if l==20 else 'source_owner' if l in (2,8,14) else 'layer') for l in range(40)},
                source_role_count_at_TP4=dict(source_owner=12,source_owner_candidates=4,layer=144,head=4),
                source_role_HBM_stacks=64,
                selection='uniform_colocated until remote-service calendar is composed',
                known_primitive_and_macro_base_mm2=38.601+16.690446336+21.677952+40,
                source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                status='analytical_area_reservations_not_physical_qualification')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--compute-dies',type=int,default=4)
    p.add_argument('--archive-dies',type=int,default=1)
    p.add_argument('--out',type=Path,default=ROOT/'results/uarch/hbrom/service_area.json')
    a=p.parse_args();out=build(a.compute_dies,a.archive_dies)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
