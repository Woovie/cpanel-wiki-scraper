#!/usr/bin/env python3.6
import language_check, requests, json, configparser, os.path, re
from bs4 import BeautifulSoup as bs
from bs4.element import Comment
from bs4 import SoupStrainer

config = configparser.ConfigParser()

config.read('settings.ini')

ver = config['scrape']['ver']

print(f'===================\ncPanel Documentation URL Gatherer and Spellchecker v{ver}\nWritten by Jordan Banasik <woovie@woovie.net>\nSupport open source software!\nSource code on https://github.com/woovie/cpanel-wiki-scraper\n===================\n')

masterURL = config['scrape']['url']
jsonFile = config['scrape']['fileout']
if os.path.isfile(jsonFile):
    jsonData = open(jsonFile, 'r')
    jsonLinks = json.load(jsonData)
links = []
problemURLs = {}

grammarTool = language_check.LanguageTool('en-US')

def tag_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    if isinstance(element, Comment):
        return False
    return True

def text_from_html(body):
    soup = bs(body, 'html.parser')
    texts = soup.find(id="main").findAll(text=True)
    visible_texts = filter(tag_visible, texts)  
    return u" ".join(t.strip() for t in visible_texts)

def check_grammar(text):
    return grammarTool.check(text)

def checkURL(url):
    print(f"URL: {url}\n===================\n")
    texts = text_from_html(requests.get(url).content)
    for match in check_grammar(texts):
        if not texts[match.fromx:match.tox] == 'cPanel' and not match.ruleId == 'WHITESPACE_RULE' and not texts[match.fromx:match.tox].lower == 'whm':
            print(f"Rule: {match.ruleId}\nRecommendations: {match.replacements}\nLocation: {match.fromx}:{match.tox}\n...{texts[match.fromx-10:match.tox+10]}...\n")
    print(f"End URL {url}\n===================\n")

def findURLs(url):
    if url.startswith('/display/'):
        url = f"{masterURL}{url}"
    print(f"searching {url}...")
    page = requests.get(url)
    linkContain = []
    for link in bs(page.content, 'html.parser', parse_only=SoupStrainer('a')):
        if link.has_attr('href'):
            link = link['href']
            if not 'atlassian' in link:
                if 'documentation.cpanel.net' in link:
                    if not 'direct_links' in problemURLs:
                        problemURLs['direct_links'] = {}
                    problemURLs['direct_links'][url] = link
                    print(f'*** WARNING *** Direct URL found! Parent: {url} URL: {link}\n')
                if link.startswith('http://'):
                    if not 'insecure' in problemURLs:
                        problemURLs['insecure'] = {}
                    problemURLs['insecure'][url] = link
                    print(f'*** WARNING *** Insecure URL found! Parent: {url} URL: {link}\n')
            if 'documentation.cpanel.net' in link or link.startswith('/display/'):
                if '%3A' in link:
                    link = link.split('%3A')[0]
                if link.startswith('/display/'):
                    link = f"https://documentation.cpanel.net{link}"
                if not link in links:
                    print(f'===================\nStoring {link}\n===================\n')
                    links.append(link)
                    linkContain.append(link)
    return linkContain

def parseURLs(linkList):
    if len(linkList) > 0:
        for link in linkList:
            parseURLs(findURLs(link))

def urlGather():
    print('Beginning URL gatherer subroutine')
    if jsonLinks:
        global links
        links = jsonLinks
        print(f'Existing JSON data found with {len(links)} URLs, using data for comparison.')
        parseURLs(links)
    else:
        print('No initial link file found, building fresh.')
        parseURLs(findURLs(masterURL))
    if jsonLinks:
        print('Gatherer subroutine complete.\nOriginal data: {len(jsonLinks)}\nNew data: {len(links)}')
        if len(links) > len(jsonLinks):
            print(f'Change detected, storing data to {jsonFile}.')
            f = open(jsonFile, 'w')
            f.write(json.dumps(links))
        else:
            print(f'No changes, not writing out to file {jsonFile}.')
    print('Completed with URL gathering.')
    if problemURLs > 0:
        print('The following problems were found:')
        for problemType in problemURLs:
            if problemType == 'insecure':
                print('* Insecure links:')
                for parentURL in problemURLs[problemType]:
                    badURL = problemURLs[problemType][parentURL]
                    newURL = badURL.replace("http", "https")
                    print(f'  * On page: {parentURL}\n    Original: {badURL}\n    Recommendation: {newURL}')
            if problemType == 'direct_links':
                print('* Direct links:')
                for parentURL in problemURLs[problemType]:
                    badURL = problemURLs[problemType][parentURL]
                    newURL = re.sub('https?://documentation.cpanel.net', '', badURL)
                    print(f'  * On page: {parentURL}\n    Original: {badURL}\n    Recommendation: {newURL}')
    print('Complete!')

urlGather()
