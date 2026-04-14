<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { store, addFlash } from '../store'
import axios from 'axios'

import LibrarySyncCard from '../components/LibrarySyncCard.vue'
import UsbDevicesCard from '../components/UsbDevicesCard.vue'
import LibraryToolbar from '../components/LibraryToolbar.vue'
import BrowseGrid from '../components/BrowseGrid.vue'
import TrackTable from '../components/TrackTable.vue'

const route = useRoute()

async function fetchData() {
  store.isLoading = true
  try {
    const artist = (route.query.artist as string) || ''
    const album = (route.query.album as string) || ''
    
    const [tracksRes, usbRes] = await Promise.all([
      axios.get('/api/tracks', { params: { artist, album } }),
      axios.get('/api/usb')
    ])
    
    store.tracks = tracksRes.data.tracks
    store.allTrackCount = tracksRes.data.allTrackCount
    store.artistGroups = tracksRes.data.artistGroups
    store.albumGroups = tracksRes.data.albumGroups
    store.activeArtist = tracksRes.data.activeArtist
    store.activeAlbum = tracksRes.data.activeAlbum
    store.selectedCount = tracksRes.data.selectedCount
    store.selectedSizeHuman = tracksRes.data.selectedSizeHuman
    
    store.usbDevices = usbRes.data.devices
    store.usbRoles = usbRes.data.roles
  } catch (error) {
    addFlash('Failed to load library data.', 'error')
  } finally {
    store.isLoading = false
  }
}

onMounted(fetchData)

// Watch for route query changes (browsing)
watch(() => route.query, fetchData)
</script>

<template>
  <div>
    <section class="dashboard-grid">
      <LibrarySyncCard />
      <UsbDevicesCard />
    </section>

    <section id="library-section">
      <article class="library-panel">
        <div class="section-header library-header">
          <h2>Track Library</h2>
          <div class="library-meta">
            <span>Showing {{ store.tracks.length }} / {{ store.allTrackCount }}</span>
            <span><span id="library-selected-count">{{ store.selectedCount }}</span> selected</span>
          </div>
        </div>

        <LibraryToolbar />
        <BrowseGrid />
        <TrackTable />
      </article>
    </section>
  </div>
</template>
