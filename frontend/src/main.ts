import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import '@picocss/pico/css/pico.min.css'
import './assets/styles.css'
import dragScroll from './directives/dragScroll'

const app = createApp(App)
app.directive('drag-scroll', dragScroll)
app.use(router)
app.mount('#app')
