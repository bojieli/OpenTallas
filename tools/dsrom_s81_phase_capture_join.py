"""Disjoint Popper emitted-phase -> Nash finite capture integration.

Uses the already constructed authoritative StageProgramJoin. No mapping scan,
program re-emission, allocator replay, source writes or runtime launches.
"""
import hashlib,json
from pathlib import Path
from dsrom_s81_capture_profile import compile_profile
from dsrom_s81_capture_install import install,replace_once
ROOT=Path(__file__).resolve().parents[1]
PROFILE='rtl/dsrom_sys/rd64_capture/ot_dsrom_s81_phase_capture_profile.sv'

def emitted_phase_profile(stage_join,connectivity,*,stage,rank,phase,positions,key,ME):
    if stage_join.lookup(stage,key,ME=ME)!=phase:raise ValueError('actual emitted key/phase mismatch')
    row=stage_join.by_stage[stage][phase]
    if rank not in row['owners']:raise ValueError('rank is not physical field owner')
    profile=compile_profile(row['matrix'],connectivity,positions)
    n=row['rows'];q,rem=divmod(n,256)
    count=[(2*q+(rem>2*r)+(rem>2*r+1))*positions for r in range(128)]
    if count!=profile['root_return_counts']:raise ValueError('canonical quota formula does not match actual plans')
    return dict(stage=stage,rank=rank,phase=phase,key=key,ME=ME,
      source_matrix_sha256=row['matrix_sha256'],phase_rows=n,positions=positions,
      root_return_counts=count,root_rows=profile['rows'],
      readonly_profile=True,hardware_admission_granted=False,
      source_of_live_count='actual PHROM word2*i_ph bits61:46 and accepted i_np, not this host result')

def install_bound_spine(spine_source,out):
    """Generate added-only actual spine with internal canonical count path.

    Parent selects CAPTURE_S81_PROFILE=1 only for source-bound Popper phase ROM.
    External capture_root_rows stays available; enable0 preserves prior install.
    """
    receipt=install(spine_source,out);dest=Path(receipt['generated']);s=dest.read_text()
    s=replace_once(s,'parameter integer CAPTURE_ENABLE = 0,','parameter integer CAPTURE_S81_PROFILE = 0,\n    parameter integer CAPTURE_ENABLE = 0,')
    s=replace_once(s,'    wire cap_ready,cap_idle;', '''    wire [128*19-1:0] canonical_root_rows;
    ot_dsrom_s81_phase_capture_profile #(.ENABLE(CAPTURE_S81_PROFILE)) u_capture_profile (
      .phase_rows(phrom[{i_ph,1'b0}][61:46]),.phase_np(i_np),.root_returns(canonical_root_rows));
    initial if(CAPTURE_S81_PROFILE && R!=128)$fatal(1,"canonical root profile requires R128");
    wire cap_ready,cap_idle;''')
    s=replace_once(s,'.phase_id(10\'(i_ph)),.phase_root_rows(capture_root_rows),',
      '.phase_id(10\'(i_ph)),.phase_root_rows(CAPTURE_S81_PROFILE ? canonical_root_rows : capture_root_rows),')
    dest.write_text(s);receipt.update(generated_sha256=hashlib.sha256(s.encode()).hexdigest(),
      canonical_profile_selection_default=0,canonical_profile_enable_parameter='CAPTURE_S81_PROFILE',
      immutable_profile_payload_added_bits=0,mutable_profile_state_added_bits=0,
      profile_source=str(ROOT/PROFILE),profile_source_sha256=hashlib.sha256((ROOT/PROFILE).read_bytes()).hexdigest(),
      profile_origin='installed actual PHROM at accepted i_ph plus actual i_np',
      bound_emitter_required='Popper StageProgramJoin exact canonical phase/key/matrix association',
      enclosing_top_installed=False)
    receipt['sources'].insert(0,str(ROOT/PROFILE))
    (Path(out)/'source_join.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--spine',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();print(json.dumps(install_bound_spine(a.spine,a.out),indent=2))
