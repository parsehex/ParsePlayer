<script setup lang="ts">
import { store } from './store'
import axios from 'axios'

async function stopJob() {
  try {
    await axios.post('/api/actions/stop')
  } catch (error) {
    console.error('Failed to stop job:', error)
  }
}
</script>

<template>
  <main class="container">
    <header class="page-header">
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
        <line class="gem-stroke gem-girdle" x1="8"  y1="52" x2="114" y2="52" stroke-width="2"   filter="url(#gem-glow)"/>
        <line class="gem-stroke" x1="38"  y1="6"  x2="61"  y2="28"  stroke-width="1.6" filter="url(#gem-glow)"/>
        <line class="gem-stroke" x1="78"  y1="4"  x2="61"  y2="28"  stroke-width="1.6" filter="url(#gem-glow)"/>
        <line class="gem-stroke" x1="61"  y1="28" x2="108" y2="24"  stroke-width="1.2" filter="url(#gem-glow)"/>
        <line class="gem-stroke" x1="61"  y1="28" x2="8"   y2="40"  stroke-width="1.2" filter="url(#gem-glow)"/>
        <line class="gem-stroke" x1="52"  y1="92" x2="61"  y2="72"  stroke-width="1.6" filter="url(#gem-glow)"/>
        <line class="gem-stroke" x1="94"  y1="88" x2="61"  y2="72"  stroke-width="1.6" filter="url(#gem-glow)"/>
        <line class="gem-stroke" x1="61"  y1="72" x2="114" y2="52"  stroke-width="1.2" filter="url(#gem-glow)"/>
        <line class="gem-stroke" x1="61"  y1="72" x2="16"  y2="72"  stroke-width="1.2" filter="url(#gem-glow)"/>
      </svg>
      <div class="lcd-title-bar">
        <span class="lcd-brand"><span class="brand-cap">P</span>arse<span class="brand-cap">P</span>layer</span>
        <span class="lcd-status">▶ ♫ ▮▮▮</span>
      </div>
    </header>

    <section v-if="store.flashMessages.length > 0">
      <article v-for="msg in store.flashMessages" :key="msg.id" :class="['flash', msg.type]">
        {{ msg.message }}
      </article>
    </section>

    <router-view />

    <div v-if="store.busyMessage || (store.jobProgress && store.jobProgress.status === 'running')" id="busy-overlay" class="busy-overlay">
      <div class="busy-panel" role="status" aria-live="polite" aria-atomic="true">
        <span v-if="!store.jobProgress || store.jobProgress.status !== 'running'" class="busy-spinner" aria-hidden="true"></span>
        <p id="busy-text">{{ store.jobProgress && store.jobProgress.status === 'running' ? store.jobProgress.message : store.busyMessage }}</p>
        <div v-if="store.jobProgress && store.jobProgress.status === 'running'" class="progress-container" style="margin-top: 1rem; width: 100%;">
          <progress :value="store.jobProgress.percentage" max="100" style="width: 100%;"></progress>
          <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem; margin-top: 0.4rem;">
            <span v-if="store.jobProgress.total > 0">{{ store.jobProgress.completed }} / {{ store.jobProgress.total }}</span>
            <button 
              @click="stopJob" 
              class="error outline stop-btn" 
              style="margin: 0; padding: 0.1rem 0.6rem; font-size: 0.75rem;"
              :disabled="store.jobProgress.status === 'stopping'"
            >
              {{ store.jobProgress.status === 'stopping' ? 'Stopping...' : 'Stop' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </main>
</template>
