# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# [START app]
import logging

from flask import Flask
from flask import request
from flask import redirect
from flask import render_template
from flask import jsonify
from flask import session
from flask import Response
app = Flask(__name__)
import os, binascii
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
from model.DBModel import GamesModel
from model.DBModel import GamesProgress
from model.DBModel import PlayerModel
import json
import base64
import re
import logging


@app.route('/')
def hello():

	signedIn = False
	#check if signed in
	if 'sign_in_name' in session.keys():
		if 'token' in session.keys():
			query = PlayerModel.query(PlayerModel.name == session['sign_in_name'],PlayerModel.token == session['token']).get()
			if query is None:
				logging.debug("pm not found")
				signedIn = False;
			else:
				session['admin'] = query.admin
				signedIn = True;
				logging.debug("pm found")
		
	qgamelist = GamesModel.query()
	gamelist = list()
	for qgame in qgamelist:
		game = {}
		game['hint'] = qgame.hint
		game['word_length'] = qgame.word_length
		game['game_id'] = qgame.key.id()
		gamelist.append(game)
	if not signedIn:
		return render_template('main.html',signed_in = signedIn)
	else:
		return render_template('main.html',signed_in = signedIn,sign_in_name = session['sign_in_name'],game_list = gamelist )

def createToken():
	
	hashed = request.headers.get('Authorization')
	token = binascii.b2a_hex(os.urandom(20))
	#store into database
	session['token'] = str(token)
	return str(token)

@app.route('/token', methods=['POST','GET'])
def AccessToken():
	
	if request.method == 'POST':
		#getting data from headers
		session['sign_in_name'] = request.authorization.username
		password = request.authorization.password
		pmQuery = PlayerModel.query(PlayerModel.name == user)
		pm = pmQuery.get()
		if pm is not None:
			return Response('User Already Existing', 409, { 'error' : 'Conflicting user id' } )		
		token = createToken()
		#create the playermodel
		pmodel = PlayerModel()
		pmodel.name = session['sign_in_name']
		pmodel.pw = password
		pmodel.games_created = 0
		pmodel.games_played = 0
		pmodel.wins = 0
		pmodel.lose = 0
		pmodel.token = token
		pmodel.admin = False
		pmodel.commit()
		data = {'token': session['token']}
		session['signed_in'] = True
		return json.dumps(data)
	elif request.method == 'GET':
		#getting data from headers
		user = request.authorization.username
		pw = request.authorization.password
		#query for the account
		pmQuery = PlayerModel.query(PlayerModel.name == user,PlayerModel.pw == pw)
		pm = pmQuery.get()
		if pm is None:
			#return render_template('404.html'), 404
			return Response('User not found', 404, { 'error' : 'User not found' })
		else:
			logging.debug("logged in")
			#set store token into session
			session['signed_in'] = True
			session['sign_in_name'] = user
			session['token'] = pm.token
			#return as json
			data = {'token': session['token']}
			return json.dumps(data)
	else:
		return Response('Method not allowed', 405, {'error': 'Method not allowed'})
		
@app.route('/games' ,methods = ['GET','POST','DELETE'])
def games():
	if request.method == 'GET':
		#declare wordlen is type int()
		wordlen = int()
		#get from headers
		wordlen = request.form['word_length']
		if wordlen is None:
			return GamesModel.query().fetch()
		else:
			return GamesModel.queryByLength(wordlen)
	elif request.method == 'POST':
		#update the game created count
		pm = PlayerModel.GetUser(session['sign_in_name'],session['token'])
		pm.games_created +=1
		pm.put()
		#post
		gamedata= json.loads(request.data)
		gm = GamesModel(word = gamedata['word'],hint=gamedata['hint'],word_length = len(gamedata['word']),solved = 0,failed = 0)
		id = gm.put().id()
		#unique token by using the id created by ndb
		gamedata.update({'game_id':str(id)})
		return json.dumps(gamedata)
	elif request.method =='DELETE':
		if session['admin'] == True:
			GamesModel.deleteAll()
			return ""
		else:
			return redirect("/",code = 302)
@app.route('/games/<int:id>' ,methods = ['GET','DELETE'])
def GoGame(id):
	intid = int(id)
	d = GamesModel.get_by_id(intid)
	if d is not None:
		if request.method == 'GET':
			#go into the game
			game = {"hint" : d.hint,"word_length":d.word_length,"game_id":intid}
			json.dumps(game)
			return render_template('game.html',game_property = game)
		elif request.method == 'DELETE':
			#delete one game
			d.delete()
	return ""
	
@app.route('/games/check_letter/<int:id>' ,methods = ['POST'])
def checkLetter(id):
	guess = request.get_json()["guess"]
	if guess == "":
		q = GamesProgress.GetRoom(id,session['sign_in_name'])
		game = GamesModel.get_by_id(id)
		if q is None:
			gameprogress = GamesProgress(roomID = id,bad_guesses = 0,username = session['sign_in_name'],word_progress ='_'*game.word_length)
			gameprogress.put()
			pm = PlayerModel.query(PlayerModel.name == session['sign_in_name'],PlayerModel.token == session['token']).get()
			pm.games_played +=1
			pm.put()
			content = {"game_state" :"ONGOING","word_state":'_'*game.word_length,"bad_guesses":0}
			return json.dumps(content)
	
		
		if game.word == q.word_progress:
			content = {"game_state" :"WIN","word_state":q.word_progress}
			return json.dumps(content)
		elif q.bad_guesses < 8:
			content = {"game_state" :"ONGOING","word_state":q.word_progress,"bad_guesses":q.bad_guesses}
			return json.dumps(content)
		else:
			content = {"game_state" :"LOSE","word_state":q.word_progress,"answer":game.word}
			return json.dumps(content)
	else:
		return IfLetterExist(guess,id)
def IfLetterExist(character, id):
	if not character.isalpha() :
		if len(character) is not 1:
			return Response("error", 400, { "error" :  "Bad request, malformed data" } )
	
	
	q = GamesProgress.query(GamesProgress.roomID == id,GamesProgress.username == session['sign_in_name']).get()
	game = GamesModel.get_by_id(id)
	count = 0
	wordprogress = list(q.word_progress)
	contains = False
	Word = list(game.word.upper())
	for letter in range(game.word_length):
		if Word[count] == character:
			contains = True
			wordprogress[count] = character
		count+=1
	if contains ==False:
		q.bad_guesses +=1
	q.word_progress = "".join(wordprogress)   
	
	if game.word.upper() == q.word_progress:
		content = {"game_state" :"WIN","word_state":q.word_progress}
		game.solved +=1
		# update player wins
		pm = PlayerModel.query(PlayerModel.name == session['sign_in_name'],PlayerModel.token == session['token']).get()
		pm.wins +=1
		
		#go into the db
		pm.put()
		game.put()
		q.put()
		
		return json.dumps(content)
	elif q.bad_guesses < 8:
		content = {"game_state" :"ONGOING","word_state":q.word_progress,"bad_guesses":q.bad_guesses}
		q.put()
		return json.dumps(content)
	else:
		content = {"game_state" :"LOSE","word_state":q.word_progress,"answer":game.word}
		game.failed +=1
		#update player lose
		pm = PlayerModel.query(PlayerModel.name == session['sign_in_name'],PlayerModel.token == session['token']).get()
		pm.lose +=1
		
		#into the db
		game.put()
		q.put()
		pm.put()
		return json.dumps(content)


@app.route('/admin' ,methods = ['GET'])
def adminStats():
	if 'admin' not in session.keys():
		return Response('error : You do not have permission to perorm this operation', 403, {'error':'You do not have permission to perorm this operation'})
	if session['admin'] == False:
		return Response('error : You do not have permission to perorm this operation', 403, {'error':'You do not have permission to perorm this operation'})
	else:
		return render_template("admin.html")


@app.route('/admin/players',methods = ['GET'])
def adminPlayers():
	sortby = request.args.get('sortby')
	order = request.args.get('order')
	query = list()
	if sortby == 'wins':
		if order == 'asc':
			query = PlayerModel.query().order(PlayerModel.wins).fetch()
		elif order == 'desc':
			query = PlayerModel.query().order(-PlayerModel.wins).fetch()
	elif sortby == 'losses':
		if order == 'asc':
			query = PlayerModel.query().order(PlayerModel.lose).fetch()
		elif order == 'desc':
			query = PlayerModel.query().order(-PlayerModel.lose).fetch()
	elif sortby == 'alphabetical':
		if order == 'asc':
			query = PlayerModel.query().order(PlayerModel.name).fetch()
		elif order == 'desc':
			query = PlayerModel.query().order(-PlayerModel.name).fetch()
	
	#prepare data for json dumps
	jsonList = list()
	for pm in query:
		data ={"name":pm.name,"games_created":pm.games_created,"games_played":pm.games_played,"games_won":pm.wins,"games_lost":pm.lose}
		jsonList.append(data)
	return json.dumps(jsonList)

	
@app.route('/admin/words',methods = ['GET'])
def adminWords():
	sortby = request.args.get('sortby')
	order = request.args.get('order')
	query = list()
	if sortby == 'solved':
		if order == 'asc':
			query = GamesModel.query().order(GamesModel.solved).fetch()
		elif order == 'desc':
			query = GamesModel.query().order(-GamesModel.solved).fetch()
	elif sortby == 'length':
		if order == 'asc':
			query = GamesModel.query().order(GamesModel.word_length).fetch()
		elif order == 'desc':
			query = GamesModel.query().order(-GamesModel.word_length).fetch()
	elif sortby == 'alphabetical':
		if order == 'asc':
			query = GamesModel.query().order(GamesModel.word).fetch()
		elif order == 'desc':
			query = GamesModel.query().order(-GamesModel.word).fetch()
	
	#prepare data for json dumps
	jsonList = list()
	for gm in query:
		data ={"word":gm.word,"wins":gm.solved,"losses":gm.failed}
		jsonList.append(data)
	return json.dumps(jsonList)

@app.errorhandler(500)
def server_error500(e):
    # Log the error and stacktrace.
    logging.exception('Error 500: Server Crash, An error occurred during a request.')
    #return redirect('/', code = 302)
    return 'An internal error occurred.', 500

@app.errorhandler(400)
def server_error400(e):
    # Log the error and stacktrace.
    logging.exception('Error 400 : Bad Request,An error occurred during a request.')
    #return redirect('/', code = 302)
    return 'An internal error occurred.', 400

@app.errorhandler(403)
def server_error403(e):
    # Log the error and stacktrace.
    logging.exception('Error 403 : Forbidden,An error occurred during a request.')
    #return redirect('/', code = 302)
    return 'An internal error occurred.', 403

@app.errorhandler(404)
def server_error404(e):
    # Log the error and stacktrace.
    logging.exception('Error 404 Not Found,An error occurred during a request.')
    #return redirect('/', code = 302)
    return 'user not found', 404

@app.errorhandler(405)
def server_error405(e):
    # Log the error and stacktrace.
    logging.exception('Error 405 Method Not Allow, An error occurred during a request.')
    #return redirect('/', code = 302)
    return 'An internal error occurred.', 405
# [END app]
