"""Render the innovation brief to PDF (reportlab). All content comes from the brief data structure."""
from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY = colors.HexColor("#0B1B33")
BLUE = colors.HexColor("#2563EB")
MUTED = colors.HexColor("#5B6B82")


def _p(text: object, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(text or "")), style)


def render_pdf(brief: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title=brief["title"], author="Virtual Science Park")
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=NAVY, fontSize=20, leading=24, alignment=0)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=NAVY, fontSize=13, spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("body", parent=ss["BodyText"], fontSize=9.5, leading=13)
    small = ParagraphStyle("small", parent=body, fontSize=8, leading=10.5, textColor=MUTED)
    tag = ParagraphStyle("tag", parent=small, textColor=BLUE)

    story: list = [
        _p("VIRTUAL SCIENCE PARK · Discover. Connect. Innovate.", tag),
        _p(brief["title"], h1),
        _p(f"Generated {brief['generated_at']} UTC · {brief['data_freshness']} · Membership: {brief['company']['membership_status']}", small),
        Spacer(1, 6),
    ]
    es = brief["executive_summary"]
    story += [_p("Executive summary", h2), _p(es["headline"], body)]
    story.append(ListFlowable([ListItem(_p(b, body)) for b in es["bullets"]], bulletType="bullet", leftIndent=12))
    if es.get("llm", {}).get("used"):
        story.append(_p("Summary wording assisted by an LLM and checked against the underlying facts.", small))

    story.append(_p("Company profile (evidence-backed)", h2))
    for c in brief["profile"]:
        marker = {"source_stated": "Source", "inferred": "Inferred", "user_provided": "User"}[c["claim_type"]]
        ref = f" [E{c['evidence_id']}]" if c["evidence_id"] else ""
        story.append(_p(f"{c['field'].replace('_', ' ').title()} — {c['label']}: {c['value']} ({marker}{ref})", body))

    story.append(_p("Most relevant opportunities", h2))
    if brief["opportunities"]:
        rows = [["Opportunity", "Score", "Deadline", "Why"]]
        for o in brief["opportunities"]:
            rows.append([_p(f"{o['title']} ({o['organisation']}) [E{o['evidence_id']}]", small), str(o["score"]), o["deadline"],
                         _p(" ".join(o["why"]), small)])
        t = Table(rows, colWidths=[62 * mm, 14 * mm, 24 * mm, 72 * mm], repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                               ("FONTSIZE", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1"))]))
        story.append(t)
        story.append(_p("Eligibility is not assessed by VSP; confirm on the official call page.", small))
    else:
        story.append(_p("No open opportunity reached the relevance threshold in the collected data.", body))

    story.append(_p("Emerging technology recommendations", h2))
    for t in brief["technologies"]:
        story.append(_p(f"{t['name']} — ring: {t['ring']} ({t['relation']}). {t['application'] or ''} Next: {t['next_step']}", body))

    story.append(_p("Potential collaboration partners", h2))
    for p in brief["partners"]:
        story.append(_p(f"{p['name']} ({p['strength']}, potential — not an existing partnership): {' '.join(p['why'])} "
                        f"Scenario: {p['scenario']} First step: {p['first_step']}", body))

    story.append(_p("Prioritised actions", h2))
    for a in brief["actions"]:
        story.append(_p(f"[{a['tier'].upper()}] {a['title']} — {a['next_step'] or ''}", body))

    story.append(_p("Source references", h2))
    for e in brief["evidence"]:
        story.append(_p(f"[E{e['id']}] {e['publisher']}: {e['title']} — {e['url']} (retrieved {e['retrieved_at']}, {e['provenance']})", small))

    story.append(_p("Data limitations", h2))
    for lim in brief["limitations"]:
        story.append(_p(f"• {lim}", small))
    doc.build(story)
    return buf.getvalue()
