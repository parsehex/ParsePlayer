import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'ParsePlayer',
  description: 'A Raspberry Pi personal music hub — index, sync, and manage your audio library from a touch-screen LCD kiosk.',
  base: '/ParsePlayer/',
  lastUpdated: true,
  cleanUrls: true,
  head: [
    ['link', { rel: 'preconnect', href: 'https://fonts.googleapis.com' }],
    ['link', { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' }],
    ['link', { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=VT323&display=swap' }]
  ],
  themeConfig: {
    siteTitle: 'ParsePlayer',
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Guides', link: '/guides/pi-fresh-setup' },
      {
        text: 'GitHub',
        link: 'https://github.com/parsehex/ParsePlayer'
      }
    ],
    sidebar: [
      {
        text: 'Getting Started',
        items: [
          { text: 'Fresh Pi Setup', link: '/guides/pi-fresh-setup' },
          { text: 'Update Workflow', link: '/guides/update-workflow' }
        ]
      }
    ],
    socialLinks: [
      { icon: 'github', link: 'https://github.com/parsehex/ParsePlayer' }
    ],
    footer: {
      message: 'Released under the MIT License.',
      copyright: 'ParsePlayer — solo-pair-programmed'
    },
    editLink: {
      pattern: 'https://github.com/parsehex/ParsePlayer/edit/main/docs/:path',
      text: 'Edit this page on GitHub'
    }
  }
})
