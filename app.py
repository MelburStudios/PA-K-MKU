from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

app = Flask(__name__)
app.config['SECRET_KEY'] = 'pa-k-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/members.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    reg_number = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    course = db.Column(db.String(100))
    year = db.Column(db.String(10))
    award_level = db.Column(db.String(20), default='Bronze')
    status = db.Column(db.String(20), default='Student')
    
    # Progress Tracking
    service_completed = db.Column(db.Boolean, default=False)
    physical_completed = db.Column(db.Boolean, default=False)
    skill_completed = db.Column(db.Boolean, default=False)
    journey_completed = db.Column(db.Boolean, default=False)
    
    # Financials
    registration_fee_paid = db.Column(db.Boolean, default=False)
    registration_fee_amount = db.Column(db.Float, default=0.0)
    
    # Admin
    admin_remarks = db.Column(db.Text)
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)

class FinancialSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    registration_fee = db.Column(db.Float, default=1000.0)  # Default fee

# Create tables
with app.app_context():
    os.makedirs('data', exist_ok=True)
    db.create_all()
    # Initialize default fee if not exists
    if not FinancialSetting.query.first():
        default_fee = FinancialSetting(registration_fee=1000.0)
        db.session.add(default_fee)
        db.session.commit()

# Routes
@app.route('/')
def dashboard():
    total_members = Member.query.count()
    total_students = Member.query.filter_by(status='Student').count()
    total_alumni = Member.query.filter_by(status='Alumni').count()
    
    # Calculate eligible students
    eligible_students = Member.query.filter_by(
        status='Student',
        service_completed=True,
        physical_completed=True, 
        skill_completed=True,
        journey_completed=True
    ).count()
    
    fee_setting = FinancialSetting.query.first()
    
    return render_template('dashboard.html',
                         total_members=total_members,
                         total_students=total_students,
                         total_alumni=total_alumni,
                         eligible_students=eligible_students,
                         fee_setting=fee_setting)

@app.route('/members')
def members():
    all_members = Member.query.order_by(Member.date_joined.desc()).all()
    return render_template('members.html', members=all_members)

@app.route('/add_member', methods=['GET', 'POST'])
def add_member():
    fee_setting = FinancialSetting.query.first()
    
    if request.method == 'POST':
        # Check if reg number already exists
        existing_member = Member.query.filter_by(reg_number=request.form['reg_number']).first()
        if existing_member:
            flash('Registration number already exists!', 'error')
            return redirect(url_for('add_member'))
        
        new_member = Member(
            full_name=request.form['full_name'],
            reg_number=request.form['reg_number'],
            email=request.form['email'],
            phone=request.form['phone'],
            course=request.form['course'],
            year=request.form['year'],
            award_level=request.form['award_level'],
            status=request.form['status'],
            registration_fee_paid=request.form.get('registration_fee_paid') == 'on',
            registration_fee_amount=fee_setting.registration_fee,
            admin_remarks=request.form['admin_remarks']
        )
        
        db.session.add(new_member)
        db.session.commit()
        flash('Member added successfully!', 'success')
        return redirect(url_for('members'))
    
    return render_template('add_member.html', fee_setting=fee_setting)

@app.route('/edit_member/<int:member_id>', methods=['GET', 'POST'])
def edit_member(member_id):
    member = Member.query.get_or_404(member_id)
    fee_setting = FinancialSetting.query.first()
    
    if request.method == 'POST':
        member.full_name = request.form['full_name']
        member.email = request.form['email']
        member.phone = request.form['phone']
        member.course = request.form['course']
        member.year = request.form['year']
        member.award_level = request.form['award_level']
        member.status = request.form['status']
        
        # Progress tracking
        member.service_completed = request.form.get('service_completed') == 'on'
        member.physical_completed = request.form.get('physical_completed') == 'on'
        member.skill_completed = request.form.get('skill_completed') == 'on'
        member.journey_completed = request.form.get('journey_completed') == 'on'
        
        # Financials
        member.registration_fee_paid = request.form.get('registration_fee_paid') == 'on'
        member.admin_remarks = request.form['admin_remarks']
        
        db.session.commit()
        flash('Member updated successfully!', 'success')
        return redirect(url_for('members'))
    
    return render_template('edit_member.html', member=member, fee_setting=fee_setting)

@app.route('/finances', methods=['GET', 'POST'])
def finances():
    fee_setting = FinancialSetting.query.first()
    
    if request.method == 'POST':
        new_fee = float(request.form['registration_fee'])
        fee_setting.registration_fee = new_fee
        db.session.commit()
        flash('Registration fee updated successfully!', 'success')
        return redirect(url_for('finances'))
    
    # Financial statistics
    total_members = Member.query.count()
    paid_members = Member.query.filter_by(registration_fee_paid=True).count()
    total_collected = paid_members * fee_setting.registration_fee
    pending_collection = (total_members - paid_members) * fee_setting.registration_fee
    
    return render_template('finances.html',
                         fee_setting=fee_setting,
                         total_members=total_members,
                         paid_members=paid_members,
                         total_collected=total_collected,
                         pending_collection=pending_collection)

@app.route('/reports')
def reports():
    # Eligible students report
    eligible_students = Member.query.filter_by(
        status='Student',
        service_completed=True,
        physical_completed=True,
        skill_completed=True,
        journey_completed=True
    ).all()
    
    all_members = Member.query.all()
    
    return render_template('reports.html',
                         eligible_students=eligible_students,
                         all_members=all_members)

@app.route('/student_report/<int:member_id>')
def student_report(member_id):
    member = Member.query.get_or_404(member_id)
    
    # Create PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        textColor=colors.HexColor('#2E86AB')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=12,
        textColor=colors.HexColor('#2E86AB')
    )
    
    # Title
    story.append(Paragraph("PRESIDENT'S AWARD CLUB - MOUNT KENYA UNIVERSITY", title_style))
    story.append(Paragraph("Student Progress Report", styles['Heading2']))
    story.append(Spacer(1, 20))
    
    # Student Information
    story.append(Paragraph("STUDENT INFORMATION", heading_style))
    student_data = [
        ['Full Name:', member.full_name],
        ['Registration Number:', member.reg_number],
        ['Email:', member.email],
        ['Phone:', member.phone],
        ['Course:', member.course],
        ['Year:', member.year],
        ['Award Level:', member.award_level],
        ['Status:', member.status],
        ['Date Joined:', member.date_joined.strftime('%Y-%m-%d')]
    ]
    
    student_table = Table(student_data, colWidths=[2*inch, 3*inch])
    student_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8F9FA')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(student_table)
    story.append(Spacer(1, 20))
    
    # Progress Tracking
    story.append(Paragraph("AWARD PROGRESS TRACKING", heading_style))
    progress_data = [
        ['Section', 'Status', 'Completion'],
        ['Service', 'Completed' if member.service_completed else 'Not Completed', '✅' if member.service_completed else '❌'],
        ['Physical Recreation', 'Completed' if member.physical_completed else 'Not Completed', '✅' if member.physical_completed else '❌'],
        ['Skill Development', 'Completed' if member.skill_completed else 'Not Completed', '✅' if member.skill_completed else '❌'],
        ['Adventurous Journey', 'Completed' if member.journey_completed else 'Not Completed', '✅' if member.journey_completed else '❌']
    ]
    
    progress_table = Table(progress_data, colWidths=[2*inch, 2*inch, 1.5*inch])
    progress_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E86AB')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    story.append(progress_table)
    story.append(Spacer(1, 20))
    
    # Financial Status
    story.append(Paragraph("FINANCIAL STATUS", heading_style))
    financial_data = [
        ['Item', 'Details'],
        ['Registration Fee Amount:', f'KSh {member.registration_fee_amount:,.2f}'],
        ['Payment Status:', 'PAID ✅' if member.registration_fee_paid else 'PENDING ❌'],
        ['Amount Paid:', f'KSh {member.registration_fee_amount:,.2f}' if member.registration_fee_paid else 'KSh 0.00'],
        ['Balance:', 'KSh 0.00' if member.registration_fee_paid else f'KSh {member.registration_fee_amount:,.2f}']
    ]
    
    financial_table = Table(financial_data, colWidths=[2*inch, 3*inch])
    financial_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8F9FA')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(financial_table)
    story.append(Spacer(1, 20))
    
    # What's Remaining
    story.append(Paragraph("REQUIREMENTS FOR NEXT AWARD", heading_style))
    remaining_sections = []
    if not member.service_completed:
        remaining_sections.append("• Service")
    if not member.physical_completed:
        remaining_sections.append("• Physical Recreation") 
    if not member.skill_completed:
        remaining_sections.append("• Skill Development")
    if not member.journey_completed:
        remaining_sections.append("• Adventurous Journey")
    
    if remaining_sections:
        remaining_text = "To qualify for the award, complete the following sections:\n\n" + "\n".join(remaining_sections)
    else:
        remaining_text = "🎉 ALL REQUIREMENTS COMPLETED! Eligible for award."
    
    story.append(Paragraph(remaining_text, styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Admin Remarks
    if member.admin_remarks:
        story.append(Paragraph("ADMIN REMARKS", heading_style))
        story.append(Paragraph(member.admin_remarks, styles['Normal']))
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    story.append(Paragraph("President's Award Club - Mount Kenya University", styles['Normal']))
    story.append(Paragraph("System Developed by Melbur Studios (https://studios.melbur.co.ke)", styles['Italic']))
    
    doc.build(story)
    buffer.seek(0)
    
    return send_file(buffer, as_attachment=True, download_name=f"PAK_Report_{member.reg_number}.pdf", mimetype='application/pdf')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)