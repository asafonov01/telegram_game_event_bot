import base64
import hashlib
import json
import os
import random
import string
import struct
import time
import urllib
import uuid

import requests
import xmltodict
from aiohttp import ClientSession
from pymongo import MongoClient
from settings import MONGO_URL, db


class GameHelper:
    def __init__(self, game_id: int, proxy: dict = {}):

        self.proxy = proxy
        self.game_id = game_id
        self.public_key = '85e927bd9203be51dfb40e6f9d245252'
        self.strange_key = None
        self.igg_id = None
        self.access_key = None

    @staticmethod
    def version_packer(version: str):
        v = '{0}{1:0<3d}{2:0<3d}'.format(*map(int, version.split('.')))
        res = struct.pack('<i', int(v))
        return res

    def get_conf(self):
        conf_request = requests.get("http://config-ore.igg.com/appconf/%s/server_config" % self.game_id,
                                    timeout=(5, 6)).content.decode('utf-8')
        return conf_request

    def server_config(self):

        conf_xml = self.get_conf()
        conf = xmltodict.parse(conf_xml)
        return {'login_server': conf['root']['LoginServer'], 'version': conf['root']['Update']['version']}

    def get_login_server(self):
        login_server = (self.server_config()['login_server']['array'][-1])
        login_ip = login_server['IP']
        login_port = login_server['PORT']
        return {'ip': login_ip, 'port': int(login_port)}

    def check_bind(self, m_id):
        return requests.get(
            'http://cgi.igg.com:9000/public/CheckHasBind?m_id=%sld&m_game_id=%s' % (str(m_id), self.game_id)).text

    def complete_login_by_igg(self, token, guest, timeout=(3.05, 10), headers={}):
        key = str(int(time.time()))
        data = guest + self.public_key + key + str(self.game_id)
        md5 = hashlib.md5(data.encode('utf-8'))
        data = md5.hexdigest()

        auth_request = requests.get(
            'http://cgi.igg.com:9000/public/google_plus_login_igg?'
            'm_google_plus_token=%s'
            '&m_guest=%s'
            '&m_key=%s'
            '&m_data=%s'
            '&m_game_id=%s'
            '&keep_time=2592000' % (
                token, urllib.parse.quote_plus(guest), key, data, self.game_id
            ), timeout=timeout, headers=headers)
        resp = str(auth_request.content, encoding='utf-8')
        print(resp)
        try:
            resp_json = json.loads(resp[:-32])['result']['0']
        except KeyError as e:
            print(resp)
            raise e

        self.strange_key = resp[-32:]
        self.igg_id = resp_json['iggid']
        self.access_key = resp_json['access_key']

        if int(resp_json['iggid']) > 0:
            db.igg_guest_old_algo.insert_one(resp_json)

        with open('igg_bots.txt', 'a') as file:
            file.write(f'{self.game_id} {self.igg_id} {self.access_key}\n')

    async def guest_login_by_igg(self, guest, headers={}):
        key = str(int(time.time()))
        data = guest + self.public_key + key
        md5 = hashlib.md5(data.encode('utf-8'))
        data = md5.hexdigest()

        async with ClientSession() as session:
            auth_request = await session.get(
                'http://cgi.igg.com/public/guest_user_login_igg?'
                '&m_guest=%s'
                '&m_key=%s'
                '&m_data=%s' % (
                    urllib.parse.quote_plus(guest), key, data
                ),
                headers=headers)

            resp = str(await auth_request.content.read(), encoding='utf-8')

        resp_json = json.loads(resp[:-32])

        resp_json = resp_json["result"]["0"]

        self.strange_key = resp[-32:]
        self.igg_id = resp_json['iggid']
        self.access_key = resp_json['access_key']
        return resp_json

    def get_version(self):
        conf = self.server_config()
        return self.version_packer(conf['version'])
