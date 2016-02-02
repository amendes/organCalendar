"""" Organ Calendar
__version__ = "0.1"
"""
import kivy
kivy.require('1.8.0')

import calendar
import datetime as dt
import os
import re
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.popup import Popup
# from kivy.uix.widget import Widget
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.modalview import ModalView
from kivy.uix.textinput import TextInput
from kivy.properties import (StringProperty,
                             ObjectProperty,
                             ListProperty,)
from kivy.animation import Animation
from kivy.uix.listview import ListView
from kivy.adapters import simplelistadapter

print('##*** Currently in:', os.getcwd())
# Data stuff
if not os.path.exists('data'):
    os.mkdir('data')

# DATABASE
from kivy.storage.jsonstore import JsonStore
MEMODB = JsonStore('data/memodb.json')
# Get a unique key for the database
def GET_UNIQUE_KEY():
        return int(time.time())

from kivy.logger import Logger


# Custom Calendar
class Calendar(calendar.TextCalendar):
    # fix date
    @staticmethod
    def fix_date(year, month):
        if month == 13:
            month = 1
            year += 1
        elif month == 0:
            month = 12
            year -= 1
        return dt.date(year, month, 1)

    # generator -  get 6 weeks for a month to fill all rows
    def month_days(self, year, month):
        thism = list(self.itermonthdates(year, month))
        nextm_date = self.fix_date(year, month + 1)
        nextm = self.itermonthdates(nextm_date.year, nextm_date.month)
        days = len(thism)
        # yield all days in thism
        # yield from thism (py3)
        for day in thism:
            yield day
        # yield days in nextm that don't exist in thism until 42 days total
        for day in nextm:
            if days == 42:
                return
            elif day not in thism:
                days += 1
                yield day


Logger.info('Building Custom Calendar.')
CALENDAR = Calendar()


class CalendarApp(App):
    # rightnow dateobject for alarms and such
    rightnow = ObjectProperty(dt.datetime.now())
    memos = ObjectProperty(JsonStore('memos.json'))

    def __init__(self, **kwargs):
        Logger.info('Building App')
        super(CalendarApp, self).__init__(**kwargs)
        # Clock.schedule_interval(self.update_time, 1)
        self.popup = AlertPopup()
        self.anim_dismiss_popup = Animation(opacity=0, duration=1.5)
        self.anim_dismiss_popup.bind(on_complete=self.popup.dismiss)

    # update self.rightnow to a new datetime object every 1sec
    def update_time(self, *args):
        self.rightnow = dt.datetime.now()

    def build(self):
        main = MainView()
        return main

    def alert(self, text):
        self.popup.label.text = text
        self.popup.open()
        self.popup.opacity = 1
        self.anim_dismiss_popup.start(self.popup)


class MainView(BoxLayout):
    def __init__(self, **kwargs):
        super(MainView, self).__init__(**kwargs)
        Logger.info('Building Main View')
        self.monthview = None
        self.yearview = None
        # Clock.schedule_once(self.go_monthview, 1)
        self.go_monthview()

    def go_monthview(self, *args, **kwargs):
        if not self.monthview:
            self.monthview = MonthView()
        self.clear_widgets()
        self.add_widget(self.monthview)

    def go_yearview(self, *args):
        if not self.yearview:
            self.yearview = YearWidget()
        self.clear_widgets()
        self.yearview.make_year(2015)
        self.add_widget(self.yearview)


class MonthView(BoxLayout):
    header = StringProperty()

    def __init__(self, **kwargs):
        super(MonthView, self).__init__(**kwargs)
        # Clock.schedule_once(self.startup)
        self.date_picker = DatePicker(self)
        self.startup()

    def startup(self, *args):
        self.make_weekday_headers()
        self.monthdaysview = MonthDaysView(self)
        self.add_widget(self.monthdaysview)

    # def on_size(self, *args):
    #     self.date_picker.y = self.y + self.height / 1.5
    #     if self.width > self.height:
    #         self.date_picker.size_hint = (.3, .25)
    #     elif self.height > self.width:
    #         self.date_picker.size_hint = (.5, .2)

    # make the seven week day header labels
    def make_weekday_headers(self, *args):
        weekdays = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
        for day in weekdays:
            dayheader = WeekDayHeader(day)
            self.ids.weekheader.add_widget(dayheader)

    def choose_date(self, *args):
        month_name = calendar.month_name[self.monthdaysview.date.month]
        self.date_picker.month.text = month_name
        self.date_picker.year.text = str(self.monthdaysview.date.year)
        self.date_picker.open()
        self.date_picker.y = self.y + self.height / 1.5

    def goto_date(self, date=None):
        self.monthdaysview.goto_date(date)


class WeekDayHeader(Label):
    def __init__(self, day, **kwargs):
        super(WeekDayHeader, self).__init__(**kwargs)
        self.text = str(day)


class MonthDaysView(GridLayout):
    # App rightnow property rightnow dateobject for alarms and such
    rightnow = ObjectProperty(dt.datetime.now())
    date = ObjectProperty()
    memos = ObjectProperty()

    def __init__(self, monthview, **kwargs):
        super(MonthDaysView, self).__init__(**kwargs)
        # current date in view
        self.date = None
        # parent
        self.monthview = monthview
        self.daypopup = DayPopup()
        # Clock.schedule_once(self.startup)
        self.startup()

    def startup(self, *args):
        # current view date and today setup
        self.date = self.rightnow.date()
        for i in range(42):
            self.add_widget(MonthDay(monthview=self))
        self.change_month()

    def goto_date(self, date=None):
        if not date:
            self.date = self.rightnow.date()
        elif not isinstance(date, dt.date):
            raise TypeError('need date of type datetime.date, not', type(date))
        elif self.date != date:
            self.date = date
        else:
            return
        self.change_month()

    def change_month(self, offset=0):
        # set current view date if offset
        if offset:
            self.date = CALENDAR.fix_date(self.date.year, self.date.month + offset)
        self.monthview.header = self.date.strftime("%B %Y")
        self.change_days()

    def change_days(self):
        # Colors:
        # 'current': (.2, .7, .7, .8),
        # 'other':   (.5, .7, .7, .9),
        # 'today':   (.4, .8, 0, .8)}
        Clock.unschedule(self.mark_days)
        dates = CALENDAR.month_days(self.date.year, self.date.month)
        for date, monthday in zip(dates, reversed(self.children)):
            # optimization?: don't use date object
            monthday.date = date.timetuple()[:3]
            # TODO: move to kv
            monthday.text = str(date.day)
            # other days
            if date.month != self.date.month:
                monthday.daycolor = (.5, .7, .7, .9)
            # current month dates
            elif date != self.rightnow.date():
                monthday.daycolor = (.2, .7, .7, .8)
            # todate
            else:
                monthday.daycolor = (.4, .8, 0, .8)
            # recolor marked dates to black
            monthday.color = (0, 0, 0, 1)
        Clock.schedule_once(self.mark_days, .5)

    # def open_daynote(self, day):
    #     self.daypopup.open(day=day.date)

    def mark_days(self, day):
        memos = MEMODB.find(year=self.date.year, month=self.date.month)
        days_with_memo = [(d['year'], d['month'], d['day']) for k, d in memos]
        for monthday in self.children:
            if monthday.date in days_with_memo:
                monthday.color = (1, 0, 0, 1)
                monthday.has_notes = True
            else:
                monthday.has_notes = False

    def on_touch_up(self, touch):
        if self.collide_point(*touch.opos):
            xdiff = touch.ox - touch.x
            if xdiff > self.width/10:
                self.change_month(1)
                return True
            elif xdiff < -self.width/10:
                self.change_month(-1)
                return True
        return super(MonthDaysView, self).on_touch_up(touch)


class MonthDay(Label):
    daycolor = ListProperty([1, 1, 1, 1])

    def __init__(self, **kwargs):
        self.monthview = kwargs['monthview']
        self.has_notes = False
        super(MonthDay, self).__init__()

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos) and self.collide_point(*touch.opos):
            self.monthview.daypopup.open(self)
            return True

    @property
    def date(self):
        return (self.year, self.month, self.day)

    @date.setter
    def date(self, datetup):
        self.year, self.month, self.day  = datetup


class DatePicker(Popup):
    month = ObjectProperty()
    year = ObjectProperty()

    def __init__(self, root, **kwargs):
        self.root = root
        super(DatePicker, self).__init__(**kwargs)

    def on_dismiss(self):
        month = list(calendar.month_name).index(self.month.text)
        year = int(self.year.text)
        self.root.goto_date(dt.date(year, month, 1))


class DayPopup(Popup):
    def __init__(self, **kwargs):
        super(DayPopup, self).__init__(**kwargs)
        self.container = AnchorLayout()
        self.add_widget(self.container)
        self.daynote = DayNote(self)
        self.dayoptions = None
        self.daynotelist = None

    def open(self, day, *args, **kwargs):
        self.title = dt.date(*day.date).strftime("%A %d %B %Y")
        self.day = day
        if day.has_notes:
            self.open_dayoptions()
        else:
            self.open_daynote()
        super(DayPopup, self).open(self, *args, **kwargs)

    def open_dayoptions(self):
        if not self.dayoptions:
            self.dayoptions = DayOptions(self)
        self.container.clear_widgets()
        self.size_hint = (.3, .2)
        self.container.add_widget(self.dayoptions)

    def open_daynote(self):
        self.container.clear_widgets()
        self.size_hint = (.5, .5)
        hour, minute = dt.datetime.now().timetuple()[3:5]
        self.daynote.time.text = "{:02}:{:02}".format(hour, minute)
        self.container.add_widget(self.daynote)

    def open_daynotelist(self):
        if not self.daynotelist:
            self.daynotelist = DayNoteList()
        self.container.clear_widgets()
        self.size_hint = (.3, .6)
        year, month, day = self.day.date
        notes = MEMODB.find(year=year, month=month, day=day)
        self.container.add_widget(self.daynotelist)
        for k, note in notes:
            time = note['hour'], note['minute']
            subject = note['subject']
            entry = DayNoteListEntry((time, subject))
            self.daynotelist.add_widget(entry)

    def on_dismiss(self, *args, **kwargs):
        self.day = None
        if self.daynote.subject:
            self.daynote.subject.text = ''
        # self.notes.text = ''


class DayOptions(BoxLayout):
    def __init__(self, popup, **kwargs):
        super(DayOptions, self).__init__(**kwargs)
        self.popup = popup


class DayNoteList(BoxLayout):
    pass


class DayNoteListEntry(BoxLayout):
    info = ListProperty()
    def __init__(self, info, **kwargs):
        self.info = info
        super(DayNoteListEntry, self).__init__(**kwargs)

class DayNote(BoxLayout):
    # App
    app = ObjectProperty()
    # HourInput
    time = ObjectProperty()
    # Label
    subject = ObjectProperty()

    def __init__(self, popup, **kwargs):
        super(DayNote, self).__init__(**kwargs)
        self.popup = popup
        self.notesinput = NotesInputView(self)

    def save(self, *args):
        # !!!: fix, make hour/min mandatory?
        if not self.subject.text:
            self.popup.dismiss()
            self.app.alert('No subject')
            return
        year, month, day = self.popup.day.date
        hour, minute = self.time.get()
        MEMODB[GET_UNIQUE_KEY()] = {'year': year,
                                    'month': month,
                                    'day': day,
                                    'hour': hour,
                                    'minute': minute,
                                    'subject': self.subject.text,
                                    'notes': self.notesinput.text}

        self.popup.dismiss()


class NotesInputView(AnchorLayout):
    text = ObjectProperty()

    def __init__(self, daynote, **kwargs):
        super(NotesInputView, self).__init__(**kwargs)
        self.daynote = daynote


class NotesInput(TextInput):
    pass


class HourInput(TextInput):
    subject = ObjectProperty()

    def __init__(self, **kwargs):
        super(HourInput, self).__init__(**kwargs)
        self.reg = re.compile(r'\d\d:\d\d')

    # return True to NOT progate the number
    def check_key(self, key):
        if self.cursor_col == 0:
            if key > 2:
                self.select_hour()
                return True
        elif self.cursor_col == 1:
            if self.text[0] == '2' and key > 3:
                return True
            self.select_minutes()
        elif self.cursor_col == 3:
            if key > 5:
                return True
        elif self.cursor_col == 4:
            if key > 9:
                return True
        elif self.cursor_col == len(self.text):
            return True
        else:
            return False

    def on_text_validate(self, *args):
        if not self.reg.match(self.text):
            colon = self.text.index(':')
            hour = int(self.text[:colon])
            minute = int(self.text[colon + 1:])
            self.text = "{:02}:{:02}".format(hour, minute)
        self.subject.focus = True

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.select_hour()
            return super(HourInput, self).on_touch_down(touch)

    def on_double_tap(self, *args):
        self.select_hour()

    def on_triple_tap(self, *args):
        self.select_hour()

    def keyboard_on_key_down(self, instance, keycode, text, modifiers):
        key = text
        try:
            key = int(text)
        except ValueError:
            if keycode[1] == 'backspace':
                if 1 <= self.cursor_col <= 3:
                    self.select_hour()
                elif 4 <= self.cursor_col <= 5:
                    self.select_minutes()
                return True
            elif keycode[1] == 'escape' or keycode[1] == 'enter':
                pass
            else:
                return True
        else:
            # True means number is NOT accepted
            if self.check_key(key):
                return True
        return super(HourInput, self).keyboard_on_key_down(instance,
                                                           keycode,
                                                           text,
                                                           modifiers)

    def select_hour(self, *args):
        def wrap(*args):
            self.select_text(0, self.text.index(':'))
            self.cursor = (0, 0)
        Clock.schedule_once(wrap)

    def select_minutes(self, *args):
        def wrap(*args):
            self.select_text(self.text.index(':') + 1, len(self.text))
            self.cursor = (3, 0)
        Clock.schedule_once(wrap)

    def get(self):
        return (self.text[:2], self.text[3:5])


# class YearWidget(GridLayout):
class YearWidget(Label):
    def __init__(self, **kwargs):
        super(YearWidget, self).__init__(**kwargs)

    def make_year(self, year):
        self.text = CALENDAR.formatyear(2016)
    #     for i in range(1, 13):
    #         month = YearMonth(2016, i)
    #         self.add_widget(month)


# class YearMonth(Label):
#     def __init__(self, year, month, **kwargs):
#         super().__init__(**kwargs)
#         self.year = year
#         self.month = month
#         Clock.schedule_once(self.make_month)

#     def make_month(self,*args, **kwargs):
#         self.text = CALENDAR.formatmonth(self.year, self.month)


class AlertPopup(ModalView):
    def __init__(self, **kwargs):
        super(AlertPopup, self).__init__(**kwargs)
        self.opacity = 0
        self.size_hint = (.2, .15)
        self.label = Label(pos=self.pos,
                           size=(100, 100),
                           text='ALERT')
        self.add_widget(self.label)


if __name__ == "__main__":
    CalendarApp().run()
