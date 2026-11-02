#!/usr/bin/env python3
"""Read-only current native transport re-age; never rewrite a programme."""
import argparse
import json
import os
from pathlib import Path
import sys
from collections import Counter


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'tree', 'manifest', 'bind', 'previous', 'out'):
        p.add_argument('--' + name, required=True, type=Path)
    p.add_argument('--selection-manifest', type=Path,
                   help='source-root assembly equivalent to the staged bind manifest')
    p.add_argument('--selection-root', type=Path,
                   help='private complete copy of selected files when source checkout is sparse')
    a = p.parse_args()
    assert not a.out.exists(), 'preserve prior verdicts'
    selection_root = a.selection_root or a.source
    os.environ['OT_S81_SELECTED_SOURCE_ROOT'] = str(selection_root)
    selection = a.selection_manifest or a.manifest
    manifest_join = None
    if a.selection_manifest:
        staged = json.loads(a.manifest.read_text())
        source = json.loads((selection_root / selection).read_text())
        # The compiler resolves modules; it does not consume placement maps or
        # clock sidecars here. Actual ages come only from the strict bind.
        relocated = {'base', 'clock_landing_table', 'map_file'}
        differences = sorted(k for k in staged.keys() | source.keys()
                             if staged.get(k) != source.get(k))
        assert set(differences) <= relocated, 'staged bind selects different source assembly'
        manifest_join = dict(source_selection=str(selection),
                             source_selection_root=str(selection_root),
                             identical_except_relocated_paths=differences,
                             actual_ages_from_strict_bind=True)
    os.environ['OT_S81_SELECTED_ASBUILT_MANIFEST'] = str(selection)
    os.environ['OT_S81_SELECTED_CHILD_FILES'] = ','.join([
        'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv',
        'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv'])
    for rel in ('tools', 'tools/s81_dv', 'tools/s81_dv/layer_prog'):
        sys.path.insert(0, str(a.source / rel))
    import dv_layer_compile as C
    from layer_prog import bound_data as B
    die = C.Die(a.tree)
    bind = B.load_bind(a.bind, str(a.manifest), a.source)
    current = B.rebind_links(die, bind)
    previous = json.loads(a.previous.read_text())
    changed, newly_blocked, newly_pass = [], [], []
    for name, row in current['rows'].items():
        before = previous['rows'].get(name)
        if before is None:
            continue
        if row['status'] == before['status'] == 'PASS':
            if row['bound_age'] != before['bound_age']:
                changed.append(dict(link=name, previous=before['bound_age'],
                                    current=row['bound_age'], delta=row['bound_age']-before['bound_age'],
                                    lanes=row.get('lanes', [])))
        elif before['status'] == 'PASS':
            newly_blocked.append(dict(link=name, previous=before['bound_age'], reason=row['reason']))
        elif row['status'] == 'PASS':
            newly_pass.append(dict(link=name, current=row['bound_age'], previous_reason=before['reason']))
    summary = dict(status='CURRENT_NATIVE_TRANSPORT_REAGE_ONLY', verdict=current['verdict'],
                   current_counts=current['counts'], previous_counts=previous['counts'],
                   same_link_identity=current['rows'].keys()==previous['rows'].keys(),
                   changed_pass_links=changed, newly_blocked=newly_blocked, newly_pass=newly_pass,
                   blocked_reason_counts=dict(Counter(r.get('reason','').split(':')[0]
                       for r in current['rows'].values() if r['status']!='PASS')),
                   previous_bind=previous['bind_dir'], current_bind=current['bind_dir'],
                   source_selection_join=manifest_join,
                   current_plan=current['bind_provenance'].get('plan'),
                   source_programme_rewritten=False, production_enabled=False, added_RTL_cycles=0,
                   scope=current['scope'])
    a.out.mkdir(parents=True)
    (a.out/'bound_data_links.json').write_text(json.dumps(current,indent=2)+'\n')
    (a.out/'comparison.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:summary[k] for k in ('status','verdict','current_counts','previous_counts')}),flush=True)
    print('changed',len(changed),'newly blocked',len(newly_blocked),'newly pass',len(newly_pass),flush=True)


if __name__=='__main__':
    main()
