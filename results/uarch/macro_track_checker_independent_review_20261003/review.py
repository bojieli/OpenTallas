#!/usr/bin/env python3
"""Cold checker review; expected gaps are evidence, not fixes/admission."""
import argparse,contextlib,hashlib,importlib.util,io,json,math,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent

def require(c,m):
 if not c:raise ValueError(m)
def canonical(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def outputs():
 spec=importlib.util.spec_from_file_location('reviewed_checker',ROOT/'tools/check_macro_track_alignment.py');C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
 paths=['tools/check_macro_track_alignment.py','tools/test_check_macro_track_alignment.py','results/uarch/dsrom_noECC_production_context_20261002/inputs/make_tracks.tcl']
 lefs=sorted(ROOT.glob('physical/asap7_memory_macros/*/*.lef'));paths += [str(p.relative_to(ROOT)) for p in lefs]
 pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
 tracks=C.parse_tracks(str(ROOT/paths[2]));tracks.pop('Pad',None);require(tracks==C.ASAP7_TRACKS_NM,'actual archived ORFS tracks match all embedded offsets/pitches')
 catalog=C.run([str(p) for p in lefs],tracks,C.ASAP7_LAYERS)
 reference=[]
 for name,expected in [('ot_sram_1r1w_128x256_m1_r2c2',24),('ot_sram_1r1w_1024x256_m2_r2c2',18)]:
  r=next(m for m in catalog['macros'] if m['macro']==name);m=C.parse_lef((ROOT/r['lef']).read_text())[0];rule=r['summary']['M4']['origin_rule_mod_track_nm']['MX'];require(rule==[expected],'actual RF/scratch MX residue')
  good=C.check_placement(m,'MX',0,expected)['layers']['M4'];bad=C.check_placement(m,'MX',0,0)['layers']['M4'];require(good['offtrack']==0 and bad['offtrack']>0,'actual placement diagnostic distinguishes valid offset')
  reference.append(dict(macro=name,MX_required_y_mod48_nm=expected,legal_offset_check=good,origin0_check=bad))
 def macro(rects,sym=('X','Y'),obs=None):return dict(name='corner',W=10000,H=20520,symmetry=list(sym),pins=rects,obs=obs or {},**{'class':'BLOCK'})
 def pin(name,rects):return dict(name=name,use='SIGNAL',rects=rects)
 def audit(m):return C.audit_macro(m,tracks,C.ASAP7_LAYERS)
 # Multiple horizontal pin layers each have legal residues and row intersections,
 # but there is no ONE y origin satisfying both:0mod48 vs2mod64.
 mixed=macro([pin('a',[('M4',(0,0,24,24))]),pin('b',[('M6',(100,62,132,94))])]);mr=audit(mixed)
 for l in ['M4','M6']:require(mr['orientations'][l]['R0']['uniform'] and mr['orientations'][l]['R0']['joint_with_row']['legal_origins_mod_joint_nm'],'individual legal layers/sites')
 require(not any(y%48==0 and y%64==2 for y in range(math.lcm(48,64))),'actual common preferred-y lattice impossible')
 # Pin2nd rect centre differs6nm; tool requires BOTHrectangles, not a pin-level
 # bounding-centre/alternative-PORT interpretation.
 multi=macro([pin('a',[('M4',(0,0,24,24)),('M4',(0,6,24,30))])]);multir=audit(multi);require(not multir['orientations']['M4']['R0']['uniform'],'multi-rect conjunctive diagnostic')
 require(C.allowed_orients(['R90'])==['R0','R90','R270'],'rotation group closure gap reproduced')
 require(C.joint_grid({0},48,270,9)['legal_origins_mod_joint_nm']==[],'nonzero site origin changes legal joint lattice')
 nonzero=[(9,36,24,48)];P,T=C.track_residues(nonzero,'y');require(C.legal_origins([(0,24)],P,T,'center')=={12},'nonzero track offset supported')
 actual_rotation_gaps=[r['macro'] for r in catalog['macros'] if any(not v['uniform'] for per in r['orientations'].values() for o,v in per.items() if o in C.ROT_SET)]
 with tempfile.TemporaryDirectory(prefix='macro-track-review-') as td:
  td=Path(td);sample='MACRO empty\n CLASS BLOCK ;\n SIZE 10 BY 10 ;\n PIN a\n USE SIGNAL ;\n PORT\n LAYER M4 ;\n POLYGON 0 0 0.024 0 0.024 0.024 0 0.024 ;\n END\n END a\nEND empty\n'
  (td/'polygon.lef').write_text(sample);(td/'empty_tracks.tcl').write_text('# no parsed track statements\n')
  with contextlib.redirect_stdout(io.StringIO()):
   polygon_rc=C.main([str(td/'polygon.lef'),'--fail-on-offtrack']);unknown_rc=C.main([str(lefs[0]),'--tracks',str(td/'empty_tracks.tcl'),'--fail-on-offtrack'])
  require(polygon_rc==0 and unknown_rc==0,'empty/unsupported geometry/track fail-open witnesses')
 result=dict(verdict='PASS_NARROW_CATALOG_DIAGNOSTIC_WITH_GUARD_SCOPE_GAPS',reviewed_commit='9b7b120388ff0c8888f69bcf38211865c7cee8e7',source_pins=pins,actual_catalog_macros=len(catalog['macros']),ORFS_source_scope='committed archived make_tracks.tcl, all embedded entries byte-content parsed equal; no live ODB or live P&R edited',actual_RF_scratch=reference,
  CLI_contract='rc1 only if a processed layer has no legal origin for an audited R0/MX/MY/R180 orientation. rc0 is NOT actual-placement approval, joint row/site approval, routing/via/DRC/SSFF closure.',
  findings=[dict(id='NO_PLACEMENT_GATE',severity='SCOPE',proof='CLI takes abstracts, no DEF/ODB instances. check_placement exists as helper and detects actual origin0 failures, but CLI does not apply it to submitted placements.'),
  dict(id='JOINT_MULTILAYER_LATTICE',severity='PRELAUNCH_GUARD_GAP',proof='M4 y0mod48 andM6 y2mod64 each legal on row270 but no common y. audit/CLI test layers independently; likewise empty joint row/site lists do not drive failure.',witness=mr),
  dict(id='EMPTY_UNSUPPORTED_INPUT_FAILOPEN',severity='PRELAUNCH_GUARD_GAP',polygon_no_RECT_rc=polygon_rc,empty_parsed_tracks_rc=unknown_rc,proof='Signal polygons/unknown track-layer/no parsed tracks can yield no audited summary and rc0. Missing input coverage must fail closed before general guard use.'),
  dict(id='ROTATION_SCOPE',severity='FOLLOWUP',actual_rotated_no_origin_macros=actual_rotation_gaps,proof='Audit computes rotated orientations but CLI no_legal_origin summary onlychecks4 mirror orientations. allowed_orients also omits R180 forR90-only, andMY/R180 forX+R90 despite composition closure.'),
  dict(id='MULTIRECT_PIN_SEMANTICS',severity='FOLLOWUP',proof='All rectangles tested conjunctively at individual centres. Counts are rect counts even labelled pins; no LEF PORT grouping/union bounding-centre/via-access interpretation. Current catalog single-rect signal scope avoids this ambiguity.',witness=multir),
  dict(id='NONZERO_GRID_ORIGIN',severity='FOLLOWUP',proof='Nonzero track offsets are correctly parsed/tested. joint_grid accepts site_origin but audit hardcodes0 and CLI has no actual row/site-origin binding. LEF ORIGIN/UNITS/grid and alternative track Tcl formats unsupported.'),
  dict(id='ACCESS_GEOMETRY_NOT_DRC',severity='SCOPE',proof='Adjacent layer cross checks/OBS cover tests do not size real via cuts/enclosures or handle partial OBS perpin, EOL/parallel-run rules, union area repair, neighbours, PDN/placement blockage. Pin-centre screen is not full access qualification.')],
  use_as_mandatory_prelaunch='Usable as a mandatory diagnostic for explicitly pinned known single-RECT catalog/current R0/MX/MY/R180 scope, alongside actual-instance checks. Not a sole/general placement admission guard. Failclosed input coverage, simultaneous same-axis layer+row/site intersection, and allowed/selected orientation checks required for stronger prelaunch meaning.',
  minimal_owner_followup=['fail closed on missing abstract/signal RECT/parsed tracks/unknown layer; declare unsupported LEF','validate combined preferred-axis residues and actual site/row origin, at least selected orientation','wire check_placement to frozen actual DEF/ODB instance coordinates before treating it as placement gate'],
  engine_or_physical_adoption=False,no_live_PnR_edits=True,no_owner_tool_edits=True)
 return {'review.json':canonical(result),'cold-catalog.json':canonical(catalog)}
def main():
 p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
 for name,raw in outputs().items():
  if a.verify:require((BASE/name).read_bytes()==raw,'byte exact '+name)
  else:require(a.output is not None,'explicit output');a.output.mkdir(parents=True,exist_ok=True);require(not (a.output/name).exists(),'fresh output');(a.output/name).write_bytes(raw)
 print('PASS independent source/corner witnesses; general prelaunch/actual-placement admission NOT established')
if __name__=='__main__':main()
