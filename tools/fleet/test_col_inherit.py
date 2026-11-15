import hashlib, json, pathlib, shutil, subprocess, sys
import pytest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import col_inherit as C
import release_tree_plan as R


def hc(repo, mod="ot_rom_4096x72_m8", lef="m/x.lef", lib="m/x.lib"):
    (repo / "m").mkdir(exist_ok=True)
    (repo / lef).write_text("LEF " + mod); (repo / lib).write_text("LIB " + mod)
    return dict(inst="u_rom", module=mod, lef=lef, lib=lib, origin_um=[1, 2], orient="R0")


def ptype(repo, pv, inst, clock="X", extra=None):
    t = dict(outline_um=[10, 20], buses=[{"name": "a"}], ft_slots=[], internal_stations=[], reset={}, hard=False,
             contents=[{"inst": "u", "module": "m"}], sources=["a.sv"], hard_cores=[hc(repo)],
             clock={"landing_contract": {"collector_tree": {"type": "col_h9_r1__t1__cl11111111__pv" + pv}, "k": clock}},
             param_set={"P_u_c0_INSTANCE": '"%s"' % inst})
    t.update(extra or {})
    return t


def plan(repo, n=3, **kw):
    pt = {"col_h9_r1__t1__cl11111111__pv%06x" % i: ptype(repo, "%06x" % i, "inst%d" % i, **kw) for i in range(n)}
    pt["col_h9_r1__t1__cl22222222"] = dict(ptype(repo, "000000", "z"), param_set={})
    return {"partition_types": pt}


def rom_dir(tmp, n=3, skip=()):
    d = tmp / "rom"; d.mkdir(exist_ok=True)
    for i in range(n):
        if i in skip: continue
        (d / ("inst%d_0.viamap.hex" % i)).write_text("0%d\n" % i); (d / ("inst%d_1.viamap.hex" % i)).write_text("1%d\n" % i)
    (d / "inst10_0.viamap.hex").write_text("decoy")
    return d


def signoff(tmp, drc=0, tt=10.0, ff=5.0, name="signoff.json"):
    p = tmp / name
    p.write_text(json.dumps(dict(die="s81", verdict="SIGNED", checks=dict(drc=dict(count=drc), setup_tt=dict(wns_ps=tt), hold_ff=dict(wns_ps=ff, verdict="PASS")))))
    return p


def rec_for(tmp, pl, sib, sg=None, **kw):
    repo = tmp / "repo"
    return C.build_record(pl, "col_h9_r1__t1__cl11111111__pv000000", sib, sg or signoff(tmp), str(repo), str(rom_dir(tmp)),
                          kw.pop("lec", dict(verdict="EQUIVALENT")), kw.pop("via", dict(verdict="PASS")), **kw)


@pytest.fixture
def env(tmp_path):
    (tmp_path / "repo").mkdir()
    return tmp_path, plan(tmp_path / "repo")


def test_groups_layout_and_singleton(env):
    tmp, pl = env
    g = C.groups(pl)[("col_h9_r1", "cl11111111")]
    assert g["verdict"] == "OK" and len(g["members"]) == 3
    assert C.groups(pl)[("col_h9_r1", "cl22222222")]["singletons"] == ["col_h9_r1__t1__cl22222222"]


def test_group_excluded_on_hard_core_or_geometry_or_clock_difference(tmp_path):
    (tmp_path / "repo").mkdir()
    pl = plan(tmp_path / "repo")
    k = "col_h9_r1__t1__cl11111111__pv000001"
    pl["partition_types"][k]["hard_cores"][0]["origin_um"] = [9, 9]
    assert "hard-core signature" in " ".join(C.groups(pl)[("col_h9_r1", "cl11111111")]["reasons"])
    pl = plan(tmp_path / "repo"); pl["partition_types"][k]["buses"] = [{"name": "b"}]
    assert "geometry" in " ".join(C.groups(pl)[("col_h9_r1", "cl11111111")]["reasons"])
    pl = plan(tmp_path / "repo"); pl["partition_types"][k]["clock"]["landing_contract"]["k"] = "Y"
    assert "clock key" in " ".join(C.groups(pl)[("col_h9_r1", "cl11111111")]["reasons"])


def test_pv_label_in_clock_is_ignored(env):
    tmp, pl = env
    assert len({C.clock_key(t) for n, t in pl["partition_types"].items() if "pv" in n}) == 1


def test_non_image_param_difference_excludes_group(tmp_path):
    (tmp_path / "repo").mkdir()
    pl = plan(tmp_path / "repo")
    for i, t in enumerate(pl["partition_types"].values()):
        if t["param_set"]:
            t["param_set"]["P_logic"] = str(i)
    assert C.groups(pl)[("col_h9_r1", "cl11111111")]["verdict"] == "EXCLUDED"


def test_rom_images_include_inner_roms_and_skip_decoys(env):
    tmp, pl = env
    im = C.rom_images(pl["partition_types"]["col_h9_r1__t1__cl11111111__pv000001"], str(rom_dir(tmp)))
    assert [f["name"] for f in im[0]["files"]] == ["inst1_0.viamap.hex", "inst1_1.viamap.hex"]
    assert all(f["sha256"] for f in im[0]["files"])
    im1 = C.rom_images(pl["partition_types"]["col_h9_r1__t1__cl11111111__pv000001"], str(rom_dir(tmp)))
    assert "inst10" not in json.dumps(im1)


def test_record_credit_ok(env):
    tmp, pl = env
    r = rec_for(tmp, pl, "col_h9_r1__t1__cl11111111__pv000001")
    assert r["credit"] and r["credit_blockers"] == [] and r["schema"] == C.SCHEMA
    assert r["differing_params"] == ["P_u_c0_INSTANCE"] and r["macro_views"][0]["lef_equal"] and r["macro_views"][0]["lib_equal"]
    assert r["param_set_sha"] != r["representative_param_set_sha"]


@pytest.mark.parametrize("kw", [dict(drc=3), dict(tt=-43.0), dict(ff=-1.0)])
def test_gates_block_credit(env, kw):
    tmp, pl = env
    r = rec_for(tmp, pl, "col_h9_r1__t1__cl11111111__pv000001", sg=signoff(tmp, **kw))
    assert not r["credit"] and "gates" in r["credit_blockers"][0]


def test_setup_at_minus_42_passes(env):
    tmp, pl = env
    assert rec_for(tmp, pl, "col_h9_r1__t1__cl11111111__pv000001", sg=signoff(tmp, tt=-42.0))["credit"]


def test_lef_or_lib_difference_blocks(env):
    tmp, pl = env
    t = pl["partition_types"]["col_h9_r1__t1__cl11111111__pv000001"]
    (tmp / "repo" / "m" / "y.lib").write_text("OTHER"); t["hard_cores"][0]["lib"] = "m/y.lib"
    r = rec_for(tmp, pl, "col_h9_r1__t1__cl11111111__pv000001")
    assert not r["credit"] and any("LEF/lib" in b or "signature" in b for b in r["credit_blockers"])


def test_missing_image_blocks(env):
    tmp, pl = env
    d = rom_dir(tmp, skip=(2,))
    r = C.build_record(pl, "col_h9_r1__t1__cl11111111__pv000000", "col_h9_r1__t1__cl11111111__pv000002", signoff(tmp), str(tmp / "repo"),
                       str(d), dict(verdict="EQUIVALENT"), dict(verdict="PASS"))
    assert not r["credit"] and any("no viamap image" in b for b in r["credit_blockers"])


def test_lec_and_via_policies(env):
    tmp, pl = env
    s = "col_h9_r1__t1__cl11111111__pv000001"
    assert not rec_for(tmp, pl, s, lec=dict(verdict="NOT_RUN"))["credit"]                           # require is the default
    assert rec_for(tmp, pl, s, lec=dict(verdict="UNPROVEN"), lec_policy="advisory")["credit"]
    assert not rec_for(tmp, pl, s, lec=dict(verdict="NOT_EQUIVALENT"), lec_policy="advisory")["credit"]
    assert rec_for(tmp, pl, s, via=dict(verdict="NOT_RUN"))["credit"]                               # via advisory by default (no GDS in repo)
    assert not rec_for(tmp, pl, s, via=dict(verdict="NOT_RUN"), via_policy="require")["credit"]
    assert not rec_for(tmp, pl, s, via=dict(verdict="FAIL"))["credit"]


def test_other_layout_is_not_a_sibling(env):
    tmp, pl = env
    r = rec_for(tmp, pl, "col_h9_r1__t1__cl22222222")
    assert not r["credit"]


def test_write_record_is_append_only(env):
    tmp, pl = env
    r = rec_for(tmp, pl, "col_h9_r1__t1__cl11111111__pv000001")
    f = C.write_record(r, tmp / "out")
    with pytest.raises(FileExistsError):
        C.write_record(r, tmp / "out")
    assert json.loads(f.read_text())["sibling"] == r["sibling"]


def test_archive_dry_run_and_local_copy_append_only(env):
    tmp, pl = env
    r = rec_for(tmp, pl, "col_h9_r1__t1__cl11111111__pv000001")
    f = C.write_record(r, tmp / "out")
    rows = C.archive([f], str(tmp / "rtx"), "/archive/opentallas-signed-1114", dry=True)
    cols = rows[0].split("\t")
    assert len(cols) == 12 and cols[0] == "s81" and cols[1] == r["sibling"] and cols[10] == "ARCHIVED-BOTH" and cols[7] == hashlib.sha256(f.read_bytes()).hexdigest()
    assert not (tmp / "rtx").exists()
    (tmp / "rtx").mkdir(); (tmp / "rtx" / "INDEX.tsv").write_text("die\telement\n")
    C.archive([f], str(tmp / "rtx"), "/archive/x")
    assert (tmp / "rtx" / "s81" / r["sibling"] / "inherited.json").exists()
    assert (tmp / "rtx" / "INDEX.tsv").read_text().count("\n") == 2
    with pytest.raises(FileExistsError):
        C.archive([f], str(tmp / "rtx"), "/archive/x")


# ---- counter
def mk_row(tmp, rec, rep_ok=True):
    r = rec_for(tmp, rec[0], rec[1])
    f = C.write_record(r, tmp / "rec")
    return dict(die="s81", member=r["sibling"], rep=r["representative"], record=str(f), sha=hashlib.sha256(f.read_bytes()).hexdigest())


def test_counter_credits_sibling_when_rep_counts(env):
    tmp, pl = env
    row = mk_row(tmp, (pl, "col_h9_r1__t1__cl11111111__pv000001"))
    st = {row["rep"]: ["epyc7:/x/signoff.json SIGNED"]}
    tm = {row["rep"]: "m", row["member"]: "m"}
    assert R.inherit_credit("s81", st, tm, [row]) == [row["member"]]
    assert "via inherit " + row["rep"] in st[row["member"]][0]


def test_counter_requires_rep_counted_record_ok_and_no_override(env):
    tmp, pl = env
    row = mk_row(tmp, (pl, "col_h9_r1__t1__cl11111111__pv000001"))
    tm = {row["rep"]: "m", row["member"]: "m"}
    assert R.inherit_credit("s81", {}, tm, [row]) == []                                    # representative not counted
    st = {row["rep"]: ["ref"]}
    assert R.inherit_credit("s81", st, tm, [dict(row, sha="0" * 64)]) == []                # sha mismatch
    assert R.inherit_credit("s81", st, tm, [dict(row, member="other")]) == []             # not in plan
    assert R.inherit_credit("s81", st, {row["rep"]: "m"}, [row]) == []
    assert R.inherit_credit("qwen_kvsys", st, tm, [row]) == []
    st2 = {row["rep"]: ["ref"], row["member"]: ["own"]}
    assert R.inherit_credit("s81", st2, tm, [row]) == [] and st2[row["member"]] == ["own"]


def test_counter_rejects_non_credit_record(env):
    tmp, pl = env
    r = rec_for(tmp, pl, "col_h9_r1__t1__cl11111111__pv001", lec=dict(verdict="NOT_EQUIVALENT")) if False else rec_for(tmp, pl, "col_h9_r1__t1__cl11111111__pv000001", lec=dict(verdict="NOT_EQUIVALENT"))
    f = C.write_record(r, tmp / "rec")
    row = dict(die="s81", member=r["sibling"], rep=r["representative"], record=str(f), sha="")
    ok, why = R.inherit_record_ok(row)
    assert not ok and "credit" in why
    assert R.inherit_credit("s81", {r["representative"]: ["x"]}, {r["representative"]: "m", r["sibling"]: "m"}, [row]) == []


def test_inherit_rows_parse(tmp_path):
    f = tmp_path / "inherit_members.tsv"
    f.write_text("die\tmember\trep\trecord\tsha\n# c\ns81\tm\to\t/r.json\tabc\n")
    assert R.inherit_rows(f) == [dict(die="s81", member="m", rep="o", record="/r.json", sha="abc")]


# ---- LEC
def test_rewrite_instances():
    t, n = C.rewrite_instances('rom #(.INSTANCE("a.b")) u(); x("a.bc")', {"P_u_INSTANCE": '"a.b"'}, {"P_u_INSTANCE": '"c.d"'})
    assert n == 1 and '"c.d"' in t and '"a.bc"' in t


@pytest.mark.skipif(shutil.which("yosys") is None, reason="yosys not installed")
def test_yosys_lec_equivalent_and_mutant(tmp_path):
    bb = tmp_path / "rom_bb.v"
    bb.write_text('(* blackbox *) module rom #(parameter INSTANCE = "") (input clk, input [1:0] a, output [1:0] q); endmodule\n')
    rtl = tmp_path / "sib.v"
    rtl.write_text('module sibtop #(parameter P_u_INSTANCE = "x") (input clk, input [1:0] d, output reg [1:0] q);\n'
                   '  wire [1:0] rq; rom #(.INSTANCE(P_u_INSTANCE)) u (.clk(clk), .a(d), .q(rq));\n  always @(posedge clk) q <= d ^ rq;\nendmodule\n')
    net = 'module reptop (input clk, input [1:0] d, output reg [1:0] q);\n  wire [1:0] rq; rom #(.INSTANCE("rep.u")) u (.clk(clk), .a(d), .q(rq));\n  always @(posedge clk) q <= d %s rq;\nendmodule\n'
    good, bad = tmp_path / "good.v", tmp_path / "bad.v"
    new, n = C.rewrite_instances(net % "^", {"P_u_INSTANCE": '"rep.u"'}, {"P_u_INSTANCE": '"sib.u"'})
    assert n == 1
    good.write_text(new); bad.write_text(C.rewrite_instances(net % "&", {"P_u_INSTANCE": '"rep.u"'}, {"P_u_INSTANCE": '"sib.u"'})[0])
    sp = {"P_u_INSTANCE": '"sib.u"'}
    st = tmp_path / "standin.v"; st.write_text(C.standin_verilog(bb.read_text()))
    assert "module rom" in st.read_text() and "assign q" in st.read_text()
    r1 = C.run_lec(C.lec_script([str(rtl)], str(good), "sibtop", "reptop", [str(st)], sp), str(tmp_path / "w1"))
    r2 = C.run_lec(C.lec_script([str(rtl)], str(bad), "sibtop", "reptop", [str(st)], sp), str(tmp_path / "w2"))
    assert r1["verdict"] == "EQUIVALENT", r1
    assert r2["verdict"] in ("NOT_EQUIVALENT", "UNPROVEN"), r2
