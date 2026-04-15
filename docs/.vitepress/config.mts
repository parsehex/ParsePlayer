import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'ParsePlayer Docs',
  description: 'Setup and operations docs for ParsePlayer on Raspberry Pi',
  lastUpdated: true,
  cleanUrls: true,
  themeConfig: {
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Fresh Pi Setup', link: '/guides/pi-fresh-setup' },
      { text: 'Update Workflow', link: '/guides/update-workflow' }
    ],
    sidebar: [
      {
        text: 'Guides',
        items: [
          { text: 'Fresh Pi Setup', link: '/guides/pi-fresh-setup' },
          { text: 'Update Workflow', link: '/guides/update-workflow' }
        ]
      }
    ]
  }
})
