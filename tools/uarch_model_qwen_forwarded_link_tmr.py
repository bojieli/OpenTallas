"""Protected synchronized-release link graph; no endpoint/physical adoption."""
import json
from pathlib import Path
def model():
    return json.loads((Path(__file__).resolve().parents[1]/'results/uarch/qwen_link_forwarded_graph_tmr_20261007/model.json').read_text())
