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


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v(); print("ok", k)
