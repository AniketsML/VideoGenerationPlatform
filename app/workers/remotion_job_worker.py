from __future__ import annotations

import asyncio
import base64
import html
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from bson import ObjectId 

from app.config import settings
from app.constants import SQS_QUEUE_URL
from app.database import videos_collection
from app.models import VideoRecord, RemotionVideoRequest
from app.services.sqs_service import SQSService
from app.services.remotion_service import RemotionService
from app.services.s3_service import S3Service

logger = logging.getLogger("app")


def _mongo_id(value: str) -> ObjectId | str:
    cleaned = str(value)
    if ObjectId.is_valid(cleaned):
        return ObjectId(cleaned)
    return cleaned


def _to_mongo_safe(obj: Any) -> Any:
    """Recursively convert Pydantic models and Paths to JSON-safe types."""
    if hasattr(obj, "model_dump"):
        obj = obj.model_dump(mode="python")
    if isinstance(obj, dict):
        return {k: _to_mongo_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_mongo_safe(v) for v in obj]
    if isinstance(obj, Path):
        return str(obj)
    return obj


def _asset_data_uri(relative_path: str) -> str:
    project_root = Path(__file__).resolve().parents[2]
    if relative_path.startswith(("app/", "Remotion/")):
        asset_path = project_root / relative_path
    else:
        asset_path = Path(__file__).resolve().parents[1] / relative_path
    if not asset_path.exists():
        logger.warning("Interactive HTML asset missing: %s", asset_path)
        return ""

    mime_type = "image/png" if asset_path.suffix.lower() == ".png" else "image/jpeg"
    encoded = base64.b64encode(asset_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


class RemotionJobWorker:
    """
    Polls the SQS queue for Remotion video generation jobs and processes them.
    Mirrors the AvatarJobWorker pattern.
    """

    def __init__(self) -> None:
        self.sqs_service = SQSService()
        self.remotion_service = RemotionService()
        self.s3_service = S3Service()
        self.videos_collection_ref = videos_collection
        self.queue_url = SQS_QUEUE_URL

    async def _set_progress(self, video_id: str, status: str, phase: str, progress: int, extra: dict[str, Any] | None = None) -> None:
        safe_progress = max(0, min(100, int(progress)))
        fields = {
            "status": status,
            "phase": phase,
            "progress": safe_progress,
            "updated_at": datetime.utcnow(),
            "job_data.status": status,
            "job_data.phase": phase,
            "job_data.progress": safe_progress,
        }
        if extra:
            fields.update(extra)
        await self.videos_collection_ref.update_one({"_id": _mongo_id(video_id)}, {"$set": fields})

    def _build_loan_reminder_html(
        self,
        *,
        video_id: str,
        title: str,
        video_url: str,
        payment_url: str,
        callback_phone: str,
    ) -> str:
        frontend_base_url = (settings.frontend_url or "").strip().rstrip("/")
        api_url = f"{frontend_base_url}/api/interactive/loan-reminder/{video_id}" if frontend_base_url else ""
        payload = json.dumps(
            {
                "apiUrl": api_url,
                "videoUrl": video_url,
                "paymentUrl": payment_url,
                "callbackPhone": callback_phone,
                "showCtaAt": 46,
            },
            ensure_ascii=True,
        )
        escaped_title = html.escape(title or "Loan Reminder")
        bank_logo_src = _asset_data_uri("Remotion/public/assets/tvs_credit_logo.png")
        credresolve_logo_src = _asset_data_uri("app/assets/credresolve_logo-removebg-preview.png")
        bank_logo_markup = (
            f'<img class="bank-logo" src="{bank_logo_src}" alt="TVS Credit" />'
            if bank_logo_src
            else '<div class="bank-logo-fallback">TVS</div>'
        )
        credresolve_logo_markup = (
            f'<img class="credresolve-logo" src="{credresolve_logo_src}" alt="CredResolve" />'
            if credresolve_logo_src
            else '<div class="credresolve-fallback">CredResolve</div>'
        )

        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escaped_title}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
      background:
        radial-gradient(circle at 16% 12%, rgba(10, 157, 88, 0.34), transparent 32%),
        radial-gradient(circle at 86% 78%, rgba(0, 107, 179, 0.42), transparent 34%),
        linear-gradient(180deg, #005baa 0%, #063f5f 58%, #021c2f 100%);
      color: #fff;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    .shell {{
      width: min(100%, 460px);
    }}
    .brand-overlay {{
      align-items: center;
      display: flex;
      gap: 14px;
      justify-content: space-between;
      left: 14px;
      pointer-events: none;
      position: absolute;
      right: 14px;
      top: 14px;
      z-index: 5;
    }}
    .bank-brand {{
      align-items: center;
      background: rgba(255, 255, 255, 0.96);
      border: 1px solid rgba(255, 255, 255, 0.34);
      border-radius: 18px;
      display: flex;
      min-height: 54px;
      padding: 8px;
      box-shadow: 0 18px 40px rgba(2, 28, 47, 0.22);
    }}
    .bank-logo {{
      width: 42px;
      height: 42px;
      display: block;
      object-fit: contain;
    }}
    .bank-logo-fallback {{
      align-items: center;
      background: #005baa;
      border-radius: 12px;
      color: #ffffff;
      display: flex;
      font-size: 13px;
      font-weight: 950;
      height: 34px;
      justify-content: center;
      width: 34px;
    }}
    .powered-by {{
      align-items: flex-end;
      display: flex;
      flex-direction: column;
      gap: 6px;
      min-width: 0;
    }}
    .powered-label {{
      color: rgba(255, 255, 255, 0.82);
      font-size: 8px;
      font-weight: 850;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .credresolve-logo {{
      width: min(30vw, 110px);
      height: auto;
      display: block;
      filter: drop-shadow(0 12px 24px rgba(2, 28, 47, 0.2));
    }}
    .credresolve-fallback {{
      color: #ffffff;
      font-size: 14px;
      font-weight: 900;
      letter-spacing: -0.02em;
    }}
    .player {{
      position: relative;
      width: 100%;
      max-width: 430px;
      max-height: min(86vh, 920px);
      aspect-ratio: 9 / 16;
      margin: 0 auto;
      overflow: hidden;
      border-radius: 12px;
      background: #063f5f;
      border: 1px solid rgba(255, 255, 255, 0.18);
      box-shadow: 0 24px 70px rgba(2, 28, 47, 0.34);
    }}
    video {{
      width: 100%;
      height: 100%;
      display: block;
      object-fit: cover;
      background: #063f5f;
    }}
    .overlay {{
      position: absolute;
      left: 0;
      right: 0;
      bottom: 0;
      display: none;
      padding: 72px 18px 18px;
      background: linear-gradient(180deg, rgba(6, 63, 95, 0) 0%, rgba(6, 63, 95, 0.72) 28%, rgba(6, 63, 95, 0.96) 100%);
    }}
    .overlay.visible {{
      display: block;
    }}
    .actions {{
      display: grid;
      gap: 12px;
    }}
    .button {{
      min-height: 54px;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 100%;
      border-radius: 8px;
      padding: 14px 18px;
      font-size: 18px;
      line-height: 1.1;
      font-weight: 900;
      text-decoration: none;
      border: 0;
    }}
    .pay {{
      color: #fff;
      background: linear-gradient(135deg, #0a9d58 0%, #25c978 100%);
      box-shadow: 0 16px 34px rgba(10, 157, 88, 0.3);
    }}
    .call {{
      color: #063f5f;
      background: #fff;
      border: 2px solid rgba(6, 63, 95, 0.16);
      box-shadow: 0 12px 28px rgba(6, 63, 95, 0.18);
    }}
    .note {{
      margin: 18px 0 0;
      text-align: center;
      font-size: 12px;
      color: rgba(255, 255, 255, 0.65);
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="player" aria-label="{escaped_title}">
      <video id="loan-video" controls playsinline preload="metadata"></video>
      <div class="brand-overlay">
        <div class="bank-brand">
          {bank_logo_markup}
        </div>
        <div class="powered-by">
          <div class="powered-label">Powered by</div>
          {credresolve_logo_markup}
        </div>
      </div>
      <div id="cta-overlay" class="overlay">
        <div class="actions">
          <a id="pay-button" class="button pay" target="_blank" rel="noopener noreferrer">Pay Now</a>
          <a id="call-button" class="button call">Call Now</a>
        </div>
      </div>
    </section>
    <p class="note">The MP4 visuals are not clickable. Use the on-screen buttons.</p>
  </main>
  <script>
    const config = {payload};
    const video = document.getElementById("loan-video");
    const overlay = document.getElementById("cta-overlay");
    const payButton = document.getElementById("pay-button");
    const callButton = document.getElementById("call-button");

    function applyConfig(nextConfig) {{
      if (nextConfig.videoUrl) {{
        video.src = nextConfig.videoUrl;
      }}
      if (nextConfig.paymentUrl) {{
        payButton.href = nextConfig.paymentUrl;
      }}
      if (nextConfig.callbackPhone) {{
        callButton.href = "tel:" + nextConfig.callbackPhone;
      }}
      payButton.style.display = nextConfig.paymentUrl ? "flex" : "none";
      callButton.style.display = nextConfig.callbackPhone ? "flex" : "none";
    }}

    applyConfig(config);

    if (config.apiUrl) {{
      fetch(config.apiUrl)
        .then((response) => response.ok ? response.json() : null)
        .then((data) => {{
          if (!data) return;
          applyConfig({{
            videoUrl: data.video_url,
            paymentUrl: data.payment_url,
            callbackPhone: data.contact_details,
          }});
        }})
        .catch(() => undefined);
    }}

    if (!config.paymentUrl) {{
      payButton.style.display = "none";
    }}
    if (!config.callbackPhone) {{
      callButton.style.display = "none";
    }}

    video.addEventListener("timeupdate", () => {{
      overlay.classList.toggle("visible", video.currentTime >= config.showCtaAt);
    }});
  </script>
</body>
</html>
"""

    def _upload_loan_reminder_html(
        self,
        *,
        video_id: str,
        title: str,
        video_url: str,
        payment_url: str,
        callback_phone: str,
    ) -> str | None:
        html_dir = settings.output_dir / "interactive" / "loan-reminder"
        html_dir.mkdir(parents=True, exist_ok=True)
        html_path = html_dir / f"{video_id}.html"
        html_path.write_text(
            self._build_loan_reminder_html(
                video_id=video_id,
                title=title,
                video_url=video_url,
                payment_url=payment_url,
                callback_phone=callback_phone,
            ),
            encoding="utf-8",
        )
        return self.s3_service.upload_file(
            html_path,
            f"interactive/loan-reminder/{video_id}.html",
            content_type="text/html; charset=utf-8",
        )

    # ------------------------------------------------------------------
    # Sales CTA static HTML (scene_loan_offer)
    # ------------------------------------------------------------------

    def _build_sales_cta_html(
        self,
        *,
        video_id: str,
        title: str,
        video_url: str,
        customer_name: str,
        sales_cta_label: str,
        sales_cta_url: str,
    ) -> str:
        escaped_title = html.escape(title or "Sales Offer")
        payload = json.dumps(
            {
                "videoUrl": video_url,
                "customerName": customer_name,
                "ctaLabel": sales_cta_label,
                "ctaUrl": sales_cta_url,
            },
            ensure_ascii=True,
        )
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escaped_title}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px;
      background: linear-gradient(160deg, #0f172a 0%, #1e293b 60%, #0f172a 100%);
      color: #fff;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }}
    .shell {{
      width: min(100%, 430px);
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .player {{
      position: relative;
      width: 100%;
      aspect-ratio: 9 / 16;
      max-height: min(82vh, 800px);
      overflow: hidden;
      border-radius: 24px;
      background: #0f172a;
      border: 1px solid rgba(255,255,255,0.1);
      box-shadow: 0 24px 70px rgba(0,0,0,0.5);
    }}
    video {{
      width: 100%;
      height: 100%;
      display: block;
      object-fit: cover;
    }}
    /* Top-right persistent CTA */
    .top-cta {{
      position: absolute;
      top: 2.8125%;
      right: 5%;
      height: 2.8125%;
      min-height: 24px;
      max-height: 36px;
      display: none;
      align-items: center;
      gap: 4px;
      padding: 0 12px;
      border-radius: 100px;
      background: rgba(15,191,93,0.95);
      color: #fff;
      font-size: 10.5px;
      font-weight: 900;
      border: 1px solid rgba(255,255,255,0.1);
      box-shadow: 0 8px 20px rgba(15,191,93,0.35);
      cursor: pointer;
      text-decoration: none;
      z-index: 20;
      transition: transform 0.2s ease;
    }}
    .top-cta:hover {{ transform: scale(1.05); }}
    .top-cta.visible {{ display: flex; }}
    /* Top-left restart */
    .restart-btn {{
      position: absolute;
      top: 2.8125%;
      left: 5%;
      height: 2.8125%;
      width: 2.8125%;
      min-height: 24px;
      max-height: 36px;
      min-width: 24px;
      max-width: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
      background: rgba(255,255,255,0.18);
      border: 1px solid rgba(255,255,255,0.24);
      box-shadow: 0 8px 20px rgba(0,0,0,0.22);
      cursor: pointer;
      z-index: 20;
      transition: transform 0.2s ease;
    }}
    .restart-btn:hover {{ transform: scale(1.08); }}
    /* Bottom overlay CTA */
    .bottom-overlay {{
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      padding: 60px 20px 24px;
      background: linear-gradient(180deg, rgba(15,23,42,0) 0%, rgba(15,23,42,0.8) 35%, rgba(15,23,42,0.95) 100%);
      display: none;
      flex-direction: column;
      gap: 12px;
      z-index: 20;
    }}
    .bottom-overlay.visible {{ display: flex; }}
    .cta-btn {{
      width: 100%;
      height: 54px;
      min-height: 54px;
      border-radius: 16px;
      font-size: 17px;
      font-weight: 800;
      color: #fff;
      background: linear-gradient(135deg, #10b981 0%, #059669 100%);
      box-shadow: 0 10px 25px rgba(16,185,129,0.4), inset 0 1px 0 rgba(255,255,255,0.3);
      border: 1px solid rgba(255,255,255,0.2);
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      cursor: pointer;
      text-decoration: none;
      transition: transform 0.2s ease;
    }}
    .cta-btn:hover {{ transform: scale(1.02); }}
    .footer-note {{
      text-align: center;
      font-size: 11px;
      color: rgba(255,255,255,0.38);
      padding: 0 16px;
    }}
  </style>
</head>
<body>
  <main class="shell">
    <div class="player">
      <video id="v" src="" playsinline controls preload="metadata"></video>

      <!-- Persistent top-right CTA (always visible once video started) -->
      <a id="top-cta" class="top-cta" target="_blank" rel="noopener noreferrer">
        <span id="top-cta-label"></span>
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
      </a>

      <!-- Top-left restart button -->
      <button id="restart-btn" class="restart-btn" title="Restart Video">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 2v6h6"/><path d="M3 13a9 9 0 1 0 3-7.7L3 8"/></svg>
      </button>

      <!-- Bottom overlay (appears at video end) -->
      <div id="bottom-overlay" class="bottom-overlay">
        <a id="bottom-cta" class="cta-btn" target="_blank" rel="noopener noreferrer">
          <span id="bottom-cta-label"></span>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
        </a>
      </div>
    </div>
    <p class="footer-note">The video graphics are not interactive. Use the buttons on screen.</p>
  </main>

  <script>
    const config = {payload};
    const video = document.getElementById('v');
    const topCta = document.getElementById('top-cta');
    const topCtaLabel = document.getElementById('top-cta-label');
    const restartBtn = document.getElementById('restart-btn');
    const bottomOverlay = document.getElementById('bottom-overlay');
    const bottomCta = document.getElementById('bottom-cta');
    const bottomCtaLabel = document.getElementById('bottom-cta-label');

    // Apply config
    video.src = config.videoUrl || '';
    if (config.ctaLabel && config.ctaUrl) {{
      topCta.href = config.ctaUrl;
      topCtaLabel.textContent = config.ctaLabel;
      bottomCta.href = config.ctaUrl;
      bottomCtaLabel.textContent = config.ctaLabel;
    }} else {{
      topCta.style.display = 'none';
      bottomCta.style.display = 'none';
    }}

    // Show top CTA once video starts
    video.addEventListener('play', () => {{
      if (config.ctaLabel && config.ctaUrl) {{
        topCta.classList.add('visible');
      }}
    }});

    // Show bottom overlay at video end
    video.addEventListener('ended', () => {{
      if (config.ctaLabel && config.ctaUrl) {{
        bottomOverlay.classList.add('visible');
      }}
    }});
    video.addEventListener('timeupdate', () => {{
      if (video.duration && video.currentTime >= video.duration - 0.5) {{
        if (config.ctaLabel && config.ctaUrl) {{
          bottomOverlay.classList.add('visible');
        }}
      }}
    }});

    // Restart button
    restartBtn.addEventListener('click', () => {{
      bottomOverlay.classList.remove('visible');
      video.currentTime = 0;
      video.play().catch(() => {{}});
    }});
  </script>
</body>
</html>
"""

    def _upload_sales_cta_html(
        self,
        *,
        video_id: str,
        title: str,
        video_url: str,
        customer_name: str,
        sales_cta_label: str,
        sales_cta_url: str,
    ) -> str | None:
        html_dir = settings.output_dir / "interactive" / "sales"
        html_dir.mkdir(parents=True, exist_ok=True)
        html_path = html_dir / f"{video_id}.html"
        html_path.write_text(
            self._build_sales_cta_html(
                video_id=video_id,
                title=title,
                video_url=video_url,
                customer_name=customer_name,
                sales_cta_label=sales_cta_label,
                sales_cta_url=sales_cta_url,
            ),
            encoding="utf-8",
        )
        return self.s3_service.upload_file(
            html_path,
            f"interactive/sales/{video_id}.html",
            content_type="text/html; charset=utf-8",
        )

    # ------------------------------------------------------------------
    # Interactive Loan Offer static HTML (loan_offer_interactive)
    # ------------------------------------------------------------------

    def _build_loan_offer_interactive_html(
        self,
        *,
        video_id: str,
        title: str,
        video_url: str,
        customer_name: str,
        client_name: str,
        contact_details: str,
        primary_color: str,
        interactive_cta_color: str,
        interactive_background_color: str,
        subtitles: list,
        loan_offer: dict,
    ) -> str:
        escaped_title = html.escape(title or "Loan Offer")
        payload = json.dumps(
            {
                "videoUrl": video_url,
                "customerName": customer_name,
                "clientName": client_name,
                "phoneNumber": contact_details or loan_offer.get("cta_phone_number", "1800-555-999"),
                "primaryColor": primary_color or "#053666",
                "ctaColor": interactive_cta_color or "#702082",
                "bgColor": interactive_background_color or "#f5f7fb",
                "subtitles": subtitles or [],
                "loanOffer": loan_offer or {},
            },
            ensure_ascii=False,
        )
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escaped_title}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: var(--bg, #f5f7fb);
      color: #111827;
    }}
    main {{
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .shell {{
      position: relative;
      width: min(100%, 430px);
      aspect-ratio: 9 / 16;
      max-height: 100dvh;
      overflow: hidden;
      border-radius: 24px;
      background: #000;
      border: 10px solid #0f172a;
      box-shadow: 0 24px 70px rgba(0,0,0,0.4);
    }}
    video {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }}
    /* Play overlay */
    #play-overlay {{
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      background: rgba(15,23,42,0.65);
      color: #fff;
      z-index: 30;
      cursor: pointer;
      border: none;
    }}
    #play-overlay .play-circle {{
      width: 64px;
      height: 64px;
      border-radius: 50%;
      background: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    #play-overlay .play-circle svg {{ color: #0f172a; margin-left: 4px; }}
    #play-overlay .play-label {{
      margin-top: 20px;
      font-size: 14px;
      font-weight: 600;
      letter-spacing: 0.02em;
    }}
    /* Top controls */
    #top-controls {{
      position: absolute;
      top: 16px;
      right: 16px;
      display: none;
      gap: 8px;
      z-index: 50;
    }}
    #top-controls.visible {{ display: flex; }}
    .ctrl-btn {{
      width: 40px;
      height: 40px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 1px solid rgba(255,255,255,0.3);
      cursor: pointer;
      backdrop-filter: blur(8px);
      transition: transform 0.2s;
    }}
    .ctrl-btn:hover {{ transform: scale(1.08); }}
    /* Avail now transparent click target */
    #avail-target {{
      position: absolute;
      left: 7.5%;
      right: 7.5%;
      bottom: 5.7%;
      height: 5.5%;
      z-index: 30;
      display: none;
      cursor: pointer;
      border: none;
      background: transparent;
    }}
    #avail-target.visible {{ display: block; }}
    /* Selector overlay */
    #selector-overlay {{
      position: absolute;
      top: 15%;
      left: 0;
      right: 0;
      bottom: 0;
      padding: 0 5%;
      display: none;
      flex-direction: column;
      gap: 12px;
      z-index: 20;
      overflow-y: auto;
    }}
    #selector-overlay.visible {{ display: flex; }}
    .card {{
      width: 100%;
      background: #fff;
      border-radius: 24px;
      padding: 16px;
      box-shadow: 0 8px 30px rgba(0,0,0,0.06);
    }}
    .card-header {{
      display: flex;
      align-items: center;
      margin-bottom: 16px;
    }}
    .card-icon {{
      width: 32px;
      height: 32px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 12px;
      flex-shrink: 0;
    }}
    .card-title {{ font-size: 16px; font-weight: 700; color: #111827; }}
    /* Slider */
    .slider-wrap {{
      position: relative;
      width: calc(100% - 60px);
      margin: 0 auto 12px;
      height: 8px;
      background: #f3f4f6;
      border-radius: 8px;
    }}
    .slider-fill {{
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      border-radius: 8px;
    }}
    .slider-thumb {{
      position: absolute;
      top: -6px;
      width: 20px;
      height: 20px;
      background: #fff;
      border-radius: 50%;
      border-width: 5px;
      border-style: solid;
      transform: translateX(-50%);
      pointer-events: none;
    }}
    .slider-tooltip {{
      position: absolute;
      top: -45px;
      padding: 6px 14px;
      border-radius: 10px;
      font-size: 14px;
      font-weight: 700;
      color: #fff;
      transform: translateX(-50%);
      white-space: nowrap;
      pointer-events: none;
    }}
    .slider-tooltip::after {{
      content: '';
      position: absolute;
      bottom: -4px;
      left: 50%;
      transform: translateX(-50%) rotate(45deg);
      width: 8px;
      height: 8px;
    }}
    input[type=range].hidden-range {{
      position: absolute;
      inset: 0;
      opacity: 0;
      cursor: pointer;
      z-index: 10;
      margin: 0;
      padding: 0;
      width: 100%;
      height: 100%;
    }}
    .minmax {{
      display: flex;
      justify-content: space-between;
      color: #9ca3af;
      font-size: 12px;
      font-weight: 500;
      margin-bottom: 16px;
    }}
    .divider {{ width: 100%; height: 1px; background: #f3f4f6; margin-bottom: 16px; }}
    /* Tenure pills */
    .tenure-row {{
      display: flex;
      justify-content: space-between;
      gap: 6px;
    }}
    .tenure-pill {{
      flex: 1;
      padding: 10px 0;
      border-radius: 10px;
      display: flex;
      flex-direction: column;
      align-items: center;
      cursor: pointer;
      font-size: 15px;
      font-weight: 800;
      transition: all 0.15s;
    }}
    .tenure-pill .months {{ font-size: 10px; font-weight: 500; opacity: 0.6; }}
    /* Summary card */
    .summary-row {{
      display: flex;
      justify-content: space-between;
      font-size: 14px;
      margin-bottom: 12px;
    }}
    .summary-label {{ display: flex; align-items: center; color: #4b5563; }}
    .summary-label svg {{ margin-right: 6px; opacity: 0.6; }}
    .summary-value {{ font-weight: 600; color: #111827; }}
    .summary-emi {{ display: flex; justify-content: space-between; align-items: center; }}
    .summary-emi-label {{ display: flex; align-items: center; font-size: 14px; font-weight: 700; }}
    .summary-emi-label svg {{ margin-right: 6px; }}
    .summary-emi-val {{ font-size: 22px; font-weight: 800; }}
    /* Proceed button */
    .proceed-btn {{
      margin-bottom: 13%;
      width: calc(100% - 15.18%);
      margin-left: 7.59%;
      margin-right: 7.59%;
      height: 9.62%;
      min-height: 48px;
      max-height: 56px;
      border-radius: 30px;
      font-size: 18px;
      font-weight: 800;
      color: #fff;
      border: 1px solid rgba(255,255,255,0.25);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: transform 0.2s;
    }}
    .proceed-btn:hover {{ transform: scale(1.02); }}
    /* Confirmed screen */
    #confirmed-overlay {{
      position: absolute;
      inset: 0;
      z-index: 40;
      display: none;
      flex-direction: column;
      padding: 20px 16px;
      overflow-y: auto;
    }}
    #confirmed-overlay.visible {{ display: flex; }}
    .confirm-card {{
      width: 100%;
      background: rgba(255,255,255,0.95);
      border-radius: 28px;
      padding: 20px 16px;
      box-shadow: 0 12px 30px rgba(0,0,0,0.1);
      border: 1px solid rgba(255,255,255,0.8);
      display: flex;
      flex-direction: column;
      align-items: center;
    }}
    .check-circle {{
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: linear-gradient(135deg, #4ade80, #16a34a);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 8px 20px rgba(22,163,74,0.3);
      margin-bottom: 12px;
    }}
    .confirm-title {{ font-size: 24px; font-weight: 800; color: #1e1b4b; margin-bottom: 6px; }}
    .confirm-sub {{ font-size: 13px; color: #6b7280; font-weight: 500; margin-bottom: 16px; text-align: center; }}
    .details-box {{
      width: 100%;
      display: flex;
      justify-content: space-between;
      padding: 12px 6px;
      border-radius: 16px;
      margin-bottom: 20px;
    }}
    .details-col {{
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
    }}
    .details-icon {{
      width: 28px;
      height: 28px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 4px;
    }}
    .details-val {{ font-size: 16px; font-weight: 800; color: #1e1b4b; margin-bottom: 2px; }}
    .details-lbl {{ font-size: 10px; color: #6b7280; font-weight: 500; }}
    .vdivider {{ width: 1px; }}
    .next-title {{ font-size: 15px; font-weight: 700; color: #111827; margin-bottom: 12px; }}
    .steps-wrap {{ position: relative; padding-left: 24px; }}
    .vline {{ position: absolute; left: 7px; top: 10px; bottom: 20px; width: 2px; }}
    .step-row {{
      display: flex;
      margin-bottom: 12px;
      position: relative;
    }}
    .step-dot {{
      position: absolute;
      left: -24px;
      top: 4px;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: #fff;
      border: 2px solid #22c55e;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #22c55e;
      z-index: 1;
    }}
    .step-icon {{
      width: 28px;
      height: 28px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 12px;
      flex-shrink: 0;
    }}
    .step-title {{ font-size: 13px; font-weight: 700; color: #1e1b4b; margin-bottom: 2px; }}
    .step-desc {{ font-size: 11px; color: #6b7280; line-height: 1.3; }}
    .call-btn {{
      width: calc(100% - 15.18%);
      margin-left: 7.59%;
      margin-right: 7.59%;
      height: 9.62%;
      min-height: 48px;
      max-height: 56px;
      border-radius: 30px;
      font-size: 18px;
      font-weight: 800;
      color: #fff;
      border: 1px solid rgba(255,255,255,0.25);
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      cursor: pointer;
      text-decoration: none;
      margin-top: auto;
      transition: transform 0.2s;
    }}
    .call-btn:hover {{ transform: scale(1.02); }}
    .replay-link {{
      margin-top: 16px;
      cursor: pointer;
      color: #6b7280;
      font-size: 13px;
      font-weight: 600;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .footer-secure {{
      display: flex;
      justify-content: center;
      align-items: center;
      margin-top: 12px;
      color: #6b7280;
      font-size: 11px;
      font-weight: 500;
    }}
    .footer-secure svg {{ margin-right: 4px; }}
  </style>
</head>
<body>
<main>
  <div class="shell">
    <video id="v" src="" playsinline preload="metadata"></video>

    <!-- Play overlay -->
    <button id="play-overlay" type="button">
      <div class="play-circle">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5 3 19 12 5 21 5 3"/></svg>
      </div>
      <div class="play-label" id="play-label">Tap to Play</div>
    </button>

    <!-- Top controls (restart + play/pause) -->
    <div id="top-controls">
      <button id="restart-btn" class="ctrl-btn" title="Restart">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 2v6h6"/><path d="M3 13a9 9 0 1 0 3-7.7L3 8"/></svg>
      </button>
      <button id="play-pause-btn" class="ctrl-btn" title="Play/Pause">
        <svg id="pp-icon" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5 3 19 12 5 21 5 3"/></svg>
      </button>
    </div>

    <!-- Transparent avail-now click target (over video button) -->
    <button id="avail-target" type="button" aria-label="Continue to view loan offer"></button>

    <!-- Selector overlay -->
    <div id="selector-overlay">
      <!-- Amount card -->
      <div class="card">
        <div class="card-header">
          <div class="card-icon" id="amount-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 12V8H6a2 2 0 0 1-2-2c0-1.1.9-2 2-2h12v4"/><path d="M4 6v12c0 1.1.9 2 2 2h14v-4"/><path d="M18 12a2 2 0 0 0-2 2c0 1.1.9 2 2 2h4v-4h-4z"/></svg>
          </div>
          <div class="card-title">Loan Amount</div>
        </div>
        <div class="slider-wrap" id="slider-wrap">
          <input type="range" class="hidden-range" id="amount-slider" min="0" value="0" />
          <div class="slider-fill" id="slider-fill"></div>
          <div class="slider-thumb" id="slider-thumb"></div>
          <div class="slider-tooltip" id="slider-tooltip"><span id="tooltip-val"></span><div class="slider-tooltip-arrow" id="tt-arrow"></div></div>
        </div>
        <div class="minmax"><span id="min-label"></span><span id="max-label"></span></div>
        <div class="divider"></div>
        <div class="card-header" style="margin-bottom:12px">
          <div class="card-icon" id="tenure-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
          </div>
          <div class="card-title">Tenure <span style="font-weight:400;color:#6b7280;font-size:13px">(in Months)</span></div>
        </div>
        <div class="tenure-row" id="tenure-row"></div>
      </div>

      <!-- Summary card -->
      <div class="card">
        <div class="card-header" style="margin-bottom:12px">
          <div class="card-icon" id="summary-icon">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z"/><path d="M16 14h-6"/><path d="M12 18H8"/><path d="M16 10h-2"/><path d="M8 10h.01"/></svg>
          </div>
          <div class="card-title">Loan Summary</div>
        </div>
        <div class="summary-row">
          <div class="summary-label"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"/><path d="M12 18V6"/></svg>&nbsp;Amount</div>
          <div class="summary-value" id="sum-amount"></div>
        </div>
        <div class="summary-row" style="padding-bottom:12px;border-bottom:1px dashed #e5e7eb;margin-bottom:12px">
          <div class="summary-label"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>&nbsp;Tenure</div>
          <div class="summary-value" id="sum-tenure"></div>
        </div>
        <div class="summary-emi" id="sum-emi-row">
          <div class="summary-emi-label"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="18" y="3" width="4" height="18"/><rect x="10" y="8" width="4" height="13"/><rect x="2" y="13" width="4" height="8"/></svg>&nbsp;Monthly EMI</div>
          <div class="summary-emi-val" id="sum-emi"></div>
        </div>
      </div>

      <!-- Proceed button -->
      <div class="proceed-btn" id="proceed-btn">Proceed</div>
    </div>

    <!-- Confirmed overlay -->
    <div id="confirmed-overlay">
      <div class="confirm-card">
        <div class="check-circle">
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
        </div>
        <div class="confirm-title">Offer Confirmed!</div>
        <div class="confirm-sub">Our team will help you complete the next steps</div>

        <div class="details-box" id="details-box">
          <div class="details-col">
            <div class="details-icon" id="d-icon-1">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 12V8H6a2 2 0 0 1-2-2c0-1.1.9-2 2-2h12v4"/><path d="M4 6v12c0 1.1.9 2 2 2h14v-4"/><path d="M18 12a2 2 0 0 0-2 2c0 1.1.9 2 2 2h4v-4h-4z"/></svg>
            </div>
            <div class="details-val" id="conf-amount"></div>
            <div class="details-lbl">Loan Amount</div>
          </div>
          <div class="vdivider" id="vd1"></div>
          <div class="details-col">
            <div class="details-icon" id="d-icon-2">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
            </div>
            <div class="details-val" id="conf-tenure"></div>
            <div class="details-lbl">Months</div>
          </div>
          <div class="vdivider" id="vd2"></div>
          <div class="details-col">
            <div class="details-icon" id="d-icon-3">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="18" y="3" width="4" height="18"/><rect x="10" y="8" width="4" height="13"/><rect x="2" y="13" width="4" height="8"/></svg>
            </div>
            <div class="details-val" id="conf-emi"></div>
            <div class="details-lbl">EMI</div>
          </div>
        </div>

        <div style="width:100%;margin-bottom:20px">
          <div class="next-title">What's next?</div>
          <div class="steps-wrap">
            <div class="vline" id="vline"></div>
            <div class="step-row">
              <div class="step-dot"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></div>
              <div class="step-icon" id="step1-icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg></div>
              <div><div class="step-title">1. Document verification</div><div class="step-desc">Our team will verify your documents within 24 hours</div></div>
            </div>
            <div class="step-row">
              <div class="step-dot"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></div>
              <div class="step-icon" id="step2-icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg></div>
              <div><div class="step-title">2. Agreement signing</div><div class="step-desc">e-Sign the agreement securely from your device</div></div>
            </div>
            <div class="step-row">
              <div class="step-dot"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></div>
              <div class="step-icon" id="step3-icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="20" width="20" height="2"/><rect x="4" y="10" width="2" height="7"/><rect x="10" y="10" width="2" height="7"/><rect x="18" y="10" width="2" height="7"/><polygon points="12 2 2 7 22 7 12 2"/></svg></div>
              <div><div class="step-title">3. Disbursal</div><div class="step-desc">Loan amount will be credited to your account</div></div>
            </div>
          </div>
        </div>

        <a id="call-btn" class="call-btn" href="">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
          <span id="call-btn-label">Call Now</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
        </a>

        <div class="replay-link" id="replay-link" style="display:none">
          <svg style="margin-right:4px" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 2v6h6"/><path d="M3 13a9 9 0 1 0 3-7.7L3 8"/></svg>
          Replay offer
        </div>

        <div class="footer-secure">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
          Your information is 100% secure with us
        </div>
      </div>
    </div>
  </div>
</main>

<script>
(function() {{
  const cfg = {payload};

  // ---- Helpers ----
  function fmt(val, fallback) {{
    fallback = fallback || 'NA';
    var s = String(val || '').trim();
    var n = Number(s.replace(/[^\d.]/g, ''));
    if (!s || !isFinite(n) || n <= 0) return s || fallback;
    return '\u20b9 ' + Math.round(n).toLocaleString('en-IN');
  }}

  function safe(val, fb) {{
    fb = fb || '';
    var s = String(val === null || val === undefined ? '' : val).trim();
    return s || fb;
  }}

  function isAvail(val) {{
    var s = safe(val).toLowerCase();
    return Boolean(s && s !== 'na' && s !== 'null');
  }}

  // ---- Build rows ----
  var TENURES = ['24','30','36','42','48','60'];
  var offer = cfg.loanOffer || {{}};
  var rows = [];
  TENURES.forEach(function(t) {{
    var amt = offer['month_' + t + '_loan_amount'];
    var emi = offer['emi_calculation' + t];
    if (isAvail(amt)) rows.push({{ tenure: t, amount: safe(amt), emi: safe(emi) }});
  }});
  if (!rows.length) {{
    rows = [{{ tenure: safe(offer.max_tenure,'60'), amount: safe(offer.max_loan_amount,'105000'), emi: safe(offer.max_emi,'3398') }}];
  }}

  var uniqueAmounts = [];
  rows.forEach(function(r) {{ if (uniqueAmounts.indexOf(r.amount) < 0) uniqueAmounts.push(r.amount); }});
  uniqueAmounts.sort(function(a,b) {{ return Number(a)-Number(b); }});

  function getInitialRow() {{
    var maxAmt = safe(offer.max_loan_amount);
    var maxTen = safe(offer.max_tenure);
    return rows.find(function(r) {{ return r.amount === maxAmt && r.tenure === maxTen; }})
      || rows.find(function(r) {{ return r.amount === maxAmt; }})
      || rows[rows.length - 1];
  }}

  var selRow = getInitialRow();
  var selAmount = selRow.amount;
  var selTenure = selRow.tenure;

  // ---- Subtitle timing ----
  function findSubStart(phrase) {{
    var subs = cfg.subtitles || [];
    var needle = phrase.toLowerCase();
    for (var i = 0; i < subs.length; i++) {{
      var s = subs[i];
      if (typeof s.text !== 'string') continue;
      var text = s.text.toLowerCase();
      var idx = text.indexOf(needle);
      if (idx >= 0) {{
        if (idx <= 0) return s.start;
        return s.start + (idx / text.length) * (s.end - s.start);
      }}
    }}
    return null;
  }}

  // ---- Colors ----
  var ctaColor = cfg.ctaColor || '#702082';
  var bgColor = cfg.bgColor || '#f5f7fb';
  var ctaDark = ctaColor + 'e6';

  function lum(hex) {{
    var c = hex.replace('#','');
    if (c.length < 6) return 128;
    var r = parseInt(c.substring(0,2),16);
    var g = parseInt(c.substring(2,4),16);
    var b = parseInt(c.substring(4,6),16);
    return (r*299+g*587+b*114)/1000;
  }}
  var ctaTextColor = lum(ctaColor) > 145 ? '#000000' : '#ffffff';

  // Apply bg
  document.body.style.background = bgColor;

  // ---- DOM refs ----
  var video = document.getElementById('v');
  var playOverlay = document.getElementById('play-overlay');
  var playLabel = document.getElementById('play-label');
  var topControls = document.getElementById('top-controls');
  var restartBtn = document.getElementById('restart-btn');
  var ppBtn = document.getElementById('play-pause-btn');
  var ppIcon = document.getElementById('pp-icon');
  var availTarget = document.getElementById('avail-target');
  var selectorOverlay = document.getElementById('selector-overlay');
  var amountSlider = document.getElementById('amount-slider');
  var sliderFill = document.getElementById('slider-fill');
  var sliderThumb = document.getElementById('slider-thumb');
  var sliderTooltip = document.getElementById('slider-tooltip');
  var tooltipVal = document.getElementById('tooltip-val');
  var ttArrow = document.getElementById('tt-arrow');
  var tenureRow = document.getElementById('tenure-row');
  var sumAmount = document.getElementById('sum-amount');
  var sumTenure = document.getElementById('sum-tenure');
  var sumEmi = document.getElementById('sum-emi');
  var proceedBtn = document.getElementById('proceed-btn');
  var confirmedOverlay = document.getElementById('confirmed-overlay');
  var confAmount = document.getElementById('conf-amount');
  var confTenure = document.getElementById('conf-tenure');
  var confEmi = document.getElementById('conf-emi');
  var callBtn = document.getElementById('call-btn');
  var callLabel = document.getElementById('call-btn-label');
  var replayLink = document.getElementById('replay-link');

  // Apply colors to themed elements
  function styleEl(el, props) {{ if (el) Object.assign(el.style, props); }}
  styleEl(document.getElementById('amount-icon'), {{ background: ctaColor+'1a', color: ctaColor }});
  styleEl(document.getElementById('tenure-icon'), {{ background: ctaColor+'1a', color: ctaColor }});
  styleEl(document.getElementById('summary-icon'), {{ background: ctaColor+'1a', color: ctaColor }});
  styleEl(document.getElementById('sum-emi-row'), {{ color: ctaColor }});
  styleEl(document.getElementById('details-box'), {{ background: ctaColor+'0d', border: '1px solid '+ctaColor+'33' }});
  styleEl(document.getElementById('d-icon-1'), {{ background: ctaColor+'26', color: ctaColor }});
  styleEl(document.getElementById('d-icon-2'), {{ background: ctaColor+'26', color: ctaColor }});
  styleEl(document.getElementById('d-icon-3'), {{ background: ctaColor+'26', color: ctaColor }});
  styleEl(document.getElementById('vd1'), {{ background: ctaColor+'33' }});
  styleEl(document.getElementById('vd2'), {{ background: ctaColor+'33' }});
  styleEl(document.getElementById('vline'), {{ background: ctaColor+'33' }});
  styleEl(document.getElementById('step1-icon'), {{ background: ctaColor+'1a', color: ctaColor }});
  styleEl(document.getElementById('step2-icon'), {{ background: ctaColor+'1a', color: ctaColor }});
  styleEl(document.getElementById('step3-icon'), {{ background: ctaColor+'1a', color: ctaColor }});
  styleEl(restartBtn, {{ background: ctaDark, color: ctaTextColor, boxShadow: '0 8px 20px '+ctaColor+'66' }});
  styleEl(ppBtn, {{ background: ctaDark, color: ctaTextColor, boxShadow: '0 8px 20px '+ctaColor+'66' }});
  styleEl(proceedBtn, {{ background: 'linear-gradient(135deg,'+ctaColor+' 0%,'+ctaDark+' 100%)', color: ctaTextColor }});
  styleEl(callBtn, {{ background: 'linear-gradient(135deg,'+ctaColor+' 0%,'+ctaDark+' 100%)', color: ctaTextColor }});
  styleEl(confirmedOverlay, {{ background: bgColor }});
  styleEl(selectorOverlay, {{ background: bgColor }});

  // Slider fill/thumb color
  sliderFill.style.background = ctaColor;
  sliderThumb.style.borderColor = ctaColor;
  sliderThumb.style.boxShadow = '0 2px 8px '+ctaColor+'4d';
  sliderTooltip.style.background = 'linear-gradient(135deg,'+ctaColor+','+ctaDark+')';
  sliderTooltip.style.color = ctaTextColor;
  if (ttArrow) {{ ttArrow.style.background = ctaColor; }}

  // Call button
  var phone = safe(cfg.phoneNumber, '1800-555-999').replace(/\\s+/g,'');
  callBtn.href = 'tel:' + phone;
  callLabel.textContent = 'Call ' + safe(cfg.phoneNumber, '1800-555-999');

  // Client name in play label
  playLabel.textContent = safe(cfg.clientName) || 'Tap to Play';

  // Video
  video.src = cfg.videoUrl || '';

  // Dynamic sizing of the proceed and call buttons to perfectly match the video's CTA button shape
  function updateButtonSizes() {{
    var shell = document.querySelector('.shell');
    if (!shell) return;
    var w = shell.clientWidth;
    var btnHeight = w * (104 / 1080);
    var btnRadius = w * (32 / 1080);
    var btnFontSize = w * (36 / 1080);

    if (proceedBtn) {{
      proceedBtn.style.height = btnHeight + 'px';
      proceedBtn.style.minHeight = btnHeight + 'px';
      proceedBtn.style.maxHeight = btnHeight + 'px';
      proceedBtn.style.borderRadius = btnRadius + 'px';
      proceedBtn.style.fontSize = btnFontSize + 'px';
      proceedBtn.style.boxShadow = '0 10px 25px ' + ctaColor + '40, inset 0 1px 0 rgba(255, 255, 255, 0.25)';
    }}
    if (callBtn) {{
      callBtn.style.height = btnHeight + 'px';
      callBtn.style.minHeight = btnHeight + 'px';
      callBtn.style.maxHeight = btnHeight + 'px';
      callBtn.style.borderRadius = btnRadius + 'px';
      callBtn.style.fontSize = btnFontSize + 'px';
      callBtn.style.boxShadow = '0 10px 25px ' + ctaColor + '40, inset 0 1px 0 rgba(255, 255, 255, 0.25)';
    }}
  }}
  updateButtonSizes();
  window.addEventListener('resize', updateButtonSizes);
  video.addEventListener('loadedmetadata', updateButtonSizes);

  // ---- Slider rendering ----
  amountSlider.max = String(Math.max(0, uniqueAmounts.length - 1));

  function renderSlider() {{
    var idx = uniqueAmounts.indexOf(selAmount);
    if (idx < 0) idx = uniqueAmounts.length - 1;
    var pct = uniqueAmounts.length > 1 ? (idx / (uniqueAmounts.length - 1)) * 100 : 100;
    amountSlider.value = String(idx);
    sliderFill.style.width = pct + '%';
    var thumbLeft = 'calc(' + pct + '% + ' + (10 - (pct/100)*20) + 'px)';
    sliderThumb.style.left = thumbLeft;
    sliderTooltip.style.left = thumbLeft;
    tooltipVal.textContent = fmt(selAmount);
    document.getElementById('min-label').textContent = fmt(uniqueAmounts[0]);
    document.getElementById('max-label').textContent = fmt(uniqueAmounts[uniqueAmounts.length-1]);
  }}

  // ---- Tenure pills ----
  var DISPLAY_TENURES = ['12','24','36','48','60'];
  function renderTenurePills() {{
    var available = rows.filter(function(r) {{ return r.amount === selAmount; }});
    if (!available.length) available = rows;
    tenureRow.innerHTML = '';
    DISPLAY_TENURES.forEach(function(t) {{
      var isSelected = t === selTenure;
      var isAvailable = available.some(function(r) {{ return r.tenure === t; }});
      var pill = document.createElement('div');
      pill.className = 'tenure-pill';
      pill.style.border = isSelected ? 'none' : '1px solid #e5e7eb';
      pill.style.background = isSelected ? 'linear-gradient(135deg,'+ctaColor+','+ctaDark+')' : '#fff';
      pill.style.color = isSelected ? ctaTextColor : '#4b5563';
      pill.style.cursor = isAvailable ? 'pointer' : 'not-allowed';
      pill.style.opacity = (isAvailable || isSelected) ? '1' : '0.4';
      pill.style.boxShadow = isSelected ? '0 4px 12px '+ctaColor+'33' : 'none';
      pill.innerHTML = '<div>' + t + '</div><div class="months">Months</div>';
      if (isAvailable) {{
        pill.addEventListener('click', function() {{
          selTenure = t;
          updateSelRow();
        }});
      }}
      tenureRow.appendChild(pill);
    }});
  }}

  function updateSelRow() {{
    var found = rows.find(function(r) {{ return r.amount === selAmount && r.tenure === selTenure; }})
      || rows.find(function(r) {{ return r.tenure === selTenure; }})
      || getInitialRow();
    selRow = found;
    renderSlider();
    renderTenurePills();
    renderSummary();
  }}

  function renderSummary() {{
    sumAmount.textContent = fmt(selRow.amount);
    sumTenure.textContent = selRow.tenure + ' Months';
    sumEmi.textContent = fmt(selRow.emi);
    confAmount.textContent = fmt(selRow.amount);
    confTenure.textContent = selRow.tenure;
    confEmi.innerHTML = fmt(selRow.emi) + '<span style="font-size:11px;color:#6b7280;font-weight:500">/mo</span>';
  }}

  renderSlider();
  renderTenurePills();
  renderSummary();

  amountSlider.addEventListener('input', function() {{
    var nextAmount = uniqueAmounts[Number(this.value)];
    var nextRow = rows.find(function(r) {{ return r.amount === nextAmount; }}) || rows[0];
    selAmount = nextAmount;
    selTenure = nextRow.tenure;
    updateSelRow();
  }});

  // ---- State machine ----
  var hasStarted = false;
  var hasDismissedAvail = false;
  var hasDismissedSelector = false;
  var confirmed = false;
  var hasEnded = false;
  var videoDuration = null;

  function getIntroTransitionTime() {{
    var detected = findSubStart('now, choose') || findSubStart('choose your') || findSubStart('select your')
      || findSubStart('preferred') || findSubStart('\u0905\u092a\u0928\u0940 \u092a\u0938\u0902\u0926 \u0915\u0940')
      || findSubStart('\u092a\u0938\u0902\u0926 \u0915\u0940') || findSubStart('\u0905\u0935\u0927\u093f') || 10.8;
    if (!videoDuration || !isFinite(videoDuration)) return detected;
    var finalHold = Math.min(6, Math.max(4, videoDuration * 0.34));
    var selHold = Math.min(5, Math.max(3, videoDuration * 0.24));
    var latest = Math.max(4, videoDuration - finalHold - selHold);
    return Math.min(detected, latest);
  }}

  function getSelectorTransitionTime(introT) {{
    var detected = findSubStart('thank you') || findSubStart('your offer') || findSubStart('our team')
      || findSubStart('assist') || findSubStart('\u0927\u0928\u094d\u092f\u0935\u093e\u0926') || findSubStart('\u0939\u092e\u093e\u0930\u0940 \u091f\u0940\u092e')
      || findSubStart('\u092e\u0926\u0926') || findSubStart('\u0938\u0939\u093e\u092f\u0924\u093e') || findSubStart('\u0915\u0949\u0932 \u0915\u0930\u0947\u0902')
      || findSubStart('\u0938\u0902\u092a\u0930\u094d\u0915') || findSubStart('call us') || findSubStart('contact')
      || findSubStart('support') || 22.0;
    if (!videoDuration || !isFinite(videoDuration)) return detected;
    var finalHold = Math.min(5, Math.max(3, videoDuration * 0.24));
    var latest = Math.max(introT + 1.2, videoDuration - finalHold);
    var earliest = Math.min(videoDuration - 1.2, introT + 1.2);
    return Math.min(Math.max(detected, earliest), latest);
  }}

  video.addEventListener('loadedmetadata', function() {{
    if (isFinite(this.duration) && this.duration > 0) videoDuration = this.duration;
  }});

  function playIcons(playing) {{
    ppIcon.innerHTML = playing
      ? '<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>'
      : '<polygon points="5 3 19 12 5 21 5 3"/>';
  }}

  video.addEventListener('play', function() {{ playIcons(true); }});
  video.addEventListener('pause', function() {{ playIcons(false); }});

  video.addEventListener('timeupdate', function() {{
    if (confirmed) return;
    var t = video.currentTime;
    var introT = getIntroTransitionTime();
    var introEnd = Math.max(0, introT - 0.35);
    var selT = getSelectorTransitionTime(introT);
    var selEnd = Math.max(0, selT - 0.1);

    // Show avail target 2.5s before intro pause
    if (t >= Math.max(0, introEnd - 2.5) && !hasDismissedAvail && !confirmed) {{
      availTarget.classList.add('visible');
    }}
    // Pause at intro end
    if (t >= introEnd && !hasDismissedAvail && !confirmed) {{
      video.pause();
      video.currentTime = introEnd;
    }}
    // Show selector as soon as the intro phase transition is active (t >= introT)
    if (hasDismissedAvail && t >= introT && !hasDismissedSelector && !confirmed) {{
      selectorOverlay.classList.add('visible');
    }}
    // Pause at selector end
    if (hasDismissedAvail && t >= selEnd && !hasDismissedSelector && !confirmed) {{
      video.pause();
      video.currentTime = selEnd;
    }}
  }});

  video.addEventListener('ended', function() {{
    confirmed = true;
    hasEnded = true;
    selectorOverlay.classList.remove('visible');
    confirmedOverlay.classList.add('visible');
    replayLink.style.display = 'flex';
  }});

  // ---- Interactions ----
  playOverlay.addEventListener('click', function() {{
    hasStarted = true;
    playOverlay.style.display = 'none';
    topControls.classList.add('visible');
    video.currentTime = 0;
    video.play().catch(function() {{}});
  }});

  restartBtn.addEventListener('click', function() {{
    hasStarted = true;
    hasDismissedAvail = false;
    hasDismissedSelector = false;
    confirmed = false;
    hasEnded = false;
    availTarget.classList.remove('visible');
    selectorOverlay.classList.remove('visible');
    confirmedOverlay.classList.remove('visible');
    replayLink.style.display = 'none';
    video.currentTime = 0;
    video.play().catch(function() {{}});
  }});

  ppBtn.addEventListener('click', function() {{
    if (video.paused) video.play().catch(function() {{}}); else video.pause();
  }});

  availTarget.addEventListener('click', function() {{
    hasDismissedAvail = true;
    availTarget.classList.remove('visible');
    video.play().catch(function() {{}});
  }});

  proceedBtn.addEventListener('click', function() {{
    hasDismissedSelector = true;
    confirmed = true;
    selectorOverlay.classList.remove('visible');
    confirmedOverlay.classList.add('visible');
    video.play().catch(function() {{}});
  }});

  replayLink.addEventListener('click', function() {{
    restartBtn.click();
  }});

}})();
</script>
</body>
</html>
"""

    def _upload_loan_offer_interactive_html(
        self,
        *,
        video_id: str,
        title: str,
        video_url: str,
        customer_name: str,
        client_name: str,
        contact_details: str,
        primary_color: str,
        interactive_cta_color: str,
        interactive_background_color: str,
        subtitles: list,
        loan_offer: dict,
    ) -> str | None:
        html_dir = settings.output_dir / "interactive" / "loan-offer"
        html_dir.mkdir(parents=True, exist_ok=True)
        html_path = html_dir / f"{video_id}.html"
        html_path.write_text(
            self._build_loan_offer_interactive_html(
                video_id=video_id,
                title=title,
                video_url=video_url,
                customer_name=customer_name,
                client_name=client_name,
                contact_details=contact_details,
                primary_color=primary_color,
                interactive_cta_color=interactive_cta_color,
                interactive_background_color=interactive_background_color,
                subtitles=subtitles,
                loan_offer=loan_offer,
            ),
            encoding="utf-8",
        )
        return self.s3_service.upload_file(
            html_path,
            f"interactive/loan-offer/{video_id}.html",
            content_type="text/html; charset=utf-8",
        )

    async def run_forever(self) -> None:
        """Continuously poll SQS for remotion jobs until the process is killed."""
        logger.info("RemotionJobWorker: Starting SQS polling loop...")
        while True:
            try:
                await self._poll_once()
            except Exception as exc:
                logger.error(f"RemotionJobWorker: Unexpected error in poll loop: {exc}")
            await asyncio.sleep(settings.sqs_poll_interval_seconds if hasattr(settings, 'sqs_poll_interval_seconds') else 5)

    async def _poll_once(self) -> None:
        """Fetch one batch of messages from SQS and process them."""
        try:
            messages = await asyncio.to_thread(
                self.sqs_service.receive_messages,
                self.queue_url,
                max_messages=5
            )
            for message in messages:
                import json
                body_raw = message.get("Body", "{}")
                try:
                    body = json.loads(body_raw)
                except Exception:
                    body = {}

                video_id = body.get('_id')
                receipt_handle = message.get("ReceiptHandle")

                if not video_id:
                    logger.warning(f"RemotionJobWorker: Received message with no video_id/job_id: {body}, skipping.")
                    if receipt_handle:
                        self.sqs_service.delete_message(receipt_handle, self.queue_url)
                    continue

                await self._process_job(str(video_id), receipt_handle)

        except Exception as exc:
            logger.error(f"RemotionJobWorker: Error processing message: {exc}")

    async def _process_job(self, video_id: str, receipt_handle: str | None) -> None:
        """Fetch job from MongoDB, run Remotion generation, and update the record."""
        # 1. Fetch full job document from MongoDB
        job_doc = await self.videos_collection_ref.find_one(
            {"_id": _mongo_id(video_id)}
        )

        if not job_doc:
            logger.warning(f"RemotionJobWorker: No job found for video_id={video_id}. It may have been processed already.")
            if receipt_handle:
                self.sqs_service.delete_message(receipt_handle, self.queue_url)
            return

        # 2. Skip only completed jobs. Failed jobs are allowed to retry.
        current_status = job_doc.get("status", "queued")
        if current_status == "completed":
            logger.info(f"RemotionJobWorker: video_id={video_id} already in status={current_status}. Deleting from SQS.")
            if receipt_handle:
                self.sqs_service.delete_message(receipt_handle, self.queue_url)
            return
        if current_status == "processing":
            logger.info(f"RemotionJobWorker: video_id={video_id} is already processing. Deleting duplicate SQS message.")
            if receipt_handle:
                self.sqs_service.delete_message(receipt_handle, self.queue_url)
            return

        # 3. Mark as processing, clearing any prior failure state so retries can run cleanly.
        # CRITICAL FIX: Only process jobs that are explicitly Remotion jobs.
        # If an Avatar job is found in SQS, let the AvatarJobWorker handle it.
        request_mode = job_doc.get("request_mode", "")
        if "remotion" not in str(request_mode).lower():
            logger.info(f"RemotionJobWorker: skipping video_id={video_id} because request_mode={request_mode} is not Remotion.")
            return

        now = datetime.utcnow()
        await self.videos_collection_ref.update_one(
            {"_id": _mongo_id(video_id)},
            {"$set": {
                "status": "processing",
                "phase": "Preparing render",
                "progress": 20,
                "updated_at": now,
                "error_message": None,
                "job_data.status": "processing",
                "job_data.phase": "Preparing render",
                "job_data.progress": 20,
            }}
        )

        try:
            # 4. Generate Remotion video
            raw_payload = job_doc.get("job_data", {}).get("request_payload", {})
            remotion_req = RemotionVideoRequest(**raw_payload)
            
            # Pass the video_id down to consolidate all file naming
            await self._set_progress(video_id, "processing", "Rendering video", 45)
            result_payload = await self.remotion_service.generate_video(remotion_req, video_id=video_id)
            result_path = result_payload["video_path"]
            
            # 5. Upload to S3
            await self._set_progress(video_id, "processing", "Uploading video", 86)
            s3_key = f"videos/{video_id}.mp4"
            final_url = self.s3_service.upload_video(result_path, s3_key)
            interactive_url = None
            subtitles = result_payload.get("subtitles") or []
            if remotion_req.template_key in {"loan_reminder", "collection_reminder"} and final_url:
                await self._set_progress(video_id, "processing", "Creating interactive page", 93)
                interactive_url = self._upload_loan_reminder_html(
                    video_id=video_id,
                    title=str(job_doc.get("title") or "Loan Reminder"),
                    video_url=final_url,
                    payment_url=remotion_req.payment_url or "",
                    callback_phone=remotion_req.contact_details or "",
                )
            elif remotion_req.template_key == "scene_loan_offer" and final_url:
                interactive_url = self._upload_sales_cta_html(
                    video_id=video_id,
                    title=str(job_doc.get("title") or "Sales Offer"),
                    video_url=final_url,
                    customer_name=str(remotion_req.customer_name or ""),
                    sales_cta_label=str(getattr(remotion_req, "sales_cta_label", "") or ""),
                    sales_cta_url=str(getattr(remotion_req, "sales_cta_url", "") or ""),
                )
            elif remotion_req.template_key == "loan_offer_interactive" and final_url:
                rp = job_doc.get("job_data", {}).get("request_payload", {})
                def _f(name: str, fallback: str = "") -> str:
                    v = rp.get(name)
                    return fallback if v is None or str(v).strip() == "" else str(v)
                loan_offer_data = {
                    "max_loan_amount": _f("max_loan_amount", _f("loan_amount", "105000")),
                    "max_tenure": _f("max_tenure", "60"),
                    "max_emi": _f("max_emi", _f("tos", "3398")),
                    "loan_id": _f("loan_id", _f("lan", "")),
                    "cta_phone_number": _f("cta_phone_number", _f("contact_details", "1800-555-999")),
                    "month_24_loan_amount": _f("month_24_loan_amount", "75000"),
                    "month_30_loan_amount": _f("month_30_loan_amount", "90000"),
                    "month_36_loan_amount": _f("month_36_loan_amount", "105000"),
                    "month_42_loan_amount": _f("month_42_loan_amount", "NA"),
                    "month_48_loan_amount": _f("month_48_loan_amount", "NA"),
                    "month_60_loan_amount": _f("month_60_loan_amount", _f("max_loan_amount", "105000")),
                    "emi_calculation24": _f("emi_calculation24", ""),
                    "emi_calculation30": _f("emi_calculation30", ""),
                    "emi_calculation36": _f("emi_calculation36", ""),
                    "emi_calculation42": _f("emi_calculation42", ""),
                    "emi_calculation48": _f("emi_calculation48", ""),
                    "emi_calculation60": _f("emi_calculation60", _f("max_emi", "3398")),
                }
                interactive_url = self._upload_loan_offer_interactive_html(
                    video_id=video_id,
                    title=str(job_doc.get("title") or "Interactive Loan Offer"),
                    video_url=final_url,
                    customer_name=_f("customer_name", "Customer"),
                    client_name=_f("client_name", "Finance Partner"),
                    contact_details=_f("contact_details", "1800-555-999"),
                    primary_color=_f("primary_color", "#053666"),
                    interactive_cta_color=_f("interactive_cta_color", "#702082"),
                    interactive_background_color=_f("interactive_background_color", "#f5f7fb"),
                    subtitles=subtitles,
                    loan_offer=loan_offer_data,
                )

            # 6. Update MongoDB to completed
            update_fields = {
                    "status": "completed",
                    "phase": "Completed",
                    "progress": 100,
                    "video_url": final_url,
                    "subtitles": subtitles,
                    "updated_at": datetime.utcnow(),
                }
            if interactive_url:
                update_fields["interactive_url"] = interactive_url

            await self.videos_collection_ref.update_one(
                {"_id": _mongo_id(video_id)},
                {"$set": update_fields}
            )
            
            # 7. Delete from SQS
            if receipt_handle:
                self.sqs_service.delete_message(receipt_handle, self.queue_url)

        except Exception as exc:
            logger.error(f"RemotionJobWorker: Failed to process video_id={video_id}: {exc}")
            await self.videos_collection_ref.update_one(
                {"_id": _mongo_id(video_id)},
                {"$set": {
                    "status": "failed",
                    "phase": "Failed",
                    "progress": 100,
                    "error_message": str(exc),
                    "job_data.status": "failed",
                    "job_data.phase": "Failed",
                    "job_data.progress": 100,
                    "updated_at": datetime.utcnow(),
                }}
            )
            if receipt_handle:
                self.sqs_service.delete_message(receipt_handle, self.queue_url)


def main():
    worker = RemotionJobWorker()
    try:
        asyncio.run(worker.run_forever())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user.")


if __name__ == "__main__":
    main()
