"""
PDF report generator for the HPC Diagnostic Tool.
Produces the same executive-grade layout as the sample report.
"""
from __future__ import annotations
import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak,
    Table, TableStyle, Image, NextPageTemplate
)
from reportlab.pdfgen import canvas

from .config_loader import HPCConfig, PILLARS
from .engine import AnalysisResult
from . import charts

# Colours
NAVY = colors.HexColor("#1F3864")
NAVY_LIGHT = colors.HexColor("#D9E2F3")
GOLD = colors.HexColor("#BF9000")
GREY_LIGHT = colors.HexColor("#F2F2F2")
GREY_MID = colors.HexColor("#8C8C8C")
GREY_BORDER = colors.HexColor("#BFBFBF")
RED = colors.HexColor("#C00000")
GREEN = colors.HexColor("#548235")
AMBER = colors.HexColor("#ED7D31")


def _styles():
    ss = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("H1", parent=ss["Normal"], fontName="Helvetica-Bold",
                             fontSize=18, leading=22, textColor=NAVY, spaceAfter=10),
        "h2": ParagraphStyle("H2", parent=ss["Normal"], fontName="Helvetica-Bold",
                             fontSize=13, leading=17, textColor=NAVY, spaceBefore=10, spaceAfter=6),
        "h3": ParagraphStyle("H3", parent=ss["Normal"], fontName="Helvetica-Bold",
                             fontSize=11, leading=14, textColor=colors.HexColor("#333333"),
                             spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle("Body", parent=ss["Normal"], fontName="Helvetica",
                               fontSize=10.5, leading=15, alignment=TA_JUSTIFY,
                               spaceAfter=6, textColor=colors.HexColor("#222222")),
        "bullet": ParagraphStyle("Bul", parent=ss["Normal"], fontName="Helvetica",
                                 fontSize=10.5, leading=15, leftIndent=14,
                                 spaceAfter=3, textColor=colors.HexColor("#222222")),
        "small": ParagraphStyle("Small", parent=ss["Normal"], fontName="Helvetica",
                                fontSize=8.5, leading=11, textColor=GREY_MID),
        "cell": ParagraphStyle("Cell", parent=ss["Normal"], fontName="Helvetica",
                               fontSize=9, leading=12, textColor=colors.HexColor("#222222"),
                               alignment=TA_LEFT),
        "cell_bold_gold": ParagraphStyle("CellB", parent=ss["Normal"], fontName="Helvetica-Bold",
                                         fontSize=9.5, leading=12, textColor=colors.HexColor("#7F6000")),
        "callout_title": ParagraphStyle("CT", parent=ss["Normal"], fontName="Helvetica-Bold",
                                        fontSize=11, leading=14, textColor=NAVY, spaceAfter=4),
    }


def _callout(styles, title: str, body_text: str):
    inner = [Paragraph(title, styles["callout_title"]),
             Paragraph(body_text, styles["body"])]
    tbl = Table([[inner]], colWidths=[16.5 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY_LIGHT),
        ("LINEBEFORE", (0, 0), (0, -1), 3, NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return tbl


def _draw_page_frame(focus_name: str, analysis_date: str):
    def _draw(c: canvas.Canvas, doc):
        w, h = A4
        c.setFillColor(NAVY)
        c.rect(0, h - 0.9 * cm, w, 0.9 * cm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(1.5 * cm, h - 0.58 * cm, "HIGH PERFORMANCE CULTURE DIAGNOSTIC REPORT")
        c.setFont("Helvetica", 8)
        c.drawRightString(w - 1.5 * cm, h - 0.58 * cm, "CONFIDENTIAL")
        c.setFillColor(GREY_MID)
        c.setFont("Helvetica", 8)
        c.drawString(1.5 * cm, 1.0 * cm,
                     f"Department focus: {focus_name}  ·  Analysis date: {analysis_date}")
        c.drawRightString(w - 1.5 * cm, 1.0 * cm, f"Page {doc.page}")
    return _draw


def _draw_cover():
    def _draw(c: canvas.Canvas, doc):
        w, h = A4
        c.setFillColor(NAVY)
        c.rect(0, h - 8.0 * cm, w, 8.0 * cm, stroke=0, fill=1)
        c.setFillColor(GOLD)
        c.rect(0, h - 8.2 * cm, w, 0.2 * cm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 30)
        c.drawString(1.8 * cm, h - 3.5 * cm, "High Performance Culture")
        c.setFont("Helvetica-Bold", 26)
        c.drawString(1.8 * cm, h - 4.7 * cm, "Diagnostic Report")
        c.setFont("Helvetica", 13)
        c.setFillColor(colors.HexColor("#D9E2F3"))
        c.drawString(1.8 * cm, h - 6.0 * cm, "Powered by the PERILL framework")
        c.setFont("Helvetica-Oblique", 11)
        c.drawString(1.8 * cm, h - 6.7 * cm, "Purpose  ·  Partnership  ·  Processes  ·  Excellence")
        c.setFillColor(NAVY)
        c.rect(0, 0, w, 1.4 * cm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica", 8.5)
        c.drawString(1.8 * cm, 0.5 * cm, "Prepared by Organization Development — Culture")
        c.drawRightString(w - 1.8 * cm, 0.5 * cm, "Confidential")
    return _draw


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def build_pdf(analysis: AnalysisResult,
              cfg: HPCConfig,
              output_path: str,
              prepared_by: str = "Organization Development — Culture",
              analysis_date: str | None = None) -> str:
    """
    Build the HPC Diagnostic Report PDF and return the output path.
    """
    if analysis_date is None:
        analysis_date = datetime.now().strftime("%d %B %Y")

    styles = _styles()
    focus = analysis.focus
    focus_name = focus.department

    doc = BaseDocTemplate(
        output_path, pagesize=A4,
        leftMargin=1.6 * cm, rightMargin=1.6 * cm,
        topMargin=1.6 * cm, bottomMargin=1.6 * cm,
        title=cfg.get("report_title", "High Performance Culture Diagnostic Report"),
        author=prepared_by,
    )
    frame_content = Frame(1.6 * cm, 1.5 * cm, A4[0] - 3.2 * cm, A4[1] - 3.4 * cm)
    frame_cover = Frame(1.6 * cm, 1.6 * cm, A4[0] - 3.2 * cm, A4[1] - 3.2 * cm)

    doc.addPageTemplates([
        PageTemplate(id="Cover", frames=[frame_cover], onPage=_draw_cover()),
        PageTemplate(id="Content", frames=[frame_content],
                     onPage=_draw_page_frame(focus_name, analysis_date)),
    ])

    story = []
    _cover(story, styles, focus, analysis, cfg, analysis_date, prepared_by)
    story.append(NextPageTemplate("Content"))
    story.append(PageBreak())
    _executive_summary(story, styles, focus, analysis, cfg)
    story.append(PageBreak())
    _radar_page(story, styles, focus, analysis)
    story.append(PageBreak())
    _summary_table(story, styles, focus, analysis, cfg)
    story.append(PageBreak())
    _heatmap_page(story, styles, analysis)
    story.append(PageBreak())
    _insights_page(story, styles, analysis, focus)
    story.append(PageBreak())
    _strengths_opps(story, styles, focus)
    story.append(PageBreak())
    _recommendations(story, styles, analysis)
    story.append(PageBreak())
    _appendix(story, styles, cfg)

    doc.build(story)
    return output_path


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------
def _cover(story, styles, focus, analysis, cfg, analysis_date, prepared_by):
    story.append(Spacer(1, 6.5 * cm))
    n_focus = focus.n_respondents
    n_total = analysis.company_n
    is_all = focus.department == "Company-wide"
    if is_all:
        resp_text = f"{n_total} respondents (company-wide)"
    else:
        resp_text = f"{n_focus} respondents (focus)  ·  {n_total} respondents (company)"

    rows = [
        ["Report title", cfg.get("report_title", "High Performance Culture Diagnostic Report")],
        ["Department focus", focus.department],
        ["Comparison group", f"Company-wide average ({analysis.all_departments.shape[0]} departments)"],
        ["Date of analysis", analysis_date],
        ["Responses analyzed", resp_text],
        ["Prepared by", prepared_by],
        ["Generated by", f"HPC Diagnostic Tool v{cfg.get('tool_version', '1.0')}"],
    ]
    t = Table(rows, colWidths=[4.6 * cm, 12.0 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10.5),
        ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#222222")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, GREY_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.7 * cm))

    strong = max(focus.pillar_means, key=focus.pillar_means.get)
    weak = min(focus.pillar_means, key=focus.pillar_means.get)
    if focus.downgraded:
        headline = (f"<b>{focus.classification}</b> — with a <b>significant imbalance</b> "
                    f"(gap = {focus.imbalance:.2f}) between the strongest pillar "
                    f"(<b>{strong}</b>, {focus.pillar_means[strong]:.2f}) and the weakest pillar "
                    f"(<b>{weak}</b>, {focus.pillar_means[weak]:.2f}). Classification "
                    f"<b>automatically downgraded</b> by the imbalance rule.")
    elif focus.imbalance > cfg.imbalance_wellbalanced_max:
        headline = (f"<b>{focus.classification}</b> — with a <b>{focus.balance_label.lower()}</b> "
                    f"(gap = {focus.imbalance:.2f}) between the strongest pillar "
                    f"(<b>{strong}</b>, {focus.pillar_means[strong]:.2f}) and the weakest pillar "
                    f"(<b>{weak}</b>, {focus.pillar_means[weak]:.2f}). Below the {cfg.imbalance_moderate_max:.2f} "
                    f"downgrade threshold, but <b>flagged as a watch item</b>.")
    else:
        headline = (f"<b>{focus.classification}</b> — well balanced across all four pillars "
                    f"(gap = {focus.imbalance:.2f}). Overall score {focus.overall:.2f}.")
    story.append(_callout(styles, "Headline classification", headline))


def _executive_summary(story, styles, focus, analysis, cfg):
    story.append(Paragraph("1. Executive Summary", styles["h1"]))
    gap_co = focus.overall - analysis.company_overall
    story.append(Paragraph(
        f"The <b>{focus.department}</b> department scores an overall <b>{focus.overall:.2f} / 10</b> on the "
        f"High Performance Culture index, versus a company-wide average of <b>{analysis.company_overall:.2f} / 10</b> "
        f"({gap_co:+.2f}). Applying the PERILL-based scoring model, the department falls into the "
        f"<b>{focus.classification}</b> band.",
        styles["body"]))

    if focus.downgraded:
        story.append(Paragraph(
            f"The gap between the strongest and weakest pillar is <b>{focus.imbalance:.2f} points</b>, exceeding "
            f"the {cfg.imbalance_moderate_max:.2f} threshold. The imbalance rule automatically downgrades the "
            f"classification and surfaces this pattern as a <b>strategic risk</b>.",
            styles["body"]))
    elif focus.imbalance > cfg.imbalance_wellbalanced_max:
        story.append(Paragraph(
            f"The pillar gap of <b>{focus.imbalance:.2f}</b> sits in the moderate range and is <b>flagged as "
            f"a watch item</b>. Left unaddressed, it will trigger an automatic downgrade at the next wave.",
            styles["body"]))

    if focus.warnings:
        for w in focus.warnings:
            story.append(_callout(styles, "Sample-size warning", w))

    strong = max(focus.pillar_means, key=focus.pillar_means.get)
    weak = min(focus.pillar_means, key=focus.pillar_means.get)

    story.append(Paragraph("Key strengths", styles["h3"]))
    for text in [
        f"<b>{strong}</b> is the strongest pillar ({focus.pillar_means[strong]:.2f}) — "
        f"{focus.pillar_means[strong] - analysis.company_pillar_means[strong]:+.2f} vs. company average.",
        "Correlations between pillars suggest reinforcing dynamics that leadership can leverage.",
    ]:
        story.append(Paragraph("•  " + text, styles["bullet"]))

    story.append(Paragraph("Key opportunities", styles["h3"]))
    for text in [
        f"<b>{weak}</b> is the weakest pillar ({focus.pillar_means[weak]:.2f}) — "
        f"{focus.pillar_means[weak] - analysis.company_pillar_means[weak]:+.2f} vs. company average.",
        f"Closing the {weak} gap is the highest-value intervention target.",
    ]:
        story.append(Paragraph("•  " + text, styles["bullet"]))

    story.append(Paragraph("Priority leadership actions", styles["h3"]))
    top_recs = [r for r in analysis.recommendations if r["Priority"] in ("Critical", "High")][:3]
    for r in top_recs:
        story.append(Paragraph(f"•  {r['Action']}  <i>({r['Pillar']} · {r['Priority']})</i>",
                               styles["bullet"]))


def _radar_page(story, styles, focus, analysis):
    story.append(Paragraph("2. Strategic Vector Performance", styles["h1"]))
    story.append(Paragraph(
        f"The radar visualizes the four pillars for the {focus.department} against the company-wide average. "
        "A symmetrical shape indicates a balanced culture; distortion signals that one or more pillars are "
        "pulling the system down.", styles["body"]))
    png = charts.radar_png(focus.pillar_means, analysis.company_pillar_means, focus.department)
    story.append(Image(png, width=15 * cm, height=12.5 * cm))
    story.append(Spacer(1, 6))
    strong = max(focus.pillar_means, key=focus.pillar_means.get)
    weak = min(focus.pillar_means, key=focus.pillar_means.get)
    story.append(_callout(styles, "How to read this chart",
        f"The {focus.department} shape is <b>elongated toward {strong}</b> and <b>compressed on {weak}</b>. "
        f"This is the classic pattern of a team whose strengths are being held back by one systemic weakness."))


def _summary_table(story, styles, focus, analysis, cfg):
    story.append(Paragraph("3. Executive Summary Table", styles["h1"]))
    story.append(Paragraph(
        "Pillar-level breakdown with classification, gap versus company-wide average, and executive interpretation.",
        styles["body"]))

    rows = [["Pillar", "Mean", "Status", "Gap vs. Co.", "Key Interpretation"]]
    for pr in focus.pillar_results:
        rows.append([
            pr.pillar, f"{pr.mean:.2f}", pr.status, f"{pr.gap_vs_company:+.2f}",
            Paragraph(pr.interpretation, styles["cell"]),
        ])
    tbl = Table(rows, colWidths=[2.6 * cm, 1.6 * cm, 3.6 * cm, 2.0 * cm, 6.8 * cm])
    ts = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ALIGN", (1, 1), (3, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, GREY_BORDER),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
    ]
    for i in range(1, len(rows)):
        if i % 2 == 0:
            ts.append(("BACKGROUND", (0, i), (-1, i), GREY_LIGHT))
        gap = float(rows[i][3])
        if gap < -0.5:
            ts.append(("TEXTCOLOR", (3, i), (3, i), RED))
            ts.append(("FONTNAME", (3, i), (3, i), "Helvetica-Bold"))
        elif gap > 0.5:
            ts.append(("TEXTCOLOR", (3, i), (3, i), GREEN))
            ts.append(("FONTNAME", (3, i), (3, i), "Helvetica-Bold"))
    tbl.setStyle(TableStyle(ts))
    story.append(tbl)
    story.append(Spacer(1, 14))

    overall_row = [[
        Paragraph("<b>Overall HPC Score</b>", styles["cell_bold_gold"]),
        Paragraph(f"<b>{focus.overall:.2f}</b>", styles["cell_bold_gold"]),
        Paragraph(f"<b>{focus.classification}</b>", styles["cell_bold_gold"]),
        Paragraph(f"<b>{focus.overall - analysis.company_overall:+.2f}</b>", styles["cell_bold_gold"]),
        Paragraph(f"<b>{focus.balance_label}</b> (gap = {focus.imbalance:.2f})"
                  + (" — downgraded" if focus.downgraded else
                     (" — watch item" if focus.imbalance > cfg.imbalance_wellbalanced_max else "")),
                  styles["cell_bold_gold"]),
    ]]
    otbl = Table(overall_row, colWidths=[2.6 * cm, 1.6 * cm, 3.6 * cm, 2.0 * cm, 6.8 * cm])
    otbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FFF2CC")),
        ("ALIGN", (1, 0), (3, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOX", (0, 0), (-1, -1), 0.8, GOLD),
    ]))
    story.append(otbl)


def _heatmap_page(story, styles, analysis):
    story.append(Paragraph("4. Strategic Pillar Inter-Correlation Heatmap", styles["h1"]))
    story.append(Paragraph(
        "Correlations show which pillars move together across respondents. Strong positive correlations "
        "indicate mutually reinforcing dynamics — a change in one is likely accompanied by a change in the other.",
        styles["body"]))
    png = charts.heatmap_png(analysis.correlation)
    story.append(Image(png, width=13.5 * cm, height=10.5 * cm))
    story.append(Spacer(1, 6))

    import numpy as np
    corr = analysis.correlation
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    off = corr.where(mask)
    max_val = off.stack().max()
    max_pair = off.stack().idxmax()
    story.append(_callout(styles, "Executive interpretation",
        f"The strongest pillar relationship is between <b>{max_pair[0]}</b> and <b>{max_pair[1]}</b> "
        f"(r = {max_val:.2f}). Investment in one is highly likely to lift the other — making them a natural "
        f"pair of intervention levers."))


def _insights_page(story, styles, analysis, focus):
    story.append(Paragraph("5. Automated Insights", styles["h1"]))
    story.append(Paragraph(
        "Rule-based observations generated directly from the calculated statistics.", styles["body"]))
    for ins in analysis.insights:
        story.append(Paragraph(
            f"<b>{ins['label']}.</b> {ins['text']}  <font color='#888888' size='8'>[{ins['rule']}]</font>",
            styles["bullet"]))
    story.append(Spacer(1, 8))
    png = charts.ranking_png(analysis.all_departments, analysis.company_overall,
                             focus_dept=focus.department if focus.department != "Company-wide" else None)
    story.append(Image(png, width=16 * cm, height=10.5 * cm))


def _strengths_opps(story, styles, focus):
    story.append(Paragraph("6. Strengths and Opportunities", styles["h1"]))

    strong = max(focus.pillar_means, key=focus.pillar_means.get)
    weak = min(focus.pillar_means, key=focus.pillar_means.get)

    story.append(Paragraph("Strengths", styles["h2"]))
    story.append(Paragraph(
        f"<b>{strong}</b> is the department's defining asset ({focus.pillar_means[strong]:.2f}). "
        f"This is a durable strength — expensive to build, cheap to lose — so protecting it should be an "
        f"explicit leadership decision.", styles["body"]))

    story.append(Paragraph("Opportunities", styles["h2"]))
    story.append(Paragraph(
        f"<b>{weak}</b> is the highest-value intervention target ({focus.pillar_means[weak]:.2f}). "
        f"Because the score is materially below the strongest pillar, incremental fixes are unlikely to "
        f"shift the classification — a focused, time-boxed programme is required.", styles["body"]))
    story.append(Paragraph(
        "If no action is taken over the next two to three quarters, expect: escalating stakeholder concerns, "
        "attrition among high performers who feel unable to deliver at pace, and a widening gap versus the "
        "company average that will be harder to close.", styles["body"]))


def _recommendations(story, styles, analysis):
    story.append(Paragraph("7. Recommendations", styles["h1"]))
    story.append(Paragraph(
        "Prioritized recommendations, mapped to the four pillars. Each includes the relevant pillar, "
        "priority level, expected impact, suggested owner and timeline.", styles["body"]))

    rows = [["#", "Action", "Pillar", "Priority", "Expected Impact", "Owner", "Timeline"]]
    for i, r in enumerate(analysis.recommendations, start=1):
        rows.append([
            str(i),
            Paragraph(r["Action"], styles["cell"]),
            Paragraph(r["Pillar"], styles["cell"]),
            r["Priority"],
            Paragraph(r["Expected Impact"], styles["cell"]),
            Paragraph(r["Owner"], styles["cell"]),
            Paragraph(r["Timeline"], styles["cell"]),
        ])
    tbl = Table(rows, colWidths=[0.7 * cm, 5.4 * cm, 2.0 * cm, 1.5 * cm, 3.8 * cm, 2.6 * cm, 1.8 * cm])
    ts = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9.5),
        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 0), (3, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.4, GREY_BORDER),
    ]
    priority_colors = {"Critical": RED, "High": AMBER, "Medium": GREEN}
    for i in range(1, len(rows)):
        if i % 2 == 0:
            ts.append(("BACKGROUND", (0, i), (-1, i), GREY_LIGHT))
        pri = rows[i][3]
        if pri in priority_colors:
            ts.append(("TEXTCOLOR", (3, i), (3, i), priority_colors[pri]))
            ts.append(("FONTNAME", (3, i), (3, i), "Helvetica-Bold"))
    tbl.setStyle(TableStyle(ts))
    story.append(tbl)


def _appendix(story, styles, cfg):
    story.append(Paragraph("Appendix — Questionnaire Items", styles["h1"]))
    story.append(Paragraph(
        f"The full active question bank used to generate this report. All items are rated on a "
        f"{cfg.scale_min}–{cfg.scale_max} scale ({cfg.scale_min} = {cfg.scale_label_min}, "
        f"{cfg.scale_max} = {cfg.scale_label_max}).", styles["body"]))

    active = cfg.active_questions
    for p in PILLARS:
        sub = active[active["Pillar"] == p]
        if sub.empty:
            continue
        story.append(Paragraph(p, styles["h3"]))
        rows = [["ID", "Question"]]
        for _, row in sub.iterrows():
            rows.append([str(row["Question ID"]), Paragraph(str(row["Question Text"]), styles["cell"])])
        at = Table(rows, colWidths=[1.2 * cm, 15.4 * cm])
        at.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.3, GREY_BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GREY_LIGHT]),
        ]))
        story.append(at)
        story.append(Spacer(1, 8))
