# Security policy

## What this project is, and what that means for security

OpenTallas is a hardware research repository: analytical models, a compiler and
runtime that build and simulate deployments, SystemVerilog RTL, and physical-design
flows. It is **not** a service, it processes no user data, and it holds no
credentials. There is no deployed system to attack.

That shapes what a security report means here. The realistic risk classes are:

**1. Untrusted input to the toolchain.** The compiler, runtime, deployment
verifier and cycle model parse model checkpoints, `deployment.json`,
`descriptors.bin`, `program.bin` and workload files. If any of those can be
crafted to cause arbitrary code execution, an unbounded write, or a path escape
outside the working tree, that is a genuine vulnerability — someone may run this
against a deployment they did not build. Report it.

**2. Supply chain.** The bootstrap scripts under `tools/` fetch external tools
(Verilator, Yosys, OpenSTA, PDKs) and pin them by commit or digest. A pin that is
wrong, missing, or silently falls back to an unpinned download is a security
issue, not just a reproducibility one.

**3. Accidentally committed secrets.** None are known — scans for API-key,
token, and private-key shapes across all tracked text return nothing, and no
`.env`, `.netrc`, or `.pem` has ever been tracked. If you find one, report it
privately rather than opening an issue.

**Not security issues** (please open a normal issue instead): a wrong number, a
drifted artifact, a failing gate, a test that fails in one execution order, or a
claim you believe is overstated. Those matter a great deal to this project, but
they are correctness, and the repository is deliberately public about them — see
`tools/check_redesign_gates.py` and `docs/REPRODUCIBILITY.md`.

## Reporting

For anything in classes 1–3, **report privately first**: use GitHub's private
vulnerability reporting on this repository, or contact the maintainer at the
address in the git history. Please include what you ran, what happened, and what
you expected.

Expect an acknowledgement within a week. This is a single-maintainer research
project, not a funded security programme — there is no bounty, and fixes ship on
a best-effort schedule. If a report goes unanswered for 30 days, you are welcome
to disclose publicly.

## Supported versions

Only `main` is supported. There are no releases, no long-lived branches, and no
backports; `pyproject.toml` declares version `0.1.0` and the repository has not
been tagged. Fixes land on `main` and nowhere else.

## Scope note on third-party content

`NOTICE` lists third-party material redistributed here, including ASAP7 cell
geometry inside committed GDSII and one model weight tensor. Vulnerabilities in
upstream tools or PDKs belong to those projects; report them there. What belongs
here is a problem with *how this repository fetches, pins, or handles* them.
