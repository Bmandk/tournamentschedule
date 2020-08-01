import asyncio
import datetime

from pyplanet.apps.config import AppConfig
from pyplanet.contrib.command import Command
from pyplanet.apps.core.maniaplanet import callbacks as mp_signals
from pyplanet.apps.core.trackmania import callbacks as tm_signals
from pyplanet.contrib.setting import Setting

from .models import TournamentScheduleModel
from .views import ScheduleView, ScheduleListView


class TournementSchedule(AppConfig):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue_start = False  # Set to true when mode will change at the end of the match
        self.queue_end = False  # Set to true when tournament will end on next map
        self.live = False  # Is set to true when the maplist has been loaded
        self.schedule = []
        self.reload_maplist = None

    async def on_start(self):
        # Settings
        await self.context.setting.register(
            Setting('normal_map_list', 'Map list to return to after tournament', Setting.CAT_OTHER, type=str,
                    default='maplist.txt', description='Map list to return to after tournament'),
            Setting('schedule_start_behavior', 'Schedule start behavior', Setting.CAT_BEHAVIOUR, type=int,
                    default='0', description="0: Don't change timelimit, start after maps finish. 1: Extend timelimit "
                                             "of the map before starting tournament (Starts exactly at the right time). "
                                             "2: End the map at the specified time."),
        )

        # Perms
        await self.instance.permission_manager.register('tournament', 'Manage tournaments', app=self, min_level=2)

        # Commands
        await self.instance.command_manager.register(
            Command(command='starttournament', target=self.command_start_tournament,
                    perms='tournamentschedule:tournament', admin=True,
                    description='Starts tournament with default settings'),
            Command(command='endtournament', target=self.command_end_tournament, perms='tournamentschedule:tournament',
                    admin=True, description='Ends tournament'),
            Command(command='scheduletournament', aliases=['st'], target=self.command_schedule_tournament,
                    perms='tournamentschedule:tournament', admin=True, description='Schedule new tournament'),
            Command(command='tournamentschedulelist', aliases=['tsl'], target=self.command_tournament_schedule_list,
                    perms='tournamentschedule:tournament', admin=True,
                    description='View and edit scheduled tournaments.'),
            Command(command='checkschedule', aliases=['cs'], target=self.command_check_schedule,
                    perms='tournamentschedule:tournament', admin=True, description='Queue tournament if ready.'),
        )

        # Signals
        self.context.signals.listen(mp_signals.map.map_begin, self.signal_map_begin)
        self.context.signals.listen(tm_signals.scores, self.signal_scores)

        await self.refresh_schedule()

    async def signal_map_begin(self, map):
        print('{}'.format(self.schedule))
        if (self.queue_end):
            self.queue_end = False
            await self.end_tournament()
            await self.instance.gbx('NextMap')

        if (self.queue_start):
            self.queue_start = False
            await self.start_tournament(self.schedule[0][0])
            await self.instance.gbx('NextMap')

        if (self.reload_maplist is not None):
            await self.load_maplist(self.reload_maplist)
            self.reload_maplist = None

        await self.check_schedule()  # This can set self.queue_start, so make sure that it is called after the above check

    async def signal_scores(self, players, teams, winner_team, use_teams, winner_player, section, **kwargs):
        # Section: PreEndRound, EndRound, EndMap, EndMatch
        # Player: matchpoints is equal to score limit when they are
        # finalist, and higher than score limit when they are finished. If the previous is not true (not sure right now),
        # then we can also use winner_player to figure out whether a player has won the game, but I am also unsure
        # about that

        # if (section == 'EndRound'):
        # await self.instance.chat(players[0]['matchpoints'])
        # await self.instance.chat("Winner player: " + winner_player + " (is empty: " + winner_player == '' + ")")

        if (section != 'EndMatch'):
            return

        if (self.live):
            self.queue_end = True

    async def command_start_tournament(self, player, data, **kwargs):
        await self.instance.chat('Command not implemented yet..', player)
        #await self.queue_tournament()
        #await self.instance.gbx('NextMap')

    async def command_end_tournament(self, player, data, **kwargs):
        await self.end_tournament()
        await self.instance.gbx('NextMap')

    async def command_schedule_tournament(self, player, data, **kwargs):
        view = ScheduleView(self, player)
        await view.display()

    async def command_tournament_schedule_list(self, player, data, **kwargs):
        view = ScheduleListView(self, player)
        await view.display()

    async def command_check_schedule(self, player, data, **kwargs):
        await self.check_schedule()

    async def refresh_schedule(self):
        schedule_instance = await TournamentScheduleModel.objects.execute(
            TournamentScheduleModel.select()
        )

        now = datetime.datetime.now()
        schedule = []

        # Check if the tournament is today and/or tomorrow
        # If a tournament is at midnight the next day, we should prepare on the current day
        for tournament in schedule_instance:
            d = now.weekday()
            weekdays = []
            if (tournament.mon):
                weekdays.append(0)
            if (tournament.tue):
                weekdays.append(1)
            if (tournament.wed):
                weekdays.append(2)
            if (tournament.thu):
                weekdays.append(3)
            if (tournament.fri):
                weekdays.append(4)
            if (tournament.sat):
                weekdays.append(5)
            if (tournament.sun):
                weekdays.append(6)

            for day in weekdays:
                days_ahead = day - now.weekday()
                if (days_ahead < 0 or (days_ahead == 0 and now.time() > tournament.start_time)):  # Tournament already happened this week or today
                    days_ahead += 7

                next_datetime = datetime.datetime.combine(now.date() + datetime.timedelta(days_ahead),
                                                          tournament.start_time)
                schedule.append([tournament, next_datetime])

        # Sort list by next time
        self.schedule = sorted(schedule, key=lambda t: t[1])

    async def check_schedule(self):
        # At first, only check for the next tournament.
        # TODO: Add support for multiple tournaments, with some queuing system or error checking

        if (len(self.schedule) <= 0):
            return

        now = datetime.datetime.now()
        next_tournament = self.schedule[0]
        schedule_start_behavior = await self.get_setting('schedule_start_behavior')
        settings = await self.instance.mode_manager.get_settings()
        time_limit = 86000
        if ('S_TimeLimit' in settings.keys()):
            time_limit = settings['S_TimeLimit']
        seconds_left = (next_tournament[1] - now).total_seconds()

        if (schedule_start_behavior == 0 and seconds_left <= time_limit):  # Start after map has finished with normal timelimit
            self.queue_start = True
            await self.instance.chat('Starting tournament when map is over')
        elif (schedule_start_behavior == 1 and seconds_left <= time_limit * 2):  # Extend timelimit
            self.queue_start = True
            if (seconds_left <= 0):
                self.instance.gbx('NextMap')
            elif ('S_TimeLimit' in settings.keys()):
                await self.instance.mode_manager.update_settings({'S_TimeLimit': int(seconds_left)})
            await self.instance.chat('Starting tournament when map is over')
        elif (schedule_start_behavior == 2 and seconds_left <= time_limit):  # Start when time is reached no matter the timelimit
            self.queue_start = True
            await asyncio.sleep(seconds_left)
            await self.instance.gbx('NextMap')

        if (self.queue_start):
            new_date = next_tournament[1] + datetime.timedelta(days=7)
            self.schedule.append([next_tournament[0], new_date])
            self.schedule.pop(0)

    async def start_tournament(self, tournament):
        await asyncio.gather(
            self.instance.chat('Starting tournament after loading!'),
            self.load_maplist(tournament.maplist, True),
        )

        self.live = True
        self.queue_start = False

        await self.instance.chat('Starting tournament now!')

    async def end_tournament(self):
        self.live = False

        normal_map_list = await self.get_setting('normal_map_list')
        await self.load_maplist(normal_map_list, True)
        await self.instance.chat('Tournament over now!')

    async def get_setting(self, setting):
        setting = await self.instance.setting_manager.get_setting('tournamentschedule', setting)
        value = await setting.get_value()

        return value

    async def load_maplist(self, maplist, do_reload=False):
        file = 'MatchSettings/{}'.format(maplist)
        await self.instance.map_manager.load_matchsettings(file)
        await self.instance.map_manager.update_list(full_update=True)
        print('{}'.format(self.instance.mode_manager.get_current_script_info()))

        if (do_reload):  # Reload is used to prevent a bug in PyPlanet/Trackmania where the mode settings are not applied
            self.reload_maplist = maplist
