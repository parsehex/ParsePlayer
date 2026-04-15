import { reactive } from 'vue'

interface SyncGroup {
  key: string;
  label: string;
  folder_path: string;
  total: number;
  selected: number;
  is_active: boolean;
  size_bytes?: number;
  size_human?: string;
  selected_size_bytes?: number;
  selected_size_human?: string;
}

interface Track {
  id: number;
  path: string;
  title: string;
  artist: string | null;
  selected_for_sync: boolean;
  virtual_artist?: string;
  virtual_album?: string;
  size_bytes?: number;
  size_human?: string;
}

interface FlashMessage {
  id: number;
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
}

interface JobProgress {
  status: string;
  message: string;
  percentage: number;
  completed: number;
  total: number;
}

interface StoreState {
  tracks: Track[];
  allTrackCount: number;
  artistGroups: SyncGroup[];
  albumGroups: SyncGroup[];
  selectedCount: number;
  selectedSizeHuman: string;
  activeArtist: string;
  activeAlbum: string;
  usbDevices: any[];
  usbRoles: string[];
  flashMessages: FlashMessage[];
  busyMessage: string;
  isLoading: boolean;
  filterQuery: string;
  jobProgress: JobProgress | null;
  refreshTrigger: number;
}

export const store = reactive<StoreState>({
  tracks: [],
  allTrackCount: 0,
  artistGroups: [],
  albumGroups: [],
  selectedCount: 0,
  selectedSizeHuman: '0 B',
  activeArtist: '',
  activeAlbum: '',
  usbDevices: [],
  usbRoles: [],
  flashMessages: [],
  busyMessage: '',
  isLoading: false,
  filterQuery: '',
  jobProgress: null,
  refreshTrigger: 0,
})

export function refreshLibrary() {
  store.refreshTrigger++
}

export function addFlash(message: string, type: FlashMessage['type'] = 'success') {
  const id = Date.now()
  store.flashMessages.push({ id, message, type })
  setTimeout(() => {
    store.flashMessages = store.flashMessages.filter(m => m.id !== id)
  }, 5000)
}
