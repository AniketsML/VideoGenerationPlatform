import React from 'react';
import {Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

const primaryColor = '#005BAA';
const secondaryColor = '#19B6A3';
const cardBg = '#FFFFFF';
const softBg = '#F4F8FB';
const ink = '#07142F';

const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

const formatAmountDue = (value) => {
  const text = String(value || '').trim();
  if (!text) return '₹38,450';
  if (/₹|rs\.?/i.test(text)) return text;
  const digits = text.replace(/[^\d.]/g, '');
  if (!digits) return text;
  return `₹${Number(digits).toLocaleString('en-IN')}`;
};

const Field = ({label, value}) => (
  <div>
    <div style={{fontSize: 25, color: '#304D7A', fontWeight: 800}}>{label}</div>
    <div style={{marginTop: 14, fontSize: 34, color: ink, fontWeight: 950, letterSpacing: 0}}>{value}</div>
  </div>
);

const Dots = ({left, top, opacity = 0.28}) => (
  <div
    style={{
      position: 'absolute',
      left,
      top,
      width: 170,
      height: 170,
      backgroundImage: `radial-gradient(circle, ${secondaryColor} 2px, transparent 2.4px)`,
      backgroundSize: '18px 18px',
      opacity,
    }}
  />
);

const DEFAULT_CTA_BUTTONS = [
  {label: 'Pay Now', value: ''},
  {label: 'Call Now', value: ''},
];

const normalizeCtaButtons = (ctaButtons) =>
  DEFAULT_CTA_BUTTONS.map((fallback, index) => {
    const button = Array.isArray(ctaButtons) ? ctaButtons[index] : null;
    return {
      label: String(button?.label || fallback.label).trim() || fallback.label,
      value: String(button?.value || '').trim(),
    };
  });

const getCtaIcon = (label, index) => {
  const lower = String(label || '').toLowerCase();
  if (lower.includes('pay') || lower.includes('payment')) return '₹';
  if (lower.includes('call') || lower.includes('phone') || lower.includes('contact')) return '☎';
  if (lower.includes('whatsapp') || lower.includes('message')) return '☎';
  return index === 0 ? '₹' : '☎';
};

const getCtaLabelSize = (label) => {
  const length = String(label || '').length;
  if (length > 16) return 30;
  if (length > 12) return 34;
  return 40;
};

export const MobileCollectionUI = ({
  customerName,
  accountNumber,
  daysOverdue,
  collectionStatus,
  amountDue,
  brandLogoPath = 'assets/TVS_Credit_logo.png',
  ctaButtons,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const status = clamp(Number(collectionStatus ?? 75), 0, 100);
  const cardEnter = spring({frame, fps, config: {damping: 20, stiffness: 92}});
  const pulse = interpolate(Math.sin(frame / 18), [-1, 1], [0.98, 1.025]);
  const progressWidth = interpolate(frame, [20, 90], [0, status], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const [primaryCta, secondaryCta] = normalizeCtaButtons(ctaButtons);

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        overflow: 'hidden',
        background: `radial-gradient(circle at 76% 6%, rgba(255,255,255,0.24), transparent 24%),
          radial-gradient(circle at 58% 48%, rgba(25,182,163,0.18), transparent 32%),
          linear-gradient(145deg, #003F99 0%, ${primaryColor} 34%, #0077BE 58%, #00457A 100%)`,
        fontFamily: 'Inter, Avenir Next, Arial, sans-serif',
      }}
    >
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            'linear-gradient(rgba(255,255,255,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.08) 1px, transparent 1px)',
          backgroundSize: '76px 76px',
          opacity: 0.24,
          transform: `translateY(${frame * -0.18}px)`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          right: -130,
          top: -50,
          width: 720,
          height: 720,
          borderRadius: 999,
          background: 'rgba(255,255,255,0.08)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          right: -220,
          bottom: 150,
          width: 700,
          height: 700,
          borderRadius: 999,
          background: 'rgba(25,182,163,0.08)',
        }}
      />
      <Dots left={985} top={260} />
      <Dots left={12} top={1380} opacity={0.22} />

      <div
        style={{
          position: 'absolute',
          right: 0,
          top: 0,
          width: 310,
          height: 126,
          borderBottomLeftRadius: 36,
          background: 'rgba(255,255,255,0.96)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 22px 60px rgba(2,28,47,0.22)',
        }}
      >
        <Img src={staticFile(brandLogoPath)} style={{width: 238, height: 'auto', objectFit: 'contain'}} />
      </div>

      <div style={{position: 'absolute', left: 62, top: 118, color: '#fff'}}>
        <div style={{fontSize: 32, fontWeight: 850}}>Repayment action needed</div>
        <div style={{marginTop: 18, width: 38, height: 3, borderRadius: 99, background: '#fff'}} />
        <div style={{marginTop: 24, width: 760, fontSize: 88, lineHeight: 1.05, fontWeight: 950, letterSpacing: 0}}>
          Review your account details
        </div>
        <div style={{marginTop: 24, fontSize: 39, lineHeight: 1.28, width: 560, fontWeight: 650}}>
          Choose a secure next step for your repayment.
        </div>
      </div>

      <div
        style={{
          position: 'absolute',
          left: 58,
          top: 520,
          width: 725,
          borderRadius: 34,
          padding: '42px 44px 38px',
          background: cardBg,
          transform: `translateY(${(1 - cardEnter) * 38}px)`,
          opacity: cardEnter,
          boxShadow: '0 28px 80px rgba(2,28,47,0.22)',
        }}
      >
        <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', columnGap: 58, rowGap: 34}}>
          <Field label="Account number" value={accountNumber || 'LAN12345'} />
          <Field label="Customer name" value={customerName || 'Ramesh Kumar'} />
          <div style={{gridColumn: '1 / 3', height: 1, background: '#D8E2EF'}} />
          <Field label="Days overdue" value={`${daysOverdue ?? 35} days`} />
          <Field label="Amount due" value={formatAmountDue(amountDue)} />
          <div style={{gridColumn: '1 / 3', height: 1, background: '#D8E2EF'}} />
        </div>

        <div style={{marginTop: 26}}>
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline'}}>
            <div style={{fontSize: 28, fontWeight: 900, color: ink}}>Collection status</div>
            <div style={{fontSize: 30, fontWeight: 950, color: '#0BAA67'}}>{status}%</div>
          </div>
          <div style={{marginTop: 22, height: 26, borderRadius: 999, background: '#DDEAF6', overflow: 'hidden'}}>
            <div
              style={{
                width: `${progressWidth}%`,
                height: '100%',
                borderRadius: 999,
                background: `linear-gradient(90deg, ${secondaryColor}, #08A878 34%, ${primaryColor})`,
              }}
            />
          </div>
        </div>
      </div>

      <div
        style={{
          position: 'absolute',
          left: 58,
          top: 1056,
          width: 435,
          height: 330,
          boxSizing: 'border-box',
          borderRadius: 28,
          padding: '48px 38px 34px',
          background: softBg,
          boxShadow: '0 24px 64px rgba(2,28,47,0.20)',
        }}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 82,
            width: 6,
            height: 188,
            borderRadius: 999,
            background: secondaryColor,
          }}
        />
        <div style={{display: 'flex', alignItems: 'center', gap: 16}}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 999,
              background: '#073FB8',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontSize: 38,
              fontWeight: 950,
            }}
          >
            !
          </div>
          <div style={{fontSize: 25, lineHeight: 1.05, color: '#073FB8', fontWeight: 900}}>
            Important notice
          </div>
        </div>
        <div style={{marginTop: 30, fontSize: 33, lineHeight: 1.2, color: ink, fontWeight: 900}}>
          Timely payment can help avoid further collection escalation.
        </div>
      </div>

      <div
        style={{
          position: 'absolute',
          left: 58,
          right: 58,
          bottom: 150,
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 34,
        }}
      >
        <div
          style={{
            height: 132,
            borderRadius: 24,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '0 34px',
            gap: 28,
            color: '#fff',
            background: `linear-gradient(135deg, #079C73 0%, ${secondaryColor} 100%)`,
            boxShadow: '0 24px 64px rgba(0,90,80,0.30)',
            transform: `scale(${pulse})`,
          }}
        >
          <div style={{fontSize: 62, lineHeight: 1, display: 'flex', alignItems: 'center'}}>
            {getCtaIcon(primaryCta.label, 0)}
          </div>
          <div>
            <div
              style={{
                fontSize: getCtaLabelSize(primaryCta.label),
                lineHeight: 1,
                fontWeight: 950,
                textAlign: 'center',
              }}
            >
              {primaryCta.label}
            </div>
          </div>
        </div>
        <div
          style={{
            height: 132,
            borderRadius: 24,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '0 34px',
            gap: 26,
            background: cardBg,
            color: '#063FB8',
            boxShadow: '0 24px 64px rgba(2,28,47,0.20)',
          }}
        >
          <div
            style={{
              width: 72,
              height: 72,
              borderRadius: 999,
              background: `linear-gradient(135deg, #073FB8, ${primaryColor})`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontSize: 42,
              fontWeight: 900,
            }}
          >
            {getCtaIcon(secondaryCta.label, 1)}
          </div>
          <div>
            <div
              style={{
                fontSize: getCtaLabelSize(secondaryCta.label),
                lineHeight: 1,
                fontWeight: 950,
                textAlign: 'center',
              }}
            >
              {secondaryCta.label}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
