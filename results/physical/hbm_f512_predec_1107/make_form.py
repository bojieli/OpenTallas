from pathlib import Path
import shutil,json,sys
r=Path(__file__).resolve().parents[3];b=Path(sys.argv[1]);k=Path(sys.argv[2]);assert not k.exists();shutil.copytree(b,k);(k/'.keep').touch()
shutil.copy2(r/'rtl/hbm_accel/generic/vm/static/faces_q0/ot_vms_bank_q0_faces_body.sv',k/'rtl/ot_vms_bank_q0_faces_body.sv')
p=k/'rtl/ot_vms_bank_q0_faces_core.sv';s=p.read_text();assert '.EG_WIDE(1))'in s;p.write_text(s.replace('.EG_WIDE(1))','.EG_WIDE(1),.WRITE_PREDECODE(1))',1))
(k/'FORM_CANDIDATE.json').write_text(json.dumps(dict(owner='CODEX-HBM1209',form='f512_vCF2_predec',kind='NEW_RTL_REBUILD_NOT_ECO',base='vCF1d',changes=['source-local sectorpredecode at existingcapture'],additional_pin_cycles=0,total_input_cycles_from_native=2,qualification='DO_NOT_COUNT; onePLACEonly; remainingclock/holdstructureunresolved'),indent=1)+'\n')
print(k)
