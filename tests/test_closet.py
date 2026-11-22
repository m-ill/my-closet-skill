import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import closet  # noqa: E402


def run(*argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = closet.main(list(argv))
    return code, json.loads(buf.getvalue())


class ClosetTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MY_CLOSET_DB"] = str(Path(self.tmp.name) / "closet.db")

    def tearDown(self):
        os.environ.pop("MY_CLOSET_DB", None)
        self.tmp.cleanup()

    def test_status_shows_menu_on_empty_closet(self):
        code, out = run("status")
        self.assertEqual(code, 0)
        self.assertEqual(out["garment_count"], 0)
        self.assertIn("👕 내 옷장 (0벌)", out["guide"])
        self.assertIn("1. 라벨 올리기", out["guide"])

    def test_add_label_and_visual_get_numbers_and_dates(self):
        code, out = run("add", json.dumps([
            {"kind": "label", "fields": {"brand": "UNIQLO", "category": "trousers", "size": "L", "sku": "321-455492"}},
            {"kind": "visual", "fields": {"category": "jacket", "color": "navy", "details": ["zipper"]}},
        ]))
        self.assertEqual(code, 0)
        self.assertEqual([s["no"] for s in out["saved"]], [1, 2])
        self.assertEqual(out["saved"][0]["summary"], "UNIQLO · 바지 · 사이즈 L · 품번 321-455492")
        self.assertRegex(out["saved"][0]["created_at"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
        self.assertIn("(2벌)", out["guide"])
        _, listed = run("list")
        self.assertEqual([i["no"] for i in listed["items"]], [2, 1])

    def test_numbers_are_never_reused_after_remove(self):
        run("add", '{"kind":"label","fields":{"brand":"A"}}')
        run("add", '{"kind":"label","fields":{"brand":"B"}}')
        code, out = run("remove", "2")
        self.assertEqual((code, out["garment_count"]), (0, 1))
        _, out = run("add", '{"kind":"label","fields":{"brand":"C"}}')
        self.assertEqual(out["saved"][0]["no"], 3)
        code, out = run("remove", "2")
        self.assertEqual(code, 2)

    def test_bad_input_saves_nothing_and_says_so(self):
        for payload in [
            '{"kind":"label","fields":{"brand":"<script>"}}',
            '{"kind":"label","fields":{"product":"https://example.com"}}',
            '{"kind":"visual","fields":{"material":"cotton"}}',
            '{"kind":"visual","fields":{"category":"spaceship"}}',
            '{"kind":"label","fields":{"gtin":"4006381333932"}}',
            '{"kind":"label","fields":{}}',
            '{"kind":"label","fields":{"brand":"A"},"owner":"x"}',
            'not json',
        ]:
            code, out = run("add", payload)
            self.assertEqual(code, 2, payload)
            self.assertFalse(out["saved"])
        _, out = run("status")
        self.assertEqual(out["garment_count"], 0)

    def test_one_bad_garment_in_a_batch_saves_none(self):
        code, _ = run("add", '[{"kind":"label","fields":{"brand":"OK"}},{"kind":"visual","fields":{"color":"plaid"}}]')
        self.assertEqual(code, 2)
        self.assertEqual(run("status")[1]["garment_count"], 0)

    def test_valid_gtin_and_text_normalization(self):
        _, out = run("add", '{"kind":"label","fields":{"gtin":"4006381333931","brand":"  UNIQLO   C "}}')
        self.assertEqual(out["saved"][0]["fields"], {"brand": "UNIQLO C", "gtin": "4006381333931"})

    def test_export_csv_and_json(self):
        run("add", '{"kind":"visual","fields":{"category":"coat","details":["belt","buttons"]}}')
        _, out = run("export", "--format", "csv")
        self.assertIn("belt buttons", out["data"])
        _, out = run("export")
        self.assertEqual(out["items"][0]["fields"]["category"], "coat")

    def test_morning_settings(self):
        code, out = run("pref", "morning_time", "07:00")
        self.assertEqual((code, out["prefs"]), (0, {"morning_time": "07:00"}))
        run("pref", "city", "Seoul")
        self.assertEqual(run("pref")[1]["prefs"], {"city": "Seoul", "morning_time": "07:00"})
        self.assertEqual(run("pref", "morning_time", "25:00")[0], 2)
        self.assertEqual(run("pref", "face_photo", "x")[0], 2)
        self.assertEqual(run("pref", "notes", "https://evil.example")[0], 2)
        run("pref", "city", "")
        self.assertEqual(run("pref")[1]["prefs"], {"morning_time": "07:00"})
        self.assertIn("아침 추천", run("status")[1]["guide"])

    def test_hidden_direction_characters_are_refused(self):
        code, _ = run("add", json.dumps({"kind": "label", "fields": {"brand": "A\u202eB"}}))
        self.assertEqual(code, 2)

    def test_outfit_gives_photo_searches_and_required_steps(self):
        run("add", json.dumps([
            {"kind": "label", "fields": {"brand": "UNIQLO", "sku": "321-455492", "category": "trousers"}},
            {"kind": "label", "fields": {"brand": "COS", "category": "jacket"}},
            {"kind": "visual", "fields": {"category": "blazer", "color": "gray"}},
        ]))
        code, out = run("outfit", "1", "2", "3")
        self.assertEqual(code, 0)
        self.assertEqual([g["photo_search"] for g in out["garments"]], ["UNIQLO 321-455492 trousers", "COS jacket", None])
        self.assertTrue(any("GENERATE ONE outfit image" in s for s in out["steps"]))
        self.assertEqual(run("outfit", "9")[0], 2)


if __name__ == "__main__":
    unittest.main()
