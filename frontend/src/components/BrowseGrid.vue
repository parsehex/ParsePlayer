<script setup lang="ts">
import { store, addFlash } from '../store'
import axios from 'axios'
import { useRouter } from 'vue-router'

const router = useRouter()

async function browse(artist: string, album: string = '') {
  router.push({ path: '/', query: { artist, album } })
}

async function bulkFolder(folderPath: string, action: 'select' | 'clear') {
  try {
    const response = await axios.post('/api/tracks/bulk', {
      scope: 'folder',
      value: folderPath,
      action: action
    })
    if (response.data.success) {
      addFlash(response.data.message, 'success')
      store.selectedCount = response.data.selectedCount
      store.selectedSizeHuman = response.data.selectedSizeHuman
      // Refresh current track view
      const res = await axios.get('/api/tracks', {
        params: { artist: store.activeArtist, album: store.activeAlbum }
      })
      store.tracks = res.data.tracks
      store.artistGroups = res.data.artistGroups
      store.albumGroups = res.data.albumGroups
    }
  } catch (error) {
    addFlash('Bulk folder update failed.', 'error')
  }
}
</script>

<template>
  <div id="browse-grid" class="browse-grid">
    <section class="browse-card">
      <h3>Artists (Folder Level)</h3>
      <div class="browse-list">
        <article v-for="group in store.artistGroups" :key="group.key" :class="['browse-item', { 'browse-item-active': group.is_active }]">
          <div class="browse-label">
            <strong>{{ group.label }}</strong>
            <small>{{ group.selected }}/{{ group.total }} selected</small>
          </div>
          <div class="browse-actions">
            <button @click="browse(group.key)" class="outline">Browse</button>
            <button @click="bulkFolder(group.folder_path, 'select')" class="outline">Select</button>
            <button @click="bulkFolder(group.folder_path, 'clear')" class="secondary outline">Clear</button>
          </div>
        </article>
        <p v-if="store.artistGroups.length === 0" class="browse-empty">No artist folders indexed yet.</p>
      </div>
    </section>

    <section class="browse-card">
      <h3>Albums (Within Artist)</h3>
      <div class="browse-list">
        <article v-for="group in store.albumGroups" :key="group.key" :class="['browse-item', { 'browse-item-active': group.is_active }]">
          <div class="browse-label">
            <strong>{{ group.label }}</strong>
            <small>{{ group.selected }}/{{ group.total }} selected</small>
          </div>
          <div class="browse-actions">
            <button @click="browse(store.activeArtist, group.key)" class="outline">Browse</button>
            <button @click="bulkFolder(group.folder_path, 'select')" class="outline">Select</button>
            <button @click="bulkFolder(group.folder_path, 'clear')" class="secondary outline">Clear</button>
          </div>
        </article>
        <p v-if="store.albumGroups.length === 0" class="browse-empty">
          {{ store.activeArtist ? 'No albums found.' : 'Select an artist folder to browse albums.' }}
        </p>
      </div>
    </section>
  </div>
</template>
