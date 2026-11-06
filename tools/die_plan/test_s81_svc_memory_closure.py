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
    assert "dsdv_idx_rg2_m1k #(" not in fit and fit.count("dsdv_idx_fit_mem #(") == 6 and ".WORDS(128), .BITS(MW + 1)) u_mq" in fit
    assert sum(macros.values()) == 13
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


def test_rebase_source_renames_tokens_and_refuses_unknown():
    rm = dict(hash={'a' * 20: 'b' * 20}, att={'719': '720', '558': '559'}, eng={'111': '112'}, procmux={'69496': '69497'})
    src = "P+'719_Y[0]' E+'111_Y' 'src_%s_Y' procmux_69496 ['558'] 0_Y" % ('a' * 20)
    assert c.rebase_source(src, rm) == "P+'720_Y[0]' E+'112_Y' 'src_%s_Y' procmux_69497 ['559'] 0_Y" % ('b' * 20)
    with pytest.raises(ValueError, match='not in the regenerated map'):
        c.rebase_source("P+'733_Y'", rm)
