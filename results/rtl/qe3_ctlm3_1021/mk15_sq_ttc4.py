# SQ-TTC4 10-21: safe15a/b = safe14a/b (QE3-CTLM3 lp9f_rr CALREG15) + per-domain spatial spine with CHILD-FLOP leaf
# targets (domain_spatial_spine.child_insertion boundary_record) -> clock_rule judged at the child flops can close.
import json
from pathlib import Path
W = Path('/home/ubuntu/wt/sq-ttc4-s15')
for src, tag in (('safe14a', 'safe15a'), ('safe14b', 'safe15b')):
    sd = W / f'physical/ref_tile/qfd_tt_ctlm_dv_{src}'
    kd = W / f'physical/ref_tile/qfd_tt_ctlm_dv_{tag}'
    kd.mkdir(exist_ok=True)
    s = json.loads(json.dumps(json.loads((sd / 'spec.json').read_text())).replace(f'qfd_tt_ctlm_dv_{src}', f'qfd_tt_ctlm_dv_{tag}'))
    s['domain_spatial_spine'] = dict(version=1, roots=[dict(domain='core', port='ck_core'), dict(domain='hr', port='ck_hr')],
                                     symmetric=True, bin_um=30, leaf_max=16, iterations=10, rc_cal=False,
                                     macro_leaf=True, macro_pin_leaf=True, child_insertion='boundary_record')
    purpose = (f"SQ-TTC4 10-21 {tag}: {src} (QE3-CTLM3 lp9f_rr CALREG15, same geometry/pins) + per-domain spatial spine "
               "(Codex cc872f3ec typed LRT) with CHILD-FLOP leaf targets (domain_spatial_spine.child_insertion "
               "boundary_record: wtn/ck 141.6, h16c ck_head 303.1 / ck_pm0 15.2 / ck_pm1 14.6 ps from the closed records) "
               "so each hard child's boundary flops are balanced with its root's soft flops (clock_rule at child flops).")
    s['job'].update(owner='STEWARD-QK/SQ-TTC4', branch='claude/sq-ttc4-safe15-1021', tag=tag, purpose=purpose)
    s['structural_recut_status'] = purpose
    (kd / 'spec.json').write_text(json.dumps(s, indent=1) + '\n')
    for f in ('lcr_dissolve_after_gpl.tcl', 'lp_cone_regions.tcl', 'assigned_pins.tcl'):
        (kd / f).write_text((sd / f).read_text().replace(f'qfd_tt_ctlm_dv_{src}', f'qfd_tt_ctlm_dv_{tag}'))
    print(tag, s['outline'])
