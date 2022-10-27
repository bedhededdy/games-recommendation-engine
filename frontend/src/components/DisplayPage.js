import React, { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Grid, Button, Typography, TextField } from "@material-ui/core";

export default function DisplayPage(props) {
    const location = useLocation();    

    const renderRecs = () => {
        const components = new Array(5);

        for (let i = 0; i < components.length; i++) {
            components[i] = (
                <Grid item xs={12}>
                    <Typography variant='h6' component='h6'>
                        {location.state.games[i]}
                    </Typography>
                </Grid>
            );
        }

        return components;
    }    

    return (
        <Grid container spacing={1} align='center'>
            {renderRecs()}
        </Grid>
    );
}
