#!/usr/bin/env python3
"""Package existing immutable native diagnostics, without new qualification runs."""
import gzip,hashlib,json,pathlib
r=pathlib.Path('.');out=r/'receipts';out.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
items={}
for name,folder,report in [('controller','controller_onebank','native.json'),('raw_whole','controller_onebank','whole_native.json'),('reset_context','controller_onebank','reset_context/native.json')]:
 p=r/folder/report;x=json.load(open(p));net=r/folder/x['netlist']['path'];assert sha(net)==x['netlist']['sha256']
 d={k:x[k] for k in ['schema','status','roots_examined','max_dynamic_loads','role_errors','netlist']};d['violations']=[{k:v for k,v in q.items() if k!='endpoints'} for q in x['violations']];d['full_report_sha256']=sha(p);d['qualified']=False;items[name]=d
(out/'native_summary.json').write_text(json.dumps(items,indent=1)+'\n')
inputs=['private_shell_proposal.sv','qkc_afifo_bits_1021.sv','qkd_host_native_engine_n32.sv','ot_host_die_cdc_sram.sv','ot_link_afifo.sv','qkd_hr_ingest_qm.v','helpers/ot_keep_regs.tcl','helpers/ot_pin_regs.tcl','helpers/ot_rst_copies.tcl','helpers/ot_rst_copies.py','controller_onebank/reconnection.json','controller_onebank/qkd_hr_ingest_soft_n32.json','controller_onebank/scalar_abi.json','controller_onebank/projection.json','controller_onebank/whole_integrated.v','controller_onebank/reset_context/whole_reset_context.v']
(out/'source_binding.json').write_text(json.dumps({p:sha(r/p) for p in inputs},indent=1)+'\n')
# Repository receipts keep exact compressed candidate/context plus the context
# projection and scalar ABI needed to reconstruct every parent connection.
for p in ['controller_onebank/whole_integrated.v','controller_onebank/reset_context/whole_reset_context.v','controller_onebank/scalar_abi.json','controller_onebank/projection.json','controller_onebank/reconnection.json','controller_onebank/qkd_hr_ingest_soft_n32.json']:
 with gzip.open(out/(pathlib.Path(p).name+'.gz'),'wb') as f:f.write((r/p).read_bytes())
print(json.dumps({k:(v['status'],v['roots_examined'],v['max_dynamic_loads']) for k,v in items.items()}))
