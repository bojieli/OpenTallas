"""FLOW-FLEET-R2: ot-tree-fork cross-host fetch prefers a host holding the tree and runs parallel size-balanced tar streams."""
import importlib.machinery, importlib.util, json, pathlib, subprocess
H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_tree_fork_fast", str(H / "ot-tree-fork"))
TF = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_tree_fork_fast", l)); l.exec_module(TF)
HASH = "a" * 64


def test_partition_balances_bytes():
    ents = [(100, "a"), (90, "b"), (10, "c"), (10, "d"), (5, "e")]
    parts = TF.partition(ents, 2)
    sizes = [sum(dict((r, s) for s, r in ents)[x] for x in p) for p in parts]
    assert sorted(x for p in parts for x in p) == ["a", "b", "c", "d", "e"] and max(sizes) - min(sizes) <= 15
    assert TF.partition([], 4) == [] and len(TF.partition([(1, "x")], 4)) == 1


def test_find_holder_uses_index_and_hash_file(monkeypatch):
    monkeypatch.setattr(TF.socket, "gethostname", lambda: "epyc7")
    idx = "\n".join([json.dumps({"path": "/s/tree-cache/old", "hash": "b" * 64}), json.dumps({"path": "/s/tree-cache/aaaa", "hash": HASH}),
                     json.dumps({"path": "/s/x.part", "hash": HASH})])

    def ask(host, cmd, timeout=0):
        if host == "epyc2":
            return 0, "" if "trees.jsonl" in cmd else ""
        if "trees.jsonl" in cmd:
            return 0, idx
        return 0, HASH + "\n" if "/s/tree-cache/aaaa/" in cmd else ""
    assert TF.find_holder(HASH, skip=("epyc8",), hosts=["epyc7", "epyc8", "epyc2", "epyc9"], ask=ask) == ("epyc9", "/s/tree-cache/aaaa")
    assert TF.find_holder("c" * 64, hosts=["epyc9"], ask=ask) is None
    assert TF.find_holder(HASH, hosts=["epyc9"], ask=lambda h, c, timeout=0: (255, "")) is None


def test_list_remote_parses_find(monkeypatch):
    monkeypatch.setattr(TF, "ssh_out", lambda h, c, timeout=0: (0, "d 4096 sub\nf 120 sub/a.v\nl 9 sub/l\nf 5 .fork.json\n"))
    dirs, files = TF.list_remote("epyc8", "/s/t")
    assert dirs == ["sub"] and files == [(120, "sub/a.v"), (9, "sub/l")]


def test_default_ssh_has_fast_cipher_no_compression():
    assert "Compression=no" in TF.SSH and any("aes128-gcm" in x for x in TF.SSH) and TF.STREAMS >= 2
