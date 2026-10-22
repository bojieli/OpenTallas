"""Pure contract check against selected immutable G9 sources; no RTL execution."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import kv_source_ack as K


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    repo = Path(__file__).resolve().parents[3]
    def blob(ref, path):
        return subprocess.check_output(['git', '-C', str(repo), 'show', ref+':'+path])
    manifest = blob(K.MANIFEST_REF, K.MANIFEST_PATH)
    assert hashlib.sha256(manifest).hexdigest() == K.MANIFEST_SHA256
    selected = json.loads(manifest)
    assert selected['selected_source_ref'] == K.SELECTED_REF
    assert selected['tops']['kv'] == 'ot_s81sl_slice_kv512'
    assert selected['tops']['kv_top_params'] == {}
    assert selected['tops']['kv_child_params'] == K.CHILD_PARAMS
    for name, digest in K.SOURCE_SHA256.items():
        assert selected['explicit_override_sha256'][name] == digest
    cases = {}
    with tempfile.TemporaryDirectory(prefix='s81-kv-source-ack-') as tmp:
        root = Path(tmp)
        original = {}
        for name in K.SOURCE_SHA256:
            original[name] = blob(K.SELECTED_REF, name)
            path = root/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(original[name])
        def check(instance='u_s_3N', master='ot_s81sl_slice_kv512', params=None):
            return K.acknowledge(root, instance, master, {} if params is None else params)
        positive = check()
        cases['exact_selected_source'] = positive['status'] == 'ACK_SOURCE_ONLY'
        for name, kwargs in [('default_off_master', dict(master='ot_s81sl_slice')),
                             ('substring_is_not_identity', dict(master='ot_other_kv_master')),
                             ('top_override', dict(params={'KV_ENABLE': 1})),
                             ('wrong_slice', dict(instance='u_s_4N'))]:
            result = check(**kwargs)
            cases[name] = result['status'] == 'REJECTED' and not result['programme_emitted']
        for name in K.SOURCE_SHA256:
            path = root/name
            path.write_bytes(original[name]+b'\n// changed source\n')
            result = check()
            cases['changed_'+Path(name).stem] = result['status'] == 'REJECTED'
            path.write_bytes(original[name])
        bank = root/(K.BASE+'ot_s81sl_kv_bank.sv')
        bank.unlink()
        cases['missing_bank'] = check()['status'] == 'REJECTED'
        positive['source_root'] = 'temporary exact git source snapshot (removed after pure check)'
    assert all(cases.values()), cases
    assert positive['calendar_rows_emitted'] == 0 and positive['status_counts_changed'] is False
    assert not any(positive[k] for k in ['producer_qualified', 'lifetime_qualified',
                                       'runtime_qualified', 'physical_binding_qualified'])
    record = dict(status='PASS_PURE_SOURCE_ACK_CHECK', cases=cases, acknowledgement=positive,
                  code_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in [Path(__file__), Path(K.__file__)]},
                  source_snapshot_provenance=dict(source_ref=K.SELECTED_REF,
                      source_sha256=K.SOURCE_SHA256, manifest_ref=K.MANIFEST_REF,
                      manifest_path=K.MANIFEST_PATH, manifest_sha256=K.MANIFEST_SHA256),
                  simulation=False, compile=False, programme_changed=False,
                  prior_compiler_status_counts=dict(PARTIAL=50, GAP=5))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(record, indent=2)+'\n')
    print(record['status'])


if __name__ == '__main__':
    main()
