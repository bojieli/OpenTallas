"""OPUS-FIX-S81-SVC-R9 11-22: hi4 att memory fit kit-RTL post step (s81_svc_hi4_att_fit.py), fail-closed."""
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

import s81_svc_hi4_att_fit as F

HOOK = Path(__file__).resolve().parents[1] / 'autopilot/kit_rtl_post.d/s81_svc_hi4_att_fit.sh'
P, E, G = F.PREFIX, F.ENGINE, F.GENERATE
RD = P + 'pmem_RD_DATA'
TR_HDR = """module ot_hdc_v41x_attn_tr_x #(
    parameter integer TD = 64,
    parameter integer NL = 2,
    parameter integer DPT = 4,
    parameter integer XOFF = 0
) (
    input wire clk,
    input wire [NL-1:0] a,
    output wire [TD-1:0] y
);
endmodule
"""


def bound_text():
    pr, phase, owner = P + 'driver_pr_Q[8:0]', P + '765_Y[1:0]', P + '768_Y[0]'
    push, wptr = E + '111_Y[0]', E + 'driver_g_pskid_wp_Q[0]'
    sk = [E + f'driver_g_pskid_sk{i}_Q' for i in range(2)]
    sq = [G + f'u_eng_driver_g_pskid_sk{i}_q' for i in range(2)]
    mux = [E + 'src_82dbfb880ff11832511c_Y', E + 'src_78b0a765f0fe2c615f5d_Y']
    pay, packed, second, ph2 = P + '785_Y', P + 'src_fbec4fd5cfde05d7eac1_Y', P + 'src_5877571a652d7724a45d_Y', P + 'src_64bef01d53623389636d_Y'
    s0, s1, nw = E + 'src_bafb416dc3650d88b313_Y', E + 'src_b3fd49500983f7d3ad57_Y', E + 'src_9b63422bdfff6b0a1f85_Y'
    L = [f'module {F.BOUND}(input clk);',
         f'  wire [1023:0] {RD};', f'  wire [1023:0] {pay};', f'  wire [1023:0] {packed};', f'  wire [511:0] {second};',
         f'  wire [1023:0] {mux[0]};', f'  wire [1023:0] {mux[1]};', f'  reg [1023:0] {sq[0]};', f'  reg [1023:0] {sq[1]};',
         f"  ot_bind_native_193c9bdc13b0c4251a5bbbc4 {G}pmem (.RD_ADDR({{{pr}, {P}src_1651537f0099f5e8b296_Y[8:0]}}), "
         f".RD_DATA({RD}), .WR_ADDR({P}driver_pw_Q[8:0]), .WR_CLK(clk), .WR_DATA(w_u_rsv_u_att_src_a522b67e2f8d4c0856fd_Q[511:0]), "
         f".WR_EN({P}src_0f96741361b34e41097a_Y[511:0]));",
         f"assign {P}src_1651537f0099f5e8b296_Y = {pr} + 9'b000000001;",
         f"assign {ph2} = {phase} == 2'b10;", f"assign {nw} = !{wptr};",
         f"assign {s0} = {push} && {nw}[0];", f"assign {s1} = {push} && {wptr};",
         f"assign {second} = {ph2}[0] ? {RD}[511:0] : {{512{{1'b1}}}};",
         f"assign {packed} = {owner} ? {{{second}[511:0], {RD}[1023:512]}} : {{1024{{1'b0}}}};",
         f"assign {pay} = {packed}[1023:0];",
         f"assign {mux[0]} = {s0}[0] ? {pay}[1023:0] : {sk[0]}[1023:0];",
         f"assign {mux[1]} = {s1}[0] ? {pay}[1023:0] : {sk[1]}[1023:0];"]
    for i in range(2):
        L += [f'always @(posedge clk) {sq[i]} <= {mux[i]}[1023:0];', f'assign {sk[i]} = {sq[i]};']
    for i in range(2):
        L += [f"    ot_hdc_v41x_attn_staging #(.D(32), .NL(4), .SRAM_MACRO(1'b0), .TROWS(640)) u_u_rsv_u_att_u_a_u_eng_g_stage2_u_stage{i} (", '    );']
    for i in range(4):
        L += [f'    ot_hdc_v41x_attn_tr_x #(.TD(32), .NL(4), .DPT(8), .XOFF({8 * i})) u_u_rsv_u_att_u_a_u_eng_g_tr_{i}_g_x_u_tr (', '    );']
    return '\n'.join(L) + '\nendmodule\n'


def make(tmp_path, text=None, bound=F.BOUND):
    tree, out = tmp_path / 'src', tmp_path / 'w/rtl'
    (tree / 'rtl/hdc/v41x').mkdir(parents=True)
    (tree / 'rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv').write_text(TR_HDR)
    entries, cores = [], []
    for i in range(4):
        v = f'ot_hdc_v41x_attn_tr_x_x{8 * i}'
        d = tree / 'lib' / v
        d.mkdir(parents=True)
        pins = ['clk'] + [f'a[{k}]' for k in range(4)] + [f'y[{k}]' for k in range(32)]
        (d / f'{v}.lef').write_text(''.join(f'  PIN {p}\n    DIRECTION {"OUTPUT" if p[0] == "y" else "INPUT"} ;\n' for p in pins))
        (d / f'{v}.lib').write_text(f'library({v}) {{}}\n')
        (d / 'clock_contract.json').write_text(json.dumps(dict(signed=True, view_lib_sha256=hashlib.sha256((d / f'{v}.lib').read_bytes()).hexdigest())))
        entries.append(dict(lib_contains=f'lib/{v}/', params=dict(TD=32, NL=4, DPT=8, XOFF=8 * i)))
        cores.append(dict(module=F.TR_LOGICAL, params=dict(XOFF=8 * i), physical_master=v,
                          lef=f'lib/{v}/{v}.lef', lib=f'lib/{v}/{v}.lib'))
    (tree / 'tools/die_plan').mkdir(parents=True)
    (tree / 'tools/die_plan/hard_core_built_params.json').write_text(json.dumps(dict(entries=entries)))
    plan = tmp_path / 'plan.json'
    plan.write_text(json.dumps(dict(partition_types={F.ATT: dict(hard_cores=cores)})))
    out.mkdir(parents=True)
    b = out / (bound + '.sv')
    b.write_text(bound_text() if text is None else text)
    (out / 'kit_rtl.f').write_text(str(b) + '\n')
    (out / 'kit_rtl.json').write_text(json.dumps(dict(bound_module=bound, files=[str(b)])))
    return tree, out, plan


def snap(d):
    return {p.name: p.read_bytes() for p in sorted(d.iterdir())}


def test_shipped_codex_fit_assets_are_the_pinned_ones():
    for f, want in F.ASSET_SHA.items():
        assert hashlib.sha256((F.ASSETS / f).read_bytes()).hexdigest()[:12] == want
    fit = (F.ASSETS / 'ot_hdc_v41x_attn_staging_fit.sv').read_text()
    assert 'module ot_hdc_v41x_attn_staging_fit' in fit and 'ot_sram_1r1w_160x265_m1_r0c0' in fit
    cap = (F.ASSETS / 'ot_t7_pmem_capture_v2.sv').read_text()
    assert cap.count('ot_sram_1r1w_256x256_m1_r0c0 ram') == 1 and 'module ot_t7_pmem_capture_v2' in cap


def test_att_bound_gets_the_fit(tmp_path):
    tree, out, plan = make(tmp_path)
    r = F.apply(out, plan, F.ATT, tree)
    assert r['status'] == 'APPLIED'
    s = (out / (F.BOUND + '.sv')).read_text()
    assert s.count("ot_hdc_v41x_attn_staging_fit #(.D(32), .NL(4), .SRAM_MACRO(1'b1), .TROWS(640))") == 2
    assert "SRAM_MACRO(1'b0)" not in s and 'ot_bind_native_193c9bdc13b0c4251a5bbbc4' not in s and RD not in s
    assert s.count('ot_t7_pmem_capture_v2 ' + G + 'pmem_capture (') == 1
    assert F.TR_LOGICAL + ' #' not in s and all(f'ot_hdc_v41x_attn_tr_x_x{8 * i} #' in s for i in range(4))
    listed = (out / 'kit_rtl.f').read_text().split()
    for f in F.ASSET_SHA:
        assert str(out / f) in listed and (out / f).read_bytes() == (F.ASSETS / f).read_bytes()
    bb = (out / 'ot_hdc_v41x_attn_tr_x_x16_bb.v').read_text()
    assert bb.startswith('(* blackbox *)') and 'parameter integer XOFF = 16' in bb and 'parameter integer TD = 32' in bb
    assert json.loads((out / 'kit_rtl.json').read_text())['files'] == listed
    with pytest.raises(F.FitError, match='already applied'):
        F.apply(out, plan, F.ATT, tree)


@pytest.mark.parametrize('old,new', [
    ('src_0f96741361b34e41097a_Y[511:0]));', 'src_0f96741361b34e41097b_Y[511:0]));'),   # other WR_EN net
    ("{1024{1'b0}}", "{1024{1'b1}}"),                                                      # other payload cone
    ('u_eng_g_stage2_u_stage1 (', 'u_eng_g_stage2_u_stageX ('),                            # staging instance gone
    ('.XOFF(16)', '.XOFF(17)'),                                                            # tr params differ from signed
])
def test_any_netlist_difference_fails_closed_and_leaves_the_kit_untouched(tmp_path, old, new):
    t = bound_text()
    assert t.count(old) == 1
    tree, out, plan = make(tmp_path, t.replace(old, new))
    before = snap(out)
    with pytest.raises(F.FitError):
        F.apply(out, plan, F.ATT, tree)
    assert snap(out) == before


def test_other_kits_untouched_and_hook_fails_closed_without_the_tool(tmp_path):
    tree, out, plan = make(tmp_path, 'module s81p_svc_hi_dsdv_svc_rs__t1_bound(input clk);\nendmodule\n', 's81p_svc_hi_dsdv_svc_rs__t1_bound')
    before = snap(out)
    assert F.apply(out, plan, 'svc_hi_dsdv_svc_rs__t1', tree)['status'] == 'NOT_APPLICABLE' and snap(out) == before
    env = dict(TYPE='svc_hi_dsdv_svc_rs__t1', OUT=str(out), PLAN=str(plan), PATH='/usr/bin:/bin')
    r = subprocess.run(['bash', '-c', HOOK.read_text()], cwd=tree, env=env, capture_output=True, text=True)
    assert r.returncode == 0 and snap(out) == before, r.stderr
    tree2, out2, plan2 = make(tmp_path / 'att')
    env.update(TYPE=F.ATT, OUT=str(out2), PLAN=str(plan2))
    r = subprocess.run(['bash', '-c', HOOK.read_text()], cwd=tree2, env=env, capture_output=True, text=True)
    assert r.returncode != 0 and 'S81_HI4_ATT_FIT' in r.stderr
