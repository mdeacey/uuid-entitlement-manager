import pytest
from utils import generate_uuid, get_balance, add_credits_manually

def test_generate_uuid():
    user_uuid = generate_uuid()
    assert isinstance(user_uuid, str)

def test_add_credits():
    user_uuid = generate_uuid(starting_credits=0)
    add_credits_manually(user_uuid, 10)
    assert get_balance(user_uuid) == 10
