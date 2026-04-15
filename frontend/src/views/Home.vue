<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { store, addFlash } from '../store'
import axios from 'axios'

import LibrarySyncCard from '../components/LibrarySyncCard.vue'
import UsbDevicesCard from '../components/UsbDevicesCard.vue'
import LibraryToolbar from '../components/LibraryToolbar.vue'
import BrowseGrid from '../components/BrowseGrid.vue'
import TrackTable from '../components/TrackTable.vue'

const route = useRoute()
const isKioskViewport = ref(false)
const isUsbPanelOpen = ref(true)

let kioskMediaQuery: MediaQueryList | null = null

function syncKioskViewport(event?: MediaQueryList | MediaQueryListEvent) {
  const matches = event ? event.matches : kioskMediaQuery?.matches ?? false
  isKioskViewport.value = matches

  if (!matches) {
    isUsbPanelOpen.value = true
    return
  }

  if (isUsbPanelOpen.value) {
    isUsbPanelOpen.value = false
  }
}

function toggleUsbPanel() {
  isUsbPanelOpen.value = !isUsbPanelOpen.value
}

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

onMounted(() => {
  kioskMediaQuery = window.matchMedia('(max-width: 480px) and (max-height: 520px)')
  syncKioskViewport()
  kioskMediaQuery.addEventListener('change', syncKioskViewport)
})

onBeforeUnmount(() => {
  kioskMediaQuery?.removeEventListener('change', syncKioskViewport)
})

// Watch for route query changes (browsing)
watch(() => route.query, fetchData)

// Watch for manual refresh triggers (e.g. job completion)
watch(() => store.refreshTrigger, fetchData)
</script>

<template>
  <div class="home-view" :class="{ 'usb-panel-open': isUsbPanelOpen }">
    <section class="dashboard-grid dashboard-rail">
      <LibrarySyncCard />
      <button
        v-if="isKioskViewport"
        class="secondary outline usb-rail-toggle"
        type="button"
        @click="toggleUsbPanel"
        :aria-expanded="isUsbPanelOpen"
        aria-controls="usb-panel"
      >
        {{ isUsbPanelOpen ? 'Tracks' : 'USB' }}
      </button>
      <div v-if="!isKioskViewport" id="usb-panel" class="usb-rail-panel">
        <UsbDevicesCard />
      </div>
    </section>

    <section id="library-section" class="library-section">
      <article class="library-panel">
        <div v-if="isKioskViewport && isUsbPanelOpen" class="section-header library-header">
          <h2>USB Devices</h2>
          <div class="library-meta">
            <span>{{ store.usbDevices.length }} devices</span>
          </div>
        </div>

        <div v-else class="section-header library-header">
          <h2>Track Library</h2>
          <div class="library-meta">
            <span>Showing {{ store.tracks.length }} / {{ store.allTrackCount }}</span>
            <span><span id="library-selected-count">{{ store.selectedCount }}</span> selected</span>
            <span>{{ store.selectedSizeHuman }}</span>
          </div>
        </div>

        <div v-drag-scroll class="library-scroll-region">
          <UsbDevicesCard v-if="isKioskViewport && isUsbPanelOpen" />
          <template v-else>
            <LibraryToolbar />
            <BrowseGrid />
            <TrackTable />
          </template>
        </div>
      </article>
    </section>
  </div>
</template>
