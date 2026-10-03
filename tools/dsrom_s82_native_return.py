"""Actual existing full-RD64 native-cell mapping receipt; no timing or fit transfer."""
import argparse,gzip,hashlib,json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_s82_native_return_20261003/r1'
AREAS={'DFFASRHQNx1_ASAP7_75t_R':.37908,'DFFHQNx1_ASAP7_75t_R':.2916,'INVx1_ASAP7_75t_R':.04374,'NAND2x1_ASAP7_75t_R':.08748}
def summarize(netlist):
 m=netlist['modules']['ot_v41_retn_w17w10'];counts=Counter(c['type'] for c in m['cells'].values())
 if set(counts)-set(AREAS):raise ValueError('non-native/unpriced cell types')
 area=sum(counts[k]*AREAS[k] for k in counts)
 return dict(cell_counts=dict(sorted(counts.items())),cells=sum(counts.values()),flops=counts['DFFHQNx1_ASAP7_75t_R']+counts['DFFASRHQNx1_ASAP7_75t_R'],cell_area_um2=area,FF50_component_reservation_um2=2*area,ports=len(m['ports']),port_bits=sum(len(p['bits']) for p in m['ports'].values()))
def build():
 if (BASE/'exit.rc').read_text().strip()!='0':raise ValueError('native mapping not successful')
 s=summarize(json.loads(gzip.decompress((BASE/'mapped.json.gz').read_bytes())))
 return dict(candidate='DS4096-TP4-S82-PAIR1',source_commit='fecb33b6dcfdecc79308c1c885ff458791803144',canonical_commit='feba0739366dfe9adb98991e59bd0cee687f5d55',actual_mapping=s,parameters={'RD':64,'RST':1,'BYPASS':1},native_node_instances=8064,node_cell_area_projection_mm2=s['cell_area_um2']*8064/1e6,node_FF50_projection_mm2=s['FF50_component_reservation_um2']*8064/1e6,retained_node_FF50_storage_mm2=51.27034558464,node_logic_delta_before_containment_mm2=s['FF50_component_reservation_um2']*8064/1e6-51.27034558464,root_storage_retained_mm2=1.62724184064,root_logic_mapped=False,root_instances_retained=128,hold_clock_PG_route_added=False,one_explicit_NAND_INV_construction_not_minimum_area_proof=True,metadata_only_no_weight_reads=True,SSFF_timing_qualified=False,PnR_admitted=False,full_die_fit=False,capacity_impossibility_claim=False,existing_area_screen_is_not_composed_native_area=True,allocation_target='Replace retained per-node storage slots with complete-node home; bind logic delta to named residual/fixed union before charging twice or taking credit',job=dict(host='5.199.165.104',unit='dsrom-s82-return-area-r1.service',directory='/srv/opentallas-scratch/codex/s82-return-area-r1',terminal='exit0',MainPID=0,admit_GB=16,run_memory_time_caps=False,source_worktree_clean=True),source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(BASE.iterdir()) if p.is_file() and p.name!='model.json'})
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
