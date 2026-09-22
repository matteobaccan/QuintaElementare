#!/usr/bin/env python3
"""Redraw handwritten lesson notes as a clean poster.

Reads a structured appunti JSON and writes, next to it:
    Appunti-<Title>.pdf   the redrawn poster
    Appunti-<Title>.png   the same poster as an image (the improved picture)
    appunti.md            the same content as markdown

Usage:
    python build_appunti.py appunti.json
    python build_appunti.py appunti.json --dpi 220 --no-png --no-md
"""

import argparse
import json
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, KeepTogether,
                                ListFlowable, ListItem, PageTemplate, Paragraph,
                                Spacer, Table, TableStyle)

# Highlighter colours, in the order sections use them.
PALETTE = ["#17B8C4", "#8BC34A", "#FFD54F", "#F06292", "#9575CD", "#FF8A65"]
HIGHLIGHT = "#FFF3A3"
INK = "#1A1A2E"
MUTED = "#5A5A6E"


# --------------------------------------------------------------------------
# inline markup
# --------------------------------------------------------------------------

def tint(hex_color, strength=0.18):
    """A pale wash of a colour - reportlab has no alpha in HexColor, and an
    8-digit '#RRGGBBAA' string is silently parsed as a 32-bit RGB integer."""
    c = colors.HexColor(hex_color)
    return colors.Color(1 - (1 - c.red) * strength,
                        1 - (1 - c.green) * strength,
                        1 - (1 - c.blue) * strength)


def rl(text):
    """Escape for reportlab and turn **bold** into a highlighted run."""
    out = escape(str(text))
    return re.sub(r"\*\*(.+?)\*\*",
                  lambda m: '<b><font backcolor="%s">%s</font></b>'
                            % (HIGHLIGHT, m.group(1)),
                  out)


def plain(text):
    """Strip inline markup, for measuring and for diagram boxes."""
    return re.sub(r"\*\*(.+?)\*\*", r"\1", str(text))


# --------------------------------------------------------------------------
# the arrow diagram - this is what "redrawing" actually means
# --------------------------------------------------------------------------

class FlowDiagram(Flowable):
    """A row of rounded boxes joined by arrows, like a hand-drawn sequence."""

    PAD = 5
    FONT = "Helvetica-Bold"
    SIZE = 7.5
    LEADING = 9.5
    ARROW = 16
    MIN_H = 30

    def __init__(self, steps, color):
        Flowable.__init__(self)
        self.steps = [plain(s) for s in steps]
        self.color = colors.HexColor(color)
        self.width = 0
        self.height = self.MIN_H
        self._lines = []

    def _wrap_box(self, text, box_w):
        avail = box_w - 2 * self.PAD
        words, lines, cur = text.split(), [], ""
        for w in words:
            trial = (cur + " " + w).strip()
            if stringWidth(trial, self.FONT, self.SIZE) <= avail or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    def wrap(self, avail_w, avail_h):
        n = len(self.steps)
        self.width = avail_w
        self.box_w = (avail_w - (n - 1) * self.ARROW) / float(n)
        self._lines = [self._wrap_box(s, self.box_w) for s in self.steps]
        rows = max(len(l) for l in self._lines)
        self.height = max(self.MIN_H, rows * self.LEADING + 2 * self.PAD + 4)
        return avail_w, self.height

    def draw(self):
        c = self.canv
        y, h = 0, self.height
        x = 0
        for i, lines in enumerate(self._lines):
            c.setFillColor(self.color)
            c.setFillAlpha(0.16)
            c.roundRect(x, y, self.box_w, h, 5, stroke=0, fill=1)
            c.setFillAlpha(1)
            c.setStrokeColor(self.color)
            c.setLineWidth(1.1)
            c.roundRect(x, y, self.box_w, h, 5, stroke=1, fill=0)

            c.setFillColor(colors.HexColor(INK))
            c.setFont(self.FONT, self.SIZE)
            block_h = len(lines) * self.LEADING
            ty = y + (h + block_h) / 2.0 - self.LEADING + 2
            for line in lines:
                c.drawCentredString(x + self.box_w / 2.0, ty, line)
                ty -= self.LEADING

            if i < len(self._lines) - 1:
                ax, ay = x + self.box_w, y + h / 2.0
                c.setStrokeColor(self.color)
                c.setLineWidth(1.6)
                c.line(ax + 3, ay, ax + self.ARROW - 6, ay)
                c.setFillColor(self.color)
                p = c.beginPath()
                p.moveTo(ax + self.ARROW - 2, ay)
                p.lineTo(ax + self.ARROW - 8, ay + 3.4)
                p.lineTo(ax + self.ARROW - 8, ay - 3.4)
                p.close()
                c.drawPath(p, stroke=0, fill=1)
            x += self.box_w + self.ARROW


class Rule(Flowable):
    """A thin coloured rule under a section heading."""

    def __init__(self, color, thickness=1.4):
        Flowable.__init__(self)
        self.color, self.thickness, self.width = color, thickness, 0
        self.height = thickness + 3

    def wrap(self, avail_w, avail_h):
        self.width = avail_w
        return avail_w, self.height

    def draw(self):
        self.canv.setStrokeColor(colors.HexColor(self.color))
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 1, self.width, 1)


# --------------------------------------------------------------------------
# styles
# --------------------------------------------------------------------------

def make_styles():
    base = getSampleStyleSheet()["Normal"]
    return {
        "h2": ParagraphStyle("h2", base, fontName="Helvetica-Bold", fontSize=11.5,
                             leading=14, textColor=colors.HexColor(INK),
                             spaceBefore=2, spaceAfter=1, keepWithNext=1,
                             borderPadding=(3, 5, 3, 5)),
        "body": ParagraphStyle("body", base, fontSize=8.8, leading=12.2,
                               textColor=colors.HexColor(INK), spaceAfter=4),
        "bullet": ParagraphStyle("bullet", base, fontSize=8.8, leading=12.2,
                                 textColor=colors.HexColor(INK), spaceAfter=1.5),
        "caption": ParagraphStyle("caption", base, fontName="Helvetica-Oblique",
                                  fontSize=7.6, leading=10,
                                  textColor=colors.HexColor(MUTED), spaceAfter=5),
        "cell": ParagraphStyle("cell", base, fontSize=8, leading=10.5,
                               textColor=colors.HexColor(INK)),
        "cellh": ParagraphStyle("cellh", base, fontName="Helvetica-Bold", fontSize=8,
                                leading=10.5, textColor=colors.white),
        "kw": ParagraphStyle("kw", base, fontName="Helvetica-Bold", fontSize=9,
                             leading=15, textColor=colors.HexColor(INK)),
    }


# --------------------------------------------------------------------------
# blocks -> flowables
# --------------------------------------------------------------------------

def block_flowables(block, color, S):
    kind = block.get("type", "text")

    if kind == "text":
        return [Paragraph(rl(block["text"]), S["body"])]

    if kind == "list":
        items = [ListItem(Paragraph(rl(i), S["bullet"]), leftIndent=12)
                 for i in block["items"]]
        return [ListFlowable(items, bulletType="bullet", bulletColor=colors.HexColor(color),
                             bulletFontSize=7, leftIndent=12, start="square"),
                Spacer(1, 4)]

    if kind == "flow":
        out = [FlowDiagram(block["steps"], color), Spacer(1, 3)]
        if block.get("caption"):
            out.append(Paragraph(rl(block["caption"]), S["caption"]))
        return [KeepTogether(out)]

    if kind == "table":
        head = [Paragraph(rl(h), S["cellh"]) for h in block["headers"]]
        rows = [[Paragraph(rl(c), S["cell"]) for c in r] for r in block["rows"]]
        t = Table([head] + rows, hAlign="LEFT", repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(color)),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F6F8")]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D5D7DE")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return [KeepTogether([t, Spacer(1, 6)])]

    if kind == "caption":
        return [Paragraph(rl(block["text"]), S["caption"])]

    sys.exit("Unknown block type: %r" % kind)


def section_flowables(section, color, S):
    head = ParagraphStyle("h", S["h2"], backColor=tint(color, 0.30),
                          borderColor=colors.HexColor(color))
    out = [Paragraph(rl(section["heading"]), head), Rule(color), Spacer(1, 3)]
    for block in section.get("blocks", []):
        out.extend(block_flowables(block, color, S))
    out.append(Spacer(1, 7))
    return out


# --------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------

def build_pdf(data, out_path):
    layout = data.get("layout", {})
    portrait = layout.get("orientation", "landscape") == "portrait"
    ncols = int(layout.get("columns", 1 if portrait else 2))
    pagesize = A4 if portrait else landscape(A4)

    S = make_styles()
    margin, gutter, header_h = 1.2 * cm, 0.8 * cm, 2.1 * cm
    pw, ph = pagesize
    usable_w = pw - 2 * margin
    col_w = (usable_w - gutter * (ncols - 1)) / float(ncols)
    frame_h = ph - 2 * margin - header_h

    frames = [Frame(margin + i * (col_w + gutter), margin, col_w, frame_h,
                    leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                    id="col%d" % i)
              for i in range(ncols)]

    accent = data.get("accent", PALETTE[0])
    title = data["title"]
    subtitle = data.get("subject", "")

    def draw_header(canvas, doc):
        canvas.saveState()
        y = ph - margin - header_h + 0.35 * cm
        canvas.setFillColor(colors.HexColor(accent))
        canvas.setFillAlpha(0.14)
        canvas.roundRect(margin, y, usable_w, header_h - 0.35 * cm, 7, stroke=0, fill=1)
        canvas.setFillAlpha(1)
        canvas.setFillColor(colors.HexColor(accent))
        canvas.roundRect(margin, y, 0.22 * cm, header_h - 0.35 * cm, 2, stroke=0, fill=1)

        canvas.setFillColor(colors.HexColor(INK))
        canvas.setFont("Helvetica-Bold", 19)
        canvas.drawString(margin + 0.65 * cm, y + header_h - 1.25 * cm, title.upper())
        if subtitle:
            canvas.setFont("Helvetica-Oblique", 9)
            canvas.setFillColor(colors.HexColor(MUTED))
            canvas.drawString(margin + 0.67 * cm, y + header_h - 1.72 * cm, subtitle)

        page = canvas.getPageNumber()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#9A9AA8"))
        canvas.drawRightString(pw - margin, margin - 0.45 * cm, str(page))
        canvas.restoreState()

    doc = BaseDocTemplate(str(out_path), pagesize=pagesize,
                          leftMargin=margin, rightMargin=margin,
                          topMargin=margin, bottomMargin=margin,
                          title=title, author="appunti-lezione")
    doc.addPageTemplates([PageTemplate(id="poster", frames=frames, onPage=draw_header)])

    story = []
    for i, section in enumerate(data.get("sections", [])):
        color = section.get("color") or PALETTE[i % len(PALETTE)]
        story.extend(section_flowables(section, color, S))

    keywords = data.get("keywords") or []
    if keywords:
        kw_style = ParagraphStyle("kwbox", S["kw"],
                                  backColor=tint(accent, 0.16),
                                  borderColor=colors.HexColor(accent),
                                  borderWidth=1, borderPadding=(6, 7, 6, 7),
                                  borderRadius=5)
        label = data.get("keywords_label", "KEYWORDS")
        body = ("&nbsp;&nbsp;<font color='%s'>&bull;</font>&nbsp;&nbsp;" % accent).join(
            escape(k) for k in keywords)
        story.append(Paragraph("<font color='%s'>%s</font><br/>%s"
                               % (accent, escape(label), body), kw_style))

    doc.build(story)
    return out_path


# --------------------------------------------------------------------------
# PNG
# --------------------------------------------------------------------------

def build_png(pdf_path, png_path, dpi):
    try:
        import fitz
    except ImportError:
        sys.exit("PNG output needs PyMuPDF: pip install pymupdf (or pass --no-png)")

    written = []
    with fitz.open(str(pdf_path)) as doc:
        for i, page in enumerate(doc):
            target = png_path if i == 0 else \
                png_path.with_name("%s-%d.png" % (png_path.stem, i + 1))
            page.get_pixmap(dpi=dpi).save(str(target))
            written.append(target)
    return written


# --------------------------------------------------------------------------
# markdown
# --------------------------------------------------------------------------

def build_md(data, out_path):
    lines = ["# %s" % data["title"], ""]
    if data.get("subject"):
        lines += ["*%s*" % data["subject"], ""]

    for section in data.get("sections", []):
        lines += ["## %s" % section["heading"], ""]
        for block in section.get("blocks", []):
            kind = block.get("type", "text")
            if kind == "text":
                lines += [block["text"], ""]
            elif kind == "list":
                lines += ["- %s" % i for i in block["items"]] + [""]
            elif kind == "flow":
                lines += ["```mermaid", "flowchart LR"]
                for i, step in enumerate(block["steps"]):
                    node = plain(step).replace('"', "'")
                    lines.append('    S%d["%s"]' % (i, node))
                if len(block["steps"]) > 1:
                    lines.append("    " + " --> ".join(
                        "S%d" % i for i in range(len(block["steps"]))))
                lines += ["```", ""]
                if block.get("caption"):
                    lines += ["*%s*" % block["caption"], ""]
            elif kind == "table":
                lines.append("| " + " | ".join(block["headers"]) + " |")
                lines.append("|" + "---|" * len(block["headers"]))
                for row in block["rows"]:
                    lines.append("| " + " | ".join(row) + " |")
                lines.append("")
            elif kind == "caption":
                lines += ["*%s*" % block["text"], ""]

    if data.get("keywords"):
        lines += ["## %s" % data.get("keywords_label", "Keywords"), "",
                  " · ".join(data["keywords"]), ""]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


# --------------------------------------------------------------------------

def slugify(text):
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip()
    return re.sub(r"[\s_-]+", "-", text) or "appunti"


def load(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not data.get("title"):
        sys.exit("Invalid notes file: missing 'title'")
    if not data.get("sections"):
        sys.exit("Invalid notes file: 'sections' is empty")
    for i, s in enumerate(data["sections"], 1):
        if not s.get("heading"):
            sys.exit("Invalid notes file: sections[%d] has no 'heading'" % i)
    return data


def main():
    ap = argparse.ArgumentParser(
        description="Redraw lesson notes as a poster (PDF + PNG) and markdown.")
    ap.add_argument("notes_json", help="path to the appunti JSON file")
    ap.add_argument("-o", "--output", help="output .pdf path")
    ap.add_argument("--dpi", type=int, default=200, help="PNG resolution (default 200)")
    ap.add_argument("--no-png", action="store_true", help="skip the PNG")
    ap.add_argument("--no-md", action="store_true", help="skip the markdown")
    args = ap.parse_args()

    src = Path(args.notes_json)
    data = load(src)

    pdf_path = Path(args.output) if args.output else \
        src.parent / ("Appunti-%s.pdf" % slugify(data["title"]))
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    build_pdf(data, pdf_path)
    print("PDF: %s" % pdf_path)

    if not args.no_png:
        for p in build_png(pdf_path, pdf_path.with_suffix(".png"), args.dpi):
            print("PNG: %s" % p)

    if not args.no_md:
        print("MD:  %s" % build_md(data, src.parent / "appunti.md"))


if __name__ == "__main__":
    main()
