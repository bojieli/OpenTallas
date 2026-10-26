from pathlib import Path
import json,re,shutil,hashlib
ROOT=Path.cwd()
B=Path('/srv/opentallas-scratch2/claude/codex-kv-bind-bank-2144/b19')
TREE=B.parent/'tree'
O=ROOT/'physical/die_plan/qwen_kvsys/sysc_g3'
O.mkdir(parents=True,exist_ok=True)
BOUT=O/'bind_snapshot';(BOUT/'rtl').mkdir(parents=True,exist_ok=True)
for n in ['bind_report.json','bind_names.json','bind_latency.json','pad_geometry_impact.json','bind.f']:
 shutil.copyfile(B/n,BOUT/n)
for n in ['bind_cells.sv','qwen_kvsys_bound_top.sv']:
 shutil.copyfile(B/'rtl'/n,BOUT/'rtl'/n)
s=(B/'rtl/kv3_sys_c_part.sv').read_text()
sha=hashlib.sha256(s.encode()).hexdigest()
assert sha=='feda9bf551322910309fbf18e3fa4ede26465f3ba441b3dbf34e219e084a793b',sha
original=s
ports=['link_v','link_flit','far_v','far_flit']
s=re.sub(r'^    (?:input|output)  ?wire .*? bump_ucie_rom_(?:link_v|link_flit|far_v|far_flit),.*\n','',s,flags=re.M)
assert 'bump_ucie_rom_' not in s.split(');',1)[0]
m=re.search(r'    ot_qkvd_ucie_x64_phy u_ucie_rom \(.*?\n    \);',s,re.S);assert m
old=m[0];new=old
for name in ports:
 new,n=re.subn(r'^        \.'+name+r'\([^\n]*\),?\n','',new,flags=re.M);assert n==1
new=new.replace(',\n    );','\n    );')
s=s[:m.start()]+new+s[m.end():]
assert 'bump_ucie_rom_' not in s
(BOUT/'rtl/kv3_sys_c_part.sv').write_text(s)
source=json.load(open(B/'asbuilt_sources.json'))
paths=list(dict.fromkeys(source['full']+source['lib']))
copy={}
def snapshot(path):
 p=Path(path)
 if str(p) in copy:return copy[str(p)]
 if p.is_relative_to(TREE):rel=Path('sources')/p.relative_to(TREE)
 elif p.is_relative_to(B):rel=Path('elab_sources')/p.relative_to(B)
 else:raise ValueError('unexpected external source '+str(p))
 dst=O/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
 copy[str(p)]=str(dst.relative_to(ROOT))
 for inc in re.findall(r'^\s*`include\s+"([^"]+)"',p.read_text(),re.M):snapshot(p.parent/inc)
 return copy[str(p)]
for p in paths:snapshot(p)
# Select the actual native seven-FDI-port PHY view; offshore pads are not fabric
# pins in this projection. The immutable functional b19 source remains untouched.
phy='physical/die_plan/qwen_kvsys/cores/sys_c_views_m6/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_bb.v'
phy_original=[x for x in paths if x.endswith('/ot_qkvd_ucie_x64_phy_bb.v')];assert len(phy_original)==1
copy[phy_original[0]]=phy
recipe=json.load(open(TREE/'physical/die_plan/qwen_kvsys/dcal_rom/bind/position2144b19/recipe_position_2144.rom64.json'))
fl=[copy[p] for p in paths]
# Exact b19 root providers win; dependencies resolve in the unchanged combined
# source tree. Explicit snapshots avoid mutable source paths in generated kits.
ab=dict(base='../../../..',top='qfd_die',rtl_roots=['rtl','physical/asap7_memory_macros_v2'],files=fl,prefer=fl,defines=recipe.get('defines',[]))
plan=json.load(open(ROOT/'physical/die_plan/qwen_kvsys/die_plan.json'));plan['asbuilt']=ab
(O/'kit_plan.json').write_text(json.dumps(plan,indent=1)+'\n')
(BOUT/'bind.f').write_text('\n'.join(str(ROOT/x) for x in fl)+'\n')
rep=json.load(open(BOUT/'bind_report.json'));rep.pop('extra_lib',None);(BOUT/'bind_report.json').write_text(json.dumps(rep,indent=1)+'\n')
checks=[]
for name in ['clk','rst_n','tx_up','tx_v','tx_flit','rx_v','rx_flit']:
 a=re.search(r'\.'+name+r'\(([^\n]*)\)',old);b=re.search(r'\.'+name+r'\(([^\n]*)\)',new)
 assert a and b and a[1]==b[1];checks.append(name)
manifest=dict(source='b19',source_sha256=sha,source_commit='498db8776',physical_plan_commit='e055c9ee57',projection='FDI-only physical view, excludes offshore bumpinterface only',removed_ports=ports,preserved_FDI=checks,removed_pipeline_registers=0,ft1_stations=len(re.findall(r'u_ft_ft1_o_\d+ \(',s)),sources=copy)
assert manifest['ft1_stations']==12
(O/'projection.json').write_text(json.dumps(manifest,indent=1)+'\n')
print('Snapshot complete',len(copy),'sources;7FDI preserved,12FT stages; functional b19 unchanged')
