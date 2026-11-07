from pathlib import Path
import shutil,json,hashlib,re
root=Path('/srv/opentallas-scratch3/claude/codex-hbm-su-1107')
out=root/'kits'
srcs={
 'opsa_rest_vH2':Path('/srv/opentallas-scratch3/claude/hbm-hard-1/kits/ot_hgi_sfu_opsa_rest_vH1/ot_hgi_sfu_opsa_rest_907926fd338d'),
 'opsa_group0_vC':Path('/srv/opentallas-scratch3/claude/die-hbm-83-opsg/kits/ot_hgi_sfu_opsa_group0_vB/ot_hgi_sfu_opsa_group0_c7fe35538610')}
for name,src in srcs.items():
 dst=out/name
 assert not dst.exists(),str(dst)
 dst.mkdir(parents=True);(dst/.keep).touch()
 for p in src.iterdir():
  if p.name in ['run','lec','lec_async.runs','face_shell_work','__pycache__','signoff'] or p.name.startswith('FAIL') or p.name.startswith('lec_async.'):
   continue
  if p.is_dir():shutil.copytree(p,dst/p.name,symlinks=True)
  elif p.is_file():shutil.copy2(p,dst/p.name)
 manifest={'source':str(src),'form':name,'rtl_changes':[],'pin_cycles':{}}
 if name=='opsa_rest_vH2':
  rel='rtl/ot_hgi_sfu_opsa_rest__fshell.sv'
  shutil.copy2(root/'bench/reset1'/rel,dst/rel)
  manifest['rtl_changes']=['asynchronous assertion unchanged; align core reset release one edge after reset pin with added data hop']
  manifest['pin_cycles']={'data_control_vs_part27r_vD':1,'reset_release_vs_vH1':1,'reset_assert':0}
 else:
  p=dst/'macro_reg_guide.json'; d=json.loads(p.read_text())
  old=next(b for b in d['boxes'] if b['name']=='hub')
  remaining=[b for b in d['boxes'] if b['name']!='hub']
  stages=[('s1',['g_s1.'],[234.,70.,526.,108.]),('s2',['g_s2.'],[234.,126.,526.,164.]),('read',['g_hc.','g_lane[','q_out[','fq[','wcoll_q','hc['],[300.,108.,460.,126.])]
  for nm,pf,box in stages:remaining.append(dict(name='hub_'+nm,prefixes=['u_fcore.u_t.u_g.'+s for s in pf],box_um=box))
  d['boxes']=remaining;p.write_text(json.dumps(d,indent=2)+'\n')
  spec=' '.join('{'+b['name']+' {'+' '.join('{'+p+'}' for p in b['prefixes'])+'} '+' '.join(map(str,b['box_um']))+'}' for b in remaining)
  p=dst/'macro_reg_guide.tcl';s=p.read_text();s=re.sub(r'^set ::ot_mrg_spec .*$',lambda _: 'set ::ot_mrg_spec [concat '+spec+']',s,count=1,flags=re.M);p.write_text(s)
  manifest['geometry_change']={'old_hub':old,'new_hub':remaining[-3:],'class':'CHANNEL central staged mux aperture','upper_bound_S1_S2_cut_nets':3456,'vertical_pitch_um':{'M3':.036,'M5':.048},'cut_width_um':292,'capacity_at_50pct':292*(1/.036+1/.048)*.5}
  manifest['pin_cycles']={'additional_vs_vB':0,'existing_rd_vs_preGP':5,'existing_fault':0}
 for q in dst.glob('rtl/*.sv'):
  manifest.setdefault('rtl_sha256',{})[q.name]=hashlib.sha256(q.read_bytes()).hexdigest()
 (dst/'CODEX_FORM.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(name,dst)
