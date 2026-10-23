"""Exact archived dependency of the selected CLOSED KV rv5 view; canonical Q59 RTL is untouched."""
import hashlib
import json
from pathlib import Path

IDENTITY='rtl/qwen_sys/static_kv_die_20261017/rv5_frozen_1022/identity.json'
CANONICAL='rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv'
SELECTED='rtl/qwen_sys/static_kv_die_20261017/rv5_frozen_1022/qkd_native_attention_record.sv'
COMMIT='2cdc6bb28a6a757666f337936a674a49726ac210'
SHA256='8b05cb0bcd886af069d6d62026f05b3229edd568eab38ea97c92879ff6c425c0'


def selected_source_map(root, enabled, *, active, params, kit=None, master=None, source_commit=None):
    if not enabled:
        return {}
    if not active or params != {'RETIRE_STATIC': 1, 'STATUS_DELAY': 213}:
        raise ValueError('rv5 frozen source requires the exact selected KV rv5 parameters')
    if kit is not None and (kit, master) != ('qkd_kvs_attn_rv5', 'qkd_kvs_attn'):
        return {}
    if source_commit is not None and source_commit != COMMIT:
        raise ValueError('rv5 frozen source is not for this closed view commit')
    root=Path(root)
    identity=json.loads((root/IDENTITY).read_text())
    expected=dict(schema='opentallas.kv.rv5_selected_source.v1',kit='qkd_kvs_attn_rv5',master='qkd_kvs_attn',
                  source_commit=COMMIT,canonical_source=CANONICAL,selected_source=SELECTED,sha256=SHA256,
                  parameter_defaults={'KV_SIDE':1,'MUT':0},top_parameters={'RETIRE_STATIC':1,'STATUS_DELAY':213})
    if identity != expected or hashlib.sha256((root/SELECTED).read_bytes()).hexdigest() != SHA256:
        raise ValueError('rv5 archived source identity/default parameters changed')
    return {CANONICAL: SELECTED}
