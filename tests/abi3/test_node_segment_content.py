"""Canonical content identity for deployment-v1 node-indexed sources."""

from __future__ import annotations

import json

import pytest

from runtime.abi3.crc import sha256
from runtime.abi3.deployment import Deployment, DeploymentError, ObjectSource, Segment

from . import probe_deployment, restamp


def _source() -> ObjectSource:
    return ObjectSource(
        kind="node_segments",
        size_bytes=8,
        node_segments=(
            (
                Segment(
                    "weights.bin",
                    0,
                    4,
                    "9f64a747e1b97f131fabb6b447296c9b6f0201e79fb3c5356e6c77e89b6a806a",
                ),
                Segment(
                    "weights.bin",
                    4,
                    4,
                    "55e5509f8052998294266ee5b50cb592938191fb5d67f73cac2e60b0276b1bdd",
                ),
            ),
            (
                Segment(
                    "weights.bin",
                    8,
                    4,
                    "e1e853684a206f1624968fbc03b4282f49b0683f0da7d6c8e52f62f7aa528d6b",
                ),
                Segment(
                    "weights.bin",
                    12,
                    4,
                    "c2eafbaa7384c3d1208d1b4cf6f32d2eacbd8eb87199c5b555aeadd9f84ed893",
                ),
            ),
        ),
    )


def _deployment_with_node_source() -> tuple[Deployment, int]:
    deployment = probe_deployment()
    object_id = deployment.notes["probe_ids"]["weights"]
    source = ObjectSource(
        kind="node_segments",
        size_bytes=128,
        node_segments=(
            (
                Segment(
                    "weights.bin", 0, 64, _source().node_segments[0][0].sha256
                ),
                Segment(
                    "weights.bin", 64, 64, _source().node_segments[0][1].sha256
                ),
            ),
        ),
    )
    deployment.objects[object_id] = source
    descriptor = deployment.table[object_id]
    descriptor.payload["content_digest"] = source.authenticated_content_digest()
    deployment.table.rewrite(object_id)
    return restamp(deployment), object_id


def _shared_source(kind: str) -> ObjectSource:
    segments = (
        (Segment("weights.bin", 0, 128, sha256(b"weights").hex()),)
        if kind == "file"
        else (
            Segment("weights.bin", 0, 64, sha256(b"weights-0").hex()),
            Segment("weights.bin", 64, 64, sha256(b"weights-1").hex()),
        )
    )
    return ObjectSource(kind=kind, size_bytes=128, segments=segments)


def test_node_segment_content_root_is_canonical_and_order_sensitive() -> None:
    source = _source()
    assert source.authenticated_content_digest().hex() == (
        "b41f742d57eb2690468adb1cf2275e15115088a550fd17c97007c5aadc9222cf"
    )
    assert ObjectSource.from_dict(source.to_dict()).authenticated_content_digest() == (
        source.authenticated_content_digest()
    )

    maps = list(source.node_segments)
    maps.reverse()
    reassigned = ObjectSource(
        kind="node_segments", size_bytes=8, node_segments=tuple(maps)
    )
    assert (
        reassigned.authenticated_content_digest()
        != source.authenticated_content_digest()
    )

    first = list(source.node_segments[0])
    first.reverse()
    reordered = ObjectSource(
        kind="node_segments",
        size_bytes=8,
        node_segments=(tuple(first), source.node_segments[1]),
    )
    assert (
        reordered.authenticated_content_digest()
        != source.authenticated_content_digest()
    )


def test_shared_segment_sources_retain_the_v1_composite_digest() -> None:
    segments = _source().node_segments[0]
    source = ObjectSource(kind="segments", size_bytes=8, segments=segments)
    expected = sha256(b"".join(bytes.fromhex(segment.sha256) for segment in segments))
    assert source.authenticated_content_digest() == expected


def test_node_segment_content_root_requires_every_range_digest() -> None:
    source = ObjectSource(
        kind="node_segments",
        size_bytes=4,
        node_segments=((Segment("weights.bin", 0, 4),),),
    )
    with pytest.raises(DeploymentError, match="no authenticated content digest"):
        source.authenticated_content_digest()


@pytest.mark.parametrize(
    ("offset", "nbytes", "message"),
    [
        (-1, 4, "offset must be non-negative"),
        (0, -1, "byte count must be non-negative"),
    ],
)
def test_segment_ranges_cannot_use_negative_slice_semantics(
    offset: int, nbytes: int, message: str
) -> None:
    """One malformed range cannot cancel another and pass size admission."""

    with pytest.raises(DeploymentError, match=message):
        Segment("weights.bin", offset, nbytes)


@pytest.mark.parametrize(
    ("offset", "nbytes"),
    [(-1, 129), (0, -1)],
)
def test_manifest_decode_rejects_negative_node_segment_ranges(
    offset: int, nbytes: int
) -> None:
    body = {
        "kind": "node_segments",
        "size_bytes": 128,
        "node_segments": [
            {
                "node_id": 0,
                "segments": [
                    {
                        "path": "weights.bin",
                        "offset": offset,
                        "bytes": nbytes,
                    },
                    {
                        "path": "weights.bin",
                        "offset": 0,
                        "bytes": 128 - nbytes,
                    },
                ],
            }
        ],
    }
    with pytest.raises(DeploymentError, match="must be non-negative"):
        ObjectSource.from_dict(body)


def test_bundle_read_and_write_admit_only_descriptor_bound_node_maps(
    tmp_path,
) -> None:
    deployment, object_id = _deployment_with_node_source()
    root = deployment.write(tmp_path / "valid")
    assert Deployment.read(root).objects[object_id] == deployment.objects[object_id]

    manifest_path = root / "deployment.json"
    manifest = json.loads(manifest_path.read_text())
    source_body = next(
        entry["source"]
        for entry in manifest["objects"]
        if entry["object_id"] == object_id
    )
    source_body["node_segments"][0]["segments"].reverse()
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(DeploymentError, match="node-segments content digest"):
        Deployment.read(root)

    stale, _ = _deployment_with_node_source()
    stale.table[object_id].payload["content_digest"] = bytes(32)
    stale.table.rewrite(object_id)
    with pytest.raises(DeploymentError, match="node-segments content digest"):
        stale.write(tmp_path / "stale")


@pytest.mark.parametrize("kind", ["file", "segments"])
def test_bundle_read_and_write_bind_complete_shared_sources(
    tmp_path, kind: str
) -> None:
    deployment = probe_deployment()
    object_id = deployment.notes["probe_ids"]["weights"]
    source = _shared_source(kind)
    deployment.objects[object_id] = source
    deployment.table[object_id].payload["content_digest"] = (
        source.authenticated_content_digest()
    )
    deployment.table.rewrite(object_id)
    deployment = restamp(deployment)

    root = deployment.write(tmp_path / kind)
    assert Deployment.read(root).objects[object_id] == source

    deployment.table[object_id].payload["content_digest"] = bytes(32)
    deployment.table.rewrite(object_id)
    with pytest.raises(
        DeploymentError, match=f"{kind} content digest does not match"
    ):
        deployment.write(tmp_path / f"stale-{kind}")


def test_bundle_legacy_shared_source_requires_zero_sentinel_and_valid_claims(
    tmp_path,
) -> None:
    deployment = probe_deployment()
    object_id = deployment.notes["probe_ids"]["weights"]
    deployment.objects[object_id] = ObjectSource(
        kind="segments",
        size_bytes=128,
        segments=(
            Segment("weights.bin", 0, 64),
            Segment("weights.bin", 64, 64, sha256(b"weights-1").hex()),
        ),
    )
    deployment = restamp(deployment)
    root = deployment.write(tmp_path / "legacy")
    assert Deployment.read(root).objects[object_id] == deployment.objects[object_id]

    manifest_path = root / "deployment.json"
    manifest = json.loads(manifest_path.read_text())
    source_body = next(
        entry["source"]
        for entry in manifest["objects"]
        if entry["object_id"] == object_id
    )
    source_body["segments"][1]["sha256"] = "not-a-sha256"
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(DeploymentError, match="must carry a 64-hex SHA-256"):
        Deployment.read(root)

    deployment.table[object_id].payload["content_digest"] = sha256(b"claimed")
    deployment.table.rewrite(object_id)
    with pytest.raises(DeploymentError, match="requires the all-zero"):
        deployment.write(tmp_path / "legacy-claimed")

    malformed = probe_deployment()
    malformed.objects[object_id] = ObjectSource(
        kind="segments",
        size_bytes=128,
        segments=(
            Segment("weights.bin", 0, 64),
            Segment("weights.bin", 64, 64, "not-a-sha256"),
        ),
    )
    with pytest.raises(DeploymentError, match="must carry a 64-hex SHA-256"):
        malformed.write(tmp_path / "legacy-malformed")
