#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from app.services.leads_service import LeadsService
from app.services.video_service import VideoService


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description='Batch-generate HeyGen videos from CSV/XLSX leads file')
    parser.add_argument('input_path', help='Path to CSV/XLSX leads file')
    parser.add_argument('--mode', choices=['direct', 'template'], default='direct')
    parser.add_argument('--template-name', default='legal_notice_safe_hi.txt')
    parser.add_argument('--payload-path', default=None)
    parser.add_argument('--avatar-id', default=None)
    parser.add_argument('--voice-id', default=None)
    parser.add_argument('--folder-id', default=None)
    parser.add_argument('--no-wait', action='store_true')
    args = parser.parse_args()

    leads_service = LeadsService()
    df = leads_service.read_table(args.input_path)
    service = VideoService()
    results = []

    if args.mode == 'direct':
        requests = leads_service.direct_requests_from_dataframe(
            df,
            template_name=args.template_name,
            avatar_id=args.avatar_id,
            voice_id=args.voice_id,
            folder=args.folder_id,
        )
        for req in requests:
            results.append(service.generate_direct(req, wait=not args.no_wait).model_dump(mode='json'))
    else:
        requests = leads_service.template_requests_from_dataframe(
            df,
            payload_path=args.payload_path,
            template_id=None,
            folder=args.folder_id,
        )
        for req in requests:
            results.append(service.generate_from_template(req, wait=not args.no_wait).model_dump(mode='json'))

    out_path = Path('output') / f'batch_results_{args.mode}.json'
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Saved {len(results)} results to {out_path}')


if __name__ == '__main__':
    main()
