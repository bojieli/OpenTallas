from pathlib import Path
import json,re,sys
b=Path(sys.argv[1]);records={}
p=b/'pdn.tcl';s=p.read_text();assert s.count('1883.52')==3,s.count('1883.52');p.write_text(s.replace('1883.52','1870.56'));records['pdn_right_margin_replacements']=3
p=b/'phy_pg.json';x=json.load(p.open());assert x[0]['rect_type_um']==[17.28,54.,1883.52,1026.];x[0]['rect_type_um'][2]=1870.56;p.write_text(json.dumps(x,indent=1)+'\n')
p=b/'landing_placement.tcl';s=p.read_text();n=0
for name in ('u_cland_i_host_fdi','u_cland_i_host_link_rst_n'):
 pat=r'('+re.escape(name)+r' \{)1883\.52000'
 s,k=re.subn(pat,r'\g<1>1870.56000',s);n+=k
assert n==2,n;p.write_text('# CODEX KV2249 truthfulPHY/PG fit variant; originaltry4 unchanged\n'+s)
p=b/'landing_contract.json';x=json.load(p.open())
for v in x['bands'].values():
 assert v['rect_um'][0]==1883.52
 v['resized_from_um']=list(v['rect_um']);v['rect_um'][0]=1870.56;v['resize']='CODEX2249 actual1848.96LEF+4.32PHYmargin; noPGcontactsremoved'
p.write_text(json.dumps(x,indent=1)+'\n')
records.update(source='DIE-KV41 try4; ownclone only',actual_phy_um=[17.28,54,1866.24,1026],old_region_um=[17.28,54,1883.52,1026],new_region_um=[17.28,54,1870.56,1026],ring_width_old_um=12.96,ring_width_new_um=25.92,rtl_changed=False,logical_cycles_added=0,pg_contacts_removed=0,reason='supplyregion still contains entire actualPHYplus4.32um; existingbumpgenerator retains in-leafsites only')
(b/'SD_PG_ALIGNMENT.json').write_text(json.dumps(records,indent=2)+'\n')
