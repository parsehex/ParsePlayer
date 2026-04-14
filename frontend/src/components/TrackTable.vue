<script setup lang="ts">
import { store, addFlash } from '../store'
import axios from 'axios'
import { computed } from 'vue'

const filteredTracks = computed(() => {
  const query = store.filterQuery.trim().toLowerCase()
  if (!query) return store.tracks
  
  return store.tracks.filter((t: any) => {
    const haystack = `${t.title} ${t.virtual_artist} ${t.virtual_album} ${t.path}`.toLowerCase()
    return haystack.includes(query)
  })
})

async function toggleTrack(trackId: number) {
  try {
    const response = await axios.post(`/api/tracks/${trackId}/toggle`)
    if (response.data.success) {
      // Find track and update in place to avoid full refresh flickers
      const index = store.tracks.findIndex((t: any) => t.id === trackId)
      if (index !== -1) {
        store.tracks[index] = response.data.track
      }
      store.selectedCount = response.data.selectedCount
      store.selectedSizeHuman = response.data.selectedSizeHuman
      
      // We might need to refresh groups if counts there need to be updated
      // but for individual toggle, it's often fine to just update the counters
      // unless we want perfect folder-level counters too.
      // To keep it snappy, we'll just update the counters.
    }
  } catch (error) {
    addFlash('Failed to toggle track.', 'error')
  }
}
</script>

<template>
  <div class="table-wrap library-table-wrap">
    <table class="library-table">
      <thead>
        <tr>
          <th>Sync</th>
          <th>Track</th>
          <th>File</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="track in filteredTracks"
          :key="track.id"
          :id="'track-' + track.id"
          :class="{ 'selected': track.selected_for_sync }"
        >
          <td class="track-action-cell">
            <button
              @click="toggleTrack(track.id)"
              class="outline track-select-btn"
              :aria-label="track.selected_for_sync ? 'Selected. Click to clear selection.' : 'Not selected. Click to select.'"
              :title="track.selected_for_sync ? 'Clear selection' : 'Select track'"
            >
              <span v-if="track.selected_for_sync" aria-hidden="true">&#10003;</span>
              <span v-else aria-hidden="true">&#9711;</span>
              <span class="visually-hidden">
                {{ track.selected_for_sync ? 'Selected' : 'Select' }}
              </span>
            </button>
          </td>
          <td class="track-main-cell">
            <small v-if="!store.activeAlbum && store.activeArtist" class="track-context">{{ track.virtual_album }}</small>
            <small v-else-if="!store.activeAlbum && !store.activeArtist" class="track-context">
              {{ track.virtual_artist }} / {{ track.virtual_album }}
            </small>
            <strong class="track-title">{{ track.title }}</strong>
          </td>
          <td class="path track-path-cell">{{ track.path }}</td>
        </tr>
        <tr v-if="filteredTracks.length === 0">
          <td colspan="3">
            {{ store.filterQuery ? 'No tracks match this filter.' : 'No tracks indexed yet. Run a scan first.' }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
