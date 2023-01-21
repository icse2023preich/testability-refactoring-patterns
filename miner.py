import os
from progress.bar import Bar
import requests
import pandas as pd
import json
import os.path
import time
import os
import fetcher
import re

def get_project(x):
    mat=re.match(r'https://github.com/([^/]+/[^/]+).*',x)
    if mat:
        return mat.group(1)
    
    
def extract_url(n):    
    return pd.DataFrame(data={'url':[n['url']]})
    
def get_files(d):
    return [d+'/' + x for x in os.listdir(d)]

def is_testability_relevant(s):
    if not isinstance(s, str):
        return (False, None)
    if '@Testable' in s:
        return (False,'@Testable')
    if 'VisibleForTesting' in s:
        return (True, 'VisibleForTesting')
    s=s.lower()
    masks=['testability','testable','easier to test', 'simplify testing','cover']
    for m in masks:
        if m in s:
            return (True, m)
    ref_masks=['test','junit']
    if 'refactor' in s:
        for m in ref_masks:
            if m in s:
                return (True, 'refactor_' + m)
    if 'add' in s:
        for m in ref_masks:
            if m in s:
                return (True, 'add_' + m)
    if 'fix' in s:
        for m in ref_masks:
            if m in s:
                return (True, 'fix_' + m)
    for m in ref_masks:
        if m in s:
            return (True, m)
            
    return (False, None)

def get_prod_files(files):
    java_files=dict([(f.split('/')[-1].replace('.java',''),f) for f in files if not 'Test.java' in f and f.endswith('.java')])
    return java_files

def get_test_files(files):
    test_java_files=dict([(f.split('/')[-1].replace('Test.java',''),f) for f in files if 'Test.java' in f])
    return test_java_files

def calc_test_pairs(java_files, test_java_files):
    return(dict([(java_files[t],test_java_files[t]) for t in test_java_files if t in java_files]))

def get_test_pairs(files):
    java_files=get_prod_files(files)
    test_java_files=get_test_files(files)
    return calc_test_pairs(java_files, test_java_files)

def make_clickable(val):
    # target _blank to open new window
    return '<a target="_blank" href="{}">{}</a>'.format(val, val)


def process_node(n, items):
    title_ok = is_testability_relevant(n['title'])
    body_ok = is_testability_relevant(n['bodyText'])
#    bodies.append(n['bodyText'])
#    titles.append(n['title'])
    if 'files' in n and int(n.get('changedFiles',0)) > 0:
        changed_files = [x.get('path', '') for x in n.get('files',{}).get('nodes',[])]
        test_pairs = get_test_pairs(changed_files)
        n.update({'java_files' : len([x for x in changed_files if '.java' in x]),
                'test_java_files' : len([x for x in changed_files if 'Test.java' in x]),
                'test_pairs' : len(test_pairs)
                })
        if body_ok[0] or title_ok[0] or True:
            n.update({'mtime':os.path.getmtime(fname)})
            n.update({'body_ok':body_ok})
            n.update({'title_ok':title_ok})
            n.update({'fname':fname})
            items.append(n)
    
def process_files(files, node_processor):
    for fname in files:
        js=json.loads(open(fname).read())
        if not js.get('data').get('repository'):
            continue
        try:
            for n in js.get('data',{}).get('repository',{}).get('pullRequests',{}).get('nodes',[]):
                node_processor(n)
        except Exception as e:
            print(e, fname)
    
if __name__ == '__main__':    
    files=get_files('cached')
    items=[]
    bodies=[]
    titles=[]
    items.sort(key=lambda x: x.get('mtime'), reverse=True)
    #for item in items[:1]:
    #    if item['title_ok'][0]:
    #        print(item['title_ok'], item['body_ok'], item['url'], item['title'])

    df=pd.DataFrame(items)[['url','title','changedFiles', 'java_files','test_java_files','test_pairs','body_ok','title_ok']]
    df.style.format({'url': make_clickable})
    df['body_mask'] = df['body_ok'].apply(lambda x: x[1])
    df['title_mask'] = df['title_ok'].apply(lambda x: x[1])
    df[['url','title','changedFiles','java_files','test_java_files','test_pairs','title_mask','body_mask']].to_csv('testable_prs.csv')

    df['repo_url'] = df['url'].apply(lambda x: re.sub(pattern='(.*?)/pull/[0-9]+',string=x,repl='\\1.git'))
    df['pull_req_id'] = df['url'].apply(lambda x: re.sub(pattern='.*?/pull/([0-9]+)',string=x,repl='\\1'))
    df['prid'] = df['url'].apply(lambda x: re.sub(pattern='.*?github.com/(.*?)/pull',string=x,repl='\\1').replace('/','_'))

    def gen_mined_csv():
        mined=pd.DataFrame()
        for fname in get_files('mined'):
            if os.path.getsize(fname) < 100:
                continue
            x=pd.read_csv(fname,sep=';')
            x['fname']=fname
            x['prid']=fname.replace('mined/','').replace('.csv','')
            mined=mined.append(x)

        m=df.merge(mined, on='prid')
        m.to_csv('mined.csv')
        return m

    print('Generate before: ', len(gen_mined_csv()))

    bar=Bar('Mining', max=len(df), suffix='%(percent)d%% %(eta)s')
    for i, row in df.sample(frac=1.0).iterrows():
        fname='mined/' + row['prid']+'.csv'
        if not (row['title_mask'] or row['body_mask']):
            continue

        cmd='mvn com.github.anonauthor:refminer-mvn-plugin:refminer -DrefminerFilename=' + fname + ' -DgitURL=%s -DpullRequest=%s' % (row['repo_url'], row['pull_req_id'])
        if not os.path.isfile(fname):
            print(cmd)
            ret=os.system(cmd)
            if ret != 0:
                print("Ended with " , ret)
                break
        bar.next()

    print('Generate after: ', len(gen_mined_csv()))
