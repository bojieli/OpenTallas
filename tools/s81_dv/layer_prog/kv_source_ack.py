"""Acknowledge one exact configured G9 KV source inventory; no lowering.

This helper emits no programme, dispatch, calendar or qualification changes.
An acknowledgement cannot authorize a physical view or runtime execution.
"""
import argparse
import hashlib
import json
from pathlib import Path

SELECTED_REF = '8a495768f02316a7a8ad2e2bafef2f4d3741b741'
MANIFEST_REF = '96043ef4d61dc3d08437186d48b46fbfd7331524'
MANIFEST_PATH = 'results/arch/s81_die72_1021/g9_assembly/minimal_configured_source_manifest.json'
MANIFEST_SHA256 = '120ce473f90bddeb40ee35c4fe28cf7ec3ab3b127f46fc95351d97cf4da66b75'
BASE = 'rtl/dsrom_sys/s81_dv/slice/'
SOURCE_SHA256 = {
    BASE+'ot_s81sl_slice_kv512.sv': 'e7e7d43950382920837e2fd553e384690338ed6f4343a7cfb83f2ea796137319',
    BASE+'ot_s81sl_slice.sv': '9f37084c7bfb27fc3c7b1a658b035c518544517f5f3b98d598228356b2daffa8',
    BASE+'ot_s81sl_kv_bank.sv': '0780e97491e2360d26acaa16a2ad1c3306ebdefe96ec1491dd159f2e8b76e718',
    BASE+'ot_s81sl_kv_leaf.sv': '39ed5129d66b27921c89fa2f836733913e8d26725227264af5b60158ef72bf81',
}
CHILD_PARAMS = dict(HB=0, DL=4, DR=6, DX=6, VQ_XMEM=2, KV_ENABLE=1, VS_MUT=0)


def acknowledge(source_root, instance, master, params):
    """Fail closed on identity, parameter or exact configured-source changes."""
    root = Path(source_root).resolve()
    record = dict(schema='opentallas.s81.kv_source_ack.v1', status='REJECTED',
        selected_source_ref=SELECTED_REF, source_root=str(root),
        instance=instance, master=master, top_params=params,
        source_sha256={}, expected_source_sha256=SOURCE_SHA256,
        source_manifest=dict(ref=MANIFEST_REF, path=MANIFEST_PATH, sha256=MANIFEST_SHA256),
        programme_emitted=False, calendar_rows_emitted=0, status_counts_changed=False,
        producer_qualified=False, lifetime_qualified=False, runtime_qualified=False,
        physical_binding_qualified=False, physical_master_status='UNBOUND')
    if instance != 'u_s_3N' or master != 'ot_s81sl_slice_kv512':
        return dict(record, reason='requires designated u_s_3N with exact unique KV512 master')
    if type(params) is not dict or params:
        return dict(record, reason='unique top is parameter-free: explicit top params {} required')
    for name, expected in SOURCE_SHA256.items():
        path = root/name
        try:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            return dict(record, reason='missing selected source: '+name)
        record['source_sha256'][name] = actual
        if actual != expected:
            return dict(record, reason='selected source hash mismatch: '+name)
    return dict(record, status='ACK_SOURCE_ONLY', child_instance='u_slice',
        configured_child_master='ot_s81sl_slice', configured_child_params=CHILD_PARAMS,
        enabled_bank_path='u_s_3N.u_slice.lf[0].u_lf.g_kv.u_kv',
        clock_reset_contract=dict(wrapper_clk='clk -> u_slice.clk unchanged',
            wrapper_reset='rst_n -> u_slice.rst_n unchanged',
            forwarded_clock_ports=['ck_line[15:0]', 'ck_v[1:0]', 'ck_xc[15:0]', 'ck_rt[7:0]'],
            wrapper_added_state=0, wrapper_added_logic=0, wrapper_added_edges=0,
            qualification='exact transparent source wrapper only; actual clock/reset/runtime qualification remains open'),
        holds=['actual producer CAP/gather and operand/parameter transport',
               'source-owned position/identity and finite row lifetimes',
               'actual fixed programme/commit/retirement dates',
               'physical views for this distinct configured master and actual clocks/resets'],
        qualification='Source identity acknowledgement only. Existing 50PARTIAL/5GAP compiler receipt unchanged.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root', required=True)
    p.add_argument('--instance', required=True)
    p.add_argument('--master', required=True)
    p.add_argument('--params-json', required=True)
    a = p.parse_args()
    record = acknowledge(a.source_root, a.instance, a.master, json.loads(a.params_json))
    print(json.dumps(record, indent=2))
    return int(record['status'] != 'ACK_SOURCE_ONLY')


if __name__ == '__main__':
    raise SystemExit(main())
