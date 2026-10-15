#!/usr/bin/env python3
"""Actual opt-in linear-Chien FEC composition, full flattened clock census.

Run once under ot-run. Existing original-source census is independent and must
remain untouched. This measures actual RTL state, never timing or library area.
"""
import argparse,hashlib,json,pathlib,subprocess,time
from fec_clock_census import census
ROOT=pathlib.Path(__file__).resolve().parents[2]
FEC='rtl/hbm_accel/io_native_20261014/'
SOURCES=[FEC+n+'.sv' for n in ('ot_hbm_kp4_enc_rooted','ot_hbm_kp4_dec_chien_linear','ot_hbm_kp4_chien55_map','ot_hbm_kp4_encode52_map','ot_hbm_kp4_syndrome55_map','hfd_serdes487_chien_linear_window')]
SOURCES+=['rtl/hbm_accel/io_static_20261015/ot_hbm_static_word_cdc.sv','rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv']
CLOCKS=['clk','clk_collect','clk_encode','clk_codeword','pma_rck','rclk_syndrome','rclk_bm0','rclk_bm1','rclk_bm2','rclk_bm3','rclk_chien','rclk_emit']
TOP='hfd_serdes487_chien_linear_window'
PARAMS={'EMUT':0,'DMUT':0,'WINDOW_WORDS':2048,'CDC_AW':4}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True,type=pathlib.Path);ap.add_argument('--yosys',default=str(pathlib.Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'));a=ap.parse_args()
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 inputs=SOURCES+['rtl/dsrom_sys/s81_link/ot_s81_gf1024.svh',FEC+'chien_linear_provenance.json']
 binding={p:sha(ROOT/p) for p in inputs}
 checker={p:sha(pathlib.Path(__file__).parent/p) for p in ('fec_clock_census.py','run_chien_linear_census.py')}
 source={'sources_sha256':binding,'checker_sha256':checker,'top':TOP,'parameters':PARAMS,'scope':'ACTUAL_FULL_OPTIN_FEC_WITH_STATIC_WINDOW'}
 (out/'source.json').write_text(json.dumps(source,indent=2)+'\n')
 script='read_verilog -sv -D SYNTHESIS -Irtl/dsrom_sys/s81_link '+' '.join(SOURCES)+'\n'
 script+='chparam '+' '.join(f'-set {k} {v}' for k,v in PARAMS.items())+' '+TOP+'\n'
 script+=f'hierarchy -check -top {TOP}\nproc\nflatten\nopt\nmemory_map\nopt\ncheck -assert\nwrite_json {out}/netlist.json\nstat\n'
 (out/'census.ys').write_text(script);started=time.monotonic()
 with (out/'yosys.log').open('w') as log:
  cp=subprocess.run([a.yosys,'-s',str(out/'census.ys')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
 elapsed=time.monotonic()-started
 if cp.returncode:
  (out/'failure.json').write_text(json.dumps({'yosys_exit':cp.returncode,'elapsed_seconds':elapsed,'source':source},indent=2)+'\n');return cp.returncode
 assert binding=={p:sha(ROOT/p) for p in inputs},'Source changed during synthesis'
 assert checker=={p:sha(pathlib.Path(__file__).parent/p) for p in checker},'Census checker changed during synthesis'
 result=census(json.loads((out/'netlist.json').read_text()),TOP,CLOCKS)
 result.update(source);result['elapsed_seconds']=elapsed;result['netlist_sha256']=sha(out/'netlist.json');result['yosys_log_sha256']=sha(out/'yosys.log')
 result['open']=['Mapped library area and leaf partition','Actual pin and routing capacity','TT setup / FF hold / DRC closure','Delivered recovered/local clock phases','Production full link calendar and native composition']
 (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ('total_flop_bits','maximum_root_bits','measured_cts_exception_required')}));return 0
if __name__=='__main__':raise SystemExit(main())
