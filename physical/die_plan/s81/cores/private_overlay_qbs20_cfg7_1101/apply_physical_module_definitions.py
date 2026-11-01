#!/usr/bin/env python3
from pathlib import Path
import json,re,sys,hashlib,shutil,ast
HERE=Path(__file__).resolve().parent;k=Path(sys.argv[1])
helper=(HERE/'parameter_helper_source.py').read_text();ns=dict(re=re)
node=next(n for n in ast.parse(helper).body if isinstance(n,ast.FunctionDef)and n.name=='_mask')
exec(compile(ast.Module(body=[node],type_ignores=[]),'<exact-module-mask>','exec'),ns)
masters=['ot_v41_rom_elem_q_qxpq_w10_gb','dsfd_cfifo_crs4','dsfd_bf_front_roots','ot_v41_bf_col']
out=k/'rtl_fixed_physical_modules';out.mkdir(exist_ok=True);cfg=(k/'config.mk').read_text();prior=k/'prior_physical_module_definitions';prior.mkdir(exist_ok=True);report=[]
for name in masters:
 source=k/'rtl'/f'{name}.sv';s=source.read_text();mask=ns['_mask'](s)
 hits=list(re.finditer(r'\bmodule\s+'+re.escape(name)+r'\b',mask));assert len(hits)==1,(name,len(hits))
 a=hits[0].start();end=re.search(r'\bendmodule\b',mask[hits[0].end():]);assert end
 b=hits[0].end()+end.end();new=s[:a]+s[b:];target=out/source.name;target.write_text(new)
 old='/work/rtl/'+source.name;newpath='/work/rtl_fixed_physical_modules/'+source.name
 assert cfg.count(old+' ')==1,(name,'source list not exact')
 cfg=cfg.replace(old+' ',newpath+' ',1)
 report.append(dict(master=name,original_sha256=hashlib.sha256(s.encode()).hexdigest(),helper_preserved_sha256=hashlib.sha256(new.encode()).hexdigest(),header='/work/rtl/'+name+'_bb.v',reason='selected hard body already blackboxed; remove duplicate definition from alternate Slang frontend; preserve all helper modules'))
shutil.copy2(k/'config.mk',prior/'config.mk')
(k/'config.mk').write_text(cfg);(k/'physical_module_definition_projection.json').write_text(json.dumps(report,indent=2))
print('Removed exactly4 duplicate native hardmodule bodies; nativeheaders+allhelper/sourceconnections retained')

