#!/usr/bin/env python3
"""S-ELEM-C 2026-10-15: ref-tile specs for the seven Engram MIX arithmetic leaf masters (each hardened once,
replicated 8/12/4/2/3/1/1 x per copy cluster ot_s81_engram_mixq, 4 clusters in dsfd_engram_mix4_c) on the v21
die-tool pins (physical/s81_die_pins/v21_engram_arithmetic).  Bench = the exact production MIX4 gate (all four
clusters, 4 x 5120, released-token L01 fixture, every FP operator target RTL) + the key->1.0 multiplier mutant."""
import json
from pathlib import Path
R = Path(__file__).resolve().parents[3]
PINS = R / 'physical/s81_die_pins/v21_engram_arithmetic'
SRCS = ["rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_fp32_f12.sv", "rtl/hdc/ot_hdc_fp32_mul_lat.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv",
        "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv", "rtl/hdc/v41x/ot_dsrom_su_add6.sv",
        "rtl/hdc/v41x/ot_dsrom_su_norm.sv", "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_fpu.sv",
        "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/hdc/ot_hdc_fastfp_lat_f12.sv", "rtl/hdc/v41/ot_hdc_fsqrt.sv", "rtl/hdc/v41/ot_hdc_fdiv.sv",
        "rtl/hdc/v41/ot_hdc_softplus.sv", "rtl/hdc/v41x/ot_hdc_v41x_sfu.sv", "rtl/hdc/v41/ot_hdc_actquant.sv",
        "rtl/hdc/v41x/ot_dsrom_aq12.sv", "rtl/hdc/v41x/ot_dsrom_divc.sv", "rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv",
        "rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv"]
FIX = 'results/rtl/s81_engram_mix_1014/fixtures/engram_L01.pkl'
BENCH = [dict(name='mix4_exact_L01', cmd=f'python3 tools/s81_engram_mix/gate.py --mix4 --fp rtl --snap {FIX} --out {{RUN}}/mix4_m0',
              expect='pass', threads=16, peak_ram_gb=48, needs=['verilator'], pass_regex='PASS native Engram MIX4'),
         dict(name='mix4_mut1_key', cmd=f'python3 tools/s81_engram_mix/gate.py --mix4 --fp rtl --snap {FIX} --mut 1 --out {{RUN}}/mix4_m1',
              expect='fail', threads=16, peak_ram_gb=48, needs=['verilator'], fail_regex='FAIL [0-9]+ words')]
COPIES = dict(mul4=8, chunk8=12, add8=4, norm=2, sum=3, signed_sqrt=1, sigmoid=1)


def main():
    rec = json.loads((PINS / 'receipt.json').read_text())
    for m in rec['masters']:
        name = m['master']; suf = name.replace('ot_s81_engram_', ''); W, H = m['outline_um']
        pj = json.loads((PINS / f'{name}.json').read_text())
        faces = {'N': [], 'S': [], 'W': [], 'E': []}
        for p, v in pj['ports'].items():
            faces[v['per_bit'][0][0]].append(p)
        spec = dict(name=f's81engm_{suf}', kind='tile', top=name, sources=SRCS, params={}, clock_port='clk', reset_ports=['arst_n'],
                    outline=dict(w=W, h=H, exact=True), util=0.5, layer_cap='M5', recipe=2, pins=faces,
                    io_tcl=f'physical/s81_die_pins/v21_engram_arithmetic/{name}.tcl',
                    route=dict(pd=0.5, threads=8, peak_ram_gb=16, pin_v='M3 M5', pin_h='M4', pin_min_tracks=1, hold_margin_ns=0.03, macro_halo_um=5.4),
                    why_floorplan=f'v21 die-tool outline right-sized from the ORFS-synthesised area {m["orfs_synth_area_um2"]} um2 (util {m["util"]}); one clock root per leaf (<=11,519 sinks); {COPIES[suf]} copies per cluster x 4 clusters',
                    structural_change='Engram MIX4 physical hierarchy (S-ELEM-C 2026-10-15): every arithmetic root of ot_s81_engram_mix is a hardened leaf master, hardened once and replicated; inputs registered at the S pins, outputs launched from registers at the N pins (no added cycle: the leaves are the unchanged exact arithmetic RTL).',
                    job=dict(owner='Claude:s81-surx-engram-1015', branch='claude/s81-mix4-phys-1015', tag='v21',
                             purpose=f'S81 Engram MIX4 arithmetic leaf {name} on v21 die-tool pins', benches=BENCH,
                             views_to=f'physical/ref_tile/s81engm_{suf}/views', record_to=f'results/rtl/ref_tile/s81engm_{suf}',
                             extra_paths=['physical/s81_die_pins/v21_engram_arithmetic', 'rtl/dsrom_sys', 'rtl/hdc', 'rtl/lib',
                                          'tools/s81_engram_mix', 'tools/s81_suhc', 'results/rtl/s81_engram_mix_1014/fixtures']),
                    macros=[], children=[], inter=[], io_flop_at_pins=dict(cols=4, allow_none=True), inhold=True, outhold=True,
                    keep_pin_regs=True, pin_reg_split=True, hold_pad=dict(cell='HB2xp67_ASAP7_75t_R'))
        (Path(__file__).parent / f's81engm_{suf}.json').write_text(json.dumps(spec, indent=1) + '\n')
        print(spec['name'], W, H)


if __name__ == '__main__':
    main()
