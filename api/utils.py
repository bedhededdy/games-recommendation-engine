import pickle
from json import JSONDecodeError

import requests
from requests.exceptions import RequestException
import pandas as pd
import numpy as np
from lightfm import LightFM
from lightfm.data import Dataset
from rest_framework import status
from rest_framework.response import Response
from django.http import JsonResponse

def get_user_library(steamid):
    '''Retrieves the list of games in a user's steam library
    
    Parameters
    ----------
    steamid : str
        The steamid of the user

    Returns
    -------
    list of dict
        A list of dictionaries that represents the games in the user's library

    Raises
    ------
    FileNotFoundError
        Steam API key was not found on disk
    KeyError
        API call did not return a response or returned an empty response
    JSONDecodeError
        An invalid steamid was passed to the function
    RequestException
        An error occurred while making the HTTP request to the API
    '''
    # Load our Steam API key
    key = None
    with open('api/key.txt', 'r') as f:
        key = f.read()

    # Call API to get user's Steam library as JSON
    url = f'http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={key}&steamid={steamid}&format=json&include_free_played_games=1'
    page = requests.get(url)
    usrdata = page.json()
    
    # Return the games list from the API response
    return usrdata['response']['games']

def load_games_dict():
    '''Loads the mappings of appids to game names from disk
    
    Parameters
    ----------
    None

    Returns
    -------
    dict of str to str
        A dictionary that maps the string representation of a game's appid to it's name

    Raises
    ------
    FileNotFoundError
        games_dict.pickle was not found
    pickle.UnpicklingError
        games_dict.pickle was unable to be unpickled
    '''
    with open('api/games_dict.pickle', 'rb') as f:
        return pickle.load(f)

def load_existing_data(games_dict, path):
    '''Loads existing data about which games are owned by which users
    
    Parameters
    ----------
    games_dict : dict of str to str
        A dictionary that contains a mapping of a game's appid to it's name
    path : str
        A path to the CSV file containing the existing data about what users own what games
        
    Returns
    -------
    pandas.DataFrame
        A pandas DataFrame with each row containing a user id and an appid of a game owned by the user
    
    Raises
    ------
    Exception
        One of many errors occurred in attempting to load the data into the DataFrame
    '''
    # Load the data and filter out rows where the appid is not in our games_dict
    recdata = pd.read_csv(path, index_col=0)
    recdata = recdata.rename(columns = {'variable': 'id', 'value': 'owned'})
    recdata = recdata[recdata['id'].isin(map(int, games_dict.keys()))]
    return recdata

def load_user_data(uid, games_dict, lib):
    '''Creates a DataFrame that contains what games the user who clicked login owns
    
    Parameters
    ----------
    uid : int
        The unique user id for the new user from the browser
    games_dict : dict of str to str
        A dictionary that contains a mapping of a game's appid to it's name
    lib : list of dict
        A list of dictionaries that represents the games in the user's library

    Returns
    -------
    pandas.DataFrame
        A pandas DataFrame with each row containing the user's id and the appid of a game owned by the user
    
    Raises
    ------
    Exception
        One of many errors occurred in attempting to load the data into the DataFrame
    '''
    # Create the DataFrame and filter out rows where the appid is not in our games_dict
    df_data = [(uid, x['appid'], 1.0) for x in lib]
    df = pd.DataFrame(data=df_data, columns=['uid', 'id', 'owned'])
    df = df[df['id'].isin(map(int, games_dict.keys()))]
    return df

# NOTE: UNUSED BUT MAY BE NEEDED IN THE FUTURE
def create_user_dict(interactions):
    user_id = list(interactions.index)
    user_dict = {}
    counter = 0
    for i in user_id:
        user_dict[i] = counter
        counter += 1
    return user_dict

# TODO: GENERATE SEQUENTIAL UIDS FOR EACH NEW USER TO THE SITE
def generate_uid():
    '''Generates a unique id for a new user to the site

    Parameters
    ----------
    None

    Returns
    -------
    int
        A number that will be the unique id for the new user
    '''
    # Return a dummy value until we implement the functionality
    return 3183

def get_user_recs(steamid):
    '''Return a list of game recommendations to the client
    
    Parameters
    ----------
    steamid : str
        A string representing the Steam ID of the user
        
    Returns
    -------
    JsonResponse
        Returns a JSONResponse with the list of game recs if everything is successful
    Response
        Returns a Response with an accompanying error message if something goes wrong
    '''
    # Get the user library
    print('getting usr lib')
    lib = None
    try:
        err = None
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        lib = get_user_library(steamid)
    except FileNotFoundError:
        err = 'Error: Unable to locate API key'
    except KeyError:
        err = 'Error: API call did not return a response'
    except JSONDecodeError:
        err = 'Error: The SteamID you entered is invalid'
        status_code = status.HTTP_400_BAD_REQUEST
    except RequestException as e:
        err = f'Error: {e.strerror}'
    finally:
        if err:
            print(err)
            return Response(err, status=status_code)

    # Load some prerequisite data from disk
    games_dict = None
    try:
        err = None
        games_dict = load_games_dict()
    except FileNotFoundError:
        err = 'Error: Could not locate games list'
    except pickle.UnpicklingError:
        err = 'Error: Could not load games list'
    finally:
        if err:
            print(err)
            return Response(err, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    existing_data = None
    try:
        existing_data = load_existing_data(games_dict, 'api/recdata_new.csv')
    except Exception as e:
        print(e)
        return Response(f'Error: {str(e)}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Generate a uid if the user is a new user
    uid = generate_uid()

    # Convert lib to pandas dataframe
    new_data = None
    try:
        new_data = load_user_data(uid, games_dict, lib)
    except Exception as e:
        print(e)
        return Response(f'Error: {str(e)}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
   
    # TODO: DO NOT COMPLETELY RETRAIN THE MODEL EACH TIME
    # Construct a Dataset from our data and use it to train the recommendation model
    dataset = None
    my_items = None
    solver = None
    try:
        print('fitting dataset')
        # Fit dataset on existing data and on the new user data
        dataset = Dataset()
        my_items = existing_data['id'].unique()

        # NOTE: WE NEED THE NEW USER ID IN THE INITIAL USER SET TO AVOID A SHAPE MISMATCH WITH
        #       THE ITEM EMBEDDINGS IN solver.fit_partial
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
        print(e)
        return Response(f'Error: {str(e)}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # NOTE: THIS CODE IS UNUSED BUT MAY BE REQUIRED IN THE FUTURE
    embeddings = solver.item_embeddings

    vector = None
    with open('api/vector.pickle', 'rb') as f:
        vector = pickle.load(f)

    user_dict = {x: x for x in range(3184)}

    # Make the recommendations
    try:
        print('making predictions')
        n_users, n_items = train_interactions.shape
        scores = pd.Series(solver.predict(uid, np.arange(n_items)))

        # Assign a label (appids) to each score generated by solver.predict
        scores.index = my_items

        # Sort values by best match first 
        scores = list(pd.Series(scores.sort_values(ascending=False).index))

        # Filter out games the user already owns and select only the slice of games we are returning to the client
        scores = list(pd.Series(filter(lambda x: x not in [y['appid'] for y in lib], scores)))
        return_score_list = scores[:5]

        # Map the appids from the index to the appropriate game_name
        scores = list(pd.Series(return_score_list).apply(lambda x: games_dict[str(x)]))
    except Exception as e:
        print(e)
        return Response(f'Error: {str(e)}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    # Return a JSONResponse of the recommended game names if all goes well
    return JsonResponse({'games': scores}, status=status.HTTP_200_OK)
