#!/usr/bin/env python3
"""Margin-first DS fused head component lockstep (default-off MARGIN / ADDR_PIPE): ctx zero-cycle trees,
hardened SRAM request distribution, five-deep fault retirement; each with negative controls."""
import argparse, hashlib, json, subprocess, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
D = 'rtl/hdc/v41/dspark_fused_head'
SRAM = 'physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v'
CTX = ['rtl/hdc/ot_hdc_delay.sv', 'rtl/hdc/ot_hdc_fpu.sv', 'rtl/hdc/ot_hdc_sfu.sv', 'rtl/hdc/ot_hdc_fastfp.sv',
       'rtl/hdc/ot_hdc_prefix.sv', 'rtl/hdc/ot_hdc_fp32_add_lat.sv', 'rtl/proto/ot_fp32_add_rne_pipe.sv',
       'rtl/hdc/ot_hdc_fp32_mul_pipe.sv', 'rtl/proto/ot_fp32_mul_rne_pipe.sv',
       f'{D}/capture_candidate/ot_hdc_v41_matvec.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_ctx.sv']
BENCH = {
  'ctx': dict(top='tb_fh_margin_ctx', srcs=CTX + [f'{D}/margin/tb_fh_margin_ctx.sv'], mut={
      'fsel_tap': (f'{D}/capture_candidate/ot_hdc_v41_fh_ctx.sv', '.d(fline[DF-3]),.q(fsel_m[fg])', '.d(fline[DF-2]),.q(fsel_m[fg])'),
      'iwg_tap': (f'{D}/capture_candidate/ot_hdc_v41_fh_ctx.sv', '.d(iw_go_n), .q(iwg_m[ic])', '.d(iw_go), .q(iwg_m[ic])'),
      'row_copy': (f'{D}/capture_candidate/ot_hdc_v41_fh_ctx.sv', '.d(leaf_row_in), .q(row_qg[rg])', '.d(leaf_row_in ^ 16\'d1), .q(row_qg[rg])'),
      'index_replica': (f'{D}/capture_candidate/ot_hdc_v41_fh_ctx.sv', '.d(am_idx_in), .q(am_idx_x)', '.d(am_idx), .q(am_idx_x)'),
      'rv_tap': (f'{D}/capture_candidate/ot_hdc_v41_matvec.sv', '.D(RETURN_EXTRA - 2)) u_return_valid', '.D(RETURN_EXTRA - 1)) u_return_valid')}),
  'addr_pipe': dict(top='tb_fh_margin_addr_pipe', srcs=[SRAM, 'rtl/dft/ot_rom_secded_dec.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_sram_return.sv',
      f'{D}/lane_hardened/ot_hdc_v41_fh_sram_return_hardened.sv', f'{D}/margin/tb_fh_margin_addr_pipe.sv'], mut={
      'no_delay_ref': ('PARAM', 'MUT', '1'),
      'lane_mask': (f'{D}/lane_hardened/ot_hdc_v41_fh_sram_return_hardened.sv', '.write_ok_d(g_wok[GR]&&s_wmask[b])', '.write_ok_d(g_wok[GR])')}),
  'addr_pipe3': dict(top='tb_fh_margin_addr_pipe', params=['-GAP=3'], srcs=[SRAM, 'rtl/dft/ot_rom_secded_dec.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_sram_return.sv',
      f'{D}/lane_hardened/ot_hdc_v41_fh_sram_return_hardened.sv', f'{D}/margin/tb_fh_margin_addr_pipe.sv'], mut={
      'no_delay_ref': ('PARAM', 'MUT', '1'),
      'pin_stage_skip': (f'{D}/lane_hardened/ot_hdc_v41_fh_sram_return_hardened.sv', 'assign g_rok=g_rok2;', 'assign g_rok=g_rok1;')}),
  'endpoint_fpipe': dict(top='tb_fh_checked_permission', params=['-GMARGIN=1', '-GFPIPE=1'],
      srcs=['rtl/dsrom_sys/protected_vm/ot_dsrom_vm_pkg.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_checked_permission.sv',
            f'{D}/capture_candidate/ot_hdc_v41_fh_vm_endpoint_ctx.sv', f'{D}/margin/tb_fh_margin_checked_permission.sv'], mut={
      'age5': (f'{D}/capture_candidate/ot_hdc_v41_fh_checked_permission.sv', "AGE=FPIPE?3'd6:3'd5", "AGE=3'd5"),
      'no_wide_veto': (f'{D}/capture_candidate/ot_hdc_v41_fh_checked_permission.sv', 'wide_bad=FPIPE?checked_error:', 'wide_bad=FPIPE?1\'b0:'),
      'drop_bank0': (f'{D}/capture_candidate/ot_hdc_v41_fh_checked_permission.sv', '.bad({metadata_bad,identity_bad,request_bad,reply_bad})', '.bad({metadata_bad,identity_bad,request_bad[RB-1:1],1\'b0,reply_bad})')}),
  'head_q': dict(top='tb_fh_head_q', params=['-GFPIPE=1'], srcs=['rtl/dsrom_sys/protected_vm/ot_dsrom_vm_pkg.sv'] + CTX + [SRAM,
      'rtl/dft/ot_rom_secded_dec.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_sram_return.sv',
      f'{D}/lane_hardened/ot_hdc_v41_fh_sram_return_hardened.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_fault_retire.sv',
      f'{D}/capture_candidate/ot_hdc_v41_fh_retire_parent.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_checked_permission.sv',
      f'{D}/capture_candidate/ot_hdc_v41_fh_vm_endpoint_ctx.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_macro_ctx.sv',
      f'{D}/quad/ot_hdc_v41_fh_quad.sv', f'{D}/quad/ot_hdc_v41_fh_head_top.sv', f'{D}/quad/ot_hdc_v41_fh_head_q.sv',
      f'{D}/quad/tb_fh_head_q.sv'], mut={
      'fsel_skip': (f'{D}/quad/ot_hdc_v41_fh_quad.sv', '.d(fsel_g), .q(fused_lane_v[l])', '.d(fsel_m), .q(fused_lane_v[l])'),
      'rh_depth': (f'{D}/quad/ot_hdc_v41_fh_quad.sv', '.D(2 + RETURN_EXTRA)) u_rh', '.D(1 + RETURN_EXTRA)) u_rh'),
      'idx_group': (f'{D}/quad/ot_hdc_v41_fh_quad.sv', "wire idx_group = gid == 2'd0;", "wire idx_group = 1'b1;"),
      'wok_mask': (f'{D}/quad/ot_hdc_v41_fh_quad.sv', '.write_ok_d(wok_q && s_wmask[l])', '.write_ok_d(wok_q)')}),
  'head_q_qpin': dict(top='tb_fh_head_q', params=['-GFPIPE=1', '-GQPIN=1'], srcs=['rtl/dsrom_sys/protected_vm/ot_dsrom_vm_pkg.sv'] + CTX + [SRAM,
      'rtl/dft/ot_rom_secded_dec.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_sram_return.sv',
      f'{D}/lane_hardened/ot_hdc_v41_fh_sram_return_hardened.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_fault_retire.sv',
      f'{D}/capture_candidate/ot_hdc_v41_fh_retire_parent.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_checked_permission.sv',
      f'{D}/capture_candidate/ot_hdc_v41_fh_vm_endpoint_ctx.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_macro_ctx.sv',
      f'{D}/quad/ot_hdc_v41_fh_quad.sv', f'{D}/quad/ot_hdc_v41_fh_head_top.sv', f'{D}/quad/ot_hdc_v41_fh_head_q.sv',
      f'{D}/quad/tb_fh_head_q.sv'], mut={
      'pin_wdata_skip': (f'{D}/quad/ot_hdc_v41_fh_quad.sv', 's_wdata <= s_wdata0;', 's_wdata <= wr_data_in;'),
      'pin_rok_skip': (f'{D}/quad/ot_hdc_v41_fh_quad.sv', 'assign rok_q = rok_p;', 'assign rok_q = rok;'),
      'wok_mask': (f'{D}/quad/ot_hdc_v41_fh_quad.sv', '.write_ok_d(wok_q && s_wmask[l])', '.write_ok_d(wok_q)')}),
  'endpoint_fpipe2': dict(top='tb_fh_checked_permission', params=['-GMARGIN=1', '-GFPIPE=2'],
      srcs=['rtl/dsrom_sys/protected_vm/ot_dsrom_vm_pkg.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_checked_permission.sv',
            f'{D}/capture_candidate/ot_hdc_v41_fh_vm_endpoint_ctx.sv', f'{D}/margin/tb_fh_margin_checked_permission.sv'], mut={
      'pin_data_skip': (f'{D}/capture_candidate/ot_hdc_v41_fh_vm_endpoint_ctx.sv', 'data_q<=head_data;', 'data_q<=0;'),
      'no_wide_veto': (f'{D}/capture_candidate/ot_hdc_v41_fh_checked_permission.sv', 'wide_bad=FPIPE?checked_error:', 'wide_bad=FPIPE?1\'b0:'),
      'drop_bank0': (f'{D}/capture_candidate/ot_hdc_v41_fh_checked_permission.sv', '.bad({metadata_bad,identity_bad,request_bad,reply_bad})', '.bad({metadata_bad,identity_bad,request_bad[RB-1:1],1\'b0,reply_bad})')}),
  'head_q_safe': dict(top='tb_fh_head_q', params=['-GFPIPE=2', '-GQPIN=1', '-GSAFE=1'], srcs=['rtl/dsrom_sys/protected_vm/ot_dsrom_vm_pkg.sv'] + CTX + [SRAM,
      'rtl/dft/ot_rom_secded_dec.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_sram_return.sv',
      f'{D}/lane_hardened/ot_hdc_v41_fh_sram_return_hardened.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_fault_retire.sv',
      f'{D}/capture_candidate/ot_hdc_v41_fh_retire_parent.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_checked_permission.sv',
      f'{D}/capture_candidate/ot_hdc_v41_fh_vm_endpoint_ctx.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_macro_ctx.sv',
      f'{D}/quad/ot_hdc_v41_fh_quad.sv', f'{D}/quad/ot_hdc_v41_fh_head_top.sv', f'{D}/quad/ot_hdc_v41_fh_head_q.sv',
      f'{D}/quad/tb_fh_head_q.sv'], mut={
      'pin_wdata_skip': (f'{D}/quad/ot_hdc_v41_fh_quad.sv', 's_wdata <= s_wdata0;', 's_wdata <= wr_data_in;'),
      'fold_skip': (f'{D}/quad/ot_hdc_v41_fh_head_top.sv', 'assign argmax_fold=f2;', 'assign argmax_fold=^f1;'),
      'wok_mask': (f'{D}/quad/ot_hdc_v41_fh_quad.sv', '.write_ok_d(wok_q && s_wmask[l])', '.write_ok_d(wok_q)')}),
  'head_q_hq': dict(top='tb_fh_head_q', params=['-GFPIPE=2', '-GQPIN=1', '-GSAFE=1', '-GHQ=1'], srcs=['rtl/dsrom_sys/protected_vm/ot_dsrom_vm_pkg.sv'] + CTX + [SRAM,
      'rtl/dft/ot_rom_secded_dec.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_sram_return.sv',
      f'{D}/lane_hardened/ot_hdc_v41_fh_sram_return_hardened.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_fault_retire.sv',
      f'{D}/capture_candidate/ot_hdc_v41_fh_retire_parent.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_checked_permission.sv',
      f'{D}/capture_candidate/ot_hdc_v41_fh_vm_endpoint_ctx.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_macro_ctx.sv',
      f'{D}/quad/ot_hdc_v41_fh_quad.sv', f'{D}/quad/ot_hdc_v41_fh_hquad.sv', f'{D}/quad/ot_hdc_v41_fh_head_top.sv', f'{D}/quad/ot_hdc_v41_fh_head_q.sv',
      f'{D}/quad/tb_fh_head_q.sv'], mut={
      'half_wdata': (f'{D}/quad/ot_hdc_v41_fh_head_q.sv', '.wr_data_in(wr_data[32*L0+:256])', '.wr_data_in(wr_data[32*W*g+:256])'),
      'hid_index': (f'{D}/quad/ot_hdc_v41_fh_hquad.sv', '.lane_in({iw_e_x[LW-1] ^ hid, iw_e_x[LW-2:0]})', '.lane_in(iw_e_x[LW-1:0])'),
      'half_leaf': (f'{D}/quad/ot_hdc_v41_fh_head_q.sv', '.leaf_mask_in(leaf_mask_in[L0+:8])', '.leaf_mask_in(leaf_mask_in[W*g+:8])')}),
  'head_q_lret': dict(top='tb_fh_head_q', params=['-GFPIPE=2', '-GQPIN=1', '-GSAFE=1', '-GHQ=1', '-GLRET=1'], srcs=['rtl/dsrom_sys/protected_vm/ot_dsrom_vm_pkg.sv'] + CTX + [SRAM,
      'rtl/dft/ot_rom_secded_dec.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_sram_return.sv',
      f'{D}/lane_hardened/ot_hdc_v41_fh_sram_return_hardened.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_fault_retire.sv',
      f'{D}/capture_candidate/ot_hdc_v41_fh_retire_parent.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_checked_permission.sv',
      f'{D}/capture_candidate/ot_hdc_v41_fh_vm_endpoint_ctx.sv', f'{D}/capture_candidate/ot_hdc_v41_fh_macro_ctx.sv',
      f'{D}/quad/ot_hdc_v41_fh_quad.sv', f'{D}/quad/ot_hdc_v41_fh_hquad.sv', f'{D}/quad/ot_hdc_v41_fh_head_top.sv', f'{D}/quad/ot_hdc_v41_fh_head_q.sv',
      f'{D}/quad/tb_fh_head_q.sv'], mut={
      'lret_depth': (f'{D}/quad/ot_hdc_v41_fh_head_q.sv', '.LRET(LRET?7:0)) u_hq', '.LRET(LRET?6:0)) u_hq'),
      'veto_skip': (f'{D}/quad/ot_hdc_v41_fh_hquad.sv', 'veto_q <= lane_veto_in;', 'veto_q <= 0;'),
      'ep_addr': (f'{D}/quad/ot_hdc_v41_fh_head_q.sv', '.head_we(o_we),.head_addr(r_oa)', '.head_we(o_we),.head_addr(t_oa)')}),
  'retire': dict(top='tb_fh_margin_retire', srcs=[f'{D}/capture_candidate/ot_hdc_v41_fh_fault_retire.sv', f'{D}/margin/tb_fh_margin_retire.sv'], mut={
      'drop_group_fault': ('PARAM', 'MUT', '1'), 'no_offset': ('PARAM', 'MUT', '2')}),
}
def run(name, b, mut, tmp):
    srcs = [ROOT / s for s in b['srcs']]; params = list(b.get('params', []))
    if mut:
        f, a, c = mut
        if f == 'PARAM': params += [f'-G{a}={c}']
        else:
            t = Path(tmp) / Path(f).name; s = (ROOT / f).read_text(); assert s.count(a) == 1, (f, a)
            t.write_text(s.replace(a, c)); srcs = [t if x == ROOT / f else x for x in srcs]
    obj = Path(tmp) / 'obj'
    c = subprocess.run(['verilator', '--binary', '-O1', '-Wno-fatal', '-Wno-WIDTH', '-Wno-UNUSED', '-Wno-TIMESCALEMOD', '-Wno-UNOPTFLAT',
                        '-Wno-MULTIDRIVEN', '-Wno-IMPORTSTAR', '--top-module', b['top'], '-Mdir', str(obj), *params, *map(str, srcs)], capture_output=True, text=True)
    if c.returncode: return dict(returncode=c.returncode, output=c.stderr[-800:])
    p = subprocess.run([str(obj / f"V{b['top']}")], capture_output=True, text=True)
    lines = [l for l in (p.stdout + p.stderr).splitlines() if 'PASS' in l or 'Fatal' in l or 'FATAL' in l or 'Error' in l]
    return dict(returncode=p.returncode, output=(lines[0] if lines else (p.stdout + p.stderr).strip()[-160:])[:200])
def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('--only', nargs='*'); a = ap.parse_args()
    out = {'pass': True, 'cases': {}}
    for name, b in BENCH.items():
        if a.only and name not in a.only: continue
        for m, mut in [('baseline', None), *b['mut'].items()]:
            with tempfile.TemporaryDirectory(prefix='fh-margin-') as tmp:
                r = run(name, b, mut, tmp)
            ok = (r['returncode'] == 0 and 'PASS' in r['output']) if m == 'baseline' else r['returncode'] != 0
            out['cases'][f'{name}/{m}'] = dict(r, expected='PASS' if m == 'baseline' else 'FAIL', ok=ok)
            out['pass'] &= ok
            print(name, m, 'ok' if ok else 'UNEXPECTED', r['output'][:120], flush=True)
    out['source_sha256'] = {s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for b in BENCH.values() for s in b['srcs']}
    print(json.dumps(out, indent=1))
    raise SystemExit(0 if out['pass'] else 1)
if __name__ == '__main__': main()
