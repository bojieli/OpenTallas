from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text().replace("if (bv && b_key == 6'(wg))", "if (bv && b_key == 6'(wg) && !(av && a_key == 6'(wg)))");Path(sys.argv[2]).write_text(s)
