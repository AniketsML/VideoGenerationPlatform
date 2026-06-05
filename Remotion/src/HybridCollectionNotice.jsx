import React from 'react';
import {AbsoluteFill} from 'remotion';
import {AvatarPip} from './components/AvatarPip';
import {LandscapeCollectionUI} from './components/LandscapeCollectionUI';
import {MobileCollectionUI} from './components/MobileCollectionUI';

export const hybridCollectionNoticeDefaults = {
  customerName: 'Rajesh Kumar Singh',
  accountNumber: 'DC-2024-089456',
  daysOverdue: 35,
  collectionStatus: 75,
  amountDue: '₹45,200',
  agentName: 'Amit',
  agentRole: 'Collections Agent',
  avatarVideoPath: 'avatar/sample-avatar.mp4',
  durationInFrames: 900,
  aspectMode: 'portrait_9_16',
  resolvedAspectMode: 'portrait_9_16',
  brandName: 'TVS Credit',
  brandLogoPath: 'assets/TVS_Credit_logo.png',
  primaryColor: '#005BAA',
  secondaryColor: '#19B6A3',
  ctaButtons: [
    {label: 'Pay Now', value: ''},
    {label: 'Call Now', value: ''},
  ],
};

const portraitPipStyle = {
  width: 470,
  height: 640,
  right: 50,
  bottom: 330,
};

const landscapePipStyle = {
  width: 480,
  height: 680,
  right: 100,
  bottom: 120,
};

export const HybridCollectionNotice = ({layout = 'portrait', ...props}) => {
  const mergedProps = {...hybridCollectionNoticeDefaults, ...props};
  const isLandscape = layout === 'landscape';
  const brandName = mergedProps.brandName || 'TVS Credit';
  const brandLogoPath = mergedProps.brandLogoPath || 'assets/TVS_Credit_logo.png';
  const primaryColor = mergedProps.primaryColor || '#005BAA';
  const secondaryColor = mergedProps.secondaryColor || '#19B6A3';

  return (
    <AbsoluteFill style={{backgroundColor: isLandscape ? '#fff' : primaryColor}}>
      {isLandscape ? (
        <LandscapeCollectionUI {...mergedProps} primaryColor={primaryColor} secondaryColor={secondaryColor} />
      ) : (
        <MobileCollectionUI
          {...mergedProps}
          ctaButtons={mergedProps.ctaButtons}
          primaryColor={primaryColor}
          secondaryColor={secondaryColor}
        />
      )}
      <AvatarPip
        avatarVideoPath={mergedProps.avatarVideoPath}
        agentName={mergedProps.agentName}
        agentRole={mergedProps.agentRole}
        brandName={brandName}
        brandLogoPath={brandLogoPath}
        primaryColor={primaryColor}
        secondaryColor={secondaryColor}
        style={isLandscape ? landscapePipStyle : portraitPipStyle}
      />
    </AbsoluteFill>
  );
};
