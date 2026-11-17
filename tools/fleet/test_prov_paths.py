import json, os, tempfile, unittest
import prov_paths as P
import build_protected_live as B

R = "/srv/opentallas-scratch2/claude/"


class Prov(unittest.TestCase):
    def tree(self):
        t = tempfile.mkdtemp() + "/src_x"; os.makedirs(t + "/physical/views/a"); os.makedirs(t + "/physical/views/b")
        json.dump({"routed_db": R + "count-archive-2/s81views/x/6_final.odb", "kit": {"own": t + "/inside"}}, open(t + "/physical/views/a/provenance.json", "w"))
        json.dump({"src": R + "kw45/src_other/a/b/c.json"}, open(t + "/physical/views/b/provenance.json", "w"))
        open(t + "/physical/views/b/other.json", "w").write(R + "not/a/prov/file/x")
        return t

    def test_scan_names_every_provenance_path_but_not_the_tree_itself_or_other_files(self):
        got = P.scan_tree(self.tree())
        self.assertEqual(sorted(got), [R + "count-archive-2/s81views/x/6_final.odb", R + "kw45/src_other/a/b/c.json"])

    def test_audit_lists_what_is_missing_everywhere_per_die(self):
        cfg = {"dies": {"s81": {"src": "/srv/x/kw45/t1", "rollback_tree": "/srv/x/kw45/t0", "gen_hosts": ["h1", "h2"]}}}
        def scanner(h, t):
            base = {R + "a/b/c/d": {"by": ["p"], "exists": h == "h1"}, R + "gone/b/c/d/e": {"by": ["p"], "exists": False}}
            return base
        a = P.audit(cfg, scanner)
        self.assertEqual(P.missing(a), [R + "gone/b/c/d/e"])
        self.assertEqual(a["paths"][R + "a/b/c/d"]["exists_on"].count("h1"), 2); self.assertIn("h2", a["paths"][R + "a/b/c/d"]["missing_on"])
        self.assertEqual(len(P.targets(cfg)), 4)                      # src + rollback x 2 hosts

    def test_builder_protects_the_cached_provenance_paths(self):
        c = tempfile.mkdtemp(); json.dump({"paths": {R + "count-archive-2/s81views/x/6_final.odb": {"dies": ["s81"], "exists_on": ["h"], "missing_on": []}}}, open(c + "/prov.json", "w"))
        out = set(); B.prov_cache_paths(c + "/prov.json", out, os.path.normpath)
        self.assertEqual(out, {R + "count-archive-2/s81views/x/6_final.odb"})
        out = set(); B.prov_cache_paths(c + "/nope.json", out, os.path.normpath); self.assertEqual(out, set())
