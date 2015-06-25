""" Organ Calendar
__version__ = "0.1"
"""
import kivy
kivy.require('1.8.0')
from kivy.app import App
# from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
import datetime as dt
import calendar
from kivy.clock import Clock
from kivy.properties import (StringProperty,
                             NumericProperty,
                             ObjectProperty,
                             ListProperty,)
from kivy.storage.jsonstore import JsonStore


# calendar.Calendar modified
class MyCalendar(calendar.Calendar):

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


# App instance
class OrganApp(App):
    def build(self):
        main = OrganMain()
        return main


class OrganMain(BoxLayout):
    pass

    # def __init__(self, **kwargs):
    #     super(OrganMain, self).__init__(**kwargs)
    #     self.memos = JsonStore('memos.json')
    #     self.memos.put('test a test with spaces', notes='asdf')


# calendar tab of book
class CalTab(BoxLayout):

    # rightnow dateobject for alarms and such
    rightnow = ObjectProperty(dt.datetime.now())

    def __init__(self, **kwargs):
        super(CalTab, self).__init__(**kwargs)
        # time updater every 1 sec
        self.date_picker = GoToDate()
        Clock.schedule_interval(self.update_time, 1)
        # schedule of gui building (better alternative?)

    # update self.rightnow to a new datetime object every 1sec
    def update_time(self, *args):
        self.rightnow = dt.datetime.now()

    # make month widget with today date
    def go_today(self, *args):
        self.ids.calview.go_today()

    def choose_date(self, *args):
        self.date_picker.open()


class CalView(BoxLayout):

    date_in_view = ObjectProperty(allownone=True)
    header = StringProperty()

    def __init__(self, **kwargs):
        super(CalView, self).__init__(**kwargs)
        Clock.schedule_once(self.startup)

    def startup(self, *args):
        self.cal = MyCalendar()
        self.make_weekday_headers()
        self.monthview = MonthView(self.cal)
        self.add_widget(self.monthview)

    # make the seven week day header labels
    def make_weekday_headers(self, *args):
        weekdays = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
        for day in weekdays:
            dayheader = WeekDayHeader(day)
            self.ids.weekheader.add_widget(dayheader)

    def go_today(self, *args):
        self.monthview.go_today()


class WeekDayHeader(Label):

    def __init__(self, day, **kwargs):
        super(WeekDayHeader, self).__init__(**kwargs)
        self.text = str(day)


# MonthWidget - called with dateobj and carousel?! :\
class MonthView(GridLayout):

    date = ObjectProperty()

    def __init__(self, cal, **kwargs):
        super(MonthView, self).__init__(**kwargs)
        self.cal = cal
        self.daypopup = DayPopup()
        Clock.schedule_once(self.startup)

    def startup(self, *args):
        # current view date and today setup
        self.date = self.today = dt.date.today()
        for i in range(42):
            self.add_widget(DayWidget())
        # self.parent.update_header(self.today.strftime("%B %Y"))
        self.change_month()

    def on_date(self, instance, date):
        self.parent.date_in_view = date
        self.parent.header = date.strftime("%B %Y")

    def go_today(self):
        # change current view date to today
        self.date = self.date.today()
        self.change_month()

    def change_month(self, offset=0):
        # set current view date if offset
        if offset:
            self.date = self.cal.fix_date(self.date.year,
                                          self.date.month + offset)
        self.change_days()

    # set day text and label color
    def change_days(self):
        # Colors:
        # 'current': (.2, .7, .7, .8),
        # 'other':   (.5, .7, .7, .9),
        # 'today':   (.4, .8, 0, .8)}
        days = self.cal.month_days(self.date.year, self.date.month)
        for day, daywidget in zip(days, reversed(self.children)):
            daywidget.text = str(day.day)
            # other days
            if day.month != self.date.month:
                daywidget.daycolor = (.5, .7, .7, .9)
            # current month days
            elif day != self.today:
                daywidget.daycolor = (.2, .7, .7, .8)
            # today
            else:
                daywidget.daycolor = (.4, .8, 0, .8)

    def open_daynote(self, day):
        self.daypopup.set_date(dt.date(self.date.year,
                               self.date.month,
                               int(day.text)))
        self.daypopup.open()

    # def on_touch_down(self, touch):
    #     self.touched = True if self.collide_point(*touch.pos) else False

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

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos) and self.collide_point(*touch.opos):
            self.parent.open_daynote(self)
            return True

class GoToDate(Popup):
    pass


class DayPopup(Popup):

    dateobj = ObjectProperty(None)
    hour = ObjectProperty(None)
    minute = ObjectProperty(None)
    subject = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(DayPopup, self).__init__(**kwargs)
        # self.year, self.month, self.day = dtobj.timetuple()[:3]
        # self.day = date
        # self.title = date.strftime("%A %d %B")
        self.memos = JsonStore('memos.json')

    def set_date(self, date):
        self.date = date
        self.title = date.strftime("%A %d %B %Y")

    def save(self, *args):
        # !!!: fix, make hour/min mandatory?
        try:
            hour = int(self.hour.text)
            minute = int(self.minute.text)
        except ValueError:
            hour = 0
            minute = 0


class HourMemoInput(TextInput):

    # minute textinput widget
    minute = ObjectProperty()

    # FIX
    # don't let user input non valid hours
    def insert_text(self, substring, from_undo=False):
        superreturn = super(HourMemoInput, self).insert_text('', from_undo=from_undo)
        try:
            int(substring)
        except ValueError:
            return superreturn
        if not self.text and int(substring) > 2:
            return superreturn
        elif self.text == '2' and int(substring) > 3:
            return superreturn
        elif len(self.text) == 2:
            return superreturn
        else:
            return super(HourMemoInput, self).insert_text(substring,
                                                          from_undo=from_undo)

    def on_text(self, *args):
        # change focus to minute textinput
        if len(self.text) == 2:
            self.focus = False
            Clock.schedule_once(self.change_focus)

    def change_focus(self, *args):
        self.minute.focus = True


class MinMemoInput(TextInput):

    # hour textinput widget
    hour = ObjectProperty()

    # don't let user input non valid minutes
    def insert_text(self, substring, from_undo=False):
        superreturn = super(MinMemoInput, self).insert_text('', from_undo=from_undo)
        try:
            int(substring)
        except ValueError:
            return superreturn
        if not self.text and int(substring) > 5:
            return superreturn
        elif len(self.text) == 2:
            return superreturn
        else:
            return super(MinMemoInput, self).insert_text(substring,
                                                         from_undo=from_undo)

    def on_key_down(self, *args):
        print(args)


class YearWidget(GridLayout):
    def __init__(self, dateobj, **kwargs):
        super(self.__class__,self).__init__(**kwargs)
        self.mycal = calendar.Calendar()
        self.dateobj = dateobj
        self.year = self.dateobj.year
        self.make_year_grid(self.year)

    def make_year_grid(self, year):
        for month in range(12):
            monthwi = MonthWidget(self.dateobj)
            self.add_widget(monthwi)


if __name__ == "__main__":
    OrganApp().run()
