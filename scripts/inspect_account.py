#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from dotenv import load_dotenv

from app.services.heygen_client import HeyGenClient


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description='Inspect HeyGen account resources')
    parser.add_argument('resource', choices=['avatars', 'voices', 'templates'])
    args = parser.parse_args()

    client = HeyGenClient()
    if args.resource == 'avatars':
        payload = client.list_avatars()
    elif args.resource == 'voices':
        payload = client.list_voices()
    else:
        payload = client.list_templates()
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
