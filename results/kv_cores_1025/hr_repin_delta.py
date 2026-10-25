#!/usr/bin/env python3
"""KV-CORES2 / KVC2-HR (2026-10-25): plan delta for the 15 qkd_hr_* hard cores of kv3_hub_Wi (KV die qwen_kvsys).

COORD ruling (BRIEFING 16a + KVG3-CORES OWNER? 6): ADOPT THE HOST-CLUSTER WRAPPERS (partition_r2.json children,
tools/qwen_kv_die/host_cluster/gen_cluster.py: one clock port per clock FAMILY) and RE-PIN.  Under 16a the host and
ingest families retire onto the die clock (ck_core); only the PHY family (ck_phy_fam / ck_phy[i]) keeps its own clock,
and the only async crossing left is the PHY edge (qkd_hr_cdc_pc u_rx/u_tx).
Reads (repo-relative): physical/die_plan/qwen_kvsys/{die_plan.json, core_conns.json, cores/qkd_hr_*_pins.json},
results/arch/qwen_split_1014/host_root_cluster/partition_r2.json, the bound hub_Wi partition (clock bindings of u_host).
Writes results/kv_cores_1025/hr_repin_delta.json.  Pin counts AFTER are estimates from the v3.8u pin files and
core_conns partners (pins whose every partner is merged into the same new core become internal); the exact pins come
from core_pins_hr.py on the regenerated (obsx, 16a) wrappers."""
import json, re, collections, sys
from pathlib import Path
R = Path(__file__).resolve().parents[2]
QK = R / 'physical/die_plan/qwen_kvsys'
P = json.load(open(QK / 'die_plan.json'))
T = P['partition_types']['kv3_hub_Wi']
CONNS = json.load(open(QK / 'core_conns.json'))['kv3_hub_Wi']
R2 = json.load(open(R / 'results/arch/qwen_split_1014/host_root_cluster/partition_r2.json'))['children']
PART = (QK / 'bind/bound_r8/rtl/kv3_hub_Wi_part.sv').read_text()
CKR = re.compile(r'^(\w+__)?(clk|ck|ck_\w+|clk_\w+|\w*clk|wck|rck|\w+_wck|\w+_rck|clk_h|clk_bank|clk_out)$')
RSR = re.compile(r'^(\w+__)?(rst_n|arst_n|\w*_rst_n|por_n|rrst_n|wrst_n)$')

# bound u_host clock bindings (proof that the many ck_* pins are already ONE net except host/ingest/phy families)
host_ck = dict(re.findall(r'\.(ck_\w+)\(\{?(clk\w*)', PART[PART.index('qkd_host_root_admission_obsx'):]))
fam_net = collections.defaultdict(list)
for p, n in sorted(host_ck.items()):
    fam_net[n].append(p)

# plan module -> r2 child (adopted wrapper); members by leaf path
PLAN2R2 = {
    'qkd_hr_cdc_ch': 'qkd_hr_cdc_host', 'qkd_hr_host_qm': 'qkd_hr_cdc_host',
    'qkd_hr_cdc_ci': 'qkd_hr_ingest_qm', 'qkd_hr_cdc_hi': 'qkd_hr_ingest_qm', 'qkd_hr_ingest_eng': 'qkd_hr_ingest_qm',
    'qkd_hr_core_tx': None,           # split: u_tx -> core_tx, u_axi -> core_prompt, u_ctrl -> core_peer
}
# (plan module, plan member leaf) -> r2 child.  Leaf names repeat across cores (u_rx / u_tx), so key by both.
PM2R2 = {
    ('qkd_hr_cdc_ch', 'u_done'): 'qkd_hr_cdc_host', ('qkd_hr_cdc_ch', 'u_ing'): 'qkd_hr_cdc_host',
    ('qkd_hr_host_qm', 'u_pacer'): 'qkd_hr_cdc_host',
    ('qkd_hr_cdc_ci', 'u_ox'): 'qkd_hr_ingest_qm', ('qkd_hr_cdc_ci', 'u_rx'): 'qkd_hr_ingest_qm',
    ('qkd_hr_cdc_hi', 'u_cx'): 'qkd_hr_ingest_qm', ('qkd_hr_cdc_hi', 'u_hx'): 'qkd_hr_ingest_qm',
    ('qkd_hr_ingest_eng', 'u_eng'): 'qkd_hr_ingest_qm',
    ('qkd_hr_core_tx', 'u_tx'): 'qkd_hr_core_tx', ('qkd_hr_core_tx', 'u_axi'): 'qkd_hr_core_prompt',
    ('qkd_hr_core_tx', 'u_ctrl'): 'qkd_hr_core_peer',
}
def r2_of(mod, m):
    return PM2R2.get((mod, m), mod)
# clocks AFTER (16a): family -> pin
AFTER_CK = {
    'qkd_hr_phy_pad': ['ck_phy'], 'qkd_hr_phy_adp': ['ck_phy'],
    'qkd_hr_cdc_pc': ['ck', 'ck_phy'],
}
# crossings: (core, member, path, before, after, latency delta)
CROSS = [
    dict(core_after='qkd_hr_cdc_host', member='u_rank/u_bridge/u_ing', module='ot_qwen_die_cdc_ch #(W546,PIPE2)',
         path='packet queue (core) -> QM host side ingest words', before='async FIFO ck -> clk_host (Gray AD8, 2-flop sync)',
         after='same-clock credit channel (SAMECLK=1: registered-write sync FIFO, same IBUF/OCRED credits, PIPE2 '
               'stations kept)', clocks_before=['ck(qw)', 'clk_host(qr)'], clocks_after=['ck']),
    dict(core_after='qkd_hr_cdc_host', member='u_rank/u_bridge/u_done', module='ot_qwen_die_cdc_ch #(W546,PIPE2)',
         path='QM completions (host) -> packet done', before='async FIFO clk_host -> ck',
         after='same-clock credit channel (SAMECLK=1)', clocks_before=['clk_host(ccw)', 'ck(ccr)'], clocks_after=['ck']),
    dict(core_after='qkd_hr_cdc_host', member='u_rank/u_bridge/u_pacer', module='qkd_host_qm_credit_pacer',
         path='QM credit pacer', before='clk_host', after='ck (no logic change)', clocks_before=['clk_host'],
         clocks_after=['ck']),
    dict(core_after='qkd_hr_cdc_host', member='u_rank/u_fence (was partition glue)', module='qkd_host_visibility_fence',
         path='visibility fence ck/clk_h', before='two clocks (ck, clk_host) + internal toggle sync',
         after='both ports on ck (clk_h tied to ck in the wrapper); toggle synchroniser becomes a same-clock 2-flop delay '
               '(no RTL change; OPTIONAL later clean-up)', clocks_before=['ck', 'clk_host'], clocks_after=['ck']),
    dict(core_after='qkd_hr_ingest_qm', member='u_rank/u_qm/u_hx', module='ot_link_afifo #(W514,AW=HFA)',
         path='host stream clk_h -> ingest clk_i', before='async FIFO SYNC=2', after='same-clock FIFO SYNC=1 (SAMECLK=1)',
         clocks_before=['clk_host', 'clk_ingest'], clocks_after=['ck']),
    dict(core_after='qkd_hr_ingest_qm', member='u_rank/u_qm/u_ox', module='ot_link_afifo #(W=AW+257,AW=OFA)',
         path='ingest requests clk_i -> core ck', before='async FIFO SYNC=2', after='same-clock FIFO SYNC=1',
         clocks_before=['clk_ingest', 'ck'], clocks_after=['ck']),
    dict(core_after='qkd_hr_ingest_qm', member='u_rank/u_qm/u_rx', module='ot_link_afifo #(W256,AW=RFA)',
         path='read returns ck -> clk_i', before='async FIFO SYNC=2', after='same-clock FIFO SYNC=1',
         clocks_before=['ck', 'clk_ingest'], clocks_after=['ck']),
    dict(core_after='qkd_hr_ingest_qm', member='u_rank/u_qm/u_cx', module='ot_link_afifo #(W64,AW=CFA)',
         path='completions clk_i -> clk_h', before='async FIFO SYNC=2', after='same-clock FIFO SYNC=1',
         clocks_before=['clk_ingest', 'clk_host'], clocks_after=['ck']),
    dict(core_after='qkd_hr_cdc_pc', member='u_rank/u_phy/u_rx,u_tx', module='ot_qwen_die_cdc_ch #(W546,PIPE2)',
         path='PHY edge rx clk_phy -> ck, tx ck -> clk_phy', before='async FIFO', after='UNCHANGED: this is the PHY-edge '
         'async FIFO that 16a keeps', clocks_before=['ck', 'clk_phy'], clocks_after=['ck', 'ck_phy']),
]


def groups(mod):
    d = json.load(open(QK / f'cores/{mod}_pins.json'))
    g = collections.Counter(re.sub(r'\[\d+\]$', '', p['name']) for p in d['pins'])
    return d, g


cores = []
by_after = collections.defaultdict(list)
insts = [h for h in T['hard_cores'] if h['module'].startswith('qkd_hr_')]
seen = set()
for h in insts:
    mod = h['module']
    if mod in seen:
        continue
    seen.add(mod)
    n_inst = sum(1 for x in insts if x['module'] == mod)
    d, g = groups(mod)
    ck = sorted(k for k in g if CKR.match(k))
    rs = sorted(k for k in g if RSR.match(k))
    mem = re.search(r"members \[([^\]]*)\]", h['note'])
    mem = [m.strip(" '") for m in mem.group(1).split(',')] if mem else []
    if mod in PLAN2R2 and PLAN2R2[mod]:
        after = PLAN2R2[mod]
    elif mod == 'qkd_hr_core_tx':
        after = 'split'
    else:
        after = mod
    cores.append(dict(module=mod, instances=n_inst, members=mem, pins_before=sum(g.values()),
                      clock_pins_before=ck, reset_pins_before=rs, r2_core_after=after,
                      member_routing={m: r2_of(mod, m) for m in mem}))
    for m in mem:
        by_after[r2_of(mod, m)].append((mod, m))

# AFTER: per r2 child, estimate pins = union of member pin groups whose partners leave the new core
after = []
plan_inst_of = {h['module']: h['inst'] for h in insts}
for ch in R2:
    srcs = by_after.get(ch, [])
    own_insts = {'host__' + m for m, _ in srcs} | ({'host__' + ch} if any(m == ch for m, _ in srcs) else set())
    n_in = n_ext = 0
    data_groups = 0
    for mod in sorted({m for m, _ in srcs}):
        d, g = groups(mod)
        mem_here = [mm for mo, mm in srcs if mo == mod]
        conns = CONNS.get(plan_inst_of[mod] if mod != 'qkd_hr_phy_adp' else 'host__qkd_hr_phy_adp_0', {})
        for k, w in g.items():
            if CKR.match(k) or RSR.match(k):
                continue
            # multi-member plan cores prefix pins with <member>__ ; keep only this child's members
            pre = k.split('__')[0] if '__' in k else None
            if pre is not None and pre not in mem_here:
                continue
            parts = conns.get(k, [])
            internal = parts and all(p.startswith('core:') and p[5:] in own_insts for p in parts)
            if internal:
                n_in += w
            else:
                n_ext += w
                data_groups += 1
    ck_after = AFTER_CK.get(ch, ['ck'])
    after.append(dict(module=ch, members=R2[ch]['members'], from_plan_cores=sorted({m for m, _ in srcs}),
                      instances=8 if ch == 'qkd_hr_phy_adp' else 1,
                      clock_pins_after=ck_after, reset_pins_after=['rst_n (host_rst_n; + por_n where a member '
                                                                 'reads it: peer/prompt/guard/tx-ctrl)'],
                      data_pins_after_est=n_ext, data_pins_internalised_est=n_in, data_pin_groups_after_est=data_groups,
                      note=R2[ch].get('direct', '')))

out = dict(
    schema='opentallas.kv_cores_1025.hr_repin_delta.v1',
    ruling='COORD 2026-10-25 (KV-CORES2): adopt host-cluster wrappers + re-pin; BRIEFING 16a (host/ingest logic on the '
           'die clock, async FIFO only at the PHY edge)',
    plan_base='origin/main die_plan.json (KV v3.9 line; hub_Wi hr cores from KVG3-WI v3.8u core_pins_hr.py)',
    bound_u_host_clock_nets={k: v for k, v in fam_net.items()},
    bound_finding='In the bound hub_Wi partition (bound_r8) every u_host ck_* port except 5 (host family), 4 (ingest) '
                  'and 11 bits (phy family) is ALREADY the die clock net clk: the 1..8 clock pins per hr core are '
                  'duplicate pins of ONE net, not separate domains. Real separate domains: clk_clk_host, '
                  'clk_clk_ingest (both retire under 16a) and clk_clk_phy (kept: PHY side).',
    cores_before=cores,
    cores_after=after,
    crossings=CROSS,
    instance_count=dict(before=len(insts), after=sum(a['instances'] for a in after)),
    module_count=dict(before=len(cores), after=len(after)),
    plan_changes_for_KV_PLAN2=[
        'kv3_hub_Wi.hard_cores: replace the 15 v3.8u hr modules / 22 instances by the 12 r2 wrappers / 19 instances '
        '(cdc_ch+host_qm(+fence glue) -> qkd_hr_cdc_host; cdc_ci+cdc_hi+ingest_eng(+qm glue) -> qkd_hr_ingest_qm; '
        'core_tx u_axi -> core_prompt, u_ctrl -> core_peer); outlines re-derived from wrapper cell area at the v3.8u '
        'fill (merged cores: sum of merged outlines as a start, GEOM first)',
        'pins: re-run core_pins_hr.py against the regenerated wrappers (members = r2 children, glue rule: NO glue left '
        'in the partition: the wrappers own fence/qm own logic) -> cores/qkd_hr_*_pins.json + core_conns.json; one '
        'clock pin per core (ck), ck_phy on phy_pad/phy_adp, ck + ck_phy on cdc_pc only',
        'clocks_v32.json: drop clk_host and clk_ingest trunks (hub_C pll_host / pll_ingest outputs unused -> remove '
        'from pll leaf, no tie-off); clk_phy stays (hub_Wi only: phy_pad, phy_adp x8, cdc_pc PHY face)',
        'bound partition kv3_hub_Wi_part: u_host ck_qm_host/ck_qm_ing_r/ck_qm_credit/ck_qm_done_w/ck_fence_host and '
        'ck_qm_ingest/ck_qm_out/ck_qm_bank[1:0] -> clk; partition ports clk_clk_host/clk_clk_ingest removed',
        'latency receipt: host ingest path changes (see crossings): u_ing / u_done PIPE2 async -> same-clock; u_hx, '
        'u_ox, u_rx, u_cx SYNC 2 -> 1; and host/ingest logic now at the die period (833 ps) instead of 1000 / 1666.7 '
        'ps: ingest engine u_eng must close at 833 ps (was clk_ingest 1666.7 ps) -> TIMING RISK, see open questions',
        'regs_um conditions L753/L754/L1449 (hub_Wi in-core stations on core_order/core_peer) re-evaluated on the new '
        'outlines',
    ],
)
op = R / 'results/kv_cores_1025/hr_repin_delta.json'
op.parent.mkdir(parents=True, exist_ok=True)
op.write_text(json.dumps(out, indent=1) + '\n')
for c in cores:
    print(f"{c['module']:22s} x{c['instances']} pins {c['pins_before']:5d} ck {len(c['clock_pins_before'])} -> {c['r2_core_after']}")
print('---')
for a in after:
    print(f"{a['module']:22s} x{a['instances']} from {a['from_plan_cores']} ck {a['clock_pins_after']} data~{a['data_pins_after_est']} internal~{a['data_pins_internalised_est']}")
print(json.dumps(out['bound_u_host_clock_nets'], indent=0)[:900])
