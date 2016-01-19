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
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.modalview import ModalView
from kivy.uix.textinput import TextInput
from kivy.properties import (StringProperty,
                             ObjectProperty,
                             ListProperty,)
from kivy.animation import Animation

print('##*** Currently in:', os.getcwd())
# Data stuff
if not os.path.exists('data'):
    os.mkdir('data')

from kivy.storage.jsonstore import JsonStore
MEMODB = JsonStore('data/memodb.json')

from kivy.logger import Logger


class Calendar(calendar.TextCalendar):
    # fix date
    def fix_date(self, year, month):
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


class Date(dt.date):
    # iterate over year-month-date
    def __iter__(self):
        for i in (self.year, self.month, self.day):
            yield i

    @property
    def key(self):
        return int(time.time())


# App instance
class CalendarApp(App):
    # rightnow dateobject for alarms and such
    rightnow = ObjectProperty(dt.datetime.now())
    memos = ObjectProperty(JsonStore('memos.json'))

    def __init__(self, **kwargs):
        Logger.info('Building App')
        super(CalendarApp, self).__init__(**kwargs)
        Clock.schedule_interval(self.update_time, 1)
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


# calendar tab of book
class MainView(BoxLayout):
    date_in_view = ObjectProperty()
    calview = ObjectProperty()

    def __init__(self, **kwargs):
        Logger.info('Building Main View')
        super(MainView, self).__init__(**kwargs)
        # time updater every 1 sec
        self.date_picker = GoToDate(self)

    def choose_date(self, *args):
        month_name = calendar.month_name[self.date_in_view.month]
        self.date_picker.month.text = month_name
        self.date_picker.year.text = str(self.date_in_view.year)
        self.date_picker.open()
        self.date_picker.y = self.y + self.height / 1.5

    def goto_date(self, date=None):
        Logger.warning('CHANGE THAT PLZ')
        self.calview.goto_date(date)

    def on_size(self, *args):
        self.date_picker.y = self.y + self.height / 1.5
        if self.width > self.height:
            self.date_picker.size_hint = (.3, .25)
        elif self.height > self.width:
            self.date_picker.size_hint = (.5, .2)

    def go_year(self, *args):
        self.calview.clear_widgets()
        year = YearWidget()
        year.make_year(2015)
        self.calview.add_widget(year)


class CalView(BoxLayout):
    date_in_view = ObjectProperty()
    header = StringProperty()

    def __init__(self, **kwargs):
        super(CalView, self).__init__(**kwargs)
        Clock.schedule_once(self.startup)

    def startup(self, *args):
        self.make_weekday_headers()
        self.monthview = MonthView()
        self.add_widget(self.monthview)

    # make the seven week day header labels
    def make_weekday_headers(self, *args):
        weekdays = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
        for day in weekdays:
            dayheader = WeekDayHeader(day)
            self.ids.weekheader.add_widget(dayheader)

    def goto_date(self, date=None):
        self.monthview.goto_date(date)


class WeekDayHeader(Label):
    def __init__(self, day, **kwargs):
        super(WeekDayHeader, self).__init__(**kwargs)
        self.text = str(day)


# MonthWidget - called with dateobj and carousel?! :\
class MonthView(GridLayout):
    # App rightnow property rightnow dateobject for alarms and such
    rightnow = ObjectProperty(dt.datetime.now())
    date = ObjectProperty()
    memos = ObjectProperty()

    def __init__(self, **kwargs):
        super(MonthView, self).__init__(**kwargs)
        self.daypopup = DayPopup()
        Clock.schedule_once(self.startup)

    def startup(self, *args):
        # current view date and today setup
        self.date = self.rightnow.date()
        for i in range(42):
            self.add_widget(DayWidget(month=self))
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
            self.date = CALENDAR.fix_date(self.date.year,
                                          self.date.month + offset)
        self.parent.date_in_view = self.date
        self.parent.header = self.date.strftime("%B %Y")
        self.change_days()

    # set day text and label color
    def change_days(self):
        # Colors:
        # 'current': (.2, .7, .7, .8),
        # 'other':   (.5, .7, .7, .9),
        # 'today':   (.4, .8, 0, .8)}
        Clock.unschedule(self.mark_days)
        days = CALENDAR.month_days(self.date.year, self.date.month)
        for day, daywidget in zip(days, reversed(self.children)):
            daywidget.datetup = day.timetuple()[:3]
            daywidget.text = str(day.day)
            # other days
            if day.month != self.date.month:
                daywidget.daycolor = (.5, .7, .7, .9)
            # current month days
            elif day != self.rightnow.date():
                daywidget.daycolor = (.2, .7, .7, .8)
            # today
            else:
                daywidget.daycolor = (.4, .8, 0, .8)
            # recolor marked days to black
            daywidget.color = (0, 0, 0, 1)
        Clock.schedule_once(self.mark_days, 1)

    def open_daynote(self, day):
        self.daypopup.set_date(Date(self.date.year,
                               self.date.month,
                               int(day.text)))
        hour, minute = self.rightnow.timetuple()[3:5]
        self.daypopup.ids.time.text = "{:02}:{:02}".format(hour, minute)
        self.daypopup.open()

    def mark_days(self, day):
        memos = MEMODB.find(year=self.date.year,
                              month=self.date.month)
        days_with_memo = [(d['year'], d['month'], d['day']) for k, d in memos]
        for day in self.children:
            if day.datetup in days_with_memo:
                day.color = (1, 0, 0, 1)

    def on_touch_up(self, touch):
        if self.collide_point(*touch.opos):
            xdiff = touch.ox - touch.x
            if xdiff > self.width/10:
                self.change_month(1)
                return True
            elif xdiff < -self.width/10:
                self.change_month(-1)
                return True
        return super(MonthView, self).on_touch_up(touch)


# DayWidget - current called with day -
class DayWidget(Label):
    daycolor = ListProperty([1, 1, 1, 1])

    def __init__(self, **kwargs):
        self.month = kwargs['month']
        super(DayWidget, self).__init__()

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos) and self.collide_point(*touch.opos):
            self.month.open_daynote(self)
            return True


class GoToDate(Popup):
    month = ObjectProperty()
    year = ObjectProperty()

    def __init__(self, root, **kwargs):
        self.root = root
        super(GoToDate, self).__init__(**kwargs)

    def goto_date(self):
        month = list(calendar.month_name).index(self.month.text)
        year = int(self.year.text)
        self.root.goto_date(dt.date(year, month, 1))
        self.dismiss()


class DayPopup(Popup):
    # App
    app = ObjectProperty()
    # HourInput
    time = ObjectProperty()
    # Label
    subject = ObjectProperty()
    # Label
    notes = ObjectProperty()

    def set_date(self, date):
        self.date = date
        self.title = date.strftime("%A %d %B %Y")

    def save(self, *args):
        # !!!: fix, make hour/min mandatory?
        if not self.subject.text:
            self.app.alert('No subject')
            self.dismiss()
            return
        year, month, day = self.date.timetuple()[:3]
        hour, minute = self.time.get()
        MEMODB[self.date.key] = {'year': year,
                                   'month': month,
                                   'day': day,
                                   'hour': hour,
                                   'minute': minute,
                                   'subject': self.subject.text,
                                   'notes': self.notes.text}

        self.dismiss()

    def on_dismiss(self, *args):
        self.subject.text = ''
        self.notes.text = ''


class NoteInputView(BoxLayout):
    pass

class NoteInput(TextInput):
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
            # TODO: FIX! change between hour and minute
            # if self.cursor_col >= 3:
            #     self.select_hour()
            # else:
            #     self.select_minutes()
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
        super(YearWidgt, self).__init__(**kwargs)

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
