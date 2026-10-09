#!/usr/bin/env python3
"""kv-die 2026-10-09: the ROM die <-> KV die interface contract of the Qwen3-8B TP4 ROM design (OWNER DECISION
2026-10-09 ~04:00 PT, option 1a of results/arch/qwen_tp8_vs_sysdie_20261009/result.json).  One source of truth for
results/arch/qwen_kv_die_20261009/CONTRACT.json (CONTRACT.md is its prose); the bench parameters, the die generators
(tools/qwen_kv_die/rom_r22k.py, kv_die.py) and the re-price (reprice.py) import it.

    python3 tools/qwen_kv_die/contract.py --out results/arch/qwen_kv_die_20261009/CONTRACT.json
"""
import argparse
import json
from pathlib import Path

CLOCK_HZ = 1.2e9
WORD_BITS = 528                     # {tag 16, data 512}
FLIT_BITS = 8 + 8 + 1 + 3 + WORD_BITS
PHY_LAT = dict(best=3, typical=5, worst=9)        # FDI -> far FDI, 1.2 GHz cycles (physical/qwen_kv_die_phy)
# adapter cycles around the macro (ot_qkvd_d2d): TX pin capture 1 + buffer write 1 + grant / flit flop 1;
# RX macro-pin capture 1 + receive-buffer write 1 + pop to the registered die face 1
ADAPTER_TX, ADAPTER_RX = 3, 3
LINK_RTT = dict({k: 2 * v + 7 for k, v in PHY_LAT.items()})   # credit loop adapter <-> adapter (flit / PHY / capture /
#                                                                 push / pop / owed / flit / PHY / capture / update)
RELAY_UM = 430.56                  # one registered die stage (the r21 relay reach; corridor gate 89e70dd78)

# message classes on the one x64 module: class number, direction, word format, per-layer / per-token counts
CLASSES = [
    dict(cls=0, name='CTL', dir='ROM->KV', src='qfd_sp_constants_sequencer.dc (via qfd_d2d_rom)', dst='qkd_seq',
         words_per_layer=1, words_per_token=1,
         format='tag[15:12] op: 1 ATTN {data[13:0] T = position + 1, [21:16] layer, [63:32] KV base (user slot)}; '
                '2 TOKEN {data[17:0] token id, [45:32] position} (argmax result to the host); 3 CSR_RSP {data[63:0]}',
         link_buffer=4, die_credits=4, critical=True),
    dict(cls=1, name='Q', dir='ROM->KV', src='qfd_sp_su64_sfu.q (x3 word, tag Q)', dst='qkd_seq -> qkd_astk x 4',
         words_per_layer=32, format='tag[5:0] beat; data = 32 BF16 q values (q[h][d], h = 8 heads of the die, '
         'd = 128): bf16(RoPE(q_norm(q))) exactly as tools/hdc_golden.py attend() consumes them',
         link_buffer=32, die_credits=48, critical=True),
    dict(cls=2, name='KVN', dir='ROM->KV', src='qfd_sp_su64_sfu.q (x3 word, tag KVN)', dst='qkd_seq -> qkd_land '
         '(merge + posted HBM write)', words_per_layer=8,
         format='tag[2:0] {v, g, half}; data = 64 FP8 E4M3 bytes, byte d at [8d +: 8]: half h of the K (v = 0) or V '
                '(v = 1) row of KV head g (2 a die) at the new position T-1, already rounded to FP8 by the SU as the '
                'golden stores it',
         link_buffer=8, die_credits=8, critical=True),
    dict(cls=3, name='EMBQ', dir='ROM->KV', src='qfd_sp_su64_sfu.ea (r21c SU embedding face, unchanged)',
         dst='qkd_seq -> qkd_embgw (ot_qfd_emb_gw)', words_per_token=65,
         format='data[23:0] address, tag[0] kind (0: code word t*64+w, 1: the BF16 scale of row t): one request '
                'word a 512-b response, 64 code words then the scale',
         link_buffer=32, die_credits=32, critical=True),
    dict(cls=4, name='RES', dir='KV->ROM', src='qkd_ahub (ot_qwen_nearhbm_attn_hub_p out_*)',
         dst='qfd_d2d_rom.ar -> qfd_sp_vector_memory.ar (r21c attn_ret bus)', words_per_layer=64,
         format='tag[6] g, tag[5:0] beat; data = 16 FP32 attention outputs o[h][d] (h = 4 g + beat / 8, d = (beat % 8) '
                '* 16 + l), bit-exact to the golden softmax(qK^T * F(1/sqrt 128)) V',
         link_buffer=32, die_credits='VM write port: always ready (credit returned the cycle the word is taken)',
         critical=True),
    dict(cls=5, name='EMBD', dir='KV->ROM', src='qkd_embgw (eq)', dst='qfd_d2d_rom.eq -> qfd_sp_su64_sfu.eq',
         words_per_token=65, format='data = 64 INT8 codes (a code word) or the BF16 row scale in data[15:0]; tag = '
         'the gateway tag (request order)', link_buffer=32, die_credits='SU embedding buffer (r21c ABI: eq posted)',
         critical=True),
    dict(cls=6, name='HCTL', dir='KV->ROM', src='qkd_host (host link)', dst='qfd_d2d_rom.dh -> sequencer / sysctl',
         words_per_token='host-driven (start, prompt token, CSR writes); 0-2 on the decode path',
         format='tag[15:12] op: 1 START {position, token}, 2 CSR_WR {addr, data}, 3 CSR_RD {addr}, 4 STOP; '
                'KV-die status / fault words use op 8 (sticky fault bits of qkd_seq / adapters / controllers)',
         link_buffer=4, die_credits=4, critical=False),
]

NON_LINK = [
    dict(name='forwarded clock', dir='KV->ROM', what='the KV-die PLL output (1.2 GHz core clock) on a dedicated '
         'differential bump pair beside the UCIe module (not a UCIe data lane); ROM die: qfd_d2d_rom.pll_fwd_o -> '
         'qfd_clkrx (deskew buffer, the root of the same 121 region trunks the r21c hub drove)',
         clocking='same frequency both dies (mesochronous); the UCIe FDI runs on each die\'s local core clock and '
                  'the macro retimes the forwarded lane clock into it (no CDC in our logic)'),
    dict(name='reset', dir='KV->ROM', what='KV-die reset sequencer -> rst_fwd bump -> qfd_clkrx: asynchronous assert, '
         'synchronous release (2-flop synchroniser) -> the sequencer (rsi), which carries it in its words as r21c'),
    dict(name='link training / up', dir='both', what='the macro\'s tx_up status (UCIe link training and sideband, '
         'inside the vendor macro); our adapters send nothing until tx_up, and the KV die holds the ROM die\'s first '
         'START until both adapters report up'),
]

LATENCY = dict(
    adapter_plus_phy=dict({k: ADAPTER_TX + v + ADAPTER_RX for k, v in PHY_LAT.items()}),
    link_credit_round_trip=LINK_RTT,
    note='one word, die face of the sender to die face of the receiver; the on-die relay stages from the producer '
         '/ to the consumer are per die (r22k / KV-die placements) and are added in reprice.json',
)

FLOW = ('Credit flow on every hop, nothing waits on a same-cycle ready: (1) producer -> sender adapter die face '
        '(credits = the adapter\'s per-class input buffer; relay stations carry data forward and one credit pulse '
        'back per stage), (2) adapter -> adapter per class (credits = the far receive buffer, returned 2 b a class a '
        'flit; buffers >= the worst link round trip so a class streams one word a cycle), (3) receiver adapter -> '
        'consumer (credits = the consumer\'s buffer).  Order is preserved within a class; classes are independent '
        '(round-robin), so the KV die starts the layer only when CTL ATTN and all 8 KVN words have arrived, and '
        'forwards Q beats to the stacks as they arrive.')

PINS = ('Registered boundaries: every adapter die-face input is captured in a flop at the pin, every output is '
        'launched from a flop; the FDI is flop-to-macro on both sides (no logic between the macro pins and the '
        'flops).  The KV-die sequencer registers every port (CTL / Q / KVN / EMBQ inputs, RES / EMBD / HCTL outputs, '
        'attention / row / KV-write / gateway / host ports).  Relay stations every <= 430.56 um on both dies.')


def contract():
    return dict(
        schema='opentallas.qwen-kv-die.contract.v1', stream='kv-die', date='2026-10-09',
        decision='OWNER 2026-10-09 ~04:00 PT: Qwen3-8B ROM = TP4 ROM die + KV die pair per package (option 1a of '
                 'results/arch/qwen_tp8_vs_sysdie_20261009/result.json); KV never crosses',
        partition=dict(
            kv_die=['4 x ot_hbm3e_phy + qfd_ctrl (HBM3E PHYs + controllers, incl. the embedding pcports)',
                    '128 x per-PC CDC (ot_qwen_stream4_cdc_pc)',
                    '4 x KV landing (the qfd_kvc successor: CDC core sides -> row engines) with the KV merge (one per '
                    'row engine: the new position\'s crossed K / V replace the row read for t = T-1) and the KVN '
                    'posted write; the embedding strip engine (ot_qfd_emb_strip)',
                    'near-HBM attention: 4 stacks x R = 8 row engines (ot_qwen_nearhbm_row_engine_p) + 4 stack '
                    'aggregators (Z / P.V trees, exp) + 1 attention hub (ot_qwen_nearhbm_attn_hub_p)',
                    'embedding gateway (ot_qfd_emb_gw, out of the r21c hub)',
                    'host link + prefill KV ingest (qfd_io_host successor, its own SerDes host PHY)',
                    'PLL + reset sequencer (the package clock / reset producer)',
                    'KV-die sequencer qkd_seq (rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_seq.sv) + the KV end of the '
                    'link (ot_qkvd_d2d) + UCIe macro'],
            rom_die=['1,536 ROM tiles (no KV slice: qfd_tile_nk)', 'spine: SU64 / SFU, banked VM, tree top, band '
                     'slabs / lanes / serializers, constant ROM, sequencer + control', 'collective (io_collective, '
                     'io_xfifo, io_ucie to the package-mate ROM die, io_serdes board SerDes)',
                     'the ROM end of the link (qfd_d2d_rom: ot_qkvd_rom_end = ot_qkvd_d2d + the r21c hub SU / VM face) '
                     '+ UCIe macro', 'clock root receiver + reset synchroniser (qfd_clkrx at the old hub slot)'],
            kv_never_crosses='per layer only q (1,024 BF16), the new K / V (512 FP8) and the attention output '
                             '(1,024 FP32) cross; the 4 MiB a layer a die KV stream stays on the KV die'),
        phy=dict(macro='ot_qkvd_ucie_x64_phy (physical/qwen_kv_die_phy, tools/qwen_kv_die/phy_gen.py)',
                 module='one UCIe-A x64 module, 16 GT/s, 1,024 Gb/s each way; flit 548 b at 1.2 GHz = 657.6 Gb/s '
                        '(64 % of raw)', area_mm2=0.6047, edge_um=777.6, latency_cycles=PHY_LAT,
                 crc_retry='inside the vendor D2D adapter (UCIe spec); ours: sequence check + fail-closed',
                 published='JSSC 2026 3.5 ns FDI-to-FDI (typical 5 cycles); CPMT 2022 < 2 ns (best 3); worst 9 '
                           'ASSUMED (2x measured)'),
        flit=dict(bits=FLIT_BITS, layout='{seq[7:0], credit return 4 x 2 b (field j = the sender\'s RX class j), dv, '
                  'class[2:0], word[527:0]}', word='{tag[15:0], data[511:0]}', rate='one flit a 1.2 GHz cycle each '
                  'way while up; idle flits carry credits'),
        classes=CLASSES, non_link=NON_LINK, latency=LATENCY, flow=FLOW, pins=PINS,
        rtl=dict(adapter='rtl/qwen_sys/kv_die_20261009/ot_qkvd_d2d.sv', rom_end='rtl/qwen_sys/kv_die_20261009/'
                 'ot_qkvd_rom_end.sv', kv_seq='rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_seq.sv',
                 bench='rtl/test/qwen_kv_die/ot_qkvd_layer_tb.sv + tb_qkvd_layer.cpp'),
        per_layer_bits=dict(rom_to_kv=(1 + 8 + 32) * WORD_BITS, kv_to_rom=64 * WORD_BITS),
        clocking='one 1.2 GHz domain on both dies, from the KV-die PLL; ROM die clock = the forwarded PLL clock '
                 '(mesochronous); no CDC FIFO in our logic (the UCIe macro retimes); the HBM 976.6 MHz domain and its '
                 'CDC stay on the KV die',
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(contract(), indent=1) + '\n')
    print(a.out)


if __name__ == '__main__':
    main()
