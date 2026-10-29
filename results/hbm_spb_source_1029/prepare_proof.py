"""Exercise actual v2 rewriter; produce narrowly wrong reset + rejection controls."""
import importlib.util,json,shutil,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'results/hbm_spb_source_1029';inputs,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=False)
Mpath=root/'tools/die_plan/hbm_spb0_assets/spb0_native.py';sp=importlib.util.spec_from_file_location('adapter',Mpath);M=importlib.util.module_from_spec(sp);sp.loader.exec_module(M)
for n in ['contract.json','actual_graph.json','placement.json']:shutil.copy2(inputs/n,out/n)
M.run(base/'reset_fixture.sv',out/'actual_graph.json',out/'contract.json',out/'good')
p=out/'good/reset_fixture.sv';s=p.read_text();s=s.replace('module SPB0_source(','module SPB0_source_wrong_reset(');assert s.count('.rst_n(rst_n_t20),.d(')==2;s=s.replace('.rst_n(rst_n_t20),.d(','.rst_n(rst_n),.d(');(out/'wrong_reset.sv').write_text(s)
# Existing strict v1 is unchanged; v2 rejects a reverse slice and a shifted reset.
findings={}
for name,old,new in [('reversed_bus','w_u_lk_S0_rx[511:0]','w_u_lk_S0_rx[0:511]'),('wrong_delivered_reset','.rst_n(rst_n_t20)','.rst_n(rst_n)')]:
 t=(base/'reset_fixture.sv').read_text();assert old in t;bad=out/(name+'.sv');bad.write_text(t.replace(old,new))
 try:M.run(bad,out/'actual_graph.json',out/'contract.json',out/(name+'_out'))
 except ValueError as e:findings[name]=str(e)
 else:raise ValueError('negative contract accepted '+name)
(out/'contract_controls.json').write_text(json.dumps(findings,indent=1)+'\n')
