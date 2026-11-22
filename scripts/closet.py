#!/usr/bin/env python3
"""My Closet: a local wardrobe database for AI assistants.

The assistant reads photos and labels itself; this script only validates and stores
the text it extracted, in a SQLite file on the user's own machine. Standard library only.

  python closet.py status
  python closet.py list [--limit N]
  python closet.py add '{"kind":"label","fields":{"brand":"UNIQLO","size":"L"}}'
  python closet.py remove 3
  python closet.py export [--format json|csv]

Every command prints one JSON object. Exit code 0 means it worked; anything else
means nothing was saved, and the assistant must say so.
"""
import argparse
import csv
import io
import json
import os
import re
import sqlite3
import sys
import unicodedata
import uuid
from pathlib import Path

LABEL = {"brand": 70, "product": 120, "sku": 64, "size": 40, "color": 48, "fit": 48, "material": 120, "gtin": 14}
VISUAL = {
    "category": "t_shirt shirt blouse polo sweater sweatshirt hoodie cardigan vest jacket blazer coat trousers jeans shorts skirt dress jumpsuit wrap other".split(),
    "color": "black white off_white cream gray charcoal navy blue light_blue brown beige tan olive green burgundy red pink purple orange yellow silver gold multicolor".split(),
    "silhouette": "straight boxy tapered flared a_line asymmetric rounded waist_shaped draped".split(),
    "length": "cropped short mid long knee ankle full".split(),
    "pattern": "solid striped checked color_block floral graphic dotted abstract herringbone camouflage mixed".split(),
    "neck_collar": "crew v_neck scoop square turtleneck mock_neck hood point_collar spread_collar band_collar lapels collarless boat other".split(),
    "sleeve": "sleeveless short three_quarter long raglan puffed".split(),
}
DETAILS = ("buttons snap_buttons zipper chest_pocket patch_pockets side_pockets drawstring belt_loops belt pleats darts ribbed_trim "
           "contrast_stitch contrast_trim elastic_cuff elastic_waist slit visible_patches visible_embroidery ruffle raised_texture "
           "smooth_texture shiny_finish matte_finish").split()
LABEL_KEYS = list(LABEL) + ["category"]
VISUAL_KEYS = list(VISUAL) + ["details"]
KO_CATEGORY = {"t_shirt": "티셔츠", "shirt": "셔츠", "blouse": "블라우스", "polo": "폴로", "sweater": "스웨터", "sweatshirt": "맨투맨",
               "hoodie": "후드티", "cardigan": "가디건", "vest": "조끼", "jacket": "재킷", "blazer": "블레이저", "coat": "코트",
               "trousers": "바지", "jeans": "청바지", "shorts": "반바지", "skirt": "치마", "dress": "원피스", "jumpsuit": "점프수트",
               "wrap": "랩", "other": "기타"}
MENU = [
    "1. 라벨 올리기 — 옷 라벨(택) 사진을 보내주세요",
    "2. 내 옷장 보기",
    "3. 사진 찍어 올리기 — 라벨 없는 옷은 옷 전체 사진",
    "4. 설정 — 옷 지우기 · 내보내기 · 코디 추천(\"오늘 뭐 입지?\")",
]
CONTROL = re.compile(r"[\u0000-\u001f\u007f-\u009f‪-‮⁦-⁩]")
UNSAFE = re.compile(r"[<>]|(?:https?|ftp|file|javascript|data):|(?:^|\s)www\.", re.I)
SCHEMA = """
CREATE TABLE IF NOT EXISTS garments (
  id          TEXT PRIMARY KEY NOT NULL,          -- permanent random id
  no          INTEGER NOT NULL UNIQUE,            -- closet number #1, #2 ... never reused
  kind        TEXT NOT NULL CHECK (kind IN ('label','visual')),
  record_json TEXT NOT NULL,
  created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now')),
  removed_at  TEXT                                -- removal keeps the row, so numbers stay unique
);
"""


class Invalid(Exception):
    pass


def db_path():
    return Path(os.environ.get("MY_CLOSET_DB") or Path.home() / ".my-closet" / "closet.db")


def connect():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def label_value(key, text):
    if not isinstance(text, str) or len(text) > LABEL[key] or CONTROL.search(text):
        raise Invalid(f"{key} must be one short line of label text.")
    value = " ".join(unicodedata.normalize("NFKC", text).split())
    if not value or UNSAFE.search(value):
        raise Invalid(f"{key} must be plain label text, with no links, markup or image data.")
    if key == "gtin":
        if not re.fullmatch(r"\d{8}|\d{12,14}", value):
            raise Invalid("gtin must be 8, 12, 13 or 14 digits.")
        total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(value[:-1])))
        if (total + int(value[-1])) % 10:
            raise Invalid("gtin checksum does not match; leave it out.")
    return value


def normalize(kind, fields):
    if kind not in ("label", "visual"):
        raise Invalid("kind must be label or visual.")
    keys = LABEL_KEYS if kind == "label" else VISUAL_KEYS
    if not isinstance(fields, dict) or any(k not in keys for k in fields):
        raise Invalid(f"fields may only contain: {', '.join(keys)}.")
    out = {}
    for key in keys:
        value = fields.get(key)
        if value is None or value == "" or value == []:
            continue
        if key == "category" or (kind == "visual" and key in VISUAL):
            if value not in VISUAL[key]:
                raise Invalid(f"{key} must be one of: {' '.join(VISUAL[key])}.")
            out[key] = value
        elif key == "details":
            if not isinstance(value, list) or len(value) > 6 or len(set(value)) != len(value) or any(v not in DETAILS for v in value):
                raise Invalid("details must be up to six different codes from: " + " ".join(DETAILS))
            out[key] = value
        else:
            out[key] = label_value(key, value)
    if not out:
        raise Invalid("Give at least one field you could actually read.")
    return out


def describe(kind, fields):
    if kind == "label":
        parts = [fields.get("brand"), fields.get("product"), KO_CATEGORY.get(fields.get("category"), fields.get("category")),
                 fields.get("size") and "사이즈 " + fields["size"], fields.get("color"), fields.get("sku") and "품번 " + fields["sku"]]
    else:
        parts = [fields.get("color"), KO_CATEGORY.get(fields.get("category"), fields.get("category")), fields.get("pattern"), fields.get("length")]
    return " · ".join(p for p in parts if p) or "옷"


def item(row):
    fields = json.loads(row["record_json"])
    return {"no": row["no"], "id": row["id"], "kind": row["kind"], "fields": fields,
            "summary": describe(row["kind"], fields), "created_at": row["created_at"]}


def count(con):
    return con.execute("SELECT COUNT(*) FROM garments WHERE removed_at IS NULL").fetchone()[0]


def guide(n):
    head = f"👕 내 옷장 ({n}벌)\n" + ("아직 비어 있어요. " if n == 0 else "") + "무엇을 할까요? 번호로 말해주세요."
    return "\n".join([head, *MENU, "📷 사진은 저장하지 않아요. 읽은 정보만 글로 저장돼요."])


def cmd_status(con, _args):
    n = count(con)
    return {"ok": True, "garment_count": n, "db": str(db_path()), "guide": guide(n)}


def cmd_list(con, args):
    limit = max(1, min(args.limit, 500))
    rows = con.execute("SELECT * FROM garments WHERE removed_at IS NULL ORDER BY no DESC LIMIT ?", (limit,)).fetchall()
    return {"ok": True, "garment_count": count(con), "items": [item(r) for r in rows]}


def cmd_add(con, args):
    try:
        payload = json.loads(args.json)
    except json.JSONDecodeError:
        raise Invalid("add takes one JSON object, e.g. '{\"kind\":\"label\",\"fields\":{\"brand\":\"UNIQLO\"}}'.")
    items = payload if isinstance(payload, list) else [payload]
    if not items or len(items) > 50 or any(not isinstance(p, dict) or set(p) - {"kind", "fields"} for p in items):
        raise Invalid("add takes an object {kind, fields} or a list of up to 50 of them.")
    prepared = [(p.get("kind"), normalize(p.get("kind"), p.get("fields"))) for p in items]
    saved = []
    with con:  # all garments in one call are saved together, or none are
        for kind, fields in prepared:
            # Removed garments keep their row, so MAX(no) + 1 never hands out a number twice.
            no = con.execute("SELECT COALESCE(MAX(no), 0) + 1 FROM garments").fetchone()[0]
            gid = str(uuid.uuid4())
            con.execute("INSERT INTO garments (id, no, kind, record_json) VALUES (?, ?, ?, ?)",
                        (gid, no, kind, json.dumps(fields, ensure_ascii=False, separators=(",", ":"))))
            saved.append(item(con.execute("SELECT * FROM garments WHERE id = ?", (gid,)).fetchone()))
    return {"ok": True, "saved": saved, "garment_count": count(con), "guide": guide(count(con))}


def cmd_remove(con, args):
    with con:
        cur = con.execute("UPDATE garments SET removed_at = strftime('%Y-%m-%d %H:%M:%S','now') WHERE no = ? AND removed_at IS NULL", (args.no,))
    if cur.rowcount != 1:
        raise Invalid(f"#{args.no} is not in the closet.")
    return {"ok": True, "removed": args.no, "garment_count": count(con), "note": "번호는 다시 쓰지 않아요."}


def cmd_export(con, args):
    rows = [item(r) for r in con.execute("SELECT * FROM garments WHERE removed_at IS NULL ORDER BY no").fetchall()]
    if args.format == "csv":
        buf = io.StringIO()
        keys = LABEL_KEYS + [k for k in VISUAL_KEYS if k not in LABEL_KEYS]
        w = csv.writer(buf)
        w.writerow(["no", "kind", "created_at", *keys])
        for r in rows:
            w.writerow([r["no"], r["kind"], r["created_at"], *[(" ".join(v) if isinstance(v := r["fields"].get(k), list) else v or "") for k in keys]])
        return {"ok": True, "format": "csv", "data": buf.getvalue()}
    return {"ok": True, "format": "json", "items": rows}


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="closet", description="My Closet local wardrobe database")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    p = sub.add_parser("list"); p.add_argument("--limit", type=int, default=100)
    p = sub.add_parser("add"); p.add_argument("json")
    p = sub.add_parser("remove"); p.add_argument("no", type=int)
    p = sub.add_parser("export"); p.add_argument("--format", choices=["json", "csv"], default="json")
    args = parser.parse_args(argv)
    commands = {"status": cmd_status, "list": cmd_list, "add": cmd_add, "remove": cmd_remove, "export": cmd_export}
    try:
        con = connect()
        try:
            result = commands[args.command](con, args)
        finally:
            con.close()
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Invalid as error:
        print(json.dumps({"ok": False, "error": "invalid", "message": str(error), "saved": False}, ensure_ascii=False))
        return 2
    except sqlite3.Error as error:
        print(json.dumps({"ok": False, "error": "database", "message": str(error), "saved": False}, ensure_ascii=False))
        return 3


if __name__ == "__main__":
    sys.exit(main())
