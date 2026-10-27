#!/usr/bin/env python3
"""Current head source-composition model; emit real provider frontier, never stubs.
The canonical plan is preserved. A source frontier is not an asbuilt manifest.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def model(plan_path):
    plan = json.loads(plan_path.read_text())
    counts = collections.Counter(p['type'] for p in plan['partitions'])
    # Only real provider sources. Partition wrappers belong to gen_rtl; a missing
    # wrapper name alone must not be mistaken for a missing logical component.
    providers = {}
    for path in sorted((ROOT / 'rtl/dsrom_sys/s81_head').glob('*.sv')):
        import re
        for name in re.findall(r'^\s*module\s+(\w+)', path.read_text(), re.M):
            providers[name] = str(path.relative_to(ROOT))
    rows = []
    for name, typ in plan['partition_types'].items():
        leaves = []
        for leaf in typ.get('contents', []):
            mod = leaf['module']
            source = providers.get(mod)
            # The actual PHY source has explicit PMA ports; binding must expose
            # them, never fabricate pads or replace st with constant status.
            if mod == 'ot_pdie_serdes':
                source = 'rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv'
                if not (ROOT / source).exists():
                    source = None
            leaves.append(dict(inst=leaf['inst'], module=mod, source=source,
                               params=leaf.get('params', {}),
                               bind=leaf.get('bind', {})))
        rows.append(dict(type=name, module=typ['module'], replicas=counts[name],
                         buses=[dict(name=b['name'],width=b['width'],direction=b['dir'])
                                for b in typ.get('buses',[])], leaves=leaves))
    return dict(schema='opentallas.s81.head-source-model.v1',
        status='COMPONENT FRONTIER; not whole-head asbuilt; G5 remains open',
        plan=str(plan_path.relative_to(ROOT)),plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        head_dies=4,hbm=0,partitions=len(plan['partitions']),partition_types=len(rows),
        parts=rows,
        xstore=dict(provider='rtl/dsrom_sys/s81_head/ot_s81hd_xstore_replay.sv',
                    role='concrete ctl subcomponent; no host decode or whole-ctl provider',
                    payload_bits=81920,stage_load_words=160,stage_word_bits=512, stage_ring_load_bits=1024, stage_ring_load_words=80,
                    banks=[dict(name='A',rows=256,bits=256),dict(name='B',rows=64,bits=256)],
                    local_load_layout='A consecutive low256/high256 halves, then B; explicit candidate ABI',
                    output='xa=A[m%256],xb=B[m%64] at G+5+m',
                    cycles='8192+7*SK; SK11=8269',
                    write_bits_per_cycle=512,read_bits_per_cycle=512,
                    data_reset=False,physical_storage_mapping='unmapped; no SRAM timing/area claim',
                    actual_source_witness='rtl/dsrom_sys/s81_head/test/tb_s81hd_mini.sv: loop ma[m%256]/mb[m%64]',
                    fullhead_issue_authority='ot_s81hd_static_issue fixed CSR9/10 dates; production BOOT/START/issue/merge calendar remains compiler work'),
        blockers=[
          'Canonical plan still awaits the one combined HEAD infra/source delta; head_control_plan_delta and head_host_plan_delta compose real ctl/HOST/LEP/mesh providers, strict leaf/module candidate checks reach zero missing/unresolved',
          'Production HBC/START/CSR9-10 dates need phase-aware compilation from actual safe8/HOST276 path; TEST fixtures are not production dates',
          'Current four-head Markov images/shared embedding/native DHSTEP-ROWS producer and master-plan capacity remain open; real full-shape and native/static K256 RTL exists (head_mtp_source_census.py)',
          'Candidate controller AR and five-step MTP ring protocol components pass exact payload/negative-control gates; synthetic DHRES fixtures do not qualify Markov numerics or whole-head G5',
          'Current geometry/PG/clock/reset kits and die real-view timing remain open; no source candidate inherits old physical views',
          'Physical SerDes PMA boundary must remain explicit and status live'],
        rankmerge=dict(provider="rtl/dsrom_sys/s81_head/ot_s81hd_rank_merge_hsf0.sv",
                       role="exact extracted real controller mechanism; transport independent",
                       input="own81-bit BEST and6x553-bit HSF0 peer frames(two copies/peer)",
                       live_record="position21,user10,bits32,row17,valid1",
                       held_payload_bits=7*96,
                       merge="hold until all7records; compare4ranks in2registered levels",
                       checks="identity equality,duplicate copies,NaN,overwrite",
                       added_cycles=0,
                       physical_mapping="unmeasured; current mesh64 codec remains external"),
        transport=dict(best64=dict(provider="rtl/dsrom_sys/s81_head/ot_s81hd_best64.sv", live_source_bits=97, lane_bits=64, beats=2, extra_vs_one_beat=1),
                       host276=dict(provider="rtl/dsrom_sys/s81_head/ot_s81hd_host276.sv", source_bits=553, lane_bits=276, beats=3, extra_vs_one_beat=2),
                       gate="results/arch/s81_head_source_1025/transport_1026/gate.json", integration="pending actual controller/endpoints and compiled dates"),
        row_mapping=dict(tool="tools/s81_head/head_row_map.py", active_bundles=[253,253,252,252],
                         rank_bases=[0,32384,64768,97024], slots_per_rank=264,
                         local_row0="128*slot for active slots", weight_row0="rank_base+local_row0",
                         dark="TEN0; no content image", added_cycles=0),
        available_library=dict(
          ar_result_model="tools/s81_head/ar_result_model.json",
          lep_provider="rtl/dsrom_sys/s81_head/ot_s81hd_lep0N_core.sv",
          lep_sources="results/arch/head_lep_source_1026/sources.json",
          lep_plan_helper="tools/s81_head/head_lep_plan_delta.py",
          lep_native_ages=dict(ro_mu_face=1,lane_K_to_N=3,lane_N_to_K=3,NR_extra=0),
          status="components only; no canonical plan/whole-head binding/physical adoption"),
        historical_controller_component="results/arch/s81_head_source_1025/hsf0_component.json",
        wholehead_implementation_allowed=False,
        allowance_note='Canonical plan adoption/native image+date composition is pending; real provider candidates now exist, so this is not a missing-RTL assertion')

if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan',type=Path,default=ROOT/'physical/die_plan/s81_head/die_plan.json')
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args(); a.out.parent.mkdir(parents=True,exist_ok=True)
    data=model(a.plan.resolve()); a.out.write_text(json.dumps(data,indent=2)+'\n')
    print(f"{data['partitions']} parts/{data['partition_types']} types; concrete xstore; whole-head G5 OPEN")
