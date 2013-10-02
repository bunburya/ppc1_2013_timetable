#!/usr/bin/env python3

# TODO:
# - Implement filter methods
#   - Days: Check search query against events; remove those which don't;
#           return self if any remain, False otherwise
#   - Weeks: Call all days' filter methods, remove those which return
#            False; return self if any remain, False otherwise
#   - Timetable: Call all weeks' filter methods, return those which
#                return False; return self
# - Have SearchQuery return its state as a tuple so it can be hashed and
#   stored in a dict (to act as a search cache)
# - Maybe drop xml.dom when building html

import re
import datetime
import time
import json
import xml.dom

EmptyValue = object()

one_day = datetime.timedelta(1)

def _get_boldtext(doc, text):
    b = doc.createElement('b')
    text = doc.createTextNode(text)
    b.appendChild(text)
    return b

def _add_td(doc, row, content, colspan=1, bold=False):
    """Create a td element containing `content` and add it to `row`,
    which is part of `doc`"""
    #print(type(text))
    if content is None:
        content = 'n/a'
    col = doc.createElement('td colspan={}'.format(colspan))
    if not isinstance(content, xml.dom.Node):
        text = doc.createTextNode(content)
        if bold:
            content = doc.createElement('b')
            content.appendChild(text)
        else:
            content = text
    col.appendChild(content)
    row.appendChild(col)

def _get_dropdown(doc, values):
    dropdown = doc.createElement('select')
    for v in values:
        opt = doc.createElement('option')
        opttext = doc.createTextNode(str(v))
        opt.appendChild(opttext)
        dropdown.appendChild(opt)
    return dropdown
    
all_tutorial_groups = list(range(1, 21))
all_seminar_groups = ['{} {}'.format(color, letter)
                        for letter in 'ABCDEFGHKLMNOPQR'
                        for color in ['Red', 'Blue']]

class Timetable:
    
    def __init__(self, fname=None):
        self.weeks = []
        if fname is not None:
            with open(fname) as f:
                d = json.load(f)
            self.from_dict(d)
    
    def new_week(self, num=None, commences=None):
        w = Week(num, commences)
        self.weeks.append(w)
        return w
    
    def is_sane(self):
        return len(self.weeks) == 30 and all(map(lambda w:w.is_sane(), self.weeks))
    
    def to_dict(self):
        d = {'type': 'timetable'}
        d['weeks'] = []
        for week in self.weeks:
            d['weeks'].append(week.to_dict())
        return d
    
    def from_dict(self, d):
        assert d['type'] == 'timetable'
        for w in d['weeks']:
            week = Week()
            week.from_dict(w)
            self.weeks.append(week)
    
    def to_html(self):
        dom = xml.dom.getDOMImplementation()
        doc = dom.createDocument(None, None, None)
        html = doc.createElement('html')
        head = doc.createElement('head')
        title = doc.createElement('title')
        title_text = doc.createTextNode('PPC1 2013 timetable')
        title.appendChild(title_text)
        head.appendChild(title)
        html.appendChild(head)
        body = doc.createElement('body')
        table = doc.createElement('table border=1')
        head_row = doc.createElement('tr')
        _add_td(doc, head_row, 'Time', bold=True)
        _add_td(doc, head_row, 'Code', bold=True)
        _add_td(doc, head_row, 'Name', bold=True)
        _add_td(doc, head_row, 'Coordinator', bold=True)
        _add_td(doc, head_row, 'Location', bold=True)
        _add_td(doc, head_row, 'Tutorial groups (click to see all)',
                bold=True)
        _add_td(doc, head_row, 'Skills groups (click to see all)',
                bold=True)
        table.appendChild(head_row)
        for w in self.weeks:
            for r in w.to_html(doc):
                table.appendChild(r)
        body.appendChild(table)
        html.appendChild(body)
        doc.appendChild(html)
        return doc.toprettyxml()
        
    def filter(self, sq):
        new_tt = Timetable()
        for w in self.weeks:
            new_week = w.filter(sq)
            if new_week.days:
                new_tt.weeks.append(new_week)
        return new_tt

class Week:
    """A work week, ie Mon-Fri."""
    
    def __init__(self, num=None, commences=None):
        self.num = num
        self.commences = commences
        self.days = []
    
    def __repr__(self):
        return '<{}>'.format(str(self))
    
    def __str__(self):
        return 'Week {}, commencing {}'.format(self.num, self.commences)
    
    def new_day(self):
        d = Day(self, len(self.days))
        self.days.append(d)
        #if len(self.days) > 4:
        #    print(self, d)
        #    raise Exception
        return d
    
    def is_sane(self):
        sane_num_days = (len(self.days) <= 7)
        days_are_sane = all(map(lambda d: d.is_sane(), self.days))
        sane = sane_num_days and days_are_sane
        if not sane:
            print('NOT SANE', self, self.num, num_days, len(self.days), self.days, sane_num_days, days_are_sane)
        return sane
    
    def to_dict(self):
        d = {'type': 'week'}
        d['num'] = self.num
        d['commences'] = self.commences.strftime('%Y/%m/%d') if self.commences else None
        d['days'] = []
        for day in self.days:
            d['days'].append(day.to_dict())
        return d
    
    def from_dict(self, d):
        assert d['type'] == 'week'
        self.num = d['num']
        self.commences = datetime.date(*(int(i) for i in d['commences'].split('/')))
        for dd in d['days']:
            day = Day(self)
            day.from_dict(dd, self)
            self.days.append(day)
    
    def to_html(self, doc):
        rows = []
        title_row = doc.createElement('tr')
        _add_td(doc, title_row, str(self), 7, bold=True)
        rows.append(title_row)
        for d in self.days:
            for r in d.to_html(doc):
                rows.append(r)
        return rows
    
    def filter(self, sq):
        new_week = Week(self.num, self.commences)
        for d in self.days:
            new_day = d.filter(sq)
            if new_day.events:
                new_week.days.append(new_day)
        return new_week
        

class Day:
    
    days_of_week = [
        'Monday',
        'Tuesday',
        'Wednesday',
        'Thursday',
        'Friday',
        'Saturday',
        'Sunday'
        ]
    
    def __init__(self, week=EmptyValue, day_of_week=EmptyValue):
        self.week = week
        if day_of_week is not EmptyValue:
            self.date = week.commences + (one_day*day_of_week)
        else:
            self.date = None
        self.events = []
    
    def __repr__(self):
        return '<Day @ {}>'.format(self.date)
    
    def __str__(self):
        return '{} {}'.format(
            self.days_of_week[self.date.weekday()],
            self.date
            )
    
    def new_event(self, off=False):
        evt_cls = DayOffEvent if off else Event
        e = evt_cls(self.week)
        self.events.append(e)
        return e
    
    def is_sane(self):
        return all(map(lambda e: e.is_sane(), self.events))
    
    def to_dict(self):
        d = {'type': 'day'}
        d['date'] = self.date.strftime('%Y/%m/%d')
        d['events'] = []
        for evt in self.events:
            d['events'].append(evt.to_dict())
        return d
    
    def from_dict(self, d, week):
        assert d['type'] == 'day'
        self.date = datetime.date(*(int(i) for i in d['date'].split('/')))
        for e in d['events']:
            evt = Event(week=week, day=self)
            evt.from_dict(e)
            self.events.append(evt)
    
    def to_html(self, doc):
        rows = []
        title_row = doc.createElement('tr')
        _add_td(doc, title_row, str(self), 7, bold=True)
        rows.append(title_row)
        for e in self.events:
            rows.append(e.to_html(doc))
        return rows
    
    def filter(self, sq):
        new_day = Day(self.week, self.date.weekday())
        for e in self.events:
            if sq.matches(e):
                new_day.events.append(e)
        return new_day

class Event:
    
    def __init__(self, week=EmptyValue, day=EmptyValue):
        
        self.starts = EmptyValue
        self.ends = EmptyValue
        self.tutorial_groups = EmptyValue
        self.seminar_groups = EmptyValue
        self.coordinator = EmptyValue
        self.location = EmptyValue
        self.name = EmptyValue
        self.code = EmptyValue
        self.day = day
        self.week = week
    
    def is_sane(self):
        sane = not EmptyValue in [self.starts, self.ends,
            self.tutorial_groups, self.seminar_groups,
            self.coordinator, self.location, self.name, self.code,
            self.day, self.week]
        if not sane:
            print('NOT SANE', self.day, self.__dict__)
        return sane
    
    def to_dict(self):
        d = {'type': 'event'}
        d['starts'] = self.starts.strftime('%H:%M') if self.starts else None
        d['ends'] = self.ends.strftime('%H:%M') if self.ends else None
        d['tutorial_groups'] = self.tutorial_groups
        d['seminar_groups'] = self.seminar_groups
        d['coordinator'] = self.coordinator
        d['location'] = self.location
        d['code'] = self.code
        d['name'] = self.name
        return d
    
    def from_dict(self, d):
        assert d['type'] == 'event'
        if d['starts'] is not None:
            self.starts = datetime.time(*(int(i) for i in d['starts'].split(':')))
        else:
            self.starts = None
        if d['ends'] is not None:
            self.ends = datetime.time(*(int(i) for i in d['ends'].split(':')))
        else:
            self.ends = None
        self.tutorial_groups = d['tutorial_groups']
        self.seminar_groups = d['seminar_groups']
        self.coordinator = d['coordinator']
        self.location = d['location']
        self.code = d['code']
        self.name = d['name']
    
    
    def to_html(self, doc):
        row = doc.createElement('tr')
        if self.starts and self.ends:
            time = '-'.join([
                self.starts.strftime('%H:%M'),
                self.ends.strftime('%H:%M')
                ])
        elif self.starts:
            time = self.starts.strftime('%H:%M')
        else:
            time = 'n/a'
        _add_td(doc, row, time)
        _add_td(doc, row, self.code)
        _add_td(doc, row, self.name)
        _add_td(doc, row, self.coordinator)
        _add_td(doc, row, self.location)
        _add_td(doc, row, _get_dropdown(doc, self.tutorial_groups))
        _add_td(doc, row, _get_dropdown(doc, self.seminar_groups))
        return row
        

class DayOffEvent(Event):
    
    def __init__(self, week=EmptyValue, day=EmptyValue):
        
        self.starts = None
        self.ends = None
        self.tutorial_groups = None
        self.seminar_groups = None
        self.coordinator = None
        self.location = None
        self.name = None
        self.code = None
        self.day = day
        self.week = week
    
class AnyValue:
    """An object that always returns True when compared with another
    object, to be used when a user does not specify a particular value
    for a field when searching."""
    
    def __eq__(self, other):
        return True
    
    def __contains__(self, item):
        return True
    
    def __iter__(self):
        return iter((None,))
    
    def __hash__(self):
        return hash(tuple(self))
    

Any = AnyValue()

class TimeRange:
    """A class representing a range of dates (using datetime.date) or of
    time (using datetime.time)."""
    
    def __init__(self, start, end):
        self.start = start
        self.end = end
    
    def __contains__(self, t):
        return self.start <= t <= self.end
    
    def __iter__(self):
        return iter((self.start, self.end))
    
    def __hash__(self):
        return hash(tuple(self))
    
    def __eq__(self, other):
        return (self.start == other.start) and (self.end == other.end)

class SearchQuery:
    
    def __init__(self, starts=Any, ends=Any, tutorial_group=Any,
        seminar_group=Any, coordinator=Any, location=Any, name=Any,
        code=Any, date=Any, day_of_week=Any, week_num=Any,
        month=Any, daterange=Any, timerange=Any):
        
        self.starts = starts
        self.ends = ends
        self.tutorial_group = tutorial_group
        self.seminar_group = seminar_group
        self.coordinator = coordinator
        self.location = location
        self.name = name
        self.code = code
        self.date = date
        self.day_of_week = day_of_week
        self.week_num = week_num
        self.month = month
        self.daterange = daterange
        self.timerange = timerange
    
    def __iter__(self):
        return iter((
                self.tutorial_group,
                self.seminar_group,
                self.starts,
                self.ends,
                self.coordinator,
                self.location,
                self.name,
                self.code,
                self.date,
                self.day_of_week,
                self.week_num,
                self.month,
                self.daterange
                ))
    
    def __hash__(self):
        return hash(tuple(self))
    
    def __eq__(self, other):
        return tuple(self) == tuple(other)
    
    def _groups_match(self, group, evt_groups):
        #print(group, evt_groups)
        if evt_groups is None:
            return False
        elif group is Any:
            return True
        else:
            return group in evt_groups
    
    def matches_groups(self, event):
        return all([
            self._groups_match(self.tutorial_group, event.tutorial_groups),
            self._groups_match(self.seminar_group, event.seminar_groups)
            ])
    
    def matches_info(self, event):
        return all([
            self.starts == event.starts,
            self.ends == event.ends,
            self.coordinator == event.coordinator,
            self.location == event.location,
            self.name == event.name,
            self.code == event.code,
            self.date == event.day.date,
            self.day_of_week == event.day.date.weekday(),
            self.week_num == event.week.num,
            self.month == event.day.date.month,
            event.day.date in self.daterange,
            (event.starts in self.timerange) or (event.ends in self.timerange)
            ])
    
    def matches(self, event):
        #print(self.matches_groups(event), self.matches_info(event))
        return self.matches_groups(event) and self.matches_info(event)
    
class MultiSearchTerm:
    """Provided as a term to a SearchQuery, and matches against a number
    of different values."""
    
    def __init__(self, *values):
        self._as_set = set(values)
        self._as_tuple = tuple(values)
    
    def __eq__(self, other):
        if isinstance(other, MultiSearchTerm):
            return tuple(other) == tuple(self)
        else:
            return other in self._as_set
    
    def __iter__(self):
        """Implemented so object can be tuple()'d, and thereby hashed"""
        return iter(self._as_tuple)
    
    def __hash__(self):
        return hash(tuple(self))
    
    def add(self, value):
        if value in self._as_set:
            return
        self._as_set.add(value)
        self._as_tuple += (value,)
    
    def remove(self, value):
        self._as_set.pop(value)
        self._as_tuple = tuple(filter(lambda x: x != value, self._as_tuple))
