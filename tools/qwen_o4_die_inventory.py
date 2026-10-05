#!/usr/bin/env python3
"""Resource inventory of the Qwen3-8B O4 die as its RTL instantiates it (rung 1).

The die RTL is what rtl/test/tb_hdc_qwen_layer0_tp2.sv builds per die:
ot_hdc_core_vector_weight at G = 6,144, W = 16, INT8_WEIGHT = 1,
INT8_SCALE_WCS_BASE = 1 and every other parameter at its default, one
ot_rom_tp_seq, and one ot_rom_oneshot_allreduce per package. Its memories are
behavioural arrays in the TB.

Method. Yosys elaborates the core (hierarchy + proc, no optimisation) at
G = 8, 16, 32 and 64. From the elaborated netlist the tool counts module
instances and flip-flop / memory bits per module kind, recursively. Each
count is fitted exactly on G in {8, 16, 32} with the basis {G*log2(G), G, 1}
and the fit must reproduce G = 64 before it is evaluated at 6,144 (with
ceil(log2(6144)) = 13, the RTL's $clog2). A count that fails the hold-out is
reported as unfitted, not extrapolated.

Reachability. At G = 6,144 every shipped matrix runs with split >= 64, so at
most G >> 6 = 96 result-port groups exist; the per-lane post-scale
multipliers, the argmax leaves and the split-tree hold registers above those
ports are instantiated but can never carry a valid result. Both counts are
reported; the floorplan prices the instantiated one and names the saving.

Ledger rows (qwen3_budget.json) with no RTL instance are listed as gaps, never
substituted.
"""
import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/floorplan/qwen_o4_die_inventory.json'
YOSYS = os.environ.get('OT_YOSYS', '/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys')
CORE_SOURCES = ['rtl/hdc/ot_hdc_delay.sv', 'rtl/hdc/ot_hdc_fp32_mul_pipe.sv', 'rtl/hdc/ot_hdc_fpu.sv',
                'rtl/proto/ot_fp32_add_rne_pipe.sv', 'rtl/hdc/ot_hdc_sfu.sv', 'rtl/hdc/ot_hdc_fastfp.sv',
                'rtl/hdc/ot_hdc_matvec.sv', 'rtl/hdc/ot_hdc_dyn_ttiles.sv', 'rtl/hdc/ot_hdc_stream.sv',
                'rtl/hdc/ot_hdc_vstream.sv', 'rtl/hdc/ot_hdc_vstream_lane.sv', 'rtl/hdc/ot_hdc_vreduce.sv',
                'rtl/hdc/ot_hdc_reduce.sv', 'rtl/hdc/ot_hdc_reduce_q.sv', 'rtl/hdc/ot_hdc_sfu_q.sv',
                'rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv', 'rtl/hdc/ot_hdc_core_vector_weight.sv']
OTHER_SOURCES = ['rtl/test/tb_hdc_qwen_layer0_tp2.sv', 'rtl/rom/ot_rom_oneshot_allreduce.sv',
                 'results/arch/qwen3_budget.json', 'results/arch/qwen3_o4_rtl_gaps.json',
                 'results/floorplan/qwen_o4_unit_areas.json']
TOP = 'ot_hdc_core_vector_weight'
FIT_G = (8, 16, 32)
HOLDOUT_G = 64
G_DIE = 6144
W = 16
MIN_SPLIT_LOG2 = 6            # gate/up at G = 6144: S = 64 (hdc_qwen_fullshape_placement)
LEAVES = ('ot_hdc_bmul', 'ot_hdc_fadd', 'ot_hdc_qadd', 'ot_hdc_fmul', 'ot_hdc_fp32_mul_pipe',
          'ot_hdc_delay', 'ot_hdc_vline', 'ot_hdc_stream', 'ot_hdc_matvec', 'ot_hdc_dyn_ttiles',
          'ot_hdc_sfu', 'ot_hdc_reduce', 'ot_fp32_add_rne_pipe')
FF_TYPES = re.compile(r'^\$(a?dff|sdff|dffe|adffe|sdffe|sdffce|aldff|aldffe|dffsr|dffsre)$')


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def base_name(t):
    parts = t.split('\\')
    if parts[0].startswith('$paramod') and len(parts) > 1:
        return parts[1]
    return parts[-1]


def elaborate(g, work):
    js = Path(work) / f'core_g{g}.json'
    cmd = ' '.join(['read_verilog -sv'] + CORE_SOURCES) + '; ' + \
        f'hierarchy -top {TOP} -chparam G {g} -chparam W {W} -chparam INT8_WEIGHT 1 ' \
        f'-chparam INT8_SCALE_WCS_BASE 1; proc; write_json {js}'
    if not js.exists():
        subprocess.run([YOSYS, '-q', '-p', cmd], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    data = json.loads(js.read_text())
    mods = data['modules']
    memo = {}

    def walk(name):
        if name in memo:
            return memo[name]
        acc = {}
        m = mods[name]
        for cell in m['cells'].values():
            t = cell['type']
            if t in mods:
                sub = walk(t)
                for k, v in sub.items():
                    acc[k] = acc.get(k, 0) + v
                bn = base_name(t)
                acc['inst:' + bn] = acc.get('inst:' + bn, 0) + 1
            elif FF_TYPES.match(t):
                acc['ff_bits'] = acc.get('ff_bits', 0) + int(cell['parameters']['WIDTH'], 2)
            elif t in ('$mem', '$mem_v2'):
                p = cell['parameters']
                acc['mem_bits'] = acc.get('mem_bits', 0) + int(p['SIZE'], 2) * int(p['WIDTH'], 2)
        for mem in m.get('memories', {}).values():
            acc['mem_bits'] = acc.get('mem_bits', 0) + int(mem['size']) * int(mem['width'])
        memo[name] = acc
        return acc

    top = [n for n, m in mods.items() if m.get('attributes', {}).get('top')]
    total = walk(top[0])
    # per-kind flop bits: attribute each leaf module's own flops to its base name
    per_kind = {}
    for n in mods:
        own = sum(int(c['parameters']['WIDTH'], 2) for c in mods[n]['cells'].values() if FF_TYPES.match(c['type']))
        per_kind[n] = own
    kind_bits = {}

    def walk_kind(name, mult):
        m = mods[name]
        bn = base_name(name)
        kind_bits[bn] = kind_bits.get(bn, 0) + per_kind[name] * mult
        for cell in m['cells'].values():
            if cell['type'] in mods:
                walk_kind(cell['type'], mult)
    walk_kind(top[0], 1)
    out = {k: v for k, v in total.items()}
    for k, v in kind_bits.items():
        out['ffbits:' + k] = v
    return out


class _Keep:
    def __init__(self, path):
        self.path = str(path)

    def __enter__(self):
        return self.path

    def __exit__(self, *a):
        return False


def lg(g):
    return math.ceil(math.log2(g))


def fit(samples):
    """Exact fit of c(G) = a*G*log2(G) + b*G + c on the three FIT_G points."""
    import fractions
    rows = [[fractions.Fraction(g * lg(g)), fractions.Fraction(g), fractions.Fraction(1)] for g in FIT_G]
    ys = [fractions.Fraction(samples[g]) for g in FIT_G]
    # Gaussian elimination
    a = [r + [y] for r, y in zip(rows, ys)]
    for i in range(3):
        p = next(r for r in range(i, 3) if a[r][i] != 0)
        a[i], a[p] = a[p], a[i]
        for r in range(3):
            if r != i and a[r][i] != 0:
                f = a[r][i] / a[i][i]
                a[r] = [x - f * y for x, y in zip(a[r], a[i])]
    return [a[i][3] / a[i][i] for i in range(3)]


def evaluate(coef, g):
    return coef[0] * g * lg(g) + coef[1] * g + coef[2]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--output', type=Path, default=OUT)
    ap.add_argument('--work', type=Path, default=None,
                    help='keep the elaborated netlists here and reuse them (they must match the pinned sources)')
    args = ap.parse_args()
    if args.work:
        args.work.mkdir(parents=True, exist_ok=True)
    with (tempfile.TemporaryDirectory() if args.work is None else _Keep(args.work)) as work:
        with ThreadPoolExecutor(4) as ex:
            res = dict(zip(FIT_G + (HOLDOUT_G,), ex.map(lambda g: elaborate(g, work), FIT_G + (HOLDOUT_G,))))
    keys = sorted(set().union(*[set(r) for r in res.values()]))
    counts = {}
    for k in keys:
        s = {g: res[g].get(k, 0) for g in res}
        coef = fit(s)
        pred = evaluate(coef, HOLDOUT_G)
        ok = pred == s[HOLDOUT_G]
        counts[k] = dict(samples={str(g): s[g] for g in sorted(s)},
                         fit=[str(c) for c in coef], holdout_ok=ok,
                         at_6144=int(evaluate(coef, G_DIE)) if ok and evaluate(coef, G_DIE).denominator == 1 else None)
    c = {k: v['at_6144'] for k, v in counts.items()}
    units = json.loads((ROOT / 'results/floorplan/qwen_o4_unit_areas.json').read_text())
    ua = {u['module']: u['area_um2'] for u in units['units']}
    dff_um2 = units['dff_bit_um2']
    ports = G_DIE >> MIN_SPLIT_LOG2
    lanes = G_DIE * W
    reach = dict(
        result_port_groups=ports,
        fmul_instantiated=c.get('inst:ot_hdc_fmul'), fmul_reachable=ports * W,
        argmax_leaves_instantiated=lanes, argmax_leaves_reachable=ports * W,
        basis='ot_hdc_matvec: tile q of a round lands on group q after the split tree; scale_gre, the '
              'fmul valid and o_we all require group < G >> split; every G = 6144 matrix has split >= 64')
    # split-tree and argmax registers, from the RTL structure (ot_hdc_matvec g_lvl, argmax tree):
    # each of LG levels holds lq (G*W*32) and a TA-deep u_hold line (G*W*32 each); the flop
    # count is not fitted (it has clog2 and power-of-two padding terms) but read off the RTL.
    LGd = lg(G_DIE)
    TA = 3
    word = W * 32
    tree_inst = LGd * (TA + 1) * G_DIE * word
    # reachable: at level l only indices below max(G >> l, G >> min_split) can carry a result
    tree_reach = sum((TA + 1) * max(G_DIE >> l, ports) * word for l in range(1, LGd + 1))
    tree = dict(levels=LGd, registers_per_level_per_word=TA + 1, word_bits=word,
                flop_bits_instantiated=tree_inst, flop_bits_reachable=tree_reach,
                basis='rtl/hdc/ot_hdc_matvec.sv g_lvl: lq and u_hold (ot_hdc_delay W = G*W*32, D = TA) per level')
    # pricing (pre-layout ASAP7 TT cell area; routed utilisation is applied by the floorplan)
    priced = dict(
        bmul_mm2=c['inst:ot_hdc_bmul'] * ua['ot_hdc_bmul'] / 1e6,
        fadd_mm2=c['inst:ot_hdc_fadd'] * ua['ot_hdc_fadd'] / 1e6,
        qadd_mm2=c['inst:ot_hdc_qadd'] * ua['ot_hdc_qadd'] / 1e6,
        fmul_instantiated_mm2=c['inst:ot_hdc_fmul'] * ua['ot_hdc_fmul'] / 1e6,
        fmul_reachable_mm2=ports * W * ua['ot_hdc_fmul'] / 1e6,
        split_tree_flop_mm2_instantiated=tree_inst * dff_um2 / 1e6,
        split_tree_flop_mm2_reachable=tree_reach * dff_um2 / 1e6,
        basis='results/floorplan/qwen_o4_unit_areas.json (yosys 0.68 + ABC -D 910 on ASAP7 RVT TT, '
              'pre-layout); flop bits from the elaborated netlist, including the units\' internal flops')
    budget = json.loads((ROOT / 'results/arch/qwen3_budget.json').read_text())
    area = budget['area']
    gaps = [
        dict(item='lane copies m = 5', ledger=f"{area['lane_copy_mm2']} mm2 x {area['lane_copies_added']} copies",
             rtl='0 instances (ot_hdc_lane_copy only in ot_hdc_qwen_m5_mac_array unit benches)'),
        dict(item='stream unit width', ledger='SW = 1,024 (spill 12.8 mm2)',
             rtl='SU_VEC = 0: scalar ot_hdc_stream, SW = 1'),
        dict(item='KV service', ledger=f"4 HBM3E stacks, KV prefetch {area['kv_prefetch_buffer_mm2']} mm2",
             rtl='KV_HBM = 0: G behavioural KV read ports in the TB; ot_hdc_qwen_kv_system and '
                 'ot_hdc_qwen_hbm_service are instantiated only by unit benches'),
        dict(item='HBM PHY / controllers', ledger=f"{area['hbm_phy_mm2']} mm2", rtl='none'),
        dict(item='UCIe PHY', ledger=f"{area['ucie_phy_mm2']} mm2",
             rtl='ot_rom_ucie_link behavioural delay-line model inside ot_rom_oneshot_allreduce'),
        dict(item='DFlash drafter / accept', ledger=f"drafter ROM {area['drafter_rom_mm2']} mm2",
             rtl='no Qwen drafter program; ot_hdc_qwen_dflash_step_ctrl only in unit benches'),
        dict(item='INT8 embedding path', ledger='INT8 rows + BF16 scale (spec C5)',
             rtl='INT8_EMBED = 0 in the TP-2 TB: the stream unit reads BF16 embedding words'),
        dict(item='memories', ledger='code/scale ROM, VM, KV ring, constants',
             rtl='behavioural arrays in the TB with G read ports; no macro instance'),
        dict(item='physical partition', ledger='6,144 groups a die',
             rtl='one monolithic ot_hdc_matvec: a single issue FSM and one wrom_addr broadcast; the '
                 'neighbourhood cut replicates the FSM per 4 groups, which needs a global group offset '
                 'the module does not have (its split masks use the local group index)'),
    ]
    rec = dict(
        schema='opentallas.qwen-o4-die-inventory.v1',
        status='rtl_inventory_extrapolated_with_holdout',
        tool='tools/qwen_o4_die_inventory.py',
        source_sha256={p: sha(p) for p in CORE_SOURCES + OTHER_SOURCES},
        tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        die_rtl=dict(top=TOP, parameters=dict(G=G_DIE, W=W, IL=8, INT8_WEIGHT=1, INT8_SCALE_WCS_BASE=1,
                                              SU_VEC=0, SW=1, KV_HBM=0, W_HBM=0, INT8_EMBED=0),
                     package=['ot_rom_tp_seq per die', 'ot_rom_oneshot_allreduce N=2 per package (2 die '
                              'engines, 2 ot_rom_ucie_link models, 16 FP32 adders a die)'],
                     basis='rtl/test/tb_hdc_qwen_layer0_tp2.sv'),
        method=dict(fit_g=list(FIT_G), holdout_g=HOLDOUT_G, basis='{G*clog2(G), G, 1}',
                    note='elaborated without optimisation: counts are what the RTL instantiates'),
        counts=counts,
        at_6144={k: v for k, v in c.items() if v is not None},
        reachability=reach, split_tree_registers=tree, priced=priced,
        ledger_gaps=gaps)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=1) + '\n')
    bad = [k for k, v in counts.items() if not v['holdout_ok']]
    print(json.dumps(dict(unfitted=bad, fmul=c.get('inst:ot_hdc_fmul'), bmul=c.get('inst:ot_hdc_bmul'),
                          qadd=c.get('inst:ot_hdc_qadd'), ff_bits=c.get('ff_bits'), priced=priced), indent=1))


if __name__ == '__main__':
    main()
