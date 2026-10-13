"""Packing tables of the Qwen ROM TP8 slot cells (gen_slot.py).  Bundle = (contract name, contract width, flow of the
bundle seen from the cell, peer, fields LSB-first)."""
RQ = 'rtl/qwen_sys/redesign_qwen/'
MASTERS = {}

# ---- qfd_tt_ctlm (slot tt_ctlm): body = the TP8 route top ot_qfd_tt_ctlm_i_fpm_tp8 (G 3,072: 24 scale groups, 6 argmax
# partials, 13-b tile selects).  Width-only derivations: tools/qwen_rom_fulldie_b3r2.py TT_BAND_C_BITS / TT_BAND_F_BITS /
# TT_XD_BITS / TT_MX_BITS / LANE_C_BITS and tools/qwen_kv_die/rom_r22k.py O4_BITS.  The seq_su side of st / xs / xm is
# physical/qwen_kv_slots/qfd_seq_su_pack.json: the same field order on both ends.
def _ctlm():
    B = []
    for b in range(3):
        B.append((f'c{b}', 343, 'out', f'sp_port_tiles_{b}.tc',
                  ['t_sel_e', 't_tv_e', 'p_v_e2', 'p_f_e2', 'scale_re', ('scale_gre', 8 * b, 8), ('scale_addr', 192 * b, 192),
                   (None, 2)]))
        B.append((f'f{b}', 107, 'in', f'sp_port_tiles_{b}.tf', [('p_am', 102 * b, 102), ('p_fault', 2 * b, 2), (None, 3)]))
        B.append((f'lc{b}', 28, 'out', f'sp_band_lanes_{b}.c', ['t_sel_e', 't_tv_e', (None, 2)]))
    B += [
     ('ld', 16, 'in', 'sp_vector_memory.ld', ['land_cnt']),
     ('mee', 8, 'out', 'sp_vector_memory.mee', ['me_clk_en'] * 8),
     ('meok', 1, 'in', 'sp_vector_memory.mo', ['me_mem_ok']),
     ('mx', 553, 'out', 'sp_vector_memory.mx', ['mx_data', 'mx_addr', 'mx_mask', 'mx_we']),
     ('pw', 75, 'in', 'd2d_rom.pw', ['pw_data', 'pw_addr', 'pw_v']),
     ('rsi', 1, 'in', 'clk_rx.rso_ctlm', ['rst_n']),
     ('sel', 26, 'out', 'tt_up4_0.sel', ['t_sel_e', 't_tv_e']),
     ('st', 49, 'in', 'seq_su.st', ['prog_base', 'pos', 'token', 'h_start']),
     ('uf', 1, 'in', 'tt_up4_0.flt', ['up_fault']),
     ('xd', 53, 'out', 'sp_vector_memory.xd', ['x_dc', 'x_dcs', 'x_dsp', 'x_dv']),
     ('xr', 1, 'in', 'sp_vector_memory.xr', ['x_rdy']),
     ('xm', 92, 'out', 'seq_su.xm', ['m_fval_o', 'm_fidx_o', 'm_fin_o', 'me_prog_o', 'me_idle_o', 'me_acc_o']),
     ('xs', 57, 'in', 'seq_su.xs', ['x_orows', 'x_oprog', 'x_oidle', 'x_oacc']),
    ]
    return B
MASTERS['qfd_tt_ctlm'] = dict(
    body='ot_qfd_tt_ctlm_i_fpm_tp8', body_file=RQ + 'ot_qfd_tt_ctlm_i_fpm_tp8.sv', bundles=_ctlm(),
    rtl='rtl/physical/ot_qfd_tt_ctlm_slot.sv', shim='rtl/test/qfd_tt_ctlm_slot_shim.sv', mutant=['xm', 'xd', 'c0'],   # mx alone was NOT detected (no mx write in the TXN stimulus): argmax word, x descriptor, split-tree selects
   
    shim_params='#(parameter integer PSRAM = 1, PMUT = 0, HQ2 = 1, MEREG = 3, RRG = 1, PCUT = 1, AUD = 33975, G = 3072, TPMUT = 0) ',
    # body ports with no contract bundle -> extra 1-bit pins (slot_change_request)
    extra=dict(kv_ok='kok', kv_write_drained='kwd', fab_fault='fab', c_fault='cf', ov='ovf'),
    tie=dict(tr_fault=("16'd0", 'retired: the band faults reach the control element through the upper tile (up_fault); '
                                'as ot_qfd_spine_band')),
    open=['kvd_v', 'kvd_wbase', 'kvd_ts', 'kvd_ks', 'kvd_js', 'kvd_wcs', 'kvd_split', 'kvd_jsh', 'kvd_tiles', 'kvd_k',
          'kvd_nout', 'kvd_kindk', 'kvd_pos'],
    notes='Body ports are pin flops in the body (AUD: die-input pin flops, kept output stations): no flop added.\n'
          't_sel_e / t_tv_e / p_v_e2 / p_f_e2 / scale_re leave on every band bundle (c0..2, lc0..2, sel): copies of one\n'
          'body output register set.  kvd_* (the ME-side KV descriptor) are not pins: the die takes the descriptor from\n'
          'seq_su (o4_kvd).  tr_fault is tied 0 (retired input).  kok / kwd / fab / cf / ovf: body ports with no bundle.')
