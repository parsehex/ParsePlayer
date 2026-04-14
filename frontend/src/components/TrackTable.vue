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
      const index = store.tracks.findIndex((t: any) => t.id === trackId)
      if (index !== -1) {
        store.tracks[index] = response.data.track
      }
      store.selectedCount = response.data.selectedCount
      store.selectedSizeHuman = response.data.selectedSizeHuman
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
          <th>Track</th>
          <th class="track-size-col">Size</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="track in filteredTracks"
          :key="track.id"
          :id="'track-' + track.id"
          :class="{ 'selected': track.selected_for_sync }"
          @click="toggleTrack(track.id)"
          role="button"
          tabindex="0"
          @keydown.enter="toggleTrack(track.id)"
          :aria-label="(track.selected_for_sync ? 'Selected: ' : 'Not selected: ') + track.title"
        >
          <td class="track-main-cell">
            <span class="track-check" aria-hidden="true">{{ track.selected_for_sync ? '✓' : '○' }}</span>
            <span class="track-text">
              <small v-if="!store.activeAlbum && store.activeArtist" class="track-context">{{ track.virtual_album }}</small>
              <small v-else-if="!store.activeAlbum && !store.activeArtist" class="track-context">
                {{ track.virtual_artist }} / {{ track.virtual_album }}
              </small>
              <strong class="track-title">{{ track.title }}</strong>
            </span>
          </td>
          <td class="track-size-cell">{{ track.size_human }}</td>
        </tr>
        <tr v-if="filteredTracks.length === 0">
          <td colspan="2">
            {{ store.filterQuery ? 'No tracks match this filter.' : 'No tracks indexed yet. Run a scan first.' }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
