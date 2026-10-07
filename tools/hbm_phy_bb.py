#!/usr/bin/env python3
"""HBM DS die PHY black boxes (CLAUDE HBM-ABSTRACTS coordinator, OWNER DECISION 2026-10-06 ~19:20).

The HBM die's off-die links are hard PHYs we do not design.  Each is modelled as a PIN-ACCURATE BLACK BOX in two
parts that the generator already places side by side:
  * the bump / analog field (hfd_serdes_slab x 2, hfd_host_slab): outline + M1-M7 obstruction, die route crosses on
    M8/M9, no digital pins (nothing of ours talks to the analog side);
  * the PHY's digital-facing pin macro on the slab's core side, every pin on the face toward its consumer (W face, M4):
      - SerDes: ot_pdie_serdes (the S81 die's black box, reused as the owner directed): clk + tx[512] + rx[512] per
        macro; the HBM die binds 487 tx + 487 rx of each of its 9 macros (the TU endpoint's NPT = 8 ports x (545-bit
        flit + valid + credit) = 4,376 b each way, striped over 9 macros; tools/hbm_accel_die_fp.py real_ports).
      - Host: ot_hbm_host_phy (NEW, this tool): the host controller's digital interface exactly as the loader RTL
        consumes it (rtl/hbm_accel/loader/ot_hbm_accel_loader_host.sv): the AXI4-Lite BAR target s_* (32 b) and the
        64-bit AXI host DMA h_dma_* (9.6 GB/s = 64 b x 1.2 GHz), PHY directions = complement of the loader's.
This tool writes ot_hbm_host_phy (bb.v, LEF, TT/SS/FF Liberty, json) and SS/FF Liberty for ot_pdie_serdes, in the
format of physical/asap7_v41x_pdie_macros_v2 (interface timing: every PHY-side pin launched / captured by a PHY flop
on clk).  CDC into the 1.2 GHz core is on OUR side and already in RTL: TU endpoint TX/RX ot_link_afifo (core <-> pclk),
loader host clk_host <-> clk_mem crossing inside ot_hbm_accel_loader_host.

  hbm_phy_bb.py --out physical/hbm_accel_die_views/phy_bb
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOADER_HOST = 'rtl/hbm_accel/loader/ot_hbm_accel_loader_host.sv'
UCIE_LEF = ROOT / 'physical/asap7_v41x_pdie_macros_v2/ot_pdie_ucie/ot_pdie_ucie.lef'
# corner interface timing of a hard PHY's registered parallel interface (ns): TT = the pdie macros' own values
CORNERS = dict(tt=dict(c2q=0.218, setup=0.050, hold=0.050, slew=0.020, proc=1, temp=25, volt=0.70),
               ss=dict(c2q=0.295, setup=0.070, hold=0.030, slew=0.030, proc=1, temp=100, volt=0.63),
               ff=dict(c2q=0.150, setup=0.035, hold=0.065, slew=0.015, proc=1, temp=0, volt=0.77))


def host_ports():
    """[(name, width, phy_direction)] of the host PHY: the loader host module's s_* and h_dma_* ports, complemented."""
    txt = (ROOT / LOADER_HOST).read_text()
    hdr = txt[txt.index('module ot_hbm_accel_loader_host'):txt.index(');')]
    out = []
    for d, w, names in re.findall(r'(input|output)\s+wire\s*(\[\d+:0\])?\s*([\w\s,]+?)(?=,\s*(?:input|output)|$)', hdr, re.S):
        width = int(re.match(r'\[(\d+):0\]', w).group(1)) + 1 if w else 1
        for n in [x.strip() for x in names.split(',') if x.strip()]:
            if n.startswith(('s_', 'h_dma_')):
                out.append((n, width, 'output' if d == 'input' else 'input'))
    return out


def lib_text(cell, area, clk, ports, corner):
    c = CORNERS[corner]
    L = [f'library({cell}_{corner}) {{', '    technology (cmos);', '    delay_model : table_lookup;', '    time_unit : "1ns";',
         '    voltage_unit : "1V";', '    current_unit : "1uA";', '    leakage_power_unit : "1uW";',
         '    pulling_resistance_unit : "1kohm";', '    capacitive_load_unit (1,pf);',
         f'    nom_process : {c["proc"]};', f'    nom_temperature : {c["temp"]:.3f};', f'    nom_voltage : {c["volt"]};',
         f'    operating_conditions({corner}) {{ process : {c["proc"]}; temperature : {c["temp"]:.3f}; voltage : {c["volt"]}; tree_type : balanced_tree; }}',
         f'    default_operating_conditions : {corner};', '    default_max_transition : 0.320;',
         '    slew_lower_threshold_pct_rise : 20.000;', '    slew_upper_threshold_pct_rise : 80.000;',
         '    slew_lower_threshold_pct_fall : 20.000;', '    slew_upper_threshold_pct_fall : 80.000;',
         '    input_threshold_pct_rise : 50.000;', '    input_threshold_pct_fall : 50.000;',
         '    output_threshold_pct_rise : 50.000;', '    output_threshold_pct_fall : 50.000;',
         f'    lu_table_template({cell}_t) {{ variable_1 : input_net_transition; variable_2 : total_output_net_capacitance; index_1 ("0.005, 0.500"); index_2 ("0.001, 0.500"); }}',
         f'    lu_table_template({cell}_c) {{ variable_1 : related_pin_transition; variable_2 : constrained_pin_transition; index_1 ("0.005, 0.500"); index_2 ("0.005, 0.500"); }}']
    for w in sorted({w for _, w, _ in ports if w > 1}):
        L.append(f'    type ({cell}_bus{w}) {{ base_type : array; data_type : bit; bit_width : {w}; bit_from : {w - 1}; bit_to : 0; downto : true; }}')
    L += [f'    cell({cell}) {{', f'        area : {area:.3f};', '        interface_timing : true;', '        dont_use : true;',
          '        dont_touch : true;', f'        pin({clk}) {{ direction : input; capacitance : 0.020; clock : true; }}']

    def tab(kind, v, tmpl):
        return [f'            {kind}({cell}_{tmpl}) {{ index_1 ("0.005, 0.500"); index_2 ("{"0.001" if tmpl == "t" else "0.005"}, 0.500"); values ("{v:.4f}, {v:.4f}", "{v:.4f}, {v:.4f}"); }}']
    for n, w, d in ports:
        head = f'        bus({n}) {{ bus_type : {cell}_bus{w};' if w > 1 else f'        pin({n}) {{'
        L.append(head)
        if d == 'input':
            L.append('            direction : input; capacitance : 0.0020;')
            for tt, v in (('setup_rising', c['setup']), ('hold_rising', c['hold'])):
                L.append(f'            timing() {{ related_pin : "{clk}"; timing_type : {tt};')
                L += tab('rise_constraint', v, 'c') + tab('fall_constraint', v, 'c')
                L.append('            }')
        else:
            L.append('            direction : output; max_capacitance : 0.500;')
            L.append(f'            timing() {{ related_pin : "{clk}"; timing_type : rising_edge; timing_sense : non_unate;')
            L += tab('cell_rise', c['c2q'], 't') + tab('cell_fall', c['c2q'], 't')
            L += tab('rise_transition', c['slew'], 't') + tab('fall_transition', c['slew'], 't')
            L.append('            }')
        L.append('        }')
    L += ['    }', '}', '']
    return '\n'.join(L)


def host_bb(out: Path):
    cell = 'ot_hbm_host_phy'
    ports = host_ports()
    m = re.search(r'SIZE ([\d.]+) BY ([\d.]+)', UCIE_LEF.read_text())
    W, H = float(m.group(1)), float(m.group(2))          # the UCIe-class host shoreline macro's outline, unchanged
    bits = [('clk', 'input')] + [(f'{n}[{i}]' if w > 1 else n, d) for n, w, d in ports for i in range(w)]
    # r13 die-context STA (measured): pins spread over the full 1652 um face put up to ~1.6 mm of unbuffered wire
    # between the host link station and a PHY pin (w299_host b[1] -> s_awready 0.83 ns, setup -1.0 ns).  The pins
    # sit in one cluster at the face centre (0.192 um = 4 M4 tracks), opposite the station chain's end.
    pitch = 0.192
    y0 = round((H / 2 - len(bits) * pitch / 2) / 0.048) * 0.048 + 0.024
    d = out / cell
    d.mkdir(parents=True, exist_ok=True)
    L = [f'# PIN-ACCURATE BLACK BOX written by tools/hbm_phy_bb.py: host PHY / controller digital interface (AXI4-Lite BAR',
         f'# target s_* + 64-bit AXI host DMA h_dma_*, 9.6 GB/s), pins on the W (core-facing) face, M4, pitch {pitch:.3f} um',
         'VERSION 5.7 ;', 'BUSBITCHARS "[]" ;', f'MACRO {cell}', f'  FOREIGN {cell} 0 0 ;', '  SYMMETRY X Y ;',
         f'  SIZE {W:.3f} BY {H:.3f} ;', '  CLASS BLOCK ;']
    for i, (n, dr) in enumerate(bits):
        y = y0 + i * pitch
        L += [f'  PIN {n}', f'    DIRECTION {dr.upper()} ;', '    USE SIGNAL ;', '    SHAPE ABUTMENT ;', '    PORT',
              '      LAYER M4 ;', f'      RECT 0.000 {y:.3f} 0.192 {y + 0.024:.3f} ;', '    END', f'  END {n}']
    L += ['  OBS'] + [f'    LAYER M{k} ;\n    RECT 0 0 {W:.3f} {H:.3f} ;' for k in range(1, 8)] + ['  END', f'END {cell}', '', 'END LIBRARY', '']
    (d / f'{cell}.lef').write_text('\n'.join(L))
    V = ['// PIN-ACCURATE BLACK BOX (tools/hbm_phy_bb.py): host PHY / controller, digital-facing side only', '(* blackbox *)',
         f'module {cell} (', '    input  wire clk,']
    V += [f'    {dr:6s} wire {f"[{w - 1}:0] " if w > 1 else ""}{n}{"," if k < len(ports) - 1 else ""}' for k, (n, w, dr) in enumerate(ports)]
    V += [');', 'endmodule', '']
    (d / f'{cell}_bb.v').write_text('\n'.join(V))
    for c in CORNERS:
        (d / f'{cell}_{c}.lib').write_text(lib_text(cell, W * H, 'clk', ports, c))
    rec = dict(name=cell, kind='host PHY black box (digital-facing)', width_um=W, height_um=H, area_um2=round(W * H, 3),
               signal_pins=len(bits), pitch_um=round(pitch, 3), face='W', layer='M4', clock='clk (die-supplied PHY-side clock; the loader host clk_host)',
               ports=[dict(name=n, width=w, direction=dr) for n, w, dr in ports],
               derived_from=LOADER_HOST, corners=CORNERS,
               cdc='on our side: ot_hbm_accel_loader_host clk_host -> clk_mem crossing (RTL)', bandwidth='h_dma 64 b x 1.2 GHz = 9.6 GB/s')
    (d / f'{cell}.json').write_text(json.dumps(rec, indent=1) + '\n')
    return rec


def serdes_libs(out: Path):
    cell = 'ot_pdie_serdes'
    src = ROOT / 'physical/asap7_v41x_pdie_macros_v2/ot_pdie_serdes'
    m = re.search(r'SIZE ([\d.]+) BY ([\d.]+)', (src / f'{cell}.lef').read_text())
    area = float(m.group(1)) * float(m.group(2))
    d = out / cell
    d.mkdir(parents=True, exist_ok=True)
    ports = [('tx', 512, 'input'), ('rx', 512, 'output')]
    for c in ('ss', 'ff'):
        (d / f'{cell}_{c}.lib').write_text(lib_text(cell, area, 'clk', ports, c))
    return dict(name=cell, lef=str(src.relative_to(ROOT) / f'{cell}.lef'), libs=['ss', 'ff'])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, default=ROOT / 'physical/hbm_accel_die_views/phy_bb')
    a = ap.parse_args(argv)
    h = host_bb(a.out)
    s = serdes_libs(a.out)
    print(json.dumps(dict(host=dict(pins=h['signal_pins'], pitch=h['pitch_um'], ports=len(h['ports'])), serdes=s)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
