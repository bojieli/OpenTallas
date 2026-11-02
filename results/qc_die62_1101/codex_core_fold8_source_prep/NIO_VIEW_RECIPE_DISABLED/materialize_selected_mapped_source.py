from pathlib import Path
import gzip,hashlib
b=Path(__file__).resolve().parents[1];raw=gzip.open(b/'native_fold_leaf_mapped.v.gz','rb').read();assert hashlib.sha256(raw).hexdigest()=='518e542ec811d9854ccc71f6904f1dca009dc82d0b7536d88491392a673df9c3'
dst=Path(__file__).resolve().parent/'MATERIALIZE_SELECTED_SOURCE/ot_coll_fold_slice.v';dst.parent.mkdir(exist_ok=True);dst.write_bytes(raw);print(dst)
