<template>
  <div 
    class="persona-card"
    :class="{ 'selected': isSelected, [persona.status]: true }"
    @click="$emit('select', persona.id)"
  >
    <div class="card-header">
      <div class="persona-avatar">
        <i :class="getPersonaIcon()"></i>
      </div>
      <div class="persona-info">
        <h4 class="persona-name">{{ persona.name }}</h4>
        <div class="persona-type">{{ persona.type }}</div>
      </div>
      <div class="status-badge" :class="persona.status">
        <i :class="getStatusIcon()"></i>
        <span>{{ persona.status }}</span>
      </div>
    </div>
    
    <div class="card-progress" v-if="persona.status === 'running'">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: `${persona.progress}%` }"></div>
      </div>
      <div class="progress-step">{{ persona.currentStep }}</div>
    </div>
    
    <div class="card-stats" v-if="persona.painPoints?.length">
      <div class="stat-badge pain">
        <i class="fas fa-bug"></i>
        <span>{{ persona.painPoints.length }} pain points</span>
      </div>
    </div>
    
    <div class="card-actions" v-if="persona.status === 'completed'">
      <button class="action-btn" @click.stop="$emit('replay', persona.id)">
        <i class="fas fa-play"></i>
        Replay
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PersonaCard',
  props: {
    persona: {
      type: Object,
      required: true
    },
    isSelected: {
      type: Boolean,
      default: false
    }
  },
  emits: ['select', 'replay'],
  setup(props) {
    const getPersonaIcon = () => {
      const icons = {
        'elderly': 'fas fa-user-graduate',
        'low_vision': 'fas fa-eye',
        'impatient': 'fas fa-tachometer-alt',
        'mobile': 'fas fa-mobile-alt',
        'accessibility': 'fas fa-universal-access'
      }
      return icons[props.persona.type] || 'fas fa-user-circle'
    }
    
    const getStatusIcon = () => {
      const icons = {
        'pending': 'fa-hourglass-half',
        'running': 'fa-spinner fa-pulse',
        'completed': 'fa-check-circle',
        'failed': 'fa-exclamation-circle',
        'blocked': 'fa-ban'
      }
      return icons[props.persona.status] || 'fa-question-circle'
    }
    
    return { getPersonaIcon, getStatusIcon }
  }
}
</script>

<style scoped>
.persona-card {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 0.75rem;
  margin-bottom: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
}

.persona-card:hover {
  border-color: var(--pink-border);
  transform: translateX(4px);
}

.persona-card.selected {
  border-color: var(--pink);
  background: var(--pink-dim);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.persona-avatar {
  width: 40px;
  height: 40px;
  background: var(--bg-surface);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--pink);
  font-size: 1.25rem;
}

.persona-info {
  flex: 1;
}

.persona-name {
  font-size: 0.875rem;
  font-weight: 600;
  margin: 0;
}

.persona-type {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 500;
}

.status-badge.running {
  background: rgba(29, 184, 122, 0.1);
  color: var(--green);
}

.status-badge.completed {
  background: rgba(29, 184, 122, 0.1);
  color: var(--green);
}

.status-badge.failed {
  background: rgba(255, 45, 120, 0.1);
  color: var(--pink);
}

.card-progress {
  margin-top: 0.75rem;
}

.progress-bar {
  height: 4px;
  background: var(--bg-surface);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--pink);
  transition: width 0.3s;
}

.progress-step {
  font-size: 0.7rem;
  color: var(--text-tertiary);
  margin-top: 0.25rem;
}

.card-stats {
  margin-top: 0.5rem;
}

.stat-badge.pain {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background: rgba(245, 166, 35, 0.1);
  border-radius: 6px;
  font-size: 0.7rem;
  color: var(--amber);
}

.card-actions {
  margin-top: 0.5rem;
}

.action-btn {
  width: 100%;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 0.375rem;
  border-radius: 6px;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  border-color: var(--pink);
  color: var(--pink);
}
</style>