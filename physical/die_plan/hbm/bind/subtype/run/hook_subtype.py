"""BIND-SUBTYPE overlay hook: insert the claude/bind-subtype-1111 subtype_bind call into a bind.py copy (exact anchors)."""
import sys
p = sys.argv[1]
t = open(p).read()
A = '        if self.ab.get("structural_bridges"):\n'
B = '    rep["type_canon_merged"] = getattr(B, "type_canon_merged", [])\n'
assert t.count(A) == 1 and t.count(B) == 1 and "subtype_bind" not in t, "anchor"
H = ('        self.subtype_receipts = []\n'
     '        if self.ab.get("subtype_bind"):\n'
     '            # BIND-SUBTYPE 11-11 (opt-in asbuilt.subtype_bind): native leaf -> exact RTL composition (bind_subtype.py)\n'
     '            import bind_subtype\n'
     '            try:\n'
     '                self.subtype_receipts = bind_subtype.apply(self, self.ab["subtype_bind"])\n'
     '            except bind_subtype.SubtypeError as exc:\n'
     '                raise BindError(f"SUBTYPE_BIND {exc}") from exc\n')
t = t.replace(A, H + A).replace(B, B + '    if getattr(B, "subtype_receipts", None):\n        rep["subtype_bind"] = B.subtype_receipts\n')
open(p, "w").write(t)
print("HOOK_OK")
