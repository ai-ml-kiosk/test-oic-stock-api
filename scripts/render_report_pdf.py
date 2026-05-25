#!/usr/bin/env python3
"""Render the PDCA markdown report as a simple dependency-free PDF."""

from __future__ import annotations

import argparse
import re
import textwrap
from pathlib import Path


PAGE_WIDTH = 612
PAGE_HEIGHT = 792
MARGIN_X = 54
MARGIN_TOP = 58
MARGIN_BOTTOM = 54
BODY_FONT_SIZE = 10
BODY_LEADING = 14
MONO_FONT_SIZE = 8
MONO_LEADING = 11


def parse_markdown(markdown: str) -> list[dict]:
    blocks: list[dict] = []
    in_code = False
    code_lines: list[str] = []

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            if in_code:
                blocks.append({"type": "code", "lines": code_lines})
                code_lines = []
            in_code = not in_code
            continue
        if in_code:
            code_lines.append(line)
            continue

        if not line:
            blocks.append({"type": "space"})
        elif line.startswith("# "):
            blocks.append({"type": "h1", "text": line[2:].strip()})
        elif line.startswith("## "):
            blocks.append({"type": "h2", "text": line[3:].strip()})
        elif line.startswith("### "):
            blocks.append({"type": "h3", "text": line[4:].strip()})
        elif line.startswith(">"):
            blocks.append({"type": "quote", "text": clean_inline(line.lstrip("> ").strip())})
        elif line.startswith("- [x] "):
            blocks.append({"type": "bullet", "text": "[x] " + clean_inline(line[6:].strip())})
        elif line.startswith("- [ ] "):
            blocks.append({"type": "bullet", "text": "[ ] " + clean_inline(line[6:].strip())})
        elif line.startswith("- "):
            blocks.append({"type": "bullet", "text": clean_inline(line[2:].strip())})
        elif line.startswith("|") and line.endswith("|"):
            cells = [clean_inline(cell.strip()) for cell in line.strip("|").split("|")]
            if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                blocks.append({"type": "table", "cells": cells})
        elif re.match(r"^\d+\. ", line):
            blocks.append({"type": "number", "text": clean_inline(line.strip())})
        else:
            blocks.append({"type": "para", "text": clean_inline(line)})

    return blocks


def clean_inline(text: str) -> str:
    text = text.replace("`", "")
    text = text.replace("[x]", "[done]")
    text = text.replace("[ ]", "[todo]")
    text = text.replace("\\", "\\\\")
    return text


def wrap_text(text: str, max_chars: int) -> list[str]:
    if not text:
        return [""]
    return textwrap.wrap(text, width=max_chars, break_long_words=False, replace_whitespace=False) or [text]


class PdfWriter:
    def __init__(self, title: str):
        self.title = title
        self.pages: list[list[tuple]] = []
        self.current: list[tuple] = []
        self.y = PAGE_HEIGHT - MARGIN_TOP
        self.page_no = 0
        self.new_page()

    def new_page(self) -> None:
        if self.current:
            self.pages.append(self.current)
        self.page_no += 1
        self.current = []
        self.y = PAGE_HEIGHT - MARGIN_TOP
        self.text(self.title, MARGIN_X, PAGE_HEIGHT - 30, 9, "Helvetica-Bold")
        self.text(f"Page {self.page_no}", PAGE_WIDTH - MARGIN_X - 35, 30, 8, "Helvetica")

    def ensure(self, needed: int) -> None:
        if self.y - needed < MARGIN_BOTTOM:
            self.new_page()

    def text(self, text: str, x: int, y: int, size: int, font: str) -> None:
        self.current.append(("text", x, y, size, font, text))

    def line(self, x1: int, y1: int, x2: int, y2: int) -> None:
        self.current.append(("line", x1, y1, x2, y2))

    def write_block(self, block: dict) -> None:
        kind = block["type"]
        if kind == "space":
            self.y -= 6
            return
        if kind == "h1":
            self.ensure(34)
            self.text(block["text"], MARGIN_X, self.y, 18, "Helvetica-Bold")
            self.y -= 14
            self.line(MARGIN_X, self.y, PAGE_WIDTH - MARGIN_X, self.y)
            self.y -= 16
            return
        if kind == "h2":
            self.ensure(28)
            self.y -= 4
            self.text(block["text"], MARGIN_X, self.y, 14, "Helvetica-Bold")
            self.y -= 20
            return
        if kind == "h3":
            self.ensure(22)
            self.text(block["text"], MARGIN_X, self.y, 11, "Helvetica-Bold")
            self.y -= 17
            return
        if kind == "quote":
            self._write_wrapped(block["text"], 82, BODY_FONT_SIZE, "Helvetica-Oblique", prefix="")
            return
        if kind == "bullet":
            self._write_wrapped(block["text"], 82, BODY_FONT_SIZE, "Helvetica", prefix="- ")
            return
        if kind == "number":
            self._write_wrapped(block["text"], 82, BODY_FONT_SIZE, "Helvetica", prefix="")
            return
        if kind == "code":
            for line in block["lines"]:
                self._write_wrapped(line, 96, MONO_FONT_SIZE, "Courier", prefix="")
            self.y -= 4
            return
        if kind == "table":
            self._write_wrapped(" | ".join(block["cells"]), 88, MONO_FONT_SIZE, "Courier", prefix="")
            return
        self._write_wrapped(block["text"], 88, BODY_FONT_SIZE, "Helvetica", prefix="")

    def _write_wrapped(self, text: str, width: int, size: int, font: str, prefix: str = "") -> None:
        lines = wrap_text(text, width)
        leading = MONO_LEADING if font == "Courier" else BODY_LEADING
        self.ensure(leading * len(lines) + 2)
        for index, line in enumerate(lines):
            left = MARGIN_X + (14 if prefix and index > 0 else 0)
            rendered = prefix + line if index == 0 else line
            self.text(rendered, left, self.y, size, font)
            self.y -= leading

    def finish(self) -> None:
        if self.current:
            self.pages.append(self.current)
            self.current = []

    def write_pdf(self, path: Path) -> None:
        self.finish()
        objects: list[bytes] = []

        def add_object(data: bytes) -> int:
            objects.append(data)
            return len(objects)

        font_helv = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        font_bold = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
        font_oblique = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique >>")
        font_courier = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")

        page_refs = []
        for page in self.pages:
            content = render_page(page)
            content_ref = add_object(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"endstream")
            page_ref = add_object(
                f"<< /Type /Page /Parent {{PAGES}} 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                f"/Resources << /Font << /F1 {font_helv} 0 R /F2 {font_bold} 0 R /F3 {font_oblique} 0 R /F4 {font_courier} 0 R >> >> "
                f"/Contents {content_ref} 0 R >>".encode()
            )
            page_refs.append(page_ref)

        kids = " ".join(f"{ref} 0 R" for ref in page_refs)
        pages_ref = add_object(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_refs)} >>".encode())
        catalog_ref = add_object(f"<< /Type /Catalog /Pages {pages_ref} 0 R >>".encode())

        patched = [obj.replace(b"{PAGES}", str(pages_ref).encode()) for obj in objects]
        write_pdf_bytes(path, patched, catalog_ref)


def render_page(commands: list[tuple]) -> bytes:
    out = ["q\n"]
    for command in commands:
        if command[0] == "text":
            _, x, y, size, font, text = command
            font_id = {"Helvetica": "F1", "Helvetica-Bold": "F2", "Helvetica-Oblique": "F3", "Courier": "F4"}[font]
            out.append(f"BT /{font_id} {size} Tf {x} {y} Td ({escape_pdf_text(text)}) Tj ET\n")
        elif command[0] == "line":
            _, x1, y1, x2, y2 = command
            out.append(f"{x1} {y1} m {x2} {y2} l S\n")
    out.append("Q\n")
    return "".join(out).encode("latin-1", errors="replace")


def escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_pdf_bytes(path: Path, objects: list[bytes], catalog_ref: int) -> None:
    offsets = [0]
    output = bytearray(b"%PDF-1.4\n")
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode())
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_ref} 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode()
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--title", default="OIC Stock Alert Completion Report")
    args = parser.parse_args()

    markdown = args.source.read_text(encoding="utf-8")
    writer = PdfWriter(args.title)
    for block in parse_markdown(markdown):
        writer.write_block(block)
    writer.write_pdf(args.target)


if __name__ == "__main__":
    main()
