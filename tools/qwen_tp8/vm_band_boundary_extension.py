#!/usr/bin/env python3
"""Necessary geometry bounds for adding two enabled stages at the band seam.
No placement, timing qualification, or production latency authorization is implied.
"""
import collections,gzip,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    cf=ROOT/'results/arch/qwen_tp8_1012/vm_band_composition_codex.json'
    pf=ROOT/'results/arch/qwen_tp8_1012/vm_leaf_plan_claude.json'
    rf=ROOT/'results/arch/qwen_tp8_1012/vm_band_paths_codex.json'
    c=json.loads(cf.read_text());p=json.loads(pf.read_text());r=json.loads(rf.read_text())
    assert r['source_sha256']==sha(cf)
    df=ROOT/r['all_bit_details']['path'];assert sha(df)==r['all_bit_details']['sha256']
    edges=[e for e in json.load(gzip.open(df,'rt'))['edges'] if e['kind']=='regional_boundary_lower_bound']
    occupied={(ch['bay'],ch.get('physical_slot',ch['slot'])) for ch in c['children'] if 'bay' in ch}
    slots=[dict(bay=b['n'],slot=s,at=[b['x']+s*21.6,b['y']],outline_um=[17.28,97.2])
           for b in p['x_relay_bays'] if b.get('padrow') for s in range(6) if (b['n'],s)not in occupied]
    assert len(slots)==114 and len(edges)==32768
    lanes=collections.defaultdict(list)
    for e in edges:lanes[e['lane']].append(e)
    def dist(a,slot,slack):
        x,y=slot['at'];w,h=slot['outline_um']
        # Permit arbitrary pins anywhere in an enlarged rectangle; this is
        # strictly more permissive than a real assigned d/q pin and pair reach.
        return max(x-slack-a[0],0,a[0]-x-w-slack)+max(y-slack-a[1],0,a[1]-y-h-slack)
    scenarios=[]
    for slack in (0,2.16):
        bad=[];single=[]
        for e in edges:
            nearest=min(dist(e['A'],s,slack) for s in slots)
            if nearest>500:bad.append(dict(lane=e['lane'],bit=e['bit'],nearest_slot_rectangle_um=round(nearest,4),launch=e['A']))
        for lane,es in lanes.items():
            if not any(all(dist(e['A'],s,slack)<=500 and dist(e['B'],s,slack)<=500 for e in es) for s in slots):single.append(lane)
        scenarios.append(dict(rectangle_expansion_um=slack,unreachable_launch_bits=len(bad),
            unreachable_launch_lanes=len({e['lane'] for e in bad}),unreachable_launch_lane_names=sorted({e['lane'] for e in bad}),unreachable_launch_bits_detail=bad,
            no_single_P2_slot_lanes=len(single),no_single_P2_slot_lane_names=single,
            max_nearest_rectangle_um=round(max(min(dist(e['A'],s,slack) for s in slots) for e in edges),4)))
    rec=dict(schema='opentallas.qwen.vm-band-boundary-extension-bound.v1',qualification=False,
        status='FAIL_FIXED_REGIONAL_ENDPOINTS_AND_BAND_SPARE_SLOTS',
        inputs={str(f.relative_to(ROOT)):sha(f) for f in (cf,pf,rf,df)},
        original_XPR=12,proposed_XPR=14,latency_adoption='not authorized or production measured; original unit price unchanged',
        lanes=len(lanes),bits=len(edges),spare_whole_slots=slots,
        raw_capacity=dict(P2_width_bits=480,P2_enabled_stages=2,P2_tile_lower_bound=math.ceil(len(edges)/480),
            remaining_slots_after_raw_minimum=114-math.ceil(len(edges)/480),
            one_stage_W512_two_level_tile_lower_bound=2*math.ceil(len(edges)/512),
            exclusions='clock/ME/control/gather tiles, pin reach, occupancy and route cuts not included'),
        necessary_geometry_bound=dict(reach_um=500,scenarios=scenarios,
            interpretation='Unreachable launch bits cannot reach any added band spare-slot tile even with arbitrary ideal pins and relaxed rectangles. Real pair-specific reach is <=500. Adding more stages only inside those slots cannot fix the first hop.'),
        next_requirement='joint regional final-relay and band first-stage placement/pin contract, or changed physical slot contract; then all-bit pair/cut re-audit and true latency/native-cost bench')
    out=ROOT/'results/arch/qwen_tp8_1012/vm_band_boundary_extension_codex.json'
    out.write_text(json.dumps(rec,indent=1)+'\n')
    print(json.dumps(dict(raw_capacity=rec['raw_capacity'],scenarios=[{k:v for k,v in s.items() if not isinstance(v,list)} for s in scenarios]),indent=1))
if __name__=='__main__':main()
