<script setup lang="ts">
import { store, addFlash } from '../store'
import axios from 'axios'

async function detectUsb() {
  store.isLoading = true
  try {
    const response = await axios.post('/api/usb/detect')
    if (response.data.success) {
      store.usbDevices = response.data.devices
      addFlash(response.data.message, 'success')
    } else {
      addFlash(response.data.message, 'error')
    }
  } catch (error) {
    addFlash('USB detection failed.', 'error')
  } finally {
    store.isLoading = false
  }
}

async function updateRole(usbId: number, role: string) {
  try {
    const response = await axios.post(`/api/usb/${usbId}/role`, { role })
    if (response.data.success) {
      addFlash(response.data.message, 'success')
      // Refresh USB list
      const res = await axios.get('/api/usb')
      store.usbDevices = res.data.devices
    } else {
      addFlash(response.data.message, 'error')
    }
  } catch (error) {
    addFlash('Failed to update role.', 'error')
  }
}

async function handleMount(usbId: number, action: 'mount' | 'unmount') {
  try {
    const response = await axios.post(`/api/usb/${usbId}/${action}`)
    if (response.data.success) {
      addFlash(response.data.message, 'success')
      // Refresh USB list
      const res = await axios.get('/api/usb')
      store.usbDevices = res.data.devices
    } else {
      addFlash(response.data.message, 'error')
    }
  } catch (error) {
    addFlash(`Failed to ${action} device.`, 'error')
  }
}
</script>

<template>
  <article class="dashboard-card compact-card usb-dashboard-card">
    <div class="section-header">
      <h2>USB Devices</h2>
      <button @click="detectUsb" :disabled="store.isLoading" class="secondary outline">Detect</button>
    </div>

    <div class="table-wrap compact-table-wrap">
      <table class="compact-table">
        <colgroup>
          <col class="usb-col-device" />
          <col class="usb-col-size" />
          <col class="usb-col-role" />
          <col class="usb-col-mount" />
          <col class="usb-col-action" />
        </colgroup>
        <thead>
          <tr>
            <th>Device</th>
            <th>Size</th>
            <th>Role</th>
            <th>Mount</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="usb in store.usbDevices" :key="usb.id">
            <td class="usb-device-cell">
              <strong>{{ usb.label }}</strong>
              <small :title="usb.device_path">{{ usb.device_path }}</small>
              <small :title="usb.device_uuid">{{ usb.uuid_short }}</small>
            </td>
            <td class="mount-cell">{{ usb.size_human }}</td>
            <td>
              <select
                :value="usb.role"
                @change="updateRole(usb.id, ($event.target as HTMLSelectElement).value)"
                aria-label="Role for {{ usb.label }}"
              >
                <option v-for="role in store.usbRoles" :key="role" :value="role">{{ role }}</option>
              </select>
            </td>
            <td class="mount-cell usb-mount-cell">
              <span v-if="usb.mount_path" :title="usb.mount_path">{{ usb.mount_path }}</span>
              <span v-else-if="usb.is_connected">Not mounted</span>
              <span v-else>Disconnected</span>
            </td>
            <td>
              <button v-if="usb.mount_path" @click="handleMount(usb.id, 'unmount')" class="secondary outline">Unmount</button>
              <button v-else @click="handleMount(usb.id, 'mount')" :disabled="!usb.is_connected" class="outline">Mount</button>
            </td>
          </tr>
          <tr v-if="store.usbDevices.length === 0">
            <td colspan="5">No USB devices registered yet.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </article>
</template>
