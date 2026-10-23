#!/usr/bin/env python3
"""KV-P3 10-23: blocker status of plan v3.2 for BINDER (supersedes blockers_v31.json): per strap port its class and fix;
relays, landing faults, clocks, reset root.
    python3 bind/blockers_v32.py bind/v32_inputs.json.gz die_plan.json clocks_v32.json [bind/tile_variants.json] > bind/blockers_v32.json"""
import gzip, json, sys
D = json.load(gzip.open(sys.argv[1])); P = json.load(open(sys.argv[2])); C = json.load(open(sys.argv[3]))
A = {'ot_qkh_lane8.bsel': 'ot_qkh_lane8_p #(BSEL)', 'ot_qkh_head_frontq_native.hid': 'ot_qkh_head_frontq_native_p #(HID)',
     'ot_qwen_tp8_pv_wide_ctl_tbf.pair_id': 'ot_qwen_tp8_pv_wide_ctl_tbf_p #(PAIR_ID)', 'qkd_astk_ctl_s.st': 'qkd_astk_ctl_s_p #(ST)',
     'qkd_astk_zn.zc': 'qkd_astk_zn_p / qkd_astk_zn_head_p #(ZC)',
     'qkd_kvs_grp_h_r2c.slg__cfg_group': 'child qkd_static_kv_landing_seg_p #(CFG_GROUP) + tile variant qkd_kvs_grp_h_p (see tile_variants)',
     'qkd_kvs_pc_h.pc__pc': 'child qkd_static_kv_pc_path_fan_nc_b_head_p #(PC) + tile variant qkd_kvs_pc_h_head_p (see tile_variants)'}
B = {'qkd_kvs_pc.pc__pc': 'pc ID lane row4 + j (ot_dp_id_add K=j)', 'qkd_hslice.lpc': 'pc ID lane row4 + j',
     'qkd_hslice_dn.lpc': 'pc ID lane row4 + j', 'qkd_kvs_pc.pc__cfg_stack': 'pc ID lane stack field',
     'qkd_kvs_pc_h.pc__cfg_stack': 'pc ID lane stack field', 'qkd_kvs_grp_r2c.slg__cfg_stack': 'pc ID lane stack field',
     'qkd_kvs_grp_h_r2c.slg__cfg_stack': 'pc ID lane stack field', 'qkd_kvs_hroot.esh__stack': 'stack lane hub_Wo/Eo -> hroot',
     'qkd_kvs_grp_r2c.slg__cfg_group': 'pc ID lane PHYS table (ot_dp_id_rot)', 'qkd_astk_ep_s.sq': 'astk ID lane (row)',
     'qkd_astk_er_owner_st.owner_id': 'astk ID lane (row)', 'qkd_astk_ep_s.eo': 'computed from sq in qkd_astk_ep_s_e (RTL)'}
HEADV = {'qkd_astk_ep_s': 'qkd_astk_ep_s_head_e', 'qkd_astk_er_owner_st': 'qkd_astk_er_owner_st_head',
         'qkd_hslice': 'qkd_host_pc_slice_die_head', 'qkd_hslice_dn': 'qkd_host_pc_slice_die_head',
         'qkd_astk_zn': 'qkd_astk_zn_head_p', 'qkd_kvs_pc_h': 'qkd_kvs_pc_h_head_p (tile) over qkd_static_kv_pc_path_fan_nc_b_head_p'}
TILE = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else dict(status='OPEN')
rows, tot = [], {}
for mp, iv in sorted(D['straps'].items()):
    w = len(next(iter(iv.values()))); bits = w * len(iv); m = mp.split('.')[0]
    if mp in A:
        cl, fix = 'A leaf parameter (type-constant)', A[mp]
    elif mp in B:
        cl, fix = 'B position id varying across replicas -> plan ID lane', B[mp]
    else:
        cl, fix = 'C chain-head input, no producer by design -> dead port removed (head variant)', HEADV[m]
    rows.append(dict(port=mp, bits=bits, insts=len(iv), cls=cl[0], what=cl, fix=fix))
    tot[cl[0]] = tot.get(cl[0], 0) + bits
out = dict(schema='opentallas.kv_p3.blockers.v32', plan='die_plan v3.2',
           straps=dict(bits=sum(r['bits'] for r in rows), ports=len(rows), by_class=tot, table=rows,
                       rtl='claude/kv-p3-leaf-1023 392d86eb2 + 9fca19d9f (variants + rtl/lib/ot_dp_id.sv, ot_dp_efault.sv), merged into claude/kv-p3-rtl-1023 @8d7467e8a'),
           pv_trunk_mux_relays=dict(cells=len(D['relays']), status='plan contents of pv types (2 per pv row per chain, '
                                    'loc pv__u_T*), chain + select edges from bitcon', by_part={}),
           landing_fault_inputs=dict(bits=356, traced_direct=len(D['landing_faults']), via_relay=dict(n=5, receivers=['hroot_WS', 'hub_Wi', 'hub_Wi', 'hub_Wi', 'pv_S_0'], note='landing fault -> qkd_rlys relay -> OR; receivers already carry a check'),
                                     status='replaced: ot_dp_efault per receiving partition (23 types / 88 partitions) + '
                                            'per-column OR chains (qkd_hp_or2 u_fch) -> 14 heads -> new hp_v32_* ORs at '
                                            'the tree root (hub_C); as-built OR tree 366 leaves -> 5 kept + 22 bypassed '
                                            'removed + 334 removed (fed only by landings)'),
           clocks=dict(regions=[r['name'] for r in C['regions']], file='clocks_v32.json',
                       status='G2 die probe with every spine (core + 8 non-core regions + plan reset root hub_Wi + POR) '
                              'on M8/M9: overflow 0, 11 nets routed (g2_clocks_v32_report.json, KV-P3b). Sidecar until '
                              'PLAN-TOOL adds clock regions to the schema/gen_rtl; measured insertion is a G3/G4 item'),
           reset_root=C['reset_root'],
           hc_transport=dict(status='DONE claude/kv-p3-rtl-1023 92926aac0: START-only HC transport (HCW 39) below the '
                                    'OBSX station, {143\'d0,cmd_hc} pad removed; hc39 lockstep eq/eq_abort 0 mismatches, '
                                    'rsv PASS, 4/4 mutants caught (results/rtl/kv_p3_hc39_1023)',
                             remaining_pads='MU root station (OT_KV_HOST_OBS=0) and OBS no-ext station: not the release '
                                            'OBSX path; unchanged'),
           tile_variants=TILE,
           binder_inputs=dict(file='bind/asbuilt.json + bind/asbuilt_map.json (bind/asbuilt_kv.py), netlist '
                                   'bind/inputs/die_rtl6.v.gz, PHY slice models bind/models/kv_phy_slices.sv',
                              requests='asbuilt.json kv_binder_requests (per-instance head substitute, class-B ID lanes, '
                                       'ot_dp_efault landing checks, multi-clock partitions, qkd_rlyi_258s = logic)'),
           open=['PLAN-TOOL: clock regions + per-bus clock + reset source partition in the schema (clocks_v32.json '
                 'tool_requests); the G2 qualification is done by g2_clocks_v32.py',
                 'BINDER2: kv_binder_requests in bind/asbuilt.json (ot_dp_efault IN_LANES/REL_AGE from the latency '
                 'table; ID cell binds; per-instance head substitution)',
                 'L1 planned cores (l1_cores_v31.json: head_eighth 383k x16 per hg/hgi, pv_pair 388k x16 per pv, '
                 'kvs_pc 140k x3 per pc, ahub/kvs_ctl, 22 host cluster cores) are not yet plan hard_cores[] / clock.taps[]'])
for r in D['relays'].values():
    out['pv_trunk_mux_relays']['by_part'][r['part']] = out['pv_trunk_mux_relays']['by_part'].get(r['part'], 0) + 1
json.dump(out, sys.stdout, indent=1)
