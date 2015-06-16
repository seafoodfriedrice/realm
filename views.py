import socket
from whois import whois
from urlparse import urlparse
from datetime import date, datetime, timedelta

from flask import render_template
from flask import request, redirect, url_for
from flask import flash
from flask.ext.login import login_user, logout_user, login_required
from flask.ext.login import current_user
from werkzeug.security import check_password_hash

from realm import app
from realm.database import session
from realm.models import Domain, Provider, Category
from realm.models import Status, WebUser, CategoryName, WhoisInfo





# Retrieve list of existing category names
category_names = [category_name.name for category_name in
                  session.query(CategoryName).all()]


# Returns the url with the http:// or https:// prefix removed
def parse_url(url):
    url = urlparse(url)
    if url.netloc:
        return url.netloc
    else:
        return url.path


def is_expiring_soon(domain):
    # Get dates one month and one week from now to use as comparison
    # that is used in template to see if domain is expiring soon
    today = datetime.today()
    week_from_now = today + timedelta(days=7)
    month_from_now = today + timedelta(days=30)

    # Have to convert domain.exp_date to datetime object
    # in order to do a comparison with week_from_now and month_from_now
    expire_datetime = datetime.combine(domain.exp_date, datetime.min.time())

    # Returns of dict() with key week, month and boolean values
    expiration = {
        "week":  expire_datetime < week_from_now,
        "month": expire_datetime < month_from_now,
        "past": expire_datetime < today
    }
    return expiration


def domain_pager(current_domain_name, domain_names_list):
    current_index = domain_names_list.index(str(current_domain_name))

    # Set next domain to current domain if last index
    # otherwise get current_index + 1
    if current_index == (len(domain_names_list) - 1):
        next_domain = domain_names_list[current_index]
    else:
        next_domain = domain_names_list[current_index + 1]

    # Set previous domain as current domain if index is 0
    # otherwise get current_index - 1
    if current_index == 0:
        previous_domain = domain_names_list[current_index]
    else:
        previous_domain = domain_names_list[current_index - 1]

    # Returns next and previous domain names as
    # tuple(str(), str())
    return (next_domain, previous_domain)




@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        web_user = session.query(WebUser).filter(
            WebUser.username == username).first()
        if not web_user or not check_password_hash(web_user.password,
                                                   password):
            flash("Incorrect username or password.", "danger")
            return redirect(url_for("login"))
        login_user(web_user)
        return redirect(request.args.get("next") or url_for("home"))
    else:
        return render_template("login.html")



@app.route("/logout", methods=["GET"])
def logout():
    if current_user.is_authenticated():
        logout_user()
        return render_template("logout.html")
    else:
        return render_template("login.html")



@app.route("/")
@login_required
def home():
    """ Display all domains """

    domains = session.query(Domain).order_by(
        Domain.domain_name).all()
    domains_count = len(domains)

    domains_expirations = []
    domains_issues = []

    for domain in domains:
        expiring = is_expiring_soon(domain)
        status_type = domain.status[-1].status_type

        if expiring.get("past"):
            pass
        elif expiring.get("week") or expiring.get("month"):
            domains_expirations.append(domain)

        if status_type.startswith("mismatch") or status_type == "failed":
            domains_issues.append(domain)

    expirations = request.args.get("expirations")
    if expirations:
        domains = domains_expirations
        # Sort domain list by expiration date, closest date on top
        domains.sort(key=lambda d: d.exp_date, reverse=False)

    issues = request.args.get("issues")
    if issues:
        domains = domains_issues
        domains.sort(key=lambda d: d.status[-1].status_type, reverse=False)

    # dict comprehension to build dict() with key as domain name
    # and value as dict returned from is_expiring_soon().
    # Used to put icon near domains that are expiring soon.
    expirations = {domain.domain_name: is_expiring_soon(domain)
                   for domain in domains}

    kwargs = {
        "domains": domains,
        "domains_count": domains_count,
        "domains_issues": domains_issues,
        "domains_expirations": domains_expirations,
        "expirations": expirations
    }
    return render_template("home.html", **kwargs)

@app.route("/<domain_name>")
def view_domain(domain_name):
    """ View individual domain """

    domain = session.query(Domain).filter(
        Domain.domain_name == domain_name).first()
    if not domain:
        message = "{}Error!{} Domain {}{}{} does not exist.".format(
                   "<strong>", "</strong>", "<em>", domain_name, "</em>")
        flash(message, "danger")
        return redirect(url_for("home"))

    domains = session.query(Domain).order_by(
        Domain.domain_name).all()

    domains_expirations = []
    for d in domains:
        expiring = is_expiring_soon(d)
        if expiring.get("past"):
            continue
        elif expiring.get("week") or expiring.get("month"):
            domains_expirations.append(d)

    # Obtain list of domain names without tuple to use
    # for domain_pager()
    if request.args.get("expirations"):
        # Sort domain list by expiration date, closest date on top
        domains_expirations.sort(key=lambda k: k.exp_date, reverse=False)
        domain_names = [k.domain_name for k in domains_expirations]
    else:
        domain_names = [d.domain_name for d in domains]

    next_domain, previous_domain = domain_pager(domain_name, domain_names)
    expiration = is_expiring_soon(domain)

    kwargs = {
        "domain": domain,
        "domain_name": domain_name,
        "next_domain": next_domain,
        "previous_domain": previous_domain,
        "expiration": expiration
    }
    return render_template("view_domain.html", **kwargs)


@app.route("/<domain_name>/<action>")
def view_domain_action(domain_name, action):
    domain = session.query(Domain).filter_by(domain_name=domain_name).first()

    if action == "status":
        try:
            resolved_ip = socket.gethostbyname(domain_name)
            if resolved_ip == domain.ip:
                status_type = "success"
            else:
                status_type = "mismatch: {}".format(resolved_ip)
        except socket.gaierror:
            status_type = "failed"

        status = Status(status_type=status_type,
                        status_time=datetime.now())
        domain.status.append(status)
        session.add(domain)

        try:
            session.commit()
            message = "{}Done!{} Status History has been updated.".format(
                "<strong>", "</strong>", "<em>", domain_name)
            flash(message , "success")
        except:
            session.rollback()
            message = "{}Error!{} Could not update Status History.".format(
                "<strong>", "</strong>", "<em>", domain_name)
            flash(message, "danger")

        return redirect(url_for("view_domain", domain_name=domain_name))

    if action == "whois":
        w = whois(domain_name)
        domain.whois_info = WhoisInfo(text=w.text, lookup_time=datetime.now())
        session.add(domain)

        try:
            session.commit()
            message = "{}Done!{} Performed Whois Lookup successfully.".format(
                "<strong>", "</strong>", "<em>", domain_name)
            flash(message , "success")
        except:
            session.rollback()
            message = "{}Error!{} Whois Lookup has failed.".format(
                "<strong>", "</strong>", "<em>", domain_name)
            flash(message, "danger")

        return redirect(url_for("view_domain", domain_name=domain_name))

    if action == "cancelled":
        status = Status(status_type="cancelled",
                        status_time=datetime.now())
        domain.status.append(status)
        session.add(domain)

        try:
            session.commit()
            message = "{}Done!{} Set domain status to Cancelled.".format(
                "<strong>", "</strong>", "<em>", domain_name)
            flash(message , "success")
        except:
            session.rollback()
            message = "{}Error!{} Could not set status to Cancelled.".format(
                "<strong>", "</strong>", "<em>", domain_name)
            flash(message, "danger")

        return redirect(url_for("view_domain", domain_name=domain_name))


@app.route("/add", methods=["GET", "POST"])
@login_required
def add_domain():
    """ Add an individual domain """

    today = date.today()

    if request.method == "POST":
        # Check to see if domain already exists because
        # duplicate domain names aren't allowed
        domain = session.query(Domain).filter_by(
            domain_name=request.form["domain-name"]).first()
        if domain:
            message = "{}Error!{} {}{}{} already exists.".format(
                "<strong>", "</strong>", "<em>", domain.domain_name, "</em>")
            flash(message, "danger")
            return redirect(url_for("add_domain", today=today,
                                    category_names=category_names))

        # Find existing Provider otherwise create new Provider object
        provider = session.query(Provider).filter(
            Provider.provider_url == request.form["provider-url"]).first()
        if not provider:
            provider = Provider(provider_url=request.form["provider-url"])

        # Get existing category name object from CategoryName table
        category_name = session.query(CategoryName).filter(
            CategoryName.name == request.form["category"]).first()

        domain = Domain(
            category=Category(),
            domain_name=request.form["domain-name"],
            ip=request.form["ip-address"],
            provider=provider)
        domain.category.category_name = category_name
        domain.status.append(Status(status_type="added"))
        domain.is_active = request.form.get("is-active", False)
        domain.is_monitored = request.form.get("is-monitored", False)

        # Convert date string from form to date object
        exp_date = datetime.strptime(request.form.get("exp-date"),
                                     "%Y-%m-%d").date()
        domain.exp_date = exp_date

        session.add(domain)

        try:
            session.commit()
            message = "{}Success!{} Added {}{}{} successfully.".format(
                "<strong>", "</strong>", "<em>", domain.domain_name, "</em>")
            flash(message , "success")
        except:
            session.rollback()
            message = "{}Error!{} Could not add add {}{}{}.".format(
                "<strong>", "</strong>", "<em>", domain.domain_name, "</em>")
            flash(message, "danger")

        if request.form["submit"] == "Submit":
            return redirect(url_for("home"))
        else:
            return redirect(url_for("add_domain", today=today,
                                    category_names=category_names))
    else:
        return render_template("add_domain.html", today=today,
                                category_names=category_names)



@app.route("/edit/<domain_name>", methods=["GET", "POST"])
@login_required
def edit_domain(domain_name):
    """ Edit an existing domain """

    if request.method == "POST":
        domain = session.query(Domain).filter(
            Domain.domain_name == domain_name).first()

        # Check if domain.provider object exists to make sure
        # duplicate Provider.provider_url is not created
        provider = session.query(Provider).filter(
            Provider.provider_url == domain.provider.provider_url).first()
        if not provider:
            provider = Provider(
                provider_url=request.form["provider-url"].strip())

        domain.category.category_name = session.query(CategoryName).filter(
            CategoryName.name == request.form["category"].strip()).first()

        domain.domain_name = parse_url(request.form["domain-name"].strip())
        domain.ip = request.form["ip-address"].strip()
        domain.provider.provider_url = parse_url(
            provider.provider_url.strip())
        domain.is_active = request.form.get("is-active", False)
        domain.is_monitored = request.form.get("is-monitored", False)

        # Convert date string from form to date object
        exp_date = datetime.strptime(request.form.get("exp-date"),
                                     "%Y-%m-%d").date()
        domain.exp_date = exp_date

        session.add(domain)

        try:
            session.commit()
            message = "{}Success!{} Updated {}{}{} successfully.".format(
                "<strong>", "</strong>", "<em>", domain.domain_name, "</em>")
            flash(message, "success")
        except:
            session.rollback()
            message = "{}Error!{} Problem with one of the fields.".format(
                "<strong>", "</strong>")
            flash(message, "danger")
            return redirect(url_for("edit_domain", domain_name=domain_name))

        if request.form["submit"] == "Save":
            return redirect(url_for("view_domain",
                            domain_name=domain.domain_name,
                            category_names=category_names))
        else:
            return redirect(url_for("edit_domain",
                            domain_name=domain.domain_name,
                            category_names=category_names))
    else:
        domain = session.query(Domain).filter(
            Domain.domain_name == domain_name).first()

        # Obtain list of domain names without tuple to use
        # for domain_pager()
        domain_names = [d.domain_name for d in session.query(
                        Domain.domain_name).order_by(Domain.domain_name).all()]
        next_domain, previous_domain = domain_pager(domain_name, domain_names)

        kwargs = {
            "domain": domain,
            "domain_name": domain_name,
            "category_names": category_names,
            "next_domain": next_domain,
            "previous_domain": previous_domain
        }
        return render_template("edit_domain.html", **kwargs)
