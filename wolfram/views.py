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

    r = requests.get(GH + '/repos/' + author + '/' + project + '?client_id=3952eacd7d6ca4eaefba&client_secret=781f37282c64a1b16460ec574066a59ba41eac74')
    metadata['name'] = r.json().get('name')
    metadata['homepage'] = r.json().get('homepage')
    metadata['description'] = r.json().get('description')
    metadata['html_url'] = r.json().get('html_url')
    metadata['forks'] = r.json().get('forks')
    metadata['creation_date'] = r.json().get('created_at')

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


# def get_languages(author, project):
#     r = requests.get('https://api.github.com/repos/' + author + '/' + project + '/languages' + '?client_id=3952eacd7d6ca4eaefba&client_secret=781f37282c64a1b16460ec574066a59ba41eac74')

#     max_bytes = 0
#     for bytes in r.json().values():
#         max_bytes += bytes

#     languages = []
#     language_percents = []
#     for lang, bytes in r.json().iteritems():
#         languages.append(lang)
#         language_percents.append((bytes / float(max_bytes)))

#     languages.reverse()
#     language_percents.reverse()
#     return (language_percents, languages)


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

def get_commit_history(author, project):
    def count_commits(t):
        if t == 'day':
            date_boundary = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        if t == 'week':
            date_boundary = datetime.datetime.utcnow() - datetime.timedelta(days=7)
        if t == 'month':
            date_boundary = datetime.datetime.utcnow() + relativedelta(months=-1)
        date_boundary = date_boundary.isoformat()

        url = 'https://api.github.com/repos/' + author + '/' + project + '/commits?client_id=3952eacd7d6ca4eaefba&client_secret=781f37282c64a1b16460ec574066a59ba41eac74&since=' + date_boundary + '&page=1&per_page=100'

        r = requests.get(url)
        return len(r.json())

    day = count_commits('day')
    week = count_commits('week')
    month = count_commits('month')

    commit_values = [day, week, month]

    total = day + week + month
    try:
        day_percentage = float(day) / total
    except ZeroDivisionError:
        day_percentage = 0
    try:
        week_percentage = float(week) / total
    except ZeroDivisionError:
        week_percentage = 0
    try:
        month_percentage = float(month) / total
    except ZeroDivisionError:
        month_percentage = 0

    commit_percentages = [day_percentage, week_percentage, month_percentage]

    return (commit_percentages, commit_values)

# def get_commit_history(author, project):
#     date_boundary = datetime.datetime.utcnow() - datetime.timedelta(days=1)
#         # date_boundary = datetime.datetime.utcnow() - datetime.timedelta(days=7)
#         # date_boundary = datetime.datetime.utcnow() + relativedelta(months=-1)
#     date_boundary = date_boundary.isoformat()

#     # urls = []
#     url = 'https://api.github.com/repos/' + author + '/' + project + '/commits?client_id=3952eacd7d6ca4eaefba&client_secret=781f37282c64a1b16460ec574066a59ba41eac74&since=' + date_boundary + '&page=1&per_page=100'

#     # service doesn't support more than 1 page because i won't encounter this during the demo

#     # def scrape_urls(url):
#         # r = requests.head(url=url)
#         # if not r.headers['link']:
#             # urls.append(url)
#             # return None
#         # next_page_str_pos = r.headers['link'].find('>; rel="next"')
#         # if next_page_str_pos == -1:
#             # return None
#         # url = r.headers['link'][1:next_page_str_pos]
#         # print url
#         # urls.append(url)
#         # scrape_urls(url)

#     # scrape_urls(url)

#     # for u in urls:
#     r = requests.get(url)
#     commits = len(r.json())
#     return commits


#     # day_data = core_work('day')
#     # week_data = core_work('week')
#     # month_data = core_work('month')

#     # commit_activity_values.append(day_data)
#     # commit_activity_values.append(week_data)
#     # commit_activity_values.append(month_data)

#     # total_data = day_data + week_data + month_data

#     # commit_activity_percentages.append(float(day_data) / total_data)
#     # commit_activity_percentages.append(float(week_data) / total_data)
#     # commit_activity_percentages.append(float(month_data) / total_data)

#     # commit_activity.append(commit_activity_percentages)
#     # commit_activity.append(commit_activity_values)
#     # return commit_activity
