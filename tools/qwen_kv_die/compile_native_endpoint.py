#!/usr/bin/env python3
"""Declared external compiler for a native attention static-controller programme.

Only descriptor/control/calendar data is emitted. No internal result, memory row,
Q, K, V or expected answer is generated. The HOST remains the identity authority.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/qwen_attention_native'))
import attn_calendar as AC

# Actual packed qfd_tt_ctlm_s descriptor checked by native59_command_guard.
FIELDS = [(24,0),(1,0),(1,0),(1,1),(1,1),(24,1),(24,1),(24,3167),(1,0),(24,0),(4,0),(3,0),
          (24,0),(24,0),(24,1),(24,13696),(24,0),(24,0),(24,0),(24,0),(1,1),(18,128),(18,1),(18,512),(1,1)]

def compile_programme(epoch, token, position, layer, rx_cmd):
    if not (0 <= epoch < 65536 and 0 <= token < 151936 and 0 <= position < 8192 and 0 <= layer < 36):
        raise ValueError('HOST identity outside native59 bounds')
    if type(rx_cmd) is not int or rx_cmd < 2:
        raise ValueError('CMD slot must follow independent programme load/run')
    command = 0
    for width, value in FIELDS:
        command = (command << width) | value
    assert sum(w for w,_ in FIELDS) == 380
    tag = (epoch << 43) | ((layer+1) << 37) | (token << 19) | (position << 6)
    c = AC.calendar(position+1, pv='w16', head_g3s2=True)
    n = AC.service_cycles(c)
    # Native service result serializer: last-result cycle = start_qk + N,
    # 32 consecutive beats. Actual input CMD capture -> start_qk is 2 edges.
    first = rx_cmd + 2 + n - 31
    if first+34 >= 65536:
        raise ValueError('16-bit controller timeline overflow')
    source_paths = ['tools/qwen_attention_native/attn_calendar.py',
                    'rtl/qwen_sys/split_20261014/qkd_native59_command_guard.sv',
                    'rtl/qwen_sys/split_20261014/qkd_native59_descriptor_producer.sv',
                    'rtl/qwen_sys/split_20261014/qkd_native_attention_static_ctl.sv',
                    'rtl/qwen_sys/split_20261014/qkd_native_attention_programme.sv']
    return dict(schema=1, authority=dict(epoch=epoch, token=token, position=position, stage=layer+1),
                descriptor_hex=f'{command:095x}', tag_hex=f'{tag:015x}',
                calendar_hex=AC.hexcal(c), compiled_rx_cmd=rx_cmd, compiled_tx_first=first, compiled_end=first+34,
                start_qk=rx_cmd+2, q_first=rx_cmd+3, q_last=rx_cmd+34,
                result_last=first+31, result_done=first+32, reserved_idle=first+32, status=first+33,
                service_edges=n, service_binding=dict(head='G3S2', HXK=13, AGE=34, RL=21, pv='w16'),
                sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source_paths},
                native_full_layer=False, native_full_token=False,
                required_producers=['HOST authority', 'actual native service and K/V memory ports',
                                    'programme loader/run', 'electrical link slots', 'physical clock/pins'])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('epoch','token','position','layer','rx-cmd'):
        p.add_argument('--'+name,type=int,required=True)
    a=p.parse_args()
    print(json.dumps(compile_programme(a.epoch,a.token,a.position,a.layer,a.rx_cmd),indent=2))
if __name__=='__main__':
    main()
