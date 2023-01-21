import requests
import pandas as pd
import json
import os.path
import time
from progress.bar import Bar


def get_prs(project, after_cursor=None):
    parts=project.split('/')
    owner=parts[0]
    name=parts[1]
    after = 'after:"%s",' % (after_cursor) if after_cursor else ""
    query = """
 {
  repository(owner:"%s", name:"%s") {
    pullRequests(first: 100, %s) {
      pageInfo {
        endCursor
        hasNextPage
      }
      totalCount
      nodes {
        url
        number
        title
        state
        id
        bodyText
        changedFiles
        files(first: 100) {
          totalCount
          nodes {
            additions
            deletions
            path
          }
        }
        labels (first: 100) {
          nodes {
            name
          }
        }
      }
    }
  }
}
""" % (owner, name, after)
    return query

def fetch_gh(project, after_cursor=None):
    fname='cached/' + project.replace('/', '_')
    if after_cursor:
        fname = fname + '_' + after_cursor
    fname = fname + '.json'
#    print(fname)
    if os.path.isfile(fname):
#        print('return cached')
        s = open(fname).read()
        x = json.loads(s)
        return x
    url = 'https://api.github.com/graphql'
    json_query = { 'query' : get_prs(project, after_cursor) }
    api_token = "737d7c04a5e3beff15421bacb25ceee99410b7c0"
    headers = {'Authorization': 'token %s' % api_token}
    r = requests.post(url=url, json=json_query, headers=headers)
    time.sleep(0.5)
    if r.status_code == 200:
        f=open(fname, 'w')
        f.write(r.text)
        f.close()
        x=json.loads(r.text)
        return x
    else:
        if r.status_code == 403:
            print("sleep 120")
            time.sleep(120)
        print(r.headers)
        print (r.text)
        return None



def fetch_gh_paginated(project):
    pi=dict()
    i = 0
    bar = None
    while True:
        i = i+1
        x=fetch_gh(project, pi.get('endCursor', None))
        try:
            pi=x.get('data').get('repository').get('pullRequests').get('pageInfo')
        except:
            print(x)
            break
        totalCount = x.get('data').get('repository').get('pullRequests').get('totalCount')
#        print(pi, i, totalCount)
        if bar is None:
            max_val = int( (totalCount-100) / 100) if totalCount > 200 else 1
            bar=Bar('Fetching ' + project + ' expected ' + str(totalCount), max=max_val, suffix='%(percent)d%% %(eta)s')
        bar.next()
        if pi.get('hasNextPage') == False:
            break


def prepare_projects():
    if os.path.isfile('large_prs.csv'):
        top_projects=pd.read_csv('large_prs.csv')
    else:
        pullreqs=pd.read_csv("new_pullreq.csv")
        jp=pullreqs[pullreqs['language']=='Java']
        jp['project']=jp[['ownername','reponame']].apply(lambda xs: xs['ownername'] + "/" + xs['reponame'], axis=1)
        top_projects=jp[jp['core_member']==0][['project','merged_or_not']].groupby(by=['project']).count()
        top_projects['cnt'] = top_projects['merged_or_not']
        top_projects['project']=top_projects.index
        top_projects[['project','cnt']].to_csv('large_prs.csv')
    
    top_projects=top_projects[top_projects['cnt'] > 20]


    projects=top_projects[['project','cnt']]
    projects=projects.sample(frac=1).drop_duplicates(subset=['project'])
    return projects

if __name__ == '__main__':
    projects=prepare_projects()
    print("Fetching ", len(projects))
    bar=Bar('Processing ' + str(len(projects)) + " projects", max=len(projects), suffix='%(percent)d%% %(eta)s')

    for i, x in projects[['project','cnt']].iterrows():
        #print('\nFetching ', x['project'], ' expected ', x['cnt'])
        try:
          fetch_gh_paginated(x['project'])
          bar.next()
        except Exception as e:
            print(e, x['project'])

