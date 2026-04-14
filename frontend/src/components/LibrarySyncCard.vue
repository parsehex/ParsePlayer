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
