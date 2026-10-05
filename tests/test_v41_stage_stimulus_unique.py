"""Stimulus audit for the V4.1 stage benches: every injected word and every folded result of a run is unique.

A bench whose golden repeats a value cannot see a reordered, dropped or duplicated word.  This regenerates, from the
campaign drivers' own vector writers and seeds, the stimulus of every case of
  tools/rtl_v41_stage_collective_campaign.py  (rtl/test/tb_v41_stage_collective.sv, tb_v41_stage_hop),
  tools/rtl_v41_collective_levers_campaign.py (rtl/test/tb_v41_stage_collective_px.sv, tb_v41_stage_hop_px.sv),
and checks that no two producer words (over every die of the message) and no two folded results are equal.  The
batch-load bench's campaign (tools/rtl_v41_hop_batch_campaign.py) tags lane 0 of every word with (source, index) and
refuses a run whose words repeat, across the hop and every user's background words.

Order: the collective benches check the consumer's output word by word in emission order (tb_v41_stage_collective*:
the expected word is selected by the consumer's running count, and the gather's source rank is checked too); the hop
benches' consumer (hc_pre) is elementwise, so any arrival order is legal and the record's index selects the golden
word; the batch-load bench checks each T1 source's background words arrive in send order (the engine's per-source
FIFO).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import rtl_v41_collective_levers_campaign as L  # noqa: E402
import rtl_v41_stage_collective_campaign as B  # noqa: E402


def words(path):
    return [x for x in path.read_text().split() if not x.startswith("@")]


def assert_unique(ws, what):
    assert len(set(ws)) == len(ws), f"{what}: {len(ws) - len(set(ws))} repeated words"


def test_o2_campaign_stimulus_is_unique(tmp_path):
    for c in B.cases():
        p = B.PATTERNS[c["pattern"]]
        n = c.get("words", p["words"])
        sch = B.schedule(dict(p, words=n), c.get("order"))
        hop = c["pattern"] == "stage_hop"
        v = tmp_path / c["name"]
        B.vectors(v, n, [sch] * B.N, 1 if hop else p["mode"], 11 + len(c["name"]), 1 if hop else B.N)
        assert_unique(words(v / "part.hex"), c["name"])
        if p["mode"] == 0:
            assert_unique(words(v / "exp.hex"), c["name"] + " folded")


def test_lever_campaign_stimulus_is_unique(tmp_path):
    for c in L.cases():
        p = B.PATTERNS[c["pattern"]]
        v = tmp_path / c["name"]
        if c["pattern"] == "stage_hop":
            sch = B.schedule(dict(p, words=L.HOP_WORDS))
            lists, uniq = L.hop_lists(c["scheme"], c["u"])
            L.hop_vectors(v, sch, lists, uniq, 101 + len(c["name"]))
            ws = words(v / "part.hex")
            assert len(ws) == L.HOP_WORDS
        else:
            sch = B.schedule(p, c.get("order"))
            L.coll_vectors(v, p["words"], sch, p["mode"], 11 + len(c["name"]), L.data_lanes(c))
            ws = words(v / "part.hex")
            assert len(ws) == B.N * p["words"]
            if p["mode"] == 0:
                assert_unique(words(v / "exp.hex"), c["name"] + " folded")
        assert_unique(ws, c["name"])
