import React from 'react';
import ReactDOM from 'react-dom'; 
import {BrowserRouter as Router, Routes, Route} from 'react-router-dom'; // FIXME: THIS IS DEPRECATED, FIGURE OUT THE CORRECT WAY
import LoginPage from './LoginPage';
import DisplayPage from './DisplayPage';

// Renders this content in the app div in index.html
export default function App(props) {
    return (
        <Router>
            <Routes>
                <Route exact path='/' element={<LoginPage />} />
                <Route exact path='/recs' element={<DisplayPage {...props}/>} />
            </Routes>
        </Router>
    );
}

const appDiv = document.getElementById('app');
ReactDOM.render(<App />, appDiv);
