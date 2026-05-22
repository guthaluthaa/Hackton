import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(1, 1, figsize=(18, 13))
ax.set_xlim(0, 18)
ax.set_ylim(0, 13)
ax.axis('off')
fig.patch.set_facecolor('#1a1a2e')
ax.set_facecolor('#1a1a2e')

def draw_box(ax, x, y, w, h, label, color='#16213e', border='#0f3460', fontsize=9, sublabel=None):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                         facecolor=color, edgecolor=border, linewidth=2)
    ax.add_patch(box)
    if sublabel:
        ax.text(x + w/2, y + h/2 + 0.15, label, ha='center', va='center',
                fontsize=fontsize, fontweight='bold', color='white')
        ax.text(x + w/2, y + h/2 - 0.25, sublabel, ha='center', va='center',
                fontsize=7, color='#a0a0a0')
    else:
        ax.text(x + w/2, y + h/2, label, ha='center', va='center',
                fontsize=fontsize, fontweight='bold', color='white')

def draw_db(ax, x, y, label, sublabel=None):
    from matplotlib.patches import Ellipse
    color = '#1a5276'
    border = '#2e86c1'
    rect = plt.Rectangle((x, y), 1.8, 0.8, facecolor=color, edgecolor=border, linewidth=2)
    ax.add_patch(rect)
    ell_top = Ellipse((x+0.9, y+0.8), 1.8, 0.4, facecolor=color, edgecolor=border, linewidth=2)
    ell_bot = Ellipse((x+0.9, y), 1.8, 0.4, facecolor=color, edgecolor=border, linewidth=2)
    ax.add_patch(ell_bot)
    ax.add_patch(rect)
    ax.add_patch(ell_top)
    ax.text(x+0.9, y+0.45, label, ha='center', va='center', fontsize=8, fontweight='bold', color='white')
    if sublabel:
        ax.text(x+0.9, y+0.1, sublabel, ha='center', va='center', fontsize=6, color='#a0a0a0')

def draw_arrow(ax, x1, y1, x2, y2, label='', color='#e94560', style='->'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=1.8,
                               connectionstyle='arc3,rad=0.0'))
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx, my + 0.2, label, ha='center', va='bottom',
                fontsize=7, color='#f5c842', fontstyle='italic',
                bbox=dict(boxstyle='round,pad=0.15', facecolor='#1a1a2e', edgecolor='none', alpha=0.8))

def draw_event_arrow(ax, x1, y1, x2, y2, label='', color='#e94560'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=2.0,
                               connectionstyle='arc3,rad=0.1'))
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx, my + 0.25, label, ha='center', va='bottom',
                fontsize=6.5, color='#f5c842', fontstyle='italic',
                bbox=dict(boxstyle='round,pad=0.15', facecolor='#2d2d44', edgecolor='#f5c842', alpha=0.9, linewidth=0.5))

# Title
ax.text(9, 12.5, 'Hackton - Architecture Overview', ha='center', va='center',
        fontsize=16, fontweight='bold', color='white')
ax.text(9, 12.1, 'Event-Driven Microservices | RabbitMQ + MassTransit', ha='center', va='center',
        fontsize=9, color='#a0a0a0')

# ===== SERVICES =====
# Front-end
draw_box(ax, 0.5, 7.5, 2, 1, 'Front-end', color='#4a148c', border='#7b1fa2')

# Gateway
draw_box(ax, 3.5, 7.5, 2.2, 1, 'API Gateway', color='#1b5e20', border='#388e3c', sublabel='YARP Proxy')

# Upload Service
draw_box(ax, 6.8, 7.5, 2.2, 1, 'Upload Service', color='#0d47a1', border='#1565c0', sublabel='.NET')

# Orchestrator Service
draw_box(ax, 7.5, 4.5, 2.5, 1, 'Orchestrator Service', color='#bf360c', border='#e64a19', sublabel='.NET')

# Analysis Service (AI)
draw_box(ax, 12.5, 7.5, 2.5, 1, 'Analysis Service', color='#4e342e', border='#6d4c41', sublabel='Python + LLM')

# Report Service
draw_box(ax, 12.5, 4.5, 2.2, 1, 'Report Service', color='#1a237e', border='#283593', sublabel='.NET')

# Message Broker
draw_box(ax, 7, 6, 3, 0.8, 'RabbitMQ', color='#ff6f00', border='#ffa000', sublabel='Message Broker')

# MinIO (Blob Storage)
draw_box(ax, 9.5, 9.5, 2, 0.9, 'MinIO', color='#004d40', border='#00796b', sublabel='Blob Storage')

# Seq
draw_box(ax, 15.5, 9.5, 1.8, 0.9, 'Seq', color='#37474f', border='#546e7a', sublabel='Logging')

# ===== DATABASES =====
draw_db(ax, 3.5, 2.0, 'upload_db', 'PostgreSQL')
draw_db(ax, 7.6, 2.0, 'orchestrator_db', 'PostgreSQL')
draw_db(ax, 11.8, 2.0, 'report_db', 'PostgreSQL')

# Single PostgreSQL instance label
ax.text(8.5, 1.2, '── 1 instância PostgreSQL 16, 3 databases lógicos ──',
        ha='center', va='center', fontsize=8, color='#85c1e9', fontstyle='italic')

# ===== ARROWS - Main Flow =====
# Frontend -> Gateway
draw_arrow(ax, 2.5, 8.0, 3.5, 8.0, color='#aaaaaa')

# Gateway -> Upload
draw_arrow(ax, 5.7, 8.0, 6.8, 8.0, color='#aaaaaa')

# Upload -> MinIO
draw_arrow(ax, 8.5, 8.5, 9.8, 9.5, label='Save file', color='#00bfa5')

# Analysis -> MinIO
draw_arrow(ax, 13.2, 8.5, 11.2, 9.7, label='Get file', color='#00bfa5')

# ===== EVENT ARROWS =====
# Upload -> Broker (JobCreatedEvent)
draw_event_arrow(ax, 7.9, 7.5, 8.2, 6.8, label='JobCreatedEvent', color='#e94560')

# Broker -> Orchestrator (consume JobCreated)
draw_event_arrow(ax, 8.5, 6.0, 8.7, 5.5, color='#e94560')

# Orchestrator -> Broker (AnalysisRequestedEvent)
draw_event_arrow(ax, 9.5, 5.5, 9.5, 6.0, color='#42a5f5')
ax.text(10.8, 5.8, 'AnalysisRequestedEvent', ha='center', va='center',
        fontsize=6.5, color='#f5c842', fontstyle='italic',
        bbox=dict(boxstyle='round,pad=0.15', facecolor='#2d2d44', edgecolor='#f5c842', alpha=0.9, linewidth=0.5))

# Broker -> Analysis Service
draw_event_arrow(ax, 10, 6.5, 12.5, 7.8, color='#42a5f5')

# Analysis -> Broker (AnalysisCompletedEvent)
draw_event_arrow(ax, 12.5, 7.5, 10, 6.6, label='AnalysisCompletedEvent', color='#66bb6a')

# Analysis -> Broker (AnalysisFailedEvent) - small note
ax.text(11.5, 7.0, '(or AnalysisFailedEvent)', ha='center', va='center',
        fontsize=5.5, color='#ef5350', fontstyle='italic')

# Orchestrator -> Broker (GenerateReportCommand)
draw_event_arrow(ax, 10, 5.0, 10, 6.0, color='#ab47bc')
ax.text(11.2, 5.2, 'GenerateReportCommand', ha='center', va='center',
        fontsize=6.5, color='#f5c842', fontstyle='italic',
        bbox=dict(boxstyle='round,pad=0.15', facecolor='#2d2d44', edgecolor='#f5c842', alpha=0.9, linewidth=0.5))

# Broker -> Report Service
draw_event_arrow(ax, 10, 6.2, 12.5, 5.0, color='#ab47bc')

# Report -> Broker (ReportGeneratedEvent)
draw_event_arrow(ax, 12.5, 4.8, 10, 6.3, label='ReportGeneratedEvent', color='#26c6da')

# ===== DB Connections =====
draw_arrow(ax, 7.9, 7.5, 4.4, 2.9, label='', color='#2e86c1')
ax.text(5.2, 5.2, 'writes', ha='center', va='center', fontsize=6, color='#85c1e9')

draw_arrow(ax, 8.7, 4.5, 8.5, 2.9, label='', color='#2e86c1')
ax.text(8.2, 3.7, 'reads/writes', ha='center', va='center', fontsize=6, color='#85c1e9')

draw_arrow(ax, 13.6, 4.5, 12.7, 2.9, label='', color='#2e86c1')
ax.text(13.5, 3.7, 'writes', ha='center', va='center', fontsize=6, color='#85c1e9')

# ===== LEGEND =====
legend_y = 0.3
ax.text(0.5, legend_y, 'Legend:', fontsize=8, color='white', fontweight='bold')
ax.plot([2.0, 2.8], [legend_y, legend_y], color='#e94560', lw=2)
ax.text(3.0, legend_y, 'Event flow', fontsize=7, color='#e94560')
ax.plot([5.0, 5.8], [legend_y, legend_y], color='#2e86c1', lw=2)
ax.text(6.0, legend_y, 'DB connection', fontsize=7, color='#2e86c1')
ax.plot([8.5, 9.3], [legend_y, legend_y], color='#00bfa5', lw=2)
ax.text(9.5, legend_y, 'File storage', fontsize=7, color='#00bfa5')
ax.plot([12.0, 12.8], [legend_y, legend_y], color='#aaaaaa', lw=2)
ax.text(13.0, legend_y, 'HTTP request', fontsize=7, color='#aaaaaa')

plt.tight_layout()
plt.savefig('c:/Users/gutha/source/repos/Hackton/docs/architecture.png', dpi=180, bbox_inches='tight',
            facecolor='#1a1a2e', edgecolor='none')
print("OK - imagem salva em docs/architecture.png")
