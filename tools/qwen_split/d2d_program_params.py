#!/usr/bin/env python3
"""Emit testbench timing constants from the actual compiler's 36-layer link image.

This is a component image playback proof; source-pinned native compute producers
and physical die paths are independently mandatory for whole-token qualification.
"""
import json
import sys
from pathlib import Path

def emit(calendar, out):
    d = json.loads(Path(calendar).read_text())
    p = d['program']; layer = p['layer']; first = p['token_run_L0']; starts = p['layers']
    assert len(starts) == 36 and d['phy'] == 5 and d['pinreg']
    assert p['host_relay_stages']['value'] == 0
    assert p['result_handoff']['visible_after_go'] == 483
    assert all(starts[i]['start'] < starts[i+1]['start'] for i in range(35))
    l0 = starts[0]['start']
    assert first['q_send'] - l0 == layer['q_send']
    rd = first['result_send'][0] - l0 - layer['result_send'][0]
    assert first['result_send'][1] - l0 - layer['result_send'][1] == rd
    params = dict(P_QS=layer['q_send'], P_RS=layer['result_send'][0], P_RE=layer['result_send'][1],
                  P_RDELTA=rd, P_ES=p['emb_send'][0], P_L0=l0,
                  P_FINISH=starts[-1]['start'] + starts[-1]['cycles'])
    od = Path(out); od.mkdir(parents=True, exist_ok=True)
    (od/'program_params.svh').write_text('\n'.join(f'localparam integer {k} = {v};' for k,v in params.items())+'\n')
    (od/'layer_starts.memh').write_text(''.join(f'{x["start"]:08x}\n' for x in starts))
    (od/'program_proof_scope.json').write_text(json.dumps(dict(parameters=params,
        expected=dict(attention_C_to_K=1188, attention_K_to_C=1188, kvn_words=144,
                      layer_results=36, host_checks=36, embedding_words=64, terminal_results=1),
        native_compute_qualification=False, physical_qualification=False), indent=2)+'\n')

if __name__ == '__main__': emit(*sys.argv[1:])
