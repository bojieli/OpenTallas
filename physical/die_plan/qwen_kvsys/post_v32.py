#!/usr/bin/env python3
"""KV-P3 10-23: plan v3.2 post-pass on the emitted plan (emit_v32.py output):
  - class A straps -> content parameters on the strap-free leaf variants (claude/kv-p3-leaf-1023 392d86eb2);
  - class C chain heads -> head-form variants (no predecessor ports);
  - astk eo -> computed from sq in qkd_astk_ep_s_e (EO_E 9, EO_RL 3);
  - synthetic ID / landing-check blocks of plan_v32 -> plan cells (rtl/lib/ot_dp_id.sv, ot_dp_efault.sv) with params;
  - census key -> v3.2 rows/map; note.
    python3 post_v32.py RAW_PLAN STAGE1 STRAPS > die_plan.json   (STRAPS = bind/v32_inputs.json.gz)"""
import gzip
import json
import re
import sys

P = json.load(open(sys.argv[1]))
S = json.load(gzip.open(sys.argv[2]))
ST = json.load(gzip.open(sys.argv[3]))['straps']
where = {k: tuple(v) for k, v in S['where'].items()}
inv = {v: k for k, v in where.items()}
PHYS = [4, 5, 0, 1, 2, 3, 6, 7]
SRC_LEAF = 'claude/kv-p3-leaf-1023 392d86eb2 rtl/qwen_sys/kv_plan_leaves_1023'
# class A: master.port -> (variant, PARAM)
A = {'ot_qkh_lane8.bsel': ('ot_qkh_lane8_p', 'BSEL'),
     'ot_qkh_head_frontq_native.hid': ('ot_qkh_head_frontq_native_p', 'HID'),
     'ot_qwen_tp8_pv_wide_ctl_tbf.pair_id': ('ot_qwen_tp8_pv_wide_ctl_tbf_p', 'PAIR_ID'),
     'qkd_astk_ctl_s.st': ('qkd_astk_ctl_s_p', 'ST'),
     'qkd_astk_zn.zc': ('qkd_astk_zn_p', 'ZC'),
     # tile wrappers: the strap lands on a child; the child variant exists (qkd_static_kv_landing_seg_p,
     # qkd_static_kv_pc_path_fan_nc_b_head_p), the tile-level variants below are OPEN (rtl generator of the tile)
     'qkd_kvs_grp_h_r2c.slg__cfg_group': ('qkd_kvs_grp_h_p', 'CFG_GROUP'),
     'qkd_kvs_pc_h.pc__pc': ('qkd_kvs_pc_h_head_p', 'PC')}
HEAD = {'qkd_astk_ep_s': 'qkd_astk_ep_s_head_e', 'qkd_astk_er_owner_st': 'qkd_astk_er_owner_st_head',
        'qkd_hslice': 'qkd_host_pc_slice_die_head', 'qkd_hslice_dn': 'qkd_host_pc_slice_die_head',
        'qkd_astk_zn': 'qkd_astk_zn_head_p', 'qkd_kvs_pc_h': 'qkd_kvs_pc_h_head_p'}
HEAD_PORTS = {'qkd_astk_ep_s': ('xi', 'zi'), 'qkd_astk_er_owner_st': ('prev_data',), 'qkd_astk_zn': ('fi',),
              'qkd_hslice': ('ci',), 'qkd_hslice_dn': ('ci',), 'qkd_kvs_pc_h': ('pc__fi',)}
heads = {i for mp, iv in ST.items() for i in iv
         if mp.split('.')[0] in HEAD_PORTS and mp.split('.')[1] in HEAD_PORTS[mp.split('.')[0]]}
stat = dict(params=0, heads=0, eo=0, id_cells=0, efault=0)


def sv(v):
    return f"{len(v)}'b{v}"


for tn, t in P['partition_types'].items():
    rep = re.search(r'representative (\S+)', t['note']).group(1)
    out = []
    for c in t['contents']:
        inst = inv.get((rep, c['inst']))
        m = c['module']
        if m == 'kvp_id_pc':
            row = int(rep.rsplit('_', 1)[1])
            q = rep.split('_')[1]
            cells = []
            if row == 0:          # chain start: stack from hroot (lane), row base + group table from the type
                cells += [dict(inst='u_id_row', module='ot_dp_id_src', params=dict(W=5, V="5'd0")),
                          dict(inst='u_id_grp', module='ot_dp_id_src',
                               params=dict(W=24, V="24'h" + format(sum(PHYS[(k + 1) % 8] << (3 * k) for k in range(8)), '06x')))]
            cells += [dict(inst=f'u_id_pc{j}', module='ot_dp_id_add', params=dict(W=5, K=j)) for j in range(4)]
            cells += [dict(inst='u_id_grp_rot', module='ot_dp_id_rot', params=dict(N=8, W=3))] if row else []
            if row < 7:
                cells += [dict(inst='u_id_next', module='ot_dp_id_add', params=dict(W=5, K=4))]
            for x in cells:
                out.append(dict(x, status='new', note='v3.2 counted ID lane (pc chain: stack 2 b | row4 5 b | PHYS '
                                                      'group table 8x3 b); rtl/lib/ot_dp_id.sv ' + SRC_LEAF.split()[1]))
            stat['id_cells'] += len(cells)
            continue
        if m in ('kvp_id_hg', 'kvp_id_hroot'):
            row = int(rep.rsplit('_', 1)[1]) if m == 'kvp_id_hg' else None
            cells = []
            if m == 'kvp_id_hg':
                if row == 0:
                    cells.append(dict(inst='u_id_row', module='ot_dp_id_src', params=dict(W=5, V="5'd0")))
                if row < 7:
                    cells.append(dict(inst='u_id_next', module='ot_dp_id_add', params=dict(W=5, K=1)))
            else:
                cells.append(dict(inst='u_id_stk', module='ot_dp_id_add', params=dict(W=2, K=0)))
            for x in cells:
                out.append(dict(x, status='new', note='v3.2 counted ID lane (' + ('astk chain position: sq / owner_id'
                                                       if m == 'kvp_id_hg' else 'quadrant stack id') + ')'))
            stat['id_cells'] += len(cells)
            continue
        if m == 'ot_dp_id_src':
            qq = re.search(r'u_idsrc_(\w\w)', c['inst']).group(1)
            st_ = {'WS': 0, 'WN': 1, 'ES': 2, 'EN': 3}[qq]
            out.append(dict(c, params=dict(W=2, V=f"2'd{st_}"), status='new',
                            note='v3.2: the only origin of the quadrant stack id (singleton hub partition)'))
            stat['id_cells'] += 1
            continue
        if m == 'ot_dp_efault':
            out.append(dict(c, status='new', params=dict(N='IN_LANES', AGE='REL_AGE'),
                            note='v3.2 plan landing check (replaces the qkd_landsh fault outputs): N = in-lane epochs, '
                                 'AGE = counted release age from the latency table (BINDER)'))
            stat['efault'] += 1
            continue
        c = dict(c)
        if inst:
            params = {}
            for mp, (var, par) in A.items():
                mm, pp = mp.split('.')
                if m == mm and inst in ST.get(mp, {}):
                    params[par] = sv(ST[mp][inst])
                    c['module'] = var
            if m == 'qkd_astk_ep_s':
                c['module'] = 'qkd_astk_ep_s_head_e' if inst in heads else 'qkd_astk_ep_s_e'
                params.update(EO_E=9, EO_RL=3)
                stat['eo'] += 1
            elif inst in heads:
                c['module'] = HEAD[m]
                stat['heads'] += 1
            if params:
                c['params'] = params
                stat['params'] += 1
            if c['module'] != m:
                c['note'] = (c.get('note', '') + f'; v3.2 strap-free variant of {m} ({SRC_LEAF})').lstrip('; ')
                c['status'] = 'rework'
        out.append(c)
    t['contents'] = out
P['census'] = [dict(rows='census/census_rows_v32.tsv.gz', map='census/census_map_v32.json',
                    note='as-built rtl6 e33504a6f (census_rows_v32.py): relays as leaves, ID lanes, landing checks + '
                         'fault chains; forward_via = plan tap-tree forwarders')]
P['note'] = ('Qwen KV/system die plan v3.2 (KV-P3 10-23) = v3.1 + generated-die blockers as plan objects: 128 PV '
             'T-chain qkd_rlyi_258s relays as pv contents (chain + select lanes), counted ID lanes (pc chain 31 b, '
             'astk chain 5 b, quadrant stack 2 b from hub_Wo/hub_Eo), strap-free leaf variants (params / chain-head '
             'forms), plan landing checks ot_dp_efault + per-column fault chains (hub OR tree re-derived), non-core '
             'clock regions + reset root in clocks_v32.json (PLAN-TOOL schema REQ). ' + P['note'])
json.dump(P, sys.stdout, indent=0)
print(json.dumps(stat), file=sys.stderr)
