import re
import time

import json
import requests
import requests_cache
import yaml


HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Referer': 'https://feedly.com',
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:81.0) Gecko/20100101 Firefox/81.0',
    'Authorization': 'token '
}

GIST_SEARCH_URL_TEMPLATE = "https://gist.github.com/search?l=YAML&o=desc&p={page}&q={query}&s="
GIST_GET_API_URL_TEMPLATE = "https://api.github.com/gists/{gist_id}"

GIST_ID_REGEX = re.compile(r'<a class="link-overlay" href="https://gist.github.com/\w+/(\w+)">')


def gen_gist_id(query):
    for page in range(1, 101):
        url = GIST_SEARCH_URL_TEMPLATE.format(page=page, query=query)
        resp = requests.get(url, headers=HEADERS)
        
        for m in GIST_ID_REGEX.finditer(resp.text):
            yield m.group(1)

        # time.sleep(2)


def gen_gist(gist_id):
    headers = HEADERS | {"Accept": "application/vnd.github.v3+json"}
    resp = requests.get(GIST_GET_API_URL_TEMPLATE.format(gist_id=gist_id), headers=headers)

    try:
        files = resp.json()["files"]
    except KeyError:
        print(resp)
        print(resp.text)
        raise

    for f in files.values():
        if f["type"] == "text/x-yaml" and not f["truncated"]:
            clean_content = f["content"].replace('\t', '  ').replace('{{', '"').replace('}}', '"')

            try:
                yield from yaml.safe_load_all(clean_content)
            except (yaml.scanner.ScannerError, yaml.parser.ParserError, yaml.composer.ComposerError):
                print(f["content"])
                raise
                

def insert(index, key, doc):
    sub_index = index.setdefault(key, {"COUNT": 0})
    sub_index["COUNT"] += 1

    if doc is None:
        return

    if isinstance(doc, list):
        if doc:
            insert(sub_index, "LIST", doc[0])
    elif isinstance(doc, dict):
        for key, value in doc.items():
            insert(sub_index, key, value)
    else:
        insert(sub_index, "VALUE-{}".format(doc), None)


if __name__ == "__main__":
    requests_cache.install_cache(backend="sqlite")

    with open("mined_gids.dat") as f:
        mined = {line.rstrip() for line in f}

    with open("kube_yaml_index.dat") as f:
        index = json.load(f)

    for gid in gen_gist_id("apiversion+kind+metadata"):
        if gid in mined:
            continue

        try:
            for doc in gen_gist(gid):
                if doc and "kind" in doc:
                    insert(index, doc["kind"], doc)
        except (yaml.scanner.ScannerError, yaml.parser.ParserError, yaml.composer.ComposerError):
            pass

        mined.add(gid)

    print("{} yamls in database".format(sum(d["COUNT"] for d in index.values())))

    with open("mined_gids.dat", 'w') as f:
        for gid in mined:
            f.write(f'{gid}\n')

    with open("kube_yaml_index.dat", 'w') as f:
        json.dump(index, f)
