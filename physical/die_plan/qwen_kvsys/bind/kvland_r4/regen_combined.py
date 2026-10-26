"""Candidate-scoped common pair-image TXDP; all other rules use canonical hook."""
import importlib.util
from pathlib import Path
def regen(ctx):
 here=Path(__file__).resolve().parent
 spec=importlib.util.spec_from_file_location('kv_combined_regen',here.parent/'kvbind1025/regen_kv_2350.py')
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 m.PAIR=here/'pair_image_txdp_combined.json'
 return m.regen(ctx)
