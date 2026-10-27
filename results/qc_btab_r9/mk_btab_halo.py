import sys,json,importlib.util
from pathlib import Path
root=Path(sys.argv[1]);out=root/'results/qc_btab_r9'
p=root/'physical/die_plan/qwen_compute/cores/legacy/gen_core_kit_qc.py'
sp=importlib.util.spec_from_file_location('qcgen',p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
s=m.pincol_halo_strips((out/'macro.lef').read_text(),[(129.6,y,'MY') for y in (30.24,86.4,142.56,198.72)],4.32)
(out/'sram_pincol_halo.json').write_text(json.dumps(dict(schema='opentallas.qc.sram_pincol_halo.v1',strips=s,mpf_halo_um=max(q['depth_um'] for q in s),source='gen_core_kit_qc.py@4b0c7c393c'),indent=2)+'\n')
(out/'halo_btab.tcl').write_text('set b [ord::get_db_block]\nset dbu [[ord::get_db_tech] getDbUnitsPerMicron]\n'+m.pch_tcl(s))
print('BTAB_R9_STRIPS',len(s),'depth',max(q['depth_um'] for q in s))
