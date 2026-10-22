#!/usr/bin/env python3
"""Emit an opt-in k8 parent using CLOSED CAPC5k, with explicit CAP clocks.

The CAP input and output buses cross through D=4/K=2 landings. Each direction
adds three edges, hence twelve total capture edges vs capc2. Existing C-clock
bundle writers stay in place.
This is source integration; the combined parent has no closure claim.
"""
import argparse
from pathlib import Path


def landing(name, width, clock, reset, source, target, read_clock='ck_C', read_reset='cap5_rst_C'):
    return f'''
    wire [4*{width}-1:0] cap5_{name}_bank;
    wire [11:0] cap5_{name}_epo;
    wire [4*(({width}+23)/24)-1:0] cap5_{name}_vld;
    ot_pl_land_n32_chunk_w #(.W({width}), .D(4), .CHUNK_BITS(24)) u_cap5_{name}_w
        (.ck({clock}), .rsi({reset}), .i({source}), .bank(cap5_{name}_bank),
         .epo(cap5_{name}_epo), .vld(cap5_{name}_vld));
    ot_pl_land_chunk_r #(.W({width}), .D(4), .K(2), .CHUNK_BITS(24)) u_cap5_{name}_r
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
    rings = landing('west_in', 280, 'ck_C', 'cap5_rst_C', 'rt_q[279:0]', 'cap5_w_in',
                    'ck_CAP_CW', 'cap5_rst_CW')
    rings += landing('east_in', 280, 'ck_C', 'cap5_rst_C', 'rt_q[559:280]', 'cap5_e_in',
                     'ck_CAP_CE', 'cap5_rst_CE')
    rings += landing('cfg_in', 161, 'ck_C', 'cap5_rst_C', '{cfg_v,cfg_d}', 'cap5_cfg_in',
                     'ck_CAP_RN', 'cap5_rst_RN')
    rings += landing('north', 180, 'ck_CAP_RN', 'cap5_rst_RN',
                    '{cap5_n_v,cap5_n_a,cap5_n_d}', '{cw_v_x[9:6],cw_a_x[119:72],cw_d_x[319:192]}')
    rings += landing('south', 270, 'ck_CAP_RS', 'cap5_rst_RS',
                     '{cap5_s_v,cap5_s_a,cap5_s_d}', '{cw_v_x[5:0],cw_a_x[71:0],cw_d_x[191:0]}')
    rings += landing('fault', 1, 'ck_CAP_RS', 'cap5_rst_RS', 'cap5_fault', 'f_cap')
    lines[i] = declarations + line + rings
    return ('// OPT-IN CAPC5k physical source binding, +12 capture edges versus capc2.\n'
            '// Compile matching op schedule with OT_S81_CAP5_C=1.\n' + '\n'.join(lines) + '\n')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(emit(args.source.read_text()))
