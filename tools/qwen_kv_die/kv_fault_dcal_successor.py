#!/usr/bin/env python3
"""Price the required DCAL leaf without inventing a physical fault pin.

Preserves every old node/transport. This is an uninstalled logical successor,
not a placement candidate and not a fixed STATUS or reset admission receipt.
"""
import argparse, copy, hashlib, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'kv_fault_bench'))
from fault_bench import normalize,path_latencies

def successor(inventory,candidate,exact):
    if len(candidate['sources'])!=356 or inventory['sources']!=candidate['sources']:
        raise ValueError('requires exact unchanged 356-source predecessor')
    pins=exact['additional_dcal_fault']
    if len(pins)!=1:raise ValueError('ambiguous DCAL evidence')
    pin=pins[0]
    if (pin['master'],pin['instance'],pin['port'],pin['width'],pin['parameters']) != ('qkd_d2d_cal_seq_pin_bc','dcal','fault',1,{'EP_SKEW':'3','GO_OFS':'0','MUT':'0'}):
        raise ValueError('unreviewed DCAL source/profile')
    if pin['clock_reset_pins']!={'ck':'n_clk_core_c[0]','rst_n':'n_rrs_n_rst_link_t0__m_0__s0[0]'}:
        raise ValueError('DCAL ownership changed')
    if pin['expression']:raise ValueError('predecessor unexpectedly already wires DCAL')
    c=copy.deepcopy(candidate)
    source=dict(id='dcal.fault',instance='dcal',master=pin['master'],port='fault',parameters=pin['parameters'],signal=None,
                clock=pin['clock_reset_pins']['ck'],reset=pin['clock_reset_pins']['rst_n'],sticky=True,requires_sticky_latch=False,
                pin_xy=None,native_exposure_required=True,rtl=pin['rtl'],rtl_sha256=pin['rtl_sha256'],
                internal_reset_release_edges=2,error_predicates=['s_fault','COL','RUN','STALE','EARLY'])
    if source['clock']!=inventory['consumer']['clock']:raise ValueError('new CDC requires separate transport model')
    c['sources'].append(source)
    old=c['sink'];rst=inventory['consumer']['reset'];ck=source['clock']
    for name,a,b,kind in [('dcal_tail_join',old,'dcal.fault','join'),('dcal_tail_sticky','dcal_tail_join','dcal_tail_sticky','sticky')]:
        c['nodes'].append(dict(id=name,a=a,b=b,kind=kind,latency=1,master='qkd_astk_fault_join',clock=ck,reset=rst,
                               placement=None,native_clock_reset_geometry_required=True))
    c['sink']='dcal_tail_sticky';c['retirement_quiet_cycles']+=2
    sources,ops,sink=normalize(c,True);ages=path_latencies(sources,ops,sink)
    c.update(schema='opentallas.kv_fault_dcal_logical_successor.v1',status='MODEL_ONLY_NATIVE_EXPOSURE_AND_TERMINAL_OBLIGATIONS_OPEN',qualified_release=False,
             source_count=357,inventory_complete=False,max_leaf_latency_bound=max(ages.values()),leaf_latencies=ages,
             added_cell_count=candidate['added_cell_count']+2,added_cell_area_um2=round(candidate['added_cell_area_um2']+2*21.6**2,4),
             binary_join_count=candidate['binary_join_count']+1,sticky_cell_count=candidate['sticky_cell_count']+1,
             successor_delta=dict(join_cells=1,sticky_cells=1,clock_pins=2,reset_pins=2,model_area_um2=2*21.6**2,
                                  old_leaf_extra_edges=2,dcal_pin_to_collector_edges=2,predicate_to_pin_edges=1,
                                  native_wire_um=None,native_clock_skew_ps=None,native_reset_skew_ps=None),
             fixed_status_contract=dict(enabled=False,functional_cutoff=None,status_edge=None,
                required_edges=['source predicate registration','per-source join/transport path','final collector','AFR','TX codec','native link','LAND','consumer'],
                terminal_path_edges=None,clear_contract_required=['exact DCAL regional reset ancestry','release_q[1] two-edge release',
                    'all source sticky clear','AHUB hf source clear plus 34/37 relay drain','loaded root/clock native bounds','priced fixed POR/admission counter width'],
                diagnostics_not_admitted=dict(root_skew_cycles=64,sink_reset_depth=273,HOLD=128,IGNORE=255),
                admission_obligations={'cal_ready':'compiler/image-derived fixed edge or priced observation','adm_done':'compiler/image-derived fixed edge or priced observation'},
                continuous_sticky_health=True,mask_at_cutoff=False,conditional_wait=False),
             physical_blockers=candidate['physical_blockers']+[dict(source='dcal.fault',reason='Require real output connection and native fault pin; no guessed coordinate'),
                 dict(source='dcal_tail_join/dcal_tail_sticky',reason='Both cells require exact clock/reset ownership, collision-free geometry and loaded native timing')])
    return c

def main():
    p=argparse.ArgumentParser();p.add_argument('--dir',type=Path,required=True);p.add_argument('--exact-pins',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    import gzip
    inv=json.loads((a.dir/'inventory.json').read_text());old=json.loads((a.dir/'candidate.json').read_text())
    raw=a.exact_pins.read_bytes();exact=json.loads(gzip.decompress(raw) if a.exact_pins.suffix=='.gz' else raw)
    c=successor(inv,old,exact);c['input_sha256']={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (a.dir/'inventory.json',a.dir/'candidate.json',a.exact_pins)}
    a.out.write_text(json.dumps(c,indent=1)+'\n');print(json.dumps({k:c[k] for k in ('source_count','max_leaf_latency_bound','successor_delta','qualified_release')}))
if __name__=='__main__':main()
