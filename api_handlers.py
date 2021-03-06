from flask.ext.sqlalchemy import SQLAlchemy 
from sqlalchemy import or_, and_
from models import Player, Team, Game
import json
import datetime

# Purposely avoiding pulling in Flask modules here
# in order to maintain some separation of concern

# -------------------
# Collection Handlers
# -------------------

def players_collection_handler(a):
    """
    Eventually we need to modify this to handle 
    Tuple rangers for numerical data sets.
    """
    return json.dumps([i.serialize for i in Player.query.filter_by(**a).all()])

def teams_collection_handler(a):
    return json.dumps([i.serialize for i in Team.query.filter_by(**a).all()])

def games_collection_handler(a):
    return json.dumps([i.serialize for i in Game.query.filter_by(**a).all()])

# ----------------
# Player Endpoints
# ----------------

def player_view_by_id_handler(id):
    data = Player.query.filter_by(id = id).first().serialize
    data["schedule"] = sorted(json.loads(team_schedule_handler(data["team_name"])), key=lambda k : k["date"], reverse=True)
    data["google_maps"] = Team.query.filter_by(name = data["team_name"]).first().google_maps
    return json.dumps(data)
    
def player_by_id_handler(id):
    return json.dumps(Player.query.filter_by(id = id).first().serialize)

# --------------
# Team Endpoints
# --------------

def team_view_by_name_handler(tn):
    data = Team.query.filter_by(name = tn).first().serialize
    data["schedule"] = sorted(json.loads(team_schedule_handler(tn)), key=lambda k : k["date"], reverse=True)
    data["players"] = sorted(data["players"], key=lambda k : k["name"])
    return json.dumps(data)

def team_by_name_handler(tn):
    data = Team.query.filter_by(name = tn).first().serialize
    return json.dumps(data)

def team_schedule_handler(tn):
    return json.dumps([i.serialize for i in Game.query.filter(or_(Game.home_team == tn, Game.away_team == tn)).all()])

def team_top_starters_handler(tn):
    data = [i.serialize for i in Player.query.filter_by(team_name = tn).all()]
    data = sorted(data, key= lambda k: k['season_GS'], reverse=True)
    return json.dumps(data[:5])

def team_wins_handler(tn):
    return json.dumps([i.serialize for i in Game.query.filter(or_(and_(Game.home_team == tn, Game.home_score > Game.away_score), \
                                                                 (and_(Game.away_team == tn, Game.away_score > Game.home_score)))).all()])

def team_losses_handler(tn):
    return json.dumps([i.serialize for i in Game.query.filter(or_(and_(Game.home_team == tn, Game.home_score < Game.away_score), \
                                                                 (and_(Game.away_team == tn, Game.away_score < Game.home_score)))).all()])
# --------------
# Game Endpoints
# --------------

def game_view_by_id_handler(id):
    data = Game.query.filter_by(id = id).first().serialize
    home_team_obj = Team.query.filter_by(name = data["home_team"]).first()
    away_team_obj = Team.query.filter_by(name = data["away_team"]).first()
    data["citation"] = { "home" : home_team_obj.citation, "away" : away_team_obj.citation}
    data["roster"] = { "home" : sorted([i.serialize for i in home_team_obj.players], key= lambda k: k['name']), "away" : sorted([i.serialize for i in away_team_obj.players], key= lambda k: k['name'])}
    data["google_maps"] = home_team_obj.google_maps
    return json.dumps(data)

def game_by_id_handler(id):
    return json.dumps(Game.query.filter_by(id = id).first().serialize)

def game_by_month_handler(month_id):
    # This is probably a bad way to do this, I'm loading up ALL
    # games and then searching through because I have to reformat the 
    # date with the datetime object before I can compare against the 
    # month ID. Unfortunately I don't think there is a way to refine 
    # the query with this comparison since processing is needed on 
    # each object before the predicate can be evaluated, hence 
    # each object must be pulled from the database.
    games = Game.query
    games = filter(lambda g, m = month_id: datetime.datetime.fromtimestamp(int(g.date)).month == int(m), games)
    games = sorted(games, key=lambda g: g.date)
    return json.dumps([i.serialize for i in games])


def game_by_site_handler(site):
    site_team = Team.query.filter_by(site_name = site).first()
    return json.dumps([i.serialize for i in Game.query.filter_by(home_team = site_team.name).all()])

# --------------
# Search Handler
# --------------
def contains(l, f):
    for x in l:
        if f(x):
            return True
    return False

def search_by_query(query):
    print("Hitting Search Query: " + query)
    team_data = []
    player_data = []
    game_data = []

    search_items = [query] + query.split()
    for item in search_items:
        teams_result   = Team.query.search(item)
        games_result   = Game.query.search(item)
        players_result = Player.query.search(item)

        #For each player, populate team and games 
        #only if they are not already populated.
        for p in players_result:
            if not contains(player_data, lambda x: x.id == p.id):
                # if the player object has already been added then
                # we don't need to grab related data.
                player_data.append(p)
#                td = Team.query.filter_by(name = p.team_name).first()
#                if not contains(team_data, lambda x: x.name == td.name):
#                    team_data.append(td)
#                gs = Game.query.filter(or_(Game.home_team == p.team_name, Game.away_team == p.team_name))
#                for g in gs:
#                    if not contains(game_data, lambda x: x.id == g.id):
#                        game_data.append(g)

        
        #For each team populate players and game as well
        for t in teams_result:
            if not contains(team_data, lambda x: x.name == t.name):
                # if the team object has already been added then 
                # so has the data related to that team object.
                team_data.append(t)
#                ps = t.players
#                for p in ps:
#                    if not contains(player_data, lambda x: x.id == p.id):
#                        player_data.append(p)
# 
#                gs = Game.query.filter(or_(Game.home_team == t.name, Game.away_team == t.name))
#                for g in gs:
#                    if not contains(game_data, lambda x: x.id == g.id):
#                        game_data.append(g)
        
        #For each game populate the teams (home and away) and 
        #players for each team
        for g in games_result:
            if not contains(game_data, lambda x: x.id == g.id):
                game_data.append(g)
#                ht = Team.query.filter_by(name = g.home_team).first()
#                at = Team.query.filter_by(name = g.away_team).first()
#                if not contains(team_data, lambda x: x.name == ht.name):
#                    team_data.append(ht)
#                    ps = ht.players
#                    for p in ps:
#                        if not contains(player_data, lambda x: x.id == p.id):
#                            player_data.append(p)
#                if not contains(team_data, lambda x: x.name == at.name):
#                    team_data.append(at)
#                    ps = at.players
#                    for p in ps:
#                        if not contains(player_data, lambda x: x.id == p.id):
#                            player_data.append(p)

    data = { 'results': {
                'teams'   : [i.serialize for i in team_data],
                'games'   : [i.serialize for i in game_data],
                'players' : [i.serialize for i in player_data]
                }
            }
    
    find_matched_keys(search_items, teams_result, data, "teams", "name", ('city', 'conference', 'division', 'mascot', 'site_name', 'state', 'twitter'))
    find_matched_keys(search_items, games_result, data, "games", "id",  ('away_score', 'away_team', 'date_string', 'home_score', 'home_team', 'id')) 
    find_matched_keys(search_items, players_result, data, "players", "id", ('age', 'current_team', 'id', 'player_number', 'position', 'twitter', 'weight'))

    return json.dumps(data);

def find_matched_keys(search_items, items_result, data, items_name_str, primary_identifier_str, attributes_of_interest):
    # temp object for matched values
    matched_keywords = {}

    #iterate through the items we found based on the query
    for i in items_result :
        # quick reference variable
        item_obj = None
        # organize results based on primary identifier
        if (primary_identifier_str == "id") :
            matched_keywords[i.id] = {}
            item_obj = matched_keywords[i.id]
        else : # identifier is names
            matched_keywords[i.name] = {}
            item_obj = matched_keywords[i.name]
        # iterate through attributes within search result vector
        for a in dir(i) :
            print(a, getattr(i, a))
            # only care about the following attributes
            if a.startswith(attributes_of_interest) :
                #check each search_item against the returned values for each attribute
                for s in search_items :
                    attr_val = getattr(i, a)
                    if ((type(attr_val) == int) and (attr_val == s) and not a in item_obj) :
                        item_obj[a] = attr_val
                    # check to see if search_item is contained within result; if so, add it to our object
                    elif (not(type(attr_val) == int) and (s.lower() in attr_val.lower()) and not a in item_obj) :
                        # We only care if we don't have this key's value sored yet, otherwise it's more than likely a duplicate
                        item_obj[a] = attr_val

    #iterate through the items in our results array to find where to put the matched_keywords
    for i in data["results"][items_name_str] :
        # store each object of matched_keywords with respective data objects
        if (i[primary_identifier_str] in matched_keywords) :
            i["matched_keywords"] = matched_keywords[i[primary_identifier_str]]
