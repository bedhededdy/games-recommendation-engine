import React, { Component } from 'react';
import { render } from 'react-dom';
import LoginPage from './LoginPage';

// Don't know how to do this with func component, but this is just a dummy anyway
// so it's fine that it's a class
export default class App extends Component {
    constructor(props) {
        super(props);
    }

    render() {
        return <LoginPage />
    }
}

const appDiv = document.getElementById('app');
render(<App />, appDiv);
