from lightfm.data import Dataset
from json import JSONDecodeError
import numpy as np
import pandas as pd
from gensim.models.keyedvectors import KeyedVectors
import pickle
import steam.webauth as wa
from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import JsonResponse
from scipy import sparse
from lightfm import LightFM
import requests
from requests.exceptions import RequestException
import os

# TODO: THIS SHOULD PROBABLY GET MOVED TO A FILE LIKE UTILS.PY

# Returns the json of the user's steam library if successful
# Else returns an empty dictionary
def get_user_library(steamid):
    key = None
    with open('api/key.txt', 'r') as f:
        key = f.read()

    url = f'http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={key}&steamid={steamid}&format=json&include_free_played_games=1'
    page = requests.get(url)
    usrdata = page.json()
    
    return usrdata['response']['games']

def load_games_dict():
    with open('api/games_dict.pickle', 'rb') as f:
        return pickle.load(f)

def load_existing_data(games_dict, path):
    recdata = pd.read_csv(path, index_col=0)
    recdata = recdata.rename(columns = {'variable': 'id', 'value': 'owned'})
    recdata = recdata[recdata['id'].isin(map(int, games_dict.keys()))]
    return recdata

def load_user_data(uid, games_dict, lib):
    df_data = [(uid, x['appid'], 1.0) for x in lib]
    df = pd.DataFrame(data=df_data, columns=['uid', 'id', 'owned'])
    df = df[df['id'].isin(map(int, games_dict.keys()))]
    return df

def create_interaction_matrix(df, user_col, item_col, rating_col, norm=False, threshold=None):
    interactions = df.groupby([user_col, item_col])[rating_col].sum().unstack().reset_index().fillna(0).set_index(user_col)
    if norm:
        interactions = interactions.applymap(lambda x : 1 if x > threshold else 0)
    return interactions

def run_model(interactions, n_components, loss, epoch, n_jobs):
    x = sparse.csr_matrix(interactions.values)
    model = LightFM(no_components=n_components, loss=loss)
    model.fit(x, epochs=epoch, num_threads=n_jobs)
    return model

def create_user_dict(interactions):
    user_id = list(interactions.index)
    user_dict = {}
    counter = 0
    for i in user_id:
        user_dict[i] = counter
        counter += 1
    return user_dict

def generate_uid():
    return 3183

def get_recs(model, interactions, user_id, user_dict, 
                               item_dict,threshold = 0,num_items = 10, show_known = True, show_recs = True):
    # FIXME: FOR NEW USERS WE NEED TO ADD THEM TO THE INTERACTION MATRIX TO GET THEIR RECOMMENDATIONS
    '''
    Produces user recommendations
    Arguments:
        model = Trained matrix factorization model
        interactions = dataset used for training the model
        user_id = user ID for which we need to generate recommendation
        user_dict = Dictionary containing interaction_index as key and user_id as value
        item_dict = Dictionary containing item_id as key and item_name as value
        threshold = value above which the rating is favorable in new interaction matrix
        num_items = Number of recommendations to provide
        show_known (optional) - if True, prints known positives
        show_recs (optional) - if True, prints list of N recommended items  which user hopefully will be interested in
    Returns:
        list of titles user_id is predicted to be interested in 
    '''
    n_users, n_items = interactions.shape
    # Get value for user_id using dictionary
    user_x = user_dict[user_id]
    # Generate predictions
    scores = pd.Series(model.predict(user_x,np.arange(n_items)))
    # Get top predictions
    scores.index = interactions.columns
    scores = list(pd.Series(scores.sort_values(ascending=False).index))
    # Get list of known values
    known_items = list(pd.Series(interactions.loc[user_id,:] \
                                 [interactions.loc[user_id,:] > threshold].index).sort_values(ascending=False))
    # Ensure predictions are not already known
    scores = [x for x in scores if x not in known_items]
    # Take required number of items from prediction list
    return_score_list = scores[0:num_items]
    # Convert from item id to item name using item_dict
    known_items = list(pd.Series(known_items).apply(lambda x: item_dict[str(x)]))
    scores = list(pd.Series(return_score_list).apply(lambda x: item_dict[str(x)]))
    
    if show_known == True:
        print("Known Likes:")
        counter = 1
        for i in known_items:
            print(str(counter) + '- ' + i)
            counter+=1
            
    if show_recs == True:
        print("\n Recommended Items:")
        counter = 1
        for i in scores:
            print(str(counter) + '- ' + i)
            counter+=1
    return scores

def get_user_recs(steamid):
    # TODO: FIGURE OUT HOW TO DO THIS WITHOUT LIGHTFM, BECAUSE IT IS CRAP AND FORCED
    #       YOU TO RETRAIN THE MODEL TO MAKE A PREDICTION ABOUT A USER NOT IN THE TRAINING SET
    #       ALSO TRY DOING THE INTERACTIONS MATRIX WITH EMPTY ENTRIES AND FILLING THEM IN LATER
    # Get the user library
    print('getting usr lib')
    lib = None
    try:
        err = None
        lib = get_user_library(steamid)
    except FileNotFoundError:
        err = {'Error': 'Unable to locate API key'}
    except KeyError:
        err = {'Error': 'API call did not return a response'}
    except JSONDecodeError:
        err = {'Error': 'API call did not return in JSON format'}
    except RequestException as e:
        err = {'Error': e.strerror}
    finally:
        if err:
            print(err)
            return Response(err, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Load some prerequisite data from disk
    games_dict = None
    try:
        err = None
        games_dict = load_games_dict()
    except FileNotFoundError:
        err = {'Error': 'Could not locate games list'}        
    except pickle.UnpicklingError:
        err = {'Error': 'Could not load games list'}
    finally:
        if err:
            print(err)
            return Response(err, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    existing_data = None
    try:
        existing_data = load_existing_data(games_dict, 'api/recdata_new.csv')
    except Exception as e:
        print(e)
        return Response({'Error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # TODO: GET THE UID FROM LAST LINE OF INTERACTIONS OR CHANGE IT TO BE THE STEAMID
    uid = generate_uid()

    # Convert lib to pandas dataframe
    new_data = None
    try:
        new_data = load_user_data(uid, games_dict, lib)
    except Exception as e:
        print(e)
        return Response({'Error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

   
    dataset = None
    my_items = None
    solver = None
    
    try:
        print('fitting dataset')
        # Fit dataset on training data and on the new user data
        dataset = Dataset()
        my_items = existing_data['id'].unique()

        dataset.fit(users=np.concatenate((existing_data['uid'].unique(), [uid])), items=my_items)
        train_interactions, train_weights = dataset.build_interactions([(x,y) for x,y,z in existing_data.to_numpy()])
        dataset.fit_partial(users=new_data['uid'].unique(), items=my_items)
        new_interactions, new_weights = dataset.build_interactions([(x,y) for x,y,z in new_data.to_numpy()])

        print('fitting model')
        # Train the model on the training data and then add the new user data on top of it
        solver = LightFM(no_components=30, loss='warp')

        solver.fit(interactions=train_interactions, sample_weight=train_weights)
        solver.fit_partial(interactions=new_interactions, sample_weight=new_weights)
    except Exception as e:
        # NOTE: LIGHTFM DOCS ARE CRAP ABT WHAT ERRORS CAN BE THROWN SO THIS IS A CRAPSHOOT
        print(e)
        return Response({'Error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    embeddings = solver.item_embeddings

    # FIXME: THIS SHOULD BE GENERATED AT RUNTIME TO HANDLE NEW ENTRIES
    vector = None
    with open('api/vector.pickle', 'rb') as f:
        vector = pickle.load(f)

    # FIXME: MAKE A REAL USER DICT
    user_dict = {x: x for x in range(3184)}

    print('making predictions')
    try:
        n_users, n_items = train_interactions.shape
        scores = pd.Series(solver.predict(uid, np.arange(n_items)))
        scores.index = my_items
        scores = list(pd.Series(scores.sort_values(ascending=False).index))
        return_score_list = scores[:5]
        scores = list(pd.Series(return_score_list).apply(lambda x: games_dict[str(x)]))
    except Exception as e:
        print(e)
        return Response({'Error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return JsonResponse({'games': scores}, status=status.HTTP_200_OK)

# Create your views here.
class LoginView(APIView):
    def post(self, request, format=None):
        session = self.request.session

        if not session.exists(session.session_key):
            session.create()

        username = request.data.get('username')
        pwd = request.data.get('pwd')
        two_factor = request.data.get('twoFactorAuth')

        if username and pwd:
            # TODO: ERROR HANDLING
            usr = wa.WebAuth(username)
            usr.login(pwd, twofactor_code=two_factor)
            steamid = usr.steam_id
        else:
            # FIXME: MAYBE THIS SHOULD BE A JSON RESPOSNE
            return Response({'Bad Request': 'Incomplete fields'}, status=status.HTTP_400_BAD_REQUEST)

        return get_user_recs(steamid)

class ValidateView(APIView):
    def post(self, request, format=None):
        session = self.request.session

        if not session.exists(session.session_key):
            session.create()

        steamid = request.data.get('steamID')
        if self.valid(steamid):
            return get_user_recs(steamid)
        else:
            return Response({'Bad Request': 'Invalid ID'}, status=status.HTTP_400_BAD_REQUEST)

    def valid(self, steamID):
        # FIXME: THE PROFILE NOT FOUND PAGE STILL RETURNS A 200 SO THIS DOESN'T WORK
        return requests.get(f'https://steamcommunity.com/profiles/{steamID}').status_code == 200 
        
