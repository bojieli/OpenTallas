#!/usr/bin/env python3
"""Distinct actual structural candidate census/scalar map, no library area claim."""
import argparse,hashlib,json,pathlib,subprocess,time
from fec_clock_census import census
CLOCKS=['fec_tx_clk','phy_tx_clk','phy_rx_clk','fec_rx_clk']+[f'tx_bank{i}' for i in range(4)]+[f'rx_bank{i}' for i in range(4)]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=pathlib.Path,required=True);ap.add_argument('--basis-receipt',type=pathlib.Path,required=True);ap.add_argument('--out',type=pathlib.Path,required=True);a=ap.parse_args()
 src=a.source.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 files=[src/'ot_hbm_pma_block_gearbox_static_words.sv',src/'ot_hbm_pma_static_words_census12.sv'];pins={p.name:sha(p) for p in files};proof=json.loads(a.basis_receipt.read_text());assert proof['positive_pass'] and proof['basis_enabled'];assert proof['source_sha256'][files[0].name]==pins[files[0].name]
 top='ot_hbm_pma_static_words_census12';binding={'top':top,'source_sha256':pins,'proof_receipt_sha256':sha(a.basis_receipt),'runner_sha256':sha(pathlib.Path(__file__)),'checker_sha256':sha(pathlib.Path(__file__).with_name('fec_clock_census.py')),'clock_roots':CLOCKS,'scope':'ISOLATED_ACTUAL_FIXED_WORD_TX_RX_PMA_GEARBOXES_ONLY','excludes':['FEC encoder/decoder/internal CDC','outer core CDC/frame transport/caller endpoints/SRAM','analog PHY pads and clock-phase/physical qualification'],'library_mapped':False,'physical_qualified':False}
 (out/'binding.json').write_text(json.dumps(binding,indent=2)+'\n');(out/'clock_manifest.json').write_text(json.dumps({'clocks':CLOCKS},indent=2)+'\n')
 script=''.join(f'read_verilog -sv {p}\n' for p in files)+f'hierarchy -check -top {top}\nproc\nflatten\nopt\nmemory_map\nopt\ncheck -assert\nwrite_json {out}/generic_netlist.json\ntechmap\nopt\ncheck -assert\nstat\nwrite_json {out}/bit_netlist.json\n'
 (out/'map.ys').write_text(script);started=time.monotonic()
 with (out/'yosys.log').open('w') as log:cp=subprocess.run([str(pathlib.Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'),'-s',str(out/'map.ys')],stdout=log,stderr=subprocess.STDOUT)
 result=dict(binding,yosys_exit=cp.returncode,elapsed_seconds=time.monotonic()-started,script_sha256=sha(out/'map.ys'),log_sha256=sha(out/'yosys.log'))
 assert {p.name:sha(p) for p in files}==pins
 if cp.returncode==0:
  count=census(json.loads((out/'generic_netlist.json').read_text()),top,CLOCKS);assert count['total_flop_bits']==70880;assert count['maximum_root_bits']==8704
  result['generic_clock_census']=count;result['generic_netlist_sha256']=sha(out/'generic_netlist.json');result['bit_netlist_sha256']=sha(out/'bit_netlist.json')
 (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return cp.returncode
if __name__=='__main__':main()
