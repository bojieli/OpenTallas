import unittest

import placement_visual_agent as review


KIT = "epyc8:/srv/opentallas-scratch2/claude/lane/run/gen/item"


class ReviewTests(unittest.TestCase):
    def test_exact_private_request_wins_over_wave_entry(self):
        header = "die\ttype\tfamily\tattempt\tstate\trender_dir\tauto_geom\thost\n"
        row = f"s81\titem\titem\t1\tWAIT-VISUAL\t{KIT}/run/layout_review\t\tepyc8\n"
        private = {"die": "s81", "item": "item", "attempt": 1, "kit": KIT,
                   "render_dir": KIT + "/run/layout_review",
                   "sidecar": "autopilot/private_visual_requests/" + "a" * 64 + "/visual_request.json",
                   "odb_sha256": "b" * 64, "stage_fingerprint": "c" * 64}
        requests, _ = review.candidates({"queue": header + row, "viewed": [],
                                         "private": [private], "canary": []})
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].odb_sha256, "b" * 64)

    def test_evidence_path_must_be_in_exact_kit(self):
        req = review.Request("s81", "item", "1", KIT, KIT + "2/run/layout_review")
        with self.assertRaisesRegex(ValueError, "outside"):
            review.evidence(req, "stat")
        with self.assertRaises(ValueError):
            review.split_location(KIT + "/../../other")

    def test_nonverdict_does_not_release_route(self):
        with self.assertRaises(ValueError):
            review.validated({"verdict": "ACCEPT", "observation": "x" * 40,
                              "findings": []})
        with self.assertRaises(ValueError):
            review.validated({"verdict": "GOOD", "observation": "OK",
                              "findings": []})
