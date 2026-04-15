<template>
  <svg class="logo-gem-svg" viewBox="0 0 130 100" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <defs>
      <filter id="gem-glow" x="-30%" y="-30%" width="160%" height="160%">
        <feGaussianBlur stdDeviation="2.5" result="blur"/>
        <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
    </defs>
    <polygon class="gem-stroke gem-outer"
      points="38,6 78,4 108,24 114,52 94,88 52,92 16,72 8,40"
      fill="none"
      stroke-width="3.2"
      stroke-linejoin="miter"
      filter="url(#gem-glow)"
    />
    <line class="gem-stroke gem-girdle" x1="8" y1="52" x2="114" y2="52" stroke-width="2" filter="url(#gem-glow)"/>
    <line class="gem-stroke" x1="38" y1="6" x2="61" y2="28" stroke-width="1.6" filter="url(#gem-glow)"/>
    <line class="gem-stroke" x1="78" y1="4" x2="61" y2="28" stroke-width="1.6" filter="url(#gem-glow)"/>
    <line class="gem-stroke" x1="61" y1="28" x2="108" y2="24" stroke-width="1.2" filter="url(#gem-glow)"/>
    <line class="gem-stroke" x1="61" y1="28" x2="8" y2="40" stroke-width="1.2" filter="url(#gem-glow)"/>
    <line class="gem-stroke" x1="52" y1="92" x2="61" y2="72" stroke-width="1.6" filter="url(#gem-glow)"/>
    <line class="gem-stroke" x1="94" y1="88" x2="61" y2="72" stroke-width="1.6" filter="url(#gem-glow)"/>
    <line class="gem-stroke" x1="61" y1="72" x2="114" y2="52" stroke-width="1.2" filter="url(#gem-glow)"/>
    <line class="gem-stroke" x1="61" y1="72" x2="16" y2="72" stroke-width="1.2" filter="url(#gem-glow)"/>
  </svg>
</template>
