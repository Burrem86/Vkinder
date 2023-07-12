import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id

from config2 import community_token, access_token, db_url_object
from core2 import *

from data_base2 import *

import sqlalchemy as sq
from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import Session
from config2 import db_url_object

metadata = MetaData()
Base = declarative_base()

engine = create_engine(db_url_object)
Base.metadata.create_all(engine)

class BotInterface:
    def __init__(self, community_token, access_token):
        self.vk = vk_api.VkApi(token=community_token)
        self.longpoll = VkLongPoll(self.vk)
        self.vk_tools = VkTools(community_token, access_token)
        self.params = {}
        self.worksheets = []
        self.offset = 0
        self.worksheet_checked = {}

    def message_send(self, user_id, message, attachment=None):
        self.vk.method('messages.send',
                       {'user_id': user_id,
                        'message': message,
                        'attachment': attachment,
                        'random_id': get_random_id()
                        }
                       )

    def worksheet_send(self, event, worksheet_checked):
        photos = self.vk_tools.get_photos(self.worksheet_checked['id'])
        photo_string = ''
        for photo in photos:
            photo_string += f'photo{photo["owner_id"]}_{photo["id"]},'
        
        self.message_send(
                        event.user_id,
                        f'Имя: {self.worksheet_checked["name"]} ссылка: vk.com/id{self.worksheet_checked["id"]}',
                        attachment=photo_string
                    )

    def process_search(self, event, params, offset):
        self.worksheets = self.vk_tools.search_worksheet(
                        self.params, self.offset
                        )
        self.offset += 10
        worksheet = self.worksheets.pop()
        while check_user(engine, event.user_id, worksheet["id"]) is True:
            if len(self.worksheets) != 0:
                worksheet = self.worksheets.pop()
                continue
            else:
                self.process_search(event, self.params, self.offset)
        else:
            self.worksheet_checked = worksheet

    def event_handler(self):
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                if event.text.lower() == 'привет':
                    self.params = self.vk_tools.get_profile_info(event.user_id)

                elif event.text.lower() == 'поиск':
                    self.message_send(event.user_id, 'Начинаем поиск')
                    self.process_search(event, self.params, self.offset)
                    self.worksheet_send(event, self.worksheet_checked["id"])
                    add_user(engine, event.user_id, self.worksheet_checked["id"])

                elif event.text.lower() == 'пока':
                    self.message_send(
                                    event.user_id,
                                    f'До скорых встреч, {self.params["name"]}'
                                    )

if __name__ == '__main__':
    bot_interface = BotInterface(community_token, access_token)
    bot_interface.event_handler()



