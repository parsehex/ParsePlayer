<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { store, addFlash } from '../store'
import axios from 'axios'

const router = useRouter()
const musicRootInput = ref('')

async function fetchSettings() {
  try {
    const response = await axios.get('/api/settings')
    musicRootInput.value = response.data.musicRoot
    store.selectedCount = response.data.selectedCount
    store.selectedSizeHuman = response.data.selectedSizeHuman
  } catch (error) {
    addFlash('Failed to load settings.', 'error')
  }
}

async function runScan() {
  store.busyMessage = `Scanned... please keep this page open.`
  try {
    const response = await axios.post('/api/library/scan', {
       source_path: musicRootInput.value
    })
    if (response.data.success) {
      addFlash(response.data.message, 'success')
      fetchSettings()
    } else {
      addFlash(response.data.message, 'error')
    }
  } catch (error) {
    addFlash('Scan failed.', 'error')
  } finally {
    store.busyMessage = ''
  }
}

onMounted(fetchSettings)
</script>

<template>
  <section shadow>
    <article class="settings-panel">
      <div class="section-header">
        <h2>Settings</h2>
        <button @click="router.back()" class="outline">Back</button>
      </div>

      <p class="sync-summary">
        <strong>{{ store.selectedCount }}</strong> selected
        <span class="summary-sep">|</span>
        <strong>{{ store.selectedSizeHuman }}</strong>
      </p>

      <h3>Library Scan</h3>
      <div class="scan-form settings-form">
        <label for="source_path">Source Folder</label>
        <div class="inline-field-row">
          <input id="source_path" v-model="musicRootInput" placeholder="/home/user/Music" />
          <button @click="runScan">Scan</button>
        </div>
      </div>
    </article>
  </section>
</template>
