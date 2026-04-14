<script setup lang="ts">
import { store, addFlash } from '../store'
import axios from 'axios'

async function handleAction(endpoint: string, message: string) {
  store.busyMessage = message
  try {
    const response = await axios.post(`/api/actions/${endpoint}`)
    if (response.data.success) {
      addFlash(response.data.message, 'success')
    } else {
      addFlash(response.data.message, 'error')
    }
  } catch (error) {
    addFlash('Action failed.', 'error')
  } finally {
    store.busyMessage = ''
  }
}
</script>

<template>
  <article class="dashboard-card compact-card library-sync-card">
    <div class="section-header">
      <h2>Library + Sync</h2>
    </div>
    <p class="sync-summary">
      <strong id="selected-count">{{ store.selectedCount }}</strong> selected
      <span class="summary-sep">|</span>
      <strong id="selected-size">{{ store.selectedSizeHuman }}</strong>
    </p>
    <div class="action-stack compact-actions">
      <button @click="handleAction('import-library-input', 'Importing music from USB. This can take a while for large libraries...')" class="secondary">
        Import From USB
      </button>
      <button @click="handleAction('sync-mp3', 'Syncing to MP3 player...')">
        Sync to MP3
      </button>
      <button @click="handleAction('backup-library', 'Backing up your library to USB. Keep this page open until it completes...')" class="secondary">
        Back Up Library
      </button>
      <router-link to="/settings" custom v-slot="{ navigate }">
        <button @click="navigate" class="outline">Settings</button>
      </router-link>
    </div>
  </article>
</template>
