<template>
  <div class="personaiq-dashboard">
    <!-- Header -->
    <header class="dashboard-header">
      <div class="header-left">
        <h1 class="logo">
            <i class="fas fa-brain"></i> 
            PersonaIQ
            </h1>
        <div class="test-badge" v-if="currentRun">
          <i class="fas fa-play-circle"></i>
          Test Run: {{ currentRun.id.slice(0, 8) }}
        </div>
      </div>
      
      <div class="header-stats">
        <div class="stat">
          <i class="fas fa-users"></i>
          <span>{{ completedPersonas }}/{{ totalPersonas }}</span>
          <small>Personas</small>
        </div>
        <div class="stat">
          <i class="fas fa-clock"></i>
          <span>{{ elapsedTime }}</span>
          <small>Elapsed</small>
        </div>
        <button class="btn-export" @click="exportResults" :disabled="!allComplete">
          <i class="fas fa-download"></i>
          Export Report
        </button>
      </div>
    </header>

    <!-- Main Split View -->
    <div class="dashboard-main">
      <!-- Left: Persona Cards -->
      <div class="persona-sidebar">
        <div class="sidebar-header">
          <i class="fas fa-user-astronaut"></i>
          <h3>Active Personas</h3>
          <span class="count-badge">{{ totalPersonas }}</span>
        </div>
        
        <div class="persona-list">
          <PersonaCard
            v-for="persona in personas"
            :key="persona.id"
            :persona="persona"
            :is-selected="selectedPersonaId === persona.id"
            @select="selectPersona"
          />
        </div>
      </div>

      <!-- Center: Live Activity Feed -->
      <div class="activity-feed">
        <div class="feed-header">
          <i class="fas fa-rss"></i>
          <h3>Live Activity Stream</h3>
          <button class="clear-feed" @click="clearFeed" v-if="activities.length">
            <i class="fas fa-trash-alt"></i>
          </button>
        </div>
        
        <div class="feed-container" ref="feedContainer">
          <div 
            v-for="activity in activities" 
            :key="activity.id"
            class="activity-item"
            :class="`activity-${activity.type}`"
          >
            <div class="activity-icon">
              <i :class="getActivityIcon(activity.type)"></i>
            </div>
            <div class="activity-content">
              <div class="activity-header">
                <span class="persona-name">{{ activity.personaName }}</span>
                <span class="activity-time">{{ formatTime(activity.timestamp) }}</span>
              </div>
              <div class="activity-message">{{ activity.message }}</div>
              <div v-if="activity.detail" class="activity-detail">
                {{ activity.detail }}
              </div>
            </div>
          </div>
          
          <div v-if="!activities.length" class="empty-feed">
            <i class="fas fa-hourglass-half"></i>
            <p>Waiting for test to start...</p>
          </div>
        </div>
      </div>

      <!-- Right: Video/Replay Viewer -->
      <div class="replay-viewer">
        <div class="viewer-header">
          <i class="fas fa-video"></i>
          <h3>
            {{ selectedPersona ? selectedPersona.name : 'Select a persona' }}
          </h3>
          <div class="viewer-controls" v-if="selectedPersona">
            <button @click="togglePlayback" class="control-btn">
              <i :class="isPlaying ? 'fa-pause' : 'fa-play'"></i>
            </button>
            <button @click="downloadVideo" class="control-btn">
              <i class="fas fa-download"></i>
            </button>
          </div>
        </div>
        
        <div class="viewer-content">
          <div v-if="!selectedPersona" class="no-selection">
            <i class="fas fa-user-circle"></i>
            <p>Click on any persona card to watch their session replay</p>
          </div>
          
          <div v-else-if="selectedPersona.videoUrl && isVideoReady" class="video-container">
            <video 
              ref="videoPlayer"
              :src="selectedPersona.videoUrl"
              controls
              @play="isPlaying = true"
              @pause="isPlaying = false"
              @loadedmetadata="onVideoLoaded"
              class="replay-video"
            >
              Your browser does not support the video tag.
            </video>
            
            <div class="video-progress" v-if="videoDuration">
              <input 
                type="range" 
                v-model="videoCurrentTime" 
                :max="videoDuration"
                @input="seekVideo"
                class="progress-slider"
              />
              <div class="progress-labels">
                <span>{{ formatDuration(videoCurrentTime) }}</span>
                <span>{{ formatDuration(videoDuration) }}</span>
              </div>
            </div>
          </div>
          
          <div v-else-if="selectedPersona && !isVideoReady" class="loading-video">
            <i class="fas fa-spinner fa-pulse"></i>
            <p>Processing video recording...</p>
          </div>
          
          <div v-if="selectedPersona?.painPoints?.length" class="pain-points">
            <div class="pain-header">
              <i class="fas fa-exclamation-triangle"></i>
              <span>Pain Points Found</span>
              <span class="pain-count">{{ selectedPersona.painPoints.length }}</span>
            </div>
            <div class="pain-list">
              <div 
                v-for="(point, idx) in selectedPersona.painPoints" 
                :key="idx"
                class="pain-item"
              >
                <i class="fas fa-bug"></i>
                <span>{{ point }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import PersonaCard from './PersonaCard.vue'

export default {
  name: 'PersonaIQDashboard',
  components: { PersonaCard },
  
  props: {
    runId: {
      type: String,
      required: true
    },
    apiBaseUrl: {
      type: String,
      default: '/api'
    }
  },
  
  setup(props) {
    // State
    const personas = ref([])
    const activities = ref([])
    const selectedPersonaId = ref(null)
    const isPlaying = ref(false)
    const videoPlayer = ref(null)
    const videoDuration = ref(0)
    const videoCurrentTime = ref(0)
    const isVideoReady = ref(false)
    const feedContainer = ref(null)
    const startTime = ref(Date.now())
    const pollingInterval = ref(null)
    
    // Computed
    const totalPersonas = computed(() => personas.value.length)
    const completedPersonas = computed(() => 
      personas.value.filter(p => p.status === 'completed').length
    )
    const allComplete = computed(() => 
      personas.value.length > 0 && completedPersonas.value === totalPersonas.value
    )
    const selectedPersona = computed(() => 
      personas.value.find(p => p.id === selectedPersonaId.value)
    )
    const elapsedTime = computed(() => {
      const seconds = Math.floor((Date.now() - startTime.value) / 1000)
      const mins = Math.floor(seconds / 60)
      const secs = seconds % 60
      return `${mins}:${secs.toString().padStart(2, '0')}`
    })
    
    // Methods
    const fetchStatus = async () => {
      try {
        const response = await fetch(`${props.apiBaseUrl}/runs/${props.runId}/status`)
        const data = await response.json()
        
        // Update personas
        data.personas.forEach(newPersona => {
          const existing = personas.value.find(p => p.id === newPersona.id)
          if (!existing) {
            // New persona - add to list
            personas.value.push(newPersona)
            addActivity('start', newPersona.name, `${newPersona.name} started testing`)
          } else if (existing.status !== newPersona.status) {
            // Status changed - add activity
            const statusMessages = {
              'running': 'is now testing',
              'completed': 'completed testing successfully',
              'failed': 'encountered an issue',
              'blocked': 'hit a navigation block'
            }
            addActivity(newPersona.status, newPersona.name, statusMessages[newPersona.status] || `status changed to ${newPersona.status}`)
            
            // Update persona data
            Object.assign(existing, newPersona)
            
            // If completed and has video, mark ready
            if (newPersona.status === 'completed' && newPersona.videoUrl) {
              isVideoReady.value = true
            }
          } else {
            // Update progress without activity
            Object.assign(existing, newPersona)
          }
        })
      } catch (error) {
        console.error('Failed to fetch status:', error)
      }
    }
    
    const addActivity = (type, personaName, message, detail = null) => {
      activities.value.unshift({
        id: Date.now() + Math.random(),
        type,
        personaName,
        message,
        detail,
        timestamp: Date.now()
      })
      
      // Keep only last 100 activities
      if (activities.value.length > 100) {
        activities.value = activities.value.slice(0, 100)
      }
      
      // Auto-scroll to top of feed
      if (feedContainer.value) {
        feedContainer.value.scrollTop = 0
      }
    }
    
    const getActivityIcon = (type) => {
      const icons = {
        'start': 'fa-play-circle',
        'running': 'fa-spinner fa-pulse',
        'completed': 'fa-check-circle',
        'failed': 'fa-exclamation-circle',
        'blocked': 'fa-ban',
        'pain_point': 'fa-bug'
      }
      return icons[type] || 'fa-info-circle'
    }
    
    const formatTime = (timestamp) => {
      const seconds = Math.floor((Date.now() - timestamp) / 1000)
      if (seconds < 60) return `${seconds}s ago`
      if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
      return `${Math.floor(seconds / 3600)}h ago`
    }
    
    const formatDuration = (seconds) => {
      const mins = Math.floor(seconds / 60)
      const secs = Math.floor(seconds % 60)
      return `${mins}:${secs.toString().padStart(2, '0')}`
    }
    
    const selectPersona = (personaId) => {
      selectedPersonaId.value = personaId
      isVideoReady.value = false
      videoDuration.value = 0
      videoCurrentTime.value = 0
      
      // Reset video player when switching personas
      if (videoPlayer.value) {
        videoPlayer.value.load()
      }
    }
    
    const togglePlayback = () => {
      if (!videoPlayer.value) return
      if (isPlaying.value) {
        videoPlayer.value.pause()
      } else {
        videoPlayer.value.play()
      }
    }
    
    const onVideoLoaded = () => {
      videoDuration.value = videoPlayer.value.duration
      isVideoReady.value = true
    }
    
    const seekVideo = () => {
      if (videoPlayer.value) {
        videoPlayer.value.currentTime = videoCurrentTime.value
      }
    }
    
    const downloadVideo = () => {
      if (selectedPersona.value?.videoUrl) {
        const a = document.createElement('a')
        a.href = selectedPersona.value.videoUrl
        a.download = `persona_${selectedPersona.value.id}_replay.webm`
        a.click()
      }
    }
    
    const exportResults = async () => {
      const response = await fetch(`${props.apiBaseUrl}/runs/${props.runId}/export`)
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `personaiq_report_${props.runId}.json`
      a.click()
      URL.revokeObjectURL(url)
    }
    
    const clearFeed = () => {
      activities.value = []
    }
    
    // Lifecycle
    onMounted(() => {
      fetchStatus()
      pollingInterval.value = setInterval(fetchStatus, 2000)
      
      // Watch for video URL changes
      watch(() => selectedPersona.value?.videoUrl, (newUrl) => {
        if (newUrl && videoPlayer.value) {
          isVideoReady.value = false
          videoPlayer.value.load()
        }
      })
    })
    
    onUnmounted(() => {
      if (pollingInterval.value) {
        clearInterval(pollingInterval.value)
      }
    })
    
    return {
      personas,
      activities,
      selectedPersonaId,
      selectedPersona,
      isPlaying,
      videoPlayer,
      videoDuration,
      videoCurrentTime,
      isVideoReady,
      feedContainer,
      totalPersonas,
      completedPersonas,
      allComplete,
      elapsedTime,
      fetchStatus,
      getActivityIcon,
      formatTime,
      formatDuration,
      selectPersona,
      togglePlayback,
      onVideoLoaded,
      seekVideo,
      downloadVideo,
      exportResults,
      clearFeed
    }
  }
}
</script>

<style scoped>
.personaiq-dashboard {
  min-height: 100vh;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-body);
}

/* Header */
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem;
  border-bottom: 1px solid var(--border);
  background: var(--bg-surface);
}

.logo {
  font-family: var(--font-logo);
  font-size: 1.6rem;
  font-weight: 700;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  letter-spacing: -0.01em;
}

.logo {
  background: linear-gradient(90deg, var(--text) 0%, var(--text) calc(100% - 2ch), var(--pink) calc(100% - 2ch), var(--pink) 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.logo {
  transition: letter-spacing 0.2s ease;
}

.logo:hover {
  letter-spacing: 0.02em;
}

.logo i {
  background: none;
  -webkit-text-fill-color: var(--pink);
  color: var(--pink);
}

.highlight {
  color: var(--pink);
}

.test-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.75rem;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.header-stats {
  display: flex;
  align-items: center;
  gap: 2rem;
}

.stat {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
}

.stat i {
  color: var(--pink);
  font-size: 1.125rem;
}

.stat span {
  font-size: 1.5rem;
  font-weight: 600;
}

.stat small {
  color: var(--text-tertiary);
  font-size: 0.75rem;
}

.btn-export {
  background: var(--pink);
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: opacity 0.2s;
}

.btn-export:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-export:not(:disabled):hover {
  opacity: 0.9;
}

/* Main Layout */
.dashboard-main {
  display: grid;
  grid-template-columns: 300px 1fr 400px;
  height: calc(100vh - 80px);
  overflow: hidden;
}

/* Persona Sidebar */
.persona-sidebar {
  border-right: 1px solid var(--border);
  background: var(--bg-surface);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  border-bottom: 1px solid var(--border);
}

.sidebar-header h3 {
  font-size: 0.875rem;
  font-weight: 500;
  margin: 0;
  flex: 1;
}

.count-badge {
  background: var(--bg-elevated);
  padding: 0.25rem 0.5rem;
  border-radius: 6px;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.persona-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
}

/* Activity Feed */
.activity-feed {
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border);
  background: var(--bg);
  overflow: hidden;
}

.feed-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  border-bottom: 1px solid var(--border);
}

.feed-header h3 {
  font-size: 0.875rem;
  font-weight: 500;
  margin: 0;
  flex: 1;
}

.clear-feed {
  background: none;
  border: none;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 4px;
  transition: all 0.2s;
}

.clear-feed:hover {
  color: var(--pink);
  background: var(--pink-dim);
}

.feed-container {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.activity-item {
  display: flex;
  gap: 0.75rem;
  padding: 0.75rem;
  margin-bottom: 0.5rem;
  background: var(--bg-elevated);
  border-left: 3px solid transparent;
  border-radius: 8px;
  transition: all 0.2s;
}

.activity-item:hover {
  background: #1e1e1e;
}

.activity-start {
  border-left-color: var(--green);
}
.activity-completed {
  border-left-color: var(--green);
}
.activity-failed {
  border-left-color: var(--pink);
}
.activity-blocked {
  border-left-color: var(--amber);
}

.activity-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-surface);
  border-radius: 6px;
  color: var(--pink);
}

.activity-content {
  flex: 1;
}

.activity-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.25rem;
}

.persona-name {
  font-weight: 500;
  font-size: 0.875rem;
}

.activity-time {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.activity-message {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-bottom: 0.25rem;
}

.activity-detail {
  font-size: 0.75rem;
  color: var(--text-tertiary);
  font-family: monospace;
}

.empty-feed {
  text-align: center;
  padding: 3rem;
  color: var(--text-tertiary);
}

.empty-feed i {
  font-size: 2rem;
  margin-bottom: 1rem;
}

/* Replay Viewer */
.replay-viewer {
  display: flex;
  flex-direction: column;
  background: var(--bg-surface);
  overflow: hidden;
}

.viewer-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  border-bottom: 1px solid var(--border);
}

.viewer-header h3 {
  font-size: 0.875rem;
  font-weight: 500;
  margin: 0;
  flex: 1;
}

.viewer-controls {
  display: flex;
  gap: 0.5rem;
}

.control-btn {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 0.25rem 0.5rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.control-btn:hover {
  border-color: var(--pink);
  color: var(--pink);
}

.viewer-content {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.no-selection, .loading-video {
  text-align: center;
  padding: 3rem;
  color: var(--text-tertiary);
}

.no-selection i, .loading-video i {
  font-size: 3rem;
  margin-bottom: 1rem;
  color: var(--pink-dim);
}

.video-container {
  margin-bottom: 1rem;
}

.replay-video {
  width: 100%;
  border-radius: 8px;
  border: 1px solid var(--border);
}

.video-progress {
  margin-top: 0.5rem;
}

.progress-slider {
  width: 100%;
  height: 4px;
  -webkit-appearance: none;
  background: var(--bg-elevated);
  border-radius: 2px;
  outline: none;
}

.progress-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--pink);
  cursor: pointer;
}

.progress-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 0.25rem;
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.pain-points {
  margin-top: 1rem;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}

.pain-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: rgba(245, 90, 35, 0.1);
  border-bottom: 1px solid var(--border);
  font-weight: 500;
}

.pain-header i {
  color: var(--amber);
}

.pain-count {
  margin-left: auto;
  background: var(--amber);
  color: black;
  padding: 0.125rem 0.375rem;
  border-radius: 4px;
  font-size: 0.75rem;
}

.pain-list {
  padding: 0.5rem;
}

.pain-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border);
}

.pain-item:last-child {
  border-bottom: none;
}

.pain-item i {
  color: var(--amber);
  font-size: 0.75rem;
}

/* Scrollbar Styling */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: var(--bg);
}

::-webkit-scrollbar-thumb {
  background: var(--border-mid);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--pink-border);
}
</style>