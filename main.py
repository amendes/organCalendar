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
from itertools import dropwhile

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
                             ListProperty,
                             BooleanProperty,)
from kivy.animation import Animation

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
    def __init__(self, *args, **kwargs):
        self.one_day = dt.timedelta(days=1)
        super().__init__(*args, **kwargs)

    # fix date
    @staticmethod
    def next_month(date, offset=1):
        year, month = date.year, date.month + offset
        if month == 13:
            month = 1
            year += 1
        elif month == 0:
            month = 12
            year -= 1
        return dt.date(year, month, 1)

    # generator -  get 6 weeks for a month to fill all rows
    def get_month_days(self, date):
        """Return 42days (6 weeks). Yield all days in this month then
        yield days in next momth that don't exist
        in this month.
        """
        year, month = date.year, date.month
        thism = list(self.itermonthdates(year, month))
        for day in thism:
            yield day
        nextm_date = self.next_month(date)
        nextm = self.itermonthdates(nextm_date.year, nextm_date.month)
        no_of_extra_days = range(42 - len(thism))
        rest_of_days = dropwhile(lambda day: day in thism, nextm)
        for _, day in zip(no_of_extra_days, rest_of_days):
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
        main = Main()
        return main

    def alert(self, text):
        self.popup.label.text = text
        self.popup.open()
        elf.popup.opacity = 1
        self.anim_dismiss_popup.start(self.popup)


class Main(BoxLayout):
    def __init__(self, **kwargs):
        super(Main, self).__init__(**kwargs)
        Logger.info('Building Main View')
        # Clock.schedule_once(self.go_month, 1)
        self.month = None
        self.year = None
        self.show_month()

    def show_month(self, *args, **kwargs):
        if not self.month:
            self.month= Month(self)
        self.clear_widgets()
        self.add_widget(self.month)

    def show_year(self, *args):
        if not self.yearview:
            self.yearview = YearWidget()
        self.clear_widgets()
        self.yearview.make_year(2015)
        self.add_widget(self.yearview)


# month controller
class Month(BoxLayout):
    header = StringProperty()

    def __init__(self, main, **kwargs):
        super(Month, self).__init__(**kwargs)
        self.main = main
        # Clock.schedule_once(self.startup)
        self.date_picker = DatePicker(self)
        self.startup()

    def startup(self, *args):
        self.make_weekday_headers()
        self._popup = DayPopup(self)
        self.view = MonthView(self)
        self.add_widget(self.view)

    @property
    def date(self):
        return self.view.date

    # def on_size(self, *args):
    #     self.date_picker.y = self.y + self.height / 1.5
    #     if self.width > self.height:
    #         self.date_picker.size_hint = (.3, .25)
    #     elif self.height > self.width:
    #         self.date_picker.size_hint = (.5, .2)

    # make the seven week day header labels
    def make_weekday_headers(self, *args):
        weekdays = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
        weekheader = self.ids.weekheader
        for day in weekdays:
            dayheader = WeekDayHeader(day)
            weekheader.add_widget(dayheader)

    def choose_date(self, *args):
        month_name = calendar.month_name[self.view.date.month]
        self.date_picker.month.text = month_name
        self.date_picker.year.text = str(self.view.date.year)
        self.date_picker.open()
        self.date_picker.y = self.y + self.height / 1.5

    def go_today(self, date=None):
        self.view.date = dt.date.today()

    @property
    def popup(self):
        return self._popup

    def save_entry(self, day):
        pass



class WeekDayHeader(Label):
    def __init__(self, day, **kwargs):
        super(WeekDayHeader, self).__init__(**kwargs)
        self.text = str(day)


class MonthView(GridLayout):
    # App rightnow property rightnow dateobject for alarms and such
    today = ObjectProperty(dt.date.today())
    date = ObjectProperty()
    memos = ObjectProperty()

    def __init__(self, month, **kwargs):
        super(MonthView, self).__init__(**kwargs)
        self.date = None
        self.month = month
        # Clock.schedule_once(self.startup)
        self.startup()

    def startup(self, *args):
        for i in range(42):
            self.add_widget(Day(self))
        # make the actual month by changing date kvproperty
        self.date = self.today

    def on_date(self, obj, date):
        self.change_month()

    def scroll_month(self, offset):
        self.date = CALENDAR.next_month(self.date, offset)

    def change_month(self):
        """Set header, retrieve memos, call change_days"""
        self.month.header = self.date.strftime("%B %Y")
        # json dict
        memos = MEMODB.find(year=self.date.year, month=self.date.month)
        self.daymemos = [(d['year'], d['month'], d['day']) for k, d in memos]
        self.change_days()

    def change_days(self):
        """Iterate over children(day widgets) and change the date kvproperty"""
        # Colors:
        # 'current': (.2, .7, .7, .8),
        # 'other':   (.5, .7, .7, .9),
        # 'today':   (.4, .8, 0, .8)}
        # days is datetime.date list
        days = CALENDAR.get_month_days(self.date)
        for date, widget in zip(days, reversed(self.children)):
            widget.date = date

    def on_touch_up(self, touch):
        if self.collide_point(*touch.opos):
            xdiff = touch.ox - touch.x
            if xdiff > self.width/10:
                self.scroll_month(1)
                return True
            elif xdiff < -self.width/10:
                self.scroll_month(-1)
                return True
        return super(MonthView, self).on_touch_up(touch)

# day controller
class Day(Label):
    daycolor = ListProperty([1, 1, 1, 1])
    has_notes = BooleanProperty(False)
    date = ObjectProperty()

    def __init__(self, view=None, **kwargs):
        if view is not None:
            self.view = view
        super(Day, self).__init__(**kwargs)

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos) and self.collide_point(*touch.opos):
            if self.has_notes:
                self.popup.show('options')
            else:
                self.popup.show('entry')
            return True
        return False

    def get_popup_view(self, name):
        if name == 'entry':
            view = ContentEntry(self)
        elif name == 'options':
            view = ContentOptions(self)
        elif name == 'list':
            view = ContentList(self)
        return view

    def on_has_notes(self, *args):
        if self.has_notes:
            self.color = (1, 0, 0, 1)
        else:
            self.color = (0, 0, 0, 1)

    def on_date(self, obj, date):
        # TODO: move to kv
        self.text = str(date.day)
        # other days
        if date.month != self.parent.date.month:
            self.daycolor = (.5, .7, .7, .9)
        # current month days
        elif date != self.parent.today:
            self.daycolor = (.2, .7, .7, .8)
        # today
        else:
            self.daycolor = (.4, .8, 0, .8)
        # recolor marked dates to black
        if self.date.timetuple()[:3] in self.parent.daymemos:
            self.has_notes = True
        else:
            self.has_notes = False

    # @property
    # def date(self):
    #     return (self.year, self.month, self.day)

    # @date.setter
    # def date(self, datetup):
    #     self.year, self.month, self.day  = datetup


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

###### POPUP ######
class DayPopup(Popup):
    def __init__(self, context, **kwargs):
        super(DayPopup, self).__init__(**kwargs)
        self.context = context
        self.views = {}

    def on_content(self, *args):
        super().on_content(*args)
        if self.content is None:
            self.dismiss()
        else:
            self.open()

    def show(self, view):
        view = self.views[view]
        if view is None:
            view = self.context.get_view(view)
        with view.open(self.context):
            self.content = view


    # def on_dismiss(self, *args, **kwargs):
    #     self.day = None
    #     if self.daynote.subject:
    #     # self.notes.text = ''


class ContentOptions(BoxLayout):
    def __init__(self, popup, **kwargs):
        super(ContentOptions, self).__init__(**kwargs)
        self.popup = popup

    def prepare(self, context):
        self.popup.size_hint = (.6, .6)

class ContentList(BoxLayout):
    def prepare(self, context):
        self.popup.size_hint = (.6, .6)
        year, month, day = context.date.timetuple()[:3]
        notes = MEMODB.find(year=year, month=month, day=day)
        for k, note in notes:
            time = note['hour'], note['minute']
            subject = note['subject']
            entry = DayNoteListEntry((time, subject))
            self.daynotelist.add_widget(entry)


class ContentListEntry(BoxLayout):
    info = ListProperty()
    def __init__(self, info, **kwargs):
        self.info = info
        super(ContentListEntry, self).__init__(**kwargs)

class ContentEntry(BoxLayout):
    # App
    app = ObjectProperty()
    # HourInput
    time = ObjectProperty()
    # Label
    subject = ObjectProperty()

    def __init__(self, popup, **kwargs):
        super(ContentEntry, self).__init__(**kwargs)
        self.popup = popup
        self.notesinput = NotesInputView(self)

    def open(self, context):
        self.day = context
        date = self.date = context.date
        self.popup.title = date.strftime("%A %d %B %Y")
        self.popup.size_hint = (.6, .6)
        hour, minute = dt.datetime.now().timetuple()[3:5]
        self.time.text = "{:02}:{:02}".format(hour, minute)
        try:
            yield self
        finally:
            self.subject.text = ''
            self.popup.content = None

    def save(self, *args):
        # !!!: fix, make hour/min mandatory?
        if not self.subject.text:
            self.popup.dismiss()
            self.app.alert('No subject')
            return
        # move to month controller
        year, month, day = day.date.timetuple()[:3]
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
