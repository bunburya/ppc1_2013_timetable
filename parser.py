"""Stuff to parse the output of running ps2ascii on the timetable PDF"""

class Parser:
    
    week_regex = re.compile(r'^Commencing:(\d+)Week: (\d{2}-\w{3}-\d{2})$')
    day_off_regex = re.compile(r'^0 ')
    event_regex = re.compile(r'^\d{2}:\d{2}')
    
    # Parsing:
    # - Parse groups, location and organiser from end of string
    # - Parse time and code from start of string
    # - What's left is the name
    
    tut_group_regexes = {
            # This dict maps potential regexes for the core group
            # listing to the number of characters that need to be shaved
            # of the end after the core groups are extracts
            
            # Where values are lambdas and not ints, they are functions
            # which take the *extracted* string and output the length to
            # be shaved off.
            re.compile(r'Core (\d{2}-\d{2})$'): 10,      # Core 01-02
            re.compile(r'Core (\d{2}/\d{2})$'): 10,      # Core 01/02
            re.compile(r'Core (\d{2}/\d{2}-\d{2})$'): 13,# Core 01/02-03
            re.compile(r'Core (\d{2}-\d{2}/\d{2})$'): 13,# Core 01-02/03
            re.compile(r'(Blue \w-\w) \((\d{1,2}-\d{1,2})\)$'):
                lambda s: len(s) + 3,                  # Blue A-B (1-2)
            re.compile(r'(Red \w-\w) \((\d{1,2}-\d{1,2})\)$'):
                lambda s: len(s) + 3,                   # Red A-B (1-2)
            re.compile(r'(ALL)$'): 3,
            re.compile(r'(All)$'): 3,
            re.compile(r'(n/a)$'): 3,
            re.compile(r'(TBC)$'): 3
        }
    
    involve_all_groups = {
            'ALL',
            'All',
            'n/a',
            'TBC'
        }
    
    location_regexes = {
            re.compile(r'(Lecture Theatre)$'): 15,
            re.compile(r'(IT Study Room)$'): 13,
            re.compile(r'(IT Ed Centre)$'): 12,
            re.compile(r'(Blue Room)$'): 9,
            re.compile(r'(Vanilla Cafe\')$'): 13,
            re.compile(r'(Language Lab)$'): 12, #testing
            re.compile(r'(Sem \d{2}-\d{2})$'): 9,
            re.compile(r'(Sem \d-\d)$'): 7,
            re.compile(r'(Sem \w-\w \(Gr Hall\))$'): 17,
            re.compile(r'(n/a)$'): 3,
            re.compile(r'(Atrium)$'): 6,
            re.compile(r'(Presidents Hall)$'): 15,
            re.compile(r'(Green Hall)$'): 10,
            re.compile(r'(IT Rooms)$'): 8,
            re.compile(r'(Kings Inns)$'): 10,
            re.compile(r'(Red Cow Moran H)$'): 15
        }
    
    time_regex = re.compile(r'^(\d{2}:\d{2})( - ?(\d{2}:\d{2}))?')
    first_event_date_regex = re.compile(r'(\w{3} \d{1,2} \w{3} \d{2})$')
    
    course_managers = [
        'Gabriel Brennan',
        'Maura Butler',
        'Padraic Courtney',
        'Joanne Cox',
        'Eva Massa',
        'Jane Moffatt',
        'Colette Reid',
        'Attracta O\'Regan',
        'Fionna Fox',
        'SDS',
        'n/a',
        'Paula Sheedy',
        'Geoffrey Shannon',
        'IT Section',
        'All',
        'Rachael Hession',
        'Anne Walsh',
        'Colette Reid / Mau'
        ]
        
    def __init__(self):
        self.all_sem_groups = (self.parse_sem_groups('Red A-H')
                + self.parse_sem_groups('Red K-R')
                + self.parse_sem_groups('Blue A-H')
                + self.parse_sem_groups('Blue K-R'))

    def parse_file(self, f):
        # TODO:  Sometimes new day happens without prior empty line.
        # We need to detect new days by presence of date in line (and
        # test this against date of previous day to make sure it's not
        # just a page break).  I think this will also mean proper
        # parsing of day off lines.
        tt = Timetable()
        new_day = True
        day = None
        for line in f:
            try:
                print('week defined as {}'.format(week))
            except:
                print('week not defined')
            line = line.strip()
            print(line)
            #if not line:
            #    new_day = True
            match = re.match(self.week_regex, line)
            if match:
                print('ADDING WEEK')
                wnum = match.group(1)
                t = time.strptime(match.group(2), '%d-%b-%y')
                week = tt.new_week(int(match.group(1)), datetime.date(*t[:3]))
                new_day = True
                continue
            match = re.match(self.day_off_regex, line)
            if match:
                day = week.new_day()
                print('added {} to {}'.format(day, week))
                evt = day.new_event(off=True)
                evt.day = day
                #new_day = False
                continue
            match = re.match(self.event_regex, line)
            if match:
                print('declaring event in {}'.format(week))
                event = Event(week)
                self.parse_event_str(line, event)
                #if day is None:
                #    day = week.new_day()
                #day.events.append(event)
                print('event is in {}'.format(event.day))
                #new_day = False
        return tt
    
    def parse_tut_groups(self, string):
        """Takes a string indicating a range or selection of core groups
        and returns the groups caught by the string"""
        print('parse_groups called with {}'.format(string))
        numstack = []
        rangestack = []
        groups = []
        in_range = False    # Whether the current section of the string
                            # refers to a range of groups (01-10)
        for c in string + '|':  # '|' indicates end of string; should
                                # not appear anywhere else in string
            if c.isdigit():
                #print('appending {} to numstack'.format(c))
                numstack.append(c)
            elif c == '-':
                in_range = True
                #print('pushing {} to rangestack'.format(''.join(numstack)))
                rangestack.append(int(''.join(numstack)))
                numstack = []
            elif c in {'/', '|'}:
                if in_range:
                    #print('pushing {} to rangestack'.format(''.join(numstack)))
                    rangestack.append(int(''.join(numstack)))
                    numstack = []
                    in_range = False
                else:
                    print('adding {} to groups'.format(''.join(numstack)))
                    groups.append(int(''.join(numstack)))
                    numstack = []
        
        if rangestack:
            start, end = rangestack
            groups.extend(range(start, end+1))
        if numstack:
            groups.append(int(''.join(numstack)))
        return groups
    
    def parse_sem_groups(self, string):
        colour, letters = string.split(' ')
        start, end = letters.split('-')
        return ['{} {}'.format(colour, chr(i)) for i in range(ord(start), ord(end)+1)]
            
            
    def parse_event_str(self, string, event):
        string = string.strip()
        #print(string)
        # Find tutorial/seminar groups involved groups involved
        for pattern in self.tut_group_regexes:
            match = re.search(pattern, string)
            if not match:
                continue
            try:
                tut_group_str = match.group(2)
                sem_group_str = match.group(1)
            except IndexError:
                sem_group_str = None
                tut_group_str = match.group(1)
            if tut_group_str in self.involve_all_groups:
                event.tutorial_groups = list(range(1, 21))
            else:
                event.tutorial_groups = self.parse_tut_groups(tut_group_str)
            if sem_group_str is None:
                event.seminar_groups = self.all_sem_groups
            else:
                event.seminar_groups = self.parse_sem_groups(sem_group_str)
            try:
                string = string[:-self.tut_group_regexes[pattern]].strip()
            except TypeError:
                string = string[:-self.tut_group_regexes[pattern](''.join(match.groups()))].strip()
            break
        if event.tutorial_groups is EmptyValue:
            event.tutorial_groups = list(range(1, 21))
        if event.seminar_groups is EmptyValue:
            event.seminar_groups = self.all_sem_groups
        print(string)
        
        # First event of each day has the date stuck in the
        # middle of the string.  We use this to detect new days.
        try:
            prev_day = event.week.days[-1]
        except IndexError:
            prev_day = None
        try:
            prev_date = prev_day.date
        except AttributeError:
            prev_date = None
        
        datematch = re.search(self.first_event_date_regex, string)
        if datematch:
            print('datematch found')
            # Either a new day, or a day is continuing after a page break
            datestr = datematch.group(1)
            print(datestr)
            t = time.strptime(datestr, '%a %d %b %y')
            date = datetime.date(*t[:3])
            print(date)
            print(prev_date)
            print(event.week.days)
            if date != prev_date:
                event.day = event.week.new_day()
            else:
                event.day = prev_day
            datelen = len(datestr)
            string = string[:-datelen]
        else:
            event.day = prev_day
        event.day.events.append(event)
            
        # Find location
        for pattern in self.location_regexes:
            match = re.search(pattern, string)
            if not match:
                continue
            print('Matched {}'.format(pattern))
            event.location = match.group()
            string = string[:-self.location_regexes[pattern]].strip()
            break
        # Find course manager
        for name in self.course_managers:
            if string.endswith(name):
                event.coordinator = name
                string = string[:-len(name)]
                break
        # Find start and end times
        match = re.match(self.time_regex, string)
        starts = match.group(1)
        hours, mins = starts.split(':')
        event.starts = datetime.time(int(hours), int(mins))
        ends = match.group(3) or None
        if ends is not None:
            hours, mins = ends.split(':')
            event.ends = datetime.time(int(hours), int(mins))
        else:
            event.ends = None
        string = re.sub(self.time_regex, '', string).strip()
        tokens = string.split(' ')
        # Find course code and event name
        event.code = tokens.pop(0)
        event.name = ' '.join(tokens)
