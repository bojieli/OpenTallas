# DIE-HBM-44 diagnostic wrapper: run wt/die-hbm-42 bind.py unchanged except the unplanned_bit_list cap (5000 -> 1e7); report-only
import sys
src_path = "/srv/opentallas-scratch2/claude/wt/die-hbm-42/tools/die_plan/bind.py"
src = open(src_path).read()
assert src.count("if len(self.unplanned_bits) < 5000:") == 1
src = src.replace("if len(self.unplanned_bits) < 5000:", "if len(self.unplanned_bits) < 10**7:")
sys.argv[0] = src_path
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/die-hbm-42/tools/die_plan")
g = {"__name__": "__main__", "__file__": src_path}
exec(compile(src, src_path, "exec"), g)
