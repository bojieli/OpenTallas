"""FLEET-OPS 11-25: delete-manifests rotation keeps every byte (sha-verified pack), only touches day dirs older than 24 h, and find() reads the pack"""
import gzip
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import delete_manifest as DM  # noqa: E402


def day(root, name, age_h, n=3):
    d = root / name
    d.mkdir(parents=True)
    for i in range(n):
        p = d / f"0{i}0000-ot-delete-x{i}.jsonl.gz"
        with gzip.open(p, "wt") as f:
            f.write(json.dumps({"tree": f"/srv/t{i}"}) + "\n" + json.dumps({"p": f"gen/file{i}.json", "size": 1}) + "\n")
        q = d / f"0{i}0000-ot-delete-x{i}.inputs.tar.gz"
        q.write_bytes(gzip.compress(b"tar-bytes-%d" % i * 100))
        for z in (p, q):
            os.utime(z, (time.time() - age_h * 3600,) * 2)
    os.utime(d, (time.time() - age_h * 3600,) * 2)
    return d


def test_old_day_is_packed_verified_and_found_new_day_untouched(tmp_path):
    root = tmp_path / "dm"
    old = day(root, "2026-11-20", 48)
    new = day(root, "2026-11-25", 1)
    orig = {f: gzip.decompress((old / f).read_bytes()) for f in os.listdir(old)}
    res = DM.rotate(24, root=str(root))
    assert [r[0] for r in res] == ["2026-11-20"] and res[0][1] == 6
    assert not old.exists() and new.exists() and len(os.listdir(new)) == 6
    pack = root / "2026-11-20.pack.tar.zst"
    raw = subprocess.run(["zstd", "-dc", "--long=27", str(pack)], capture_output=True, check=True).stdout
    import io
    import tarfile
    with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
        got = {m.name.split("/", 1)[1]: tf.extractfile(m).read() for m in tf.getmembers()}
    assert got == {f[:-3]: b for f, b in orig.items()}                          # every byte kept
    os.environ["OT_DELETE_MANIFEST_DIR"] = str(root)
    try:
        hits = DM.find("file1.json", days=3650)
    finally:
        del os.environ["OT_DELETE_MANIFEST_DIR"]
    assert any(h[1] == "/srv/t1" for h in hits)


def test_a_day_with_one_young_file_and_a_second_run_do_nothing(tmp_path):
    root = tmp_path / "dm"
    d = day(root, "2026-11-24", 48)
    (d / "999999-late.jsonl.gz").write_bytes(gzip.compress(b"{}\n"))
    assert DM.rotate(24, root=str(root)) == [] and len(os.listdir(d)) == 7
    d2 = day(root, "2026-11-19", 48)
    assert len(DM.rotate(24, root=str(root))) == 1 and DM.rotate(24, root=str(root)) == []
