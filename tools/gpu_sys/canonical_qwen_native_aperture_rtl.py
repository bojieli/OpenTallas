"""Generate actual sealed collector with CURRENT query/lease observation ports."""
from pathlib import Path
from tools.gpu_sys.canonical_qwen_native_aperture_model import BITS,OFF
ROOT=Path(__file__).resolve().parents[2]
def generate(out):
 s=Path(__file__).with_name('canonical_qwen_native_aperture_template.sv').read_text()
 s=s.replace('@BITS@',str(BITS)).replace('@OFFSETS@','\n'.join(f' localparam integer C_{n.upper()}={o};' for n,(o,w) in OFF.items()))
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 f=out/'ot_gpu_qwen_native_aperture_collector.sv';f.write_text(s);return f
if __name__=='__main__':
 import argparse
 a=argparse.ArgumentParser();a.add_argument('--out',required=True);print(generate(a.parse_args().out))
