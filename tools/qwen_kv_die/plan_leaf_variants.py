#!/usr/bin/env python3
"""KV-P3-LEAF 10-23: source-level plan variants of the KV-die leaves whose ports are constant straps in the as-built die.

The top-down KV die plan binds every leaf port by name and never generates a constant.  13,082 leaf-input bits of the
as-built die (case_kv/die.v @ e33504a6f) are constant straps.  Two classes are removed here at SOURCE level (the original
leaf files are untouched; they have many other users):

  class A  per-content parameter: the port declaration becomes a parameter of the same width named in upper case and the
           body reads the parameter (variant name = original + "_p");
  class C  chain-head form: the first element of a chain has no predecessor; the predecessor ports are removed from the
           port list and the body sees them as a zero localparam of the same name and width (variant = original + "_head").
           The predecessor terms enter only through pin registers / child ports whose cones are shared with the live
           terms, so pruning them by hand would fork the body (or the child modules); the zero localparam is folded by
           the synthesiser and the generated text stays a mechanical function of the original;
  eo       qkd_astk_ep_s's EXP-offset strap eo = EO_E e + EO_RL (e + e / 2) (qkd_astk_strip_st: 9 e + RL (e + e / 2),
           RL = 3 in the release strip) is computed in the leaf from the row e = sq[2:0] (sq = {st, e} stays an input,
           delivered by a plan ID lane); the eo port is removed.

Every variant is a pure text transform of the original module (header re-emitted one port per line, body verbatim with
identifier substitution outside comments).  The generator also writes the equivalence benches
(rtl/test/kv_plan_leaves_1023/).

usage: plan_leaf_variants.py [--check]     --check: regenerate in memory, exit 1 unless byte-identical to the tree
"""
import argparse
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = 'rtl/qwen_sys/kv_plan_leaves_1023'
TBD = 'rtl/test/kv_plan_leaves_1023'
NCYC = 2400

ASTK_LIBS = ['rtl/hdc/ot_hdc_delay.sv', 'rtl/hdc/ot_hdc_fp32_add_lat.sv', 'rtl/hdc/ot_hdc_fp32_add_lat_nr.sv',
             'rtl/hdc/ot_hdc_prefix.sv', 'rtl/hdc/ot_hdc_fastfp.sv', 'rtl/hdc/ot_hdc_fp32_mul_lat.sv',
             'physical/qkd_astk_strip/macros/ot_sram_1r1w_256x128_m1_r2c2/ot_sram_1r1w_256x128_m1_r2c2.v',
             'physical/qkd_astk_strip/macros/ot_sram_1r1w_64x128_m1_r2c2/ot_sram_1r1w_64x128_m1_r2c2.v']
PCPATH_LIBS = ['rtl/qwen_sys/static_embedding_20261014/' + n + '.sv' for n in (
    'qkd_kv_pc_chain_station_b', 'qkd_static_kv_pc_es_merge_b', 'qkd_static_kv_pc_es_merge',
    'qkd_embedding_static_map')] + ['rtl/qwen_sys/static_kv_20261014/' + n + '.sv' for n in (
        'qkd_static_kv_pc_path_nc', 'qkd_ctrl_pc_nc', 'ot_qkd_static_ctrl_pc_emb', 'ot_qkd_static_kv_timing',
        'qkd_ctrl_pc_host_static_core', 'ot_qkd_static_emb_cdc', 'qkd_static_kv_write_observer', 'qkd_ctrl_pc_children',
        'qkd_controller_hbm_calendar', 'qkd_static_kv_return_calendar', 'qkd_static_kv_return_slots_mc',
        'qkd_kv_hbm_elastic_front_mc')] + [
    'rtl/qwen_sys/kv_die_20261009/ot_qkvd_kcmd_tap.sv', 'rtl/lib/ot_async_fifo.sv', 'rtl/lib/ot_reset_sync.sv',
    'rtl/qwen_sys/host_20261013/qkd_host_static_pc.sv', 'rtl/qwen_sys/q5_20261009/ot_qfd_kv_landing_ecc.sv']

TILE_SRC = 'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_hl_mu_ba_n32_pj.sv'
GRP_LIBS = ['physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
            'rtl/lib/ot_async_fifo.sv', 'rtl/lib/ot_reset_sync.sv'] + ['rtl/qwen_sys/static_kv_20261014/' + n + '.sv' for n in (
                'qkd_kv_cfault_tree', 'qkd_kv_front_cal', 'qkd_kv_landing_cal', 'qkd_static_kv_boot_cdc',
                'qkd_static_kv_hop', 'qkd_static_kv_landing', 'qkd_static_kv_landing_seg', 'qkd_static_kv_ownership',
                'qkd_static_kv_phase_launch')]

# ep_s: rare starts and small EXP base ages so the schedule trigger / calendar check (exp_age = cal_exp + eo) fire
EP_BIAS = ['i_qi[0] = ($urandom % 64) == 0;', "i_cal_exp = 16'($urandom % 48);"]
# name: variant module; src/module: the original; die: the as-built die master(s) and port names; param: [(port, NAME)];
# head: removed predecessor ports; eo: eo computed from sq; ov: the parameter overrides the die (or its tile) uses;
# vals: class-A values benched (from strap_values_rtl6.json), mut: the mutant value (must FAIL); libs: bench sources.
VARIANTS = [
    dict(name='ot_qkh_lane8_p', src='rtl/hdc/nearhbm/ot_qkh_subtiles.sv', module='ot_qkh_lane8',
         die='ot_qkh_lane8.bsel', param=[('bsel', 'BSEL')], vals=[[0], [1], [2], [3]], mut=[[2], [1]],
         libs=['rtl/lib/ot_rst_relay.sv', 'rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv'] + ASTK_LIBS[:5]),
    dict(name='ot_qkh_head_frontq_native_p', src='rtl/qwen_sys/split_20261014/ot_qkh_head_native_r4.sv',
         module='ot_qkh_head_frontq_native', die='ot_qkh_head_frontq_native.hid', param=[('hid', 'HID')],
         ov={'Q_FP32': '1', 'MUT': '0'}, vals=[[0], [1], [2], [3]], mut=[[3], [0]],
         libs=['rtl/lib/ot_rst_relay.sv', 'rtl/hdc/nearhbm/ot_qwen_nearhbm_head_hs.sv']),
    dict(name='ot_qwen_tp8_pv_wide_ctl_tbf_p', src='rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_ctl_tbf.sv',
         module='ot_qwen_tp8_pv_wide_ctl_tbf', die='ot_qwen_tp8_pv_wide_ctl_tbf.pair_id', param=[('pair_id', 'PAIR_ID')],
         ov={'FIRST_INPUT_AGE': '127', 'END_FLOOR': '1', 'RESET_PIN': '1', 'MUT': '0', 'TRUNK_D': '54', 'FLAG_D': '58'},
         vals=[[0], [1]], mut=[[0], [1]], libs=['rtl/lib/ot_rst_relay_bounded32.sv']),
    dict(name='qkd_astk_ctl_s_p', src='rtl/qwen_sys/split_20261014/qkd_astk_static_leaves.sv', module='qkd_astk_ctl_s',
         die='qkd_astk_ctl_s.st', param=[('st', 'ST')], ov={'Z_STRIDE': '4'}, vals=[[0], [1], [2], [3]], mut=[[1], [0]],
         libs=ASTK_LIBS),
    dict(name='qkd_astk_zn_p', src='rtl/qwen_sys/kv_die_20261009/qkd_astk_leaves.sv', module='qkd_astk_zn',
         die='qkd_astk_zn.zc (zn_1..3)', param=[('zc', 'ZC')], vals=[[4], [9], [15]], mut=[[4], [5]], libs=ASTK_LIBS),
    dict(name='qkd_astk_zn_head_p', src='rtl/qwen_sys/kv_die_20261009/qkd_astk_leaves.sv', module='qkd_astk_zn',
         die='qkd_astk_zn.zc + fi (zn_0)', param=[('zc', 'ZC')], head=['fi'], vals=[[0], [3]], mut=[[0], [8]],
         libs=ASTK_LIBS),
    dict(name='qkd_astk_ep_s_e', src='rtl/qwen_sys/split_20261014/qkd_astk_static_leaves.sv', module='qkd_astk_ep_s',
         die='qkd_astk_ep_s.eo (ep_1..7)', eo=True, bias=EP_BIAS, libs=ASTK_LIBS),
    dict(name='qkd_astk_ep_s_head_e', src='rtl/qwen_sys/split_20261014/qkd_astk_static_leaves.sv',
         module='qkd_astk_ep_s', die='qkd_astk_ep_s.eo + xi + zi (ep_0)', eo=True, head=['xi', 'zi'], bias=EP_BIAS, libs=ASTK_LIBS),
    dict(name='qkd_astk_er_owner_st_head', src='rtl/qwen_sys/split_20261014/qkd_astk_er_owner_st.sv',
         module='qkd_astk_er_owner_st', die='qkd_astk_er_owner_st.prev_* (owner_0)', ov={'N': '4'},
         head=['prev_v', 'prev_addr', 'prev_data', 'prev_fault'], libs=[]),
    dict(name='qkd_host_pc_slice_die_head', src='rtl/qwen_sys/split_20261014/qkd_host_pc_slice_die.sv',
         module='qkd_host_pc_slice_die', die='qkd_hslice / qkd_hslice_dn chain head (hsl_*S_31, hsl_*N_0)',
         head=['ci', 'ai', 'fault_i', 'ski', 'sdi', 'soi', 'sfi'],
         libs=['rtl/qwen_sys/split_20261014/qkd_host_pc_slice.sv', 'rtl/qwen_sys/host_20261013/qkd_host_ingest_station.sv',
               'rtl/qwen_sys/host_20261013/qkd_host_static_pc_emback.sv',
               'rtl/qwen_sys/split_20261014/qkd_hbm_boot_static_completion.sv',
               'rtl/qwen_sys/split_20261014/qkd_hbm_boot_static.sv', 'rtl/qwen_sys/split_20261014/qkd_hbm_boot_pc.sv',
               'rtl/qwen_sys/split_20261014/qkd_static_completion_ownerdemux.sv']),
    dict(name='qkd_static_kv_landing_seg_p', src='rtl/qwen_sys/static_kv_20261014/qkd_static_kv_landing_seg.sv',
         module='qkd_static_kv_landing_seg',
         die='qkd_kvs_grp_h_r2c.slg__cfg_group (r2c <- qkd_kvs_grp_h_r2 <- qkd_kvs_grp_h u_slg)',
         param=[('cfg_group', 'CFG_GROUP')], ov={'MUT': '0', 'HOP_MUT': '0'}, vals=[[4], [0]], mut=[[4], [5]],
         # cfg_group only feeds the sticky get-check fault, which random stimulus sets first through other checks: the
         # bench also compares the four landing PCs' group pin registers (internal probes)
         probes=[f'g_pc[{q}].u_pc.group_q' for q in range(4)],
         libs=['rtl/qwen_sys/static_kv_20261014/qkd_static_kv_hop.sv',
               'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_landing.sv',
               'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']),
    dict(name='qkd_static_kv_pc_path_fan_nc_b_head_p',
         src='rtl/qwen_sys/static_embedding_20261014/qkd_static_kv_pc_path_fan_nc_b.sv',
         module='qkd_static_kv_pc_path_fan_nc_b',
         die='qkd_kvs_pc_h.pc__pc + pc__fi (tile qkd_kvs_pc_h u_pc)', param=[('pc', 'PC')], head=['fi'],
         children=[dict(inst='u_chain', module='qkd_kv_pc_chain_station_b', new='qkd_kv_pc_chain_station_b_p',
                        params={'PC': 'PC'}, drop={'pc': 'PC'})],
         ov={'MU': '1'}, vals=[[0], [17]], mut=[[0], [1]], libs=PCPATH_LIBS + [f'{OUT}/qkd_kv_pc_chain_station_b_p.sv']),
    # u_chain of the pc_path head: its pc strap pin register spc (kept) becomes the folded PC parameter
    dict(name='qkd_kv_pc_chain_station_b_p', src='rtl/qwen_sys/static_embedding_20261014/qkd_kv_pc_chain_station_b.sv',
         module='qkd_kv_pc_chain_station_b', die='u_chain.pc of every pc_path (tile pc__pc)', param=[('pc', 'PC')],
         ov={'MUT': '0'}, vals=[[0], [5], [17]], mut=[[0], [1]], probes=['spc'], libs=[]),
    # TILE level (KV-P3b-TILE 10-23): the as-built die masters.  qkd_kvs_pc_h comes from ..._n32_pj_nc32.sv (gen_source_ports
    # @ e33504a6f); its module text is byte-identical to the one in ..._n32_pj.sv used here.  qkd_kvs_grp_h_r2c is the mapped
    # structural copy (kv_grp_safe5.py) of qkd_kvs_grp_h_r2 (qkd_kvs_grp_r2.sv) whose u_core is qkd_kvs_grp_h of ..._n32_pj.sv.
    dict(name='qkd_kvs_pc_h_head_p', src=TILE_SRC, module='qkd_kvs_pc_h',
         die='qkd_kvs_pc_h.pc__pc (0) + pc__fi (chain head kvpc_*_0)', param=[('pc__pc', 'PC')], head=['pc__fi'],
         children=[dict(inst='u_pc', module='qkd_static_kv_pc_path_fan_nc_b', new='qkd_static_kv_pc_path_fan_nc_b_head_p',
                        params={'PC': 'PC'}, drop={'pc': 'PC', 'fi': 'pc__fi'})],
         vals=[[0], [17]], mut=[[0], [1]], probes=['u_pc.u_chain.spc'],
         libs=PCPATH_LIBS + ['rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_return_head.sv',
                             'rtl/qwen_sys/static_embedding_20261014/qkd_static_kv_pc_path_fan_nc_b.sv',
                             f'{OUT}/qkd_static_kv_pc_path_fan_nc_b_head_p.sv', f'{OUT}/qkd_kv_pc_chain_station_b_p.sv']),
    dict(name='qkd_kvs_grp_h_p', src=TILE_SRC, module='qkd_kvs_grp_h',
         die='qkd_kvs_grp_h.slg__cfg_group (u_core of qkd_kvs_grp_h_r2 -> r2c)', param=[('slg__cfg_group', 'CFG_GROUP')],
         children=[dict(inst='u_slg', module='qkd_static_kv_landing_seg', new='qkd_static_kv_landing_seg_p',
                        params={'CFG_GROUP': 'CFG_GROUP'}, drop={'cfg_group': 'CFG_GROUP'})],
         vals=[[4], [0]], mut=[[4], [5]], probes=[f'u_slg.g_pc[{q}].u_pc.group_q' for q in range(4)],
         libs=GRP_LIBS + [f'{OUT}/qkd_static_kv_landing_seg_p.sv']),
    dict(name='qkd_kvs_grp_h_r2_p', src='rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_grp_r2.sv', module='qkd_kvs_grp_h_r2',
         die='qkd_kvs_grp_h_r2c.slg__cfg_group (4; r2c = mapped copy of this module)',
         param=[('slg__cfg_group', 'CFG_GROUP')],
         children=[dict(inst='u_core', module='qkd_kvs_grp_h', new='qkd_kvs_grp_h_p', params={'CFG_GROUP': 'CFG_GROUP'},
                        drop={'slg__cfg_group': 'CFG_GROUP'})],
         vals=[[4], [0]], mut=[[4], [5]], probes=[f'u_core.u_slg.g_pc[{q}].u_pc.group_q' for q in range(4)],
         libs=[TILE_SRC] + GRP_LIBS + [f'{OUT}/qkd_kvs_grp_h_p.sv', f'{OUT}/qkd_static_kv_landing_seg_p.sv']),
]


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def split_code(text):
    """[(is_code, segment)] with // and /* */ comments separated"""
    out, i, n, start = [], 0, len(text), 0
    while i < n:
        if text.startswith('//', i) or text.startswith('/*', i):
            if i > start:
                out.append((True, text[start:i]))
            j = text.find('\n', i) if text[i + 1] == '/' else text.find('*/', i) + 2
            j = n if j < 0 or (text[i + 1] == '*' and j == 1) else j
            out.append((False, text[i:j]))
            i = start = j
        elif text[i] == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == '\\' else 1
            i = j + 1
        else:
            i += 1
    if start < n:
        out.append((True, text[start:]))
    return out


def strip_comments(text):
    return ''.join(s for c, s in split_code(text) if c)


def top_split(text):
    items, depth, cur = [], 0, ''
    for ch in text:
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        if ch == ',' and depth == 0:
            items.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur.strip():
        items.append(cur.strip())
    return items


def balanced(text, i):
    """index after the paren group that opens at text[i] == '('"""
    depth = 0
    for j in range(i, len(text)):
        depth += {'(': 1, ')': -1}.get(text[j], 0)
        if depth == 0:
            return j + 1
    raise ValueError('unbalanced')


def extract(src, module):
    text = (ROOT / src).read_text()
    m = re.search(r'^\s*module\s+' + module + r'\b', text, re.M)
    end = text.index('endmodule', m.end())
    mod = text[m.start():end + len('endmodule')].lstrip('\n')
    # header end: the first ';' outside comments
    pos = 0
    for code, seg in split_code(mod):
        if code and ';' in seg:
            hdr_end = pos + seg.index(';') + 1
            break
        pos += len(seg)
    header, body = strip_comments(mod[:hdr_end]), mod[hdr_end:]
    h = re.match(r'\s*module\s+\w+\s*', header)
    i = h.end()
    params = []
    if header[i] == '#':
        p0 = header.index('(', i)
        p1 = balanced(header, p0)
        params = top_split(header[p0 + 1:p1 - 1])
        i = p1
    q0 = header.index('(', i)
    ports, prefix = [], None
    for item in top_split(header[q0 + 1:balanced(header, q0) - 1]):
        item = ' '.join(item.split())
        mm = re.match(r'((?:input|output|inout)\b.*?)\s*(\w+)$', item)
        if mm:
            prefix = mm.group(1)
            name = mm.group(2)
        else:
            assert re.fullmatch(r'\w+', item), item
            name = item
        rng = re.search(r'\[[^\]]*\]', prefix)
        ports.append(dict(name=name, prefix=prefix, dir=prefix.split()[0], range=rng.group(0) if rng else ''))
    return mod, params, ports, body


def subst_body(body, mapping):
    out = []
    for code, seg in split_code(body):
        if code:
            for old, new in mapping.items():
                seg = re.sub(r'(?<![.\w$`])\b' + old + r'\b', new, seg)
        out.append(seg)
    return ''.join(out)


def code_balanced(text, i):
    """index after the paren group that opens at text[i] == '(' (parens inside comments ignored)"""
    pos, depth = 0, 0
    for code, seg in split_code(text):
        if code:
            for k, ch in enumerate(seg):
                if pos + k < i:
                    continue
                depth += {'(': 1, ')': -1}.get(ch, 0)
                if depth == 0:
                    return pos + k + 1
        pos += len(seg)
    raise ValueError('unbalanced')


def rebind_child(body, c):
    """child instance c['inst'] of c['module'] -> c['new'] with parameter overrides c['params'] {child param: expr}; its
    named connections c['drop'] {child port: expr} are removed (each must be connected to exactly that expression)"""
    code = strip_comments(body)
    pat = re.compile(r'(?<![\w.])' + c['module'] + r'(\s*#\s*\(.*?\))?\s+' + c['inst'] + r'\s*\(', re.S)
    assert len(pat.findall(code)) == 1, (c, 'instance not unique')
    m = pat.search(body)
    end = code_balanced(body, m.end() - 1)
    inst = body[m.end():end]
    for port, expr in c['drop'].items():
        conn = r'\.\s*' + port + r'\s*\(\s*' + re.escape(expr) + r'\s*\)'
        n_mid = len(re.findall(conn + r'\s*,\s*', inst))
        inst, k = re.subn(conn + r'\s*,\s*', '', inst) if n_mid else re.subn(r'\s*,\s*' + conn, '', inst)
        assert k == 1 and not re.search(r'\.\s*' + port + r'\s*\(', inst), (c, port, 'connection')
    ov = ', '.join(f'.{n}({e})' for n, e in c['params'].items())
    head = c['new'] + (m.group(1)[:-1].rstrip() + ', ' + ov + ')' if m.group(1) else ' #(' + ov + ')') + \
        body[m.start() + len(c['module']) + len(m.group(1) or ''):m.end()]
    return body[:m.start()] + head + inst + body[end:]


def unkeep(body, consts):
    """drop the keep attribute of registers whose every assignment is a constant (a replaced parameter / head localparam):
    a kept flop of a constant would be a tie cell again; unkept, synthesis folds it"""
    code = strip_comments(body)
    rhs = {}
    for mm in re.finditer(r'(?<![\w.])(\w+)\s*(?:\[[^\]]*\])?\s*<=\s*([^;]*);', code):
        rhs.setdefault(mm.group(1), []).append(mm.group(2))
    num = re.compile(r"\d*'[sS]?[bBhHdD][0-9a-fA-F_xXzZ]+|\d+")

    def const(e):
        ids = set(re.findall(r'[A-Za-z_]\w*', num.sub(' ', e)))
        return ids <= set(consts)
    folded = sorted(r for r, es in rhs.items() if any(set(re.findall(r'\w+', e)) & set(consts) for e in es)
                    and all(const(e) for e in es))
    out = []
    for line in body.split('\n'):
        mm = re.match(r'^(\s*)\(\*\s*keep[^)]*\*\)\s*(reg\s*(?:signed\s*)?(?:\[[^\]]*\])?)\s*([\w\s,]+);(.*)$', line)
        if mm:
            names = [n.strip() for n in mm.group(3).split(',')]
            f = [n for n in names if n in folded]
            if f:
                k = [n for n in names if n not in folded]
                line = (f'{mm.group(1)}{mm.group(2)} {", ".join(f)};   // constant (plan variant): not kept, folded'
                        + (f'\n{mm.group(1)}(* keep *) {mm.group(2)} {", ".join(k)};{mm.group(4)}' if k else ''))
        out.append(line)
    return '\n'.join(out), folded


def variant(v):
    mod, params, ports, body = extract(v['src'], v['module'])
    pmap = dict(v.get('param', []))
    heads = v.get('head', [])
    gone = set(pmap) | set(heads) | ({'eo'} if v.get('eo') else set())
    byname = {p['name']: p for p in ports}
    for n in gone:
        assert byname[n]['dir'] == 'input', (v['name'], n)
    for new in list(pmap.values()) + (['EO_E', 'EO_RL'] if v.get('eo') else []):
        assert not re.search(r'\b' + new + r'\b', strip_comments(mod)), (v['name'], new, 'name already used')
    src_text = (ROOT / v['src']).read_text()
    lines = ['`timescale 1ns/1ps',
             f'// GENERATED by tools/qwen_kv_die/plan_leaf_variants.py (KV-P3-LEAF 10-23) -- do not edit.',
             f'// {v["name"]}: plan variant of {v["module"]} ({v["src"]}, sha256 {sha(src_text)[:16]}).',
             f'// As-built die strap(s): {v["die"]}.']
    if pmap:
        lines.append('// class A: ' + ', '.join(f'port {p} -> parameter {n}' for p, n in pmap.items())
                     + ' (same width; the body reads the parameter).')
    if heads:
        lines.append('// class C chain head: predecessor ports ' + ', '.join(heads) + ' removed; the body sees them as a'
                     ' zero localparam of the same name (no predecessor), folded by synthesis.')
    used = set(re.findall(r'`(\w+)', strip_comments(mod)))
    for mm in re.finditer(r'^`ifndef\s+(\w+)\s*\n`define\s+\1\b[^\n]*\n`endif[^\n]*\n', src_text, re.M):
        if mm.group(1) in used:
            lines.append(mm.group(0).rstrip('\n'))   # the original file's default for a macro the module reads
    if v.get('eo'):
        lines.append('// eo: port removed; eo = EO_E e + EO_RL (e + e / 2), e = sq[2:0] (qkd_astk_strip_st: 9 e + RL'
                     ' (e + e / 2), RL 3).')
    ps = list(params)
    for p, n in pmap.items():
        rng = byname[p]['range'] or '[0:0]'
        ps.append(f'parameter {rng} {n} = 0')
    if v.get('eo'):
        ps += ['parameter integer EO_E = 9', 'parameter integer EO_RL = 3']
    lines.append(f'module {v["name"]} #(')
    lines += [f'    {p}{"," if k < len(ps) - 1 else ""}' for k, p in enumerate(ps)]
    keep = [p for p in ports if p['name'] not in gone]
    lines.append(') (')
    lines += [f'    {p["prefix"]} {p["name"]}{"," if k < len(keep) - 1 else ""}' for k, p in enumerate(keep)]
    lines.append(');')
    body = subst_body(body, pmap)
    for c in v.get('children', []):
        body = rebind_child(body, c)
        lines.insert(4, f'// child {c["inst"]}: {c["module"]} -> plan variant {c["new"]} #(' + ', '.join(
            f'.{n}({e})' for n, e in c['params'].items()) + '); connections ' + ', '.join(
            f'.{p}({e})' for p, e in c['drop'].items()) + ' removed.')
    for h in heads:
        if re.search(r'(?<![.\w$`])\b' + h + r'\b', strip_comments(body)):
            lines.append(f'    localparam {byname[h]["range"] or "[0:0]"} {h} = 0;   // chain head: no predecessor')
        else:
            lines = [ln.replace(f' {h} removed; the body sees them', f' {h} removed (read only by the rebound child, now in'
                                ' its head form: no localparam left); the body sees any other') for ln in lines]
    if v.get('eo'):
        lines.append('    wire [2:0] eo_e = sq[2:0];   // the strip row (sq = {st, e})')
        lines.append("    wire [7:0] eo = 8'(EO_E) * {5'd0, eo_e} + 8'(EO_RL) * ({5'd0, eo_e} + {6'd0, eo_e[2:1]});")
    body, folded = unkeep(body, list(pmap.values()) + heads)
    if folded:
        lines.insert(4, '// registers of a constant only (keep dropped where present; folded by synthesis, no tie cell): ' + ', '.join(folded) + '.')
    lines.append(body.rstrip('\n').lstrip('\n'))
    return '\n'.join(lines) + '\n', ports, params


def default_params(params, ov):
    """[(name, value)] of the integer parameters (defaults, die overrides)"""
    out = []
    for p in params:
        mm = re.match(r'(?:parameter\s+)?(?:integer\s+)?(\w+)\s*=\s*(.+)$', ' '.join(p.split()))
        out.append((mm.group(1), ov.get(mm.group(1), mm.group(2))))
    return out


CLOCK = re.compile(r'^(clk|ck|hck|ck_\w+|pll_\w+|\w+_hck|\w+_ck)$')
RESET = re.compile(r'^(rst_n|rsi|hrst|hrst_n|\w+_rst_n)$')


def bench(v, ports, params):
    """lockstep equivalence bench: original (straps / zero head inputs on the ports) vs the variant"""
    pmap = dict(v.get('param', []))
    heads = v.get('head', [])
    eo = v.get('eo')
    pv = default_params(params, v.get('ov', {}))
    np_ = len(pmap)
    t = ['`timescale 1ns/1ps', f'// GENERATED by tools/qwen_kv_die/plan_leaf_variants.py: {v["module"]} vs {v["name"]}.',
         '// Same random stimulus (incl. reset sequences) on every other input; every output compared every cycle.',
         '// TMUT 1 = mutant (class A: the original gets value MV; head: random predecessor inputs; eo: eo + 1).',
         f'module tb_{v["name"]} #(parameter integer TMUT = 0' +
         ''.join(f', parameter integer V{k} = 0, parameter integer MV{k} = 0' for k in range(np_)) +
         (', parameter integer SQV = 0' if eo else '') + ');']
    for n, val in pv:
        t.append(f'    localparam integer {n} = {val};')
    t += ['    reg clk = 0;', '    always #5 clk = ~clk;', '    reg rstv = 0;']
    ins = [p for p in ports if p['dir'] == 'input' and not CLOCK.match(p['name']) and not RESET.match(p['name'])]
    outs = [p for p in ports if p['dir'] != 'input']
    for p in ins:
        t.append(f'    reg {p["range"]} i_{p["name"]};')
    for p in outs:
        t.append(f'    wire {p["range"]} r_{p["name"]}, d_{p["name"]};')
    plist = ', '.join(f'.{n}({n})' for n, _ in pv)

    def conns(ref):
        c = []
        for p in ports:
            n = p['name']
            if CLOCK.match(n):
                c.append(f'.{n}(clk)')
            elif RESET.match(n):
                c.append(f'.{n}(rstv)')
            elif p['dir'] != 'input':
                c.append(f'.{n}({"r" if ref else "d"}_{n})')
            elif n in pmap:
                if ref:
                    k = list(pmap).index(n)
                    c.append(f'.{n}(TMUT ? MV{k} : V{k})')
            elif n in heads:
                if ref:
                    c.append(f'.{n}(TMUT ? i_{n} : 0)')
            elif n == 'eo' and eo:
                if ref:
                    c.append(f".{n}(8'(9 * (SQV % 8) + 3 * ((SQV % 8) + (SQV % 8) / 2) + TMUT))")
            else:
                c.append(f'.{n}(i_{n})')
        return ', '.join(c)
    dparams = plist + ''.join(f', .{n}(V{k})' for k, n in enumerate(pmap.values()))
    t.append(f'    {v["module"]} #({plist}) u_ref ({conns(True)});')
    t.append(f'    {v["name"]} #({dparams.lstrip(", ")}) u_dut ({conns(False)});')
    t += ['    integer cyc, errs, w;',
          '    task automatic drive;',
          '        begin']
    for p in ins:
        if eo and p['name'] == 'sq':
            t.append("            i_sq = 5'(SQV);")
            continue
        t.append(f'            for (w = 0; w < $bits(i_{p["name"]}); w = w + 32) i_{p["name"]} = '
                 f"{{i_{p['name']}, 32'($urandom)}};")
    t += ['            ' + b for b in v.get('bias', [])]
    t += ['        end', '    endtask', '    initial begin', '        errs = 0;',
          f'        for (cyc = 0; cyc < {NCYC}; cyc = cyc + 1) begin',
          '            @(negedge clk);',
          '            if (cyc > 0) begin']
    for p in outs:
        n = p['name']
        t += [f'                if (r_{n} !== d_{n}) begin errs = errs + 1;',
              f'                    if (errs <= 5) $display("MISMATCH cyc %0d {n} ref %h dut %h", cyc, r_{n}, d_{n}); end']
    for k, pr in enumerate(v.get('probes', [])):
        t += [f'                if (u_ref.{pr} !== u_dut.{pr}) begin errs = errs + 1;',
              f'                    if (errs <= 5) $display("MISMATCH cyc %0d probe {pr} ref %h dut %h", cyc, u_ref.{pr}, u_dut.{pr}); end']
    t += ['            end',
          '            rstv = !(cyc < 12 || (cyc >= 800 && cyc < 806) || (cyc >= 1700 && cyc < 1702));',
          '            drive;',
          '        end',
          f'        if (errs == 0) $display("PASS tb_{v["name"]} %0d cycles TMUT %0d", cyc, TMUT);',
          f'        else $display("FAIL tb_{v["name"]} %0d mismatches TMUT %0d", errs, TMUT);',
          '        $finish;', '    end', 'endmodule']
    return '\n'.join(t) + '\n'


def child_renames(v):
    """[(child variant, its original)] of every rebound child, recursively"""
    out = []
    for c in v.get('children', []):
        out.append((c['new'], c['module']))
        out += child_renames(next(w for w in VARIANTS if w['name'] == c['new']))
    return out


def run_script():
    s = ['#!/bin/bash',
         '# GENERATED by tools/qwen_kv_die/plan_leaf_variants.py: equivalence benches of the KV plan leaf variants.',
         '# usage: run.sh OUTDIR [J]   (Verilator 5.050; J parallel benches; every bench must PASS, every mutant must FAIL)',
         'set -u', 'R=$(cd "$(dirname "$0")/../../.." && pwd); OUT=${1:-/tmp/kv_plan_leaves_1023}; mkdir -p "$OUT"',
         'V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}',
         'NF=0; J=${2:-8}; rm -f "$OUT"/*.res',
         'one() {  # tag top srcs... -- gparams',
         '  local tag=$1 top=$2; shift 2; local src=() g=()',
         '  while [ "$1" != -- ]; do src+=("$R/$1"); shift; done; shift; g=("$@")',
         '  "$V" --binary -j 4 --timing -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module "$top" "${g[@]}" \\',
         '    -Mdir "$OUT/$tag" -o Vtb "${src[@]}" > "$OUT/$tag.build.log" 2>&1 || { echo "BUILD_FAIL $tag" | tee "$OUT/$tag.res"; return; }',
         '  "$OUT/$tag/Vtb" > "$OUT/$tag.log" 2>&1',
         '  local mut=0; case " ${g[*]} " in *" -G"*"MUT="[12]" "*) mut=1;; esac',
         '  { if [ $mut = 0 ]; then grep -q "^PASS" "$OUT/$tag.log" && echo "PASS   $tag $(grep -m1 ^PASS "$OUT/$tag.log")" || echo "FAIL   $tag"',
         '    else grep -q "^FAIL" "$OUT/$tag.log" && echo "CAUGHT $tag $(grep -m1 ^FAIL "$OUT/$tag.log")" || echo "MISSED $tag"; fi; } | tee "$OUT/$tag.res"',
         '  rm -rf "$OUT/$tag"',
         '}',
         'job() { while [ "$(jobs -rp | wc -l)" -ge "$J" ]; do wait -n; done; one "$@" & }']
    for v in VARIANTS:
        srcs = ' '.join([f'{TBD}/tb_{v["name"]}.sv', f'{OUT}/{v["name"]}.sv', v['src']] + v['libs'])
        top = f'tb_{v["name"]}'
        runs = []
        if v.get('param'):
            for vals in v['vals']:
                runs.append(('v' + '_'.join(map(str, vals)), ' '.join(f'-GV{k}={x} -GMV{k}={x}' for k, x in enumerate(vals))))
            good, bad = v['mut']
            runs.append(('mut', ' '.join(f'-GV{k}={g} -GMV{k}={b}' for k, (g, b) in enumerate(zip(good, bad))) + ' -GTMUT=1'))
        elif v.get('eo'):
            runs += [(f'e{e}', f'-GSQV={e}') for e in range(8)]
            runs.append(('mut', '-GSQV=5 -GTMUT=1'))
        else:
            runs += [('h', ''), ('mut', '-GTMUT=1')]
        for tag, g in runs:
            s.append(f'job {v["name"]}_{tag} {top} {srcs} -- {g}'.rstrip())
    s += ['lint() {  # name orig variant_file renames srcs...: -Wall warnings (code + message, locations dropped) of the variant;',
          '  # renames (sed): child plan variants -> their originals, so messages naming a child compare equal',
          '  local name=$1 orig=$2 vf=$3 rn=$4; shift 4; local src=(); for f in "$@"; do src+=("$R/$f"); done',
          '  "$V" --lint-only -Wall --top-module "$orig" "${src[@]}" 2>&1 | grep -E "^%(Warning|Error)" | sed -E "s/^(%[A-Za-z]+-?[A-Z0-9_]*): [^ ]+ /\\1 /" | sed "s/\\b$orig\\b/MOD/g" | sort -u > "$OUT/$name.lint_orig"',
          '  "$V" --lint-only -Wall --top-module "$name" "$R/$vf" "${src[@]}" 2>&1 | grep -E "^%(Warning|Error)" | sed -E "s/^(%[A-Za-z]+-?[A-Z0-9_]*): [^ ]+ /\\1 /" | sed "$rn" | sed "s/\\b$name\\b/MOD/g" | sort -u > "$OUT/$name.lint_var"',
          '  local new; new=$(comm -13 "$OUT/$name.lint_orig" "$OUT/$name.lint_var" | grep -v DECLFILENAME | wc -l); new=$((new + $(grep "^%Error" "$OUT/$name.lint_var" | grep -vc " due to ")))',
          '  if [ "$new" = 0 ]; then NL=$((NL+1)); echo "LINT   $name no new warnings ($(wc -l < "$OUT/$name.lint_orig") orig / $(wc -l < "$OUT/$name.lint_var") variant)"; else NF=$((NF+1)); echo "LINTNEW $name $new new warnings:"; comm -13 "$OUT/$name.lint_orig" "$OUT/$name.lint_var" | grep -v DECLFILENAME | head -5; fi',
          '}', 'NL=0']
    for v in VARIANTS:
        rn = ';'.join(f's/\\b{n}\\b/{o}/g' for n, o in child_renames(v)) or 's/^//'
        s.append(f'lint {v["name"]} {v["module"]} {OUT}/{v["name"]}.sv \'{rn}\' {" ".join([v["src"]] + v["libs"])}')
    for tag, g in (('h', ''), ('mut1', '-GMUT=1'), ('mut2', '-GMUT=2')):
        s.append(f'job ot_dp_id_{tag} tb_ot_dp_id {TBD}/tb_ot_dp_id.sv rtl/lib/ot_dp_id.sv -- {g}'.rstrip())
        s.append(f'job ot_dp_efault_{tag} tb_ot_dp_efault {TBD}/tb_ot_dp_efault.sv rtl/lib/ot_dp_efault.sv -- {g}'.rstrip())
    s.append('for c in "ot_dp_id_src rtl/lib/ot_dp_id.sv -GW=24" "ot_dp_id_add rtl/lib/ot_dp_id.sv -GW=40 -GK=-3" '
             '"ot_dp_id_rot rtl/lib/ot_dp_id.sv -GN=8 -GW=3" "ot_dp_efault rtl/lib/ot_dp_efault.sv -GN=3 -GAGE=6" '
             '"ot_dp_efault rtl/lib/ot_dp_efault.sv -GN=1 -GAGE=0"; do set -- $c; '
             'if "$V" --lint-only -Wall --top-module $1 "$R/$2" ${@:3} > "$OUT/lint_$1.log" 2>&1; '
             'then NL=$((NL+1)); echo "LINT   $* clean"; else NF=$((NF+1)); echo "LINTNEW $*"; fi; done')
    s += ['wait', 'NP=$(cat "$OUT"/*.res | grep -c "^PASS"); NM=$(cat "$OUT"/*.res | grep -c "^CAUGHT")',
          'NF=$((NF + $(cat "$OUT"/*.res | grep -vc "^PASS\\|^CAUGHT")))']
    s += ['echo "SUMMARY pass $NP mutants_caught $NM lint_clean $NL fail $NF"', '[ $NF = 0 ]']
    return '\n'.join(s) + '\n'


def outputs():
    files = {}
    for v in VARIANTS:
        text, ports, params = variant(v)
        files[f'{OUT}/{v["name"]}.sv'] = text
        files[f'{TBD}/tb_{v["name"]}.sv'] = bench(v, ports, params)
    files[f'{TBD}/run.sh'] = run_script()
    return files


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    bad = 0
    for rel, text in outputs().items():
        p = ROOT / rel
        if a.check:
            if not p.exists() or p.read_text() != text:
                print(f'STALE {rel}')
                bad += 1
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
            if rel.endswith('.sh'):
                p.chmod(0o755)
    if a.check:
        print('CHECK ' + ('FAIL' if bad else 'OK'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
