

from google.appengine.api import memcache
from google.appengine.api import mail
from google.appengine.api import urlfetch
from google.appengine.ext import ndb

class PlayerModel(ndb.Model):
	name = ndb.StringProperty()
	pw = ndb.StringProperty()
	games_created = ndb.IntegerProperty()
	games_played = ndb.IntegerProperty()
	wins = ndb.IntegerProperty()
	lose = ndb.IntegerProperty()
	token = ndb.StringProperty()
	admin = ndb.BooleanProperty()
	def commit(self):
		return self.put()
	@classmethod
	def GetUser(cls,name,token):
		q1 = PlayerModel.query()
		q2 = q1.filter(PlayerModel.name == name)
		q3 = q2.filter(PlayerModel.token == token)
		return q3.get()
	
	
class GamesModel(ndb.Model):
	word = ndb.StringProperty()
	hint = ndb.StringProperty()
	word_length = ndb.IntegerProperty()
	solved = ndb.IntegerProperty()
	failed = ndb.IntegerProperty()
	@classmethod
	def queryByLength(cls,word_length):
		query = GamesModel.query(GamesModel.word_length == word_length)
		return query
	@classmethod
	def queryBykey(cls,passedIn):
		query = GamesModel.query(GamesModel.key == passedIn)
		return query
	def delete(self):
		self.key.delete()
		return ""
	@classmethod
	def deleteAll(cls):
		ndb.delete_multi(GamesModel.query().fetch(keys_only = True))
		return ""
	def commit(self):
		return self.put()
		

		
class GamesProgress(ndb.Model):
	roomID = ndb.IntegerProperty()
	word_progress = ndb.StringProperty()
	username = ndb.StringProperty()
	bad_guesses = ndb.IntegerProperty()
	
	@classmethod
	def GetRoom(cls,id,name):
		q1 = GamesProgress.query()
		q2 = q1.filter(GamesProgress.roomID == int(id))
		q3 = q2.filter(GamesProgress.username == str(name))
		return q3.get()
	
	def delete(self):
		self.key.delete()
		return ""