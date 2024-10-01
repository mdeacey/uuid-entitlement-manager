import requests

class CreditManagerSDK:
    def __init__(self, base_url):
        self.base_url = base_url

    def create_user(self):
        response = requests.post(f'{self.base_url}/api/user')
        return response.json()

    def get_balance(self, user_uuid):
        response = requests.get(f'{self.base_url}/api/user/{user_uuid}/balance')
        return response.json()

    def add_credits(self, user_uuid, credits):
        response = requests.post(f'{self.base_url}/api/user/{user_uuid}/add_credits', json={'credits': credits})
        return response.json()
