#!/usr/bin/env python3
import gzip, json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import signed_store as ss


def entry(eid, aliases, key="k", pins=None):
    return dict(schema=ss.SCHEMA, id=eid, origin=aliases[0], rows=[dict(die="d", kind="type", key=key)], scan=dict(name="n", top="t", generated="g", pins_path="/p"),
                aliases=aliases, archive="/archive/x", files=[["srv/a/6_final.v", 1, "aa"], ["srv/a/6_final.spef", 2, "bb"], ["srv/a/x.lef", 3, "cc"]], netlist_sha="aa", pins=pins)


def test_write_is_immutable_and_load_expands_aliases():
    with tempfile.TemporaryDirectory() as d:
        e = entry("ab" * 32, ["h1:/x/signoff.json", "h2:/y/signoff.json"], pins={"rows": []})
        assert ss.write_entry(e, d)
        assert not ss.write_entry(dict(e, verdict="changed"), d)
        assert ss.read_manifest(d)[0].get("verdict") is None
        recs, pins = ss.load_records(d)
        assert sorted(r["scan_host"] for r in recs) == ["h1", "h2"]
        assert ("h1", "/p") in pins and all(r["netlist_sha"] == "aa" for r in recs)


def test_removed_row_is_gone():
    with tempfile.TemporaryDirectory() as d:
        a, b = "aa" * 32, "bb" * 32
        ss.write_entry(entry(a, ["h:/a"], "ka"), d); ss.write_entry(entry(b, ["h:/b"], "kb"), d)
        os.remove(ss.entry_path(a, d))
        assert [e["id"] for e in ss.read_manifest(d)] == [b]


def test_classes_filter():
    e = entry("cc" * 32, ["h:/a"])
    assert [f[0] for f in ss.entry_files(e, ["lef"])] == ["srv/a/x.lef"]
    assert len(ss.entry_files(e)) == 3


def test_netlist_of_prefers_routed_db_dir():
    shas = {"/r/base/6_final.v": [1, "n1"], "/k/run/results/a/b/base/6_final.v": [1, "n2"]}
    assert ss.netlist_of(dict(path="/k/signoff/signoff.json", routed_db="/r/base/6_final.odb"), shas) == "n1"
    assert ss.netlist_of(dict(path="/k/signoff/signoff.json"), shas) == "n2"


def test_do_not_count_marker():
    import release_tree_plan as rtp
    a = dict(scan_host="h1", path="/k/so/signoff/signoff.json", name="n", top="t", generated="g1")
    a2 = dict(a, scan_host="h2", path="/copy/signoff/signoff.json")
    b = dict(scan_host="h1", path="/other/signoff/signoff.json", name="n", top="t", generated="g2")
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "dnc.tsv")
        for state, want in (("HOLD", ["g2"]), ("PENDING", ["g1", "g1", "g2"]), ("CLEARED", ["g1", "g1", "g2"])):
            open(f, "w").write("# c\nh1:/k/so\t%s\tno main RTL\t2026-11-09\n" % state)
            kept, held = rtp.split_dnc([a, a2, b], rtp.dnc_rows(f))
            assert [r["generated"] for r in kept] == want, (state, kept)
            assert len(held) == (2 if state == "HOLD" else 0)
        kept, held = rtp.split_dnc([a, b], rtp.dnc_rows(os.path.join(d, "absent.tsv")))
        assert len(kept) == 2 and not held
        # a marker on a directory that is only a name prefix of the record's directory does not match
        open(f, "w").write("h1:/k/s\tHOLD\tx\td\n")
        assert len(rtp.split_dnc([a], rtp.dnc_rows(f))[0]) == 1


def test_late_provenance_once_and_only_without_one():
    import hashlib
    with tempfile.TemporaryDirectory() as d:
        so = '{"verdict": "SIGNED"}'
        eid = hashlib.sha256(so.encode()).hexdigest()
        e = entry(eid, ["h1:/k/r/signoff/signoff.json"])
        e["scan"] = dict(name="n", top="t", generated="g", pins_path="/p")
        assert ss.write_entry(e, d)
        scan = dict(name="n", top="t", generated="g", flow_tag="flow-x", src_commit="abc", prov_file="/k/r/PROVENANCE.json", resign=True)
        assert not ss.late_provenance(eid, dict(scan, prov_file=None), {"kind": "resign"}, "/archive/h1", [], d)   # fresh scan has none
        assert ss.late_provenance(eid, scan, {"kind": "resign"}, "/archive/h1", [["k/r/PROVENANCE.json", 10, "pp"]], d)
        assert not ss.late_provenance(eid, dict(scan, flow_tag="flow-y"), {"kind": "resign"}, "/archive/h1", [], d)   # never replaced
        recs, _ = ss.load_records(d)
        assert recs[0]["flow_tag"] == "flow-x" and recs[0]["versioned"]
        e2 = ss.read_manifest(d)[0]
        assert e2["id"] == eid and e2["flow_tag"] == "flow-x"
        assert ["k/r/PROVENANCE.json", 10, "pp", "/archive/h1"] in ss.entry_files(e2)


def test_late_pass_refuses_changed_unit():
    try:
        import signed_store_ingest as si
    except ImportError:
        print("SKIP test_late_pass_refuses_changed_unit: signed_store_ingest not beside this file"); return
    import hashlib
    so = '{"verdict": "SIGNED"}'
    eid = hashlib.sha256(so.encode()).hexdigest()
    e = dict(id=eid, origin="h1:/k/r/signoff/signoff.json", name="n", top="t", generated="g", scan=dict(name="n"),
             files=[["k/r/signoff/signoff.json", 5, "s1"], ["k/r/x.v", 7, "s2"]])
    r = dict(scan_host="h1", path="/k/r/signoff/signoff.json", name="n", top="t", generated="g", prov_file="/k/r/PROVENANCE.json", flow_tag="flow-x")
    assert si.select_late([r], [e]) == [(e, r)]
    assert si.select_late([dict(r, flow_tag=None)], [e]) == []
    assert si.select_late([r], [dict(e, provenance_json="x")]) == []
    unit = dict(files=[["/k/r/signoff/signoff.json", 5], ["/k/r/x.v", 7], ["/k/r/PROVENANCE.json", 3]])
    calls = []
    orig = si.ss.late_provenance
    si.ss.late_provenance = lambda *a, **k: calls.append(a) or True
    try:
        coll = lambda h, p: dict(signoff=so, prov='{"kind": "resign"}')
        good = {"/k/r/signoff/signoff.json": [5, "s1"], "/k/r/x.v": [7, "s2"], "/k/r/PROVENANCE.json": [3, "pp"]}
        fails = []
        assert si.late_pass([(e, r)], fails, archive=lambda h, c, f: (good, {r["path"]: unit}), collect=coll) == [eid] and not fails
        assert calls[0][4] == [["k/r/PROVENANCE.json", 3, "pp"]]
        bad = dict(good, **{"/k/r/x.v": [7, "CHANGED"]}); fails = []
        assert si.late_pass([(e, r)], fails, archive=lambda h, c, f: (bad, {r["path"]: unit}), collect=coll) == [] and "changed" in fails[0][2]
        e3 = dict(e, files=e["files"] + [["k/r/lec.log", 0, "s0"]]); unit3 = dict(files=unit["files"] + [["/k/r/lec.log", 9]])
        g3 = dict(good); fails = []; calls.clear()   # archive keeps the first lec.log, so it is not in good
        assert si.late_pass([(e3, r)], fails, archive=lambda h, c, f: (g3, {r["path"]: unit3}), collect=coll) == [eid] and not fails
        assert calls and True
        fails = []
        assert si.late_pass([(e, r)], fails, archive=lambda h, c, f: (good, {r["path"]: unit}), collect=lambda h, p: dict(signoff=so + " ", prov="{}")) == []
        assert "signoff.json changed" in fails[0][2]
    finally:
        si.ss.late_provenance = orig

if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v(); print("ok", k)
