from pathlib import Path
import re

r = Path(__file__).parent
s = (r / "asap7_functional.v").read_text()
s, n = re.subn(
    r"module DFFASRHQNx1_ASAP7_75t_R\b.*?endmodule",
    (r / "asap7_asr_functional.v").read_text(),
    s,
    count=1,
    flags=re.S,
)
assert n == 1
(r / "asap7_functional.v").write_text(s)
