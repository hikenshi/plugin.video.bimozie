# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
from utils.mozie_request import Request
from utils.aes import CryptoAES
import utils.xbmc_helper as helper
import re
import json


def from_char_code(*args):
    return ''.join(map(chr, args))


class Parser:
    key = "PhimMoi.Net@"

    def get(self, response, skipEps=False):
        movie = {
            'group': {},
            'episode': [],
            'links': [],
        }
        soup = BeautifulSoup(response, "html.parser")

        # get episode if possible
        servers = soup.select('div.list-server > div.server')
        if skipEps is False and len(servers) > 0:
            print("***********************Get Movie Episode*****************************")
            found = False
            items = self.get_server_list(servers)
            if items is not None and len(items) > 0:
                movie['group'] = items
                found = True
            else:
                found = False
            if found is False:
                servers = soup.select('ul.server-list > li.backup-server')
                movie['group'] = self.get_server_list(servers)

        else:
            print("***********************Get Movie Link*****************************")
            url = self.get_token_url(response)
            response = Request().get(url)

            self.key = self.get_decrypt_key(response)
            jsonresponse = re.search("_responseJson='(.*)';", response).group(1)
            jsonresponse = json.loads(jsonresponse.decode('utf-8'))

            if jsonresponse['medias']:
                media = sorted(jsonresponse['medias'], key=lambda elem: elem['resolution'], reverse=True)
                for item in media:
                    # if item['resolution'] <= 480: continue
                    url = CryptoAES().decrypt(item['url'], bytes(self.key.encode('utf-8')))
                    movie['links'].append({
                        'link': url,
                        'title': 'Link %s' % item['resolution'],
                        'type': item['resolution'],
                        'resolve': True
                    })
            elif jsonresponse['embedUrls']:
                for item in jsonresponse['embedUrls']:
                    url = CryptoAES().decrypt(item, bytes(self.key.encode('utf-8')))
                    if not re.search('hydrax', url):
                        movie['links'].append({
                            'link': url,
                            'title': 'Link Unknow',
                            'type': 'Unknow',
                            'resolve': False
                        })
                    # else:
                    #     movie['links'].append({
                    #         'link': self.get_hydrax(url),
                    #         'title': 'Link 720p',
                    #         'type': '720p',
                    #         'resolve': False
                    #     })
        return movie

    def get_server_list(self, servers):
        items = {}
        for server in servers:
            if server.select_one('h3') is not None:
                server_name = server.select_one('h3').text.strip().replace("\n", "").encode('utf-8')
            else:
                return None

            if server_name not in items: items[server_name] = []

            if len(server.select('ul.list-episode li a')) > 0:
                for episode in server.select('ul.list-episode li a'):
                    items[server_name].append({
                        'link': episode.get('href'),
                        'title': episode.get('title').encode('utf-8'),
                    })

        return items

    def search_tokenize(self, response):
        m = re.search("eval\(.*\);}\('(.*)','(.*)','(.*)','(.*)'\)\);", response)
        a = self.decode_token(m.group(1), m.group(2), m.group(3), m.group(4))
        m = re.search("join\(''\);}\('(.*)','(.*)','(.*)','(.*)'\)\);$", a)
        a = self.decode_token(m.group(1), m.group(2), m.group(3), m.group(4))
        m = re.search("join\(''\);}\('(.*)','(.*)','(.*)','(.*)'\)\);$", a)
        a = self.decode_token(m.group(1), m.group(2), m.group(3), m.group(4))
        return a

    def get_decrypt_key(self, response):
        a = self.search_tokenize(response)
        return re.search("setDecryptKey\('(.*)'\);watching", a).group(1)

    def get_token_url(self, response):
        a = self.search_tokenize(response)
        return re.search("'url':'(.*)','method'", a).group(1).replace("ip='+window.CLIENT_IP+'&", "")

    def decode_token(self, w, i, s, e):
        a = 0
        b = 0
        c = 0
        string1 = []
        string2 = []
        string_len = len(w + i + s + e)

        while True:
            if a < 5:
                string2.append(w[a])
            else:
                if a < len(w):
                    string1.append(w[a])
            a += 1
            if b < 5:
                string2.append(i[b])
            else:
                if b < len(i):
                    string1.append(i[b])
            b += 1
            if c < 5:
                string2.append(s[c])
            else:
                if c < len(s):
                    string1.append(s[c])
            c += 1
            if string_len == len(string1) + len(string2) + len(e):
                break

        raw_string1 = ''.join(string1)
        raw_string2 = ''.join(string2)
        b = 0
        result = []
        for a in range(0, len(string1), 2):
            ll11 = -1
            if ord(raw_string2[b]) % 2: ll11 = 1
            part = raw_string1[a:a + 2]
            result.append(from_char_code(int(part, 36) - ll11))
            b += 1
            if b >= len(string2):
                b = 0

        return ''.join(result)

    def get_hydrax(self, url):
        return "C:\\Users\\Billy Nguyen\\AppData\\Roaming\\Kodi\\userdata\\addon_data\\plugin.video.bimozie\\phimmoi.m3u8"
        response = Request().get(url)
        id = re.search('"key":"(.*?)",', response).group(1)
        params = {
            'key': id,
            'type': 'slug',
            'value': re.search('#slug=(.*)', url).group(1)
        }
        response = Request().post('https://multi.hydrax.net/vip', params, {
            'Origin': 'http://www.phimmoi.net',
            'Referer': 'http://www.phimmoi.net/hydrax.html'
        })

        response = json.loads(response)
        if response['hd']:
            response = response['hd']
            i, j = 0, 0
            playlist = '''#EXTM3U
#EXT-X-VERSION:4
#EXT-X-PLAYLIST-TYPE:VOD
#EXT-X-TARGETDURATION:%s
#EXT-X-MEDIA-SEQUENCE:0
''' % response['duration']

            for ranges in response['multiRange']:
                for range in ranges:
                    playlist += "#EXTINF:%s,\n" % response['extinf'][i]
                    playlist += "#EXT-X-BYTERANGE:%s\n" % range
                    url = "%s/%s/%s" % (
                        'http://immortal.hydrax.net', response['expired'], response['multiData'][j]['file'])
                    url = self.fetch_hydrax_link(url)
                    playlist += "%s\n" % url
                    i += 1
                j += 1

        playlist += "#EXT-X-ENDLIST"
        return helper.write_file('phimmoi.m3u8', playlist)

    last_url = None
    last_respone = None

    def fetch_hydrax_link(self, url):
        if url == self.last_url: return self.last_respone
        self.last_url = url
        text = Request().post(url, {}, {
            'Origin': 'http://www.phimmoi.net',
            'Referer': 'http://www.phimmoi.net/hydrax.html'
        })
        self.last_respone = re.search('"url":"(.*?)"', text).group(1)
        return self.last_respone
