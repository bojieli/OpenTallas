# Image provenance correction

The original method README called `af971398d91e` the actual installed image ID. That was incorrect: it is the `frozen_calibration_image_id` retained by the input models, not a universal current image identity. The original claim is preserved as method history and superseded by this correction. The method capability logs do not retain a contemporaneous per-host Docker inspection, so their original-session image ID must not be reconstructed from the frozen calibration field.

The Stage A receipts preserve the actual image ID strings for the original ep8 check, ep6 reporting pickup, and ep7 true-fixed-pin control. These are distinct observations from the frozen calibration identity. Their binary version/SHA is unchanged; this correction does not request restart, geometry repair or another DRC run.

`image_provenance/` additionally contains read-only validation observations from 2026-10-19 21:32:26 UTC on each of ot-epyc6, ot-epyc7 and ot-epyc8. These are current validation receipts, explicitly not retroactive job receipts. Each retains raw `docker image inspect` Id/RepoDigests output, raw binary SHA output and a timestamped parsed record. All three observed:

- requested image: `openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29`;
- actual `.Id`: `sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29`;
- actual `.RepoDigests`: the same pinned OpenROAD reference;
- actual OpenROAD binary SHA256: `21eda99eeae7eccb22ca64ad28949c08a6c01dcece3ccb23e2206d635f8d2846`.

No host-specific image ID should be inferred solely from a tag, another host, an input model or a repository digest. Future native jobs should retain their own actual host/image/binary receipt. The Stage A source-join failures, fixed-pin visibility findings and rule-coverage limitations are unchanged.
