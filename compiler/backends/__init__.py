"""ABI 3.0 backends.

Each backend lowers one neutral Tensor Kernel IR v3 document onto one physical
target.  A backend owns placement and scheduling; it never owns model
semantics, and it never invents an ABI construct: descriptors and instructions
are emitted only through :mod:`runtime.abi3.builder`.
"""
