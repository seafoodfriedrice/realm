import socket
import json
import requests
from time import sleep
from random import randint

endpoint_get = "http://localhost:8080/api/domains"
r = requests.get(endpoint_get)
domains = r.json()

for domain in domains:
    ip, domain_name = domain["ip"], domain["domain_name"]
    is_active = domain["is_active"]

    if not is_active:
        continue

    endpoint_post = "http://localhost:8080/api/domains/{}".format(domain_name)
    headers = {"Content-Type": "application/json"}
    data = {"status": ""}

    try:
        resolved_ip = socket.gethostbyname(domain_name)
        if  resolved_ip == ip:
            data["status"] = "success"
        else:
            data["status"] = "mismatch"
    except socket.gaierror:
        data["status"] = "failed"

    print domain_name, data["status"]
    requests.post(endpoint_post, headers=headers, data=json.dumps(data))

    min, max = 5, 15 
    sleep(randint(min, max))
