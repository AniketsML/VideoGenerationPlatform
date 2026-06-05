#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from dotenv import load_dotenv

from app.services.heygen_client import HeyGenClient


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description='Fetch HeyGen template details')
    parser.add_argument('template_id')
    parser.add_argument('--version', choices=['v2', 'v3'], default='v3')
    args = parser.parse_args()

    client = HeyGenClient()
    payload = client.get_template_details(args.template_id, version=args.version)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
