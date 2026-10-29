import hashlib,json,pathlib,re,subprocess,sys
W=pathlib.Path('/srv/opentallas-scratch2/claude/wt/codex-s81-frame-sub-1028');R=pathlib.Path('/srv/opentallas-scratch2/claude/codex-tok-s81-1028')
sys.path[:0]=[str(W/'tools/die_plan'),str(W/'tools/s81_dv')]
import bind_elab as E
import bind as B
import frame_bound_images as F
ab=json.loads((W/'physical/die_plan/s81/bind/asbuilt_b178_coll_s13pfunc.json').read_text());records=[]
for kind,frame in [('col_h10_x','u_f_0L01'),('col_h9_x','u_f_0L02'),('col_h9_nx','u_f_0L03')]:
 master=kind.replace('_x','_l4_lp_asb_x').replace('_nx','_l4_lp_asb_nx')
 # construct explicitly to avoid replacing the x inside an already expanded name
 base,var=kind.rsplit('_',1);master=base+'_l4_lp_asb_'+var
 js=json.loads((R/f'fs_work/{kind}/{master}.json').read_text());f=E.flatten(js,master);defaults={}
 for c in f.cells:
  c.path=frame+'.'+c.path
  defaults[(c.ytype,c.module)]={k:E._pval(v)[0]for k,v in js['modules'].get(c.ytype,{}).get('parameter_default_values',{}).items()}
 audit=B.instance_path_params(f.cells,defaults,ab['instance_path_params'])
 v=pathlib.Path('/srv/opentallas-scratch2/claude/tok17-gb/slice/vec')/frame
 meta=json.loads((v/'meta.json').read_text());material={p.name:p.read_text()for p in v.glob(frame+'_*.viamap.hex')}
 out=F.alias_material(material,master,frame,meta['pairs'],audit,W)
 assert all(out[k]==value for k,value in material.items())
 assert len(out)==2*len(material),(master,len(out),len(material))
 bad=[dict(row)for row in audit]
 q=next(row for row in bad if row['module']=='ot_v41_rom_elem_q_qxpq_w10' and row['inst'].endswith('.u_e'+str(meta['pairs'][0])))
 q['value']='""'
 try:F.alias_material(material,master,frame,meta['pairs'],bad,W)
 except ValueError as e:assert 'empty or wrong' in str(e)
 else:raise AssertionError('production bound material accepted empty native QX selector')
 rec=dict(master=master,frame=frame,active_pairs=meta['pairs'],original_images=len(material),bound_aliases=len(out)-len(material),original_bytes_unchanged=True,empty_selector_control='CAUGHT',full_frame_qualified=False)
 records.append(rec);print(rec,flush=True)
(R/'bound_material_check.json').write_text(json.dumps(dict(source_commit=subprocess.check_output(['git','-C',str(W),'rev-parse','HEAD'],text=True).strip(),scope='production image-material emitter invoked on three actual frame source-selector audits and real L0 checkpoint files; current bind/provider qualification separate',frames=records),indent=1)+'\n')
