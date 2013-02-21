from flask import request, render_template, make_response, redirect
from wolfram import app
import requests
from base64 import b64decode
from urllib import quote
from bs4 import BeautifulSoup
import datetime
from dateutil.relativedelta import relativedelta
import dateutil.parser
import datetime


GH = 'https://api.github.com'
CLIENT_SECRET = app.config['CLIENT_SECRET']


@app.route('/', methods=['GET'])
def home():
    return render_template('home.html')


@app.route('/s/', methods=['POST'])
def search():
    if not request.form['search_query']:
        return make_response('error: no query')
    return redirect('/s/' + request.form['search_query'])


def get_project(query):
    r = requests.get('https://api.github.com/legacy/repos/search/' + query + '?client_id=3952eacd7d6ca4eaefba&client_secret=' + CLIENT_SECRET)

    author = r.json().get('repositories')[0].get('owner')
    project = r.json().get('repositories')[0].get('name')

    return (author, project)


@app.route('/s/<query>/', methods=['GET'])
def search_results(query):
    project = get_project(query)

    metadata = get_general_metadata(*project)
    wikipedia_url = get_wikipedia_url(project[1])
    languages = get_languages(*project)
    license = get_license(*project)
    commits = get_commit_history(project[0], project[1])

    return render_template('results.html',
                           metadata=metadata,
                           languages=languages,
                           license=license,
                           wikipedia_url=wikipedia_url,
                           commits=commits)


@app.route('/s/<author>/<project>/', methods=['GET'])
def specific_search_results(author, project):
    project = (author, project)

    metadata = get_general_metadata(*project)
    wikipedia_url = get_wikipedia_url(project[1])
    languages = get_languages(*project)
    license = get_license(*project)
    commits = get_commit_history(project[0], project[1])

    return render_template('results.html',
                           metadata=metadata,
                           languages=languages,
                           license=license,
                           wikipedia_url=wikipedia_url,
                           commits=commits)

# Description API


def get_general_metadata(author, project):
    metadata = {}

    r = requests.get(GH + '/repos/' + author + '/' + project + '?client_id=3952eacd7d6ca4eaefba&client_secret=' + CLIENT_SECRET)
    metadata['name'] = r.json().get('name')
    metadata['homepage'] = r.json().get('homepage')
    metadata['description'] = r.json().get('description')
    metadata['html_url'] = r.json().get('html_url')
    metadata['forks'] = r.json().get('forks')
    metadata['creation_date'] = dateutil.parser.parse(r.json().get('created_at')).strftime('%m/%d/%y')
    return metadata


def get_wikipedia_url(project):
    keywords = ['server', 'framework', 'programming', 'open source']

    # r = requests.Session()
    # r.headers.update({'User-Agent': 'ghbot by randall@randallma.com'})
    r = requests.get('https://en.wikipedia.org/w/api.php?action=query&redirects&prop=revisions&rvprop=content&format=xml&titles=' + quote(project))

    if 'disambiguation' in r.text:
        # r2 = requests.Session()
        # r2.headers.update({'User-Agent': 'ghbot by randall@randallma.com'})
        r2 = requests.get('https://en.wikipedia.org/wiki/' + quote(project) + '?client_id=3952eacd7d6ca4eaefba&client_secret=' + CLIENT_SECRET)

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
    r = requests.get('https://api.github.com/repos/' + author + '/' + project + '/languages' + '?client_id=3952eacd7d6ca4eaefba&client_secret=' + CLIENT_SECRET)

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

    r = requests.get(GH + '/repos/' + author + '/' + project + '/contents' + '?client_id=3952eacd7d6ca4eaefba&client_secret=' + CLIENT_SECRET)
    for f in r.json():
        if 'license' in f.get('name').lower():
            r2 = requests.get(GH + '/repos/' + author + '/' + project + '/contents/' + f.get('name') + '?client_id=3952eacd7d6ca4eaefba&client_secret=' + CLIENT_SECRET)
            license = b64decode(r2.json().get('content') + '?client_id=3952eacd7d6ca4eaefba&client_secret=' + CLIENT_SECRET)
            if check_license(license):
                return check_license(license)

        if 'readme' in f.get('name').lower():
            r2 = requests.get(GH + '/repos/' + author + '/' + project + '/contents/' + f.get('name') + '?client_id=3952eacd7d6ca4eaefba&client_secret=' + CLIENT_SECRET)
            license = b64decode(r2.json().get('content') + '?client_id=3952eacd7d6ca4eaefba&client_secret=' + CLIENT_SECRET)
            if check_license(license):
                return check_license(license)

    return 'Unknown'


# Repo Activity API

def get_commit_history(author, project):

    class CommitCount(object):
        def __init__(self):
            self.day_count = 0
            self.week_count = 0
            self.month_count = 0

        def setup_commit_count_query(self, t):
            if t == 'day':
                date_boundary = datetime.datetime.utcnow() - datetime.timedelta(days=1)
            if t == 'week':
                date_boundary = datetime.datetime.utcnow() - datetime.timedelta(days=7)
            if t == 'month':
                date_boundary = datetime.datetime.utcnow() + relativedelta(months=-1)
            date_boundary = date_boundary.isoformat()

            url = 'https://api.github.com/repos/' + author + '/' + project + '/commits?client_id=3952eacd7d6ca4eaefba&client_secret=' + CLIENT_SECRET + '&since=' + date_boundary + '&page=1&per_page=100'

            return url

        # TODO: fix edge case of day/weeks with >100 commits
        def count_paginated_commits(self, request):
            try:
                url = request.links['next']['url']
                self.month_count += 100
                self.count_paginated_commits(requests.head(url=url))
            except KeyError:
                r = requests.get(request.url)
                self.month_count += len(r.json())

    cc = CommitCount()

    day_query = cc.setup_commit_count_query('day')
    day_r = requests.get(day_query)
    cc.day_count = len(day_r.json())

    week_query = cc.setup_commit_count_query('week')
    week_r = requests.get(week_query)
    cc.week_count = len(week_r.json())

    month_query = cc.setup_commit_count_query('month')
    month_r = requests.head(url=month_query)
    if not month_r.links:
        month_r = requests.get(month_query)
        cc.month_count = len(month_r.json())
    else:
        cc.count_paginated_commits(month_r)

    commit_values = [cc.day_count, cc.week_count, cc.month_count]
    total = cc.day_count + cc.week_count + cc.month_count

    try:
        day_percentage = float(cc.day_count) / total
    except ZeroDivisionError:
        day_percentage = 0
    try:
        week_percentage = float(cc.week_count) / total
    except ZeroDivisionError:
        week_percentage = 0
    try:
        month_percentage = float(cc.month_count) / total
    except ZeroDivisionError:
        month_percentage = 0

    commit_percentages = [day_percentage, week_percentage, month_percentage]

    return (commit_percentages, commit_values)
