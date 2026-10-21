#!/usr/bin/env python3
"""KV-CTL10 2026-10-20 (K.STA.CTL): the EXACT native-census successor of the die's generated control tile qkd_kvs_ctl.

The strict die (OT_KV_MU=1 OT_KV_BOOT_AGES=1 ..., tile file qkd_kvs_tiles_hroot_ff_k_mu_ba.sv) binds a wires-only qkd_kvs_ctl
(62 ports, 20 member instances).  Its closed views (mu2 ...) and the KV-CTL3 successor qkd_kvs_ctl_s32 (45 ports: no boot-age
outputs, o_attn 77 b) are a different tile, so kv_tile_views REFUSES them and the die keeps the ctl ASSUMED (a 0.194 mm2
placeholder).  OT_KV_CTL_C32 = 1 | 2 makes kv_static_die.rtl_text() emit THE SAME qkd_kvs_ctl (same 62 ports, same wiring,
same assigns) with the members replaced by their native-census successors, into its own tile file (suffix _c32 / _c32b), so a
kit built from that file passes kv_tile_views identity:

  u_boot qkd_static_kv_boot_dispatch_mu      -> qkd_static_kv_boot_dispatch_mu_s32 (SRQ 2)        qkd_kv_ctl_s32_boot.sv
  u_dcfg qkd_kv_die_cfg_a (AGES 1)           -> qkd_kv_die_cfg_a_c32 (AGES 1)                     qkd_kv_ctl_c32_dcfg.sv
  u_fanr qkd_kv_es_fan_root2_b               -> qkd_kv_es_fan_root2_b_s32 (S32, RCOPIES 32, PH1C)  qkd_kv_ctl_s32_misc.sv
  u_lprg qkd_static_kv_layer_programme_mu    -> qkd_static_kv_layer_programme_s32 (CTLSRAM, RCOPIES 32)
  u_oobs qkd_kv_ownership_obs                -> qkd_kv_ownership_obs_c32 (RCOPIES 2)              qkd_kv_ctl_c32_obs.sv
  u_own  qkd_static_kv_ownership_calendar_mu -> _mu_s32 (PIPE 1, SAFE 1, RCOPIES 12, S32)         qkd_kv_ctl_s32_misc.sv
  u_wprg qkd_kv_native_programme             -> qkd_kv_native_programme_s32 (SRAM, CTLSRAM, NC 4)  qkd_kv_ctl_s32_writer.sv
  u_wrn  qkd_kv_static_writer_native_mu      -> qkd_kv_static_writer_native_mu_s32 (NC 4)          qkd_kv_ctl_s32_writer.sv
         + the programme's kept word slot / index copies (tile-internal wires)
CTLSRAM 1 = 3 x ctl_sram_1r1w_64x64_p192 a table (OT_KV_CTL_C32=1), 2 = 2 x ctl_sram_1r1w_64x128_p192 (=2).
Schedule deltas vs the BA tile (handed to the die schedule / compiler, kit README): u_own PIPE 1 + SAFE 1 = the enter / leave
drain guards sample the group drain 2 edges earlier (compiler QUIET / drain window +2 ck before enter and leave; roots,
windows and every token edge unchanged); u_boot SRQ 2 = setup_ready +2 boot edges (boot level, no static-schedule
consumer).  Every other port edge is unchanged (lockstep benches).  Every substitution must apply exactly once.
"""
import os
import re

CTL_C32 = os.environ.get('OT_KV_CTL_C32', '0')
if CTL_C32 not in ('0', '1', '2'):
    raise ValueError(f'OT_KV_CTL_C32={CTL_C32!r}: 0 (off), 1 (CTLSRAM 1) or 2 (CTLSRAM 2)')
ON = CTL_C32 != '0'
SUFFIX = {'0': '', '1': '_c32', '2': '_c32b'}[CTL_C32]

D = 'rtl/qwen_sys/static_kv_die_20261017/'
M = 'rtl/qwen_sys/mu_qwen_20261018/'
SOURCES = (
    'rtl/lib/ot_s32_cells.sv',
    D + 'qkd_kv_ctl_s32_boot.sv', D + 'qkd_kv_ctl_s32_misc.sv', D + 'qkd_kv_ctl_s32_writer.sv',
    D + 'qkd_kv_ctl_c32_dcfg.sv', D + 'qkd_kv_ctl_c32_obs.sv',
    M + 'qkd_static_kv_layer_programme_s32.sv',
    'physical/asap7_memory_macros_v2/ctl_sram_1r1w_64x64_p192/ctl_sram_1r1w_64x64_p192.v',
    'physical/asap7_memory_macros_v2/ctl_sram_1r1w_64x128_p192/ctl_sram_1r1w_64x128_p192.v',
)


def subs(ctlsram):
    c = int(ctlsram)
    wc = ('(.compiled_word_slot_c(w_wprg__compiled_word_slot_c), '
          '.compiled_word_index_c(w_wprg__compiled_word_index_c), ')
    return [
        ('qkd_static_kv_boot_dispatch_mu #(.MUT(0), .DIECFG(1), .NRST(43), .LINKCFG(1), .ESCFG(1), .DIECAP(1), .MU(1), '
         '.WMUT(0)) u_boot',
         'qkd_static_kv_boot_dispatch_mu_s32 #(.MUT(0), .DIECFG(1), .NRST(43), .LINKCFG(1), .ESCFG(1), .DIECAP(1), .MU(1), '
         '.WMUT(0), .SRQ(2)) u_boot'),
        ('qkd_kv_die_cfg_a #(.NRST(43), .CAP(1), .AGES(1), .MUT(0)) u_dcfg',
         'qkd_kv_die_cfg_a_c32 #(.NRST(43), .CAP(1), .AGES(1), .MUT(0)) u_dcfg'),
        ('qkd_kv_es_fan_root2_b #(.MUT(0)) u_fanr',
         'qkd_kv_es_fan_root2_b_s32 #(.MUT(0), .RCOPIES(32), .PH1C(1), .S32(1)) u_fanr'),
        ('qkd_static_kv_layer_programme_mu #(.MUT(0), .MU(1)) u_lprg',
         f'qkd_static_kv_layer_programme_s32 #(.MUT(0), .MU(1), .CTLSRAM({c}), .RCOPIES(32)) u_lprg'),
        ('qkd_kv_ownership_obs #(.QUIET_WIN(16), .MUT(0)) u_oobs',
         'qkd_kv_ownership_obs_c32 #(.QUIET_WIN(16), .MUT(0), .RCOPIES(2)) u_oobs'),
        ('qkd_static_kv_ownership_calendar_mu #(.MUT(0), .MU(1)) u_own',
         'qkd_static_kv_ownership_calendar_mu_s32 #(.MUT(0), .MU(1), .PIPE(1), .SAFE(1), .RCOPIES(12), .S32(1)) u_own'),
        ('qkd_kv_native_programme #(.MUT(0), .VMAP(1)) u_wprg (',
         f'qkd_kv_native_programme_s32 #(.MUT(0), .VMAP(1), .RCOPIES(20), .SRAM(1), .CTLSRAM({c}), .NC(4)) u_wprg ' + wc),
        ('qkd_kv_static_writer_native_mu #(.MUT(0), .VMAP(1), .MU(1)) u_wrn (',
         'qkd_kv_static_writer_native_mu_s32 #(.MUT(0), .VMAP(1), .MU(1), .NC(4), .RST_COPIES(12)) u_wrn ' + wc),
        ('    wire [0:0] w_wprg__compiled_word_slot;\n',
         '    wire [0:0] w_wprg__compiled_word_slot;\n    wire [3:0] w_wprg__compiled_word_slot_c;\n'
         '    wire [7:0] w_wprg__compiled_word_index_c;\n'),
    ]


def transform(module_txt, ctlsram=None):
    """the qkd_kvs_ctl module text with the native-census members (refuses unless every substitution applies once)"""
    ctlsram = CTL_C32 if ctlsram is None else str(ctlsram)
    if not re.match(r'(//[^\n]*\n)*module qkd_kvs_ctl \(', module_txt):
        raise ValueError('kv_ctl_c32: not the generated qkd_kvs_ctl module (no parameter list expected)')
    out = module_txt
    for old, new in subs(ctlsram):
        n = out.count(old)
        if n != 1:
            raise ValueError(f'kv_ctl_c32: substitution applies {n} times (need 1): {old[:90]}')
        out = out.replace(old, new)
    tag = (f'// KV-CTL10 OT_KV_CTL_C32={ctlsram}: native-census members (tools/qwen_kv_die/kv_ctl_c32.py); same ports, '
           'wiring and assigns as the boot-ages tile.\n')
    return tag + out
