import json
import requests

endpoint_get = "http://localhost:8080/api/domains/resolver1.opendns.com"
r = requests.get(endpoint_get)
domain = r.json()

domain_name = domain["domain_name"]
ip = domain["ip"]
category = domain["category"]
status = domain["status"]
provider = domain["provider"]
is_active = domain["is_active"]
is_monitored = domain["is_monitored"]

endpoint_put = "http://localhost:8080/api/domains/{}".format(domain_name)
headers = {"Content-Type": "application/json"}
data = {
    "domain_name": "resolver1.opendns.com",
    "ip": "208.67.222.222",
    "category": "unassigned",
    "is_monitored": True,
    "is_active": True
}

put = requests.put(endpoint_put, headers=headers, data=json.dumps(data))
