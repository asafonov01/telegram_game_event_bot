import requests

from settings import MONOBANK_TOKEN

if __name__ == '__main__':
    r = requests.post('https://api.monobank.ua/personal/webhook',
                  json={
                      "webHookUrl": "http://51.195.203.27:25024/monobank_payment_callback_ak4nfGK27h07"
                  }, headers={'X-Token': MONOBANK_TOKEN})
    print(r.text)
