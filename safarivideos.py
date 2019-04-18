from urllib.parse import urlparse
import time
import shutil
import os
import sys
from bs4 import BeautifulSoup

def title_from_url(url):
    return urlparse(url).path.strip('/').replace('/', '_')

def get_course(toc, fallback_title):
    soup = BeautifulSoup(toc, 'html.parser')
    title = soup.find('meta', property='og:title').get('content', fallback_title)
    return title, soup

def get_lessons(soup):
    return [('{}. {}'.format(ind + 1, l.a.text.strip()).replace("'", "`"), l) for ind, l in enumerate(soup.find_all('li', class_='toc-level-1'))]

def get_videos(lesson):
    return [('{}. {}'.format(ind + 1, a.text.strip()).replace("'", "`"), a.get('href')) for ind, a in enumerate(lesson.ol.find_all('a'))]

def iter_videos(course_soup):
    for l_name, l_soup in get_lessons(course_soup):
        for v_name, v_url in get_videos(l_soup):
            yield l_name, v_name, v_url

def download_command(url, output, username=None, password=None):
    cmd = "youtube-dl -v --output '{}' --write-info-json --write-sub --convert-subs srt -f 'bestvideo[height<=480]+bestaudio/best[height<=480]' {}".format(output, url)
    if username:
        cmd += " -u {}".format(username)
    if password:
        cmd += " -p {}".format(password)
    return cmd

def resume_command(json_file, output):
    return "youtube-dl -v --output '{}' --load-info-json '{}'".format(output, json_file)

def iter_commands(toc, default_title, root_path):
    c_name, c_soup = get_course(toc, default_title)

    for l_name, v_name, v_url in iter_videos(c_soup):
        folder = os.path.join(root_path, c_name, l_name)
        output = os.path.join(folder, v_name + '.mp4')
        json_file = os.path.join(folder, v_name + '.info.json')
        resume_cmd = resume_command(json_file, output)
        download_cmd = download_command(v_url, output)
        yield folder, output, json_file, resume_cmd, download_cmd


if __name__ == '__main__':
    import requests
    import subprocess
    import getopt

    def print_usage():
        print('''safarivideos.py --login <username:password> -cookies <cookies file> --prefix <root path> <video url>''')

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'l:c:p:', ['login=', 'cookies=', 'prefix='])
    except getopt.GetoptError:
        print_usage()
        sys.exit(2)

    url = args[0]

    username, password, cookies_file, prefix = None, None, None, None

    for opt, arg in opts:
        if opt in ("-l", "--login"):
            username, password = arg.split(':', 1)
        elif opt in ("-c", "--cookies"):
            cookies_file = arg
        elif opt in ("-p", "--prefix"):
            prefix = arg

    if cookies_file is None and username is None:
        username, password = filter(None, open(os.path.expanduser('~/.safaribooks'), 'r').read().split())

    if prefix is None:
        prefix = 'Books'

    toc = requests.get(url).text

    for folder, output, json_file, resume_cmd, download_cmd in iter_commands(toc, title_from_url(url), prefix):
        os.makedirs(folder, exist_ok=True)

        if os.path.exists(output):
            continue

        if os.path.exists(json_file):
            subprocess.call(resume_cmd, shell=True)
        else:
            if cookies_file:
                cmd = '{} --cookies {}'.format(download_cmd, cookies_file)
            else:
                cmd = '{} -u {} -p {}'.format(download_cmd, username, password)
            subprocess.call(cmd, shell=True)
        try:
            os.remove(json_file)
        except Exception as e:
            pass

        break