from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Trainer
from form.models import Attendance
from feedback.models import Feedback
from django.db.models import Avg, Count
import json
import csv
from datetime import datetime
from django.http import HttpResponse
from django.db import models
try:
    import pandas as pd
except ImportError:
    pd = None

# import gspread
# from google.oauth2.service_account import Credentials
import os
from django.http import HttpResponse, JsonResponse
import requests
import time
from django.conf import settings
from form.models import Student, WhatsAppMessageLog
from .models import Batch
import pywhatkit as pwk

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def get_feedback_stats(feedback_qs):
    # Optimizing database hits using aggregation with conditional filters
    stats = feedback_qs.aggregate(
        q1=Avg('ques1_rating'),
        q2=Avg('ques2_rating'),
        q3=Avg('ques3_rating'),
        q4=Avg('ques4_rating'),
        f_count=Count('id'),
        
        # Distribution counts for each rating type
        q1_5=Count('id', filter=models.Q(ques1_rating=5)),
        q1_4=Count('id', filter=models.Q(ques1_rating=4)),
        q1_3=Count('id', filter=models.Q(ques1_rating=3)),
        q1_lt3=Count('id', filter=models.Q(ques1_rating__lt=3)),
        
        q2_5=Count('id', filter=models.Q(ques2_rating=5)),
        q2_4=Count('id', filter=models.Q(ques2_rating=4)),
        q2_3=Count('id', filter=models.Q(ques2_rating=3)),
        q2_lt3=Count('id', filter=models.Q(ques2_rating__lt=3)),
        
        q3_5=Count('id', filter=models.Q(ques3_rating=5)),
        q3_4=Count('id', filter=models.Q(ques3_rating=4)),
        q3_3=Count('id', filter=models.Q(ques3_rating=3)),
        q3_lt3=Count('id', filter=models.Q(ques3_rating__lt=3)),
        
        q4_5=Count('id', filter=models.Q(ques4_rating=5)),
        q4_4=Count('id', filter=models.Q(ques4_rating=4)),
        q4_3=Count('id', filter=models.Q(ques4_rating=3)),
        q4_lt3=Count('id', filter=models.Q(ques4_rating__lt=3)),
    )
    
    # Realistic Rating
    rating = ((stats['q1'] or 0) + (stats['q2'] or 0) + (stats['q3'] or 0) + (stats['q4'] or 0)) / 4 if stats['f_count'] > 0 else 0.0

    feedback_list = []
    dist = [0, 0, 0, 0] # 5 Stars, 4 Stars, 3 Stars, Poor

    for f in feedback_qs.order_by('-submitted_at'):
        f_avg = (f.ques1_rating + f.ques2_rating + f.ques3_rating + f.ques4_rating) / 4
        
        # Bucketize based on average
        if f_avg >= 4.5: dist[0] += 1
        elif f_avg >= 3.5: dist[1] += 1
        elif f_avg >= 2.5: dist[2] += 1
        else: dist[3] += 1

        feedback_list.append({
            'sid': f.student_id,
            'name': f.student_name,
            'email': f.email,
            'phone': f.phone,
            'review': f.review_description,
            'q1': f.ques1_rating,
            'q2': f.ques2_rating,
            'q3': f.ques3_rating,
            'q4': f.ques4_rating,
            'avg': round(f_avg, 1),
            'date': f.submitted_at.strftime('%Y-%m-%d %H:%M')
        })

    return {
        'q1': round(stats['q1'] or 0, 1),
        'q2': round(stats['q2'] or 0, 1),
        'q3': round(stats['q3'] or 0, 1),
        'q4': round(stats['q4'] or 0, 1),
        'count': stats['f_count'],
        'avg': round(rating, 1),
        'list': feedback_list,
        'q1_dist': [stats['q1_5'], stats['q1_4'], stats['q1_3'], stats['q1_lt3']],
        'q2_dist': [stats['q2_5'], stats['q2_4'], stats['q2_3'], stats['q2_lt3']],
        'q3_dist': [stats['q3_5'], stats['q3_4'], stats['q3_3'], stats['q3_lt3']],
        'q4_dist': [stats['q4_5'], stats['q4_4'], stats['q4_3'], stats['q4_lt3']],
        'dist': dist
    }

@login_required
def index(request):
    trainers = Trainer.objects.prefetch_related('batches').all()
    trainers_data = []
    
    # Date Filtering Logic (Range, Month, Year)
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    month_name = request.GET.get('month')
    year_val = request.GET.get('year')
    
    # Base Querysets
    all_attendance = Attendance.objects.all().order_by('-submitted_at')
    all_feedback_qs = Feedback.objects.all().order_by('-submitted_at')
    
    # Apply Range Filter
    if start_date and end_date:
        all_attendance = all_attendance.filter(submitted_at__date__range=[start_date, end_date])
        all_feedback_qs = all_feedback_qs.filter(submitted_at__date__range=[start_date, end_date])
    
    # Apply Month Filter
    if month_name:
        # Convert month name to number
        try:
            m_num = datetime.strptime(month_name, "%B").month
            all_attendance = all_attendance.filter(submitted_at__month=m_num)
            all_feedback_qs = all_feedback_qs.filter(submitted_at__month=m_num)
        except ValueError: pass

    # Apply Year Filter
    if year_val:
        all_attendance = all_attendance.filter(submitted_at__year=year_val)
        all_feedback_qs = all_feedback_qs.filter(submitted_at__year=year_val)

    for t in trainers:
        batches = t.batches.all()
        # Filter trainer specific stuff from the already filtered base sets
        trainer_attendance = all_attendance.filter(trainer_name=t.name)
        real_submission_count = trainer_attendance.count()
        total_target = sum(b.students_count for b in batches)
        
        # Calculate feedback stats
        feedback_qs = all_feedback_qs.filter(trainer_name=t.name)
        
        trainer_attendance_list = [
            {
                'sid': att.student_id,
                'name': att.name,
                'topic': att.today_topic,
                'technology': att.technology,
                'mode': att.batch_mode,
                'week_type': att.week_type,
                'date': att.submitted_at.strftime('%Y-%m-%d %H:%M')
            } for att in trainer_attendance
        ]

        # Phase Stats Breakdown
        trainer_phase_stats = {
            p: {
                'overall': get_feedback_stats(feedback_qs.filter(phase=p)),
                'online': get_feedback_stats(feedback_qs.filter(phase=p, batch_mode="Online")),
                'offline': get_feedback_stats(feedback_qs.filter(phase=p, batch_mode="Offline")),
            } for p in ['P-1', 'P-2', 'P-3', 'P-4', 'P-5']
        }
        
        phase_stats = {
            'overall': get_feedback_stats(feedback_qs),
            'online': get_feedback_stats(feedback_qs.filter(batch_mode="Online")),
            'offline': get_feedback_stats(feedback_qs.filter(batch_mode="Offline")),
            'phases': trainer_phase_stats
        }
        
        # Rating for main table
        rating = phase_stats['overall']['avg']

        trainer_dict = {
            'name': t.name,
            'course': t.course,
            'rating': round(rating, 1),
            'real_count': real_submission_count,
            'target_count': total_target if total_target > 0 else 30, # Default target for aesthetics
            'month': batches[0].month if batches.exists() else "January",
            'year': batches[0].year if batches.exists() else "2024",
            'trainer_attendance_list': trainer_attendance_list,
            'phase_stats': phase_stats, # Global trainer phase stats
            'batches': [
                {
                    'type': b.batch_type,
                    'batch_name': b.batch_name,
                    'target': b.students_count,
                    'timing': b.timing,
                    'start_date': b.start_date.strftime('%d %b, %Y') if b.start_date else 'N/A',
                    'end_date': b.end_date.strftime('%d %b, %Y') if b.end_date else 'N/A',
                    'students_total': trainer_attendance.filter(week_type=b.batch_type, batch_time=b.timing).count(),
                    'phase_stats': {
                        p: {
                            'overall': get_feedback_stats(feedback_qs.filter(batch_type__iexact=b.batch_type, batch_timing__iexact=b.timing, phase=p)),
                            'online': get_feedback_stats(feedback_qs.filter(batch_type__iexact=b.batch_type, batch_timing__iexact=b.timing, phase=p, batch_mode__iexact="Online")),
                            'offline': get_feedback_stats(feedback_qs.filter(batch_type__iexact=b.batch_type, batch_timing__iexact=b.timing, phase=p, batch_mode__iexact="Offline")),
                        } for p in ['P-1', 'P-2', 'P-3', 'P-4', 'P-5']
                    },
                    'attendance_list': [
                        {
                            'sid': att.student_id,
                            'name': att.name,
                            'topic': att.today_topic,
                            'technology': att.technology,
                            'mode': att.batch_mode,
                            'date': att.submitted_at.strftime('%Y-%m-%d %H:%M')
                        } for att in trainer_attendance.filter(week_type=b.batch_type, batch_time=b.timing)
                    ]
                } for b in batches
            ]
        }
        trainers_data.append(trainer_dict)
    
    # Global Student Stats
    all_students = Student.objects.all().order_by('-joining_date')
    all_students_data = [
        {
            'sid': s.sid,
            'name': s.name,
            'phone': s.phone_number or 'N/A',
            'email': s.email or 'N/A',
            'course': s.course or 'N/A',
            'joining_date': s.joining_date.strftime('%d-%b-%Y') if s.joining_date else 'N/A'
        } for s in all_students
    ]

    # Recent Announcement Logs for Marquee
    recent_logs = WhatsAppMessageLog.objects.all().order_by('-sent_at')[:5]
    recent_announcements = []
    for log in recent_logs:
        status_icon = "✅" if log.status == 'Sent' else "❌"
        msg_preview = log.message_body[:40] + "..." if len(log.message_body) > 40 else log.message_body
        recent_announcements.append(f"{status_icon} To: {log.student.name} | Batch: {log.batch.batch_name if log.batch else 'N/A'} | Status: {log.status} | Time: {log.sent_at.strftime('%d-%b %H:%M')}")

    # Global Feedback Stats for Overall Modal
    global_stats = get_feedback_stats(all_feedback_qs)

    context = {
        'trainers_json': json.dumps(trainers_data),
        'all_students_json': json.dumps(all_students_data),
        'global_stats_json': json.dumps(global_stats),
        'total_students_count': all_students.count(),
        'total_feedbacks_count': all_feedback_qs.count(),
        'month_filter': month_name,
        'year_filter': year_val,
        'start_date': start_date,
        'end_date': end_date,
        'technology_choices': Attendance.TECHNOLOGY_CHOICES,
        'recent_announcements': recent_announcements
    }
    return render(request, 'dashboard/index.html', context)

def export_attendance_csv(request):
    trainer_name = request.GET.get('trainer')
    timing = request.GET.get('timing')
    response = HttpResponse(content_type='text/csv')
    filename = f"attendance_{trainer_name}.csv" if trainer_name else "attendance_all.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    writer.writerow(['Student Name', 'Student ID', 'Technology', 'Topic', 'Mode', 'Batch Timing', 'Trainer', 'Week Type', 'Submitted At'])
    
    attendances = Attendance.objects.all().order_by('-submitted_at')
    if trainer_name:
        attendances = attendances.filter(trainer_name=trainer_name)
    if timing:
        attendances = attendances.filter(batch_time=timing)
    for att in attendances:
        writer.writerow([
            att.name, 
            att.student_id, 
            att.technology, 
            att.today_topic, 
            att.batch_mode,
            att.batch_time, 
            att.trainer_name, 
            att.week_type, 
            att.submitted_at.strftime('%Y-%m-%d %H:%M')
        ])
    
    return response

def export_attendance_excel(request):
    if pd is None:
        return HttpResponse("Pandas and openpyxl are not installed on the server.", status=500)
    
    trainer_name = request.GET.get('trainer')
    timing = request.GET.get('timing')
    attendances = Attendance.objects.all().order_by('-submitted_at')
    if trainer_name:
        attendances = attendances.filter(trainer_name=trainer_name)
    if timing:
        attendances = attendances.filter(batch_time=timing)
        
    data = []
    for att in attendances:
        data.append({
            'Student Name': att.name,
            'Student ID': att.student_id,
            'Technology': att.technology,
            'Topic': att.today_topic,
            'Mode': att.batch_mode,
            'Batch Timing': att.batch_time.strftime('%H:%M') if att.batch_time else '',
            'Trainer': att.trainer_name,
            'Week Type': att.week_type,
            'Submitted At': att.submitted_at.strftime('%Y-%m-%d %H:%M')
        })
    
    df = pd.DataFrame(data)
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"attendance_{trainer_name}.xlsx" if trainer_name else "attendance_all.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    with pd.ExcelWriter(response, engine='openpyxl') as excel_writer:
        df.to_excel(excel_writer, index=False, sheet_name='Attendance')
    
    return response

def export_feedback_csv(request):
    trainer = request.GET.get('trainer')
    batch = request.GET.get('batch')
    phase = request.GET.get('phase')
    mode = request.GET.get('mode')
    timing = request.GET.get('timing')

    filename = f"Feedback_{trainer}_{batch}_{phase}.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['Student Name', 'Student ID', 'Email', 'Phone', 'Trainer', 'Tech', 'Batch', 'Mode', 'Phase', 'Q1 (Understand)', 'Q2 (Regularity)', 'Q3 (Practical)', 'Q4 (Doubt)', 'Avg Rating', 'Review', 'Submitted At'])

    feedback_qs = Feedback.objects.all().order_by('-submitted_at')
    if trainer: feedback_qs = feedback_qs.filter(trainer_name__iexact=trainer)
    if batch: feedback_qs = feedback_qs.filter(batch_type__iexact=batch)
    if phase: feedback_qs = feedback_qs.filter(phase__iexact=phase)
    if timing: feedback_qs = feedback_qs.filter(batch_timing__iexact=timing)
    if mode and mode.lower() != 'overall': 
        feedback_qs = feedback_qs.filter(batch_mode__iexact=mode)

    print(f"DEBUG EXPORT: {trainer}, {batch}, {phase}, {mode} -> Found {feedback_qs.count()} records")

    for f in feedback_qs:
        avg = round((f.ques1_rating + f.ques2_rating + f.ques3_rating + f.ques4_rating) / 4, 1)
        writer.writerow([
            f.student_name, f.student_id, f.email, f.phone, f.trainer_name, f.technology, f.batch_type, f.batch_mode, f.phase, f.ques1_rating, f.ques2_rating, f.ques3_rating, f.ques4_rating, avg, f.review_description, f.submitted_at.strftime('%Y-%m-%d %H:%M')
        ])
    return response

def export_feedback_excel(request):
    if pd is None: return HttpResponse("Pandas not installed.", status=500)
    
    trainer = request.GET.get('trainer')
    batch = request.GET.get('batch')
    phase = request.GET.get('phase')
    mode = request.GET.get('mode')
    timing = request.GET.get('timing')

    feedback_qs = Feedback.objects.all().order_by('-submitted_at')
    if trainer: feedback_qs = feedback_qs.filter(trainer_name__iexact=trainer)
    if batch: feedback_qs = feedback_qs.filter(batch_type__iexact=batch)
    if phase: feedback_qs = feedback_qs.filter(phase__iexact=phase)
    if timing: feedback_qs = feedback_qs.filter(batch_timing__iexact=timing)
    if mode and mode.lower() != 'overall':
        feedback_qs = feedback_qs.filter(batch_mode__iexact=mode)

    data = []
    for f in feedback_qs:
        data.append({
            'Student Name': f.student_name, 'Student ID': f.student_id, 'Email': f.email, 'Phone': f.phone,
            'Trainer': f.trainer_name, 'Tech': f.technology, 'Batch': f.batch_type, 'Mode': f.batch_mode, 'Phase': f.phase,
            'Q1': f.ques1_rating, 'Q2': f.ques2_rating, 'Q3': f.ques3_rating, 'Q4': f.ques4_rating,
            'Avg': round((f.ques1_rating + f.ques2_rating + f.ques3_rating + f.ques4_rating) / 4, 1),
            'Review': f.review_description, 'Date': f.submitted_at.strftime('%Y-%m-%d %H:%M')
        })

    df = pd.DataFrame(data)
    filename = f"Feedback_{trainer}_{batch}_{phase}.xlsx"
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Feedback Analysis')
    return response

def export_feedback_pdf(request):
    trainer = request.GET.get('trainer')
    batch = request.GET.get('batch')
    phase = request.GET.get('phase')
    mode = request.GET.get('mode')
    timing = request.GET.get('timing')

    feedback_qs = Feedback.objects.all().order_by('-submitted_at')
    if trainer: feedback_qs = feedback_qs.filter(trainer_name__iexact=trainer)
    if batch: feedback_qs = feedback_qs.filter(batch_type__iexact=batch)
    if phase: feedback_qs = feedback_qs.filter(phase__iexact=phase)
    if timing: feedback_qs = feedback_qs.filter(batch_timing__iexact=timing)
    if mode and mode.lower() != 'overall':
        feedback_qs = feedback_qs.filter(batch_mode__iexact=mode)

    response = HttpResponse(content_type='application/pdf')
    filename = f"Feedback_{trainer}_{batch}_{phase}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    doc = SimpleDocTemplate(response, pagesize=landscape(letter))
    elements = []
    styles = getSampleStyleSheet()
    
    # Title Styles
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor("#003459"), alignment=1, spaceAfter=20)
    subtitle_style = ParagraphStyle('SubtitleStyle', parent=styles['Normal'], fontSize=10, textColor=colors.grey, alignment=1, spaceAfter=30)

    elements.append(Paragraph(f"Feedback Analysis Report: {trainer}", title_style))
    elements.append(Paragraph(f"Batch: {batch} | Phase: {phase} | Segment: {mode.capitalize() if mode else 'Overall'}", subtitle_style))

    data = [['ID', 'Student Name', 'Tech', 'Mode', 'Q1', 'Q2', 'Q3', 'Q4', 'Avg', 'Review Date']]
    for f in feedback_qs:
        avg = round((f.ques1_rating + f.ques2_rating + f.ques3_rating + f.ques4_rating) / 4, 1)
        data.append([
            f.student_id, 
            Paragraph(f.student_name, styles['Normal']), 
            f.technology, 
            f.batch_mode, 
            str(f.ques1_rating), 
            str(f.ques2_rating), 
            str(f.ques3_rating), 
            str(f.ques4_rating), 
            str(avg), 
            f.submitted_at.strftime('%Y-%m-%d')
        ])

    table = Table(data, colWidths=[50, 120, 100, 60, 30, 30, 30, 30, 40, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#003459")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
        ('GRID', (0,0), (-1,-1), 1, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    elements.append(table)
    doc.build(elements)
    return response

def export_feedback_sheets(request):
    trainer_name = request.GET.get('trainer')
    batch_type = request.GET.get('batch')
    phase = request.GET.get('phase')
    mode = request.GET.get('mode', 'overall').lower()
    timing = request.GET.get('timing')
    
    # 1. Get filtered Feedback
    feedback_qs = Feedback.objects.filter(trainer_name=trainer_name)
    if phase:
        feedback_qs = feedback_qs.filter(phase=phase)
    if mode != 'overall':
        feedback_qs = feedback_qs.filter(batch_mode__iexact=mode)
    if batch_type:
        feedback_qs = feedback_qs.filter(batch_type__iexact=batch_type)
    if timing:
        feedback_qs = feedback_qs.filter(batch_timing__iexact=timing)
    
    html = f"""
    <html>
    <head>
        <title>{trainer_name} Feedback Sheet - {phase}</title>
        <style>
            body {{ background: #f1f5f9; color: #334155; padding: 30px; font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; }}
            .container {{ max-width: 1300px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }}
            .header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 25px; border-bottom: 2px solid #0f9d58; padding-bottom: 20px; }}
            h1 {{ color: #0f9d58; margin: 0; font-size: 1.6rem; font-weight: 800; }}
            .badge {{ background: #f1f5f9; padding: 6px 12px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase; }}
            table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; }}
            th, td {{ border: 1px solid #e2e8f0; padding: 12px 15px; text-align: left; }}
            th {{ background-color: #f8fafc; color: #475569; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; font-size: 0.7rem; }}
            tr:hover {{ background-color: #f8fafc; }}
            .rating-chip {{ display: inline-block; padding: 4px 10px; border-radius: 20px; font-weight: 800; font-size: 0.8rem; background: #ecfdf5; color: #10b981; }}
        </style>
    </head>
    <body onload="window.focus()">
        <div class="container">
            <div class="header">
                <div>
                    <h1>{trainer_name}</h1>
                    <div style="margin-top: 8px; display: flex; gap: 10px;">
                        <span class="badge">Phase: {phase or 'All'}</span>
                        <span class="badge">Mode: {mode}</span>
                        <span class="badge">Batch: {batch_type or 'All'}</span>
                    </div>
                </div>
                <div style="text-align: right; color: #64748b; font-size: 0.8rem;">
                    Generated on: {datetime.now().strftime('%B %d, %Y %H:%M')}
                </div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Enrollment ID</th>
                        <th>Student Name</th>
                        <th style="color: #3b82f6;">UNDERSTANDING</th>
                        <th style="color: #6366f1;">REGULARITY</th>
                        <th style="color: #8b5cf6;">PRACTICALS</th>
                        <th style="color: #a855f7;">DOUBTS</th>
                        <th style="background: #f8fafc;">Average</th>
                        <th>Student Feedback / Review</th>
                        <th>Phase</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody>
    """
    for f in feedback_qs.order_by('-submitted_at'):
        avg = (f.ques1_rating + f.ques2_rating + f.ques3_rating + f.ques4_rating)/4
        html += f"""
                <tr>
                    <td style="font-family: monospace; font-weight: 700; color: #0f172a;">{f.student_id}</td>
                    <td style="font-weight: 600;">{f.student_name}</td>
                    <td style="text-align: center; color: #3b82f6; font-weight: 700;">{f.ques1_rating}★</td>
                    <td style="text-align: center; color: #6366f1; font-weight: 700;">{f.ques2_rating}★</td>
                    <td style="text-align: center; color: #8b5cf6; font-weight: 700;">{f.ques3_rating}★</td>
                    <td style="text-align: center; color: #a855f7; font-weight: 700;">{f.ques4_rating}★</td>
                    <td><span class="rating-chip">{avg:.1f} / 5</span></td>
                    <td style="color: #475569; max-width: 400px; line-height: 1.4;">{f.review_description or 'No comments provided.'}</td>
                    <td><span class="badge" style="background: #f5f3ff; color: #7c3aed;">{f.phase}</span></td>
                    <td style="font-size: 0.8rem; white-space: nowrap;">{f.submitted_at.strftime('%Y-%m-%d')}</td>
                </tr>
        """
    
    if not feedback_qs.exists():
        html += """
                <tr>
                    <td colspan="7" style="text-align:center; padding: 60px; color: #94a3b8; font-style: italic;">
                        No feedback records found for this selection.
                    </td>
                </tr>
        """
        
    html += """
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html)

# def sync_to_google_sheets(request):
#     try:
#         # 1. Path to your Service Account JSON (Must be in project folder)
#         cred_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials.json')
        
#         if not os.path.exists(cred_path):
#             return JsonResponse({
#                 'status': 'error', 
#                 'message': 'API Connect Error: "credentials.json" file not found in project folder. Please download it from Google Cloud Console.'
#             })
            
#         # 2. Setup Authentication
#         scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
#         creds = Credentials.from_service_account_file(cred_path, scopes=scopes)
#         client = gspread.authorize(creds)

#         # 3. Spreadsheet Target (ID IS BEST)
#         # BHAi, agar ID ho toh yahan daal dein, naam ki zarurat nahi:
#         sheet_id = "" # PASTE YOUR SHEET ID HERE (from URL)
        
#         sh = None
#         try:
#             if sheet_id:
#                 sh = client.open_by_key(sheet_id)
#             else:
#                 sh = client.open("Feedback Dashboard Sync")
#         except Exception as e:
#             # Fallback to smart search
#             try:
#                 all_sheets = client.openall()
#                 for s in all_sheets:
#                     if "feedback" in s.title.lower():
#                         sh = s
#                         break
#             except: pass
                    
#         if not sh:
#             try:
#                 visible_names = [s.title for s in client.openall()]
#             except: visible_names = ["Drive API not enabled?"]
#             return JsonResponse({
#                 'status': 'error', 
#                 'message': f'NOT CONNECTED! Total Sheets Visible: {len(visible_names)}. Please SHARE your sheet with: {creds.service_account_email} and click SEND on Google Sheet.'
#             })
            
#         worksheet = sh.get_worksheet(0)
#         if not worksheet:
#             worksheet = sh.add_worksheet(title="Dashboard", rows="100", cols="20")

#         # 4. Filter data & push
#         trainers = Trainer.objects.all()
#         data = [["TRAINER NAME", "COURSE / TECHNOLOGY", "UNDERSTANDING", "REGULARITY", "PRACTICALS", "DOUBTS", "AVG RATING", "RESPONSES", "LAST SYNC"]]
        
#         for t in trainers:
#             feedback_qs = Feedback.objects.filter(trainer_name=t.name)
#             stats = get_feedback_stats(feedback_qs)
#             data.append([
#                 t.name,
#                 t.course,
#                 f"{stats['q1_avg']:.1f}",
#                 f"{stats['q2_avg']:.1f}",
#                 f"{stats['q3_avg']:.1f}",
#                 f"{stats['q4_avg']:.1f}",
#                 f"{stats['avg_rating']:.1f}",
#                 stats['total_responses'],
#                 datetime.now().strftime('%Y-%m-%d %H:%M')
#             ])
            
#         # 5. Push to Sheet
#         worksheet.clear()
#         worksheet.update('A1', data)
        
#         return JsonResponse({
#             'status': 'success', 
#             'message': f'Hooray! Data synced to Google Sheet. Check your Google Drive.'
#         })

#     except Exception as e:
#         return JsonResponse({'status': 'error', 'message': f'API Error: {str(e)}'})


# def send_bulk_whatsapp(request):
#     if request.method != 'POST':
#         return JsonResponse({'status': 'error', 'message': 'Only POST allowed'}, status=405)

#     try:
#         data = json.loads(request.body)
#         batch_ids = data.get('batch_ids', [])
#         message_template = data.get('message', '')

#         if not batch_ids or not message_template:
#             return JsonResponse({'status': 'error', 'message': 'Missing batch_ids or message'}, status=400)

#         # Fetch students from selected batches
#         students = Student.objects.filter(current_batch_id__in=batch_ids).select_related('current_batch')
        
#         results = {
#             'total': students.count(),
#             'sent': 0,
#             'failed': 0,
#             'errors': []
#         }

#         # WATI Config from settings
#         base_url = getattr(settings, 'WATI_BASE_URL', '').rstrip('/')
#         api_token = getattr(settings, 'WATI_API_TOKEN', '')

#         # SIMULATION MODE: If credentials are placeholders, simulate success for testing
#         is_simulation = not api_token or "YOUR_WATI_TOKEN" in api_token or not base_url

#         for student in students:
#             if not student.phone_number:
#                 results['failed'] += 1
#                 results['errors'].append(f"Missing phone for {student.name}")
#                 continue

#             # Personalize message
#             b_name = student.current_batch.batch_name if student.current_batch else "your batch"
#             d_str = datetime.now().strftime('%d-%b-%Y')

#             personalized_msg = message_template.replace('{name}', student.name or "Student")
#             personalized_msg = personalized_msg.replace('{batch}', b_name)
#             personalized_msg = personalized_msg.replace('{date}', d_str)

#             if is_simulation:
#                 # Simulate network delay and success
#                 time.sleep(0.2)
#                 results['sent'] += 1
#                 WhatsAppMessageLog.objects.create(
#                     student=student,
#                     batch=student.current_batch,
#                     message_body=personalized_msg,
#                     status='Sent (Simulated)'
#                 )
#                 continue

#             # REAL API MODE - Only runs if real credentials exist
#             phone = str(student.phone_number).strip().replace(' ', '').replace('-', '')
#             if len(phone) == 10:
#                 phone = "91" + phone
#             elif phone.startswith('+91'):
#                 phone = phone[1:]
            
#             # WATI API Call
#             api_endpoint = f"{base_url}/api/v1/sendSessionMessage/{phone}"
#             headers = {
#                 "Authorization": api_token,
#                 "Content-Type": "application/json"
#             }
#             payload = {"messageText": personalized_msg}

#             try:
#                 response = requests.post(api_endpoint, headers=headers, json=payload, timeout=10)
#                 resp_data = response.json()

#                 if response.status_code == 200 and resp_data.get('result') == 'success':
#                     results['sent'] += 1
#                     WhatsAppMessageLog.objects.create(
#                         student=student,
#                         batch=student.current_batch,
#                         message_body=personalized_msg,
#                         status='Sent'
#                     )
#                 else:
#                     results['failed'] += 1
#                     err_msg = resp_data.get('errors', 'Unknown API Error')
#                     results['errors'].append(f"Failed {phone}: {err_msg}")
#                     WhatsAppMessageLog.objects.create(
#                         student=student,
#                         batch=student.current_batch,
#                         message_body=personalized_msg,
#                         status='Failed',
#                         error_response=str(resp_data)
#                     )
#             except Exception as e:
#                 results['failed'] += 1
#                 results['errors'].append(f"Network error for {phone}: {str(e)}")
            
#             # Add a small delay to prevent rapid-fire rate limits
#             time.sleep(0.5)

#         return JsonResponse({
#             'status': 'success',
#             'summary': results
#         })

#     except Exception as e:
#         return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def get_announcement_logs(request):
    logs = WhatsAppMessageLog.objects.all().order_by('-sent_at')[:20]
    log_data = []
    for log in logs:
        log_data.append({
            'student': log.student.name,
            'batch': log.batch.batch_name if log.batch else 'N/A',
            'message': log.message_body[:50] + '...' if len(log.message_body) > 50 else log.message_body,
            'status': log.status,
            'time': log.sent_at.strftime('%d-%b %H:%M'),
            'error': log.error_response if log.error_response else ''
        })
    return JsonResponse({'status': 'success', 'logs': log_data})

def import_students(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        file = request.FILES['csv_file']
        try:
            content = file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(content)
            count = 0
            for row in reader:
                # Support multiple column name formats
                sid = row.get('sid') or row.get('Student ID') or row.get('SID')
                name = row.get('name') or row.get('Student Name') or row.get('Name')
                phone = row.get('phone') or row.get('Phone Number') or row.get('Phone')
                email = row.get('email') or row.get('Email')
                
                if sid:
                    Student.objects.update_or_create(
                        sid=sid,
                        defaults={
                            'name': name if name else '',
                            'phone_number': phone if phone else '',
                            'email': email if email else ''
                        }
                    )
                    count += 1
            return JsonResponse({'status': 'success', 'message': f'Hooray! Successfully imported {count} students.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Please upload a valid CSV file.'})

# @login_required # Optional, but recommended. Wait, dashboard views usually don't have it explicitly if middleware handles it.
# def send_single_whatsapp(request):
#     if request.method != 'POST':
#         return JsonResponse({'status': 'error', 'message': 'Only POST allowed'}, status=405)

#     try:
#         data = json.loads(request.body)
#         phone = data.get('phone')
#         message = data.get('message')

#         if not phone or not message:
#             return JsonResponse({'status': 'error', 'message': 'Missing phone or message'}, status=400)

#         # Ensure phone has country code
#         clean_phone = str(phone).strip().replace(' ', '').replace('-', '')
#         if len(clean_phone) == 10:
#             clean_phone = "+91" + clean_phone
#         elif not clean_phone.startswith('+'):
#             clean_phone = "+" + clean_phone

#         # Pywhatkit Automation (as per screenshot)
#         pwk.sendwhatmsg_instantly(clean_phone, message, 10, tab_close=True)

#         return JsonResponse({
#             'status': 'success',
#             'message': f'Hooray! Instant WhatsApp window opened for {clean_phone}.'
#         })
#     except Exception as e:
#         return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# def send_batch_individual_whatsapp(request):
#     if request.method != 'POST':
#         return JsonResponse({'status': 'error', 'message': 'Only POST allowed'}, status=405)

#     try:
#         data = json.loads(request.body)
#         batch_id = data.get('batch_id')
#         message_template = data.get('message', '')

#         if not batch_id or not message_template:
#             return JsonResponse({'status': 'error', 'message': 'Missing batch_id or message'}, status=400)

#         # Handle multiple IDs if provided
#         batch_ids = [bid.strip() for bid in str(batch_id).split(',') if bid.strip()]
#         students = Student.objects.filter(current_batch_id__in=batch_ids).select_related('current_batch')
        
#         if not students.exists():
#             return JsonResponse({'status': 'error', 'message': 'No students found'}, status=404)

#         count = 0
#         for student in students:
#             if not student.phone_number:
#                 continue
                
#             phone = str(student.phone_number).strip().replace(' ', '').replace('-', '')
#             if len(phone) == 10:
#                 phone = "+91" + phone
#             elif not phone.startswith('+'):
#                 phone = "+" + phone
            
#             # Personalize message using student's specific batch context
#             b_name = student.current_batch.batch_name if student.current_batch else "your batch"
#             personalized_msg = message_template.replace('{name}', student.name or "Student").replace('{batch}', b_name)
            
#             # Pywhatkit Automation - Opens individual tabs
#             # WARNING: This will open many tabs if the batch is large. 
#             # But this is what "single single" send implies for pywhatkit.
#             pwk.sendwhatmsg_instantly(phone, personalized_msg, 15, tab_close=True)
#             time.sleep(3) # Small buffer to let the browser process
            
#             WhatsAppMessageLog.objects.create(
#                 student=student,
#                 batch=student.current_batch,
#                 message_body=personalized_msg,
#                 status='Sent (Personal)'
#             )
#             count += 1

#         return JsonResponse({
#             'status': 'success',
#             'message': f'Processing complete! Opened {count} WhatsApp windows.'
#         })
#     except Exception as e:
#         return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
