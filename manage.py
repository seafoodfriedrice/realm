import json
from os import environ
from getpass import getpass
from datetime import date

from werkzeug.security import generate_password_hash
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand

from realm import app
from realm.database import Base, session
from realm.models import Domain, Provider, Category
from realm.models import Status, WebUser, CategoryName

manager = Manager(app)


@manager.command
def run():
    port = int(environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)


@manager.command
def seed():
    # Create all the available category names
    for name in ['unassigned', 'alpha', 'bravo', 'charlie',
                 'delta', 'echo', 'foxtrot']:
        category_name = CategoryName(name=name)
        session.add(category_name)
        session.commit()

    # Get the alpha CategoryName object
    alpha = session.query(CategoryName).filter(
        CategoryName.name == "alpha").first()

    def add_domain(domain_name, ip, provider_url, status_type):
        domain = Domain(domain_name=domain_name, ip=ip)
        category = Category()
        domain.category = category
        domain.category.category_name = alpha
        status = Status(status_type=status_type)
        provider = Provider(provider_url=provider_url)
        domain.status.append(status)
        provider.domains.append(domain)
        domain.is_active = True
        domain.is_monitored = True
        domain.exp_date = date.today()
        session.add(domain)
        session.commit()

    add_domain("google-public-dns-a.google.com", "8.8.8.8",
               "google.com", "added")
    add_domain("google-public-dns-b.google.com.com", "8.8.4.4",
               "google.com", "added")
    add_domain("resolver1.opendns.com", "208.67.222.222",
               "opendns.com", "added")


@manager.command
def import_domains_csv():
    unassigned = session.query(CategoryName).filter(
        CategoryName.name == "unassigned").first()
    if not unassigned:
        unassigned = CategoryName(name="unassigned")
        session.add(unassigned)
        session.commit()

    with open("realm_domains.csv") as file:
        for line in file:
            domain_name, ip, provider_url, _ = line.split(',')

            domain = Domain(domain_name=domain_name, ip=ip)
            status = Status(status_type="added")
            domain.status.append(status)

            provider = session.query(Provider).filter(
                Provider.provider_url == provider_url).first()
            if not provider:
                provider = Provider(provider_url=provider_url)

            provider.domains.append(domain)

            session.add(domain)
            session.commit()


@manager.command
def import_domains_json():
    for name in ['unassigned', 'alpha', 'bravo', 'charlie',
                 'delta', 'echo', 'foxtrot']:
        category_name = CategoryName(name=name)
        session.add(category_name)
        session.commit()

    unassigned = session.query(CategoryName).filter(
        CategoryName.name == "unassigned").first()

    with open("/root/realm_domains-20150528.json", 'r') as file:
        domains = json.load(file)

    for domain in domains:
        domain_name = domain["domain_name"]
        ip = domain["ip"]
        provider_url = domain["provider"]

        domain = Domain(domain_name=domain_name, ip=ip)
        status = Status(status_type="added")
        domain.status.append(status)

        domain.is_active, domain.is_monitored = True, True

        provider = session.query(Provider).filter(
            Provider.provider_url == provider_url).first()
        if not provider:
            provider = Provider(provider_url=provider_url)

        provider.domains.append(domain)

        category_name = session.query(CategoryName).filter(
            CategoryName.name == "unassigned").first()
        domain.category = Category()
        domain.category.category_name = category_name

        session.add(domain)
        session.commit()


@manager.command
def add_user():
    username = raw_input("Username: ")
    if session.query(WebUser).filter_by(username=username).first():
        print "Username already exists."
        return
    password = ""
    repeat_password = ""
    while not (password and repeat_password) or password != repeat_password:
        password = getpass("Password: ")
        repeat_password = getpass("Re-enter password: ")
    web_user = WebUser(username=username,
                       password=generate_password_hash(password))
    session.add(web_user)
    session.commit()


class DB(object):
    def __init__(self, metadata):
        self.metadata = metadata

migrate = Migrate(app, DB(Base.metadata))
manager.add_command('db', MigrateCommand)

if __name__ == "__main__":
    manager.run()
