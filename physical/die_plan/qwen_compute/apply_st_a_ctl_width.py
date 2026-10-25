"""Carry every bit of the canonical station-to-controller word, after param_regen.

The historical receipt used267 bits; the fresh source receipt verifies268.
These twelve lanes are direct abutments, so the correction adds one boundary
bit on each side, with no feedthrough stage or schedule-cycle change.
"""
import json
from pathlib import Path

RECEIPT = Path(__file__).with_name('inputs')/'st_a_ctl_width_1309.json'
LANES = {f'sl_{side}{i}_st_a__x_st_a_ctl' for side in 'EW' for i in range(6)}


def apply(raw):
    if raw.get('die',{}).get('name')!='qwen_compute':raise ValueError('width correction is QC-only')
    proof=json.loads(RECEIPT.read_text())
    if proof.get('verdict')!='POST_PARAM_REGEN_PASS' or set(proof.get('lanes',[]))!=LANES:
        raise ValueError('station/controller width correction requires its exact post-param-regeneration receipt')
    if (proof.get('old_width'),proof.get('new_width'))!=(267,268):raise ValueError('unexpected width receipt')
    ports={p['id']:p for p in raw['ports']};parts={p['name']:p for p in raw['partitions']}
    found=set();busdefs=set();changed=0
    for lane in raw['lanes']:
        if lane['id'] not in LANES:continue
        found.add(lane['id'])
        if len(lane['ports'])!=1:raise ValueError(f"{lane['id']}: no longer a direct lane; re-plan required")
        port=ports[lane['ports'][0]]
        if port['width'] not in (267,268):raise ValueError(f"{lane['id']}: stale width {port['width']}")
        changed+=int(port['width']==267);port['width']=268
        for end in ('src','dst'):
            ep=port[end];tn=parts[ep['part']]['type'];t=raw['partition_types'][tn]
            buses=[b for b in t.get('buses',[]) if b['name']==ep['bus']]
            if len(buses)!=1 or buses[0]['width'] not in (267,268):
                raise ValueError(f"{lane['id']}: actual bus {tn}.{ep['bus']} is not the proven direct endpoint")
            buses[0]['width']=268;busdefs.add((tn,ep['bus']))
    if found!=LANES:raise ValueError(f'missing scoped width lanes: {sorted(LANES-found)}')
    return dict(changed_lanes=changed,bus_definitions=len(busdefs),added_boundary_flops=changed*2,data_cycles_added=0)
