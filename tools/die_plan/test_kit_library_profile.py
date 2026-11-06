import copy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import kit_library_profile as L
import bind

class LibraryProfileTest(unittest.TestCase):
    def fixture(self,r):
        old=r/"old.sv";new=r/"new.sv"
        old.write_text("module leaf(input a,output y); assign y=a; endmodule\n")
        new.write_text("module leaf(input a,output y); helper u_h(.a(a),.y(y)); endmodule\n"
                       "module helper(input a,output y); assign y=a; endmodule\n")
        row=dict(original=str(old),replacement=str(new),
            original_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),
            replacement_sha256=hashlib.sha256(new.read_bytes()).hexdigest(),
            original_modules=["leaf"],replacement_modules=["leaf","helper"])
        doc=dict(schema=L.SCHEMA,type="t",replacements=[row],defines=["CANDIDATE"],
                 proof="actual source proof",model={"cycles":4},bound_body_policy=L.POLICY)
        p=r/"profile.json";p.write_text(json.dumps(doc))
        return p,doc,{"leaf":[str(old)]},[str(old)]

    def test_real_closure_selects_new_source_and_added_helper(self):
        with TemporaryDirectory() as d:
            r=Path(d);p,doc,idx,pref=self.fixture(r);before=copy.deepcopy(idx)
            out,preferred,rec=L.apply(p,"t",idx,pref,["ORIGINAL"],r)
            self.assertEqual(idx,before)
            self.assertEqual(rec["defines"],["ORIGINAL","CANDIDATE"])
            picks={}
            files,missing,macros=bind.kit_closure(["leaf"],out,preferred,picks,views={},wide={},widened={},defines=rec["defines"])
            self.assertFalse(missing)
            self.assertEqual({str(Path(f).resolve()) for f in files},{str(r/"new.sv")})
            self.assertEqual(out["helper"],[str(r/"new.sv")])
            self.assertTrue(rec["captured_bind_unchanged"])

    def test_wrong_hash_or_module_inventory_is_rejected(self):
        with TemporaryDirectory() as d:
            r=Path(d);p,doc,idx,pref=self.fixture(r)
            for key,value in [("replacement_sha256","0"*64),("replacement_modules",["leaf"])]:
                bad=copy.deepcopy(doc);bad["replacements"][0][key]=value;p.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):L.apply(p,"t",idx,pref,[],r)

    def test_unselected_original_or_new_module_collision_refuses(self):
        with TemporaryDirectory() as d:
            r=Path(d);p,doc,idx,pref=self.fixture(r)
            with self.assertRaisesRegex(ValueError,"absent"):L.apply(p,"t",{},pref,[],r)
            idx["helper"]=[str(r/"other.sv")]
            with self.assertRaisesRegex(ValueError,"collides"):L.apply(p,"t",idx,pref,[],r)

    def test_wrong_type_or_conflicting_define_refuses(self):
        with TemporaryDirectory() as d:
            r=Path(d);p,doc,idx,pref=self.fixture(r)
            with self.assertRaisesRegex(ValueError,"schema/type"):L.apply(p,"other",idx,pref,[],r)
            with self.assertRaisesRegex(ValueError,"conflicts"):L.apply(p,"t",idx,pref,["CANDIDATE=0"],r)

if __name__=="__main__":unittest.main()
