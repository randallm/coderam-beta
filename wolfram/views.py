from flask import request, render_template, make_response, redirect
from wolfram import app
import requests
from base64 import b64decode
from urllib import quote
from bs4 import BeautifulSoup
import datetime
from dateutil.relativedelta import relativedelta


GH = 'https://api.github.com'


@app.route('/', methods=['GET'])
def home():
    return render_template('home.html')


@app.route('/s/', methods=['POST'])
def search():
    if not request.form['search_query']:
        return make_response('error: no query')
    return redirect('/s/' + request.form['search_query'])


def get_project(query):
    r = requests.get('https://api.github.com/legacy/repos/search/' + query + '?client_id=3952eacd7d6ca4eaefba&client_secret=781f37282c64a1b16460ec574066a59ba41eac74')

    author = r.json().get('repositories')[0].get('owner')
    project = r.json().get('repositories')[0].get('name')

    return (author, project)


@app.route('/s/<query>/', methods=['GET'])
def search_results(query):
    project = get_project(query)

    languages = get_languages(*project)
    license = get_license(*project)

    return render_template('results.html', languages=languages, license=license)


# Description API


def get_general_metadata(author, project):
    metadata = []

    r = requests.get(GH + '/repos/' + author + '/' + project + '?client_id=3952eacd7d6ca4eaefba&client_secret=781f37282c64a1b16460ec574066a59ba41eac74')
    metadata.append(('description', r.json().get('description')))
    metadata.append(('html_url', r.json().get('html_url')))
    metadata.append(('forks', r.json().get('forks')))
    metadata.append(('creation_date', r.json().get('created_at')))

    return metadata


def get_wikipedia_url(project):
    keywords = ['server', 'framework', 'programming', 'open source']

    # r = requests.Session()
    # r.headers.update({'User-Agent': 'ghbot by randall@randallma.com'})
    r = requests.get('https://en.wikipedia.org/w/api.php?action=query&redirects&prop=revisions&rvprop=content&format=xml&titles=' + quote(project))

    if 'disambiguation' in r.text:
        # r2 = requests.Session()
        # r2.headers.update({'User-Agent': 'ghbot by randall@randallma.com'})
        r2 = requests.get('https://en.wikipedia.org/wiki/' + quote(project) + '?client_id=3952eacd7d6ca4eaefba&client_secret=781f37282c64a1b16460ec574066a59ba41eac74')

        soup = BeautifulSoup(r2.text)
        links = soup.find_all('a')

        for link in links:
            for keyword in keywords:
                if keyword in str(link):
                    return 'https://en.wikipedia.org' + link['href']

    for keyword in keywords:
        if keyword in r.text:
            return 'https://en.wikipedia.org/wiki/' + quote(project)
    return False


def get_languages(author, project):
    r = requests.get('https://api.github.com/repos/' + author + '/' + project + '/languages' + '?client_id=3952eacd7d6ca4eaefba&client_secret=781f37282c64a1b16460ec574066a59ba41eac74')

    max_bytes = 0
    for bytes in r.json().values():
        max_bytes += bytes

    languages = {}
    for lang, bytes in r.json().iteritems():
        languages[lang] = (bytes / float(max_bytes)) * 100

    return languages


def get_license(author, project):
    def check_license(license):
        if 'GNU Lesser General Public License' in license:
            return 'LGPL'
        elif 'GNU General Public License' in license:
            return 'GPL'
        elif 'Permission to use, copy, modify, and/or distribute this software for any purpose with or without fee is hereby granted, provided that the above copyright notice and this permission notice appear in all copies.' in license:
            return 'ISC'
        elif 'Redistribution and use in source and binary forms, with or without' in license:
            return 'BSD'
        elif 'Permission is hereby granted, free of charge, to any person obtaining' in license:
            return 'MIT'
        elif 'Apache License' in license:
            return 'Apache 2.0'
        elif 'Version 2.0' in license:
            return 'Apache 2.0'
        elif 'Artistic License 2.0' in license:
            return 'Artistic'
        else:
            return False

    r = requests.get(GH + '/repos/' + author + '/' + project + '/contents' + '?client_id=3952eacd7d6ca4eaefba&client_secret=781f37282c64a1b16460ec574066a59ba41eac74')
    for f in r.json():
        if 'license' in f.get('name').lower():
            r2 = requests.get(GH + '/repos/' + author + '/' + project + '/contents/' + f.get('name') + '?client_id=3952eacd7d6ca4eaefba&client_secret=781f37282c64a1b16460ec574066a59ba41eac74')
            license = b64decode(r2.json().get('content') + '?client_id=3952eacd7d6ca4eaefba&client_secret=781f37282c64a1b16460ec574066a59ba41eac74')
            if check_license(license):
                return check_license(license)

        if 'readme' in f.get('name').lower():
            r2 = requests.get(GH + '/repos/' + author + '/' + project + '/contents/' + f.get('name') + '?client_id=3952eacd7d6ca4eaefba&client_secret=781f37282c64a1b16460ec574066a59ba41eac74')
            license = b64decode(r2.json().get('content') + '?client_id=3952eacd7d6ca4eaefba&client_secret=781f37282c64a1b16460ec574066a59ba41eac74')
            if check_license(license):
                return check_license(license)

    return 'Unknown'


# Repo Activity API

def get_commit_history(author, project, commit_since):
    if commit_since == 'week':
        date_boundary = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    elif commit_since == 'month':
        date_boundary = datetime.datetime.utcnow() + relativedelta(months=-1)
    elif commit_since == '6mo':
        date_boundary = datetime.datetime.utcnow() + relativedelta(months=-6)
    date_boundary = date_boundary.isoformat()

    urls = []
    url = 'https://api.github.com/repos/' + author + '/' + project + '/commits?client_id=3952eacd7d6ca4eaefba&client_secret=781f37282c64a1b16460ec574066a59ba41eac74&since=' + date_boundary + '&page=1&per_page=100'

    def scrape_urls(url):
        r = requests.head(url=url)
        if not r.headers['link']:
            urls.append(url)
            return None
        next_page_str_pos = r.headers['link'].find('>; rel="next"')
        if next_page_str_pos == -1:
            return None
        url = r.headers['link'][1:next_page_str_pos]
        urls.append(url)
        scrape_urls(url)

    scrape_urls(url)

    # demons lie below this line:

    commits = 0
    commit_authors = []

    for u in urls:
        r = requests.get(u)

        commits += len(r.json())

        # for commit in r.json():
        #     commit_author = commit.get('author')
        #     commit_author = commit_author.get('login')
        #     if commit_author not in commit_authors:
        #         commit_authors.append(commit_author)

    # return commits, commit_authors

    return commits

    # for u in urls:
        # r = requests.get(u)
    #     new_latest_commit_hash = r.json()[0].get('sha')
    #     # github api doesn't error out if you pick a page that doesn't exist
    #     if latest_commit_hash == new_latest_commit_hash:
    #         return (commits, len(commit_authors))

    #     latest_commit_hash = new_latest_commit_hash

    #     commits += len(r.json())
    #     for commit in r.json():
    #         commit_author = commit.get('author')
    #         commit_author = commit.get('login')
    #         if commit_author not in commit_authors:
    #             commit_authors.append(commit_author)

    #     else:
    #         return (commits, len(commit_authors))
