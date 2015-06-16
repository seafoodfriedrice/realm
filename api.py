import json
from urlparse import urlparse
from datetime import datetime

from flask import request, Response, url_for, redirect, flash
from jsonschema import validate, ValidationError
from datetime import datetime

from realm import app
from realm.database import session
from realm.models import Domain, Status, Category, CategoryName, WhoisInfo

@app.route("/api/domains", methods=["GET"])
def domains_get():
    """ Retrieve full list of domains """
    domains = session.query(Domain).all()
    data = json.dumps([domain.as_dictionary() for domain in domains])
    return Response(data, 200, mimetype="application/json")

domain_post_schema = {
    "properties": {
        "status": {
            "type": "string",
            "pattern": "^(success|failed|mismatch: (\d{1,3}.){3}\d{1,3})$"
        }
    },
    "required": ["status"]
}

domain_put_schema = {
    "properties": {
        "category": {
            "type": "string",
            "enum": ["unassigned", "alpha", "bravo",
                     "charlie", "delta", "echo", "foxtrot"]
        },
        "domain_name": { "type": "string" },
        "ip": { "type": "string" },
        "provider": { "type": "string" },
        "is_active": { "type": "boolean" },
        "is_monitored": { "type": "boolean" }
    },
    "required": ["domain_name"]
}


# Returns the url with the http:// or https:// prefix removed
def parse_url(url):
    url = urlparse(url)
    if url.netloc:
        return url.netloc
    else:
        return url.path

@app.route("/api/domains/<domain_name>", methods=["GET", "POST", "PUT"])
def domain(domain_name):
    # Get JSON for individual domain when
    # using GET method
    if request.method =="GET":
        domain = session.query(Domain).filter(
            Domain.domain_name == domain_name).first()
        if domain:
            data = json.dumps(domain.as_dictionary())
            return Response(data, 200, mimetype="application/json")
        else:
            data = json.dumps({domain_name: "Domain not found."})
            return Response(data, 404, mimetype="application/json")

    # Append new Status to Domain.status when
    # using POST method
    if request.method == "POST":
        data = request.json
        try:
            validate(data, domain_post_schema)
        except ValidationError as error:
            data = {"message": error.message}
            return Response(json.dumps(data), 422, mimetype="application/json")

        domain = session.query(Domain).filter(
            Domain.domain_name == domain_name).first()
        domain.status.append(Status(status_type=data["status"],
                                    status_time=datetime.now()))

        session.add(domain)
        headers = {"Location": url_for("domain", domain_name=domain_name)}

        try:
            session.commit()
            data = {
                "message": "Updated {} with status '{}'.".format(
                    domain.domain_name, data["status"])
            }
            return Response(json.dumps(data), 201, mimetype="application/json")
        except:
            session.rollback()
            data = {"message": "Unknown error has occured."}
            return Response(json.dumps(data), 422, mimetype="application/json")

    # Update individual domain information when
    # using PUT method
    if request.method == "PUT":
        data = request.json
        try:
            validate(data, domain_put_schema)
        except ValidationError as error:
            data = {"message": error.message}
            return Response(json.dumps(data), 422, mimetype="application/json")

        domain = session.query(Domain).filter(
            Domain.domain_name == domain_name).first()
        domain.domain_name = parse_url(data["domain_name"].strip())

        # Get Provider if attribute is set in request
        if data.get("provider", None):
            provider = session.query(Provider).filter(
                Provider.provider_url == data["provider"]).first()
            # Create new Provider if requested one doesn't exist
            if not provider:
                provider = Provider(provider_url=data["provider"].strip())

            # Add provider to domain object to update
            domain.provider = provider

        if data.get("category", None):
            domain.category = session.query(Category).get(domain.id)
            domain.category.category_name = session.query(CategoryName).filter(
                CategoryName.name == data["category"].strip()).first()

        if data.get("ip", None):
            domain.ip = data["ip"].strip()

        # Only updates is_active if explicitly set to True or False
        # we don't want to update if is_active isn't present in the request
        if (data.get("is_active") == True
                or data.get("is_active") == False):
            domain.is_active = data["is_active"]

        # Only updates is_monitored if explicitly set to True or False
        # we don't want to update if is_monitored isn't present in the request
        if (data.get("is_monitored") == True
                or data.get("is_monitored") == False):
            domain.is_monitored = data["is_monitored"]

        session.add(domain)
        headers = {"Location": url_for("domain", domain_name=domain_name)}

        try:
            session.commit()
            message = "Updated {} successfully.".format(domain.domain_name)
            data = {"message": message}
            return Response(json.dumps(data), 201, mimetype="application/json")
        except:
            session.rollback()
            data = {"message": "Unknown error has occured."}
            return Response(json.dumps(data), 422, mimetype="application/json")
