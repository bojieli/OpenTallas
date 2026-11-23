"""OPUS-FIX-S81-SVC-R9 11-22 (COORD 18:0x): per-helper svc memory closure (s81_svc_mem_cones), its plan rows and the
plan_gate_pre MACROGHOST check."""
import json

import pytest

import plan_gate_pre as PG
import s81_svc_mem_cones as C
import s81_svc_memory_closure as MC

H = C.HELPER


def bound_text(G='g_u_rsv_06_u_u_att_', land=True, pvq='narrow', name='s81p_svc_lo_dsdv_svc_rs__t3_bound'):
    """a minimal svc bound with the structural pmem cone (net names of the J7/J8 narrow-pvq variant)"""
    P, E = 'w_' + G[2:], 'w_' + G[2:] + 'u_eng_'
    U = 'u_' + G[2:]
    RD = P + 'pmem_RD_DATA'
    pr, phase, owner = P + 'driver_pr_Q[8:0]', P + '765_Y[1:0]', P + '768_Y[0]'
    push, wptr = E + '111_Y[0]', E + 'driver_g_pskid_wp_Q[0]'
    sk = [E + f'driver_g_pskid_sk{i}_Q' for i in range(2)]
    sq = [G + f'u_eng_driver_g_pskid_sk{i}_q' for i in range(2)]
    mux = [E + 'src_82dbfb880ff11832511c_Y', E + 'src_78b0a765f0fe2c615f5d_Y']
    pay, packed, second, ph2 = P + '785_Y', P + 'src_fbec4fd5cfde05d7eac1_Y', P + 'src_5877571a652d7724a45d_Y', P + 'src_64bef01d53623389636d_Y'
    s0, s1, nw = E + 'src_bafb416dc3650d88b313_Y', E + 'src_b3fd49500983f7d3ad57_Y', E + 'src_9b63422bdfff6b0a1f85_Y'
    inc = P + 'src_1651537f0099f5e8b296_Y'
    L = [f'module {name}(input clk);',
         f'    wire [1023:0] {RD};', f'    wire [1023:0] {pay};', f'    wire [1023:0] {packed};', f'    wire [511:0] {second};',
         f'    wire [1023:0] {mux[0]};', f'    wire [1023:0] {mux[1]};', f'    reg [1023:0] {sq[0]};', f'    reg [1023:0] {sq[1]};',
         f"    {H['pmem']} {G}pmem (.RD_ADDR({{{pr}, {inc}[8:0]}}), .RD_DATA({RD}), .WR_ADDR({P}driver_pw_Q[8:0]), "
         f".WR_CLK(clk), .WR_DATA(w_u_rsv_06_u_u_att_src_a522b67e2f8d4c0856fd_Q[511:0]), .WR_EN({P}src_0f96741361b34e41097a_Y[511:0]));",
         f"    assign {inc} = {pr} + 9'b000000001;",
         f"    assign {ph2} = {phase} == 2'b10;", f'    assign {nw} = !{wptr};',
         f'    assign {s0} = {push} && {nw}[0];', f'    assign {s1} = {push} && {wptr};',
         f"    assign {second} = {ph2}[0] ? {RD}[511:0] : {{512{{1'b1}}}};",
         f"    assign {packed} = {owner} ? {{{second}[511:0], {RD}[1023:512]}} : {{1024{{1'b0}}}};",
         f'    assign {pay} = {packed}[1023:0];',
         f'    assign {mux[0]} = {s0}[0] ? {pay}[1023:0] : {sk[0]}[1023:0];',
         f'    assign {mux[1]} = {s1}[0] ? {pay}[1023:0] : {sk[1]}[1023:0];']
    for i in range(2):
        L += [f'    always @(posedge clk) {sq[i]} <= {mux[i]}[1023:0];  // loc', f'    assign {sk[i]} = {sq[i]};']
    for i in range(2):
        L += [f"    ot_hdc_v41x_attn_staging #(.D(32), .NL(4), .SRAM_MACRO(1'b0), .TROWS(640)) {U}u_eng_g_stage2_u_stage{i} (", '    );']
    if land:
        L += [f'    {H["land"]} {G}land (.RD_DATA(x));']
    if pvq == 'narrow':
        L += [f'    {C.PVQ_NARROW} {G}pvq (.RD_DATA(y));']
    elif pvq == 'wide':
        L += [f'    {H["pvq"]} {G}pvq (.RD_DATA(y));']
    L += [f'    dsdv_svc_mem_ar #(.AW(3), .W(341)) {U}g_wqm_0_g_pc_0_u_wq_mem (', '    );']
    return '\n'.join(L) + '\nendmodule\n'


def test_helpers_and_steps_of_the_narrow_pvq_variant():
    s = bound_text()
    h = C.helpers(s)
    assert h == dict(pmem=1, pvq=0, land=1, stage=2, pvq_narrow=1)
    assert not MC.applies(s) and MC.closure_kind(s) == 'struct'
    assert C.predict_steps(s) == {'pmem', 'stage'}
    full = bound_text(pvq='wide')
    assert MC.applies(full) and MC.closure_kind(full) == 'class' and C.predict_steps(full) == set(C.STEPS)
    assert MC.closure_kind('module m; endmodule\n') is None


@pytest.mark.parametrize('G', ['g_u_rsv_06_u_u_att_', 'g_u_rsv_01_u_u_att_u_a_', 'g_u_rsv_05_u_u_u_att_u_a_', 'g_u_rsv_u_att_u_a_'])
def test_struct_closure_cuts_pmem_and_flips_staging(G):
    s = bound_text(G)
    closed, steps, rep = C.close_struct(s)
    assert steps == ['stage', 'pmem'] and rep['left_native'] == dict(land=1, pvq_narrow=1)
    assert closed.count('ot_t7_pmem_capture_v2 ' + G + 'pmem_capture (') == 1
    assert H['pmem'] not in closed and 'pmem_RD_DATA' not in closed
    assert closed.count("ot_hdc_v41x_attn_staging_fit #(.D(32), .NL(4), .SRAM_MACRO(1'b1), .TROWS(640))") == 2
    assert "SRAM_MACRO(1'b0)" not in closed
    assert H['land'] in closed and C.PVQ_NARROW in closed          # untouched helpers stay native
    assert s.split(');', 1)[0] == closed.split(');', 1)[0]


@pytest.mark.parametrize('old,new', [
    ('src_0f96741361b34e41097a_Y[511:0]));', 'src_0f96741361b34e41097a_Y[511:0]), .X(z));'),    # extra pmem port
    ("{1024{1'b0}}", "{1024{1'b1}}"),                                                          # other payload cone
    ('_stage1 (', '_stageX ('),                                                                # staging instance missing
    ('assign w_u_rsv_06_u_u_att_u_eng_driver_g_pskid_sk1_Q = ', 'assign w_u_rsv_06_u_u_att_u_eng_driver_g_pskid_sk1_Q = ~'),  # skid output
])
def test_any_cone_difference_refuses(old, new):
    s = bound_text()
    assert s.count(old) == 1
    with pytest.raises(C.ConeError):
        C.close_struct(s.replace(old, new))


def test_skid_reg_with_an_extra_reader_refuses():
    s = bound_text()
    s = s.replace('endmodule', '    assign w_peek = g_u_rsv_06_u_u_att_u_eng_driver_g_pskid_sk0_q[0];\nendmodule')
    with pytest.raises(C.ConeError, match='skid reg'):
        C.close_struct(s)


def test_plan_rows_follow_the_steps():
    rows = [dict(inst='u_bound.g_u_rsv_06_u_u_att_pmem_capture.b[0].s[0].ram'),
            dict(inst='u_bound.g_u_rsv_06_u_u_att_land_capture.g_w[0].g_b[0].ram'),
            dict(inst='u_bound.g_u_rsv_06_u_u_att_pvq_capture.b[0].s'),
            dict(inst='u_bound.u_u_rsv_06_u_u_att_u_eng_g_stage2_u_stage0.g_macro.g_fit.g_lane[0].u_mem'),
            dict(inst='u_bound.u_u_rsv_06_u_g_smt_u_tgt.g_bank[0].u_mem')]
    assert [C.plan_row_group(r['inst']) for r in rows] == ['pmem', 'land', 'pvq', 'stage', None]
    assert [r['inst'] for r in C.ghost_rows(rows, {'pmem', 'stage'})] == [rows[1]['inst'], rows[2]['inst']]
    assert C.ghost_rows(rows, set(C.STEPS)) == []
    raw = dict(partition_types=dict(t=dict(contents=list(rows))))
    assert C.derive_rows(raw, dict(t={'pmem', 'stage'})) == dict(t=[rows[1]['inst'], rows[2]['inst']])
    assert len(raw['partition_types']['t']['contents']) == 3


def test_apply_kit_struct_path_lists_only_the_applied_children(tmp_path):
    bm = 's81p_svc_lo_dsdv_svc_rs__t3_bound'
    b = tmp_path / (bm + '.sv')
    b.write_text(bound_text(name=bm))
    (tmp_path / 'kit_rtl.f').write_text(str(b) + '\n')
    (tmp_path / 'kit_rtl.json').write_text(json.dumps(dict(bound_module=bm, bound_type='svc_lo_dsdv_svc_rs__t3', files=[str(b)])))
    rep = MC.apply_kit(tmp_path)
    assert rep['status'] == 'APPLIED' and rep['kind'] == 'struct' and rep['steps'] == ['stage', 'pmem']
    assert rep['macros_added'] == {'ot_sram_1r1w_160x265_m1_r0c0': 8, 'ot_sram_1r1w_256x256_m1_r0c0': 4}
    kr = json.loads((tmp_path / 'kit_rtl.json').read_text())
    names = [x.rsplit('/', 1)[-1] for x in kr['files']]
    assert 'ot_t7_pmem_capture_v2.sv' in names and 'ot_hdc_v41x_attn_staging_fit.sv' in names
    assert 'ot_t7_land_capture_v2.sv' not in names and 'ot_t7_pvq_capture_v2.sv' not in names
    assert (tmp_path / 'ot_t7_pmem_capture_v2.sv').read_bytes() == MC.struct_child('ot_t7_pmem_capture_v2.sv')
    assert 'ot_t7_pmem_capture_v2' in b.read_text() and set(kr['hard_macros']) == set(rep['macros_added'])
    assert MC.apply_kit(tmp_path)['status'] == 'APPLIED'          # receipt: idempotent, no second transform


def test_apply_kit_struct_witness_difference_fails_and_leaves_the_kit(tmp_path):
    bm = 's81p_svc_lo_dsdv_svc_rs__t3_bound'
    b = tmp_path / (bm + '.sv')
    b.write_text(bound_text(name=bm).replace("{1024{1'b0}}", "{1024{1'b1}}"))
    (tmp_path / 'kit_rtl.json').write_text(json.dumps(dict(bound_module=bm, files=[str(b)])))
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(ValueError):
        MC.apply_kit(tmp_path)
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


def test_macroghost_flags_rows_the_bound_cannot_have(tmp_path):
    rtl = tmp_path / 'bind' / 'rtl'
    rtl.mkdir(parents=True)
    (rtl / 's81p_svc_lo_dsdv_svc_rs__t3.sv').write_text(bound_text())
    (rtl / 's81p_svc_hi_dsdv_svc_rs__t1.sv').write_text(bound_text('g_u_rsv_01_u_u_att_u_a_', pvq='wide'))
    lef = dict(lef='x.lef')
    plan = tmp_path / 'plan.json'
    plan.write_text(json.dumps(dict(partition_types={
        'svc_lo_dsdv_svc_rs__t3': dict(contents=[
            dict(inst='u_bound.g_u_rsv_06_u_u_att_pmem_capture.b[0].s[0].ram', **lef),
            dict(inst='u_bound.g_u_rsv_06_u_u_att_pvq_capture.b[0].s', **lef),
            dict(inst='u_bound.u_u_rsv_06_u_u_att_g_wqm_0_g_pc_0_u_wq_mem.g_m[0].g_32.u_mem', **lef),
            dict(inst='u_bound.u_u_irg_03.g_land[0].u_mem', **lef)]),
        'svc_hi_dsdv_svc_rs__t1': dict(contents=[
            dict(inst='u_bound.g_u_rsv_01_u_u_att_u_a_pvq_capture.b[0].s', **lef)]),
        'no_bind_type': dict(contents=[dict(inst='u_bound.u_x.ram', **lef)])})))
    out = PG.check_macroghost(str(plan), str(tmp_path / 'bind'))
    fails = [x for x in out if x.startswith('FAIL MACROGHOST')]
    warns = [x for x in out if x.startswith('WARN MACROGHOST')]
    assert len(fails) == 1 and 'svc_lo_dsdv_svc_rs__t3: 1 placed' in fails[0] and 'pvq not closed' in fails[0]
    assert len(warns) == 1 and 'u_u_irg_03' in warns[0] and 'wq_mem' not in warns[0]
    assert PG.check_macroghost(str(plan), None) == [] and PG.check_macroghost(str(plan), str(tmp_path / 'none')) == []
    assert 'MACROGHOST' in PG.CLASSES


def test_apply_kit_struct_retypes_tr_cores_of_the_plan_type(tmp_path, monkeypatch):
    import s81_svc_hi4_att_fit as R9
    bm = 's81p_svc_lo_dsdv_svc_rs__t3_bound'
    b = tmp_path / (bm + '.sv')
    b.write_text(bound_text(name=bm))
    (tmp_path / 'kit_rtl.f').write_text(str(b) + '\n')
    (tmp_path / 'kit_rtl_sim.f').write_text(str(b) + '\n')
    (tmp_path / 'kit_rtl.json').write_text(json.dumps(dict(bound_module=bm, files=[str(b)])))
    rows = [dict(module=R9.TR_LOGICAL, physical_master='ot_tr_x%d' % i, params=dict(XOFF=8 * i)) for i in range(4)]
    typ = dict(hard_cores=rows + [dict(module=R9.TR_LOGICAL, params=dict(XOFF=0)), dict(module='other', physical_master='m')])
    seen = {}
    def fake(source, t, tree, engine, expect):
        seen.update(engine=engine, expect=expect, tree=tree)
        assert 'ot_t7_pmem_capture_v2' in source
        return source + '// typed\n', {r['physical_master'] + '_bb.v': b'(* blackbox *)\n' for r in rows}
    monkeypatch.setattr(R9, 'typed_tr', fake)
    rep = MC.apply_kit(tmp_path, typ=typ, tree=tmp_path)
    assert seen == dict(engine='u_u_rsv_06_u_u_att_u_eng_g_tr_', expect=4, tree=tmp_path)
    assert rep['tr_typed'] == sorted('ot_tr_x%d_bb.v' % i for i in range(4)) and b.read_text().endswith('// typed\n')
    names = lambda p: [x.rsplit('/', 1)[-1] for x in p.read_text().split()]
    assert 'ot_tr_x0_bb.v' in names(tmp_path / 'kit_rtl.f') and 'ot_tr_x0_bb.v' not in names(tmp_path / 'kit_rtl_sim.f')
    assert 'ot_tr_x3_bb.v' in [x.rsplit('/', 1)[-1] for x in json.loads((tmp_path / 'kit_rtl.json').read_text())['files']]
    assert MC.tr_rows(dict(hard_cores=[dict(module=R9.TR_LOGICAL)])) == [] and MC.tr_rows(None) == []


def flat_bound(P='u_u_irg_03_', D=139, cite='35b4139a8c40_dsdv_idx_rg3.sv'):
    """a bound with the flat svc_lo reader (13 top-level dsdv_idx_rg2_m1k, J7/J8 bind form)"""
    W = 'w_' + P[2:]
    z8 = lambda n: "{{2{1'b0}}, %s[7:0]}" % n
    def inst(role, ra, wa, wd, re_='x_re[0]', we='x_we[0]'):
        return (f"    dsdv_idx_rg2_m1k #(.SRAM_MACRO(1'b1)) {P}{role} (\n        .ck(clk),\n        .ra({ra}),\n"
                f"        .rd({W}{role}_rd),\n        .re({re_}),\n        .wa({wa}),\n        .wd({wd}),\n        .we({we})\n    );")
    L = ['module s81p_svc_lo_dsdv_svc_rs__t3_bound(input clk);',
         f'    assign {W}x_Y = {W}y;  // structural_full/{cite}:12.1-12.9']
    for k in range(4):
        L.append(inst('g_land_%d_u_h0' % k, f'{W}h0r{k}[9:0]', f'{W}lwa{k}[9:0]', f'{W}lwd{k}[255:0]'))
        L.append(inst('g_land_%d_u_h1' % k, z8(f'{W}c_row'), f'{W}lwa{k}[9:0]', f'{W}lwd{k}[255:0]'))
    for k in range(2):
        L.append(inst('g_lm_%d_u_mem' % k, z8(f'{W}lfr'), z8(f'{W}lfw'), f'{W}lfd[255:0]'))
    L.append(inst('u_iq', f'{W}iqr[9:0]', f'{W}iqw[9:0]', "{{221{1'b0}}, %siqd[34:0]}" % W))
    L.append(inst('u_sq', f'{W}sqr[9:0]', f'{W}sqw[9:0]', "{{217{1'b0}}, %ssqd[38:0]}" % W))
    L += [f'    wire [255:0] {W}u_mq_rd;', f"    assign {W}mqra_Y = {W}mw_Q[9:0] - 10'b{D:010b};",
          inst('u_mq', f'{W}mqra_Y[9:0]', f'{W}mw_Q[9:0]', "{{233{1'b0}}, %smqd[22:0]}" % W, "1'b1", "1'b1"),
          f'    assign {W}use = {W}u_mq_rd[22:0];', 'endmodule']
    return '\n'.join(L) + '\n'


@pytest.mark.parametrize('P,D,T', [('u_u_irg_03_', 139, 12), ('u_u_irg_07_u_rg3_', 139, 12), ('u_u_irg_01_', 123, 0)])
def test_flat_idx_fit_retypes_the_13_reader_memories(P, D, T):
    import s81_svc_idx_fit as IDX
    cite = ('797dbb85dc12_dsdv_idx_rg3_nq_native.sv' if 'u_rg3' in P else '35b4139a8c40_dsdv_idx_rg3.sv')
    b = flat_bound(P, D, cite)
    out, n, mac, rep = IDX.fit_flat(b, MC.ROOT)
    assert n == 13 and mac == IDX.MACROS and rep['mq_depth'] == D and rep['mq_tail'] == T and rep['prefix'] == P
    assert 'dsdv_idx_rg2_m1k' not in out
    assert out.count("dsdv_idx_fit_mem #(.SRAM_MACRO(1'b1), .WORDS(768), .BITS(256)) %sg_land_" % P) == 4
    assert out.count("dsdv_idx_fit_mem #(.SRAM_MACRO(1'b1), .WORDS(256), .BITS(256))") == 6
    assert "dsdv_idx_fit_mem #(.SRAM_MACRO(1'b1), .WORDS(128), .BITS(23)) %su_mq (" % P in out
    W = 'w_' + P[2:]
    if T:
        assert f"wire [9:0] {P}mq_ra_fit = {W}mw_Q[9:0] - 10'd127;" in out and f'.ra({P}mq_ra_fit)' in out
        assert f'reg [{23 * T - 1}:0] {P}mq_sh;' in out and f"assign {W}u_mq_rd = {{{{233{{1'b0}}}}, {P}mq_sh[{23 * T - 1} -: 23]}};" in out
    else:
        assert 'mq_ra_fit' not in out and f'.rd({W}u_mq_rd)' in out
    assert IDX.fit_flat('module m; endmodule\n', MC.ROOT) == ('module m; endmodule\n', 0, {}, None)


@pytest.mark.parametrize('old,new,why', [
    ("{{2{1'b0}}, w_u_irg_03_lfr[7:0]}", 'w_u_irg_03_lfr[9:0]', '8-bit'),
    ("{{217{1'b0}}, ", "{{216{1'b0}}, ", 'wd is not zero'),
    ("10'b0010001011", "10'b0010010000", '>= 144'),
    ('structural_full/35b4139a8c40_dsdv_idx_rg3.sv', 'structural_full/35b4139a8c40_other.sv', 'provenance'),
    ('u_u_irg_03_u_iq (', 'u_u_irg_03_u_iqx (', 'reader roles'),
])
def test_flat_idx_fit_refuses_any_netlist_difference(old, new, why):
    import s81_svc_idx_fit as IDX
    b = flat_bound()
    assert old in b
    with pytest.raises(ValueError, match=why):
        IDX.fit_flat(b.replace(old, new), MC.ROOT)
