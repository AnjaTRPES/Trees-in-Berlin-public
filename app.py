# -*- coding: utf-8 -*-
"""
Created on Fri Sep  3 11:19:06 2021

@author: Anja
"""

import pandas as pd
import geopandas as gpd
import pyproj as pyproj
import treat_trees_data as tr




#make the Dash app
#from jupyter_dash import JupyterDash
import dash_core_components as dcc
import numpy as np
import dash_html_components as html
#from dash.dependencies import Input, Output
from dash_extensions.enrich import Output, DashProxy, Input, MultiplexerTransform, State
from dash.exceptions import PreventUpdate
import plotly.express as px
import plotly.graph_objects as go
import os as os
from github import Github

def get_wiki_link(latin_names):
    latin_name = latin_names[0]
    #remove the '' if present
    splitted = latin_name.split("'")
    if len(splitted) == 0:
        latin_name = splitted[0]
    elif len(splitted) == 3:
        if latin_name[0] == "'":
            latin_name = splitted[-1]
        else:
            latin_name = splitted[0]
    
    #check whether the last few ones are 'spec.'

    if latin_name[-5:]=='spec.':
        latin_name = latin_name[:-5]+' (Gattung)'

    latin_name = latin_name.replace(' ','_')
    wiki_link = f'https://de.wikipedia.org/w/index.php?title={latin_name}&redirect=yes'
    return wiki_link

token = os.environ['mapbox_token']
px.set_mapbox_access_token(token)

app=DashProxy(__name__,prevent_initial_callbacks=True, transforms=[MultiplexerTransform()],
              title = 'Bäume in Berlin')

server = app.server



bucket = 'static'
folder = 'variants'
#make the repository
token_git = os.environ['github_token']
github = Github(token_git)
repository = github.get_user().get_repo('Trees-in-Berlin-public')

#load all the variant names
variant_names, variant_names_ext = tr.load_variant_list_git(repository)
variant_names = np.sort(np.array(variant_names))

#get the trees for the first variant in the folder
trees = tr.load_variant_git(repository, variant_names[0]+'-'+variant_names_ext[0][0])

Explainertext = '''
Es gibt jede Menge Bäume in Berlin - und die Stadt Berlin dokumentiert das! 
Die Datensätze gibt es öffentlich auf https://daten.berlin.de/datensaetze.
Hier könnt ihr sehen, wo es welche Bäume gepflanzt wurden. Einfach die entsprechende
 Art im Dropdown-Menü auswählen - und euch werden die Sorten angezeigt! Bei zu vielen Sorten 
 (z.B. bei den Arten Linde und Ahorn) könnt ihr im zweiten Dropdown-Menü dann verfeinern, denn bei
 80 verschiedene Sorten blickt ja keiner mehr durch ;).
Weiter unten könnt ihr euch dann über die entsprechende Baumsorte informieren - vorausgesetzt, der entsprechende
 Wikipediartikel existiert!


\n\n\n  \n
'''


fig = px.scatter_mapbox(trees,
                        lat = 'lat',
                        lon = 'lon',
                        hover_name = "art_dtsch",
                        color = 'art_dtsch',
                        zoom = 9, center = {"lat": 52.5200, "lon": 13.4050},
                        labels = {'art_dtsch':'Art:'}
                       )
fig.update_layout(mapbox_style = "open-street-map")
fig.update_layout(margin = {"r":0,"t":0,"l":0,"b":0})

arts_initial=trees.art_dtsch.unique()

trees_json = trees.to_json(orient = 'split')

app.layout=html.Div([
    html.H1('Bäume in Berlin'),
    html.Div(children=Explainertext),
    html.Div(children='Erstellt von: https://github.com/AnjaTRPES'),
    html.Div(children=[
        html.Div(children=[
            dcc.Dropdown(id = 'variants_dropdown',
                        options = [{'label': value,'value': value} for value in variant_names],
                         value = variant_names[0]
                        )],
            style=dict(width='50%')),
        html.Div(children=[
        dcc.Dropdown(id = 'variants_more',
                     options = [{'label': value,'value': value} for value in variant_names_ext[0]],
                     value = variant_names_ext[0][0]
                     )],
            style=dict(width='40%'))
    ],style=dict(display='flex')),
    dcc.Graph(id = 'map',figure = fig),
    
    dcc.Checklist(id = 'type_checklist',
        options=[{'label': value,'value': value} for value in np.sort(arts_initial)],
        value = np.sort(arts_initial)
    ),
    html.H2('Mehr Details zu einer bestimmten Art'),
    dcc.Dropdown(id = 'arts_dropdown',
                options = [{'label':value,'value':value} for value in np.sort(arts_initial)],
                value = np.sort(arts_initial)[0]),
    html.Iframe(id = 'wikipedia_link',
                src = get_wiki_link(np.sort(trees[trees.art_dtsch==np.sort(arts_initial)[0]].art_bot.unique())),
                style = {"height": "1067px", "width": "100%"}),
    dcc.Store(id = 'trees_df',
              storage_type = 'memory',
              data = trees_json)
])

@app.callback([Output('variants_more','options'),
               Output('variants_more','value')],
              [Input('variants_dropdown','value')])
def update_more_variants(value):
    #get the index of variant_names
    location = list(variant_names).index(value)
    options = [{'label': value,'value': value} for value in variant_names_ext[location]]
    print('options',options)
    print('value',value)
    return options, variant_names_ext[location][0]


@app.callback([Output('map','figure'),
              Output('type_checklist','options'),
              Output('type_checklist','value'),
               Output('arts_dropdown','options'),
               Output('arts_dropdown','value'),
              Output('wikipedia_link','src'),
              Output('trees_df', 'data')],
              [Input('variants_more','value')],
               [State('variants_dropdown','value')])
def update_figure(more,value):
    print('value',value)
    print('more',more)
    print(more=='')
    if more!='':
        value = value+'-'+more
    print('value',value)
    trees = tr.load_variant_git(repository, value)

    fig = px.scatter_mapbox(trees,
                        lat='lat',
                        lon='lon',
                        hover_name="art_dtsch",
                        color='art_dtsch',
                        zoom=9, center = {"lat": 52.5200, "lon": 13.4050},
                        labels = {'art_dtsch':'Art:'}
                       )
    fig.update_layout(mapbox_style="open-street-map",
                     uirevision='True',
                     #transition={'duration':500,'easing':'cubic-in-out'}
                     )
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

    arts=trees.art_dtsch.unique()
    options=[{'label':value,'value':value} for value in np.sort(arts)]
    
    
    #make the wikipedia link
    art_web=arts[0]
    #update_wiki(art_web)
    #get the latin name
    latin_names=np.sort(trees[trees.art_dtsch==art_web].art_bot.unique())
    wiki_link=get_wiki_link(latin_names)
    return fig,options,arts,options,arts[0],wiki_link,trees.to_json(orient = 'split')


@app.callback(Output('wikipedia_link','src'),
             [Input('arts_dropdown','value')],
              [State('trees_df', 'data')])
def update_wiki(value, data):
    if data !=None:   
        trees = pd.read_json(data, orient = 'split')
        latin_names = np.sort(trees[trees.art_dtsch==value].art_bot.unique())
        wiki_link = get_wiki_link(latin_names)
        return wiki_link
    else:
        raise PreventUpdate

@app.callback(Output('map','figure'),
             [Input('type_checklist','value')],
             [State('map','figure')])
def change_selection_figure(value,fig):
    data_new = list(fig['data'])#transform to a list in order to go over it and check
    for i,scattermapbox in enumerate(data_new):
        #remove it
        if scattermapbox['hovertext'][0] not in value:
            data_new[i]['visible'] = False
            data_new[i]['showlegend'] = False
        else:
            data_new[i]['visible'] = True
            data_new[i]['showlegend'] = True
    data_new = tuple(data_new)
    fig['data'] = data_new
    return fig
          
        
    




if __name__=='__main__':
    
    # Run app
    app.run_server(debug = False)



