"""Fast checks of the S81 svc memory-closure class port (full chain self-check = 12605dc2 is the packet run)."""
import pytest
import s81_svc_memory_closure as c


def test_reference_is_t7_original():
    assert c.sha(c.ref_text()).startswith('61c902f1')


def test_reference_applies_and_ports_with_identity_map():
    ref = c.ref_text()
    assert c.applies(ref)
    rn, tn, m = c.name_map(ref, ref)
    assert rn == tn == 'u_rsv_14_'
    for step in ('pmem', 'pvq', 'land', 'stage'):
        src, _ = c.port_source(c.REF[step].read_text(), tn, m, rn)
        assert 'hash lock -> class port' in src
        compile(src, step, 'exec')


def test_unmapped_reference_net_refuses():
    ref = c.ref_text()
    rn, tn, m = c.name_map(ref, ref)
    m = {k: v for k, v in m.items() if 'procmux_69594' not in k}
    with pytest.raises(ValueError, match='unmapped reference net'):
        c.port_source(c.REF['land'].read_text(), tn, m, rn)


def test_head_detects_wrapper_level():
    assert c.rsv('w_u_rsv_05_u_u_u_att_x w_u_rsv_05_u_y') == 'u_rsv_05_u_'
    assert c.rsv('w_u_rsv_01_u_u_att_x') == 'u_rsv_01_'
    with pytest.raises(ValueError):
        c.rsv('w_u_rsv_01_u_u_att_x w_u_rsv_02_u_u_att_x')


def test_not_applicable_without_helpers():
    assert not c.applies('module m; endmodule\n')


def test_fit_v2_rebinds_children_and_is_idempotent():
    import gzip, json
    pk = c.ROOT / "results/rtl/s81_svc_memory_fit_1103"
    v1 = c.ROOT / "results/rtl/s81_svc_memory_closure_1103/closed/s81p_svc_hi_dsdv_svc_rs__t1_bound.sv.gz"
    s1 = gzip.decompress(v1.read_bytes()).decode()
    s2 = c.fit_v2(s1)
    assert c.fit_v2(s2) == s2
    assert s2.count("ot_hdc_v41x_attn_staging_fit #(") == 2 and "ot_t7_land_capture_candidate " not in s2
    rec = json.loads((pk / "closure.json").read_text())["types"]["svc_hi_dsdv_svc_rs__t1"]
    assert c.sha(s2) == rec["after_sha256"] and c.sha(s1) == rec["v1_after_sha256"]
    for name, (p, _) in c.CHILDREN_V2.items():
        assert (c.ROOT / p).exists(), name
    with pytest.raises(ValueError):
        c.fit_v2(s1.replace("ot_t7_pvq_capture_candidate ", "ot_t7_pvq_capture_x "))


def test_idx_fit_renames_svc_lo_reader_and_sizes_masters():
    import gzip
    import s81_svc_idx_fit as idx
    pk = c.ROOT / "results/rtl/s81_svc_memory_fit_1103/closed"
    lo = gzip.decompress((pk / "s81p_svc_lo_dsdv_svc_rs__t1_bound.sv.gz").read_bytes()).decode()
    hi = gzip.decompress((pk / "s81p_svc_hi_dsdv_svc_rs__t1_bound.sv.gz").read_bytes()).decode()
    src = c.ROOT / "physical/die_plan/s81/bind/source_modules/portfix178/dsdv_idx_rg3.sv"
    files = ["/x/rtl/dsdv_idx_rg2.sv", str(src)]
    s2, kids, macros, rep = c.idx_fit(lo, files)
    assert s2.count("dsdv_idx_rg3_fit #(") == 1 and rep["renamed"] == 1 and set(kids) == {"dsdv_idx_fit_mem.sv", "dsdv_idx_rg3_fit.sv"}
    assert c.idx_fit(s2, files)[0] == s2                      # idempotent
    fit = kids["dsdv_idx_rg3_fit.sv"]
    assert "dsdv_idx_rg2_m1k #(" not in fit and fit.count("dsdv_idx_fit_mem #(") == 6 and ".WORDS(MQ_D - MQ_T < 128 ? 128 : 1024), .BITS(MW + 1)) u_mq" in fit and "g_mq_tail" in fit
    assert sum(macros.values()) == 13 and macros == idx.MACROS
    assert c.idx_fit(hi, files)[1:] == ({}, {}, None)         # svc_hi: no reader, untouched
    with pytest.raises(ValueError, match="not a proven source"):
        idx.fit_source(src.read_text().replace("lw_h1[u] <= !sc && bt[0];", "lw_h1[u] <= !sc;"))


def test_idx_fit_chain_end_nq_reader():
    """DIE-S81-66 11-05: svc_lo t7 binds the chain-end reader dsdv_idx_rg3_nq (wrapper, u_rg3 = nq_native)."""
    import s81_svc_idx_fit as idx
    pf = c.ROOT / "physical/die_plan/s81/bind/source_modules/portfix178"
    files = ["/x/rtl/dsdv_idx_rg2.sv", str(pf / "dsdv_idx_rg3_nq.sv"), str(pf / "dsdv_idx_rg3_nq_native.sv")]
    line = ("    dsdv_idx_rg3_nq #(.DQR(24), .EL(124), .IH(0), .IQD(512), .KR(0), .LFD(256), .MUT(0), .SQD(256), "
            ".SRAM_MACRO(1'b1)) u_u_irg_07 (\n")
    s2, kids, macros, rep = c.idx_fit("module b;\n" + line + "    );\nendmodule\n", files)
    assert s2.count("dsdv_idx_rg3_nq_fit #(") == 1 and "dsdv_idx_rg3_nq #(" not in s2
    assert rep["renamed"] == 1 and rep["kind"] == "nq" and sorted(rep["dropped"]) == sorted(files[1:])
    assert set(kids) == {"dsdv_idx_fit_mem.sv", "dsdv_idx_rg3_nq_fit.sv", "dsdv_idx_rg3_nq_native_fit.sv"}
    assert c.idx_fit(s2, files)[0] == s2                      # idempotent
    w, fit = kids["dsdv_idx_rg3_nq_fit.sv"], kids["dsdv_idx_rg3_nq_native_fit.sv"]
    assert "module dsdv_idx_rg3_nq_fit #(" in w and "dsdv_idx_rg3_nq_native_fit #(" in w and ") u_rg3 (" in w
    assert "module dsdv_idx_rg3_nq_native_fit #(" in fit and "infk2_left" in fit and "dsdv_idx_rg2_m1k #(" not in fit
    ref = idx.fit_source((pf / "dsdv_idx_rg3.sv").read_text())
    mems = lambda t: sorted(ln.strip() for ln in t.splitlines() if "dsdv_idx_fit_mem #(" in ln)
    assert len(mems(fit)) == 6 and mems(fit) == mems(ref)     # the same 13 memory swaps as the proven rg3 fit
    assert sum(macros.values()) == 13
    with pytest.raises(ValueError, match="not a proven source"):
        idx.fit_source((pf / "dsdv_idx_rg3_nq_native.sv").read_text() + "\n", nq=True)
    with pytest.raises(ValueError, match="not a proven source"):
        idx.fit_source((pf / "dsdv_idx_rg3.sv").read_text(), nq=True)
    with pytest.raises(ValueError, match="instances"):
        c.idx_fit("module b;\n" + line + line.replace("u_u_irg_07", "u_u_irg_08") + "endmodule\n", files)


def test_idx_fit_el140_pin_stages_keep_128x23_ring_plus_tail():
    """S81-SVCRS-3 11-11 / S81-CORES-R 11-16 (COORD): with the IRG pin stages (.EL(140), .PR(1)) the metadata ring is read
    139 edges behind: u_mq keeps the 128x23 macro read 127 behind plus a 12-stage FF tail (MQ_T = MQ_D - 127), never
    the 1024x256 master; any other EL / PR pair is refused."""
    import s81_svc_idx_fit as idx
    pf = c.ROOT / "physical/die_plan/s81/bind/source_modules/portfix178"
    for kind, mod, files in (("rg3", "dsdv_idx_rg3", ["/x/rtl/dsdv_idx_rg2.sv", str(pf / "dsdv_idx_rg3.sv")]),
                             ("nq", "dsdv_idx_rg3_nq", ["/x/rtl/dsdv_idx_rg2.sv", str(pf / "dsdv_idx_rg3_nq.sv"),
                                                        str(pf / "dsdv_idx_rg3_nq_native.sv")])):
        line = ("    %s #(.DQR(24), .EL(140), .IH(0), .IQD(512), .KR(0), .LFD(256), .MUT(0), .PR(1), .SQD(256), "
                ".SRAM_MACRO(1'b1)) u_u_irg_07 (\n" % mod)
        s2, kids, macros, rep = c.idx_fit("module b;\n" + line + "    );\nendmodule\n", files)
        assert rep["kind"] == kind and rep["renamed"] == 1 and macros == idx.MACROS_EL140
        assert macros == idx.MACROS and "ot_sram_1r1w_1024x256_m2_r2c2" not in macros and sum(macros.values()) == 13
        with pytest.raises(ValueError, match="EL 140 with PR 0"):
            c.idx_fit("module b;\n" + line.replace(".PR(1), ", "") + "    );\nendmodule\n", files)
    fit = idx.fit_source((pf / "dsdv_idx_rg3.sv").read_text())
    assert ".WORDS(MQ_D - MQ_T < 128 ? 128 : 1024), .BITS(MW + 1)) u_mq" in fit and ".ra(mw - 10'(MQ_D - MQ_T)), .rd(mq_qm)," in fit
    assert "localparam integer MQ_T = MQ_D < 128 ? 0 : MQ_D - 127;" in fit and fit.count("g_mq_tail") == 1
    assert "g_mq_depth_bad" in fit and "endmodule" in fit[fit.index("g_mq_tail"):]
    mem = (c.ROOT / idx.FIT_MEM).read_text()
    assert "SRAM_MACRO && BITS == 23 && WORDS != 128" in mem and "g_no_wide23" in mem


def test_rebase_source_renames_tokens_and_refuses_unknown():
    rm = dict(hash={'a' * 20: 'b' * 20}, att={'719': '720', '558': '559'}, eng={'111': '112'}, procmux={'69496': '69497'})
    src = "P+'719_Y[0]' E+'111_Y' 'src_%s_Y' procmux_69496 ['558'] 0_Y" % ('a' * 20)
    assert c.rebase_source(src, rm) == "P+'720_Y[0]' E+'112_Y' 'src_%s_Y' procmux_69497 ['559'] 0_Y" % ('b' * 20)
    with pytest.raises(ValueError, match='not in the regenerated map'):
        c.rebase_source("P+'733_Y'", rm)


def _kit_rtl_main(monkeypatch, tmp_path, **kw):
    import json
    bm = 's81p_svc_hi_dsdv_svc_rs__t1_bound'
    (tmp_path / 'kit_rtl.json').write_text(json.dumps(dict(bound_module=bm, files=[])))
    (tmp_path / (bm + '.sv')).write_text('module ' + bm + ';\n' +
        '\n'.join('    %s u%d();' % (name, i) for i, name in enumerate(c.NATIVE)) + '\nendmodule\n')
    called = []
    monkeypatch.setattr(c, 'apply_kit', lambda *a, **k: called.append('apply_kit') or dict(status='APPLIED'))
    for k, v in kw.items(): monkeypatch.setattr(c, k, v)
    monkeypatch.setattr(c.sys, 'argv', ['closure', '--kit-rtl', str(tmp_path)])
    return called


def test_kit_rtl_inputs_all_present_in_the_tree():
    assert [p for p in c.closure_inputs('v2') if not p.exists()] == []
    assert [p for p in c.closure_inputs('v1') if not p.exists()] == []


def test_kit_rtl_proceeds_when_inputs_present(monkeypatch, tmp_path):
    called = _kit_rtl_main(monkeypatch, tmp_path, ref_text=lambda p=None: 'ref', cur_ref=lambda b=None: ('cur', {}))
    c.main()
    assert called == ['apply_kit']


@pytest.mark.parametrize('name', ['CUR_REF', 'transform', 'child', 'idx'])
def test_kit_rtl_missing_input_fails_and_names_it_without_fallback(monkeypatch, tmp_path, name):
    def no_fallback(*a, **k): raise AssertionError('reference was read: fallback to 61c902f1')
    gone = tmp_path / 'absent'
    kw = dict(ref_text=no_fallback, cur_ref=no_fallback)
    if name == 'CUR_REF':
        kw['CUR_REF'] = gone; want = str(gone / 'ref_map.json')
    elif name == 'transform':
        kw['REF'] = {**c.REF, 'land': gone / 'transform.py'}; want = str(gone / 'transform.py')
    elif name == 'child':
        kw['CHILDREN_V2'] = {**c.CHILDREN_V2, 'x.sv': (str(gone / 'x.sv'), None)}; want = str(gone / 'x.sv')
    else:
        monkeypatch.setattr(c.IDX, 'FIT_MEM', str(gone / 'fit_mem.sv')); want = str(gone / 'fit_mem.sv')
    called = _kit_rtl_main(monkeypatch, tmp_path, **kw)
    with pytest.raises(SystemExit) as e:
        c.main()
    assert str(e.value).startswith('closure inputs missing: ') and want in str(e.value)
    assert called == []

def test_kit_rtl_no_helpers_needs_no_reference_assets(monkeypatch, tmp_path, capsys):
    import json
    bm = 's81p_svc_hi_dsdv_svc_rs__t1_bound'
    (tmp_path / 'kit_rtl.json').write_text(json.dumps(dict(bound_module=bm, files=[])))
    bound = tmp_path / (bm + '.sv')
    text = 'module ' + bm + '; endmodule\n'
    bound.write_text(text)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    def forbidden(*a, **k): raise AssertionError('no-op tried to load transform/reference assets')
    monkeypatch.setattr(c, 'closure_inputs', forbidden)
    monkeypatch.setattr(c, 'ref_text', forbidden)
    monkeypatch.setattr(c, 'cur_ref', forbidden)
    monkeypatch.setattr(c.sys, 'argv', ['closure', '--kit-rtl', str(tmp_path)])
    c.main()
    assert 'NOT_APPLICABLE' in capsys.readouterr().out
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


def test_cur_ref_selects_reference_by_stage_digest(monkeypatch, tmp_path):
    """FABLE-FIX-S81-SVC2 11-17: one reference per bind; the bound's staged-file digest picks it, CUR_REF otherwise."""
    import gzip, json
    def mk(name, digest):
        d = tmp_path / name; d.mkdir()
        s = 'x  // structural_full/%s_dsdv_svc_att.sv:1.1-1.2\n' % digest
        (d / 'ref_t7_bound.sv.gz').write_bytes(gzip.compress(s.encode()))
        (d / 'ref_map.json').write_text(json.dumps(dict(reference=c.sha(s), map=dict(tag=name))))
        return d
    cur = mk('ref_a_main', 'a' * 12); mk('ref_b_main', 'b' * 12); (tmp_path / 'ref_old_src').mkdir()
    monkeypatch.setattr(c, 'CUR_REF', cur); monkeypatch.setattr(c, 'REF_ROOT', tmp_path)
    bound = lambda g: 'y  // structural_full/%s_dsdv_svc_att.sv:9.1-9.2\n' % g
    assert c.cur_ref(bound('b' * 12))[1] == dict(tag='ref_b_main')
    assert c.cur_ref(bound('a' * 12))[1] == dict(tag='ref_a_main')
    assert c.cur_ref(bound('c' * 12))[1] == dict(tag='ref_a_main')      # unknown digest: CUR_REF as before
    assert c.cur_ref()[1] == dict(tag='ref_a_main')


def test_cur_ref_finds_reference_shipped_with_tools(monkeypatch, tmp_path):
    """S81-KITRTL-NETMAP-1118: a die tree cut before a bind's reference was regenerated has no results/ref_<bind>; the tools carry it."""
    import gzip, json
    def mk(root, name, digest):
        d = root / name; d.mkdir(parents=True)
        s = 'x  // structural_full/%s_dsdv_svc_att.sv:1.1-1.2\n' % digest
        (d / 'ref_t7_bound.sv.gz').write_bytes(gzip.compress(s.encode()))
        (d / 'ref_map.json').write_text(json.dumps(dict(reference=c.sha(s), map=dict(tag=name))))
        return d
    res = tmp_path / 'results'; tools = tmp_path / 'refs'
    cur = mk(res, 'ref_a_main', 'a' * 12); mk(tools, 'ref_b_main', 'b' * 12)
    monkeypatch.setattr(c, 'CUR_REF', cur); monkeypatch.setattr(c, 'REF_ROOT', res); monkeypatch.setattr(c, 'TOOL_REFS', tools)
    bound = lambda g: 'y  // structural_full/%s_dsdv_svc_att.sv:9.1-9.2\n' % g
    assert c.cur_ref(bound('b' * 12))[1] == dict(tag='ref_b_main')
    assert c.cur_ref(bound('a' * 12))[1] == dict(tag='ref_a_main')
