import React, { useState } from 'react';
import { Grid, Button, Typography, TextField } from "@material-ui/core";
import { BrowserRouter as Router, Routes, Route, useNavigate, Link, Navigate } from 'react-router-dom';
import DisplayPage from './DisplayPage'

export default function LoginPage(props) {
    /* The login page will either take a username and password which we can use
     * to get the user's steamID (via a Steam API call we will make on the backend)
     * or the user can just enter their steamID directly */
    const [username, setUsername] = useState('');
    const [pwd, setPwd] = useState('');
    const [steamID, setSteamID] = useState('');
    const [twoFactorAuth, setTwoFactorAuth] = useState('');

    const [btnDisabled, setBtnDisabled] = useState(false);

    const navigate = useNavigate();
    // NOTE: UNUSED
    const [error, setError] = useState('');

    let enterPressed = false;

    const handleUsernameTextFieldChange = (e) => {
        setUsername(e.target.value);
    }

    const handlePwdTextFieldChange = (e) => {
        setPwd(e.target.value);
    }

    const handleSteamIDTextFieldChange = (e) => {
        setSteamID(e.target.value);
    }    

    const handleTwoFactorAuthTextFieldChange = (e) => {
        setTwoFactorAuth(e.target.value);
    }

    const handleLoginButtonPressed = async () => {
        // Prevent user from overloading us with requests
        setBtnDisabled(true);
        
        // If the user entered a steamID we will just send that to the backend 
        // Else we need to authenticate the username and password to get the user's steamID
        let usrLib = null;
        console.log('steamid: ' + steamID);
        if (steamID !== '') {
            console.log('got an id')
            const requestOptions = {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({steamID: steamID})
            };

            await fetch('/api/validate-id', requestOptions)
            .then(response => {
                if (response.ok) {
                    console.log('ID validated');
                    return response.json();
                }
                else {
                    throw response;
                }
            }).then(data => usrLib = data)
            .catch(myError => myError.text().then(err => alert(err)));
        } else {
            console.log('no id found')
            const requestOptions = {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({username: username, pwd: pwd, twoFactorAuth: twoFactorAuth})
            };

            await fetch('/api/login', requestOptions)
            .then(response => {
                if (response.ok) {
                    console.log('Login successful');
                    return response.json();
                }
                else
                    throw response;
            }).then(data => usrLib = data)
            .catch(myError => myError.text().then(err => alert(err)));
        }

        // Waits for the fetch to finish before doing this
        // TODO: RENDER THE GAMES IN A GRAPHICAL WAY AS OPPOSED TO LOGGING THEM
        let games = usrLib.games;
        console.log('games: ' + games.toString());

        // Reenable button
        setBtnDisabled(false);

        // Redirect to games recs page (hopefully?)
        navigate('/recs', {state: {games: games}});    
    }

    return (
        <div>

        <Grid container spacing={1} align='center'>
            <Grid item xs={12} >
                <Typography variant='h6' component='h6'>
                    Login to your steam account
                </Typography>
            </Grid>
            <Grid item xs={12}>
                <TextField error={error}
                label='Username'
                placeholder='Enter your username'
                value={username}
                helperText={error}
                variant='outlined'
                onChange={handleUsernameTextFieldChange} />
            </Grid>
            <Grid item xs={12}>
                <TextField error={error}
                label='Password'
                placeholder='Enter your password'
                value={pwd}
                helperText={error}
                variant='outlined'
                onChange={handlePwdTextFieldChange} />
            </Grid>
            <Grid item xs={12}>
                <TextField error={error}
                label='2FA Code'
                placeholder='Enter your 2FA code'
                value={twoFactorAuth}
                helperText={error}
                variant='outlined'
                onChange={handleTwoFactorAuthTextFieldChange} />
            </Grid>
            <Grid item xs={12}>
                <Typography variant='h6' component='h6'>
                    Or directly enter your steamID
                </Typography>
            </Grid>
            <Grid item xs={12}>
                <TextField error={error}
                label='SteamID'
                placeholder='Enter your SteamID'
                value={steamID}
                helperText={error}
                variant='outlined'
                onChange={handleSteamIDTextFieldChange} />
            </Grid>
            <Grid item xs={12}>
                <Button disabled={btnDisabled} variant='contained' color='primary' onClick={handleLoginButtonPressed}>
                    Login
                </Button>
            </Grid>
        </Grid>
        </div>
    );
}
