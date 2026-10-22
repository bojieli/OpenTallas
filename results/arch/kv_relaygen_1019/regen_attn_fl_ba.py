import re, sys
from pathlib import Path
W = Path(sys.argv[1]); copies = int(sys.argv[2])
sys.path.insert(0, str(W / "tools/ref_tile"))
import face_land as F
p = W / "rtl/lib/face_land/qkd_kvs_attn_fl_ba.sv"
old = p.read_text()
reason = re.search(r"^//   reason: (.*)$", old, re.M).group(1)
fl = {"core": "qkd_kvs_attn", "core_src": "rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu_ba.sv",
      "reset_ports": ["rst_n"], "land": {"fin": 1, "i_ctl": 1}, "reason": reason}
pl = F.ports(W / fl["core_src"], fl["core"])
hdr = "".join(old.splitlines(True)[:4])
wr = lambda: F.wrapper(fl, pl, "ck").split("\n", 1)[1]
base = hdr + wr()
assert base == old, "regen without copies is NOT byte-identical to the committed wrapper"
print("REGEN copies=1 byte-identical to committed wrapper: OK")
fl["reset_copies"] = {"rst_n": copies}
new = hdr.replace("// so the closed qkd_kvs_attn_fl.sv stays byte-identical.\n",
                  "// so the closed qkd_kvs_attn_fl.sv stays byte-identical.  KV-RELAYGEN 10-19: rst_n relay with "
                  f"{copies} kept copies (face_land reset_copies; gate ba1: 1,221 loads on one copy).\n") + wr()
p.write_text(new)
print("wrote", p)
