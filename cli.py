import click
from utils import generate_uuid, get_balance, add_credits_manually

@click.group()
def cli():
    pass

@cli.command()
def create_user():
    user_uuid = generate_uuid(starting_credits=10)
    click.echo(f'User created with UUID: {user_uuid}')

@cli.command()
@click.argument('user_uuid')
def balance(user_uuid):
    credits = get_balance(user_uuid)
    click.echo(f'User {user_uuid} has {credits} credits.')

@cli.command()
@click.argument('user_uuid')
@click.argument('credits', type=int)
def add_credits(user_uuid, credits):
    add_credits_manually(user_uuid, credits)
    click.echo(f'Added {credits} credits to user {user_uuid}.')

if __name__ == '__main__':
    cli()
