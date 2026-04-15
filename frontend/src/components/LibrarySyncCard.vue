<script setup lang="ts">
import { store, addFlash, refreshLibrary } from '../store'
import axios from 'axios'

let pollInterval: number | null = null;

async function pollProgress() {
  try {
    const resp = await axios.get('/api/actions/status');
    const data = resp.data;
    store.jobProgress = data;
    if (data.status === 'completed' || data.status === 'error') {
      if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
      }
      store.busyMessage = '';
      if (data.status === 'completed') {
        addFlash(data.message, 'success');
        refreshLibrary();
      } else {
        addFlash(data.message, 'error');
      }
    }
  } catch (error) {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
    store.busyMessage = '';
    addFlash('Lost connection to server.', 'error');
  }
}

async function handleAction(endpoint: string, message: string) {
  store.busyMessage = message;
  store.jobProgress = { status: 'running', message: message, percentage: 0, completed: 0, total: 0 };

  try {
    const response = await axios.post(`/api/actions/${endpoint}`);
    if (response.data.success) {
      if (!pollInterval) {
        pollInterval = window.setInterval(pollProgress, 1000);
      }
    } else {
      addFlash(response.data.message, 'error');
      store.busyMessage = '';
      store.jobProgress = null;
    }
  } catch (error) {
    addFlash('Action failed.', 'error');
    store.busyMessage = '';
    store.jobProgress = null;
  }
}
</script>

<template>
  <article class="dashboard-card compact-card library-sync-card">
    <div class="section-header">
      <h2>Actions</h2>
    </div>
    <div class="action-stack compact-actions">
      <button @click="handleAction('import-library-input', 'Importing music from USB. This can take a while for large libraries...')" class="secondary">
        Import
      </button>
      <button @click="handleAction('sync-mp3', 'Syncing to MP3 player...')">
        Sync
      </button>
      <button @click="handleAction('backup-library', 'Backing up your library to USB. Keep this page open until it completes...')" class="secondary">
        Backup
      </button>
      <router-link to="/settings" custom v-slot="{ navigate }">
        <button @click="navigate" class="outline settings-icon-btn" aria-label="Settings" title="Settings">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.01a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h.01a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.01a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
          </svg>
        </button>
      </router-link>
    </div>
  </article>
</template>
