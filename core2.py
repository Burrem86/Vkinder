from pprint import pprint
from datetime import datetime

import vk_api
from vk_api.exceptions import ApiError
from vk_api.utils import get_random_id
from vk_api.longpoll import VkLongPoll, VkEventType

from config2 import access_token, community_token

class VkTools:
    def __init__(self, community_token, access_token):
        self.vkapi = vk_api.VkApi(token=access_token)
        self.vkapi_send = vk_api.VkApi(token=community_token)
        self.longpoll = VkLongPoll(self.vkapi_send)

    def _bdate_toyear(self, bdate):
        user_year = bdate.split('.')[2]
        now = datetime.now().year
        return now - int(user_year)

    def get_profile_info(self, user_id):
        info_data = {"name": "ФИО", "city": "Город"}
        try:
            info, = self.vkapi.method('users.get', {'user_id': user_id, 'fields': 'city, sex, bdate, relation'})
        except ApiError as e:
            info = {}
            print(f'error = {e}')

        result = {'name': (info['first_name'] + ' ' + info['last_name']) if 'first_name' in info and 'last_name' in info else None,
                  'sex': info.get('sex'),
                  'city': info.get('city')['title'] if info.get('city') is not None else None,
                  'year': self._bdate_toyear(info.get('bdate')),
                  'user_id': user_id
                  }

        self.vkapi_send.method('messages.send',
                                  {'user_id': user_id,
                                   'message': f'Привет, {result["name"]}',
                                   'attachment': [],
                                   'random_id': get_random_id()
                                   }
                                  )

        for k, v in result.items():
            if k in info_data and v is None:
                self.vkapi_send.method('messages.send',
                                  {'user_id': user_id,
                                   'message': f"У вас не указан {info_data[k]}, напишите его пожалуйста",
                                   'attachment': [],
                                   'random_id': get_random_id()
                                   }
                                  )

                for event in self.longpoll.listen():
                    if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text.lower() not in ['привет', 'поиск']:
                        result[k] = event.text.capitalize()
                        self.vkapi_send.method('messages.send',
                                  {'user_id': user_id,
                                   'message': 'Можем начинать поиск анкет! Введите команду: поиск',
                                   'attachment': [],
                                   'random_id': get_random_id()
                                   }
                                  )
                        break

        return result

    def search_worksheet(self, params, offset):
        try:
            users = self.vkapi.method('users.search',
                                      {
                                          'count': 10,
                                          'offset': offset,
                                          'hometown': params['city'],
                                          'sex': 1 if params['sex'] == 2 else 2,
                                          'has_photo': True,
                                          'age_from': params['year'] - 3,
                                          'age_to': params['year'] + 3
                                      }
                                      )
        except ApiError as e:
            users = []
            print(f'error = {e}')

        result = [
            {
                'name': item['first_name'] + ' ' + item['last_name'],
                'id': item['id']
            } for item in users['items'] if item['is_closed'] is False
        ]

        return result

    def get_photos(self, id):
        try:
            photos = self.vkapi.method('photos.get',
                                       {'owner_id': id,
                                        'album_id': 'profile',
                                        'extended': 1
                                        }
                                       )
        except ApiError as e:
            photos = {}
            print(f'error = {e}')

        result = [{'owner_id': item['owner_id'],
                   'id': item['id'],
                   'likes': item['likes']['count'],
                   'comments': item['comments']['count'],
                   'a': item['likes']['count'] + item['comments']['count']
                   } for item in photos['items']
                  ]

        return sorted(result[:3], key=lambda dict: dict['a'], reverse=True)

if __name__ == '__main__':
    user_id = 106475323
    tools = VkTools(community_token, access_token)
    params = tools.get_profile_info(user_id)
    worksheets = tools.search_worksheet(params, 10)
    worksheet = worksheets.pop()
    photos = tools.get_photos(worksheet['id'])

    pprint(params)
