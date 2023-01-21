from miner import get_files
import traceback, sys
from statsmodels.stats.proportion import proportions_ztest
import math
from io import BytesIO
import requests
import os
import re
import json
import pandas as pd
import numpy as np
import time
import matplotlib.pyplot as plt
import seaborn as sns

def df_to_latex(df,index=True):
    s=df.round(2).to_latex(index=index)
    s=s.replace('\\toprule','\hline').replace('\\midrule','\hline').replace('\\bottomrule','\hline')
    m=re.match(r'.*?\{(l*r*)\}.*', s)
    if m:
        s=s.replace(m.group(1),'|'+('|'.join(list(m.group(1)))+'|'))
    return s

def contains_in_masks(s, masks):
    return len([m for m in masks if m in s]) > 0

def is_testability_relevant(s):
    if not isinstance(s, str):
        return (False, "other")
    s=s.lower()
    testability_masks=['testability','testable']
    for m in testability_masks:
        if m in s:
            return (True, 'testability')
    if 'refactor' in s and ('test' in s or 'junit' in s):
        return (True, 'Refactor for test')
    if 'dependency' in s or 'depend' in s:
        return (True, 'Dependency')
    if 'concurren' in s or 'thread' in s or 'sleep' in s or 'latch' in s:
        return (True, 'Concurrency')
    if 'singleton' in s:
        return (True, 'Singleton')
    if 'inject' in s or 'wire' in s or 'wiring' in s:
        return (True, 'Inject')
    if 'socket' in s or 'network' in s or 'connectivity' in s:
        return (True, 'Network')
    
#    if 'fix' in s:
#        return (True, 'fix')
    if 'test' in s or 'junit' in s:
        return (True, 'test')
    
#    if 'junit' in s:
#        return (True, 'junit')
            
    return (False, "Other")

def is_testability_relevant_suggested(s):
    if not isinstance(s, str):
        return (False, "other")
    s=s.lower()
    test_junit=['test','junit']
    #m1
    if contains_in_masks(s, ['testabilit','testable']):
        return (True, 'testability')
    #m2
    if contains_in_masks(s, ['simpl','visibl','eas']) and contains_in_masks(s, test_junit):
        return (True, 'Easier to test')
    #m3
    if 'refactor' in s and contains_in_masks(s, test_junit):
        return (True, 'Refactor for test')
    #m4
    if 'depend' in s and contains_in_masks(s, test_junit):
        return (True, 'Dependency')
    #m5
    if contains_in_masks(s, ['concurren','thread','sleep','latch']) and contains_in_masks(s, test_junit):
        return (True, 'Concurrency')
    #m6
    if 'singleton' in s and contains_in_masks(s, test_junit):
        return (True, 'Singleton')
    #m7
    if contains_in_masks(s, ['inject','wire','wiring']) and contains_in_masks(s, test_junit):
        return (True, 'Injection')
    #m8
    if contains_in_masks(s, ['network','socket','connectivity','connection']) and contains_in_masks(s, test_junit):
        return (True, 'Network')
    
    if 'fix' in s:
        return (True, 'Fix')
    if 'test' in s:
        return (True, 'test')
            
    return (False, "other")

def generate_all_prs(df):
    all_prs=df.groupby(['url','title_mask','body_mask','title'], as_index=False).agg(
        {'prod_file':'count', 
         'prod_additions': 'sum',
         'test_additions': 'sum',
         'prod_deletions': 'sum',
         'test_deletions': 'sum',
         'test_pairs':'first',
         'changed_files':'first'
        })
    ja = df.groupby(['url'])
    ja=ja.agg({'changedFile':lambda f: len([s for s in f if s.endswith('.java')] )})
    ja=ja.reset_index().rename(columns={'changedFile':"java_files_count"})
    all_prs=all_prs.merge(ja, on='url')
    return all_prs

def normalise_url(x):
    mat=re.match(r'(https://github.com/[^/]+/[^/]+/pull/[0-9]+).*',x)
    if mat:
        return mat.group(1)

    
def get_project(x):
    mat=re.match(r'https://github.com/([^/]+/[^/]+).*',x)
    if mat:
        return mat.group(1)

def create_mined_filename(row):
    fname='mined/' + row['prid']+'.csv'
    return fname

def derive_prid(x):
    return re.sub(pattern='.*?github.com/(.*?)/pull/([0-9]+).*',string=x,repl='\\1_\\2').replace('/','_')

def enrich_mine_df(df):
    df['repo_url'] = df['url'].apply(lambda x: re.sub(pattern='(.*?)/pull/[0-9]+',string=x,repl='\\1.git'))
    df['pull_req_id'] = df['url'].apply(lambda x: re.sub(pattern='.*?/pull/([0-9]+)',string=x,repl='\\1'))
    df['prid'] = df['url'].apply(lambda x: re.sub(pattern='.*?github.com/(.*?)/pull',string=x,repl='\\1').replace('/','_'))
    df['mined_filename']=df.apply(create_mined_filename, axis=1)
    df['mined_already']=df['mined_filename'].apply(os.path.isfile)
    return df

def gen_mined_csv(files=None):
    mined=pd.DataFrame()
    for fname in files:
        if os.path.getsize(fname) < 100:
            continue
        x=pd.read_csv(fname,sep=';')
        x['fname']=fname
        x['prid']=fname.replace('mined/','').replace('.csv','')
        mined=mined.append(x)

    return mined

def get_manually_mined(all_prs, manually_reviewed):
    mined_filenames=enrich_mine_df(manually_reviewed[['url','pr_group','ref_pattern']].merge(all_prs).drop_duplicates())
    mined=gen_mined_csv(mined_filenames[mined_filenames.mined_already==True]['mined_filename'])
    mined=mined.merge(mined_filenames)
    return mined    

def mine_prs(df):
    df=enrich_mine_df(df)
    print(df['mined_already'].value_counts())
    mdf=df[df['mined_already']==False]
    print('Mining ', len(mdf), 'PRs')
    counter=0
    for i, row in mdf.sample(frac=1.0).iterrows():
        fname='mined/' + row['prid']+'.csv'
        cmd='mvn com.github.jazzmuesli:refminer-mvn-plugin:commitminer -DrefminerFilename=' + fname + ' -DgitURL=%s -DpullRequest=%s' % (row['repo_url'], row['pull_req_id'])
        if not os.path.isfile(fname):
            print(counter, '/', len(mdf), cmd)
            ret=os.system(cmd)
            counter = counter+1
            if ret != 0:
                print("Ended with " , ret)
                time.sleep(900)
                
def get_3k_mined(prs_to_mine):
    mined_filenames=enrich_mine_df(prs_to_mine)
    print(pd.crosstab(mined_filenames['test_pairs']>0,mined_filenames['mined_already'],margins=True))
    mined=gen_mined_csv(mined_filenames[mined_filenames.mined_already==True]['mined_filename'])
    mined=mined.merge(mined_filenames)
    return mined    

# exclude refactored Test classes
def exclude_refactored_tests(mined):
    mined['is_test']=False
    mined.loc[(mined.classesAfter.notnull()) & (mined.classesAfter.str.endswith('Test')),'is_test']=True
    mined=mined[mined.is_test==False]
    # exclude my half-baked pattern
    mined=mined[mined.refactoringType != 'ADD_CONSTRUCTOR_PARAMETER']
    return mined

#mark PRs with test pairs
def mark_prs_with_test_pairs(mined):
    mined['with_test_pairs']=False
    mined.loc[mined.test_pairs>0,'with_test_pairs']=True
    return mined

def mark_reviewed_prs_with_test_pairs(mined, manually_reviewed):
    if 'pr_group' in mined:
        mined=mined.merge(manually_reviewed[['url','pr_group']].drop_duplicates())
        mined['with_test_pairs']=False
        mined.loc[mined.pr_group!='irrelevant','with_test_pairs']=True
    return mined

def exclude_too_large_commits(mined, all_prs_with_files):
    # remove commits that are too large and likely to be merge commits
    java_files_by_url=all_prs_with_files[all_prs_with_files.changedFile.str.endswith('.java')][['url','changedFile']].groupby('url').count()
    cafter_by_url=mined.groupby(['url','commit']).agg({'classesAfter':lambda x: len(set(x))}).sort_values('classesAfter').reset_index()
    commits=cafter_by_url.merge(java_files_by_url.reset_index())
    irrelevant_commits=commits[commits.classesAfter > commits.changedFile]['commit'].drop_duplicates()
    mined=mined[~mined.commit.isin(irrelevant_commits)]
    return mined

def extract_simple_file_name(s):
    return re.sub(r'.*?/([^/]+).java$', '\\1', s) if isinstance(s,str) else ''

def extract_simple_class_name(s):
    return re.sub(r'.*?([^\\.]+)$', '\\1', s)

def merge_refs_on_prod_file(mined, manually_reviewed):
    dmined=mined
    derived=manually_reviewed
    derived['prod_file_className']=derived['prod_file'].apply(extract_simple_file_name)
    dmined['classNameBefore']=dmined['classesBefore'].apply(extract_simple_class_name)
    dmined['classNameAfter']=dmined['classesAfter'].apply(extract_simple_class_name)
    m=dmined[dmined.pr_group!='irrelevant'].merge(derived[['url','prod_file_className']].drop_duplicates(), left_on=['url','classNameBefore'], right_on=['url','prod_file_className'])
    m=m.append(dmined[dmined.pr_group!='irrelevant'].merge(derived[['url','prod_file_className']].drop_duplicates(), left_on=['url','classNameAfter'], right_on=['url','prod_file_className']))
    m=m.append(dmined[dmined.pr_group=='irrelevant'])
    m=m.drop_duplicates()
    return m


def filter_mined(mined, with_test_pairs):
    sel=mined[mined['with_test_pairs']==with_test_pairs]
    return sel

def get_refs_per_url(mined, with_test_pairs):
    sel=filter_mined(mined, with_test_pairs)
    return pd.crosstab(sel.url, sel.refactoringType)


def agg_data(mined, with_test_pairs):
    col_name='with_test_pairs' if with_test_pairs else 'without_test_pairs'
    sel=filter_mined(mined, with_test_pairs)
    p=pd.DataFrame(get_refs_per_url(mined, with_test_pairs).agg(np.mean),columns=[col_name])
    p['refactoringType']=p.index
    p.index.name=None
    cnt=sel[['url','refactoringType']].drop_duplicates().groupby('refactoringType').count().reset_index().sort_values('url').rename(columns={'url':col_name+'_cnt'})
    cnt=pd.DataFrame(get_refs_per_url(mined, with_test_pairs).agg(sum),columns=[col_name+'_cnt'])
    cnt['refactoringType']=cnt.index
    cnt.index.name=None
    return pd.DataFrame(p[['refactoringType',col_name]]).merge(pd.DataFrame(cnt[['refactoringType',col_name+'_cnt']]))

def calc_means_and_counts_by_ref_type(mined, min_count=5):
    w1=agg_data(mined, True)
    w2=agg_data(mined, False)
    w=w2.merge(w1,on='refactoringType')
    with_tests_cnt=len(set(mined[mined.test_pairs>0]['prid']))
    without_tests_cnt=len(set(mined[mined.test_pairs==0]['prid']))

    w['significance']=w[['with_test_pairs_cnt','without_test_pairs_cnt']].apply(lambda row: round(proportions_ztest([row[0], row[1]], [with_tests_cnt,without_tests_cnt])[1],4), axis=1)

    w=w[(w.without_test_pairs_cnt>min_count) & (w.with_test_pairs_cnt > min_count)]
    w['ratio']=w['with_test_pairs']/w['without_test_pairs']
    return w.sort_values('ratio')


def plot_means(means):
    melted=pd.melt(means[['refactoringType','without_test_pairs','with_test_pairs','ratio']], id_vars=['refactoringType','ratio'])
    plt.figure(figsize=(16, 6))
    sns.stripplot(data=melted, x='refactoringType',y='value',hue='variable',order=means.sort_values('ratio',ascending=False)['refactoringType'].drop_duplicates())
    plt.xticks(rotation=90)
    plt.ylabel('Frequency per PR')
    plt.xlabel('RefactoringMiner pattern')
    return means

def old_plot_ci_means(mined, means, leg_title):
    a1=get_refs_per_url(mined, True)
    a1['with_tpairs']=True
    a2=get_refs_per_url(mined, False)
    a2['with_tpairs']=False
    a=a1.append(a2)
    melted=pd.melt(a.reset_index(), id_vars=['url','with_tpairs'])
    plt.figure(figsize=(16, 6))
    ax = sns.pointplot(x="variable", y="value", hue="with_tpairs",
                   data=melted[melted.variable.isin(means.refactoringType)],dodge=True,
                   order=means.sort_values('ratio',ascending=False)['refactoringType'],
                   markers=["o", "x"],capsize=.2,
                   linestyles=[" ", " "])
    plt.legend(title=leg_title, loc='upper left')
    plt.xticks(rotation=90)
    plt.ylabel('Frequency per PR')
    plt.xlabel('RefactoringMiner pattern')
    return ax

def as_title(x):
    return (' '.join(x.split('_'))).title()

def plot_ci_means(mined, means, leg_title):
    a1=get_refs_per_url(mined, True)
    a1['with_tpairs']=True
    a2=get_refs_per_url(mined, False)
    a2['with_tpairs']=False
    a=a1.append(a2)
    melted=pd.melt(a.reset_index(), id_vars=['url','with_tpairs'])
    means['refactoringTitle']=means['refactoringType'].apply(as_title)
    melted['variableTitle']=melted['variable'].apply(as_title)
    plt.figure(figsize=(5, 8))
    ax = sns.pointplot(x="value", y="variableTitle", hue="with_tpairs",
                   data=melted[melted.variableTitle.isin(means.refactoringTitle)],dodge=0.2,
                   order=means.sort_values('ratio',ascending=False)['refactoringTitle'],
                   markers=["o", "x"],capsize=.2,
                   linestyles=[" ", " "])
    plt.legend(title=leg_title, loc='upper right')
    plt.xticks(rotation=0)
    plt.xlabel('Frequency per PR')
    plt.ylabel('')
    return ax


def make_clickable(val):
    return '<a href="{}">{}</a>'.format(val,val)

def rows_to_latex(df, header=False,index=True, grey_idx=0):
    lines=df.to_latex(header=header,index=index).split('\n')

    lines=[line for line in lines if not re.match(r'\\begin|\\end|\\toprule|\\bottomrule', line)]
    lines=['\\rowcolor{palegrey}' + x[0]  if x[1] % 2 == grey_idx else x[0] for x in zip(lines,range(len(lines)))]
    return '\n'.join(lines)

def derive_url(x):
    if isinstance(x,str):
        return re.sub(pattern='(.*?github.com/.*?/pull/[0-9]+).*',string=x,repl='\\1')
    return x

def derive_reviewer_id(x):
    if not isinstance(x,str):
        return x
        # names hidden
    if 'fauthor' in x:
        return 'Reviewer1'
    elif 'sauthor' in x:
        return 'Reviewer2'
    elif 'tauthor' in x:
        return 'Reviewer3'
    elif 'author4' in x:
        return 'Reviewer4'
    return x


def import_csv_from_url(url, header='infer'):
    r = requests.get(url)
    data = r.content

    df = pd.read_csv(BytesIO(data),header=header)
    return df

def as_title_sig(row):
    star = ''
    if math.isnan(row[0]) or row[0] < 0.05:
        star = ' *'
    elif row[0] >= 0.5:
        star = ' +'
    return as_title(row[1]) + star

def plot_ci_generic_means(mined, means, pos_title, neg_title):
    a1=get_refs_per_url(mined, True)
    a1['with_tpairs']=True
    a2=get_refs_per_url(mined, False)
    a2['with_tpairs']=False
    a=a1.append(a2)
    melted=pd.melt(a.reset_index(), id_vars=['url','with_tpairs'])
    means['refactoringTitle']=means['refactoringType'].apply(as_title)
    means['refactoringTitleSig']=means[['significance','refactoringType']].apply(as_title_sig, axis=1)

    melted['variableTitle']=melted['refactoringType'].apply(as_title)
    melted['hue']=melted['with_tpairs'].apply(lambda x: pos_title+' (N=' + str(len(a1)) + ')' if x else neg_title + ' (N=' + str(len(a2)) + ')')
    plt.figure(figsize=(5, 12))
    melted=melted.merge(means[['refactoringTitle','refactoringTitleSig']].drop_duplicates(), left_on='variableTitle',right_on='refactoringTitle')
    sel=melted[melted.variableTitle.isin(means.refactoringTitle)]

    ax = sns.pointplot(x="value", y="refactoringTitleSig", hue="hue",
                   data=melted[melted.variableTitle.isin(means.refactoringTitle)],dodge=0.2,
                   order=means.sort_values('ratio',ascending=False)['refactoringTitleSig'],
                   markers=["o", "x"],capsize=.2,
                   linestyles=[" ", " "])
    plt.legend(loc='best',bbox_to_anchor=(0.5, 0.78))
    plt.xticks(rotation=0)
    plt.xlabel('Frequency per PR')
    plt.ylabel('')
    return ax




def reparse_files(): 
    files=get_files('cached') 
    df_split = np.array_split(files, 100) 
    with Pool(7) as p: 
        df=pd.concat(p.map(process_multiple_files, df_split)) 
    df['title_mask']=df.title.apply(lambda x: is_testability_relevant(x)[1])
    df.to_csv('all_prs_with_files.csv',index=False) 
    return df




def process_file(fname, fnproc):
    try:
        text=open(fname).read()
        js=json.loads(text)
        data=js.get('data',{})
        repository=data.get('repository',{})
        if not repository or js.get('errors'):
            return pd.DataFrame()
        nodes=repository.get('pullRequests',{}).get('nodes',[])
        ret=[fnproc(fname,x) for x in nodes]
        if len(ret) > 0:
            return pd.concat(ret)
        else:
            return pd.DataFrame()
    except Exception as e:
        print(fname, e)
        traceback.print_exc(file=sys.stdout)
        return pd.DataFrame()

def nodeProcessor(fname, n, max_changed_files=10):
    if not n.get('files'):
        return pd.DataFrame()
    changed_files = {x.get('path', ''):x for x in n.get('files',{}).get('nodes',[])}
    test_pairs = get_test_pairs(changed_files)
    d=pd.DataFrame()
    items=[]
    if len(test_pairs) > 0 and len(changed_files) < max_changed_files:
        for s,t in test_pairs.items():
            prod_unit = changed_files[s]
            test_unit = changed_files[t]
            if True or test_unit['additions'] > 10:
                items.append({'fname':fname, 
                              'url':n['url'], 
                              'title':n['title'], 
                              'body_mask': is_testability_relevant(n['bodyText'])[1], 
                              'prod_file':s, 
                              'test_file':t, 
                              'test_pairs':len(test_pairs),
                              'changed_files':len(changed_files),
                             'prod_additions': prod_unit['additions'],
                             'test_additions': test_unit['additions'],
                             'prod_deletions': prod_unit['deletions'],
                             'test_deletions': test_unit['deletions']
                             })
    return pd.DataFrame(items)

def process_multiple_files(files, nproc=None):
    if not nproc:
        nproc=nodeProcessor
    return pd.concat([process_file(f, nproc) for f in files])