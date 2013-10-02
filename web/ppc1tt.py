#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, flash
from timetable import (Timetable, SearchQuery, MultiSearchTerm,
                        TimeRange, Any)

import datetime

TT_JSON_FILE = 'tt.json'

app = Flask(__name__)

tt = Timetable(TT_JSON_FILE)

search_cache = {}

def _get_date(request):
    date = request.form.get('date')
    if date == 'all':
        date_term = Any
    elif date == 'today':
        date_term = datetime.date.today()
    elif date == 'single':
        date_term = datetime.date(
            int(request.form.get('date_year')),
            int(request.form.get('date_month')),
            int(request.form.get('date_day')))
    elif date == 'range':
        start = datetime.date(
            int(request.form.get('date_start_year')),
            int(request.form.get('date_start_month')),
            int(request.form.get('date_start_day')))
        end = datetime.date(
            int(request.form.get('date_end_year')),
            int(request.form.get('date_end_month')),
            int(request.form.get('date_end_day')))
        date_term = TimeRange(start, end)
    return date_term

def _get_timerange(request):
    time = request.form.get('time')
    if time == 'all':
        tr_term = Any
    elif time == 'range':
        start_hour = int(request.form.get('time_start_hour'))
        start_min = int(request.form.get('time_start_min'))
        start = datetime.time(start_hour, start_min)
        end_hour = int(request.form.get('time_end_hour'))
        end_min = int(request.form.get('time_end_min'))
        end = datetime.time(end_hour, end_min)
        tr_term = TimeRange(start, end)
    return tr_term

@app.route('/')
def main():
    return render_template('index.html')

@app.route('/search')
def show_search_form():
    return render_template('search_form.html', error_msgs=[])

@app.route('/timetable', methods=['POST'])
def handle_search():
    error_msgs = []
    terms = {}
    terms['tutorial_group'] = int(request.form.get('tutorial_group'))
    terms['seminar_group'] = request.form.get('seminar_group')
    terms['code'] = MultiSearchTerm(*request.form.getlist('code'))
    terms['day_of_week'] = MultiSearchTerm(*(int(i) for i in request.form.getlist('weekday')))
    try:
        terms['date'] = _get_date(request)
    except ValueError:
        error_msgs.append('Invalid value for date.')
    try:
        terms['timerange'] = _get_timerange(request)
    except ValueError:
        error_msgs.append('Invalid value for time.')
        
    if error_msgs:
        # Pass error messages directly to template rather than
        # flashing, which requires app.secret_key to be set.
        return render_template('search_form.html', error_msgs=error_msgs)
    else:
        query = SearchQuery(**terms)
        cached_result = search_cache.get(query)
        if cached_result:
            return cached_result
        else:
            new_tt = tt.filter(query)
            result = new_tt.to_html()
            search_cache[query] = result
            return result

if __name__ == '__main__':
    app.run()
