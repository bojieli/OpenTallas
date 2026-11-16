import unittest
import kit_wave as KW

CFG = {"dies": {"d": {"event": "e2"}}}


def row(item, event, q="FAIL", status="ENQUEUED"):
    return {"die": "d", "item": item, "event": event, "status": status, "q_status": q}


class Retire(unittest.TestCase):
    def test_retire_when_current_row_else_relaunch(self):
        st = {"items": {"a1": row("a", "e1"), "a2": row("a", "e2", "RUNNING"),
                        "b1": row("b", "e1"), "c1": row("c", "e1", "SIGNED"), "d1": row("d", "e1", "RUNNING"),
                        "e2": row("e", "e2")}}
        self.assertEqual(KW.retire_superseded_rows(None, CFG, st, now=5), (1, 1))
        it = st["items"]
        self.assertEqual((it["a1"]["status"], it["a1"]["retire"]), ("CANCELLED", "retired"))
        self.assertEqual((it["b1"]["status"], it["b1"]["retire"]), ("CANCELLED", "relaunch"))
        self.assertEqual(it["a1"]["class"], "SUPERSEDED")
        for k in ("a2", "c1", "d1", "e2"):
            self.assertEqual(it[k]["status"], "ENQUEUED", k)      # current event, SIGNED, RUNNING untouched

    def test_idempotent(self):
        st = {"items": {"b1": row("b", "e1")}}
        KW.retire_superseded_rows(None, CFG, st)
        self.assertEqual(KW.retire_superseded_rows(None, CFG, st), (0, 0))
