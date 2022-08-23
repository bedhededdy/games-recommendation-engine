import steam.webauth as wa
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from .utils import get_user_recs

# TODO: There is a lot of code duplication here. Attempt to condense the two views into one
class LoginView(APIView):
    '''A view that validates a user's Steam login and returns their game recommendations

    Methods
    -------
    post(request, format=None)
        Posts JsonResponse containing game recommendations to the client upon successful login
        Else posts Response containing the appropriate error message
    '''
    def post(self, request, format=None):
        '''Posts JsonResponse containing game recommendations to the client upon successful login
        Else posts Response containing the appropriate error message

        Parameters
        ----------
        request : rest_framework.request.Request
            A request containing the login information of the user
        format : Any
            Unused variable that may in the future be used for formatting

        Returns
        -------
        JsonResponse
            A JsonResponse containing the list of game recommendations
        Response
            A Response that contains the error message of what went wrong
        '''
        # Create a session if one doesn't exist
        session = self.request.session

        if not session.exists(session.session_key):
            session.create()

        # Get login data from request
        username = request.data.get('username')
        pwd = request.data.get('pwd')
        two_factor = request.data.get('twoFactorAuth')

        # Attempt to login and retrieve the user's Steam ID
        if username and pwd:
            try:
                usr = wa.WebAuth(username)
                usr.login(pwd, twofactor_code=two_factor)
                steamid = usr.steam_id
            except wa.LoginIncorrect:
                return Response('Error: You have misentered your login information', status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response('Error: Incomplete fields', status=status.HTTP_400_BAD_REQUEST)

        # Return game recommendations for the user is all went well
        return get_user_recs(steamid)

class ValidateView(APIView):
    '''A view that gets a user's Steam ID and returns their game recommendations

    Methods
    -------
    post(request, format=None)
        Posts JsonResponse containing game recommendations to the client upon successful login
        Else posts Response containing the appropriate error message
    '''
    def post(self, request, format=None):
        '''Posts JsonResponse containing game recommendations to the client upon successful login
        Else posts Response containing the appropriate error message

        Parameters
        ----------
        request : rest_framework.request.Request
            A request containing the Steam ID of the user
        format : Any
            Unused variable that may in the future be used for formatting

        Returns
        -------
        JsonResponse
            A JsonResponse containing the list of game recommendations
        Response
            A Response that contains the error message of what went wrong
        '''
        # Create a session if one doesn't exist
        session = self.request.session

        if not session.exists(session.session_key):
            session.create()

        # Get the Steam ID and attempt to get recommendations (errors for invalid id is handled in get_user_recs)
        steamid = request.data.get('steamID')
        return get_user_recs(steamid)
