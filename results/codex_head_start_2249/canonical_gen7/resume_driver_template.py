"""Resume canonical physical generation from its complete, audited RTL output."""
import json,shutil,sys
from pathlib import Path
r=Path('/srv/opentallas-scratch2/claude/codex-head-start-2249');w=Path('/srv/opentallas-scratch2/claude/wt/codex-head-start-2249')
sys.path[:0]=[str(w/'tools/die_plan'),str(w/'tools/s81_head')]
import gen_phys,gen_rtl
from head_start_raw_private import patch_rtl as private_raw
from head_start_reset_aliases import patch_rtl as aliases
prior=r/'canonical_gen5';cache=prior/'gen'/'_rtl';out=r/'canonical_gen6';out.mkdir(exist_ok=False)
raw=json.load(open(prior/'source_plan_rekit.json'));side=json.load(open(r/'inputsrc4'/'source_sidecar.json'))
assert json.load(open(cache/'gen_count_strap_audit.json'))['verdict']=='PASS'
assert json.load(open(cache/'gen_clock_landings.json'))['implemented']
plan=out/'source_plan_rekit.json';plan.write_text(json.dumps(raw,indent=1));(out/'core_pins').symlink_to((prior/'core_pins').resolve())
def cached_write_rtl(given,dest,root=None,types=None,plan_path=None,landing=None):
    assert given==raw and landing==side
    shutil.copytree(cache,dest)
    return list(Path(dest).iterdir())
gen_rtl.write_rtl=cached_write_rtl
types={'hd_st_str','hd_st_n3_transit','hd_st_m'}
print('CANONICAL_PHYS_RESUME_COMPLETE_RTL_CACHE',flush=True)
kits=gen_phys.write_phys(raw,out/'gen',rtl_root=w,types=types,plan_path=plan,trial=True,landing=side)
rows=[]
for tn in sorted(types):
    t=raw['partition_types'][tn];mod=t['module'];wr=out/'gen'/'_rtl'/(mod+'.sv');kit=out/'gen'/tn
    text=aliases(wr.read_text(),t.get('reset_start_raw_exports',[]));text,pv=private_raw(text,t)
    wr.write_text(text);(kit/'rtl'/(mod+'.sv')).write_text(text)
    assert '# OT_FWD_RING_INPUTS' in (kit/'constraint.sdc').read_text(),tn
    assert 'reader-start-origin' in (kit/'landing_placement.tcl').read_text(),tn
    rows.append(dict(type=tn,kit=str(kit),canonical_fwd_ring_sdc=True,explicit_origin_anchor=True,
                     private_raw=pv,boot_extra_cycles=2,steady_data_cycles_added=0))
(out/'summary.json').write_text(json.dumps(rows,indent=1));print(json.dumps(dict(canonical_kits=len(rows),types=sorted(types))),flush=True)
