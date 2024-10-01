import click
from utils import generate_uuid, get_balance, add_balance_manually

@click.group()
def cli():
    pass

@cli.command()
def create_user():
    user_uuid = generate_uuid(starting_balance=10)
    click.echo(f'User created with UUID: {user_uuid}')

@cli.command()
@click.argument('user_uuid')
def balance(user_uuid):
    balance = get_balance(user_uuid)
    click.echo(f'User {user_uuid} has {balance} balance.')

@cli.command()
@click.argument('user_uuid')
@click.argument('balance', type=int)
def add_balance(user_uuid, balance):
    add_balance_manually(user_uuid, balance)
    click.echo(f'Added {balance} balance to user {user_uuid}.')

if __name__ == '__main__':
    cli()
