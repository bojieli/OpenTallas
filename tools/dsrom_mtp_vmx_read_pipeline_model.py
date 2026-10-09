"""Model-only VMX read partition proposal; Claude review precedes implementation."""
import json
from pathlib import Path


def model():
    return json.loads((Path(__file__).resolve().parents[1] /
        'physical/s81_ph_views/mtp/vmx_read_pipeline_proposal.json').read_text())
