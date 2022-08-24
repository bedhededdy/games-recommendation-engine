import React from 'react';
import ReactDOM from 'react-dom'; // FIXME: THIS IS DEPRECATED, FIGURE OUT THE CORRECT WAY
import LoginPage from './LoginPage';

// Renders this content in the app div in index.html
export default function App(props) {
    return <LoginPage />
}

const appDiv = document.getElementById('app');
ReactDOM.render(<App />, appDiv);
