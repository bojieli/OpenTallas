#!/usr/bin/env python3
"""kv-die 2026-10-09: the additive ledger updates of the ROM die + KV die build.

  * results/fleet_viz/element_registry/qwen_kv_die_20261009.json -- one record per KV-die / new ROM-die master
    (new element names: qkd_* on the KV die; qfd_d2d_rom, qfd_clkrx, qfd_tile_nk on the ROM die);
  * results/arch/coverage_20261008/T1.json -- a `kv_die_20261009` entry on every T1 node the partition moves or
    changes (existing fields untouched; verdicts are never overwritten).

    python3 tools/qwen_kv_die/gen_ledgers.py --src COMMIT
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = 'results/arch/qwen_kv_die_20261009'
RTL = 'rtl/qwen_sys/kv_die_20261009'


def J(p):
    return json.loads((ROOT / p).read_text())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True)
    ap.add_argument('--at', default='2026-10-09T05:00:00-07:00')
    a = ap.parse_args()
    bench, plan, rom, rp = J(f'{D}/bench.json'), J(f'{D}/kv_die/plan.json'), J(f'{D}/rom_r22k.json'), J(f'{D}/reprice.json')
    typ = bench['cases']['typical']
    ex = dict(status='pass' if bench['ok'] else 'fail',
              evidence=f"{D}/bench.json: attention layer step through the link bit-exact on {typ['runs']} runs "
                       f"(7 contexts x stall 0/1), mutants {', '.join(k + ' ' + v['verdict'] for k, v in typ.get('mutants', {}).items())}")
    phys_none = dict(status='missing', evidence='no element route yet (route specs queued: see kv-die.log COLLECT)')
    die_kv = dict(status='pending', evidence=f"{D}/kv_die/plan.json (legal: 0 overlaps / 0 outside; strict ports "
                  f"{'ok' if plan['strict_ports']['ok'] else 'FAIL'}; relay margin lint in {D}/kv_die/lint.json); die GRT / STA "
                  "chain on EPYC1 /srv/opentallas-scratch/claude/kv-die/die_kv")
    die_rom = dict(status='pending', evidence=f"{D}/rom_r22k.json (r22k {rom['die_mm2']} mm2, legal); die GRT / STA chain on "
                   "EPYC1 /srv/opentallas-scratch/claude/kv-die/die_r22k")

    def rec(element, desc, paths, exact=None, phys=None, deps=(), integ=None, model=None):
        r = dict(element=element, target='Qwen ROM', recorded_at=a.at, owner='Claude:kv-die', description=desc,
                 source=dict(commit=a.src, paths=list(paths)),
                 implementation=dict(status='implemented' if paths else 'missing', evidence=', '.join(paths)),
                 exactness=dict(positive=exact or dict(status='pending', evidence='element bench owed'),
                                negative=exact or dict(status='pending', evidence='element mutant owed')),
                 physical=phys or phys_none, dependencies=list(deps),
                 integration=integ or dict(status='pending', evidence='die views ' + D))
        if model:
            r['model'] = model
        return r
    recs = [
        rec('qkd_d2d', 'KV-die end of the ROM <-> KV link: ot_qkvd_kv_end (ot_qkvd_d2d NT 3 / NR 4) + forwarded clock / '
            'reset bumps; CONTRACT.md classes, credits, sequence check', [f'{RTL}/ot_qkvd_kv_end.sv', f'{RTL}/ot_qkvd_d2d.sv',
            f'{RTL}/ot_qkvd_fifo.sv', 'physical/qwen_die_masters/cfg/qkd_d2d_a.env', 'physical/qwen_die_masters/cfg/qkd_d2d_b.env'],
            exact=ex, integ=die_kv),
        rec('qfd_d2d_rom', 'ROM-die end of the link: ot_qkvd_rom_end = the r21c hub SU / VM / sequencer faces (x3, ar '
            '519 b, ea, eq, dc, dh) over ot_qkvd_d2d', [f'{RTL}/ot_qkvd_rom_end.sv', f'{RTL}/ot_qkvd_d2d.sv',
            'physical/qwen_die_masters/cfg/qfd_d2d_rom_a.env', 'physical/qwen_die_masters/cfg/qfd_d2d_rom_b.env'],
            exact=ex, integ=die_rom),
        rec('qkd_seq', 'KV-die sequencer ot_qkvd_kv_seq: CTL / Q / KVN / EMBQ in, RES / EMBD / HCTL out, attention start, '
            'KVN posted rows, gateway / host bridges', [f'{RTL}/ot_qkvd_kv_seq.sv', f'{RTL}/ot_qkvd_cbridge.sv'], exact=ex,
            integ=die_kv),
        rec('qkd_land', 'KV landing (qfd_kvc successor): 32 CDC core sides -> R = 8 row engines, KV merge slices '
            '(ot_qkvd_kv_merge), posted KVN write, embedding strip', [f'{RTL}/ot_qkvd_kv_merge.sv'], exact=ex,
            deps=['landing crossbar RTL (32 PC -> 8 engines) owed', 'ot_qfd_emb_strip'], integ=die_kv),
        rec('qkd_reng', 'near-HBM row engine (512 lanes): ot_qwen_nearhbm_row_engine_p, R = 8 a stack (32 a die)',
            ['rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_p.sv'],
            exact=dict(status='pass', evidence='results/uarch/qwen_nearhbm_attn_rtl_20261003/gate_hd128_r8_dpi.json + ' + D + '/bench.json'),
            phys=dict(status='failed', evidence='results/uarch/qwen_nearhbm_attn_rtl_20261003/pnr/retry_20261004/verdict.json '
                      '(DROP 10-04: never reached CTS in 6 h; 1 M instances, 34 k IO bits) -- re-cut owed'), integ=die_kv),
        rec('qkd_astk', 'stack aggregator (ot_qwen_nearhbm_attn_stack_p minus its engines: q registers, exp quads, Z / '
            'P.V trees); frame ASSUMED 777.6 um x 4 engines tall', ['rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_p.sv'],
            exact=dict(status='pass', evidence='inside the stack gates above'), deps=['element cut owed'], integ=die_kv),
        rec('qkd_ahub', 'near-HBM attention hub ot_qwen_nearhbm_attn_hub_p (max exchange, Z levels 5-10, P.V 8-9, '
            'reciprocal, x 1/Z)', ['rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_p.sv'],
            exact=dict(status='pass', evidence='gate_hd128_r8_dpi.json + ' + D + '/bench.json'),
            phys=dict(status='failed', evidence='hub_r9 post-CTS SS -88.95 ps (10-04, 6 h budget); J2 SRAM chain = '
                      'fallback'), integ=die_kv),
        rec('qkd_embgw', 'embedding gateway ot_qfd_emb_gw moved from the r21c hub to the KV die',
            ['rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_gw.sv'], integ=die_kv),
        rec('qkd_host', 'host link + prefill KV ingest on the KV die (qfd_io_host successor) with the 112G SerDes host '
            'PHY macro', [], deps=['hing_qfd ingest', 'ot_qfd_link_adapter'], integ=die_kv),
        rec('qkd_pll', 'PLL + reset sequencer of the package (clock forwarded to the ROM die)', [],
            deps=['vendor PLL abstract (MISSING_HW)', 'ot_qwen_sys_rst_seq'], integ=die_kv),
        rec('qkd_ctrl', 'HBM controller band on the KV die = the qfd_ctrl element (unchanged)', [], integ=die_kv),
        rec('qkd_cdc', 'per-PC CDC on the KV die = ot_qwen_stream4_cdc_pc (unchanged)', ['rtl/hdc/kv/ot_qwen_stream4_cdc_pc.sv'],
            integ=die_kv),
        rec('qfd_clkrx', 'ROM-die clock root at the old hub slot: forwarded KV-die PLL clock, the 121 region trunks, '
            'reset synchroniser', [], integ=die_rom),
        rec('qfd_tile_nk', 'ROM tile without the KV slice / landing hop (attention moved to the KV die): '
            'ot_qwen_rom_tile_die minus li / lo and the two ot_sram_1r1w_128x256 macros', ['rtl/physical/ot_qwen_rom_tile_die.sv'],
            deps=['no-KV tile variant RTL + route owed (tile closure stream)'], integ=die_rom),
        rec('ot_qkvd_ucie_x64_phy', 'UCIe-A x64 PHY + D2D adapter abstract (licensed IP, FDI 548 b at 1.2 GHz, 3 / 5 / 9 '
            'cycles)', ['physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy.json'],
            exact=dict(status='pass', evidence='cycle model in ' + D + '/bench.json'),
            phys=dict(status='abstract', evidence='vendor IP abstract; footprint / timing ASSUMED as stated'), integ=die_rom),
    ]
    reg = dict(schema_version=1, records=recs)
    p = ROOT / 'results/fleet_viz/element_registry/qwen_kv_die_20261009.json'
    p.write_text(json.dumps(reg, indent=1) + '\n')
    # ---- T1 coverage ledger (additive) ----
    t1p = ROOT / 'results/arch/coverage_20261008/T1.json'
    t1 = json.loads(t1p.read_text())
    c = rp['cases']['typical']
    upd = {
        'D01': ('KV die: embedding gateway qkd_embgw + landing strips + controllers; EMBQ / EMBD cross the link (65 words '
                'each way a token)', f"priced {c['embed_cycles']} cycles typical ({D}/reprice.json)", ['NOT_CLOSED']),
        'B02': ('KV die: the boot load comes from the host (qkd_host) straight into HBM; it no longer crosses the ROM die',
                'host RAW stream path on the KV die (frames only)', ['NOT_CLOSED', 'NOT_EXACT']),
        'F03': ('KV die (gateway + strips)', 'unchanged RTL, new placement', ['NOT_CLOSED']),
        'D09': ('ROM die SU (unchanged); the FP8 K / V of the new position cross on KVN (8 words)', 'exact through the '
                'link (bench)', ['NOT_CLOSED']),
        'D10': ('KV die near-HBM attention (row engines + aggregators + hub), q crosses (32 words)', 'bit-exact through '
                'the link (bench.json)', ['NOT_CLOSED']),
        'D11': ('KV die near-HBM attention', 'bit-exact through the link', ['NOT_CLOSED']),
        'D12': ('KV die near-HBM attention', 'bit-exact through the link', ['NOT_CLOSED']),
        'D13': ('KV die attention hub (x 1/Z); RES crosses (64 words) into the VM', 'bit-exact through the link',
                ['NOT_CLOSED']),
        'C05': ('KV die (landing / controllers)', 'unchanged', ['NOT_CLOSED', 'MODELLED_ONLY']),
        'C06': ('KV die: KVN rows posted by qkd_seq to the landings (write queue) and merged for t = T-1',
                'merge exact in the bench (poisoned HBM rows)', ['NOT_CLOSED']),
        'C07': ('KV die: no cross-layer prefetch needed (near-HBM attention streams its own KV)', 'L0 cold penalty '
                'removed in the re-price', ['NOT_CLOSED']),
        'C14': ('NEW crossing: UCIe-A x64 between the ROM die and its KV die (ot_qkvd_ucie_x64_phy, our ot_qkvd_d2d '
                'ends); the package UCIe / SerDes of the collective unchanged', 'link RTL exact + mutants (bench.json)',
                ['NOT_CLOSED', 'MODELLED_ONLY']),
        'F04': ('ROM / KV link ends: sequence error, overrun, credit overflow, class range (sticky, registered)',
                'mutants caught (bench.json)', []),
        'H03': ('KV die: qkd_host + 112G SerDes host PHY macro', 'frame + macro only', ['NOT_CLOSED', 'MODELLED_ONLY']),
        'H04': ('KV die: ingest straight into HBM through the landings (never crosses)', 'frame only',
                ['NOT_CLOSED', 'NOT_EXACT']),
        'B04': ('KV die qkd_pll (reset sequencer) -> rst_fwd -> ROM-die qfd_clkrx synchroniser', 'frame only',
                ['NOT_CLOSED']),
        'B05': ('KV die qkd_pll (PLL frame, forwarded clock to the ROM die)', 'vendor PLL abstract still missing',
                ['MISSING_HW']),
        'F01': ('KV die (unchanged path)', 'J4: check bits read as an ordinary scheduled read', ['NOT_CLOSED']),
        'F02': ('KV die controllers: SECDED check bits as an ordinary scheduled read, corrected before the CDC (Q7)',
                'policy settled (CONTRACT.md section 6); RTL owed', ['MISSING_HW']),
        'C02': ('host words reach the ROM-die sequencer as HCTL; TOKEN words go back as CTL', 'link classes exact',
                ['NOT_ON_DIE', 'NOT_CLOSED']),
    }
    for n in t1['nodes']:
        if n['id'] in upd:
            die, ev, gap = upd[n['id']]
            n['kv_die_20261009'] = dict(die=die, evidence=ev, gap=gap, contract=f'{D}/CONTRACT.md',
                                        source=a.src)
    t1['kv_die_20261009'] = dict(
        decision='OWNER 2026-10-09 ~04:00 PT option 1a: ROM die (r22k) + KV die pair', rom_die_mm2=rom['die_mm2'],
        kv_die_mm2=plan['die_mm2'], token_typical=c, contract=f'{D}/CONTRACT.md', reprice=f'{D}/reprice.json',
        note='additive: the r21b/r21c fields above are the pre-decision record and are kept')
    t1p.write_text(json.dumps(t1, indent=1) + '\n')
    print(len(recs), 'registry records;', sum('kv_die_20261009' in n for n in t1['nodes']), 'T1 nodes updated')


if __name__ == '__main__':
    main()
