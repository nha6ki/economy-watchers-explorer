"""Regression checks for the public snapshot and generated output."""

from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import unittest
from xml.etree import ElementTree
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.ids = []
        self.classes = Counter()
        self.scripts = []
        self.local_links = []
        self.feed(path.read_text(encoding="utf-8"))

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        self.classes.update(attrs.get("class", "").split())
        if tag == "script":
            self.scripts.append(attrs)
        for key in ("href", "src"):
            url = attrs.get(key, "")
            if url and not url.startswith(("#", "https://")):
                self.local_links.append(url)


class PublicBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.responses = build.load("responses.json")
        cls.rows = {r["id"]: r for r in cls.responses["answers"]}
        cls.findings = build.load("findings.json")
        cls.labels = build.load("labels.en.json")
        build.build()

    def test_snapshot(self):
        self.assertEqual(len(self.responses["answers"]), 2513)
        self.assertEqual(len(self.rows), 2513)
        self.assertEqual(len(self.findings), 6)
        groups = {(r["k"], r["s"], r["b"]) for r in self.rows.values()}
        seen = set()
        total = 0
        for group in self.findings:
            for industry in group["industries"]:
                key = (group["period"], group["sector"], industry["name"])
                self.assertNotIn(key, seen)
                seen.add(key)
                for finding in industry["findings"]:
                    total += 1
                    self.assertTrue(finding["en"] and finding["ja"] and finding["evidence"])
                    for ref in finding["evidence"]:
                        row = self.rows[ref["id"]]
                        self.assertEqual((row["k"], row["s"], row["b"]), key)
                        build.evidence_excerpt(row["text"], ref["spans"])
        self.assertEqual(seen, groups)
        self.assertEqual(len(seen), 412)
        self.assertEqual(total, 618)
        theme_keys = set(self.responses["themes"])
        self.assertEqual(theme_keys, set(self.labels["themes"]))
        for row in self.rows.values():
            for theme, topic, quote in row["ev"]:
                self.assertIn(theme, theme_keys)
                self.assertTrue(topic and quote)
                self.assertIn(quote, row["text"])
            for field, key in (("b", "industries"), ("region", "regions"), ("k", "periods"),
                               ("s", "sectors"), ("jud", "judgments")):
                self.assertIn(row[field], self.labels[key])

    def test_pages_and_reproducible_build(self):
        def digests():
            return {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in build.OUTPUT.iterdir() if f.is_file()}

        for name in ("index.html", "ja.html"):
            page = Page(build.OUTPUT / name)
            self.assertEqual(len(page.ids), len(set(page.ids)))
            self.assertEqual(page.classes["industry"], 412)
            self.assertEqual(page.classes["gemma-finding"], 618)
            self.assertEqual(page.classes["evidence-row"], 719)
            self.assertTrue(all((build.OUTPUT / url).is_file() for url in page.local_links))
            self.assertTrue(all("src" in s or s.get("type") == "application/json" for s in page.scripts))
        old = digests()
        subprocess.run([sys.executable, str(ROOT / "scripts/build.py")], cwd=ROOT.parent, check=True)
        self.assertEqual(old, digests())

    def test_safe_embedded_data(self):
        payload = {"text": "</script><script>alert(1)</script>"}
        tag = build.json_script("db", payload)
        self.assertEqual(tag.count("</script>"), 1)
        self.assertEqual(json.loads(tag.split(">", 1)[1].rsplit("<", 1)[0]), payload)
        self.assertEqual(build.evidence_excerpt("・<b>&", [[1, 4]]), "<mark>&lt;b&gt;</mark>&amp;")

    def test_workbook(self):
        workbook = build.DATA / "all-industry-themes.xlsx"
        self.assertEqual(workbook.read_bytes(), (build.OUTPUT / workbook.name).read_bytes())
        with ZipFile(workbook) as z:
            for name in z.namelist():
                self.assertNotRegex(name, r"(?i)(externalLinks|vbaProject|embeddings|connections|comments|person)")
                if name.endswith(".rels"):
                    links = ElementTree.fromstring(z.read(name))
                    self.assertFalse(any(link.get("TargetMode") == "External" for link in links))
                if name.startswith("xl/worksheets/") and name.endswith(".xml"):
                    sheet = ElementTree.fromstring(z.read(name))
                    self.assertFalse(any(node.tag.endswith("}f") for node in sheet.iter()))
            props = ElementTree.fromstring(z.read("docProps/core.xml"))
            self.assertFalse(any((n.text or "").strip() for n in props if n.tag.endswith(("}creator", "}lastModifiedBy"))))


if __name__ == "__main__":
    unittest.main()
