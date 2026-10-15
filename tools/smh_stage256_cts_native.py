#!/usr/bin/env python3
"""Read-only native pin extraction from the preserved stage256 CTS database.

This is placement-RC evidence, not a routed/sign-off view. Uses the same clock
replay as ck_insertion and reports real pin coordinates for geometry admission.
"""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/closure_loop'))
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
import ck_insertion as CK
import pinreg_audit as PA
def run(base,out,image):
 out.mkdir(parents=True,exist_ok=False)
 text=CK.tcl('tt','4_1_cts.odb','4_cts.sdc',False,'core_clk',raw_source=True)
 assert text.count('\nexit\n')==1
 text=text.replace('\nexit\n','\nwrite_timing_model -library_name ot_smh_static_stage256_tt /out/ot_smh_static_stage256_tt.lib\nwrite_abstract_lef /out/ot_smh_static_stage256.lef\nexit\n')
 (out/'native.tcl').write_text(text)
 cmd=['docker','run','--rm','-v',f'{base}:/base:ro','-v',f'{out}:/out',image,'bash','-lc','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/native.tcl']
 result=subprocess.run(cmd,capture_output=True,text=True);log=result.stdout+result.stderr;(out/'native.log').write_text(log)
 if result.returncode:raise RuntimeError(log[-2000:])
 rows=[(int(a),float(b)) for a,b in re.findall(r'^OT_CK (\d) (\S+)',log,re.M)]
 assert len(rows)==256 and all(a==1 for a,b in rows)
 clock=CK.stats([b for a,b in rows]);ins={'tt':{'boundary':clock,'all':clock},'clock_measurements':{}}
 (out/'insertion.json').write_text(json.dumps(ins,indent=2)+'\n')
 lib=PA.parse_lib(out/'ot_smh_static_stage256_tt.lib');refs=PA.clock_refs(lib,ins,'tt');metrics=PA.pin_metrics(lib,refs)
 launch=max((m['out'],n) for n,m in metrics.items() if m['dir']=='output' and m['out'] is not None)
 capture=max((m['inp'],n) for n,m in metrics.items() if m['dir']=='input' and m['inp'] is not None)
 comb=[n for n,m in metrics.items() if m['comb']]
 rec={'schema':'opentallas.smh.stage256.cts-native.v1','source_db':str(base/'4_1_cts.odb'),'source_db_sha256':hashlib.sha256((base/'4_1_cts.odb').read_bytes()).hexdigest(),'source_sdc_sha256':hashlib.sha256((base/'4_cts.sdc').read_bytes()).hexdigest(),'scope':'placement-RC CTS extraction only; no routed qualification','clock':clock,'launch_ps':launch[0],'launch_pin':launch[1],'capture_ps':capture[0],'capture_pin':capture[1],'comb_pins':comb,'native_pass':launch[0]<=220 and capture[0]<=190 and clock['max']-clock['min']<=80 and not comb,'image':image,'image_id':subprocess.check_output(['docker','image','inspect',image,'--format','{{.Id}}'],text=True).strip(),'command':cmd}
 (out/'verdict.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--image',default='openroad/orfs:latest');a=p.parse_args();run(a.base.resolve(),a.out.resolve(),a.image)
