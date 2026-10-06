#!/usr/bin/env python3
"""Only source-changing W5 AO/gate exactness. Reuses original element flatten method."""
from pathlib import Path
import sys,json,subprocess
import rom_stage_cdc_sim as c
import rom_stage_pg_sim as b
ROOT=b.ROOT
p=Path(sys.argv[1]);p.mkdir(parents=True,exist_ok=True)
# Do not build unchanged arithmetic again: use the retained fullshape instrumented
# element only when its actual ELEM hashes match this source. Otherwise flatten.
reuse=Path(sys.argv[2]); evidence=json.loads((reuse/'exact.json').read_text())
for f in b.ELEM:
    if evidence['sources'][f]!=b.sha(ROOT/f): raise SystemExit('retained element source mismatch: '+f)
flat=p/'elem_flat_pgx.v';ref=p/'elem_ref.v'
import shutil
shutil.copy2(reuse/'build/elem_flat_pgx.v',flat);shutil.copy2(reuse/'build/elem_ref.v',ref)
state=evidence['domain_state']
s=(ROOT/c.TB).read_text().replace('ot_v41_rom_stage_q_pg_cdc_w10 #(.K(1)', 'ot_w5_stage_q_pg_cdc_w10 #(.PROTECTED_AO(1),.RETENTION_EDGE_WRITE(1),.K(1)')
s=s.replace('.go(go), .xs_v(xs_v)', '.context_fault(1\'b0), .go(go), .xs_v(xs_v)')
s=s.replace('dut.u_ao.u_ctl','dut.u_ao.u_p.u_ctl').replace('dut.u_ao.g_e','dut.u_ao.u_p.g_e').replace('dut.u_ao.pwr_good','dut.u_ao.u_p.pwr_good').replace('dut.u_ao.iso_n','dut.u_ao.u_p.iso_n')
# Legacy simultaneous AO and domain clock falling edges must not alter the
# request/receipt timeline; quarantined mode is exercised in the AO fault bench.
pth=p/'bench.sv';pth.write_text(s)
c.TB=str(pth);c.PG_RTL=['rtl/experimental/w5_context/ot_w5_stage.sv']
r=c.run(p,None,flat,ref)
(p/'exact.json').write_text(json.dumps({'run':r,'state':state,'sources':{f:b.sha(ROOT/f) for f in b.ELEM+c.PG_RTL},'scope':'source-changing protected fullshape stage; original flattened domain randomisation'},indent=2)+'\n')
print(json.dumps(r,indent=2));raise SystemExit(0 if r['pass_'] else 1)
