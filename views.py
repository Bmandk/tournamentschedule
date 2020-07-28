import asyncio

from pyplanet.views import TemplateView
from pyplanet.views.generics import ListView

from .models import TournamentSchedule


class ScheduleView(TemplateView):
    template_name = 'tournamentschedule/scheduler.xml'

    def __init__(self, app, player, instance=None):
        super().__init__(app.context.ui)

        self.app = app
        self.player = player

        self.subscribe('button_close', self.close)
        self.subscribe('button_cancel', self.close)
        self.subscribe('button_save', self.save)

        self.response_future = asyncio.Future()

        self.destroy_on_exit = False
        self.instance = instance
        if (instance is None):
            self.instance = TournamentSchedule()
            self.destroy_on_exit = True

    async def display(self, **kwargs):
        kwargs['player'] = self.player
        return await super().display(**kwargs)

    async def get_context_data(self):
        context = await super().get_context_data()
        context['name'] = self.instance.name
        context['format'] = self.instance.format
        context['maplist'] = self.instance.maplist
        context['starttime'] = self.instance.start_time
        context['mon'] = self.instance.mon
        context['tue'] = self.instance.tue
        context['wed'] = self.instance.wed
        context['thu'] = self.instance.thu
        context['fri'] = self.instance.fri
        context['sat'] = self.instance.sat
        context['sun'] = self.instance.sun

        return context

    async def wait_for_response(self):
        return await self.response_future

    async def close(self, player, *args, **kwargs):
        if self.player_data and player.login in self.player_data:
            del self.player_data[player.login]

        if (self.destroy_on_exit):
            await self.destroy()
        else:
            self.response_future.set_result(None)
            self.response_future.done()

    async def save(self, player, action, values, *args, **kwargs):
        name = values['schedule_name_field']
        format = values['schedule_format_field']
        maplist = values['schedule_maplist_field']
        starttime = values['schedule_starttime_field']
        days = [int(values['schedule_mon_field']),
                int(values['schedule_tue_field']),
                int(values['schedule_wed_field']),
                int(values['schedule_thu_field']),
                int(values['schedule_fri_field']),
                int(values['schedule_sat_field']),
                int(values['schedule_sun_field'])]

        self.instance.name = name
        self.instance.format = format
        self.instance.maplist = maplist
        self.instance.start_time = starttime
        self.instance.mon = days[0]
        self.instance.tue = days[1]
        self.instance.wed = days[2]
        self.instance.thu = days[3]
        self.instance.fri = days[4]
        self.instance.sat = days[5]
        self.instance.sun = days[6]

        await self.instance.save()
        if (self.destroy_on_exit):
            await self.destroy()
        else:
            self.response_future.set_result(self.instance)
            self.response_future.done()


class ScheduleListView(ListView):
    query = TournamentSchedule.select()
    model = TournamentSchedule
    title = 'Select your item'

    def __init__(self, app, player, *args, **kwargs):
        self.id = 'tournamentschedule.schedulelist'
        super(ScheduleListView, self).__init__(*args, **kwargs)
        self.app = app
        self.manager = app.context.ui
        self.player = player
        self.child = None

    async def display(self, **kwargs):
        kwargs['player'] = self.player
        return await super().display(**kwargs)

    async def get_fields(self):
        return [
            {'name': 'Name', 'index': 'name', 'searching': True, 'sorting': False, 'width': 30,
             'action': self.action_edit},
            {'name': 'Format', 'index': 'format', 'searching': True, 'sorting': False, 'width': 20,
             'action': self.action_edit},
            {'name': 'Maplist', 'index': 'maplist', 'searching': True, 'sorting': False, 'width': 30,
             'action': self.action_edit},
            {'name': 'Start Time', 'index': 'start_time', 'searching': True, 'sorting': False, 'width': 25,
             'action': self.action_edit},
            {'name': 'Mon', 'index': 'mon', 'searching': False, 'sorting': False, 'width': 7,
             'action': self.action_edit},
            {'name': 'Tue', 'index': 'tue', 'searching': False, 'sorting': False, 'width': 7,
             'action': self.action_edit},
            {'name': 'Wed', 'index': 'wed', 'searching': False, 'sorting': False, 'width': 7,
             'action': self.action_edit},
            {'name': 'Thu', 'index': 'thu', 'searching': False, 'sorting': False, 'width': 7,
             'action': self.action_edit},
            {'name': 'Fri', 'index': 'fri', 'searching': False, 'sorting': False, 'width': 7,
             'action': self.action_edit},
            {'name': 'Sat', 'index': 'sat', 'searching': False, 'sorting': False, 'width': 7,
             'action': self.action_edit},
            {'name': 'Sun', 'index': 'sun', 'searching': False, 'sorting': False, 'width': 7,
             'action': self.action_edit},
        ]

    async def get_actions(self):
        return [
            {
                'name': 'Delete',
                'action': self.action_delete,
                'style': 'Icons64x64_1',
                'substyle': 'Close',
                'width': 5
            },
        ]

    async def action_edit(self, player, values, instance, **kwargs):
        if self.child:
            return

        # Show edit view.
        self.child = ScheduleView(self.app, self.player, instance)
        await self.child.display()
        await self.child.wait_for_response()
        await self.child.destroy()
        await self.display()  # refresh.
        self.child = None

    async def action_delete(self, player, values, instance, **kwargs):
        await instance.destroy()
        await self.display()
