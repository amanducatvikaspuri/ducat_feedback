from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Trainer
from form.models import Attendance
from feedback.models import Feedback
from django.db.models import Avg, Count, Prefetch
import json
import csv
from datetime import datetime, timedelta
from django.utils import timezone
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
from django.core.mail import send_mail
from form.models import Student, Attendance
from .models import Batch, DailyAttendance
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
# import pywhatkit as pwk

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def normalize_feedback_rows(feedback_source):
    if isinstance(feedback_source, list):
        return feedback_source
    try:
        return list(feedback_source.order_by('-submitted_at').values(
            'id', 'student_id', 'student_name', 'email', 'phone', 'trainer_name',
            'batch_type', 'batch_timing', 'phase', 'review_description',
            'ques1_rating', 'ques2_rating', 'ques3_rating', 'ques4_rating',
            'batch_mode', 'technology', 'submitted_at'
        ))
    except Exception:
        return list(feedback_source)


def get_feedback_stats(feedback_source, batch_lookup=None):
    rows = normalize_feedback_rows(feedback_source)

    stats = {
        'q1': 0.0,
        'q2': 0.0,
        'q3': 0.0,
        'q4': 0.0,
        'f_count': 0,
        'q1_5': 0,
        'q1_4': 0,
        'q1_3': 0,
        'q1_lt3': 0,
        'q2_5': 0,
        'q2_4': 0,
        'q2_3': 0,
        'q2_lt3': 0,
        'q3_5': 0,
        'q3_4': 0,
        'q3_3': 0,
        'q3_lt3': 0,
        'q4_5': 0,
        'q4_4': 0,
        'q4_3': 0,
        'q4_lt3': 0,
        'p1_count': 0,
        'p2_count': 0,
        'p3_count': 0,
        'p4_count': 0,
        'p5_count': 0,
    }

    feedback_list = []
    dist = [0, 0, 0, 0]

    for f in rows:
        q1 = f.get('ques1_rating') or 0
        q2 = f.get('ques2_rating') or 0
        q3 = f.get('ques3_rating') or 0
        q4 = f.get('ques4_rating') or 0
        stats['q1'] += q1
        stats['q2'] += q2
        stats['q3'] += q3
        stats['q4'] += q4
        stats['f_count'] += 1

        if q1 == 5:
            stats['q1_5'] += 1
        elif q1 == 4:
            stats['q1_4'] += 1
        elif q1 == 3:
            stats['q1_3'] += 1
        else:
            stats['q1_lt3'] += 1

        if q2 == 5:
            stats['q2_5'] += 1
        elif q2 == 4:
            stats['q2_4'] += 1
        elif q2 == 3:
            stats['q2_3'] += 1
        else:
            stats['q2_lt3'] += 1

        if q3 == 5:
            stats['q3_5'] += 1
        elif q3 == 4:
            stats['q3_4'] += 1
        elif q3 == 3:
            stats['q3_3'] += 1
        else:
            stats['q3_lt3'] += 1

        if q4 == 5:
            stats['q4_5'] += 1
        elif q4 == 4:
            stats['q4_4'] += 1
        elif q4 == 3:
            stats['q4_3'] += 1
        else:
            stats['q4_lt3'] += 1

        phase = str(f.get('phase') or '').strip()
        if phase.upper() == 'P-1':
            stats['p1_count'] += 1
        elif phase.upper() == 'P-2':
            stats['p2_count'] += 1
        elif phase.upper() == 'P-3':
            stats['p3_count'] += 1
        elif phase.upper() == 'P-4':
            stats['p4_count'] += 1
        elif phase.upper() == 'P-5':
            stats['p5_count'] += 1

        f_avg = (q1 + q2 + q3 + q4) / 4.0
        if f_avg >= 4.5:
            dist[0] += 1
        elif f_avg >= 3.5:
            dist[1] += 1
        elif f_avg >= 2.5:
            dist[2] += 1
        else:
            dist[3] += 1

        f_key = (
            str(f.get('trainer_name') or '').strip().upper(),
            str(f.get('batch_timing') or '').strip().upper(),
            str(f.get('batch_type') or '').strip().upper()
        )
        display_batch_name = (batch_lookup or {}).get(f_key, f.get('technology') or 'N/A')

        feedback_list.append({
            'sid': f.get('student_id'),
            'name': f.get('student_name'),
            'email': f.get('email'),
            'phone': f.get('phone'),
            'trainer': f.get('trainer_name') or '-',
            'batch': f.get('batch_type') or 'N/A',
            'timing': f.get('batch_timing') or 'N/A',
            'phase': phase or 'N/A',
            'review': f.get('review_description'),
            'q1': q1,
            'q2': q2,
            'q3': q3,
            'q4': q4,
            'avg': round(f_avg, 1),
            'date': f.get('submitted_at').strftime('%Y-%m-%d') if f.get('submitted_at') else 'N/A',
            'batch_mode': f.get('batch_mode') or 'Offline',
            'technology': f.get('technology') or 'N/A',
            'batch_name': display_batch_name,
        })

    if stats['f_count'] > 0:
        stats['q1'] = round(stats['q1'] / stats['f_count'], 1)
        stats['q2'] = round(stats['q2'] / stats['f_count'], 1)
        stats['q3'] = round(stats['q3'] / stats['f_count'], 1)
        stats['q4'] = round(stats['q4'] / stats['f_count'], 1)
    else:
        stats['q1'] = stats['q2'] = stats['q3'] = stats['q4'] = 0.0

    rating = ((stats['q1'] or 0) + (stats['q2'] or 0) + (stats['q3'] or 0) + (stats['q4'] or 0)) / 4 if stats['f_count'] > 0 else 0.0

    return {
        'q1': stats['q1'],
        'q2': stats['q2'],
        'q3': stats['q3'],
        'q4': stats['q4'],
        'count': stats['f_count'],
        'avg': round(rating, 1),
        'list': feedback_list,
        'q1_dist': [stats['q1_5'], stats['q1_4'], stats['q1_3'], stats['q1_lt3']],
        'q2_dist': [stats['q2_5'], stats['q2_4'], stats['q2_3'], stats['q2_lt3']],
        'q3_dist': [stats['q3_5'], stats['q3_4'], stats['q3_3'], stats['q3_lt3']],
        'q4_dist': [stats['q4_5'], stats['q4_4'], stats['q4_3'], stats['q4_lt3']],
        'dist': dist,
        'p1': stats['p1_count'],
        'p2': stats['p2_count'],
        'p3': stats['p3_count'],
        'p4': stats['p4_count'],
        'p5': stats['p5_count'],
    }

def check_and_send_batch_notifications():
    try:
        today = timezone.now().date()
        ended_batches = Batch.objects.filter(end_date__lte=today, email_sent=False)
        for batch in ended_batches:
            students = Student.objects.filter(
                models.Q(current_batch=batch) |
                models.Q(sid__in=Attendance.objects.filter(week_type=batch.batch_type, batch_time=batch.timing).values_list('student_id', flat=True))
            ).distinct()

            student_list_str = "\n".join([f"ID: {s.sid} - Name: {s.name}" for s in students])

            subject = f"Batch Ended Notification: {batch.batch_name} ({batch.batch_type})"
            message = (
                f"Hello,\n\n"
                f"This is an automated notification to inform you that the following batch has ended.\n\n"
                f"Trainer: {batch.trainer.name}\n"
                f"Course: {batch.batch_name}\n"
                f"Timing: {batch.timing}\n"
                f"Mode: {batch.batch_type}\n"
                f"End Date: {batch.end_date.strftime('%d-%b-%Y') if batch.end_date else 'N/A'}\n\n"
                f"Total Students: {students.count()}\n\n"
                f"Student List:\n{student_list_str}\n\n"
                f"Best regards,\nDucat Vikaspuri System"
            )

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                ['shubham.vikaspuri007@gmail.com'],
                fail_silently=False,
            )

            batch.email_sent = True
            batch.save()
            print(f"Sent end notification for batch {batch.id}")
    except Exception as e:
        print(f"Error checking batch notifications: {e}")

def parse_time_for_sort(timing_str):
    import re
    from datetime import time
    if not timing_str:
        return time(23, 59)

    match = re.search(r'(\d{1,2}):(\d{2})(?:\s*(AM|PM|am|pm))?', timing_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        ampm = match.group(3)

        if ampm:
            ampm = ampm.lower()
            if ampm == 'pm' and hour < 12:
                hour += 12
            if ampm == 'am' and hour == 12:
                hour = 0

        try:
            return time(hour=hour, minute=minute)
        except ValueError:
            pass

    return time(23, 59)

from django.http import JsonResponse
from django.db.models import Prefetch

@login_required
def index(request):
    check_and_send_batch_notifications()
    branch_filter = request.GET.get('branch', 'Vikaspuri').strip()

    # OPTIMIZATION: Only run cleanup during a full page refresh, not during fast tab switches
    if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        existing_sids = set(Student.objects.values_list('sid', flat=True))
        Attendance.objects.exclude(student_id__in=existing_sids).delete()
        Feedback.objects.exclude(student_id__in=existing_sids).delete()

    # OPTIMIZATION: Optimized prefetching for related batches to avoid looping database queries
    trainers = Trainer.objects.filter(branch__iexact=branch_filter).prefetch_related(
        Prefetch(
            'batches',
            queryset=Batch.objects.all().order_by('timing').prefetch_related(
                Prefetch('enrolled_students', queryset=Student.objects.only('sid', 'name', 'email'))
            )
        )
    )

    all_trainers_in_branch = list(trainers.values_list('name', flat=True).order_by('name'))
    trainer_filter = ""
    trainers_data = []

    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    month_name = request.GET.get('month')
    year_val = request.GET.get('year')

    trainer_names = list(trainers.values_list('name', flat=True))
    trainer_names_upper = [name.upper() for name in trainer_names]

    all_attendance = Attendance.objects.filter(
        models.Q(branch=branch_filter) &
        (models.Q(trainer_name__in=trainer_names) | models.Q(trainer_name__in=trainer_names_upper))
    ).order_by('-submitted_at')

    all_feedback_qs = Feedback.objects.filter(
        models.Q(branch=branch_filter) &
        (models.Q(trainer_name__in=trainer_names) | models.Q(trainer_name__in=trainer_names_upper))
    ).order_by('-submitted_at')

    if start_date and end_date:
        all_attendance = all_attendance.filter(submitted_at__date__range=[start_date, end_date])
        all_feedback_qs = all_feedback_qs.filter(submitted_at__date__range=[start_date, end_date])

    if month_name:
        try:
            m_num = datetime.strptime(month_name, "%B").month
            all_attendance = all_attendance.filter(submitted_at__month=m_num)
            all_feedback_qs = all_feedback_qs.filter(submitted_at__month=m_num)
        except ValueError:
            pass

    if year_val:
        all_attendance = all_attendance.filter(submitted_at__year=year_val)
        all_feedback_qs = all_feedback_qs.filter(submitted_at__year=year_val)

    selected_date = start_date if (start_date and start_date == end_date) else timezone.now().date().isoformat()
    if isinstance(selected_date, datetime):
        selected_date = selected_date.date().isoformat()

    batch_lookup = {}
    for trainer in trainers:
        for batch in trainer.batches.all():
            batch_lookup[(trainer.name.strip().upper(), batch.timing.strip().upper(), batch.batch_type.strip().upper())] = batch.batch_name

    all_feedback_rows = normalize_feedback_rows(all_feedback_qs)

    students_in_branch = list(Student.objects.filter(branch__iexact=branch_filter))

    for t in trainers:
        all_batches = list(t.batches.all())
        today_date = timezone.now().date()
        display_batches = [b for b in all_batches if b.status == 'Active' and (not b.end_date or b.end_date >= today_date)]

        valid_signatures = set((b.batch_type.strip().upper(), b.timing.strip().upper()) for b in all_batches)

        trainer_attendance_list = []
        for att in all_attendance.filter(trainer_name__iexact=t.name).values(
            'student_id', 'name', 'today_topic', 'technology', 'batch_mode', 'week_type', 'batch_time', 'submitted_at'
        ):
            if (str(att['week_type']).strip().upper(), str(att['batch_time']).strip().upper()) in valid_signatures:
                trainer_attendance_list.append({
                    'sid': att['student_id'],
                    'name': att['name'],
                    'topic': att['today_topic'],
                    'technology': att['technology'],
                    'mode': att['batch_mode'],
                    'week_type': att['week_type'],
                    'batch_time': att['batch_time'],
                    'date': att['submitted_at'].strftime('%Y-%m-%d %H:%M') if att['submitted_at'] else 'N/A'
                })

        real_submission_count = len(trainer_attendance_list)
        total_target = sum(b.students_count for b in display_batches)

        trainer_feedback_rows = [
            f for f in all_feedback_rows
            if str(f.get('trainer_name') or '').strip().upper() == t.name.strip().upper()
        ]

        valid_feedback_rows = [
            f for f in trainer_feedback_rows
            if (str(f.get('batch_type') or '').strip().upper(), str(f.get('batch_timing') or '').strip().upper()) in valid_signatures
        ]

        trainer_phase_stats = {
            p: {
                'overall': get_feedback_stats([f for f in valid_feedback_rows if str(f.get('phase') or '').strip().upper() == p.upper()], batch_lookup),
                'online': get_feedback_stats([f for f in valid_feedback_rows if str(f.get('phase') or '').strip().upper() == p.upper() and str(f.get('batch_mode') or '').strip().lower() == 'online'], batch_lookup),
                'offline': get_feedback_stats([f for f in valid_feedback_rows if str(f.get('phase') or '').strip().upper() == p.upper() and str(f.get('batch_mode') or '').strip().lower() == 'offline'], batch_lookup),
            } for p in ['P-1', 'P-2', 'P-3', 'P-4', 'P-5']
        }

        phase_stats = {
            'overall': get_feedback_stats(valid_feedback_rows, batch_lookup),
            'online': get_feedback_stats([f for f in valid_feedback_rows if str(f.get('batch_mode') or '').strip().lower() == 'online'], batch_lookup),
            'offline': get_feedback_stats([f for f in valid_feedback_rows if str(f.get('batch_mode') or '').strip().lower() == 'offline'], batch_lookup),
            'phases': trainer_phase_stats
        }

        rating = phase_stats['overall']['avg']

        # Build batch-specific attendance lists so the attendance modal can show actual attendees
        batch_attendance_map = {
            b.id: [
                att for att in trainer_attendance_list
                if str(att['week_type']).strip().upper() == b.batch_type.strip().upper()
                and str(att['batch_time']).strip().upper() == b.timing.strip().upper()
            ]
            for b in all_batches
        }

        # Daily attendance counts should reflect the currently selected date (today by default)
        selected_date_str = str(selected_date) if selected_date else timezone.now().date().isoformat()
        batch_daily_attendance_map = {
            batch_id: [att for att in entries if att['date'].startswith(selected_date_str)]
            for batch_id, entries in batch_attendance_map.items()
        }

        trainer_dict = {
            'name': t.name,
            'course': t.course,
            'rating': round(rating, 1),
            'real_count': real_submission_count,
            'target_count': total_target if total_target > 0 else 30,
            'month': display_batches[0].start_date.strftime("%B") if (len(display_batches) > 0 and display_batches[0].start_date) else "January",
            'year': display_batches[0].start_date.year if (len(display_batches) > 0 and display_batches[0].start_date) else "2025",
            'trainer_attendance_list': trainer_attendance_list,
            'roster': {'overall': [], 'online': [], 'offline': []},
            'phase_stats': phase_stats,
            'batches': [
                {
                    'id': b.id,
                    'type': b.batch_type,
                    'batch_name': b.batch_name,
                    'target': b.students_count,
                    'timing': b.timing,
                    'start_date': b.start_date.strftime('%d %b, %Y') if b.start_date else 'N/A',
                    'end_date': b.end_date.strftime('%d %b, %Y') if b.end_date else 'N/A',
                    'attendance_list': batch_attendance_map.get(b.id, []),
                    'enrolled_students': [
                        {
                            'sid': s.sid,
                            'name': s.name,
                            'email': s.email or 'N/A'
                        }
                        for s in b.enrolled_students.all()
                    ],
                    'students_total': len(set(att['sid'] for att in batch_attendance_map.get(b.id, []))) or len(list(b.enrolled_students.all())),
                    'status': b.status,
                    'present_count': len(set(att['sid'] for att in batch_daily_attendance_map.get(b.id, []))),
                    'attendance_marked': bool(batch_daily_attendance_map.get(b.id, [])),
                    'phase_stats': {
                        p: {
                            'overall': get_feedback_stats([
                                f for f in valid_feedback_rows
                                if str(f.get('batch_type') or '').strip().upper() == b.batch_type.strip().upper() and str(f.get('batch_timing') or '').strip().upper() == b.timing.strip().upper() and str(f.get('phase') or '').strip().upper() == p.upper()
                            ], batch_lookup),
                            'online': get_feedback_stats([
                                f for f in valid_feedback_rows
                                if str(f.get('batch_type') or '').strip().upper() == b.batch_type.strip().upper() and str(f.get('batch_timing') or '').strip().upper() == b.timing.strip().upper() and str(f.get('phase') or '').strip().upper() == p.upper() and str(f.get('batch_mode') or '').strip().lower() == 'online'
                            ], batch_lookup),
                            'offline': get_feedback_stats([
                                f for f in valid_feedback_rows
                                if str(f.get('batch_type') or '').strip().upper() == b.batch_type.strip().upper() and str(f.get('batch_timing') or '').strip().upper() == b.timing.strip().upper() and str(f.get('phase') or '').strip().upper() == p.upper() and str(f.get('batch_mode') or '').strip().lower() == 'offline'
                            ], batch_lookup),
                        } for p in ['P-1', 'P-2', 'P-3', 'P-4', 'P-5']
                    }
                } for b in all_batches
            ]
        }
        trainers_data.append(trainer_dict)

    all_students_data = [
        {
            'sid': s.sid,
            'name': s.name,
            'phone': s.phone_number or 'N/A',
            'email': s.email or 'N/A',
            'technology': s.course or 'N/A',
            'joining_date': s.joining_date.strftime('%d-%b-%Y') if s.joining_date else 'N/A',
            'current_batch_id': s.current_batch.id if s.current_batch else None,
            'current_batch_name': s.current_batch.batch_name if s.current_batch else None
        } for s in students_in_branch
    ]

    global_stats = get_feedback_stats(all_feedback_rows, batch_lookup)
    today = timezone.now().date()

    # Optimize trend lookups
    trend_weekly = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        count = all_attendance.filter(submitted_at__date=d).count()
        trend_weekly.append({'label': d.strftime('%a %d %b'), 'data': count, 'date': d.isoformat()})

    global_stats['trend_weekly'] = trend_weekly
    global_stats['trend_monthly'] = []

    context_data = {
        'trainers_data': trainers_data,
        'all_students_data': all_students_data,
        'selected_date': selected_date,
        'global_stats': global_stats,
        'total_students_count': len(students_in_branch),
        'total_feedbacks_count': len(all_feedback_rows),
        'active_branch': branch_filter,
        'all_trainers_in_branch': all_trainers_in_branch,
    }
    print(context_data['total_students_count'], context_data['total_feedbacks_count'])
    # CHECK FOR AJAX: If requested by Tab Switcher via JS, send pure raw fast JSON data
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse(context_data)

    # Fallback context serialization for standard initial loads
    context = {
        'trainers_json': json.dumps(trainers_data),
        'all_students_json': json.dumps(all_enrolled_data if 'all_enrolled_data' in locals() else all_students_data),
        'selected_date': selected_date,
        'global_stats_json': json.dumps(global_stats),
        'total_students_count': len(students_in_branch),
        'total_feedbacks_count': all_feedback_qs.count(),
        'active_branch': branch_filter,
        'all_trainers_in_branch': all_trainers_in_branch,
        'recent_announcements': []
    }
    return render(request, 'dashboard/index.html', context)
# @login_required
# def index(request):
#     check_and_send_batch_notifications()
#     branch_filter = request.GET.get('branch', 'Vikaspuri')

#     # CLEANUP: Remove orphaned data that no longer has a matching Student record (User Request)
#     existing_sids = set(Student.objects.values_list('sid', flat=True))
#     Attendance.objects.exclude(student_id__in=existing_sids).delete()
#     Feedback.objects.exclude(student_id__in=existing_sids).delete()

#     trainers = Trainer.objects.prefetch_related('batches').filter(branch=branch_filter)

#     # Get all trainers for the dropdown
#     all_trainers_in_branch = list(Trainer.objects.filter(branch=branch_filter).values_list('name', flat=True).order_by('name'))
#     # Trainer filter removed from here to keep Home Page always full.
#     # Filtering is now handled client-side in the Feedback Modal.
#     trainer_filter = ""

#     trainers_data = []

#     # Date Filtering Logic (Range, Month, Year)
#     start_date = request.GET.get('start')
#     end_date = request.GET.get('end')
#     month_name = request.GET.get('month')
#     year_val = request.GET.get('year')

#     # Base Querysets (Filtered by branch)
#     trainer_names = list(trainers.values_list('name', flat=True))
#     # Normalize trainer names for case-insensitive matching
#     trainer_names_upper = [name.upper() for name in trainer_names]

#     all_attendance = Attendance.objects.filter(
#         models.Q(branch=branch_filter) &
#         (models.Q(trainer_name__in=trainer_names) | models.Q(trainer_name__in=trainer_names_upper))
#     ).order_by('-submitted_at')

#     all_feedback_qs = Feedback.objects.filter(
#         models.Q(branch=branch_filter) &
#         (models.Q(trainer_name__in=trainer_names) | models.Q(trainer_name__in=trainer_names_upper))
#     ).order_by('-submitted_at')

#     # Apply Range Filter
#     if start_date and end_date:
#         all_attendance = all_attendance.filter(submitted_at__date__range=[start_date, end_date])
#         all_feedback_qs = all_feedback_qs.filter(submitted_at__date__range=[start_date, end_date])

#     # Apply Month Filter
#     if month_name:
#         # Convert month name to number
#         try:
#             m_num = datetime.strptime(month_name, "%B").month
#             all_attendance = all_attendance.filter(submitted_at__month=m_num)
#             all_feedback_qs = all_feedback_qs.filter(submitted_at__month=m_num)
#         except ValueError: pass

#     # Apply Year Filter
#     if year_val:
#         all_attendance = all_attendance.filter(submitted_at__year=year_val)
#         all_feedback_qs = all_feedback_qs.filter(submitted_at__year=year_val)

#     # Daily Attendance Filter (for historical viewing)
#     selected_date = start_date if (start_date and start_date == end_date) else timezone.now().date().isoformat()
#     if isinstance(selected_date, datetime):
#         selected_date = selected_date.date().isoformat()

#     daily_attendance_qs = DailyAttendance.objects.filter(date=selected_date)

#     for t in trainers:
#         # Separate active and closed batches
#         all_batches = sorted(t.batches.all(), key=lambda b: parse_time_for_sort(b.timing))
#         today_date = timezone.now().date()
#         active_batches = [b for b in all_batches if b.status == 'Active' and (not b.end_date or b.end_date >= today_date)]
#         closed_batches = [b for b in all_batches if b.status == 'Closed' or (b.status == 'Active' and b.end_date and b.end_date < today_date)]

#         # We'll process active_batches for the main display,
#         # but keep closed_batches available for the "Archives" view
#         display_batches = active_batches

#         # Create signature of valid batches for THIS trainer in THIS branch
#         # Normalizing signatures to uppercase for robust matching
#         valid_signatures = set((b.batch_type.upper(), b.timing.upper()) for b in all_batches)

#         # Filter trainer specific stuff from the already filtered base sets
#         # Only include records that match a batch signature belonging to this branch's trainer
#         trainer_attendance_qs = all_attendance.filter(trainer_name__iexact=t.name)
#         trainer_attendance_list = []
#         for att in trainer_attendance_qs:
#             if (att.week_type.upper(), att.batch_time.upper()) in valid_signatures:
#                 trainer_attendance_list.append({
#                     'sid': att.student_id,
#                     'name': att.name,
#                     'topic': att.today_topic,
#                     'technology': att.technology,
#                     'mode': att.batch_mode,
#                     'week_type': att.week_type,
#                     'batch_time': att.batch_time,
#                     'date': att.submitted_at.strftime('%Y-%m-%d %H:%M')
#                 })

#         real_submission_count = len(trainer_attendance_list)
#         total_target = sum(b.students_count for b in display_batches)

#         # Calculate feedback stats matching valid signatures
#         feedback_qs = all_feedback_qs.filter(trainer_name__iexact=t.name)
#         feedback_list = [fb.id for fb in feedback_qs if (fb.batch_type.upper(), fb.batch_timing.upper()) in valid_signatures]
#         feedback_qs = feedback_qs.filter(id__in=feedback_list)

#         # Phase Stats Breakdown
#         trainer_phase_stats = {
#             p: {
#                 'overall': get_feedback_stats(feedback_qs.filter(phase=p)),
#                 'online': get_feedback_stats(feedback_qs.filter(phase=p, batch_mode="Online")),
#                 'offline': get_feedback_stats(feedback_qs.filter(phase=p, batch_mode="Offline")),
#             } for p in ['P-1', 'P-2', 'P-3', 'P-4', 'P-5']
#         }

#         phase_stats = {
#             'overall': get_feedback_stats(feedback_qs),
#             'online': get_feedback_stats(feedback_qs.filter(batch_mode="Online")),
#             'offline': get_feedback_stats(feedback_qs.filter(batch_mode="Offline")),
#             'phases': trainer_phase_stats
#         }

#         # Rating for main table
#         rating = phase_stats['overall']['avg']

#         trainer_dict = {
#             'name': t.name,
#             'course': t.course,
#             'rating': round(rating, 1),
#             'real_count': real_submission_count,
#             'target_count': total_target if total_target > 0 else 30, # Default target for aesthetics
#             'month': display_batches[0].start_date.strftime("%B") if (len(display_batches) > 0 and display_batches[0].start_date) else "January",
#             'year': display_batches[0].start_date.year if (len(display_batches) > 0 and display_batches[0].start_date) else "2025",
#             'trainer_attendance_list': trainer_attendance_list,
#             'roster': {
#                 'overall': [
#                     {'sid': s.sid, 'name': s.name, 'batchSet': list(set(trainer_attendance_qs.filter(student_id=s.sid).values_list('batch_time', flat=True)))}
#                     for s in Student.objects.filter(models.Q(current_batch__trainer=t) | models.Q(sid__in=trainer_attendance_qs.values_list('student_id', flat=True)) | models.Q(sid__in=feedback_qs.values_list('student_id', flat=True))).distinct()
#                 ],
#                 'online': [
#                     {'sid': s.sid, 'name': s.name, 'batchSet': list(set(trainer_attendance_qs.filter(student_id=s.sid).values_list('batch_time', flat=True)))}
#                     for s in Student.objects.filter(models.Q(current_batch__trainer=t, current_batch__batch_type__icontains='Online') | models.Q(sid__in=trainer_attendance_qs.filter(batch_mode='Online').values_list('student_id', flat=True)) | models.Q(sid__in=feedback_qs.filter(batch_mode='Online').values_list('student_id', flat=True))).distinct()
#                 ],
#                 'offline': [
#                     {'sid': s.sid, 'name': s.name, 'batchSet': list(set(trainer_attendance_qs.filter(student_id=s.sid).values_list('batch_time', flat=True)))}
#                     for s in Student.objects.filter(models.Q(current_batch__trainer=t, current_batch__batch_type__icontains='Offline') | models.Q(sid__in=trainer_attendance_qs.filter(batch_mode='Offline').values_list('student_id', flat=True)) | models.Q(sid__in=feedback_qs.filter(batch_mode='Offline').values_list('student_id', flat=True))).distinct()
#                 ],
#             },
#             'phase_stats': phase_stats, # Global trainer phase stats
#             'batches': [
#                 {
#                     'id': b.id,
#                     'type': b.batch_type,
#                     'batch_name': b.batch_name,
#                     'target': b.students_count,
#                     'timing': b.timing,
#                     'start_date': b.start_date.strftime('%d %b, %Y') if b.start_date else 'N/A',
#                     'end_date': b.end_date.strftime('%d %b, %Y') if b.end_date else 'N/A',
#                     'enrolled_students': [
#                         {'sid': s.sid, 'name': s.name, 'email': s.email} for s in Student.objects.filter(
#                             models.Q(current_batch=b) |
#                             models.Q(sid__in=(lambda q: q.filter(submitted_at__gte=b.start_date, submitted_at__lte=b.end_date if (b.end_date and b.status == 'Closed') else timezone.now()) if b.start_date else q)(trainer_attendance_qs.filter(week_type=b.batch_type, batch_time=b.timing)).values_list('student_id', flat=True)) |
#                             models.Q(sid__in=feedback_qs.filter(batch_type__iexact=b.batch_type, batch_timing__iexact=b.timing).values_list('student_id', flat=True))
#                         ).distinct()
#                     ],
#                     'students_total': 0, # Will be updated below
#                     'attendance_marked': daily_attendance_qs.filter(batch=b).exists() or trainer_attendance_qs.filter(week_type=b.batch_type, batch_time=b.timing, submitted_at__date=selected_date).exists(),
#                     'present_count': len(set(daily_attendance_qs.filter(batch=b, is_present=True).values_list('student_sid', flat=True)) | set(trainer_attendance_qs.filter(week_type=b.batch_type, batch_time=b.timing, submitted_at__date=selected_date).values_list('student_id', flat=True))),
#                     'form_submission_sids': list(trainer_attendance_qs.filter(week_type=b.batch_type, batch_time=b.timing, submitted_at__date=selected_date).values_list('student_id', flat=True)),
#                     'status': b.status,
#                     'phase_stats': {
#                         p: {
#                             'overall': get_feedback_stats(feedback_qs.filter(batch_type__iexact=b.batch_type, batch_timing__iexact=b.timing, phase=p, submitted_at__gte=b.start_date, submitted_at__lte=b.end_date if (b.end_date and b.status == 'Closed') else timezone.now()) if b.start_date else feedback_qs.filter(batch_type__iexact=b.batch_type, batch_timing__iexact=b.timing, phase=p)),
#                             'online': get_feedback_stats(feedback_qs.filter(batch_type__iexact=b.batch_type, batch_timing__iexact=b.timing, phase=p, batch_mode__iexact="Online", submitted_at__gte=b.start_date, submitted_at__lte=b.end_date if (b.end_date and b.status == 'Closed') else timezone.now()) if b.start_date else feedback_qs.filter(batch_type__iexact=b.batch_type, batch_timing__iexact=b.timing, phase=p, batch_mode__iexact="Online")),
#                             'offline': get_feedback_stats(feedback_qs.filter(batch_type__iexact=b.batch_type, batch_timing__iexact=b.timing, phase=p, batch_mode__iexact="Offline", submitted_at__gte=b.start_date, submitted_at__lte=b.end_date if (b.end_date and b.status == 'Closed') else timezone.now()) if b.start_date else feedback_qs.filter(batch_type__iexact=b.batch_type, batch_timing__iexact=b.timing, phase=p, batch_mode__iexact="Offline")),
#                         } for p in ['P-1', 'P-2', 'P-3', 'P-4', 'P-5']
#                     },
#                     'attendance_list': [
#                         {
#                             'sid': sid,
#                             'name': next(att.name for att in group),
#                             'topic': next(att.today_topic for att in group),
#                             'technology': next(att.technology for att in group),
#                             'mode': next(att.batch_mode for att in group),
#                             'date': next(att.submitted_at.strftime('%Y-%m-%d %H:%M') for att in group)
#                         } for sid, group in (
#                             lambda q: [(sid, list(q.filter(student_id=sid))) for sid in sorted(set(q.values_list('student_id', flat=True)))]
#                         )((lambda q: q.filter(submitted_at__gte=b.start_date, submitted_at__lte=b.end_date if (b.end_date and b.status == 'Closed') else timezone.now()) if b.start_date else q)(trainer_attendance_qs.filter(week_type=b.batch_type, batch_time=b.timing)))
#                     ]
#                 } for b in all_batches
#             ]
#         }

#         # Post-process: Update students_total to be the length of enrolled_students
#         for b_data in trainer_dict['batches']:
#             b_data['students_total'] = len(b_data['enrolled_students'])

#         trainers_data.append(trainer_dict)

#     # Global Student Stats (Only for current branch)
#     all_students = Student.objects.filter(branch=branch_filter).order_by('-joining_date')
#     all_students_data = [
#         {
#             'sid': s.sid,
#             'name': s.name,
#             'phone': s.phone_number or 'N/A',
#             'email': s.email or 'N/A',
#             'technology': s.course or 'N/A',
#             'joining_date': s.joining_date.strftime('%d-%b-%Y') if s.joining_date else 'N/A'
#         } for s in all_students
#     ]

#     # Recent Announcement Logs for Marquee
#     # recent_logs = WhatsAppMessageLog.objects.all().order_by('-sent_at')[:5]
#     recent_announcements = []
#     # for log in recent_logs:
#     #     status_icon = "✅" if log.status == 'Sent' else "❌"
#     #     msg_preview = log.message_body[:40] + "..." if len(log.message_body) > 40 else log.message_body
#     #     recent_announcements.append(f"{status_icon} To: {log.student.name} | Batch: {log.batch.batch_name if log.batch else 'N/A'} | Status: {log.status} | Time: {log.sent_at.strftime('%d-%b %H:%M')}")

#     # Global Feedback Stats for Overall Modal
#     global_stats = get_feedback_stats(all_feedback_qs)

#     today = timezone.now().date()

#     trend_weekly = []
#     for i in range(6, -1, -1):
#         d = today - timedelta(days=i)
#         count = Attendance.objects.filter(submitted_at__date=d).count()
#         trend_weekly.append({'label': d.strftime('%a %d %b'), 'data': count, 'date': d.isoformat()})

#     trend_monthly = []
#     for i in range(3, -1, -1):
#         w_end = today - timedelta(days=i*7)
#         w_start = w_end - timedelta(days=6)
#         count = Attendance.objects.filter(submitted_at__date__range=[w_start, w_end]).count()
#         trend_monthly.append({'label': f"W{4-i} ({w_start.strftime('%d%b')}-{w_end.strftime('%d%b')})", 'data': count, 'start_date': w_start.isoformat(), 'end_date': w_end.isoformat()})

#     global_stats['trend_weekly'] = trend_weekly
#     global_stats['trend_monthly'] = trend_monthly

#     context = {
#         'trainers_json': json.dumps(trainers_data),
#         'all_students_json': json.dumps(all_students_data),
#         'selected_date': selected_date,
#         'global_stats_json': json.dumps(global_stats),
#         'total_students_count': all_students.count(),
#         'total_feedbacks_count': all_feedback_qs.count(),
#         'active_branch': branch_filter,
#         'month_filter': month_name,
#         'year_filter': year_val,
#         'start_date': start_date,
#         'end_date': end_date,
#         'technology_choices': Attendance.TECHNOLOGY_CHOICES,
#         'all_trainers_in_branch': all_trainers_in_branch,
#         'selected_trainer': trainer_filter,
#         'recent_announcements': [] # recent_announcements
#     }
#     return render(request, 'dashboard/index.html', context)

def export_attendance_csv(request):
    trainer_name = request.GET.get('trainer')
    timing = request.GET.get('timing')
    response = HttpResponse(content_type='text/csv')
    filename = f"attendance_{trainer_name}.csv" if trainer_name else "attendance_all.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['Student Name', 'Student ID', 'Technology', 'Topic', 'Mode', 'Batch Timing', 'Trainer', 'Week Type', 'Submitted At'])

    branch = request.GET.get('branch', 'Vikaspuri')

    attendances = Attendance.objects.all().order_by('-submitted_at')
    if trainer_name:
        attendances = attendances.filter(trainer_name=trainer_name)
        # Apply strict branch checking based on batch signatures
        batches = Batch.objects.filter(trainer__name=trainer_name, trainer__branch=branch)
        valid_signatures = set((b.batch_type, b.timing) for b in batches)

        q_obj = models.Q()
        for batch_type, batch_timing in valid_signatures:
            q_obj |= models.Q(week_type=batch_type, batch_time=batch_timing)

        if q_obj:
            attendances = attendances.filter(q_obj)
        else:
            attendances = Attendance.objects.none()

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
            'Batch Timing': att.batch_time if att.batch_time else '',
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

    branch = request.GET.get('branch', 'Vikaspuri')

    filename = f"Feedback_{trainer}_{batch}_{phase}.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['Student Name', 'Student ID', 'Email', 'Phone', 'Trainer', 'Tech', 'Batch', 'Mode', 'Phase', 'Q1 (Understand)', 'Q2 (Regularity)', 'Q3 (Practical)', 'Q4 (Doubt)', 'Avg Rating', 'Review', 'Submitted At'])

    feedback_qs = Feedback.objects.all().order_by('-submitted_at')
    if trainer:
        feedback_qs = feedback_qs.filter(trainer_name__iexact=trainer)
        batches = Batch.objects.filter(trainer__name=trainer, trainer__branch=branch)
        valid_signatures = set((b.batch_type, b.timing) for b in batches)

        q_obj = models.Q()
        for b_type, b_timing in valid_signatures:
            q_obj |= models.Q(batch_type__iexact=b_type, batch_timing__iexact=b_timing)

        if q_obj:
            feedback_qs = feedback_qs.filter(q_obj)
        else:
            feedback_qs = Feedback.objects.none()
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
    branch = request.GET.get('branch', 'Vikaspuri')

    feedback_qs = Feedback.objects.all().order_by('-submitted_at')
    if trainer:
        feedback_qs = feedback_qs.filter(trainer_name__iexact=trainer)
        batches = Batch.objects.filter(trainer__name=trainer, trainer__branch=branch)
        valid_signatures = set((b.batch_type, b.timing) for b in batches)

        q_obj = models.Q()
        for b_type, b_timing in valid_signatures:
            q_obj |= models.Q(batch_type__iexact=b_type, batch_timing__iexact=b_timing)

        if q_obj:
            feedback_qs = feedback_qs.filter(q_obj)
        else:
            feedback_qs = Feedback.objects.none()
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
    branch = request.GET.get('branch', 'Vikaspuri')

    feedback_qs = Feedback.objects.all().order_by('-submitted_at')
    if trainer:
        feedback_qs = feedback_qs.filter(trainer_name__iexact=trainer)
        batches = Batch.objects.filter(trainer__name=trainer, trainer__branch=branch)
        valid_signatures = set((b.batch_type, b.timing) for b in batches)

        q_obj = models.Q()
        for b_type, b_timing in valid_signatures:
            q_obj |= models.Q(batch_type__iexact=b_type, batch_timing__iexact=b_timing)

        if q_obj:
            feedback_qs = feedback_qs.filter(q_obj)
        else:
            feedback_qs = Feedback.objects.none()
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

    branch = request.GET.get('branch', 'Vikaspuri')

    # 1. Get filtered Feedback
    feedback_qs = Feedback.objects.filter(trainer_name=trainer_name)
    batches = Batch.objects.filter(trainer__name=trainer_name, trainer__branch=branch)
    valid_signatures = set((b.batch_type, b.timing) for b in batches)

    q_obj = models.Q()
    for b_type, b_timing in valid_signatures:
        q_obj |= models.Q(batch_type__iexact=b_type, batch_timing__iexact=b_timing)

    if q_obj:
        feedback_qs = feedback_qs.filter(q_obj)
    else:
        feedback_qs = Feedback.objects.none()
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

# def get_announcement_logs(request):
#     logs = WhatsAppMessageLog.objects.all().order_by('-sent_at')[:20]
#     log_data = []
#     for log in logs:
#         log_data.append({
#             'student': log.student.name,
#             'batch': log.batch.batch_name if log.batch else 'N/A',
#             'message': log.message_body[:50] + '...' if len(log.message_body) > 50 else log.message_body,
#             'status': log.status,
#             'time': log.sent_at.strftime('%d-%b %H:%M'),
#             'error': log.error_response if log.error_response else ''
#         })
#     return JsonResponse({'status': 'success', 'logs': log_data})

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
# API Views for Daily Attendance
@login_required
@csrf_exempt
def mark_daily_attendance(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST allowed'}, status=405)

    try:
        data = json.loads(request.body)
        batch_id = data.get('batch_id')
        date_str = data.get('date') # YYYY-MM-DD
        attendance_data = data.get('attendance', []) # List of {sid, name, is_present}

        if not batch_id or not date_str:
            return JsonResponse({'status': 'error', 'message': 'Missing batch_id or date'}, status=400)

        batch = Batch.objects.get(id=batch_id)

        # Clear existing for this date/batch to avoid duplicates (and handle updates)
        DailyAttendance.objects.filter(batch=batch, date=date_str).delete()

        # Create new records
        to_create = []
        for item in attendance_data:
            to_create.append(DailyAttendance(
                batch=batch,
                student_sid=item['sid'],
                student_name=item['name'],
                date=date_str,
                is_present=item['is_present']
            ))

        DailyAttendance.objects.bulk_create(to_create)

        return JsonResponse({'status': 'success', 'message': f'Attendance saved for {date_str}'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def get_daily_attendance_history(request):
    batch_id = request.GET.get('batch_id')
    date_str = request.GET.get('date')

    if not batch_id or not date_str:
        return JsonResponse({'status': 'error', 'message': 'Missing parameters'}, status=400)

    batch = Batch.objects.get(id=batch_id)

    # 1. Trainer marked logs
    logs = DailyAttendance.objects.filter(batch=batch, date=date_str)
    marked_data = {log.student_sid: log.is_present for log in logs}

    # 2. Student form submissions
    # We need to match by batch timing and type
    form_submissions = Attendance.objects.filter(
        submitted_at__date=date_str,
        batch_time=batch.timing,
        week_type=batch.batch_type
    )

    student_modes = {sub.student_id: sub.batch_mode for sub in form_submissions}
    submitted_sids = list(student_modes.keys())

    return JsonResponse({
        'status': 'success',
        'marked': marked_data,
        'submitted': submitted_sids,
        'modes': student_modes
    })

@login_required
def get_student_attendance_calendar(request):
    batch_id = request.GET.get('batch_id')
    student_sid = request.GET.get('student_sid')

    if not batch_id or not student_sid:
        return JsonResponse({'status': 'error', 'message': 'Missing parameters'}, status=400)

    try:
        batch = Batch.objects.get(id=batch_id)

        # Get trainer marked attendance for this student
        daily_records = DailyAttendance.objects.filter(batch=batch, student_sid=student_sid)

        # Get student form submissions
        form_records = Attendance.objects.filter(
            student_id=student_sid,
            batch_time=batch.timing,
            week_type=batch.batch_type
        )

        attendance_data = {}

        # Initialize with form submissions (Present)
        for f in form_records:
            date_str = f.submitted_at.date().strftime('%Y-%m-%d')
            attendance_data[date_str] = 'present'

        # Override with trainer's manual marks
        for d in daily_records:
            date_str = d.date.strftime('%Y-%m-%d')
            attendance_data[date_str] = 'present' if d.is_present else 'absent'

        return JsonResponse({
            'status': 'success',
            'history': attendance_data,
            'batch_start': batch.start_date.strftime('%Y-%m-%d') if batch.start_date else None,
            'batch_end': batch.end_date.strftime('%Y-%m-%d') if batch.end_date else None,
            'batch_type': batch.batch_type
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
@login_required
def send_batch_notification(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST allowed'}, status=405)

    try:
        data = json.loads(request.body)
        batch_id = data.get('batch_id')
        subject = data.get('subject', 'Notification from DUCAT Trainer')
        message = data.get('message')

        if not batch_id or not message:
            return JsonResponse({'status': 'error', 'message': 'Batch ID and Message are required'}, status=400)

        batch = Batch.objects.get(id=batch_id)

        # Get students explicitly enrolled + students who marked attendance/feedback for this batch
        # We need to filter based on batch timing/type to be accurate
        from form.models import Attendance
        batch_student_ids = Attendance.objects.filter(
            trainer_name=batch.trainer.name,
            batch_time=batch.timing,
            week_type=batch.batch_type
        ).values_list('student_id', flat=True).distinct()

        students = Student.objects.filter(
            models.Q(current_batch=batch) |
            models.Q(sid__in=batch_student_ids)
        ).distinct()

        emails = [s.email for s in students if s.email]
        # emails = ["riyariya3467@gmail.com"]

        if not emails:
             return JsonResponse({'status': 'error', 'message': 'No students with email addresses found in this batch.'}, status=400)

        # Send Email
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@ducatindia.com'),
            recipient_list=emails,
            fail_silently=False,
        )

        return JsonResponse({'status': 'success', 'message': f'Notification sent to {len(emails)} students.'})

    except Batch.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Batch not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
@login_required
def delete_batch(request, batch_id):
    if request.method == 'POST':
        try:
            batch = Batch.objects.get(id=batch_id)
            batch_name = batch.batch_name
            batch.delete()
            return JsonResponse({'status': 'success', 'message': f'Batch {batch_name} deleted successfully'})
        except Batch.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Batch not found'}, status=404)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

@login_required
def get_trend_details(request):
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')

    if not start_date or not end_date:
        return JsonResponse({'status': 'error', 'message': 'Missing dates'})

    try:
        att_qs = Attendance.objects.filter(submitted_at__date__range=[start_date, end_date]).order_by('-submitted_at')
        fb_qs = Feedback.objects.filter(submitted_at__date__range=[start_date, end_date]).order_by('-submitted_at')

        attendance_data = [{
            'name': a.name,
            'sid': a.student_id,
            'trainer': a.trainer_name,
            'topic': a.today_topic or 'N/A',
            'date': a.submitted_at.strftime('%Y-%m-%d'),
            'type': 'Attendance',
            'color': '#10b981'
        } for a in att_qs]

        feedback_data = [{
            'name': f.student_name,
            'sid': f.student_id,
            'trainer': getattr(f, 'trainer_name', '-'),
            'topic': getattr(f, 'phase', 'N/A'),
            'date': f.submitted_at.strftime('%Y-%m-%d'),
            'type': 'Feedback',
            'color': '#f59e0b'
        } for f in fb_qs]

        return JsonResponse({
            'status': 'success',
            'attendance': attendance_data,
            'feedbacks': feedback_data
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def get_student_profile(request):
    from form.models import Attendance
    from feedback.models import Feedback
    from .models import Batch

    sid = request.GET.get('sid')
    if not sid:
        return JsonResponse({'status': 'error', 'message': 'Missing SID'})

    try:
        student = Student.objects.get(sid=sid)

        # Get batches from multiple sources for data integrity
        # 1. Official Enrollment
        all_enrolled = Batch.objects.filter(enrolled_students=student)

        # 2. Extract from Attendance records
        att_records = Attendance.objects.filter(student_id=sid)
        att_signatures = set()
        for a in att_records:
            # signature: (Trainer, Tech/Course, Timing, Type)
            sig = (a.trainer_name.strip().upper(), a.technology.strip().upper(), a.batch_time.strip().upper(), a.week_type.strip().upper())
            att_signatures.add(sig)

        # 3. Extract from Feedback records
        fb_records = Feedback.objects.filter(student_id=sid)
        fb_signatures = set()
        for f in fb_records:
            sig = (f.trainer_name.strip().upper(), f.technology.strip().upper(), f.batch_timing.strip().upper(), f.batch_type.strip().upper())
            fb_signatures.add(sig)

        # Merge all signatures
        all_sigs = att_signatures.union(fb_signatures)

        # Resolve signatures to real Batch objects where possible
        # Pre-fetch batches for lookup
        all_batches_qs = Batch.objects.select_related('trainer').all()
        batch_map = {}
        loose_batch_map = {} # For looser matching (Trainer, Timing)
        for b in all_batches_qs:
            key = (b.trainer.name.strip().upper(), b.batch_name.strip().upper(), b.timing.strip().upper(), b.batch_type.strip().upper())
            batch_map[key] = b

            loose_key = (b.trainer.name.strip().upper(), b.timing.strip().upper())
            if loose_key not in loose_batch_map:
                loose_batch_map[loose_key] = b

        final_batches = {} # key -> data

        # Process Official Batches first
        for b in all_enrolled:
            key = f"{b.batch_name}|{b.timing}"
            final_batches[key] = {
                'technology': student.course or b.trainer.course, # Use Master Technology
                'batch_name': b.batch_name,
                'trainer': b.trainer.name,
                'type': b.batch_type,
                'timing': b.timing,
                'status': b.status,
                'mode': 'Offline' # Fallback
            }

        # Process inferred batches
        for sig in all_sigs:
            b_obj = batch_map.get(sig)
            if not b_obj:
                loose_key = (sig[0], sig[2]) # (Trainer, Timing)
                b_obj = loose_batch_map.get(loose_key)

            # Use b_obj's batch_name for key if found to merge with official batches
            batch_name_for_key = b_obj.batch_name if b_obj else sig[1]
            key = f"{batch_name_for_key}|{sig[2]}"

            if key not in final_batches:
                final_batches[key] = {
                    'technology': student.course or (b_obj.trainer.course if b_obj else sig[1]),
                    'batch_name': batch_name_for_key,
                    'trainer': sig[0],
                    'type': sig[3],
                    'timing': sig[2],
                    'status': b_obj.status if b_obj else 'Active',
                    'mode': 'Offline'
                }

        # Update modes from attendance if available
        for a in att_records:
            # We must use the same key logic. Try to find if this matches any b_obj
            loose_key = (a.trainer_name.strip().upper(), a.batch_time.strip().upper())
            b_obj = loose_batch_map.get(loose_key)
            batch_name_for_key = b_obj.batch_name if b_obj else a.technology
            key = f"{batch_name_for_key}|{a.batch_time}"

            # Case insensitive key matching since case might differ
            for f_key in list(final_batches.keys()):
                if f_key.upper() == key.upper():
                    final_batches[f_key]['mode'] = a.batch_mode
                    break

        active_list = [v for v in final_batches.values() if v['status'].lower() == 'active']
        closed_list = [v for v in final_batches.values() if v['status'].lower() == 'closed']

        # Get feedbacks for the list
        feedbacks = Feedback.objects.filter(student_id=sid).order_by('-submitted_at')

        # Calculate Total Present Count
        from dashboard.models import DailyAttendance
        form_dates = set(Attendance.objects.filter(student_id=sid).values_list('submitted_at__date', flat=True))
        trainer_dates = set(DailyAttendance.objects.filter(student_sid=sid, is_present=True).values_list('date', flat=True))
        total_present_count = len(form_dates.union(trainer_dates))

        return JsonResponse({
            'status': 'success',
            'student_name': student.name,
            'sid': student.sid,
            'enrolled_course': student.course,
            'total_present_count': total_present_count,
            'active_batches': active_list,
            'closed_batches': closed_list,
            'feedbacks': [{
                'date': f.submitted_at.strftime('%Y-%m-%d'),
                'trainer': getattr(f, 'trainer_name', '-'),
                'phase': getattr(f, 'phase', 'N/A'),
                'avg_rating': round((f.ques1_rating + f.ques2_rating + f.ques3_rating + f.ques4_rating)/4.0, 1)
            } for f in feedbacks]
        })
    except Student.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Student not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def export_timetable_csv(request):
    import csv
    from django.http import HttpResponse
    trainer_name = request.GET.get('trainer')
    branch = request.GET.get('branch', 'Vikaspuri')
    response = HttpResponse(content_type='text/csv')
    filename = f"timetable_{trainer_name}_{branch}.csv" if trainer_name else f"timetable_all_{branch}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['Trainer Name', 'Batch Name', 'Batch Type', 'Timing', 'Month', 'Year', 'Status', 'Target Students', 'Start Date', 'Branch'])

    batches = Batch.objects.filter(trainer__branch=branch).order_by('trainer__name', 'timing')
    if trainer_name:
        batches = batches.filter(trainer__name=trainer_name)

    for b in batches:
        writer.writerow([
            b.trainer.name,
            b.batch_name,
            b.batch_type,
            b.timing,
            b.month,
            b.year,
            b.status,
            b.students_count,
            b.start_date.strftime('%d-%b-%Y') if b.start_date else 'N/A',
            b.trainer.branch
        ])
    return response

def export_timetable_excel(request):
    try:
        import pandas as pd
    except ImportError:
        return HttpResponse("Pandas not installed.", status=500)

    trainer_name = request.GET.get('trainer')
    branch = request.GET.get('branch', 'Vikaspuri')
    batches = Batch.objects.filter(trainer__branch=branch).order_by('trainer__name', 'timing')
    if trainer_name:
        batches = batches.filter(trainer__name=trainer_name)

    data = []
    for b in batches:
        data.append({
            'Trainer Name': b.trainer.name,
            'Batch Name': b.batch_name,
            'Batch Type': b.batch_type,
            'Timing': b.timing,
            'Month': b.month,
            'Year': b.year,
            'Status': b.status,
            'Target Students': b.students_count,
            'Start Date': b.start_date.strftime('%d-%b-%Y') if b.start_date else 'N/A',
            'Branch': b.trainer.branch
        })

    df = pd.DataFrame(data)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"timetable_{trainer_name}_{branch}.xlsx" if trainer_name else f"timetable_all_{branch}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    with pd.ExcelWriter(response, engine='openpyxl') as excel_writer:
        df.to_excel(excel_writer, index=False, sheet_name='Timetable')

    return response

def export_student_roster_csv(request):
    trainer_name = request.GET.get('trainer')
    timing = request.GET.get('timing')
    branch = request.GET.get('branch', 'Vikaspuri')

    response = HttpResponse(content_type='text/csv')
    filename = f"roster_{trainer_name}.csv" if trainer_name else "roster_all.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['Student ID', 'Student Name', 'Active Batches & Mode'])

    # Logic to aggregate students (copied from JS openMainModal logic)
    from feedback.models import Feedback

    # 1. Get attendance based students
    attendances = Attendance.objects.filter(branch=branch).order_by('-submitted_at')
    if trainer_name:
        attendances = attendances.filter(trainer_name=trainer_name)
    if timing:
        attendances = attendances.filter(batch_time=timing)

    # 2. Get feedback based students
    feedbacks = Feedback.objects.filter(branch=branch).order_by('-submitted_at')
    if trainer_name:
        feedbacks = feedbacks.filter(trainer_name=trainer_name)
    if timing:
        feedbacks = feedbacks.filter(batch_timing=timing)

    unique_students = {} # SID -> {name, batches: set}

    # 3. Get Enrolled Students from Batches (Ensures even those without records show up)
    from dashboard.models import Batch
    batches = Batch.objects.filter(trainer__branch=branch)
    if trainer_name:
        batches = batches.filter(trainer__name=trainer_name)
    if timing:
        batches = batches.filter(timing=timing)

    for b in batches:
        for s in b.enrolled_students.all():
            sid = s.sid
            detail = f"{b.batch_name} ({b.batch_type})"
            if sid not in unique_students:
                unique_students[sid] = {'name': s.name, 'batches': {detail}}
            else:
                unique_students[sid]['batches'].add(detail)

    for att in attendances:
        sid = att.student_id
        # Find batch name if possible
        match_b = batches.filter(batch_type__iexact=att.week_type, timing__iexact=att.batch_time).first()
        b_name = match_b.batch_name if match_b else att.technology
        detail = f"{b_name} ({att.batch_mode})"
        if sid not in unique_students:
            unique_students[sid] = {'name': att.name, 'batches': {detail}}
        else:
            unique_students[sid]['batches'].add(detail)

    for fb in feedbacks:
        sid = fb.student_id
        match_b = batches.filter(batch_type__iexact=fb.batch_type, timing__iexact=fb.batch_timing).first()
        b_name = match_b.batch_name if match_b else fb.course
        detail = f"{b_name} ({fb.batch_mode})"
        if sid not in unique_students:
            unique_students[sid] = {'name': fb.student_name, 'batches': {detail}}
        else:
            unique_students[sid]['batches'].add(detail)

    for sid, data in unique_students.items():
        writer.writerow([
            sid,
            data['name'],
            ", ".join(sorted(list(data['batches'])))
        ])

    return response

def export_student_roster_excel(request):
    try:
        import pandas as pd
    except ImportError:
        return HttpResponse("Pandas not installed.", status=500)

    trainer_name = request.GET.get('trainer')
    timing = request.GET.get('timing')
    branch = request.GET.get('branch', 'Vikaspuri')

    from feedback.models import Feedback

    attendances = Attendance.objects.filter(branch=branch)
    if trainer_name: attendances = attendances.filter(trainer_name=trainer_name)
    if timing: attendances = attendances.filter(batch_time=timing)

    feedbacks = Feedback.objects.filter(branch=branch)
    if trainer_name: feedbacks = feedbacks.filter(trainer_name=trainer_name)
    if timing: feedbacks = feedbacks.filter(batch_timing=timing)

    unique_students = {}

    # 3. Get Enrolled Students from Batches
    from dashboard.models import Batch
    batches = Batch.objects.filter(trainer__branch=branch)
    if trainer_name:
        batches = batches.filter(trainer__name=trainer_name)
    if timing:
        batches = batches.filter(timing=timing)

    for b in batches:
        for s in b.enrolled_students.all():
            sid = s.sid
            detail = f"{b.batch_name} ({b.batch_type})"
            if sid not in unique_students:
                unique_students[sid] = {'name': s.name, 'batches': {detail}}
            else:
                unique_students[sid]['batches'].add(detail)

    for att in attendances:
        sid = att.student_id
        match_b = batches.filter(batch_type__iexact=att.week_type, timing__iexact=att.batch_time).first()
        b_name = match_b.batch_name if match_b else att.technology
        detail = f"{b_name} ({att.batch_mode})"
        if sid not in unique_students:
            unique_students[sid] = {'name': att.name, 'batches': {detail}}
        else:
            unique_students[sid]['batches'].add(detail)

    for fb in feedbacks:
        sid = fb.student_id
        match_b = batches.filter(batch_type__iexact=fb.batch_type, timing__iexact=fb.batch_timing).first()
        b_name = match_b.batch_name if match_b else fb.course
        detail = f"{b_name} ({fb.batch_mode})"
        if sid not in unique_students:
            unique_students[sid] = {'name': fb.student_name, 'batches': {detail}}
        else:
            unique_students[sid]['batches'].add(detail)

    export_data = []
    for sid, data in unique_students.items():
        export_data.append({
            'Student ID': sid,
            'Student Name': data['name'],
            'Active Batches & Mode': ", ".join(sorted(list(data['batches'])))
        })

    df = pd.DataFrame(export_data)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"roster_{trainer_name}.xlsx" if trainer_name else "roster_all.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    with pd.ExcelWriter(response, engine='openpyxl') as excel_writer:
        df.to_excel(excel_writer, index=False, sheet_name='Student Roster')

    return response
