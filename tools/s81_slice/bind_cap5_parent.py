#!/usr/bin/env python3
"""Emit an opt-in k8 parent using CLOSED CAPC5k, with explicit CAP clocks.

The CAP input and output buses cross through D=4/K=2 landings. Each direction
adds three edges, hence twelve total capture edges vs capc2. Existing C-clock
bundle writers stay in place.
This is source integration; the combined parent has no closure claim.
"""
import argparse
import json
from pathlib import Path

# (name, width, write clock, write reset, source, target, read clock/reset) -- one table for the RTL and the record.
# S81-SLICE-1021: instance names follow the lp.py landing convention u_lpl_<name>_w / _r, so the landed-cluster SDC
# (clock_entry_constraints.landed_sdc: multicycle -setup E -hold D-1 per record landing) constrains these rings too.
LANDINGS = [
    ('west_in', 280, 'ck_C', 'cap5_rst_C', 'rt_q[279:0]', 'cap5_w_in', dict(read_clock='ck_CAP_CW', read_reset='cap5_rst_CW')),
    ('east_in', 280, 'ck_C', 'cap5_rst_C', 'rt_q[559:280]', 'cap5_e_in', dict(read_clock='ck_CAP_CE', read_reset='cap5_rst_CE')),
    ('cfg_in', 161, 'ck_C', 'cap5_rst_C', '{cfg_v,cfg_d}', 'cap5_cfg_in', dict(read_clock='ck_CAP_RN', read_reset='cap5_rst_RN')),
    ('north', 180, 'ck_CAP_RN', 'cap5_rst_RN', '{cap5_n_v,cap5_n_a,cap5_n_d}', '{cw_v_x[9:6],cw_a_x[119:72],cw_d_x[319:192]}', {}),
    ('south', 270, 'ck_CAP_RS', 'cap5_rst_RS', '{cap5_s_v,cap5_s_a,cap5_s_d}', '{cw_v_x[5:0],cw_a_x[71:0],cw_d_x[191:0]}', {}),
    ('fault', 1, 'ck_CAP_RS', 'cap5_rst_RS', 'cap5_fault', 'f_cap', {}),
]
CAP_REGIONS = {'CAP_RT': 'ck_CAP_RT', 'CAP_CW': 'ck_CAP_CW', 'CAP_CE': 'ck_CAP_CE', 'CAP_RN': 'ck_CAP_RN', 'CAP_RS': 'ck_CAP_RS'}


def landing(name, width, clock, reset, source, target, read_clock='ck_C', read_reset='cap5_rst_C'):
    return f'''
    wire [4*{width}-1:0] cap5_{name}_bank;
    wire [11:0] cap5_{name}_epo;
    wire [4*(({width}+23)/24)-1:0] cap5_{name}_vld;
    ot_pl_land_n32_chunk_w #(.W({width}), .D(4), .CHUNK_BITS(24)) u_lpl_cap5_{name}_w
        (.ck({clock}), .rsi({reset}), .i({source}), .bank(cap5_{name}_bank),
         .epo(cap5_{name}_epo), .vld(cap5_{name}_vld));
    ot_pl_land_chunk_r #(.W({width}), .D(4), .K(2), .CHUNK_BITS(24)) u_lpl_cap5_{name}_r
        (.ck({read_clock}), .rsi({read_reset}), .bank(cap5_{name}_bank),
         .epo(cap5_{name}_epo), .vld(cap5_{name}_vld), .o({target}));
'''


def emit(text):
    old = 'ot_s81sl_slice_c1x_k8_lp'
    new = 'ot_s81sl_slice_c1x_k8_cap5_lp'
    text = text.replace(old, new)
    text = text.replace('    input wire ck_C,', '''    // Five distinct CAP regional roots; parent integration must export each.
    input wire ck_CAP_RT, ck_CAP_CW, ck_CAP_CE, ck_CAP_RN, ck_CAP_RS,
    input wire ck_C,''', 1)
    lines = [line for line in text.splitlines() if 'wire lpr_c_u_cap;' not in line]
    i = next(i for i, line in enumerate(lines) if 'ot_s81sl_capc2 u_cap (' in line)
    line = lines[i].replace('ot_s81sl_capc2 u_cap (.clk(ck_C),',
        'ot_s81sl_capc5c u_cap (.ck_rt(ck_CAP_RT), .ck_cw(ck_CAP_CW), .ck_ce(ck_CAP_CE), .ck_rn(ck_CAP_RN), .ck_rs(ck_CAP_RS),')
    substitutions = {
        'rst_n(lpr_c_u_cap)': 'rst_n(cap5_rst_RT)',
        'rt_w(rt_q[279:0])': 'rt_w(cap5_w_in)',
        'rt_e(rt_q[559:280])': 'rt_e(cap5_e_in)',
        'cfg_v(cfg_v)': 'cfg_v(cap5_cfg_in[160])',
        'cfg_d(cfg_d)': 'cfg_d(cap5_cfg_in[159:0])',
        'cw_s_v(cw_v_x[5:0])': 'cw_s_v(cap5_s_v)',
        'cw_s_a(cw_a_x[71:0])': 'cw_s_a(cap5_s_a)',
        'cw_s_d(cw_d_x[191:0])': 'cw_s_d(cap5_s_d)',
        'cw_n_v(cw_v_x[9:6])': 'cw_n_v(cap5_n_v)',
        'cw_n_a(cw_a_x[119:72])': 'cw_n_a(cap5_n_a)',
        'cw_n_d(cw_d_x[319:192])': 'cw_n_d(cap5_n_d)',
        'fault(f_cap)': 'fault(cap5_fault)',
    }
    for before, after in substitutions.items():
        line = line.replace(before, after)
    declarations = '''
    // CLOSED child: physical/ref_tile/s81sl_capc5k/views/ot_s81sl_capc5c.
    // CAP internal plain regional reset distribution remains a known source
    // limitation; these new output landings do not waive it.
    wire [5:0] cap5_s_v; wire [71:0] cap5_s_a; wire [191:0] cap5_s_d;
    wire [3:0] cap5_n_v; wire [47:0] cap5_n_a; wire [127:0] cap5_n_d;
    wire [279:0] cap5_w_in, cap5_e_in;
    wire [160:0] cap5_cfg_in;
    wire cap5_fault, cap5_rst_RN, cap5_rst_RS, cap5_rst_CW, cap5_rst_CE, cap5_rst_RT, cap5_rst_C;
    ot_reset_sync #(.ASYNC_STAGES(2)) u_cap5_reset_RN
        (.clk(ck_CAP_RN), .async_rst_n(rst_n), .sync_rst_n(cap5_rst_RN));
    ot_reset_sync #(.ASYNC_STAGES(2)) u_cap5_reset_RS
        (.clk(ck_CAP_RS), .async_rst_n(rst_n), .sync_rst_n(cap5_rst_RS));
    ot_reset_sync #(.ASYNC_STAGES(2)) u_cap5_reset_CW
        (.clk(ck_CAP_CW), .async_rst_n(rst_n), .sync_rst_n(cap5_rst_CW));
    ot_reset_sync #(.ASYNC_STAGES(2)) u_cap5_reset_CE
        (.clk(ck_CAP_CE), .async_rst_n(rst_n), .sync_rst_n(cap5_rst_CE));
    ot_reset_sync #(.ASYNC_STAGES(2)) u_cap5_reset_RT
        (.clk(ck_CAP_RT), .async_rst_n(rst_n), .sync_rst_n(cap5_rst_RT));
    ot_reset_sync #(.ASYNC_STAGES(2)) u_cap5_reset_C
        (.clk(ck_C), .async_rst_n(rst_n), .sync_rst_n(cap5_rst_C));
'''
    rings = ''.join(landing(*L[:6], **L[6]) for L in LANDINGS)
    lines[i] = declarations + line + rings
    return ('// OPT-IN CAPC5k physical source binding, +12 capture edges versus capc2.\n'
            '// Compile matching op schedule with OT_S81_CAP5_C=1.\n' + '\n'.join(lines) + '\n')


def record(base, rtl_path):
    """The landed record of the CAP5 parent: the lp.py record of ot_s81sl_slice_c1x_k8_lp (the source this file
    transforms) plus the five CAP regions and the six CAP landings above.  The RTL transform is the only change."""
    rec = json.loads(json.dumps(base))
    old, new = 'ot_s81sl_slice_c1x_k8_lp', 'ot_s81sl_slice_c1x_k8_cap5_lp'
    assert rec.get('generator') == 'tools/landed_parent/lp.py' and rec.get('top') == old, 'base is not the k8 lp record'
    rec['top'] = new
    rec['derived_by'] = {'tool': 'tools/s81_slice/bind_cap5_parent.py', 'base_record_top': old, 'rtl': str(rtl_path),
                         'note': 'lp.py record of the k8 parent + CLOSED CAPC5k five-clock child (503dcae1b/e450c42b2)'}
    rec['regions']['C']['children'] = [c for c in rec['regions']['C']['children'] if c != 'u_cap']
    for r, port in CAP_REGIONS.items():
        rec['regions'][r] = {'clock_port': port, 'children': ['u_cap'] if r == 'CAP_RT' else [],
                             'note': f'u_cap.{port.lower().replace("ck_cap_", "ck_")} (CLOSED ot_s81sl_capc5c region root)'}
    port_region = {v: k for k, v in CAP_REGIONS.items()}
    port_region['ck_C'] = 'C'
    for name, width, wck, _wr, src, dst, kw in LANDINGS:
        rck = kw.get('read_clock', 'ck_C')
        rec['landings'].append({'name': f'cap5_{name}', 'net': src, 'src_region': port_region[wck],
                                'dst_region': port_region[rck], 'width': width, 'readers': [dst],
                                'ring': f'u_lpl_cap5_{name}_w ({wck})', 'read': f'u_lpl_cap5_{name}_r ({rck})',
                                'added_edges': 3, 'sdc': f'set_multicycle_path -setup 2 / -hold 3 -from u_lpl_cap5_{name}_w.* '
                                f'-to u_lpl_cap5_{name}_r.*'})
    pairs = sorted({'-'.join(sorted((port_region[L[2]], port_region[L[6].get('read_clock', 'ck_C')]))) for L in LANDINGS})
    rec['communicating_region_pairs']['landed'] = sorted(set(rec['communicating_region_pairs']['landed']) | set(pairs))
    rec['reset'].setdefault('cap5', {'note': 'each CAP region and the C-side CAP writer reset by ot_reset_sync '
                                    '(2 stages, own region clock) from rst_n; CAP internal plain regional reset fix owed (no waiver)',
                                    'regions': sorted(CAP_REGIONS)})
    rec['compiler']['child_offset_edges']['u_cap'] = 3
    rec['compiler']['cap5_capture_extra_edges'] = 12
    rec['compiler']['cap5_env'] = {'OT_S81_CAP5_C': '1'}
    rec['flops']['landing'] += sum(4 * L[1] for L in LANDINGS)
    rec['die_obligations'] = list(rec['die_obligations']) + [
        'CAP regions CAP_RT/CW/CE/RN/RS: one root per u_cap clock pin; C<->CAP crossings are D4/K2 landings (no phase alignment)']
    rec['audit'] = dict(rec.get('audit') or {}, landings=len(rec['landings']))
    return rec


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--record-in', type=Path, help='lp.py record of the k8 source parent')
    ap.add_argument('--record-out', type=Path, help='derived landed record of the CAP5 parent')
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(emit(args.source.read_text()))
    if args.record_in and args.record_out:
        args.record_out.parent.mkdir(parents=True, exist_ok=True)
        args.record_out.write_text(json.dumps(record(json.loads(args.record_in.read_text()), args.out), indent=1) + '\n')
