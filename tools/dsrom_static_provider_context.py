"""One source-sized static-provider/issuer contextual route admission, not die closure."""
import hashlib,json
from pathlib import Path
import dsrom_s81_fulldie as S
from dsrom_noECC_local_context_cuts import pdn
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/rtl/dsrom_recovery_20261004/static_provider_context'
def build():
 c=S.build()['hub']['capture']; parent=[c.x,c.y,c.x+c.w,c.y+c.h]
 issuer=[15186.96,13476.24,15251.76,13484.88]
 provider=[15256.08,13476.24,15385.68,13562.64]
 corridor=[15186.96,13563.072,15385.68,13579.464]
 boxes=[issuer,provider,corridor]
 for r in boxes:
  assert parent[0]<=r[0]<r[2]<=parent[2] and parent[1]<=r[1]<r[3]<=parent[3]
 for i,a in enumerate(boxes):
  for b in boxes[i+1:]:assert min(a[2],b[2])<=max(a[0],b[0]) or min(a[3],b[3])<=max(a[1],b[1])
 gp=ROOT/'results/uarch/dsrom_noECC_complete_element_20261002/inputs/grid.json'
 grid=json.loads(gp.read_text());g=next(x for x in grid['grids'] if x['layer']=='M6')
 start,_,pitch=g['Y'][0]
 # Local context origin is sp_capture; use actual platform M6 tracks.
 lo=round((corridor[1]-parent[1])*1000);hi=round((corridor[3]-parent[1])*1000)
 ys=[y for y in range(start,round(c.h*1000),pitch) if lo<=y<hi]
 stripes=pdn(round(c.w*1000),round(c.h*1000))
 power=[r['bbox_DBU'] for r in stripes if r['layer']=='M6']
 # 96nm source power spacing + 12nm half signal width.
 usable=[y for y in ys if not any(r[1]-108<=y<=r[3]+108 for r in power)]
 assert len(usable)>=200
 sources=['rtl/v41die/ot_v41_spine_pq_w17w10.sv','rtl/hdc/ot_hdc_delay.sv',
          'tools/dsrom_s81_fulldie.py','tools/dsrom_noECC_local_context_cuts.py',str(gp.relative_to(ROOT))]
 return dict(schema='opentallas.static-provider-context.v1',parent_bbox_um=parent,
  provider_source_commit='551aaa7e7edc660eb3c0f3c924b733d7378b6f1b',
  source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},
  issuer_bbox_um=issuer,provider_bbox_um=provider,local_signal_corridor_bbox_um=corridor,
  contained=True,disjoint_cell_and_corridor_reservations=True,
  issuer_provider_gross_um2=11757.312,corridor_extra_reserved_um2=(corridor[2]-corridor[0])*(corridor[3]-corridor[1]),
  corridor_layer='M6 horizontal / M5 vertical access over standard-cell region, no hard macro OBS',
  tracks_required=200,M6_raw_tracks=len(ys),M6_tracks_after_source_PG_spacing=len(usable),
  PDN_source='Existing M2 followpins + M5/M6/M7 source stripes from dsrom_noECC_local_context_cuts.pdn; construct same-net via landings outside signal tracks, route validates connectivity.',
  clock=dict(domain='stream_1p2',period_ns=.833333,setup_uncertainty_ns=.060,hold_uncertainty_ns=.025,
   issuer_sinks=47,provider_sinks=0,provider_resets=0,
   context_phase_launch_FF=10,context_phase_capture_FF=320,context_stream_capture_FF=48,
   conservative_total_context_clock_sinks=425,fanout8_clock_buffer_allowance=61,
   context_launch_capture_FF_floor_um2=378*.2916,clock_buffer_floor_um2=61*.10206,
   allocation='Within issuer50pct spare198.60876um2: conservative additional context FF/clock floor116.45046um2 leaves82.15830um2 for capture mux/remaining construction; actual mapping must fit or reject. Full four PHROM capture banks retained.',
   policy='ONE common context clock; actual 47FF issuer/active_addr plus all FOUR existing s_pw/s_rs banks and sw captures. Phase i_ph requires held registered launch context, not zero-delay input.',
   trunk='M8 clock with adjacent shields; separate from M6 data corridor. CTS includes phase-launch and all source capture sinks.',
   whole_parent_clock_bound=False),
  context=dict(top='stage37 or stage38 static provider + source issuer and existing phase/stream captures',
   endpoints=['registered i_ph[9:0] -> 2x64 PHROM -> s_pw[63:0]/s_rs[15:0]',
    'active_addr[13:0] -> 48bit STREAM -> sw[47:0]'],
   baseline='Same constant provider on original legacy_st_a combinational source path; no substitution of address-register path for baseline.',
   additional_provider_cycles=0,per_token_programming_cycles=0,II=1,
   wire_max_manhattan_um=(provider[2]-issuer[0])+(corridor[3]-issuer[1]),
   acceptance='Full actual decoder+buffer+wire SS setup>=0 with60ps; FF hold>=0 with25ps. No IO0 shortcut: registered phase/stream launch and actual captures included.',
   source_initialization='Compile-time literal image, no runtime write or table reset; original control reset/valid qualification retained.',
   placement='Provider and issuer cells restricted to separate named boxes at <=50%; M5 access routes and real vias must avoid source PG, no macro/old-cell credit.',
   routing_scope='ONE minimum provider/issuer/source-capture component, not sp_capture remainder or full S81'),
  component_contextual_build_admitted=True,whole_parent_adopted=False,physical_closes=False)
if __name__=='__main__':
 OUT.mkdir(parents=True,exist_ok=True)
 m=build();(OUT/'model.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'tracks':m['M6_tracks_after_source_PG_spacing'],'component_contextual_build_admitted':True}))
