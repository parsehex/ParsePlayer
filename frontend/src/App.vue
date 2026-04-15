<script setup lang="ts">
import { store } from './store'
import axios from 'axios'
import PearlLogo from './components/PearlLogo.vue'
import BootLoadingScreen from './components/BootLoadingScreen.vue'

async function stopJob() {
  try {
    await axios.post('/api/actions/stop')
  } catch (error) {
    console.error('Failed to stop job:', error)
  }
}
</script>

<template>
  <BootLoadingScreen />
  <main class="container">
    <header class="page-header">
      <PearlLogo />
      <div class="lcd-title-bar">
        <span class="lcd-brand"><span class="brand-cap">P</span>arse<span class="brand-cap">P</span>layer</span>
      </div>
    </header>

    <section v-if="store.flashMessages.length > 0">
      <article v-for="msg in store.flashMessages" :key="msg.id" :class="['flash', msg.type]">
        {{ msg.message }}
      </article>
    </section>

    <div class="app-view">
      <router-view />
    </div>

    <div v-if="store.busyMessage || (store.jobProgress && (store.jobProgress.status === 'running' || store.jobProgress.status === 'stopping'))" id="busy-overlay" class="busy-overlay">
      <div class="busy-panel" role="status" aria-live="polite" aria-atomic="true">
        <span v-if="!store.jobProgress || (store.jobProgress.status !== 'running' && store.jobProgress.status !== 'stopping')" class="busy-spinner" aria-hidden="true"></span>
        <p id="busy-text">{{ store.jobProgress && (store.jobProgress.status === 'running' || store.jobProgress.status === 'stopping') ? store.jobProgress.message : store.busyMessage }}</p>
        <div v-if="store.jobProgress && (store.jobProgress.status === 'running' || store.jobProgress.status === 'stopping')" class="progress-container" style="margin-top: 1rem; width: 100%;">
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
