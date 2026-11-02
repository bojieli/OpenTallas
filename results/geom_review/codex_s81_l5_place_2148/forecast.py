import json,importlib.util,pathlib
p=pathlib.Path('/home/ubuntu/coord/tmp/codex-s81-l5-2148');s=importlib.util.spec_from_file_location('g','/home/ubuntu/OpenTallas/tools/autopilot/geom_rules.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
d=g.Design(p/'A/current_geom.tsv',memory_libs=[p/'ot_sram_1r1w2c_32x64_m1_tt.lib'],memory_reach=True);changes=[];j=0
for cid,c in list(d.cells.items()):
 name=c[6];x=y=None
 if name.startswith('u_dn.s\\[0\\]') or name=='u_dn.v\\[0\\]$_DFF_PN0_':x=c[2]+149.568;y=c[3]
 elif c[0]=='S' and (name.startswith('wa\\[') or name.startswith('wd\\[') or name=='wv$_DFF_PN0_' or name.startswith('g_tbl_safe.g_tj2\\[')):x=155.52+(j%24)*1.35;y=145.8+(j//24)*.54;j+=1
 if x is not None:
  a=list(c);a[2]=x;a[4]=x+(c[4]-c[2]);a[3]=y;a[5]=y+(c[5]-c[3]);d.cells[cid]=tuple(a);changes.append({'cell':name,'old':[c[2],c[3]],'proposed':[x,y]})
r=g.r2r_metrics(d);r['kind']='FORECAST_ONLY_NOT_ACTUAL_NOT_LEGALIZED';r['moved_cells']=len(changes);r['config_regs']=j;r['required']='Owner/parent coordinatedpincontract; sourcekitregen+actualplacement+actualfulltypedreach beforeCTS; no adoption/closure credit';(p/'virtual_reach_FORECAST.json').write_text(json.dumps(r,indent=2));(p/'reg_locations_PROPOSED.json').write_text(json.dumps(changes,indent=2));print(json.dumps(r))
