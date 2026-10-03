#!/usr/bin/env python3
"""One collector reconstruction aligned to the selected KV7 channel edges.
Preserve native failures, source counts and selected map; no hardware build.
"""
import gzip
import json
import shutil
from pathlib import Path
import qwen_rom_native_local_release as J
R=J.R;M=J.M;G=J.G;A=J.A
OUT=Path('results/uarch/qwen_rom_channel_aligned_context_20261002')


def generate():
    root=R.ROOT/OUT
    if (root/'model-r2.json').exists():raise ValueError('preserve aligned model')
    #A new region boundary at both sides of the named upper-metal channel.
    #Local clock/reset branches stay inside each region; only collector
    #trunks cross its cuts. Source FF/macro inventory is unchanged.
    G.BOUNDS=([0.,130.464,227.232,357.696],[0.,393.12,489.888,700.,796.768,1360.8])
    #The historical helper deliberately enumerates only three regions. Bind
    #the extension's exact region function rather than compressing high FFs
    #into the old third region after adding channel boundaries.
    def channel_region(pos):
        return tuple(next(i for i in range(len(bounds)-1)
            if v<bounds[i+1] or i==len(bounds)-2) for v,bounds in zip(pos,G.BOUNDS))
    G.region=channel_region
    native_input=OUT/'inputs/native-clock';(R.ROOT/native_input/'inputs').mkdir(parents=True,exist_ok=True)
    shutil.copy2(R.ROOT/A.OUT/'inputs/capture-connectivity.json',R.ROOT/native_input/'inputs/capture-connectivity.json')
    A.OUT=native_input
    print('construct one source-matched clock tree at actual KV7 band cuts',flush=True)
    A.generate()
    J.OUT=OUT
    print('construct local groups, raw/reset intervals and startupACK',flush=True)
    J.generate(1)
    #The source phase correction uses local groups. ACK receiver moves to an
    #endpoint-matched leaf in r2 and receives its own independent rawRST check.
    record=J.record
    def local_groups(name):
        value=record(name)
        if name=='model-r1.json':
            value['timing']['ss']['raw_reset_checks']=[q for q in value['timing']['ss']['raw_reset_checks'] if q['instance'].startswith('native_release_')]
        return value
    J.record=local_groups
    J.generate(2)
    model=record('model-r2.json');model['schema']='QWEN_KV7_CHANNEL_ALIGNED_LOCAL_COLLECTOR_R2'
    model['channel_band_local_y_um']=[700,796.768]
    model['source_counts_not_new_mapped_counts']=True
    model['channel_parent_model_sha256']=R.sha(Path('results/uarch/qwen_rom_kv_channel_shoreline_20261002/model-r5.json'))
    model['full_slot_routing_and_pin_landing_proven']=False
    #Separate final coherent composition from both immutable constructor rows.
    M.write(root/'composition-r1.json',model)
    print(json.dumps(dict(clock_and_reset_ACK_cuts=model['cuts'],area_um2=model['complete_reserved_cell_area_um2'],
        corner_failures={c:dict(raw_FF=t['raw_reset_failures'],controlled=t['controlled_reset_failures'],skew=t['nominal_same_source_clock_scenarios']) for c,t in model['timing'].items()}),indent=2),flush=True)


if __name__=='__main__':generate()
