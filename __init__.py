import asyncio

from pyplanet.apps.config import AppConfig
from pyplanet.contrib.command import Command
from pyplanet.apps.core.maniaplanet import callbacks as mp_signals
from pyplanet.apps.core.trackmania import callbacks as tm_signals
from pyplanet.contrib.setting import Setting
from datetime import datetime

class TournementSchedule(AppConfig):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.queueStart = False
		self.live = False
		self.queueFinish = False

	async def on_start(self):
		# Settings
		await self.context.setting.register(
			Setting('tournament_map_list', 'Map list to use for tournament', Setting.CAT_OTHER, type=str, default='tournament.txt', description='Map list to use for tournament'),
			Setting('normal_map_list', 'Map list to return to after tournament', Setting.CAT_OTHER, type=str, default='maplist.txt', description='Map list to return to after tournament'),
		)

		# Perms
		await self.instance.permission_manager.register('tournament', 'Handles server', app=self, min_level=2)

		# Commands
		await self.instance.command_manager.register(Command(command='starttournament', target=self.command_start_tournament, perms='tournamentschedule:tournament', admin=True, description='Starts competitive match'))
		await self.instance.command_manager.register(Command(command='endtournament', target=self.command_end_tournament, perms='tournamentschedule:tournament', admin=True, description='Starts competitive match'))

		# Signals
		self.context.signals.listen(mp_signals.map.map_begin, self.map_begin)
		self.context.signals.listen(tm_signals.scores, self.scores)

	async def command_start_tournament(self, player, data, **kwargs):
		await self.start_tournament()

	async def start_tournament(self):
		tournament_map_list = await self.get_map_list('tournament_map_list')

		await asyncio.gather(
			self.instance.chat('Starting tournament now!'),
			#self.instance.mode_manager.set_next_script("Trackmania/TM_Cup_Online.Script.txt"),
			self.instance.map_manager.load_matchsettings(tournament_map_list),
			self.instance.gbx('NextMap'),
		)

		self.queueStart = True

		await self.instance.map_manager.update_list(full_update=True),

	async def command_end_tournament(self, player, data, **kwargs):
		await self.end_tournament()

	async def map_begin(self, map):
		if (self.queueStart):
			self.live = True
			self.queueStart = False

		if (self.queueFinish):
			self.end_tournament()


	async def end_tournament(self):
		normal_map_list = await self.get_map_list('normal_map_list')

		await self.instance.chat('Tournament over now!'),
		#await self.instance.mode_manager.set_next_script("Trackmania/TM_TimeAttack_Online.Script.txt"),

		self.live = False
		await self.instance.map_manager.load_matchsettings(normal_map_list),
		await self.instance.map_manager.update_list(full_update=True)

		await self.instance.gbx.multicall(
			self.instance.gbx('NextMap'),
		)

	async def scores(self, players, teams, winner_team, use_teams, winner_player, section, **kwargs):
		# Section: PreEndRound, EndRound, EndMap, EndMatch
		# Player: matchpoints is equal to score limit when they are
		# finalist, and higher than score limit when they are finished. If the previous is not true (not sure right now),
		# then we can also use winner_player to figure out whether a player has won the game, but I am also unsure
		# about that


		#if (section == 'EndRound'):
			#await self.instance.chat(players[0]['matchpoints'])
			#await self.instance.chat("Winner player: " + winner_player + " (is empty: " + winner_player == '' + ")")

		if (not self.live or section != 'EndMatch'):
			return

		#await self.instance.chat(winner_player)
		self.queueFinish = True

	async def handle_scores(self, players):
		self.current_rankings = []
		self.current_finishes = []

		current_script = (await self.instance.mode_manager.get_current_script()).lower()
		if 'timeattack' in current_script:
			for player in players:
				if 'best_race_time' in player:
					if player['best_race_time'] != -1:
						new_ranking = dict(login=player['player'].login, nickname=player['player'].nickname,
										   score=player['best_race_time'])
						self.current_rankings.append(new_ranking)
				elif 'bestracetime' in player:
					if player['bestracetime'] != -1:
						new_ranking = dict(login=player['login'], nickname=player['name'],
										   score=player['bestracetime'])
						self.current_rankings.append(new_ranking)

			self.current_rankings.sort(key=lambda x: x['score'])
		elif 'rounds' in current_script or 'team' in current_script or 'cup' in current_script:
			for player in players:
				if 'map_points' in player:
					if player['map_points'] != -1:
						new_ranking = dict(login=player['player'].login, nickname=player['player'].nickname,
										   score=player['map_points'], points_added=0)
						self.current_rankings.append(new_ranking)
				elif 'mappoints' in player:
					if player['mappoints'] != -1:
						new_ranking = dict(login=player['login'], nickname=player['name'],
										   score=player['mappoints'], points_added=0)
						self.current_rankings.append(new_ranking)

			self.current_rankings.sort(key=lambda x: x['score'])
			self.current_rankings.reverse()

	async def get_map_list(self, setting):
		map_list_setting = await self.instance.setting_manager.get_setting('tournamentschedule', setting)
		map_list = 'MatchSettings/' + await map_list_setting.get_value()

		return map_list