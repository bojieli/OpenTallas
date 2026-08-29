from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

import runtime.service_engine.secure_artifacts as secure_module
from runtime.service_engine.secure_artifacts import (
    SecureArtifactError,
    SecureDirectory,
    canonical_json_bytes,
    parse_canonical_json,
    publish_payload_tree,
    safe_relative_path,
)


def test_canonical_json_roundtrip_is_exact_and_type_preserving() -> None:
    value = {
        "array": [None, False, True, 0, 1, "µ"],
        "nested": {"z": -3, "a": "value"},
    }
    payload = canonical_json_bytes(value)
    assert payload == (
        b'{"array":[null,false,true,0,1,"\xc2\xb5"],"nested":{"a":"value","z":-3}}\n'
    )
    observed = parse_canonical_json(
        payload,
        label="fixture manifest",
        maximum_bytes=len(payload),
    )
    assert observed == value
    assert type(observed["array"][1]) is bool
    assert type(observed["array"][3]) is int


@pytest.mark.parametrize(
    "payload",
    [
        b'{"a":1, "b":2}\n',
        b'{"b":2,"a":1}\n',
        b'{"a":1}',
        b'{"a":1}\n\n',
        b'{"a":1,"a":1}\n',
        b'{"a":NaN}\n',
        b'{"a":Infinity}\n',
        b"\xff\n",
        b"",
    ],
)
def test_noncanonical_duplicate_nonfinite_and_invalid_json_fail_closed(
    payload: bytes,
) -> None:
    with pytest.raises(SecureArtifactError):
        parse_canonical_json(payload, label="bad JSON", maximum_bytes=1024)


def test_json_size_and_argument_types_are_bounded() -> None:
    payload = canonical_json_bytes({"a": 1})
    with pytest.raises(SecureArtifactError, match="bounded JSON size"):
        parse_canonical_json(payload, label="manifest", maximum_bytes=len(payload) - 1)
    with pytest.raises(SecureArtifactError, match="exact bytes"):
        parse_canonical_json(  # type: ignore[arg-type]
            bytearray(payload),
            label="manifest",
            maximum_bytes=1024,
        )
    with pytest.raises(SecureArtifactError, match="canonical JSON"):
        canonical_json_bytes({"not-json": object()})


@pytest.mark.parametrize(
    "value",
    [
        "",
        ".",
        "..",
        "/absolute",
        "a/../b",
        "a/./b",
        "a//b",
        "a\\b",
        "a\x00b",
        1,
        True,
        None,
    ],
)
def test_relative_path_validation_rejects_aliases_and_escapes(value: object) -> None:
    with pytest.raises(SecureArtifactError, match="relative path|canonical POSIX"):
        safe_relative_path(value, label="artifact")
    assert safe_relative_path("a/b-c_1.bin", label="artifact") == "a/b-c_1.bin"


def _fixture_tree(root: Path) -> dict[str, bytes]:
    (root / "a/b").mkdir(parents=True)
    payloads = {
        "manifest.json": canonical_json_bytes({"schema": "fixture.v1"}),
        "a/value.bin": b"value",
        "a/b/empty.bin": b"",
    }
    for relative, payload in payloads.items():
        (root / relative).write_bytes(payload)
    return payloads


def test_secure_directory_reads_hashes_enumerates_and_reverifies(
    tmp_path: Path,
) -> None:
    root = tmp_path / "tree"
    payloads = _fixture_tree(root)
    with SecureDirectory(root, label="fixture tree") as tree:
        files, directories = tree.enumerate_tree()
        assert files == set(payloads)
        assert directories == {"a", "a/b"}
        for relative, expected in payloads.items():
            source = tree.open_file(
                relative,
                label=relative,
                minimum_size=0,
                maximum_size=len(expected),
                exact_size=len(expected),
            )
            assert (
                source.read_bytes(
                    label=relative,
                    maximum_bytes=max(1, len(expected)),
                )
                == expected
            )
            assert source.sha256(label=relative) == hashlib.sha256(expected).hexdigest()
        tree.verify()


def test_secure_directory_rejects_symlinked_root_component_and_file(
    tmp_path: Path,
) -> None:
    real = tmp_path / "real"
    real.mkdir()
    (real / "payload.bin").write_bytes(b"x")
    (tmp_path / "root-link").symlink_to(real, target_is_directory=True)
    with pytest.raises(SecureArtifactError, match="without following symlinks"):
        SecureDirectory(tmp_path / "root-link", label="linked root")

    (real / "target.bin").write_bytes(b"x")
    (real / "file-link").symlink_to("target.bin")
    with SecureDirectory(real, label="real root") as tree:
        with pytest.raises(SecureArtifactError, match="without following symlinks"):
            tree.open_file(
                "file-link",
                label="linked file",
                maximum_size=1,
            )


def test_fifo_is_rejected_without_blocking(tmp_path: Path) -> None:
    root = tmp_path / "fifo-tree"
    root.mkdir()
    os.mkfifo(root / "pipe")
    with SecureDirectory(root, label="FIFO tree") as tree:
        with pytest.raises(SecureArtifactError, match="not a regular file"):
            tree.open_file("pipe", label="FIFO", maximum_size=16)
        with pytest.raises(SecureArtifactError, match="non-regular"):
            tree.enumerate_tree()


def test_file_size_bounds_fail_before_payload_use(tmp_path: Path) -> None:
    root = tmp_path / "tree"
    root.mkdir()
    (root / "payload.bin").write_bytes(b"1234")
    with SecureDirectory(root, label="tree") as tree:
        with pytest.raises(SecureArtifactError, match="expected 3"):
            tree.open_file(
                "payload.bin",
                label="payload",
                maximum_size=4,
                exact_size=3,
            )
        with pytest.raises(SecureArtifactError, match="bounded size"):
            tree.open_file(
                "payload.bin",
                label="payload",
                maximum_size=3,
            )


def test_in_place_mutation_is_detected_before_read_or_verify(tmp_path: Path) -> None:
    root = tmp_path / "tree"
    root.mkdir()
    path = root / "payload.bin"
    path.write_bytes(b"before")
    with SecureDirectory(root, label="tree") as tree:
        source = tree.open_file("payload.bin", label="payload", maximum_size=16)
        path.write_bytes(b"after!")
        with pytest.raises(SecureArtifactError, match="changed"):
            source.read_bytes(label="payload", maximum_bytes=16)
        with pytest.raises(SecureArtifactError, match="changed"):
            tree.verify()


def test_namespace_replacement_is_detected_with_held_inode(tmp_path: Path) -> None:
    root = tmp_path / "tree"
    root.mkdir()
    path = root / "payload.bin"
    path.write_bytes(b"original")
    with SecureDirectory(root, label="tree") as tree:
        source = tree.open_file("payload.bin", label="payload", maximum_size=16)
        replacement = root / "replacement"
        replacement.write_bytes(b"original")
        os.replace(replacement, path)
        with pytest.raises(SecureArtifactError, match="changed"):
            source.read_bytes(label="held payload", maximum_bytes=16)
        with pytest.raises(SecureArtifactError, match="changed|replaced"):
            tree.verify()


def test_root_replacement_is_detected(tmp_path: Path) -> None:
    root = tmp_path / "tree"
    root.mkdir()
    with SecureDirectory(root, label="tree") as tree:
        old = tmp_path / "old-tree"
        os.replace(root, old)
        root.mkdir()
        with pytest.raises(SecureArtifactError, match="root was replaced"):
            tree.verify_identity()


def test_tree_depth_and_entry_bounds_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "tree"
    (root / "a/b/c").mkdir(parents=True)
    (root / "a/one").write_bytes(b"1")
    (root / "a/two").write_bytes(b"2")
    with SecureDirectory(root, label="bounded tree") as tree:
        with pytest.raises(SecureArtifactError, match="tree-depth"):
            tree.enumerate_tree(maximum_depth=1)
        with pytest.raises(SecureArtifactError, match="tree-entry"):
            tree.enumerate_tree(maximum_entries=1)


def test_publish_payload_tree_is_exact_durable_and_create_once(tmp_path: Path) -> None:
    output = tmp_path / "result"
    payloads = {
        "manifest.json": canonical_json_bytes({"schema": "result.v1"}),
        "outputs/value.bin": b"payload",
        "diagnostics/empty.bin": b"",
    }
    publish_payload_tree(
        output,
        payloads=payloads,
        directories=("outputs", "diagnostics"),
        label="fixture result",
    )
    assert output.is_dir()
    for relative, expected in payloads.items():
        assert (output / relative).read_bytes() == expected
    assert not any(path.name.startswith(".result.tmp-") for path in tmp_path.iterdir())

    with pytest.raises(SecureArtifactError, match="already exists"):
        publish_payload_tree(
            output,
            payloads=payloads,
            directories=("outputs", "diagnostics"),
            label="fixture result",
        )
    for relative, expected in payloads.items():
        assert (output / relative).read_bytes() == expected


def test_two_publications_have_byte_identical_trees(tmp_path: Path) -> None:
    payloads = {
        "request_manifest.json": canonical_json_bytes({"schema": "request.v1"}),
        "input/value.bin": bytes(range(64)),
    }
    for name in ("first", "second"):
        publish_payload_tree(
            tmp_path / name,
            payloads=payloads,
            directories=("input",),
            label=name,
        )
    first = sorted(
        (path.relative_to(tmp_path / "first").as_posix(), path.read_bytes())
        for path in (tmp_path / "first").rglob("*")
        if path.is_file()
    )
    second = sorted(
        (path.relative_to(tmp_path / "second").as_posix(), path.read_bytes())
        for path in (tmp_path / "second").rglob("*")
        if path.is_file()
    )
    assert first == second


@pytest.mark.parametrize(
    ("payloads", "directories", "match"),
    [
        ({}, (), "nonempty"),
        ({"value.bin": bytearray(b"x")}, (), "payload closure"),
        ({"../value.bin": b"x"}, (), "relative path"),
        ({"nested/value.bin": b"x"}, (), "directory closure"),
        ({"value.bin": b"x"}, ("unused",), "directory closure"),
        ({"nested/value.bin": b"x"}, ("nested", "nested"), "repeats"),
        ({"nested/value.bin": b"x"}, "nested", "directories"),
    ],
)
def test_publication_rejects_invalid_path_and_role_closure(
    tmp_path: Path,
    payloads: object,
    directories: object,
    match: str,
) -> None:
    with pytest.raises(SecureArtifactError, match=match):
        publish_payload_tree(
            tmp_path / "output",
            payloads=payloads,  # type: ignore[arg-type]
            directories=directories,  # type: ignore[arg-type]
            label="invalid tree",
        )
    assert not (tmp_path / "output").exists()


def test_late_parent_sync_failure_rolls_back_owned_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "result"
    original_fsync = secure_module.os.fsync
    parent_identity = (tmp_path.stat().st_dev, tmp_path.stat().st_ino)
    parent_sync_count = 0

    def fail_parent_sync(descriptor: int) -> None:
        nonlocal parent_sync_count
        metadata = os.fstat(descriptor)
        if (metadata.st_dev, metadata.st_ino) == parent_identity:
            parent_sync_count += 1
            raise OSError("injected parent sync failure")
        original_fsync(descriptor)

    monkeypatch.setattr(secure_module.os, "fsync", fail_parent_sync)
    with pytest.raises(OSError, match="injected parent sync failure"):
        publish_payload_tree(
            output,
            payloads={"manifest.json": canonical_json_bytes({"a": 1})},
            directories=(),
            label="rollback result",
        )
    assert parent_sync_count == 1
    assert not output.exists()
    assert not any(path.name.startswith(".result.tmp-") for path in tmp_path.iterdir())


def test_competing_destination_is_preserved_and_temporary_tree_is_cleaned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "result"
    original = secure_module._rename_no_replace

    def race_destination(**kwargs: object) -> None:
        parent_descriptor = kwargs["parent_descriptor"]
        destination_name = kwargs["destination_name"]
        assert type(parent_descriptor) is int and type(destination_name) is str
        os.mkdir(destination_name, 0o700, dir_fd=parent_descriptor)
        destination_descriptor = os.open(
            destination_name,
            os.O_RDONLY | os.O_DIRECTORY,
            dir_fd=parent_descriptor,
        )
        try:
            descriptor = os.open(
                "competitor.txt",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=destination_descriptor,
            )
            try:
                os.write(descriptor, b"competitor")
            finally:
                os.close(descriptor)
        finally:
            os.close(destination_descriptor)
        original(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(secure_module, "_rename_no_replace", race_destination)
    with pytest.raises(SecureArtifactError, match="already exists"):
        publish_payload_tree(
            output,
            payloads={"manifest.json": canonical_json_bytes({"a": 1})},
            directories=(),
            label="raced result",
        )
    assert (output / "competitor.txt").read_bytes() == b"competitor"
    assert not any(path.name.startswith(".result.tmp-") for path in tmp_path.iterdir())
