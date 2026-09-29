#!/usr/bin/env python3
"""Integer ROM image placement of one Qwen3-8B O4 TP-2 die onto ASAP7 macro views.

Rung 2 of docs/INTEGRATED_PHYSICAL_PLAN.md for the Qwen ROM die. Every weight
word, scale word, embedding row and constant goes to a named macro bank with
whole-macro counts; nothing is fractional. The matrix geometry is
tools/hdc_qwen_fullshape_placement.py (the RTL tiling rule hdc_program uses),
the drafter is placed with the same rule (fc at the golden's S = 4096, which
ot_hdc_matvec runs with 2,048 idle groups), and the macro views are
physical/asap7_memory_macros (predictive ASAP7 LEF/Liberty).

What is NOT established here: ROM contents (no checkpoint is read), macro
timing beyond the view's Liberty, the embedding/constant read ports of the
die RTL (see qwen_o4_die_inventory.py), and anything about N6 area.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hdc_golden as GOLD  # noqa: E402
import hdc_qwen_fullshape_placement as FP  # noqa: E402

OUT = ROOT / 'results/floorplan/qwen_o4_rom_placement.json'
MACROS = ROOT / 'physical/asap7_memory_macros/index.json'
TB = ROOT / 'rtl/test/tb_hdc_qwen_layer0_tp2.sv'
MATVEC = ROOT / 'rtl/hdc/ot_hdc_matvec.sv'
BUDGET = ROOT / 'results/arch/qwen3_budget.json'
SOURCES = [Path('tools/hdc_qwen_fullshape_placement.py'), Path('tools/hdc_golden.py'),
           Path('compiler/models/qwen3-8b/config.json'),
           Path('physical/asap7_memory_macros/index.json'),
           Path('rtl/test/tb_hdc_qwen_layer0_tp2.sv'), Path('rtl/hdc/ot_hdc_matvec.sv'),
           Path('rtl/physical/ot_qwen_o4_g4_rommac.sv'), Path('results/arch/qwen3_budget.json')]

G, W, IL = 6144, 16, 8
PAIR_BITS = 2 * W * 8                 # a group pair's 256-bit slice of the 786,432-bit code word
TP = 2
# DFlash drafter: fc 4096 x 20480 (5 target taps), 5 Qwen3-shaped layers (qwen3_o4_rtl_gaps.py)
DRAFTER_LAYERS = 5
DRAFTER_FC = (4096, 5 * 4096)
CLOCK_NS = 1e9 / 1098640000.0         # results/arch/qwen3_budget.json clock_hz
UNCERTAINTY_NS = 0.060


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def drafter_fc(base):
    """fc slice (2,048 x 20,480 a die) at the golden split S = 4,096.

    6,144 is not a multiple of 4,096, so FP.matrix refuses it; ot_hdc_matvec
    runs it with G >> 12 = 1 tile a round and groups 4,096..6,143 idle
    (x_re / e_gm masks). Words = rounds x kc x IL, the matvec's own count.
    """
    n, k = DRAFTER_FC[0] // TP, DRAFTER_FC[1]
    split = GOLD.split_for(n, k, G, W, IL)
    kc = k // split
    per_round = G // split
    tiles = -(-n // (W * IL))
    rounds = -(-tiles // per_round)
    words = rounds * kc * IL
    return {'name': 'D.fc', 'base': base, 'end': base + words, 'words': words, 'rows': n,
            'columns': k, 'split': split, 'k_per_split': kc, 'tiles_per_round': per_round,
            'rounds': rounds, 'scale_rows': n, 'scale_words': -(-n // W),
            'idle_groups': G - per_round * split}


def image():
    target = FP.placement()
    mats = [dict(m) for m in target['matrices_per_die']]
    base = target['matrix_code_words_per_die']
    sbase = target['matrix_scale_words_per_die']
    fc = drafter_fc(base)
    fc['scale_base'], fc['scale_end'] = sbase, sbase + fc['scale_words']
    mats.append(fc)
    base, sbase = fc['end'], fc['scale_end']
    h, nh, kv, hd, ff = 4096, 32, 8, 128, 12288
    dims = [('qkv', (nh // 2 + 2 * kv // 2) * hd, h), ('o', h, nh // 2 * hd),
            ('gu', ff, h), ('down', h, ff // 2)]
    for layer in range(DRAFTER_LAYERS):
        for name, n, k in dims:
            m = FP.matrix(base, f'D{layer}.{name}', n, k, G)
            m['scale_base'], m['scale_end'] = sbase, sbase + m['scale_words']
            mats.append(m)
            base, sbase = m['end'], m['scale_end']
    return target, mats, base, sbase


def port_scale_words(mats):
    """Scale words each result-port group reads (ot_hdc_matvec g_post_scale).

    After the split tree, tile r*(G/S)+q lands on port group q; group q reads
    words sbase + r*(G/S)*IL + q*IL + j (j < IL) for its valid tiles only.
    """
    ports = max(m['tiles_per_round'] for m in mats)
    words = [0] * ports
    addrs_per_matrix_group0 = 0
    for m in mats:
        tiles = -(-m['rows'] // (W * IL))
        per_round = m['tiles_per_round']
        for q in range(per_round):
            valid = sum(1 for r in range(m['rounds']) if r * per_round + q < tiles)
            words[q] += valid * IL
        addrs_per_matrix_group0 += IL * m['rounds']
    return ports, words


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--output', type=Path, default=OUT)
    args = ap.parse_args()

    cat = json.loads(MACROS.read_text())['macros']
    code_m = 'ot_rom_4096x266_m8'
    dense_m = 'ot_rom_8192x266_m8'
    narrow_m = 'ot_rom_4096x72_m8'
    geom = {n: dict(width_um=cat[n]['width_um'], height_um=cat[n]['height_um'],
                    area_um2=cat[n]['area_um2'], capacity_bits=cat[n]['capacity_bits'],
                    clk_to_q_tt_ps=cat[n]['clk_to_q_ps']['tt'], min_period_tt_ps=cat[n]['min_period_ps']['tt'])
            for n in (code_m, dense_m, narrow_m)}
    depth = {code_m: 4096, dense_m: 8192, narrow_m: 4096}

    target, mats, code_words, scale_words = image()
    target_words = target['matrix_code_words_per_die']
    drafter_words = code_words - target_words
    columns = G // 2                                        # group-pair word columns
    banks = -(-code_words // depth[code_m])
    code = dict(macro=code_m, word_columns=columns, useful_bits_per_macro_word=PAIR_BITS,
                spare_bits_per_macro_word=10, words_per_column=code_words,
                target_words=target_words, drafter_words=drafter_words,
                banks_per_column=banks, bank_depth=depth[code_m],
                padding_words_per_column=banks * depth[code_m] - code_words,
                macros=columns * banks, area_mm2=columns * banks * geom[code_m]['area_um2'] / 1e6,
                bank_select='bank b holds words 4096b..4096b+4095; ce only for its own addresses; the '
                            'registered select ORs the enabled bank into the matvec MEM_PIPE capture '
                            '(rtl/physical/ot_qwen_o4_g4_rommac.sv): zero added cycles')
    # the same image at the densest period-eligible 266-bit view, for comparison
    dense_banks = -(-code_words // depth[dense_m])
    code_alt = dict(macro=dense_m, banks_per_column=dense_banks, macros=columns * dense_banks,
                    area_mm2=columns * dense_banks * geom[dense_m]['area_um2'] / 1e6,
                    rejected_because=(
                        f"clk-to-q {geom[dense_m]['clk_to_q_tt_ps']:.1f} ps + setup leaves "
                        f"{(CLOCK_NS - UNCERTAINTY_NS) * 1e3 - geom[dense_m]['clk_to_q_tt_ps'] - 28.3:.1f} ps at "
                        f"{CLOCK_NS:.6f} ns with 60 ps uncertainty for the pin-to-capture wire and the "
                        f"{dense_banks}-bank select; a per-bank capture would add one cycle to the matvec contract"))
    segments = []
    for m in mats:
        segments.append(dict(name=m['name'], first_word=m['base'], last_word=m['end'] - 1,
                             first_bank=m['base'] // depth[code_m], last_bank=(m['end'] - 1) // depth[code_m],
                             split=m['split'], rounds=m['rounds']))

    # scale: one BF16 per output row, 16 per 256-bit word; only result-port groups read
    ports, per_port = port_scale_words(mats)
    rep_banks = -(-scale_words // depth[code_m])
    exact_banks = [-(-w // depth[code_m]) for w in per_port]
    scale = dict(
        macro=code_m, words_per_die=scale_words, rows_per_die=sum(m['scale_rows'] for m in mats),
        result_port_groups=ports,
        rtl_compatible=dict(
            organization='each result-port group holds the whole dense scale image (the RTL scale_addr '
                         'is the global dense address sbase + row word + q*IL)',
            banks_per_port_group=rep_banks, macros=ports * rep_banks,
            area_mm2=ports * rep_banks * geom[code_m]['area_um2'] / 1e6),
        exact_subset_needs_rtl_remap=dict(
            organization='each port group holds only the words it reads; needs a per-matrix local base in '
                         'the scale request (an ot_hdc_matvec change, not made)',
            words_per_port_group_max=max(per_port), words_per_port_group_min=min(per_port),
            words_total=sum(per_port), macros=sum(exact_banks),
            area_mm2=sum(exact_banks) * geom[code_m]['area_um2'] / 1e6),
        rtl_as_instantiated_note='ot_hdc_matvec instantiates scale_q and an ot_hdc_fmul for all 6,144 x 16 '
                                 'lanes; at G = 6144 the smallest split is 64 (gate/up), so only groups '
                                 f'0..{ports - 1} can ever raise scale_gre')
    # embedding: TP-2 splits the vocabulary (spec D5): 75,968 rows a die, 4,096 INT8 codes + one BF16 scale
    vocab_die = 151936 // TP
    emb_bits = vocab_die * 4096 * 8
    emb_word_bits = 2 * 256                                  # 64 codes a 512-bit word (EMBED_CODES_PER_WORD)
    emb_words = vocab_die * 4096 // 64
    emb_banks = -(-emb_words // depth[code_m])
    emb = dict(macro=code_m, rows=vocab_die, words=emb_words, word_bits=emb_word_bits,
               macros_per_word=2, banks=emb_banks, macros=2 * emb_banks,
               area_mm2=2 * emb_banks * geom[code_m]['area_um2'] / 1e6,
               scale_words=-(-vocab_die // W), scale_macros=-(-(-(-vocab_die // W)) // depth[code_m]),
               note='fullshape_placement computes the full vocabulary (9,723,904 words) per die; under TP-2 '
                    'each die holds half and hands one row across UCIe a token (spec D5)')
    emb['area_mm2'] += emb['scale_macros'] * geom[code_m]['area_um2'] / 1e6
    # constants ROM (RoPE/norm constants) as sized by the full-shape TB, 64-bit words
    tb = TB.read_text()
    crom_words = int(tb.split('CROM_WORDS=')[1].split(')')[0].split(',')[0])
    crom_banks = -(-crom_words // depth[narrow_m])
    crom = dict(macro=narrow_m, words=crom_words, word_bits=64, macros=crom_banks,
                area_mm2=crom_banks * geom[narrow_m]['area_um2'] / 1e6,
                basis='tb_hdc_qwen_layer0_tp2 CROM_WORDS (layer-0 gate sizing; full-token constants not audited)')

    total_macros = code['macros'] + scale['rtl_compatible']['macros'] + emb['macros'] + emb['scale_macros'] + crom['macros']
    total_area = code['area_mm2'] + scale['rtl_compatible']['area_mm2'] + emb['area_mm2'] + crom['area_mm2']
    budget = json.loads(BUDGET.read_text())
    stored_bits = (code_words * 786432 + scale_words * 256 + emb_bits + emb['scale_words'] * 256 + crom_words * 64)
    placed_bits = (code['macros'] * depth[code_m] * PAIR_BITS + scale['rtl_compatible']['macros'] * depth[code_m] * 256
                   + (emb['macros'] + emb['scale_macros']) * depth[code_m] * 256 + crom['macros'] * depth[narrow_m] * 64)
    rec = dict(
        schema='opentallas.qwen-o4-rom-placement.v1',
        status='integer_placement_closed_on_predictive_asap7_views',
        tool='tools/qwen_o4_rom_placement.py',
        source_sha256={str(p): sha(p) for p in SOURCES},
        tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        clock=dict(adopted_ns=round(CLOCK_NS, 6), basis='results/arch/qwen3_budget.json clock_hz 1,098,640,000 Hz; '
                   'the 0.92 ns of earlier cuts is 1.07% slower and is not adopted', uncertainty_ns=UNCERTAINTY_NS),
        die=dict(groups=G, lanes=G * W, tp=TP, code_word_bits=G * W * 8),
        macro_views=geom,
        code_rom=code, code_rom_alternative=code_alt, code_segments=segments,
        scale_rom=scale, embedding_rom=emb, constant_rom=crom,
        totals=dict(macros=total_macros, area_mm2=round(total_area, 3),
                    stored_bits=stored_bits, placed_capacity_useful_bits=placed_bits,
                    padding_fraction=round(1 - stored_bits / placed_bits, 5),
                    ledger_rom_mm2_n6=budget['area']['target_rom_mm2'] + budget['area']['drafter_rom_mm2'],
                    ledger_note='the N6 ledger ROM figure is an analytical density, not a macro view; it is '
                                'quoted, never substituted'),
        excluded=['ROM contents and via maps (no checkpoint read)', 'ECC (none on the O4 path)',
                  'program ROM (64 x 1,024 bits: flops)', 'KV ring and VM SRAM (see qwen_o4_floorplan.py)',
                  'macro manufacturing qualification; predictive ASAP7 views only'])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(code=code['macros'], banks=banks, scale=scale['rtl_compatible']['macros'],
                          scale_exact=scale['exact_subset_needs_rtl_remap']['macros'], emb=emb['macros'],
                          crom=crom['macros'], total_macros=total_macros, area=round(total_area, 2))))


if __name__ == '__main__':
    main()
