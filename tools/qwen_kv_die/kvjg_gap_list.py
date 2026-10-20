#!/usr/bin/env python3
"""KVJ-G 2026-10-17 (kv_static_join_plan.md item 10): exact gap list of the Qwen KV die static join.

Two inputs, both measured, nothing guessed:
  1. the strict die port bind (tools/qwen_kv_die/kv_port_bind_v2.sh -> port_bind_v2.json) of the current split die.v;
  2. the static compiler join as far as the merged lanes build it (kv_static.template + kv_static_boot_join joins).
Every open input / undriven bit / tie is classified by the 0da rules and given the lane that owns its producer:
  0da (a) identity straps ACCEPT, (b) tied-low spare bits no consumer reads ACCEPT, (c) unused-mode ties ACCEPT when
  the mode is provably unused, (d) functional config straps REJECT.  Clock / reset entries are die clock-tree wiring
  (item 10, owner KVJ-G), never ties.  The `--mode case` hold in kv_die.py stays until both lists are empty.

    python3 tools/qwen_kv_die/kvjg_gap_list.py --bind BIND_DIR/port_bind_v2.json --out OUT.json
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kv_static as K                                   # noqa: E402
import kv_static_boot_join as B                         # noqa: E402
import kv_static_kvjf_join as F                         # noqa: E402
import kv_static_attn_join as A                         # noqa: E402

CLOCK_RESET = {'ck', 'rst_n', 'hck', 'hrst_n', 'hrst', 'por_n', 'cal_hck', 'cal_rst_n', 'front_hck', 'return_hck',
               'return_ck', 'pll_hbm', 'pll_hbm_port', 'pll_hbm_ecc', 'pll_hbm_cdc', 'pll_hbm_obs'}

# Die-bind findings of the split die (instance master -> port prefix -> (producer, owner lane)).
DIE_OWNERS = {
    ('qkd_pv16_vport', 'in'): ('landing slg_<st>_<2k|2k+1> rsp_* (static landing_seg, joined in kv_static.template); '
                               'die must instantiate the 32 landing segments (row_h3 V response regate)', 'KVJ-F + KVJ-G2'),
    ('qkd_d2d_static', 'att_tx'): ('attention_programme tx_valid/tx_payload (template join exists); attention control '
                                   'tile = programme + qkd_attn_cal_gen + qkd_attn_service_root', 'KVJ-B + KVJ-G2'),
    ('qkd_d2d_static', 'emb_tx'): ('qkd_embedding_row_tx emb_tx_v/emb_tx_payload (RTL merged, KVJ-C 294d90e06); '
                                   'die role + kit', 'KVJ-C2'),
    ('qkd_d2d_static', 'kv_'): ('qkd_kv_ownership_obs kv_active/drained/flush_local (RTL in progress, not pushed)', 'KVJ-F'),
    ('qkd_embgw', 'r_ea'): ('none: D2 boot-only gateway qkd_embgw_boot + lnk successor ot_qkvd_split_kvlink_se drop '
                            'the gq/gr bundles (kv_die.py edit in progress, not pushed)', 'KVJ-C2'),
    ('qkd_host_pc_slice_die', 'ctrl_completion'): ('pc_path completion_v/we x128 (static pc_path parent, '
                                                   'qkd_static_kv_pc_path_emb); die must instantiate pc_path', 'KVJ-C2 + KVJ-G2'),
    ('qkd_host_root_admission', 'ctrl_completion_fault'): ('cf_root.fault (qkd_kv_cfault_tree registered radix-4 neighbour OR '
                                                           'of the 128 pc_path completion_fault, kv_static_cfault_join; bit 0, '
                                                           '[127:1] tree-reduced)', 'KVJ-G2 (wiring); KVJ-A3 port narrowing'),
    ('qkd_host_root_pt', 'ctrl_completion_fault'): ('as qkd_host_root_admission.ctrl_completion_fault (pre-KVJ-A die.v)', 'KVJ-G2'),
    ('qkd_host_root_admission', 'static_setup_ready'): ('boot.setup_ready (HOST_DIE_JOINS, kv_static_boot_join)', 'KVJ-G2'),
    ('qkd_host_root_admission', 'native_reserved'): ('ownership.native_reserved (HOST_DIE_JOINS)', 'KVJ-G2'),
    ('qkd_host_root_admission', 'ownership_valid'): ('ownership.ownership_valid (HOST_DIE_JOINS)', 'KVJ-G2'),
    ('ot_qwen_tp8_pv_wide_ctl_t', ''): ('UNBOUND: OT_KV_PV_T_CTL_STANDIN view qkd_pv_ctl_rstpin_a72; real kit '
                                        'qkd_pv_ctl_t after the PV calendar move', 'KVJ-B (move) then KVE (kit)'),
}
# KV-BIND4-GUARD 10-19: the MU 1 HOST root (OT_KV_MU=1) binds qkd_host_root_admission_mu (same ports): same owners
DIE_OWNERS.update({('qkd_host_root_admission_mu', p): v for (m, p), v in list(DIE_OWNERS.items())
                   if m == 'qkd_host_root_admission'})
# Static-join open inputs (role, port) -> (class, producer, owner).  Classes: DIE_JOIN (producer is an existing die
# master or another static role; wiring only), NEW_RTL (producer RTL not on the integration branch), COMPILER (item 9
# programme compiler / boot image), PHY (analog PHY digital face: off-chip by contract).
STATIC_OWNERS = {
    ('layer_programme', 'start'): ('DIE_JOIN', 'd2d engine_result_token RESULT (token-run trigger)', 'KVJ-G2'),
    ('layer_programme', 'authority_'): ('DIE_JOIN', 'host root token authority (token_epoch / native_request_*)', 'KVJ-G2'),
    ('layer_programme', 'programme_'): ('DIE_JOIN', 'host root program_authorized_* / program_epoch / program_digest', 'KVJ-G2'),
    ('attention_programme', 'compiled_'): ('DIE_JOIN', 'qkd_attn_cal_gen STRETCH=1 (D_QK, D_RL, SERVICE_END from the die '
                                           'report; KVJ-SMALL 10-17) cal / rx_cmd / tx_first / end_age in the attention '
                                           'control tile', 'KVJ-G2'),
    ('attention_programme', 'fused_program_capability'): ('COMPILER', 'boot image capability bit', 'item 9 compiler'),
    # KVJ-SMALL (a) 10-17: request_ready / result_* / service_fault are joined (kv_static_attn_join: attn_root +
    # attn_face); the face's own inputs from the PV final join and the unit faults are die joins
    ('producer', 'f_valid'): ('DIE_JOIN', 'PV final join ot_qwen_tp8_pv256_finalize_static_cal out_valid -> attn_face', 'KVJ-G2'),
    ('producer', 'f_data'): ('DIE_JOIN', 'PV final join out_data (16,384 b) -> attn_face', 'KVJ-G2'),
    ('producer', 'f_epoch'): ('DIE_JOIN', 'PV final join out_epoch -> attn_face', 'KVJ-G2'),
    ('producer', 'unit_fault'): ('DIE_JOIN', 'attention service unit sticky faults (stacks, hub, PV pairs, finalize, V req, '
                                 'e-read, rz-late, K identity) -> attn_face', 'KVJ-G2'),
    ('producer', 'fused_program_capability'): ('COMPILER', 'boot image capability bit (attn_root)', 'item 9 compiler'),
    ('ownership', ''): ('NEW_RTL', 'qkd_kv_ownership_obs go/host_quiet/upstream_quiet (not pushed)', 'KVJ-F'),
    ('drain_guard', 'upstream_'): ('NEW_RTL', 'pc_path ctrl faults / ownership_obs (grp_ctl kit KVJ-D merged)', 'KVJ-F'),
    ('link', 'emb_tx'): ('NEW_RTL', 'qkd_embedding_row_tx role in the graph', 'KVJ-C2'),
    ('link', 'kv_'): ('NEW_RTL', 'qkd_kv_ownership_obs', 'KVJ-F'),
    ('link', 'host_'): ('DIE_JOIN', 'host root host_link_reset_req / host_recovery_clear / boot_go / host_interface_idle',
                        'KVJ-G2'),
    ('link', 'cfg_'): ('COMPILER', 'boot dispatcher link-calendar target (no dispatcher target for the d2d cfg yet)',
                       'KVJ-A follow-up + item 9'),
    ('link', 'cal_'): ('COMPILER', 'd2d_link_calendar start/segment from the layer programme', 'item 9 compiler'),
    ('link', 'record_tx'): ('DIE_JOIN', 'host root record_tx_v / record_tx', 'KVJ-G2'),
    ('link', 'status_epoch16'): ('DIE_JOIN', 'host root local_service_epoch', 'KVJ-G2'),
    ('link', 'serdes_up'): ('PHY', 'SerDes PHY link-up (digital layer in host root)', 'KVJ-G2'),
    ('link', 'fdi_'): ('PHY', 'UCIe x64 PHY FDI (allowed analog model)', 'KVJ-G2'),
    ('vport', 'pr_'): ('DIE_JOIN', 'pvw pair V request (pvrq) words', 'KVJ-G2'),
    ('ectla', 'x_i'): ('DIE_JOIN', 'ECTL B/C ring x face (ectla_kiss tile, KVJ-D merged)', 'KVJ-D'),
    ('pc_path', 'es'): ('NEW_RTL', 'writer es lane -> PC fan-out + es merge (qkd_static_kv_pc_path_emb, KVJ-C merged; '
                        'ROLES still name qkd_static_kv_pc_path)', 'KVJ-C2'),
    # KVJ-C3 10-17: the PC chain root + join4_cal calendar constants (kvjc3_pc_chain.py boot_words, one shared boot bus)
    # KVJ-SMALL b2: bound by kv_static_boot_join (dispatcher ESCFG=1 targets 12 / 13); kept for joins built without it
    ('es_fan_root', 'cfg_'): ('COMPILER', 'boot dispatcher ESCFG target 12 (kvjc3_pc_chain boot_words, '
                              'target 0 = PC player constants) via kv_static_boot_join', 'KVJ-SMALL b2 (bound)'),
    ('emb_join', 'cfg_'): ('COMPILER', 'boot dispatcher ESCFG target 13 on the same bus (join beat calendar) via '
                           'kv_static_boot_join', 'KVJ-SMALL b2 (bound)'),
    ('pc_path', 'front_hbm_data'): ('PHY', 'HBM3E PHY pi (qkd_hbm3e_phy_pc)', 'KVJ-G2'),
    ('pc_path', 'return_hbm_data'): ('PHY', 'HBM3E PHY pi (qkd_hbm3e_phy_pc)', 'KVJ-G2'),
    ('pc_path', ''): ('DIE_JOIN', 'pc_path chain neighbours rsi/ci/pi/ki/fi (host PC slice / ctrl chain)', 'KVJ-G2'),
    ('producer', 'boot_'): ('DIE_JOIN', 'host root boot_pr / boot_image_* (HOST_DIE_JOINS)', 'KVJ-G2'),
}


def owner(table, a, port):
    best = None
    for (r, pre), v in table.items():
        if r == a and port.startswith(pre) and (best is None or len(pre) > len(best[0])):
            best = (pre, v)
    return best[1] if best else None


def static_gaps():
    # KV-INT 10-17: the full merged join (template + boot + 160 boot CDC + host admission + KVJ-F ownership_obs + die cfg)
    # KVJ-SMALL (a): + attention service root / result face (kv_static_attn_join)
    graph, _ = A.build()
    rows, ck = defaultdict(lambda: dict(instances=0)), Counter()
    for i in graph['instances']:
        for p, v in i['inputs'].items():
            if v is not None:
                continue
            if p in CLOCK_RESET:
                ck[i['role']] += 1
                continue
            o = owner(STATIC_OWNERS, i['role'], p) or ('UNCLASSIFIED', '?', 'UNOWNED')
            r = rows[(i['role'], p)]
            r.update(role=i['role'], port=p, cls=o[0], producer=o[1], owner=o[2])
            r['instances'] += 1
    return dict(instances=len(graph['instances']), clock_reset_entries=dict(ck), clock_reset_owner='KVJ-G2 (die clock tree)',
                functional_open=sorted(rows.values(), key=lambda r: (r['owner'], r['role'], r['port'])),
                die_joins=graph.get('die_joins', []))


# 0da classes of the die's declared straps / constant bits (stub_audit_1017.md K-12..K-17)
STRAP_CLASS = {
    'qkd_ectl_a_tp8_epoch_direct:cfg': ('d_FUNCTIONAL_CFG_REJECT', 'boot dispatcher / boot_cdc target', 'KVJ-F'),
    'qkd_ectl_b_tp8_direct:cfg': ('d_FUNCTIONAL_CFG_REJECT', 'boot dispatcher / boot_cdc target', 'KVJ-F'),
    'qkd_ectl_c_tp8_direct:cfg': ('d_FUNCTIONAL_CFG_REJECT', 'boot dispatcher / boot_cdc target', 'KVJ-F'),
    'qkd_rst_region:dly': ('d_FUNCTIONAL_CFG_REJECT', 'boot config load (rst_region fq1 registers it at the pin)', 'KVJ-F'),
}
SUPERSEDED_0DB = ('qkd_kvwq_leaf_s_w129_m', 'qkd_kvwq_ctl_bin', 'qkd_cdc_wleaf', 'qkd_land', 'qkd_land_n')
DIE_UNDRIVEN = {
    'n_pvw_N__in_e': ('ASTK e-read qkd_astk_er_tap in the strip successor qkd_astk_strip_er_s (KVJ-D merged); die binding '
                      'of qkd_astk/qkd_astk_n to the er strip + ASTK credit removal', 'KVE-2 + KVJ-D'),
    'n_pvw_N__epoch': ('qkd_attn_service_root ep (KVJ-B be205336f, not pushed)', 'KVJ-B'),
    'n_pvw_N__context_len': ('qkd_attn_service_root ctx (KVJ-B, not pushed)', 'KVJ-B'),
    'n_pvw_N__start': ('qkd_attn_service_root start_pv (KVJ-B, not pushed)', 'KVJ-B'),
}


def die_gaps(bind):
    """Per die master: unconnected inputs, tied inputs, straps (0da class), undriven classes, each with its owner."""
    r = json.loads(Path(bind).read_text())
    unconn, tied, straps = [], [], []
    for m, v in r['masters'].items():
        if v.get('verdict') == 'PASS' and not v.get('straps'):
            continue
        for p in v.get('input_unconnected', []):
            o = owner(DIE_OWNERS, m, p) or ('?', 'UNOWNED')
            unconn.append(dict(master=m, port=p, instances=v['instances'], producer=o[0], owner=o[1]))
        for p in v.get('input_tied', []):
            tied.append(dict(master=m, port=p, instances=v['instances']))
        if v.get('kind') == 'unbound' or (v.get('verdict') != 'PASS' and not v.get('rtl')):
            o = owner(DIE_OWNERS, m, '') or ('?', 'UNOWNED')
            unconn.append(dict(master=m, port='<UNBOUND master>', instances=v['instances'], producer=o[0], owner=o[1]))
    for s in r.get('straps_declared', []):
        c = STRAP_CLASS.get(s, ('a_IDENTITY_or_c_UNUSED_MODE_ACCEPT', 'physical position / mode strap', '-'))
        straps.append(dict(strap=s, cls=c[0], producer=c[1], owner=c[2]))
    und = [dict(net_class=k, bits=v['bits'], producer=DIE_UNDRIVEN.get(k, ('?', 'UNOWNED'))[0],
                owner=DIE_UNDRIVEN.get(k, ('?', 'UNOWNED'))[1]) for k, v in r.get('undriven_classes', {}).items()]
    # 0db: the old credit write / landing elements are SUPERSEDED (static writer / landing); the die must not hold them
    superseded = [dict(die_master=k, module=v['module'], instances=v['instances'],
                       replacement='static writer + pc_path es / static landing_seg x32 (die homes owed)', owner='KVJ-G2')
                  for k, v in r.get('die_masters', {}).items() if k in SUPERSEDED_0DB]
    consts = r.get('bound_netlist', {}).get('constant_nets_by_class', {})
    return dict(summary=r['summary'], die_sha256=r.get('bound_netlist', {}).get('die_sha256'), input_unconnected=unconn,
                input_tied=tied, undriven=und, straps=straps, constant_bits_by_class=consts,
                pads_declared=r.get('pads_declared', []), superseded_present=superseded,
                constant_owner=dict(unclassified='KVJ-F (classify 2,576 b: identity vs functional, 0da)',
                                    reset_delay_strap='KVJ-F (functional, 0da d)'))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--bind', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    d = die_gaps(a.bind)
    s = static_gaps()
    func_ties = [x for x in d['straps'] if x['cls'].startswith('d_')]
    doc = dict(schema='opentallas.qwen_kv.kvjg_gap_list.v1', die=d, static_join=s,
               totals=dict(die_input_unconnected=d['summary']['input_unconnected'],
                           die_undriven_bits=d['summary']['undriven_net_bits'],
                           die_unbound_masters=d['summary']['unbound_masters'],
                           die_functional_tie_ports=len(func_ties),
                           die_superseded_masters_present=len(d['superseded_present']),
                           static_functional_open_ports=sum(r['instances'] for r in s['functional_open']),
                           static_clock_reset_entries=sum(s['clock_reset_entries'].values())),
               case_hold='KEPT: strict bind not clean (kv_die.py OT_KV_STATIC --mode case refusal unchanged)')
    a.out.write_text(json.dumps(doc, indent=1) + '\n')
    print(json.dumps(dict(doc['totals'], unowned=[f"{r['role']}.{r['port']}" for r in s['functional_open']
                                                   if r['owner'] == 'UNOWNED'] + [f"{u['master']}.{u['port']}" for u in
                                                   d['input_unconnected'] if u['owner'] == 'UNOWNED'])))


if __name__ == '__main__':
    main()
