from pathlib import Path
import shutil,json,sys,re
r=Path(__file__).resolve().parent;sys.path.insert(0,'/srv/opentallas-scratch/claude/wt/codex-hbm-mesh-core-union-1131/tools/die_plan');import clock_routed as C
for form in ['route','fixed']:
 o=r/f'mesh_contact_{form}_r3';shutil.copytree(r/'mesh_contact_narrow_r2',o,dirs_exist_ok=True)
 s=(o/'pilot.def').read_text();s=s.replace('FIXED ( 255230 ', 'FIXED ( 255796 ');s=s.replace('FIXED ( 257036 3244320 )','FIXED ( '+('257076' if form=='route' else '257040')+' 3246480 )');(o/'pilot.def').write_text(s)
 t=(o/'mesh_contact_route.tcl').read_text();t=t.replace('$mesh clearSpecial','$mesh clearSpecial\nforeach it [$mesh getITerms] {$it clearSpecial}')
 if form=='fixed':
  cells={'M0_11':dict(x=256.23,y=3107.16,orient='R0',lib='BUFx24_ASAP7_75t_R'),'M0_12':dict(x=256.23,y=3372.57,orient='MX',lib='BUFx24_ASAP7_75t_R')}
  ys=sorted([3000,3103.92,3107.295,3246.48,3372.705,3376.08,3450]);edges=[[['M9',257.04,a],['M9',257.04,b]] for a,b in zip(ys,ys[1:])]
  for y in [3103.92,3376.08]:
   edges += [[['M8',220,y],['M8',257.04,y]],[['M8',257.04,y],['M8',300,y]],[['M8',257.04,y],['M9',257.04,y]]]
  graph=dict(edges=edges,vias=2,drivers=[dict(anchor=['M9',257.04,y],units=[n]) for n,y in [('M0_11',3107.295),('M0_12',3372.705)]],taps=[dict(port_node=['M9',257.04,3246.48],port='mesh_contact')])
  wire=dict(name='ck_mesh',explicit_mesh=True,ndr='4w',mesh_graph=graph)
  lines,record=C.routed_tcl([wire],cells,{'mesh_contact':dict(layer='M9',xy=[257.04,3246.48])},'BUFx24_ASAP7_75t_R','CONTACT')
  (o/'fixed_mesh.tcl').write_text('set blk [ord::get_db_block]\nset tech [ord::get_db_tech]\nforeach sw [[$blk findNet ck_mesh] getSWires] {odb::dbSWire_destroy $sw}\n'+'\n'.join(lines)+'\n')
  (o/'fixed_graph.json').write_text(json.dumps(dict(wire=wire,cells=cells,record=record),indent=2))
  t=t.replace('source /o/ndr.tcl','source /o/ndr.tcl\nsource /o/fixed_mesh.tcl')
  # Keep mesh own0.16NDR fromthe shared fixed encoder; the two input nets retain0.04.
  t=t.replace('foreach n [get_nets *] {assign_ndr','foreach n [get_nets {input0 input1}] {assign_ndr')
 (o/'mesh_contact_route.tcl').write_text(t)
 (o/'run.sh').write_text((o/'run.sh').read_text().replace('--memory=8g --memory-swap=8g','--memory=4g --memory-swap=4g'))
 j=json.load(open(o/'scope.json'));j.update(form=form,input_port_x_um=255.796,clock_contact_x_um=257.076 if form=='route' else 257.04)
 j['clock_contact_x_um']=257.076 if form=='route' else 257.04
 j['contact']=[j['clock_contact_x_um'],3246.48]
 j['scope']='ActualtwoY→commonphysicalmeshcontacts; routeformretainsunextractedSBoxesdiagnostic, fixedformsharedexplicit_clock_meshencoder materializesallgridmetal/vias/stairs asRCX-extractable regularFIXEDwire. Noaliases.'
 (o/'scope.json').write_text(json.dumps(j,indent=2))
