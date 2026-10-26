#!/usr/bin/env python3
"""Run the recovered valid-masked four-state DRST comparison and two live mutants."""
import argparse,concurrent.futures,json,subprocess,re,shutil
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2]);ap.add_argument('--gold-ref',default='5e2d78d280');ap.add_argument('--prepare-only',action='store_true');a=ap.parse_args();r=a.out.resolve();r.mkdir(parents=True,exist_ok=True);src=r/'src';src.mkdir(exist_ok=True)
for path in ['rtl/hdc/'+n for n in ['ot_hdc_prefix.sv','ot_hdc_fastfp.sv','ot_hdc_fp32_add_lat.sv','ot_hdc_fp32_mul_lat.sv']]+['rtl/hdc/v41x/ot_hdc_v41x_hcp.sv']:
 p=a.repo/path;text=p.read_text() if p.exists() else subprocess.check_output(['git','-C',str(a.repo),'show','HEAD:'+path],text=True);(src/p.name).write_text(text)
gold=subprocess.check_output(['git','-C',str(a.repo),'show',a.gold_ref+':rtl/hdc/v41x/ot_hdc_v41x_hcp.sv'],text=True);leaf=re.search(r'^module ot_hdc_v41x_hcp_lanes.*?^endmodule',gold,re.M|re.S)[0].replace('module ot_hdc_v41x_hcp_lanes','module gold_hcp_lanes',1);(r/'gold_lanes.sv').write_text(leaf)
assert '.DRST(ADRST)) u_mul' in (src/'ot_hdc_v41x_hcp.sv').read_text()
md=re.search(r'^module ot_hdc_fp32_mul_lat.*?^endmodule',(src/'ot_hdc_fp32_mul_lat.sv').read_text(),re.M|re.S)[0].replace('module ot_hdc_fp32_mul_lat','module ot_hdc_fp32_mul_lat_md',1);k=md.index('g_output_valid_reset');md=md[:k]+md[k:].replace(': e_code;',": e_code ^ 32'h1;",1);(r/'mul_md.sv').write_text(md)
shutil.copyfile(Path(__file__).with_name('hc128_drst_tb.sv'),r/'tb_drst_3k.sv')
if a.prepare_only:raise SystemExit(0)
files=[src/n for n in ['ot_hdc_prefix.sv','ot_hdc_fastfp.sv','ot_hdc_fp32_add_lat.sv','ot_hdc_fp32_mul_lat.sv','ot_hdc_v41x_hcp.sv']]+[r/'gold_lanes.sv']
def run(mode):
 d=[] if mode=='gate' else ['-D'+mode];extra=[r/'mul_md.sv'] if mode=='MUT_DATA' else []
 with (r/(mode+'.build.log')).open('w') as f:rc=subprocess.run(['iverilog','-g2012','-DSYNTHESIS',*d,'-s','tb','-o',str(r/(mode+'.vvp')),*map(str,files+extra),str(r/'tb_drst_3k.sv')],stdout=f,stderr=subprocess.STDOUT).returncode
 assert rc==0,(mode,'build',rc)
 with (r/(mode+'.log')).open('w') as f:rc=subprocess.run(['vvp','-n',str(r/(mode+'.vvp'))],stdout=f,stderr=subprocess.STDOUT).returncode
 text=(r/(mode+'.log')).read_text();ma=re.search(r'DRST_CHECK cycles=(\d+) mul_valid_compares=(\d+) leaf_valid_compares=(\d+) fails=(\d+)\s+(PASS|FAIL)',text);assert ma,(mode,'no result',rc)
 cy,mul,leaf,fails=map(int,ma.groups()[:4]);assert cy==3000 and mul>100 and leaf>100,(mode,ma.groups())
 verdict='PASS' if mode=='gate' and fails==0 and ma[5]=='PASS' else 'CAUGHT' if mode!='gate' and fails>0 and ma[5]=='FAIL' else 'FAIL';assert verdict!='FAIL',(mode,text[-500:])
 return mode,dict(verdict=verdict,cycles=cy,mul_valid_compares=mul,leaf_valid_compares=leaf,failures=fails,rc=rc)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:result=dict(ex.map(run,['gate','MUT_NORST','MUT_DATA']))
(r/'result.json').write_text(json.dumps(dict(schema='opentallas.hbm.hc128.drst_4state.v1',verdict='PASS',scope='3000-cycle four-state multiplier+8-lane leaf valid-masked comparison including active reset pulse; finite simulation, not unbounded proof',checks=result),indent=2)+'\n');print(json.dumps(result))
