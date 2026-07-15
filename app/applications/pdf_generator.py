"""PDF generator helper using ReportLab."""

from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from app.applications.models import Application


def generate_application_pdf(application: Application) -> bytes:
    """Generate a PDF document summarizing an application's details and responses."""
    buffer = BytesIO()

    # Define page setup
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "PDFTitle",
        parent=styles["Heading1"],
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#1A365D"),
        spaceAfter=15,
    )

    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=15,
        spaceAfter=10,
        keepWithNext=True,
    )

    label_style = ParagraphStyle(
        "LabelStyle",
        parent=styles["Normal"],
        fontSize=10,
        leading=13,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#4A5568"),
    )

    value_style = ParagraphStyle(
        "ValueStyle",
        parent=styles["Normal"],
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#2D3748"),
    )

    story = []

    # 1. Header Title
    story.append(Paragraph("Smart University Management System", ParagraphStyle("SubHeader", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#718096"), spaceAfter=5)))
    story.append(Paragraph(application.subject or "Application Document", title_style))
    story.append(Spacer(1, 10))

    # 2. Application Info Table
    info_data = [
        [
            Paragraph("Application ID:", label_style),
            Paragraph(str(application.id), value_style),
            Paragraph("Category:", label_style),
            Paragraph(application.category.name if application.category else "N/A", value_style),
        ],
        [
            Paragraph("Status:", label_style),
            Paragraph(application.status.value.upper(), value_style),
            Paragraph("Submitted At:", label_style),
            Paragraph(
                application.submitted_at.strftime("%Y-%m-%d %H:%M:%S")
                if application.submitted_at
                else "N/A",
                value_style,
            ),
        ],
    ]

    t_info = Table(info_data, colWidths=[90, 160, 90, 160])
    t_info.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(t_info)
    story.append(Spacer(1, 15))

    # 3. Student Profile Info
    story.append(Paragraph("Applicant Details", section_heading))
    
    student = application.student if getattr(application, "student", None) else None
    student_name = student.full_name if student else "N/A"
    student_email = student.email if student else "N/A"
    profile = student.student_profile if student else None
    reg_num = profile.registration_number if profile else "N/A"
    semester = str(profile.semester) if profile and profile.semester else "N/A"
    batch = profile.batch if profile else "N/A"

    student_data = [
        [
            Paragraph("Full Name:", label_style),
            Paragraph(student_name, value_style),
            Paragraph("Reg. Number:", label_style),
            Paragraph(reg_num, value_style),
        ],
        [
            Paragraph("Email Address:", label_style),
            Paragraph(student_email, value_style),
            Paragraph("Semester / Batch:", label_style),
            Paragraph(f"Sem {semester} / {batch}", value_style),
        ],
    ]

    t_student = Table(student_data, colWidths=[90, 160, 90, 160])
    t_student.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(t_student)
    story.append(Spacer(1, 15))

    # 4. Responses Section
    story.append(Paragraph("Form Responses", section_heading))

    responses_data = []
    # Sort responses by field display_order if we can map them, otherwise by key
    for resp in sorted(application.responses, key=lambda r: r.field_key):
        # We can add each key-value pair to a table row
        responses_data.append([
            Paragraph(resp.field_key.replace("_", " ").title(), label_style),
            Paragraph(resp.value or "", value_style),
        ])

    if not responses_data:
        responses_data.append([
            Paragraph("No fields submitted.", value_style),
            Paragraph("", value_style),
        ])

    t_responses = Table(responses_data, colWidths=[150, 350])
    t_responses.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F7FAFC")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(t_responses)

    # Build the document
    doc.build(story)
    return buffer.getvalue()
