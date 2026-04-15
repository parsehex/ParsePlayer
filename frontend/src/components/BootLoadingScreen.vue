<script setup lang="ts">
import { ref, onMounted } from 'vue'

const showLoader = ref(true)

onMounted(() => {
  // Hide loader after a short delay to ensure DOM is painted
  const timer = setTimeout(() => {
    showLoader.value = false
  }, 500)

  return () => clearTimeout(timer)
})
</script>

<template>
  <div v-if="showLoader" class="boot-loading-screen">
    <div class="boot-loading-content">
      <div class="boot-spinner"></div>
      <p>ParsePlayer</p>
    </div>
  </div>
</template>

<style scoped>
.boot-loading-screen {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: #9edd00;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.boot-loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2rem;
}

.boot-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #103100;
  border-top: 4px solid transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.boot-loading-content p {
  font-family: "VT323", "Courier New", monospace;
  font-size: 28px;
  color: #103100;
  margin: 0;
  letter-spacing: 10px;
}
</style>
