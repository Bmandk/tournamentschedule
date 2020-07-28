from peewee import *
from pyplanet.core.db import TimedModel
from pyplanet.apps.core.maniaplanet.models import Map, Player

class TournamentSchedule(TimedModel):
	name = TextField(default='Empty Tournament')
	"""
	The name of the tournament.
	"""

	format = TextField(null=True)
	"""
	Free text field for the format of the tournament.
	"""

	maplist = TextField(null=False, default='maplist.txt')
	"""
	Maplist to use for settings and maps.
	"""

	start_time = TimeField()
	"""
	The time the tournament should start
	"""

	mon = BooleanField(default=False)
	"""
	Play tournament on monday.
	"""

	tue = BooleanField(default=False)
	"""
	Play tournament on tuesday.
	"""

	wed = BooleanField(default=False)
	"""
	Play tournament on wednesday.
	"""

	thu = BooleanField(default=False)
	"""
	Play tournament on thursday.
	"""

	fri = BooleanField(default=False)
	"""
	Play tournament on friday.
	"""

	sat = BooleanField(default=False)
	"""
	Play tournament on saturday.
	"""

	sun = BooleanField(default=False)
	"""
	Play tournament on sunday.
	"""