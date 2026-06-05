import React from 'react';
import {Video, staticFile} from 'remotion';

const DEFAULT_BRAND = {
  brandName: 'TVS Credit',
  brandLogoPath: 'assets/TVS_Credit_logo.png',
  primaryColor: '#005BAA',
  secondaryColor: '#19B6A3',
};

export const AvatarPip = ({
  avatarVideoPath,
  agentName = 'Amit',
  agentRole = 'Collections Assistant',
  brandName = DEFAULT_BRAND.brandName,
  brandLogoPath = DEFAULT_BRAND.brandLogoPath,
  primaryColor = DEFAULT_BRAND.primaryColor,
  secondaryColor = DEFAULT_BRAND.secondaryColor,
  style = {},
}) => {
  const src = avatarVideoPath || 'avatar/sample-avatar.mp4';
  const logoSrc = brandLogoPath ? staticFile(brandLogoPath) : null;

  return (
    <div
      style={{
        position: 'absolute',
        borderRadius: 32,
        overflow: 'hidden',
        border: `3px solid ${secondaryColor}`,
        boxShadow: `0 34px 86px ${primaryColor}80, 0 0 0 1px rgba(255,255,255,0.5) inset`,
        background: `radial-gradient(circle at 48% 12%, rgba(255,255,255,0.92), rgba(224,245,255,0.86) 28%, transparent 46%),
          linear-gradient(180deg, #eefaff 0%, #d8f2fb 38%, ${secondaryColor} 64%, ${primaryColor} 100%)`,
        ...style,
      }}
    >
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            'radial-gradient(circle, rgba(0,91,170,0.22) 1.8px, transparent 2px)',
          backgroundPosition: '34px 34px, 0 0',
          backgroundSize: '22px 22px',
          opacity: 0.32,
          zIndex: 1,
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: -70,
          right: -70,
          top: 290,
          height: 260,
          zIndex: 2,
          background: `linear-gradient(135deg, ${secondaryColor} 0%, #11a995 48%, ${primaryColor} 100%)`,
          borderRadius: '50% 50% 0 0',
          transform: 'rotate(-4deg)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          top: 28,
          right: 24,
          zIndex: 10,
          minHeight: 54,
          minWidth: 190,
          padding: 0,
          borderRadius: 0,
          background: 'transparent',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
          filter: `drop-shadow(0 10px 18px ${primaryColor}30)`,
        }}
      >
        {logoSrc ? (
          <img
            src={logoSrc}
            onError={(event) => {
              event.currentTarget.style.display = 'none';
              const fallback = event.currentTarget.nextElementSibling;
              if (fallback) {
                fallback.style.display = 'block';
              }
            }}
            style={{
              height: 50,
              width: 'auto',
              maxWidth: 190,
              objectFit: 'contain',
            }}
          />
        ) : null}
        <span
          style={{
            color: primaryColor,
            display: logoSrc ? 'none' : 'block',
            fontSize: 18,
            fontWeight: 900,
            letterSpacing: 0,
            whiteSpace: 'nowrap',
          }}
        >
          {brandName}
        </span>
      </div>

      <Video
        src={staticFile(src)}
        volume={1}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          display: 'block',
          position: 'relative',
          zIndex: 4,
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 0,
          height: 166,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '28px 44px 0',
          background: `linear-gradient(180deg, rgba(2,28,47,0) 0%, ${primaryColor}E8 34%, #021C2F 100%)`,
          color: '#fff',
          zIndex: 8,
        }}
      >
        <div style={{fontSize: 44, lineHeight: 1, fontWeight: 900}}>
          {agentName}
        </div>
        <div style={{marginTop: 16, fontSize: 27, lineHeight: 1, color: secondaryColor, fontWeight: 750}}>
          {agentRole}
        </div>
        <div
          style={{
            marginTop: 18,
            width: 240,
            height: 2,
            background: `linear-gradient(90deg, ${secondaryColor}, transparent)`,
          }}
        />
      </div>
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 0,
          height: 5,
          zIndex: 12,
          background: `linear-gradient(90deg, ${primaryColor}, ${secondaryColor})`,
        }}
      />
    </div>
  );
};
