"""Exact RTL dependency list of the opt-in static per-PC wires-only parent."""
STATIC = 'rtl/qwen_sys/static_kv_20261014/'
SOURCES = [STATIC + n + '.sv' for n in (
    'qkd_static_kv_pc_path', 'qkd_controller_hbm_calendar',
    'qkd_static_kv_return_calendar', 'qkd_ctrl_pc_host_static',
    'ot_qkd_static_ctrl_pc_emb', 'ot_qkd_static_kv_timing',
    'ot_qkd_static_emb_cdc', 'qkd_static_kv_write_observer',
    'qkd_kv_hbm_elastic_front_mc', 'qkd_static_kv_return_slots_mc')]
SOURCES += [
    'rtl/qwen_sys/kv_die_20261009/ot_qkvd_kcmd_tap.sv',
    'rtl/qwen_sys/emb_hbm_20261008/synth/ot_qfd_emb_pcport.sv',
    'rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_cdc.sv',
    'rtl/qwen_sys/q5_20261009/synth/ot_qfd_kv_landing_ecc.sv',
    'rtl/qwen_sys/host_20261013/qkd_host_static_pc.sv',
    'rtl/lib/ot_async_fifo.sv', 'rtl/lib/ot_reset_sync.sv',
]
