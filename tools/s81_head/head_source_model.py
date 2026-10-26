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
                    payload_bits=81920,stage_load_words=160,stage_word_bits=512,
                    banks=[dict(name='A',rows=256,bits=256),dict(name='B',rows=64,bits=256)],
                    local_load_layout='A consecutive low256/high256 halves, then B; explicit candidate ABI',
                    output='xa=A[m%256],xb=B[m%64] at G+5+m',
                    cycles='8192+7*SK; SK11=8269',
                    write_bits_per_cycle=512,read_bits_per_cycle=512,
                    data_reset=False,physical_storage_mapping='unmapped; no SRAM timing/area claim',
                    actual_source_witness='rtl/dsrom_sys/s81_head/test/tb_s81hd_mini.sv: loop ma[m%256]/mb[m%64]',
                    fullhead_issue_authority='unresolved; consume compiled native/head START contract'),
        blockers=[
          'hd_ctl: real stage/context admission, x command origin, rank-argmax merge/token formation missing; xstore now implemented separately',
          'hd_mesh: historical real HSF0 BEST has81 live bits including user10+position21, so64-bit lane needs explicit multi-beat framing; safe8_ntf rx515 includes channel-board bit while plan carries514',
          'hd_host: real dsdv_hostb_stage_hbc1104-bit ring/context/status interface is not a drop-in276-bit endpoint; 553-bit record needs explicit N3 codec or279-bit N2 lane',
          'hd_lep0N: provider named dsdv_slice_lepw_mu.LP is nested historical source; exact current source extraction and input contracts required',
          'tile position ROW0/TEN must be mapped from current264-slot/253-active plan, not copied from old253-tile17-SerDes top',
          'physical SerDes PMA boundary must remain explicit and status live'],
        historical_controller_component="results/arch/s81_head_source_1025/hsf0_component.json",
        wholehead_implementation_allowed=False)

if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan',type=Path,default=ROOT/'physical/die_plan/s81_head/die_plan.json')
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args(); a.out.parent.mkdir(parents=True,exist_ok=True)
    data=model(a.plan.resolve()); a.out.write_text(json.dumps(data,indent=2)+'\n')
    print(f"{data['partitions']} parts/{data['partition_types']} types; concrete xstore; whole-head G5 OPEN")
