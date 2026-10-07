"""Source-pinned directional Qwen link graph composition, no adoption credit."""
import json
from pathlib import Path
def model():
    return json.loads((Path(__file__).resolve().parents[1]/'results/uarch/qwen_link_forwarded_graph_20261007/graph_prebuild_model.json').read_text())
