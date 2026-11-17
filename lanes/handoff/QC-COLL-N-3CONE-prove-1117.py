import importlib.util,json
from pathlib import Path
r=Path('/srv/opentallas-scratch2/claude/qc-pinaccess-o/coll_n_hold80_1116');out=r/'lec5_diag3_512_1117';s=importlib.util.spec_from_file_location('saved_lec',r/'lec_kit/lec.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
d=m.read_aig(out/'joint_three.aig');a=m.Aig();a.ni=d['I'];a.inames=['joint_basis_'+str(i) for i in range(a.ni)];a.ands=d['ands'];a.outs=d['outputs'];a.onames=['epoch_abort','fault_cause[0]','rx_v'];log=[]
st=m.prove(a,out,10000,log,tag='joint_three_proof',single_cap=3);(out/'joint_proof_status.json').write_text(json.dumps(st,indent=2)+'\n');(out/'joint_proof.log').write_text('\n'.join(log));print(st,flush=True)
