#!/usr/bin/env python3
"""Inventory legal spare whole slots; never assign absent boundary/station pins."""
import hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
A=ROOT/'results/arch/qwen_tp8_1012'

def main():
    cp=A/'vm_band_composition_codex.json';bp=A/'vm_leaf_plan_claude.json'
    comp=json.loads(cp.read_text());leaf=json.loads(bp.read_text())
    occ={(c['bay'],c.get('physical_slot',c['slot'])) for c in comp['children'] if 'bay' in c}
    x0,y0=comp['origin_um'];w,h=comp['outline_um'];pool=[]
    for b in leaf['x_relay_bays']:
      if not b.get('padrow'):continue
      for s in range(6):
        if (b['n'],s) in occ:continue
        x=b['x']+s*21.6;y=b['y']
        assert x>=x0 and y>=y0 and x+17.28<=x0+w+1e-6 and y+97.2<=y0+h+1e-6
        for c in comp['children']:
          cx=x0+c['at'][0];cy=y0+c['at'][1];cw,ch=c['outline_um']
          assert not (x<cx+cw-1e-6 and cx<x+17.28-1e-6 and y<cy+ch-1e-6 and cy<y+97.2-1e-6),(b['n'],s,c['inst'])
        pool.append(dict(bay=b['n'],physical_slot=s,at_um=[x,y],outline_um=[17.28,97.2]))
    assert len(occ)==270 and len(pool)==114
    masters=[]
    for name,width,en,count in [('pc',20,1,37),('lc',28,1,74),('me',1,0,5)]:
      base=ROOT/f'physical/ref_tile/qfd_vm_fan_{name}'
      spec=json.loads((base/'spec.json').read_text());ins=json.loads((base/'views/ot_qfd_vm_fan_t/insertion.json').read_text())
      assert spec['params']==dict(W=width,EN=en,MEREG=1)
      masters.append(dict(master=f'qfd_vm_fan_{name}',instances=count,params=spec['params'],outline=spec['outline'],view=str((base/'views/ot_qfd_vm_fan_t').relative_to(ROOT)),insertion=ins))
    rec=dict(schema='opentallas.qwen.vm-band-controls-plan.v1',status='LOGICAL_TOPOLOGY_ONLY_NO_PHYSICAL_ASSIGNMENT',origin_um=comp['origin_um'],outline_um=comp['outline_um'],
      source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (cp,bp)},preserved_existing_whole_tiles=len(occ),preserved_source_columns=32,preserved_existing_lanes=4096,
      unoccupied_whole_pad_slots=pool,available_slots=len(pool),logical_control_tiles=116,co_pack_vertical_capacity_per_slot=5,minimum_slots_by_count=24,
      logical_tree=dict(pc_levels=[1,4,32],lc_payload_levels=[1,4,32],lc_tag_levels=[1,4,32],me_levels=[1,4],enabled_edges=3,free_me_edges=2,own_child_clock_entries=116,common_parent_clock_tree=False),masters=masters,
      geometry_warning='116 fans can co-pack five17.28um-high fans per97.2um-high whole spare slot; the resulting minimum24slots proves only a footprint count and legal spare-slot inventory. A central source to a band end has about2419um span, at least5<=500um hops even with ideal pins; 3control stages cannot establish a full-band reach proof. Do not instantiate this topology physically until redesigned for real boundaries/stations.',
      requirements=['Die-assigned boundary/control/me source pins and32station coordinates with allowed scheduler early taps.','Balanced registered station chain/tree or multiple source entries, <=500um AND pair-specific o+s wirebudget at every actualpin.','Depth can grow7 or more; explicit source-root3enabled-edge tags and c_a/c_n/control consumer alignment must be reproved with scheduler changes.','ME source routing must be owned inside VM; free-running ME path depth and each fan MEREG must align payload capture under stalls.','Each of116logical child clocks delivered phi-R at its own entry; no parent CTS.','Use only spare whole padslots. Preserve existing270tile placements, fine offsets, permutations and4096lanes.','VM owns all inside distribution; no die signal/reset trunk over M1-M9blocked VM. Local PG M7; die PG M8/M9 .48um/net at9.091um pitch reserves10.56percent pending authority.'],
      previous_control_tree=leaf.get('control_trees'),physical_boundary_and_station_assignment='PENDING; no coordinates guessed',bench_record='results/rtl/qwen_tp8_vm_plane_20261013/vm_band_controls/record.json')
    (A/'vm_band_controls_plan_codex.json').write_text(json.dumps(rec,indent=2)+'\n')
    print('PASS sparewholepadslots=114 occupiedexistingtiles=270 logicalfans=116 unassignedphysicalentries=116')
if __name__=='__main__':main()
