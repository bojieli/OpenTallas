This directory is a standalone frozen component gate for physical grant
5838d364e: 86.4 by 194.4 micrometres, 348 pins, one 833.334 ps root.

The producer's git source commit is
f74794fa41fba1b7f53946533e4e7c8f76bdbb35. Its source-file SHA256 is
b50da24fa0ebd9cce161e44af8028cfd76e47538c2494b594e8ce11d5a0bd60c.
These are distinct identifiers. A shorthand such as f747/b50 denotes the
commit/file-hash pair, not one git revision.

All dependencies are local in this directory: the exact producer, the actual
qkd_kv_static_writer core and native wrapper, ot_rst_relay, the standalone TB
and the frozen reset_v4 boot.hex. The manifest records the original paths and
full hashes. There are no compiler, package-module, checkpoint, global
uarch_model or physical inventory imports. The writer is the actual upstream
RTL, not a substituted memory array or idealized writer.

From any directory, run the package runner with a fresh output directory:

    /path/to/leaf_package_v1/run.sh /fresh/output

This checks frozen hashes, runs the full all36/two-token production component
fixture, then runs the observed MUT1 negative control. For a scalar mutant
gate only:

    /path/to/leaf_package_v1/run.sh /fresh/mutant-output 1

MUT0 must complete 1152 cohorts, 4608 word slots and 9216 sectors after one
boot/seal and no normal reset/configuration. MUT1 flips one independently
captured compiled TAG59 epoch bit while actual input words retain the original
identity; the actual native writer must report fault. Both gates use the same
frozen external fixture. Gate receipts and logs are included. Functional RTL
has not changed since f74794fa4.

The 181-write boot image is byte-identical to reset_v4/boot.hex, SHA256
5a4692f113422dc5c1d3d15f81d7dccb130c821398e0a405c05cb71e760d7bfe.
It is a declared component test timeline, not a measured production programme
or a full-token timing receipt. Physical timing and whole-root qualification
remain separate.

The source branch is pushed. Authoritative root-publication confirmation is
owned by the root publisher and was pending when this package was assembled.
Do not interpret this component gate receipt as an origin/main publication
receipt. The physical owner must use the root publisher's explicit receipt
before submitting the physical run.
