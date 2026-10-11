#!/usr/bin/env python3
"""Write the v2 layer-die control-plane binding manifest (s81-ctl-1011): physical/s81_ctrl/bindings/layer_v2.json.
Endpoints name hub slab keys of tools/dsrom_s81_fulldie.py (m['hub'][key]) or TOP (die pins); the generator resolves
them under --ctrl-slab --ctrl-adapters.  Re-run after any pinned RTL change (shas)."""
import hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from s81_ctrl.die_binding_contract import validate_manifest_v2, ENGINE_INDEX  # noqa: E402
sha = lambda rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
CTRL = 'rtl/dsrom_sys/s81_ph/ctrl_c/'
EP = dict(queue_depth=8, credit_return='done', endpoint='ot_s81_slab_ep (c_cmd 85 / c_done 9 / c_st 2)')
engines = dict(
    fld=dict(status='BOUND', slab='gather', master='dsfd_sp_gather_c', master_rtl=CTRL + 'dsfd_sp_gather_c.sv',
             clock_domain='stream_1p2', descriptor='arg[9:0] = field phase id',
             start='releases the staged VM phase word (f_vm kind 0) to the capture + t_xgo {v, phase} to the x source',
             done='dsfd_sp_capture_c t_cd drained event of that phase (every root quota written)',
             pq_dies='--pq-place: the PQ core master (sp_pq) is the field issuer; no RTL yet -> fld UNBOUND on PQ dies',
             **EP),
    su=dict(status='PENDING', owner='s81-suhc-1011', slab='su_s / su_n', clock_domain='serial_0p9'),
    hc=dict(status='PENDING', owner='s81-suhc-1011', slab='hc_s / hc_n', clock_domain='serial_0p9'),
    coll=dict(status='PENDING', owner='s81-ctl-1011', slab='collective', clock_domain='stream_1p2',
              note='done = last result record of the collective landed toward the VM (t_vm record stream)'),
    svc=dict(status='PENDING', owner='s81-ctl-1011', slab='svc_<stack>', clock_domain='stream_1p2'),
    sel=dict(status='BOUND', slab='selector', master='dsfd_bk_selector_c', master_rtl=CTRL + 'dsfd_bk_selector_c.sv',
             clock_domain='stream_1p2', descriptor='arg[7:0] = segment tag',
             start='arms the job ahead of its in-band (valid-only) scan data', done='selector DONE word, tag checked', **EP),
    col=dict(status='BOUND', slab='collector', master='dsfd_bk_collector_c', master_rtl=CTRL + 'dsfd_bk_collector_c.sv',
             clock_domain='stream_1p2', descriptor='arg[7:0] = job tag',
             start='arms the job ahead of its in-band frames', done='collector DONE word (all four stacks), tag checked', **EP),
    hop=dict(status='PENDING', owner='mtp-wfc-1010', slab='WFC kit (stage hand-off descriptor; hop_tx retired)',
             clock_domain='stream_1p2'),
    head=dict(status='ROLE_ABSENT', note='head-root dies only'),
    emb=dict(status='ROLE_ABSENT', note='source die only'),
    eng=dict(status='PENDING', owner='s81-ctl-1011', slab='eng (layer1e home dies; S001 / S029 route Engram ops)',
             clock_domain='stream_1p2'),
    spare=dict(status='ROLE_ABSENT', note='no production engine; stage programs route nothing here'))
for e, s in engines.items():
    s['index'] = ENGINE_INDEX[e]
T = lambda p: ['TOP', 'ctrl_' + p]
ports = {p: dict(endpoint=T(p), note='die cfg / status pin') for p in ('pw_v', 'pw_a', 'pw_d', 'prog_len', 'cfg_users',
                                                                         'flt', 'fvec', 'stk', 'snap')}
ports.update(i_v=dict(endpoint=['collective', 'c_rx_v']), i_r=dict(endpoint=['collective', 'c_rx_r']),
             i_d=dict(endpoint=['collective', 'c_rx_d']), i_l=dict(endpoint=['collective', 'c_rx_l']),
             vwe=dict(endpoint=['vm', 'vwe']), vwa=dict(endpoint=['vm', 'vwa']), vwd=dict(endpoint=['vm', 'vwd']))
man = dict(schema='opentallas.s81.ctrl-native-binding.v2', role='layer', shell='physical/s81_ctrl/rtl/dsfd_sp_ctrl_e.sv',
           shell_sha256=sha('physical/s81_ctrl/rtl/dsfd_sp_ctrl_e.sv'),
           adapter_rtl='rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv',
           adapter_sha256=sha('rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv'),
           endpoint_rtl='rtl/dsrom_sys/s81_ctrl/ot_s81_slab_ep.sv', endpoint_sha256=sha('rtl/dsrom_sys/s81_ctrl/ot_s81_slab_ep.sv'),
           ports=ports, engines=engines,
           nets=[dict(name='ctl_fld_cd', bits=12, driver=['capture', 't_cd'], load=['gather', 'f_cd']),
                 dict(name='ctl_fld_xgo', bits=11, driver=['gather', 't_xgo'], load=['vm', 'f_xgo'])],
           qualification='PARTIAL')
out = ROOT / 'physical/s81_ctrl/bindings/layer_v2.json'
out.write_text(json.dumps(man, indent=1) + '\n')
v = validate_manifest_v2(out, ROOT, 'layer')
man['qualification'] = v['qualification']; man['program_engines'] = v['program_engines']
out.write_text(json.dumps(man, indent=1) + '\n')
print(out, v['qualification'], v['program_engines'])
