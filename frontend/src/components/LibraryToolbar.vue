<script setup lang="ts">
import { store, addFlash } from '../store'
import axios from 'axios'
import { useRouter } from 'vue-router'

const router = useRouter()

async function bulkUpdate(action: 'select' | 'clear') {
  try {
    const response = await axios.post('/api/tracks/bulk', {
      scope: 'all',
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
    addFlash('Bulk update failed.', 'error')
  }
}

function resetBrowse() {
  router.push('/')
}
</script>

<template>
  <div class="library-toolbar">
    <label class="library-filter-field" for="library-filter">Search</label>
    <input
      id="library-filter"
      type="search"
      v-model="store.filterQuery"
      placeholder="Filter by title, artist, or path"
      autocomplete="off"
    />
    <button @click="resetBrowse" class="outline">All Tracks</button>
    <div class="library-bulk-all">
      <button @click="bulkUpdate('select')" class="outline">Select All</button>
      <button @click="bulkUpdate('clear')" class="secondary outline">Clear All</button>
    </div>
  </div>
</template>
