# -*- coding: utf-8 -*-
"""
Created on Fri Sep  3 11:19:58 2021

@author: Anja
"""

import pandas as pd
import geopandas as gpd
import pyproj as pyproj
from shapely import wkt
from io import StringIO
import io
import numpy as np
from github import Github, GithubException
import base64


foldername_variants='variants'
#concatenate them
columns = ['baumid', 'standortnr', 'kennzeich', 'namenr', 'art_dtsch', 'art_bot',
       'gattung_deutsch', 'gattung', 'pflanzjahr', 'standalter', 'kronedurch',
       'stammumfg', 'baumhoehe', 'bezirk', 'eigentuemer', 'coordinates']

#check whether Anlagenbaueme is good
columns_to_save = ['art_dtsch','art_bot','gattung_deutsch','gattung',
                   'lon','lat']


#add a new column 'variant'
Baumsorten_common = ['Eiche','Linde','Kiefer','Ahorn','Fichte','Buche','Birke',
                  'Esche','Erle','Douglasie','Kastanie','Hasel',
                   'Weissdorn','Ulme','Pappel','Pappel','Weide',
                   'Lärche','Tanne','Robinie','Platane','Gleditschie',
                  'Magnolie','Akazie','Zypresse','Schnurbaum',
                  'Zelkove','Goldregen','Hartriegel', 'Amberbaum',
                  'Essigbaum','Zeder','Eisenholzbaum','Lebensbaum',
                  'Wacholder','Korkbaum','Judasbaum','Zürgelbaum',
                  'Stechpalme','Trompetenbaum', 'Fächerblattbaum',
                  'Mammutbaum','Kreuzdorn']
Obstsorten_common = ['Apfel','Kirsche','Mirabelle','Pflaume', 'Birne','Walnuss',
                   'Zwetschge','Holunder','Schlehe',
                  'Mehlbeere','Maulbeerbaum','Eibe','Schwarznuss',
                   'Lederhülsenbaum','Vogelbeere','Elsbeere'#Unusual, but edible stuff
                  ]

variants_names={'Rot-Weissdorn':['Weissdorn','Weiss-Dorn','Weißdorn',
                             'Rotdorn']}

def add_variants(df,Baumsorten_list,art_dtsch='art_dtsch'):

    df['variant']=df[art_dtsch]
    for Baumsorten in Baumsorten_list:
        for art in Baumsorten:
            df.loc[df.art_dtsch.str.contains(art, case=False),'variant']=art
    return df

def replace_variants_sev_names(df,variants_names):
    for vari in variants_names:
        for alt_name in variants_names[vari]:
            df.loc[df.variant.str.contains(alt_name, case=False),'variant']=vari
    return df
    

#need to add longitude and latitude, converted from the coordinates
def xy_to_lonlat(x, y):
    proj_latlon = pyproj.Proj(proj='latlong',datum='WGS84')
    proj_xy = pyproj.Proj(proj="utm", zone=33, datum='WGS84')
    lonlat = pyproj.transform(proj_xy, proj_latlon, x, y)
    return lonlat[0], lonlat[1]

#add the exotic category to variants for those trees who have less than 4 members
def add_exotic_variants(df,numbers=[1,2,3,4],name='exotic_'):
    variants_counts=df.variant.value_counts()
    for numb in numbers:
        new_variant=name+str(numb)
        v_list_num=variants_counts[variants_counts==numb].index
        for variant in v_list_num:
            df.loc[df.variant.str.contains(variant, case=False),'variant']=new_variant
    return df    


def treat_trees_for_nans(df):
    for col in ['art_dtsch', 'art_bot', 'gattung_deutsch', 'gattung']:
        df[col] = df[col].fillna('Unbekannt')
    return df

def df2gpd(df):
    df['coordinates'] = gpd.GeoSeries.from_wkt(df['WKT'])
    gdf = gpd.GeoDataFrame(df, geometry='coordinates')
    return gdf



def treat_trees(df_trees):  
    df_trees = add_variants(df_trees,[Baumsorten_common,Obstsorten_common])
    df_trees = replace_variants_sev_names(df_trees,variants_names)
    df_trees['lon'],df_trees['lat'] = xy_to_lonlat(list(df_trees.coordinates.x),
                                                        list(df_trees.coordinates.y))
    df_trees = add_exotic_variants(df_trees)
    #summarize the similar names in variant (to reduce it further)
    return df_trees 


        



def get_blob_content(repo, branch, path_name):
    # first get the branch reference
    ref = repo.get_git_ref(f'heads/{branch}')
    # then get the tree
    tree = repo.get_git_tree(ref.object.sha, recursive='/' in path_name).tree
    # look for path in tree
    sha = [x.sha for x in tree if x.path == path_name]
    if not sha:
        # well, not found..
        return None
    # we have sha
    return repo.get_git_blob(sha[0])

def load_variant_git(repository, variant,bucket='static',folder='variants'):
    path_name=bucket+'/'+folder+'/'+variant+'.csv'
    try:
        file = repository.get_contents(path_name)
        trees = pd.read_csv(io.StringIO(file.decoded_content.decode('utf-8')))
    except GithubException:
        file = get_blob_content(repository,'master',path_name)
        b64 = base64.b64decode(file.content)
        trees = pd.read_csv(io.StringIO(b64.decode('utf-8')))
    return trees

def load_variant_list_git(repository,folder='static/variants'):
    contents = repository.get_contents(folder)
    variants = []
    while len(contents)>0:
        file_content = contents.pop(0)
        if file_content.type!='dir':
            vari=file_content.path.split('/')[-1]
            variants.append(vari.split('.')[0])
    #sort by unique
    variants = np.sort(np.array(variants))
    variants_unique = []
    variants_sublists = []
    for vari in variants:
        splitted = vari.split('-')
        basename = splitted[0]
        for i,split in enumerate(splitted):
            if split not in '123456789' and i!=0:
                basename+='-'
                basename+=split
        if basename not in variants_unique:
            variants_unique.append(basename)
            if splitted[-1] in '123456789':
                variants_sublists.append([splitted[-1]])
            else:
                variants_sublists.append([''])
        else:
            variants_sublists[-1].append(splitted[-1])
    return variants_unique, variants_sublists

def get_trees_df_local(folder,filenames):
    for i,filename in enumerate(filenames):
        if i==0:
            trees = pd.read_csv(folder+'/'+filename, encoding='utf-8')
            trees = treat_trees_for_nans(trees)
            trees = df2gpd(trees)
            trees = trees[columns]
        else:
            df = pd.read_csv(folder+'/'+filename, encoding='utf-8')
            df = treat_trees_for_nans(df)
            df = df2gpd(df)
            trees = pd.concat([trees[columns],df[columns]])
    return trees
        
    

def save_different_variants_local(trees,folder):
    for vari in trees.variant.unique():
        #have a hard limit of max 10 different variants per tree type!
        df_to_save = trees[trees.variant==vari]
        df_to_save = df_to_save[columns_to_save]
        counter = 1
        while len(df_to_save.art_dtsch.unique())>10:
            art_unique = np.sort(np.array(df_to_save.art_dtsch.unique()))
            interm = df_to_save[df_to_save.art_dtsch.isin(art_unique[:10])]
            interm = interm.sort_values(by = 'art_dtsch')
            interm.to_csv(folder+'/'+vari+'-'+str(counter)+'.csv', index=False)
            counter+=1
            df_to_save = df_to_save[~df_to_save.art_dtsch.isin(art_unique[:10])]
            print(art_unique)
        df_to_save = df_to_save.sort_values(by ='art_dtsch')
        if counter == 1:
            df_to_save.to_csv(folder+'/'+vari+'.csv', index=False)
        else: 
            df_to_save.to_csv(folder+'/'+vari+'-'+str(counter)+'.csv', index=False)
            
def load_treat_save_local():
    filenames = ['baumanlagen2.csv','strassenbaume2.csv']
    folder = 'static'
    print('loading trees')
    trees = get_trees_df_local(folder,filenames)
    print('treating trees')
    trees = treat_trees(trees)
    print('saving variants')
    save_different_variants_local(trees,'static/variants')


    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    


    
    






