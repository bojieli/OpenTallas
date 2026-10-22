"""Minimum actual four-user codec comparison for n36 DATA reset and stored lpos_next."""
from pathlib import Path
import subprocess,sys
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
s=Path('rtl/qwen_sys/mu_qwen_20261018/qkd_host_record_port_mu.sv').read_text()
s=s[s.index('module qkd_host_native_context_tx_mu'):].replace('module qkd_host_native_context_tx_mu','module qkd_host_native_context_tx_mu_ref',1)
(out/'reference.sv').write_text(s)
cmd=['verilator','--binary','--timing','-j','4','-Wno-fatal','-Wno-lint','-Wno-style','--top-module','tb_hkv_context_n36','-Mdir',str(out/'obj'),str(out/'reference.sv'),'rtl/qwen_sys/host_cluster_20261017/prompt_safe5/qkd_host_record_port_mu.sv','rtl/test/qwen_host/tb_hkv_context_n36.sv']
with (out/'build.log').open('w') as f: subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
with (out/'run.log').open('w') as f: r=subprocess.run([str(out/'obj/Vtb_hkv_context_n36')],stdout=f,stderr=subprocess.STDOUT)
log=(out/'run.log').read_text();print(log);assert r.returncode==0 and 'N36_CONTEXT PASS' in log
