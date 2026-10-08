#!/usr/bin/env python3
"""HBM accelerator (DS-V4.1 on HBM, r23 die): SM / gather / collective / shared-service -> SU result contract.

An executable inventory.  It reads the RTL, the die generator model and the committed composition records, checks every
claim it makes against the sources (fail closed: any missing file, changed port, changed record or unmet check stops
the tool with exit 1), and writes results/rtl/hbm_sm_su_result_contract_20261007/contract.json.

Question answered (Codex consumer audit, 2026-10-07): which unit actually PRODUCES each result the SU consumes, over
which ports, with which protocol, latency, die route, credit depth and queue area -- and does the published HBM
composition count the die-view path SM r (270 b) -> gather stations -> hfd_su.r as native execution, although
hfd_su is a physical envelope that XOR-folds its inputs?

Every edge item carries a status:
  implemented-in-RTL      the producer and consumer ports and the protocol exist in committed RTL (component or join)
  exists-only-in-die-view the wires / stations exist in the die views or generator, with no functional consumer
  missing                 neither

Latency classes: 'rtl-measured' (a committed bench record), 'die-model' (generator stage count, r23 Manhattan floor
from committed sources), 'estimate' (stated formula with stated assumptions; never composed as measured).

    python3 tools/hbm_sm_su_result_contract.py            # write contract.json
    python3 tools/hbm_sm_su_result_contract.py --check    # regenerate and require a byte-identical contract.json

Stdlib only; reads repo-relative paths only (reproducible from a clean `git archive`).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/rtl/hbm_sm_su_result_contract_20261007/contract.json'
CLK_HZ = 1.2e9

SRC = dict(
    sm_v='rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv',
    su_exec='rtl/hbm_accel/su/ot_hbm_accel_su_parent_exec.sv',
    cluster='rtl/hbm_accel/integrated_20261005/ot_ds_hbm_cluster20_integrated.sv',
    w2_sink='rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_w2_result_sink.sv',
    gather_bridge='rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_gather_bridge.sv',
    result_provider='rtl/hbm_accel/control_20261007/result_provider/ot_hbm_sm_result_provider.sv',
    relay_slice='rtl/hbm_accel/result_relay_stage_20261007/ot_hbm_result_relay_slice.sv',
    delay_bank='rtl/hbm_accel/result_delay_bank_20261007/ot_hbm_result_delay_bank.sv',
    tu_endpoint='rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint.sv',
    mreq_cdc='rtl/gpu_sys/ot_gpu_mreq_cdc.sv',
    memsys='rtl/gpu_sys/ot_gpu_memsys.sv',
    l2_slice='rtl/gpu_sys/ot_gpu_l2_slice.sv',
    hfd_su='physical/hbm_accel_die_views/su/rtl/hfd_su.sv',
    hfd_su_plan='physical/hbm_accel_die_views/su/rtl/plan.json',
    quarter_gen='tools/hbm_hub_quarter_gen.py',
    die_fp='tools/hbm_accel_die_fp.py',
    die_price='tools/hbm_accel_die_price.py',
    die_views='tools/hbm_die_views.py',
    recompose_tool='tools/hbm_die_views_recompose.py',
    station_roles='physical/hbm_accel_die_views/station_roles.json',
    relay_ends='physical/hbm_accel_die_views/relay_ends.json',
    rp_component='results/rtl/hbm_sm_result_provider_20261007/component.json',
    relay_record='results/rtl/hbm_result_relay_stage_20261007/record.json',
    delay_gate='results/rtl/hbm_result_delay_bank_20261007/component_gate.json',
    matched='results/rtl/dshbm_matched_reference_20261005/composition.json',
    seq_ar='results/rtl/dshbm_matched_reference_20261005/sm_seq/ar_l20_nc8_a1.json',
    seq_wg='results/rtl/dshbm_matched_reference_20261005/sm_seq/wg_nc8_a1.json',
    seq_other='results/rtl/dshbm_matched_reference_20261005/sm_seq/other_nc8_a1.json',
    closure_ledger='results/rtl/hbm_accel_die_views_20261006/closure_cost_ledger.md',
    recompose_r23='results/rtl/hbm_accel_die_views_20261006/recompose_r23_r23cwire__cp_in_su.json',
    headline_r23='results/rtl/hbm_accel_die_views_20261006/headline_with_closure_r23.json',
    su_provider_prertl='results/uarch/hbm_su_parent_join_20261005/pre_rtl.json',
)

# Unified ledger (branch claude/unified-composition-20261007 @ 3fbad709d, not in this tree): HBM DS rows, constants
UNIFIED = dict(commit='3fbad709d830b4d856625a3db32424ed59094ab5',
               file='results/arch/unified_composition_20261007/ledger.json',
               unified_candidate=dict(AR_us=561.067, MTP_step_us=1102.39, AR_tok_s=1782.3, MTP_tok_s=3772.7),
               closure_fec_no_lever_credit=dict(AR_us=603.616, MTP_step_us=1179.446, AR_tok_s=1656.7, MTP_tok_s=3526.2),
               tau=4.159)

# SM node of the matched AR walk -> the measured sequence ops whose result rows that node hands to its consumer
# (rows of 8 x FP32 = 256 b; rows per SM per op from the bit-exact sm_seq records).  'est' rows have no op of that
# tag in the records and use the stated proxy.
NODE_OPS = {
    'sm:wq_a': [('seq_ar', 'wq_a')],
    'sm:wkv': [('seq_ar', 'wkv')],
    'sm:wq_b (head-aligned: head h on die h)': [('seq_ar', 'wq_b')],
    "sm:wo_a K-split: the die's head against its o-group's 1,024 rows": [('seq_ar', 'wo_a')],
    'sm:wo_b': [('seq_ar', 'wo_b')],
    'sm:router gate': [('seq_ar', 'router gate')],
    'sm:routed gate/up workgroup': [('seq_wg', 'routed gate/up workgroup (12 matrices)'), ('seq_wg', 'expert slot 6 w1'),
                                    ('seq_wg', 'expert slot 6 w3')],
    'sm:expert slot 0 w2': [('seq_ar', f'expert slot {i} w2') for i in range(7)],
    'sm:indexer.weights_proj': [('seq_ar', 'indexer.weights_proj')],
    'sm:indexer.wq_b': [('seq_ar', 'indexer.wq_b')],
    'sm:compressor.wkv': [('seq_ar', 'compressor.wkv')],
    'sm:compressor.wkv|wgate': [('seq_ar', 'compressor.wkv')],           # est: wgate same K5120 R1 shape
    'sm:engram.wkv': [('seq_ar', 'compressor.wkv')],                     # est: no engram op in the records -> 1 row
    'sm:LM head': [('seq_other', 'head bf16 K5120 (43 rows)')],
}
NODE_EST = {'sm:compressor.wkv|wgate', 'sm:engram.wkv'}

# estimate parameters for the RTL store-and-forward path (no committed bench of the real backend round trip)
EST = dict(sync=3, mem_period_ps=1000, sm_period_ps=833,
           note='one-outstanding round trip through ot_gpu_mreq_cdc (AW3 Gray FIFO, SYNC=3 each way) + xbar + L2 '
                'slice, floor only: request crossing >= SYNC+1 clk_mem edges (4.8 SM cycles), response crossing >= '
                'SYNC+1 SM edges, xbar + L2 acceptance >= 2 clk_mem edges (2.4 SM cycles) -> >= 12 SM cycles; a '
                'write is acknowledged only after the HBM partition acknowledges it (ot_gpu_l2_slice write-through), '
                'which this floor does NOT include')
T_RTT_FLOOR = 12           # SM cycles, see EST
DRAIN_FIXED = 4            # per row, ot_hbm_sm_result_provider model drain_cycles_per_row


class Refused(Exception):
    pass


def need(cond, msg):
    if not cond:
        raise Refused(msg)


def rd(key):
    p = ROOT / SRC[key]
    need(p.is_file(), f'missing input {SRC[key]}')
    return p.read_text()


def sha(key):
    return hashlib.sha256((ROOT / SRC[key]).read_bytes()).hexdigest()


def ports(text, module):
    text = re.sub(r'//[^\n]*', '', text)
    m = re.search(r'module\s+' + re.escape(module) + r'\b(.*?)\);', text, re.S)
    need(m is not None, f'module {module} not found')
    return m.group(1)


def width_of(body, name):
    m = re.search(r'(?:input|output)\s+(?:wire|reg)?\s*(\[[^\]]+\])?\s*(?:[\w$]+\s*,\s*)*' + re.escape(name) + r'\b', body)
    need(m is not None, f'port {name} not found')
    if not m.group(1):
        return 1
    r = m.group(1)[1:-1].split(':')
    return r


def die_model():
    """r23 die generator model + Manhattan-floor pricing (committed sources only; the generator prints nothing here)."""
    sys.path.insert(0, str(ROOT / 'tools'))
    with redirect_stdout(io.StringIO()):
        import hbm_accel_die_fp as F  # noqa: E402
        import hbm_accel_die_price as PR  # noqa: E402
        import hbm_die_views as V  # noqa: E402
        m = V.model()[0]
        rp = {}
        for p, v in F.manhattan_paths(m).items():
            rp[p] = dict(segments=v['segments'], routed_um=v['um'], stages_430=v['stages_430'], stages_504=v['stages_504'],
                         stages_430_mean_bundle=v['stages_430'], stages_430_median_bundle=v['stages_430'],
                         stages_430_manhattan=v['stages_430'])
        cm = PR.class_max(rp)
        priced = PR._price(m, rp, cm, 'stages_430_manhattan')
    return F, PR, m, rp, cm, priced


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true', help='require the committed contract.json to be byte-identical')
    a = ap.parse_args(argv)
    try:
        rec = build()
    except Refused as e:
        print(f'REFUSED: {e}', file=sys.stderr)
        return 1
    text = json.dumps(rec, indent=1, sort_keys=False) + '\n'
    if a.check:
        if not OUT.is_file() or OUT.read_text() != text:
            print('REFUSED: contract.json differs from a fresh build', file=sys.stderr)
            return 1
        print('check: contract.json reproduces byte-identically; all checks pass')
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(json.dumps(rec['summary'], indent=1))
    return 0


def build():
    checks = []

    def chk(name, cond, detail):
        need(cond, f'check {name} failed: {detail}')
        checks.append(dict(check=name, ok=True, detail=detail))

    # ---------------------------------------------------------------- RTL ports
    smv = ports(rd('sm_v'), 'ot_hbm_accel_sm_v')
    sm_out = {n: width_of(smv, n) for n in ('rv', 'rrow', 'rdata', 'fault')}
    chk('sm_v_result_port', all(re.search(r'output\s+wire[^;\n]*\b' + n + r'\b', smv) for n in sm_out)
        and not re.search(r'\b(rready|r_ready|rrdy|res_ready)\b', smv),
        'ot_hbm_accel_sm_v results: output rv, rrow[$clog2(RMAX)-1:0], rdata[NC*32-1:0], fault; NO ready input '
        '(one-way, one row a cycle at most, PIO=2 boundary stages inside the measured start->done)')
    sm_bits = 1 + 12 + 8 * 32 + 1
    fp_text = rd('die_fp')
    chk('die_w_res', re.search(r'W_RES\s*=\s*256\s*\+\s*12\s*\+\s*1\s*\+\s*1', fp_text) is not None,
        f'generator W_RES = 256 + 12 + 1 + 1 = {sm_bits} b = the SM r face (rdata / rrow / rv / fault)')

    sux = ports(rd('su_exec'), 'ot_hbm_accel_su_parent_exec')
    su_has_result_in = re.search(r'\b(result_v|res_v|rv|rdata|result_data|coll_data|inj_data|del_flit)\b', sux)
    chk('su_exec_ports', su_has_result_in is None and re.search(r'output wire req_v,input wire req_rdy,output wire \[336:0\] req',
                                                                rd('su_exec')) is not None
        and re.search(r'input wire rsp_v,output wire rsp_rdy,input wire \[272:0\] rsp', rd('su_exec')) is not None,
        'ot_hbm_accel_su_parent_exec: the ONLY data ports are a memory request (req_v/req_rdy, 337 b = we 1 + addr 32 + '
        'wdata 256 + wstrb 32 + tag 16) and response (rsp_v/rsp_rdy, 273 b = tag 16 + we 1 + data 256); no SM-result, '
        'collective-delivery or attention-output ingress port exists')

    cl = rd('cluster')
    chk('cluster_sm_is_simt', 'ot_ds_hbm_simt_sm20' in cl and 'ot_hbm_accel_sm_v' not in cl,
        'the integrated DS cluster (ot_ds_hbm_cluster20_integrated) instantiates the SIMT SM ot_ds_hbm_simt_sm20, not '
        'the matrix SM ot_hbm_accel_sm_v whose cycles the composition uses')
    chk('cluster_w2_result_from_pins', re.search(r'input wire \[ND-1:0\][^;]*\bw2_result_v\b', cl) is not None
        and re.search(r'input wire \[ND\*256-1:0\] w2_result_data', cl) is not None
        and 'ot_hbm_integrated_w2_result_sink' in cl,
        'W2 (matrix) results enter the cluster as TOP-LEVEL inputs w2_result_v / w2_result_row / w2_result_data[256] '
        '(bench-driven) into ONE ot_hbm_integrated_w2_result_sink per die, which writes them through shared provider '
        'port p_req[2]')
    chk('cluster_su_via_memsys', re.search(r'p_req_addr\[63:32\],p_req_wdata\[511:256\][^;]*su_provider_req', cl) is not None
        and 'ot_gpu_mreq_cdc #(.ENABLE(1), .AW(3))' in cl and 'ot_gpu_memsys_adapter' in cl,
        'the SU reads its operands as 256-b sectors: su_parent_exec req -> su_provider adapter -> shared provider port '
        'p_req[1] -> ot_gpu_mreq_cdc (AW3, clk_sm -> clk_mem) -> ot_gpu_memsys_adapter (xbar -> L2 slice -> HBM '
        'partition model of the GPU-organised comparator)')
    chk('cluster_no_tu_endpoint', 'ot_hbm_accel_tu_endpoint' not in cl and 'ot_gpu_coll_system' in cl,
        'the integrated cluster wires the SIMT SMs to ot_gpu_coll_system (GPU comparator collective); the HBM '
        'accelerator TU endpoint is not instantiated with any SU-side producer')

    sink = ports(rd('w2_sink'), 'ot_hbm_integrated_w2_result_sink')
    chk('w2_sink_ports', all(s in sink for s in ('input wire result_v', 'input wire [11:0] result_row',
                                                   'input wire [255:0] result_data', 'output wire [336:0] req',
                                                   'input wire [272:0] rsp')),
        'w2_result_sink: no-ready capture (result_v, row 12, data 256) and a valid/ready provider req 337 / rsp 273')

    rp_ports = ports(rd('result_provider'), 'ot_hbm_sm_result_provider')
    chk('result_provider_ports', all(s in rp_ports for s in ('input wire result_v', 'input wire [11:0] result_row',
                                                             'input wire [255:0] result_data', 'output wire req_v',
                                                             'input wire req_r', 'input wire rsp_v', 'output wire rsp_r',
                                                             'input wire reserve_v', 'output wire reserve_r')),
        'ot_hbm_sm_result_provider (SM-control native result store): reserve_v/reserve_r, no-ready capture, '
        'valid/ready write+readback request / response, publication_v/publication_r')
    rpc = json.loads(rd('rp_component'))
    full = next(c for c in rpc['cases'] if c['name'] == 'full4096_reverse_order')
    mfull = re.search(r'rows=(\d+).*cycles=(\d+)', full['stdout'])
    chk('result_provider_component', rpc['verdict'] == 'PASS' and rpc['physical_admitted'] is False
        and 'test memory, not die service' in rpc['scope'] and mfull is not None,
        f"component PASS (full4096), scope '{rpc['scope']}', physical_admitted false, floorplan_fit "
        f"{rpc['model']['floorplan_fit']}")
    rp_rows, rp_cycles = int(mfull.group(1)), int(mfull.group(2))
    rp_model = rpc['model']

    gb = ports(rd('gather_bridge'), 'ot_hbm_integrated_gather_bridge')
    chk('gather_bridge_unrelated', 'input wire [511:0] req_data' in gb and re.search(r'score', rd('gather_bridge')) is not None
        and 'result_v' not in gb and 'rdata' not in gb,
        'ot_hbm_integrated_gather_bridge is a 512-b score / ID store-and-read memory (kinds: source read, score store, '
        'ID store, formatter read, final ID sink); it has no SM result input')

    tu = rd('tu_endpoint')
    tup = ports(tu, 'ot_hbm_accel_tu_endpoint')
    hubw = int(re.search(r'parameter integer HUBW\s*=\s*(\d+)', tu).group(1))
    inj = int(re.search(r'parameter integer INJ\s*=\s*(\d+)', tu).group(1))
    dl = int(re.search(r'parameter integer DEL\s*=\s*(\d+)', tu).group(1))
    lanes = int(re.search(r'parameter integer LANES\s*=\s*(\d+)', tu).group(1))
    pwb = int(re.search(r'parameter integer PWB\s*=\s*(\d+)', tu).group(1))
    chk('tu_endpoint_ports', all(s in tup for s in ('output wire [INJ*16-1:0]    inj_idx', 'output wire [INJ-1:0]       inj_rd',
                                                    'input  wire [INJ*FW-1:0]    inj_data',
                                                    'output wire [DEL-1:0]       del_valid'))
        and 'del_ready' not in tup and 'inj_v' not in tup and f'.D(HUBW)' in tu,
        f'TU endpoint: injection is a PULL (inj_idx 16 / inj_rd per stream, inj_data FW={32 * lanes} b per stream, '
        f'INJ={inj}, a read returns after the HUBW={hubw} hub wire stages inside the endpoint); delivery is a PUSH '
        f'with NO ready (del_valid / del_flit, DEL={dl} flits of {pwb} b a cycle), so the consumer must sink every '
        f'delivered flit; both HUBW chains are inside the measured endpoint cycles')

    rel = json.loads(rd('relay_record'))
    chk('relay_slice_scope', 'not production' in rel['scope'] and 'die adoption' in rel['scope'],
        f"ot_hbm_result_relay_slice: '{rel['scope']}'; required before adoption: {rel['required_before_adoption']}")
    dg = json.loads(rd('delay_gate'))
    chk('delay_bank_scope', dg['status'] == 'COMPONENT_EXACTNESS_PASS_PHYSICAL_OPEN' and dg['selected'] is False,
        f"ot_hbm_result_delay_bank {dg['full_shape']}: {dg['status']}, selected false")

    # ---------------------------------------------------------------- die view: hfd_su is an envelope
    hs = rd('hfd_su')
    r_w = int(re.search(r'input\s+wire\s+\[(\d+):0\]\s+r,', hs).group(1)) + 1
    xor_r = len(re.findall(r'\^ r_i1\[\d+\]', hs))
    chk('hfd_su_envelope', hs.startswith('// tools/hbm_hub_quarter_gen.py --quarter su: PHYSICAL ENVELOPE') and xor_r > 0
        and 'ot_hbm_accel_su_parent_exec' not in hs,
        f'hfd_su: header says PHYSICAL ENVELOPE; its r input ({r_w} b) is registered twice and XOR-folded into the '
        f'result chains ({xor_r} XOR terms read r_i1); no SU controller / ingress is instantiated')
    qg = rd('quarter_gen')
    chk('quarter_gen_disclaimer', 'It is NOT the SU / SFU / HC function' in qg and 'PHYSICAL ENVELOPE' in qg,
        'tools/hbm_hub_quarter_gen.py: "This is a PHYSICAL ENVELOPE ... It is NOT the SU / SFU / HC function: the SU '
        'controller (CTL12) and the die-port protocol of these blocks are not built"')
    plan = json.loads(rd('hfd_su_plan'))

    # ---------------------------------------------------------------- die model (r23)
    F, PR, m, rp, cm, priced = die_model()
    chk('generator_round', F.FINAL_ROUND == 'r23', f'generator FINAL_ROUND {F.FINAL_ROUND}')
    ins = {i.name: i for i in m['insts']}
    res_buses = [b for b in m['buses'] if b[1] in ('result_leaf', 'result_trunk')]
    ends = sorted({n for b in res_buses for n, _ in b[3]})
    stations = [n for n in ends if n in ins and ins[n].master not in ('hfd_su', 'hfd_sm')]
    sus = [n for n in ends if n in ins and ins[n].master == 'hfd_su']
    sms = [n for n in ends if n in ins and ins[n].master == 'hfd_sm']
    st_area = sum(ins[n].w * ins[n].h for n in stations)
    st_masters = sorted({ins[n].master for n in stations})
    relay_res = [r for r in m['relay_ends'] if r[0].startswith(('rl_', 'rh_', 'rt_'))]
    bw = {b[0]: b[2] for b in res_buses}
    relay_bits = sum(bw[r[0]] for r in relay_res)
    rpaths = {k: v for k, v in rp.items() if k.startswith('result_')}
    worst = max(rpaths, key=lambda k: (rpaths[k]['stages_430'], rpaths[k]['routed_um']))
    S = priced['one_way_cycles']
    terms = priced['compositions']['ds_matched']['terms']
    counts = priced['compositions']['ds_matched']['counts']
    chk('die_result_tree', len(sms) == 32 and len(sus) == 4 and all(bw[b] for b in bw),
        f'{len(sms)} SM r faces ({sm_bits} b) -> {len(stations)} gather / waypoint stations ({", ".join(st_masters)}) -> '
        f'{len(sus)} hfd_su r faces ({r_w} b); {len(res_buses)} buses, {sum(bw.values())} bus bits')
    chk('result_gather_hidden', terms['result_gather']['cycles_each'] == 0 and S['result'] < 2 * S['control'],
        f"die price: result_gather = barrier x max(0, result {S['result']} - 2 x control {S['control']}) = 0 per "
        f"barrier on the r23 Manhattan floor ('{terms['result_gather']['basis']}')")

    # ---------------------------------------------------------------- composition counts and rows
    mt = json.loads(rd('matched'))
    path = mt['path']
    nbar = sum(1 for t in path if t['node'] == 'barrier')
    chk('barrier_count', nbar == counts['barrier'] == 343, f'matched AR walk: {nbar} barriers (= SM -> consumer handoffs)')
    nxt = {}
    for i, t in enumerate(path):
        if t['node'] == 'barrier' and i + 1 < len(path):
            k = path[i + 1]['node'].split(':')[0]
            nxt[k] = nxt.get(k, 0) + 1
    seqs = {k: json.loads(rd(k)) for k in ('seq_ar', 'seq_wg', 'seq_other')}
    nodes = {}
    for t in path:
        if t['node'].startswith('sm:'):
            nodes[t['node']] = nodes.get(t['node'], 0) + 1
    need(set(nodes) == set(NODE_OPS), f'SM node set changed: {sorted(set(nodes) ^ set(NODE_OPS))}')
    rows_tab, rows_tok, rmax = [], 0, 0
    for n, c in sorted(nodes.items(), key=lambda kv: -kv[1]):
        r = 0
        for sk, tag in NODE_OPS[n]:
            op = [o for o in seqs[sk]['ops'] if o['tag'] == tag]
            need(len(op) == 1 and op[0]['exact'] and op[0]['rtl']['results'] == op[0]['rows'],
                 f'{sk}:{tag} not a unique exact op')
            r += op[0]['rows']
        rmax = max(rmax, max(next(o['rows'] for o in seqs[sk]['ops'] if o['tag'] == tag) for sk, tag in NODE_OPS[n]))
        rows_tab.append(dict(node=n, count=c, rows_per_sm=r, est=n in NODE_EST))
        rows_tok += c * r
    chk('rows_per_token', rows_tok > 0, f'{rows_tok} result rows (256 b) per SM per AR token; max rows one op {rmax}')

    # ---------------------------------------------------------------- publication ledger lines
    led = rd('closure_ledger')
    mg = re.search(r'\| stations gather a2 \+1 \| (\d+) \| ([\d.]+) \|', led)
    chk('ledger_gather_line', mg is not None and int(mg.group(1)) == counts['barrier'] * 1,
        f'closure_cost_ledger.md "stations gather a2 +1": {mg.group(1)} cycles/token, {mg.group(2)} % AR '
        '(+1 per barrier for the die-view gather station a2 register, charged unconditionally)')
    rc = json.loads(rd('recompose_r23'))
    chk('recompose_gather', rc['ledger']['gather'] == 1 and rc['bases']['stages_430']['extra_cycles']['gather'] == 343,
        'recompose_r23_r23cwire__cp_in_su.json: ledger gather 1 -> extra_cycles.gather 343 (all three bases)')
    h23 = json.loads(rd('headline_r23'))['with_closure']
    mc = re.search(r'\| collective SU faces \+6 \| (\d+) \|', led)
    chk('ledger_coll_faces', mc is not None and int(mc.group(1)) == 6 * counts['coll_terms'],
        f'closure ledger "collective SU faces +6": {mc.group(1)} cycles (6 x {counts["coll_terms"]} collectives)')
    pre = json.loads(rd('su_provider_prertl'))
    chk('su_provider_prior_verdict', 'NOT an acceleration credit' in json.dumps(pre),
        'results/uarch/hbm_su_parent_join_20261005/pre_rtl.json already rules the SU sector-provider path a '
        '"functional-integration candidate, NOT an acceleration credit"')

    # ---------------------------------------------------------------- quantification
    hz = CLK_HZ
    us = lambda c: round(c / hz * 1e6, 3)  # noqa: E731
    ar_u, st_u = UNIFIED['unified_candidate']['AR_us'], UNIFIED['unified_candidate']['MTP_step_us']
    ar_r, st_r = h23['AR_us'], h23['MTP_step_us']

    def pct(c, base):
        return round(100 * c / hz * 1e6 / base, 3)

    published = counts['barrier'] * 1 + counts['barrier'] * terms['result_gather']['cycles_each']
    ingress = 2      # SU result-ingress FIFO write -> read (estimate: registered write, registered read)
    native_slack = 2 * S['control'] - (S['result'] + ingress)
    native = counts['barrier'] * (1 + ingress)       # conservative: station + ingress charged even though hidden
    per_row = DRAIN_FIXED + T_RTT_FLOOR + T_RTT_FLOOR + T_RTT_FLOOR      # write, readback, SU read
    store_fwd = rows_tok * per_row
    rp_drain_tb = round((rp_cycles - rp_rows) / rp_rows, 3)
    tb_fwd = round(rows_tok * (rp_drain_tb + 1))      # the component bench's own 1-cycle test memory (+1 SU read)
    hubw_die = S['su_coll'] + S['coll_su'] + 6
    hubw_give = counts['coll_terms'] * (2 * hubw - hubw_die)

    def row(c, note):
        return dict(cycles_per_token=c, us=us(c), AR_pct_of_unified=pct(c, ar_u), MTP_pct_of_unified_step=pct(c, st_u),
                    AR_pct_of_r23=pct(c, ar_r), note=note)

    impact = dict(
        published_synthetic=row(published, 'what the r23 closure ledger / unified ledger charge today for SM -> SU '
                                'results: 0 exposed wire (hidden under the barrier round trip) + gather a2 +1 per '
                                'barrier.  This is the cost of a native level-2 edge (SM rows straight into SU lane '
                                'registers) that does NOT exist in RTL: the die-view path ends in an XOR envelope'),
        native_edge_proposed=row(native, f'proposed native edge (relay slices + real merge + SU result-ingress FIFO '
                                 f'with a row-count release): wire {S["result"]} one-way hidden under the barrier '
                                 f'round trip 2 x {S["control"]} with {native_slack} cycles slack at the r23 floor '
                                 f'(r23c routed bound: 72 vs 144, scratch GRT, not pinned); station +1 and ingress '
                                 f'+{ingress} charged per barrier although hidden (conservative); estimate until built'),
        rtl_store_and_forward_floor=row(store_fwd, f'the path the committed RTL implements: result store capture, '
                                        f'per-row write + readback through the shared provider, then SU sector read, '
                                        f'one outstanding: {rows_tok} rows x ({DRAIN_FIXED} + 3 x {T_RTT_FLOOR}) = '
                                        f'{store_fwd}; FLOOR estimate (CDC/L2 only, no HBM write-through ack, every '
                                        f'SM store and memory port assumed parallel; the integrated cluster has ONE '
                                        f'sink per die)'),
        rtl_store_and_forward_testmemory=row(tb_fwd, f'same path at the component bench\'s own test memory (1-cycle '
                                             f'response, ready 4 of 5 cycles): {rp_drain_tb} drain cycles/row measured '
                                             f'(full4096 {rp_cycles} cycles) + 1 SU read; not a die service'),
    )
    impact['delta_native_vs_published'] = row(native - published, 'correction if the native edge is adopted as proposed')
    impact['delta_store_forward_floor_vs_published'] = row(store_fwd - published,
                                                           'correction if publication must use the implemented RTL path')
    impact['collective_hubw_reconciliation_not_credited'] = row(
        -hubw_give, f'NOT a correction: the measured TU endpoint cycles carry HUBW={hubw} hub wire stages each way; the '
        f'die price adds SU<->endpoint {S["su_coll"]}+{S["coll_su"]} and the closure ledger +6 faces on top '
        f'({counts["coll_terms"]} collectives).  If the endpoint is re-measured with HUBW = the die path, up to '
        f'{hubw_give} cycles come back; no credit until that measurement')

    edges = [
        dict(id='E1', edge='SM matrix element (ot_hbm_accel_sm_v) result pins -> native result store (SM control)',
             producer='ot_hbm_accel_sm_v rv / rrow[11:0] / rdata[255:0] / fault', consumer='ot_hbm_sm_result_provider '
             'result_v / result_row / result_data (or the integrated ot_hbm_integrated_w2_result_sink)',
             bits=dict(sm_face=sm_bits, capture_boundary=rp_model['capture_boundary_bits']),
             protocol='one-way valid, NO ready; <= 1 row a cycle; rows per op from the descriptor (op_rows <= 4096); the '
                      'store must accept every row (reservation before start: reserve_v / reserve_r)',
             rate='1 row (32 B) a cycle per SM at 1.2 GHz while a column emits; rows per op 1..43 on the DS AR walk',
             latency=dict(cls='rtl-measured (SM side)', cycles='PIO=2 pin stages inside the measured SM start->done; '
                          'store capture +1 (component)'),
             die_route='none: the r23 floorplan has no result-store block; the SM r face is routed to the gather tree',
             credit='reservation (rows granted before start); no round-trip credit needed for a no-ready source',
             area=dict(cls='rtl-component model', per_store_um2=round(rp_model['macro_area_um2'], 1),
                       macros=rp_model['macro_count'], note='40 x ot_sram_2rw_512x64 per 4096 x 256 store; '
                       f'{len(sms)} SMs -> {round(len(sms) * rp_model["macro_area_um2"] / 1e6, 2)} mm2 if one store per SM '
                       '(ownership/count is the SM-control owner\'s decision); floorplan_fit false'),
             status=dict(producer='implemented-in-RTL', store='implemented-in-RTL (component, test-memory peer)',
                         join_to_sm_v='missing (cluster feeds the sink from top-level pins; the cluster SM is SIMT)',
                         die='missing')),
        dict(id='E2', edge='native result store -> shared service (memory provider) write + readback',
             producer='ot_hbm_sm_result_provider req_v/req_r/req_we/req_addr[36:0]/req_data[255:0]/req_tag[15:0]',
             consumer='shared provider port (integrated: p_req[2] -> ot_gpu_mreq_cdc AW3 -> ot_gpu_memsys_adapter)',
             bits=dict(request=rp_model['request_boundary_bits'], request_with_strobes=rp_model[
                 'shared_provider_request_with_strobes_bits'], response=rp_model['return_bits']),
             protocol='valid/ready both ways, ONE outstanding, write then readback compare per 32-B row; publication '
                      'only after every row is written, acknowledged and read back',
             rate='component: (cycles-rows)/rows = %.3f cycles/row at 1-cycle test memory' % rp_drain_tb,
             latency=dict(cls='rtl-measured (test memory) / estimate (die service)',
                          tb_cycles_full4096=rp_cycles, per_row_formula=rp_model['drain_cycles_per_row'],
                          die_floor_per_row=DRAIN_FIXED + 2 * T_RTT_FLOOR, estimate_basis=EST['note']),
             die_route='no die block or route: the GPU-organised memsys has no place in the r23 accelerator floorplan',
             credit='single outstanding (no credit pool); CDC FIFO 8 entries each way',
             area=dict(cls='rtl', note='mreq_cdc 2 x 8-entry FIFOs (337 b / 273 b) per client; memsys is the '
                       'comparator\'s xbar / L2 / HBM model'),
             status=dict(rtl='implemented-in-RTL (integrated join, GPU-comparator backend)', die='missing')),
        dict(id='E3', edge='shared service -> SU operand read (the SU\'s only data input in RTL)',
             producer='ot_gpu_memsys_adapter via ot_gpu_mreq_cdc response (tag 16 / we / data 256)',
             consumer='ot_hbm_accel_su_parent_exec rsp_v/rsp_rdy/rsp[272:0] (request req[336:0])',
             bits=dict(request=337, response=273),
             protocol='valid/ready, one outstanding (selection.json: "one-outstanding actual latency sums measured '
                      'ready waits + full request/response CDC/backend round trips")',
             rate='one 32-B sector per round trip',
             latency=dict(cls='estimate', floor_cycles=T_RTT_FLOOR, basis=EST['note']),
             die_route='hfd_su f_vm / t_vm faces (2048 b each) exist in the die view; their payload is XOR-folded',
             credit='single outstanding', area=dict(cls='rtl', note='inside su_provider adapter / margin; not '
                                                  'separately recorded'),
             status=dict(rtl='implemented-in-RTL (GPU-comparator memsys)', die='exists-only-in-die-view (envelope)')),
        dict(id='E4', edge='die-view result tree: SM r face -> gather stations -> hfd_su.r',
             producer=f'{len(sms)} hfd_sm r faces ({sm_bits} b)', consumer=f'{len(sus)} hfd_su r inputs ({r_w} b)',
             bits=dict(leaf=sm_bits, trunk=r_w, total_bus_bits=sum(bw.values())),
             protocol='none: registered wires, no valid/ready, no merge arbitration (trunk = 8 SM rows side by side); '
                      'hfd_su XOR-folds r into its result chains',
             rate='would carry 8 rows a cycle per stack half if a consumer existed',
             latency=dict(cls='die-model', one_way_cycles_incl_meso=S['result'], worst_path=worst,
                          worst_um=rpaths[worst]['routed_um'], worst_stages_430=rpaths[worst]['stages_430'],
                          segments=rpaths[worst]['segments'], control_one_way=S['control']),
             die_route=f'SM r (E face) -> rg<st>{{0,3,1,2}} gather stations beside row 1 -> rh arms -> rt trunk '
                       f'waypoints in channel 2 -> hub edge -> hfd_su S/N r face; {len(stations)} station instances, '
                       f'{len(relay_res)} r22 relay ends on result buses ({relay_bits} relay bits)',
             credit='none (no flow control)',
             area=dict(cls='die-model', station_instances=len(stations), station_masters=st_masters,
                       station_area_um2=round(st_area, 1), relay_ends=len(relay_res), relay_bits=relay_bits,
                       relay_raw_dff_um2_TT=round(relay_bits * rel['mapping']['cell_area_um2'], 1),
                       hfd_su_boundary_flops_for_r=2 * r_w),
             status=dict(wires_and_stations='exists-only-in-die-view', consumer='missing (envelope)',
                         relay_primitive='implemented-in-RTL as component (ot_hbm_result_relay_slice, not adopted)')),
        dict(id='E5', edge='SU -> TU collective endpoint injection, endpoint -> SU delivery',
             producer='SU (would hold the injection buffer)', consumer='ot_hbm_accel_tu_endpoint inj_idx/inj_rd/inj_data; '
                                                                       'del_valid/del_flit back',
             bits=dict(inj_data=inj * 32 * lanes, delivery=dl * pwb, die_view_t_coll=1024, die_view_f_coll=580),
             protocol=f'pull injection (index + read strobe, fixed HUBW={hubw} latency), push delivery with no ready '
                      f'({dl} flits a cycle)',
             rate=f'inj {inj} x {32 * lanes} b a cycle; delivery up to {dl} x {pwb} b a cycle vs die-view return 580 b',
             latency=dict(cls='rtl-measured inside endpoint (HUBW both ways) + die-model', die_one_way=dict(
                 su_coll=S['su_coll'], coll_su=S['coll_su']), endpoint_hubw_each_way=hubw),
             die_route='hfd_su t_coll / f_coll faces <-> collective endpoint (spine); +6 face stages in the ledger',
             credit='none on delivery (consumer must sink DEL flits a cycle); switch credits inside the endpoint',
             area=dict(cls='missing', note='no SU-side injection buffer or delivery sink exists'),
             status=dict(endpoint='implemented-in-RTL', su_side='missing', die='exists-only-in-die-view (envelope)',
                         width_check=f'die-view return 580 b < RTL delivery {dl * pwb} b: needs DEL=1 pacing measured '
                                     'or a wider face')),
    ]

    proposal = dict(
        contract='native level-2 SM -> SU result edge (AGENTS dataflow level 2: producer results staged at the hub '
                 'edge and delivered straight into lane registers)',
        items=[
            f'SM r face {sm_bits} b one-way, rows <= descriptor op_rows; SU grants a reservation of op_rows rows per '
            f'SM at issue (cmdproc), so no ready / credit return crosses the die (max {rmax} rows per SM per op on '
            f'the DS walk)',
            f'transport: ot_hbm_result_relay_slice x {-(-sm_bits // 64)} per station (64-b slices) at every gather '
            f'station and relay end of the r23 tree ({len(stations)} stations, {len(relay_res)} relay ends); the 8-SM '
            f'trunk stays a parallel bundle (no arbitration needed)',
            f'SU result ingress (NEW, SU owner): per SM lane a FIFO of >= {rmax} rows x 268 b (rrow + rdata) with a row '
            f'counter; release / start of the consumer is gated on count == op_rows (ordering by protocol, not by the '
            f'{native_slack}-cycle timing slack); estimate {round(len(sms) * rmax * 268 * rel["mapping"]["cell_area_um2"] / 1e6, 3)} '
            f'mm2 raw DFF (TT cell area, {len(sms)} lanes) or 2 x 512x64 SRAM per lane',
            'collective: the SU ingress also feeds the endpoint injection buffer (pull by index); endpoint delivery '
            f'needs a {dl}-flit/cycle sink or a measured DEL=1 pacing',
            'result store (SM control) stays the publication / readback path for results that leave the die or must '
            'be retained; it is NOT on the per-token SM -> SU critical path',
        ],
        ledger_lines=dict(
            replace=dict(line='stations gather a2 +1 (343 cycles)', by='SM -> SU native result edge: station +1 and '
                         f'SU ingress +{ingress} per barrier ({native} cycles/token, {us(native)} us, '
                         f'+{pct(native - published, ar_u)} % AR vs today); status gated: sm_su_result_edge_native'),
            add_gate='sm_su_result_edge_native (unified ledger gated_by, HBM DS rows): hfd_su r face has no functional '
                     'consumer; the RTL path is store-and-forward through the GPU-comparator memsys',
            label='until the gate closes, HBM DS AR / MTP rows that rely on the result_gather term must say: SM -> SU '
                  'handoff priced as a native edge that is die-view-only (envelope)',
            not_credited=f'collective HUBW reconciliation ({hubw_give} cycles) stays uncredited until re-measured'),
    )

    summary = dict(
        verdict='The SM -> SU result handoff the composition prices (hidden wire + gather +1 = %d cycles/token) is '
                'not implemented: the die-view tree ends in an XOR envelope, and the committed RTL path is '
                'store-and-forward through the GPU-comparator memory system (>= %d cycles/token floor estimate). '
                'Proposed native edge: %d cycles/token (+%.3f %% AR on the unified candidate), gated.'
                % (published, store_fwd, native, pct(native - published, ar_u)),
        published_cycles=published, native_cycles=native, store_forward_floor_cycles=store_fwd,
        rows_per_token=rows_tok, barrier_handoffs=nbar, handoff_targets=nxt)

    return dict(
        schema='opentallas.hbm_sm_su_result_contract.v1',
        scope='HBM accelerator DS-V4.1 1M, r23 die generator, matched AR walk; Qwen8K HBM rows price no result gather '
              '(the W12 vehicle carries its own tree) and are unaffected',
        clock_hz=CLK_HZ, summary=summary, edges=edges, impact=impact, proposal=proposal,
        rows_table=rows_tab, die_one_way_cycles_r23_floor=S, composition_counts=counts,
        unified_ledger_reference=UNIFIED, estimate_parameters=EST,
        hfd_su_plan=dict(WI=plan['WI'], WO=plan['WO'], lanes=plan['lanes'], face_stages_r=plan['face_stages']['r']),
        checks=checks, inputs={SRC[k]: sha(k) for k in sorted(SRC)},
        tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())


if __name__ == '__main__':
    raise SystemExit(main())
