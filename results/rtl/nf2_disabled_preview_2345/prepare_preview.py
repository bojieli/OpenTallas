"""Create one private disabled NF2 SYNTH-only capsule from the qualified actual source."""
from pathlib import Path
import argparse,hashlib,json,shutil

def prepare(subject,root):
    subject,root=Path(subject),Path(root)
    q=json.loads((root/'qualification/COMPOSITE.json').read_text())
    assert q['verdict']=='EQUIVALENT_COMPOSITE_6370_OF_6370' and q['constraints']==0
    source=subject/'normal'; target=root/'kit'
    if target.exists():raise ValueError('preview exists; preserve prior attempt')
    patterns=['run','views','signoff','lec','lec_post','diag','__pycache__','*.log','*.rc','rc.txt','*.on','*.pid','*.owner','.ot-run-spill-copy']
    shutil.copytree(source,target,ignore=shutil.ignore_patterns(*patterns))
    h=hashlib.sha256((target/'rtl/qkd_ahub_static_dw.sv').read_bytes()).hexdigest()
    assert h==q['normal_source_sha256']
    event=dict(status='DISABLED_ONE_SYNTH_PREVIEW',module='qkd_ahub_static_core_la_ck7',source_sha256=h,
               qualification=str(root/'qualification/COMPOSITE.json'),added_source_ff=16,added_cycles=0,pin_abi_changes=0,
               target_outline_um=[604.8,440.64],activation='OFF; no canonical source/recipe/plan modification',
               allowed_stage='synth only; no floorplan/place/CTS/GRT/DRT/STA',
               resource=dict(mem_gb=8,threads=2,measured_AHUB_native_synth_peak_KB=356976,original_synth_elapsed_s=75.69),
               current_mutant='existing job preserved, collect independently')
    (target/'DISABLED_EVENT.json').write_text(json.dumps(event,indent=2)+'\n')
    (target/'.keep').touch()
    print(json.dumps(event,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--subject',required=True);p.add_argument('--root',required=True);a=p.parse_args();prepare(a.subject,a.root)
